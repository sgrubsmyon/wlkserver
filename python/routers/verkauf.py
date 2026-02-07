from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Verkauf,
    VerkaufPublic,
    VerkaufCreate,
    VerkaufMwst,
    VerkaufMwstPublic,
    VerkaufMwstCreate,
    VerkaufDetails,
    VerkaufDetailsPublic,
    VerkaufDetailsCreate,
)
from ..session import SessionDep

router = APIRouter(
    prefix="/verkauf",
    tags=["verkauf"],
    responses={404: {"description": "Not found"}},
)


# class VerkaufPayload(BaseModel):
#     verkaufsdatum: datetime
#     ec_zahlung: bool = False
#     kunde_gibt: Optional[float] = None
#     storno_von: Optional[int] = None
#     verkauf_details: Optional[List[VerkaufDetailsCreate]] = None
#     verkauf_mwst: Optional[List[VerkaufMwstCreate]] = None


@router.get("/")
def read_verkaeufe(
    session: SessionDep,
    since: Optional[str] = None,
    until: Optional[str] = None,
    include_details: bool = False,
    include_mwst: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> List[dict]:
    selection = select(Verkauf)
    if since:
        selection = selection.where(Verkauf.verkaufsdatum >= datetime.fromisoformat(since))
    if until:
        selection = selection.where(Verkauf.verkaufsdatum <= datetime.fromisoformat(until))
    verkaeufe = session.exec(
        selection.offset(offset).limit(limit).order_by(Verkauf.verkaufsdatum)
    ).all()
    # return verkaeufe

    results = []
    for v in verkaeufe:
        v_obj = VerkaufPublic.model_validate(v).model_dump()
        if include_details:
            details = []
            for d in v.verkauf_details or []:
                d_obj = VerkaufDetailsPublic.model_validate(d).model_dump(update={
                    "artikel_name": d.artikel.artikel_name if d.artikel else None,
                    "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                    "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
                })
                details.append(d_obj)
            v_obj["verkauf_details"] = details
        if include_mwst:
            mwsts = [VerkaufMwstPublic.model_validate(m).model_dump() for m in (v.verkauf_mwst or [])]
            v_obj["verkauf_mwst"] = mwsts
        results.append(v_obj)
    return results


@router.get("/{rechnungs_nr}")
def read_single_verkauf(
    rechnungs_nr: int,
    session: SessionDep,
    include_details: bool = True,
    include_mwst: bool = True,
) -> dict:
    v = session.get(Verkauf, rechnungs_nr)
    if not v:
        raise HTTPException(status_code=404, detail="Verkauf not found")
    v_obj = VerkaufPublic.model_validate(v).model_dump()
    if include_details:
        v_obj["verkauf_details"] = [
            VerkaufDetailsPublic.model_validate(d).model_dump(update={
                "artikel_name": d.artikel.artikel_name if d.artikel else None,
                "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
            }) for d in (v.verkauf_details or [])
        ]
    if include_mwst:
        v_obj["verkauf_mwst"] = [VerkaufMwstPublic.model_validate(m).model_dump() for m in (v.verkauf_mwst or [])]
    return v_obj


@router.post("/", response_model=dict)
def create_verkauf(payload: dict, session: SessionDep):
    base = VerkaufCreate.model_validate(payload)
    new_v = Verkauf.model_validate(base)
    new_v.rechnungs_nr = None
    session.add(new_v)
    session.commit()
    session.refresh(new_v)

    # Add details if present
    for d in payload.get("verkauf_details", []) or []:
        d_obj = VerkaufDetails.model_validate(d)
        d_obj.vd_id = None
        d_obj.rechnungs_nr = new_v.rechnungs_nr
        if d_obj.position is None:
            q = select(VerkaufDetails).where(VerkaufDetails.rechnungs_nr == new_v.rechnungs_nr)
            existing = session.exec(q).all()
            d_obj.position = (max((e.position or 0) for e in existing) + 1) if existing else 1
        session.add(d_obj)

    # Add mwst if present
    for m in payload.get("verkauf_mwst", []) or []:
        m_obj = VerkaufMwst.model_validate(m)
        m_obj.rechnungs_nr = new_v.rechnungs_nr
        session.add(m_obj)

    session.commit()
    session.refresh(new_v)
    return read_single_verkauf(new_v.rechnungs_nr, session)


# --- Storno endpoint ---


@router.post("/{rechnungs_nr}/storno", response_model=dict)
def storno_verkauf(rechnungs_nr: int, session: SessionDep):
    original = session.get(Verkauf, rechnungs_nr)
    if not original:
        raise HTTPException(status_code=404, detail="Original Verkauf not found")
    # Prevent storno of a storno
    if original.storno_von is not None:
        raise HTTPException(status_code=400, detail="Cannot storno a storno")
    # Prevent duplicate storno (if any sale already references this as storno_von)
    existing_storno = session.exec(select(Verkauf).where(Verkauf.storno_von == rechnungs_nr)).first()
    if existing_storno:
        raise HTTPException(status_code=400, detail="This Verkauf already has a storno")

    # Create storno sale
    storno_sale = Verkauf(
        verkaufsdatum=datetime.now(),
        ec_zahlung=False,
        kunde_gibt=None,
        storno_von=rechnungs_nr,
    )
    storno_sale.rechnungs_nr = None
    session.add(storno_sale)
    session.commit()
    session.refresh(storno_sale)

    # Create inverted details
    for d in original.verkauf_details or []:
        inv = VerkaufDetails(
            position=d.position,
            stueckzahl=-d.stueckzahl,
            ges_preis=-d.ges_preis,
            mwst_satz=d.mwst_satz,
            rechnungs_nr=storno_sale.rechnungs_nr,
            artikel_id=d.artikel_id,
            rabatt_id=d.rabatt_id,
        )
        session.add(inv)

    # Create inverted mwst entries
    for m in original.verkauf_mwst or []:
        inv_m = VerkaufMwst(
            rechnungs_nr=storno_sale.rechnungs_nr,
            mwst_satz=m.mwst_satz,
            mwst_netto=-m.mwst_netto,
            mwst_betrag=-m.mwst_betrag,
        )
        session.add(inv_m)

    session.commit()
    session.refresh(storno_sale)
    return read_single_verkauf(storno_sale.rechnungs_nr, session)


# --- VerkaufMwst subroutes ---


# @router.get("/{rechnungs_nr}/mwst")
# def read_verkauf_mwst(rechnungs_nr: int, session: SessionDep) -> List[VerkaufMwstPublic]:
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     return [VerkaufMwstPublic.model_validate(m) for m in (v.verkauf_mwst or [])]


# @router.post("/{rechnungs_nr}/mwst", response_model=List[VerkaufMwstPublic])
# def create_verkauf_mwst(rechnungs_nr: int, mwst: List[VerkaufMwstCreate], session: SessionDep):
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     created = []
#     for m in mwst:
#         m_obj = VerkaufMwst.model_validate(m)
#         m_obj.rechnungs_nr = rechnungs_nr
#         session.add(m_obj)
#         created.append(m_obj)
#     session.commit()
#     for c in created:
#         session.refresh(c)
#     return [VerkaufMwstPublic.model_validate(c) for c in created]


## @router.delete("/{rechnungs_nr}/mwst/{mwst_satz}")
## def delete_verkauf_mwst(rechnungs_nr: int, mwst_satz: float, session: SessionDep):
##     key = (rechnungs_nr, mwst_satz)
##     stmt = select(VerkaufMwst).where(
##         VerkaufMwst.rechnungs_nr == rechnungs_nr,
##         VerkaufMwst.mwst_satz == mwst_satz,
##     )
##     row = session.exec(stmt).one_or_none()
##     if not row:
##         raise HTTPException(status_code=404, detail="VerkaufMwst not found")
##     session.delete(row)
##     session.commit()
##     return {"message": "VerkaufMwst deleted"}


# --- VerkaufDetails subroutes ---


# @router.get("/{rechnungs_nr}/details")
# def read_verkauf_details(rechnungs_nr: int, session: SessionDep) -> List[dict]:
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     out = []
#     for d in (v.verkauf_details or []):
#         d_obj = VerkaufDetailsPublic.model_validate(d).model_dump(update={
#             "artikel_name": d.artikel.artikel_name if d.artikel else None,
#             "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
#             "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
#         })
#         out.append(d_obj)
#     return out


# @router.post("/{rechnungs_nr}/details", response_model=VerkaufDetailsPublic)
# def create_verkauf_detail(rechnungs_nr: int, detail: VerkaufDetailsCreate, session: SessionDep):
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     d = VerkaufDetails.model_validate(detail)
#     d.vd_id = None
#     d.rechnungs_nr = rechnungs_nr
#     if d.position is None:
#         q = select(VerkaufDetails).where(VerkaufDetails.rechnungs_nr == rechnungs_nr)
#         existing = session.exec(q).all()
#         d.position = (max((e.position or 0) for e in existing) + 1) if existing else 1
#     session.add(d)
#     session.commit()
#     session.refresh(d)
#     # enrich with artikel info
#     d_out = VerkaufDetailsPublic.model_validate(d).model_dump(update={
#         "artikel_name": d.artikel.artikel_name if d.artikel else None,
#         "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
#         "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
#     })
#     return d_out


## @router.delete("/{rechnungs_nr}/details/{vd_id}")
## def delete_verkauf_detail(rechnungs_nr: int, vd_id: int, session: SessionDep):
##     d = session.get(VerkaufDetails, vd_id)
##     if not d or d.rechnungs_nr != rechnungs_nr:
##         raise HTTPException(status_code=404, detail="VerkaufDetails not found")
##     session.delete(d)
##     session.commit()
##     return {"message": "VerkaufDetails deleted"}


## @router.patch("/{rechnungs_nr}/details/{vd_id}", response_model=VerkaufDetailsPublic)
## def update_verkauf_detail(rechnungs_nr: int, vd_id: int, detail: VerkaufDetailsCreate, session: SessionDep):
##     d = session.get(VerkaufDetails, vd_id)
##     if not d or d.rechnungs_nr != rechnungs_nr:
##         raise HTTPException(status_code=404, detail="VerkaufDetails not found")
##     data = detail.model_dump(exclude_unset=True)
##     for k, v in data.items():
##         setattr(d, k, v)
##     session.add(d)
##     session.commit()
##     session.refresh(d)
##     d_out = VerkaufDetailsPublic.model_validate(d).model_dump(update={
##         "artikel_name": d.artikel.artikel_name if d.artikel else None,
##         "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
##         "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
##     })
##     return d_out