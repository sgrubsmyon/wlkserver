from datetime import datetime
from typing import Annotated, List, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Artikel,
    Rabattaktion,
    Verkauf,
    VerkaufPublic,
    VerkaufCreate,
    VerkaufMwst,
    VerkaufMwstPublic,
    # VerkaufMwstCreate,
    VerkaufDetails,
    VerkaufDetailsPublic,
    # VerkaufDetailsCreate,
)
from ..session import SessionDep

router = APIRouter(
    prefix="/verkauf",
    tags=["verkauf"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_verkaeufe(
    session: SessionDep,
    since: Optional[str] = None,
    until: Optional[str] = None,
    only_storno: bool = False,
    include_details: bool = False,
    include_mwst: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    desc: bool = False,
) -> List[dict]:
    selection = select(Verkauf)
    if since:
        selection = selection.where(Verkauf.verkaufsdatum >= datetime.fromisoformat(since))
    if until:
        selection = selection.where(Verkauf.verkaufsdatum <= datetime.fromisoformat(until))
    if only_storno:
        selection = selection.where(Verkauf.storno_von.is_not(None))
    verkaeufe = session.exec(
        selection.offset(offset).limit(limit).order_by(Verkauf.verkaufsdatum.desc() if desc else Verkauf.verkaufsdatum)
    ).all()
    # return verkaeufe

    results = []
    for v in verkaeufe:
        v_obj = VerkaufPublic.model_validate(v).model_dump()
        if include_details:
            details = []
            for d in v.verkauf_details or []:
                d_obj = VerkaufDetailsPublic.model_validate(d, update={
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
            VerkaufDetailsPublic.model_validate(d, update={
                "artikel_name": d.artikel.artikel_name if d.artikel else None,
                "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
            }) for d in (v.verkauf_details or [])
        ]
    if include_mwst:
        v_obj["verkauf_mwst"] = [VerkaufMwstPublic.model_validate(m).model_dump() for m in (v.verkauf_mwst or [])]
    return v_obj


@router.post("/", response_model=VerkaufPublic)
def create_verkauf(verkauf: VerkaufCreate, session: SessionDep):
    # base = VerkaufCreate.model_validate(verkauf)
    new_v = Verkauf.model_validate(verkauf)
    new_v.rechnungs_nr = None
    new_v.verkaufsdatum = datetime.now()
    session.add(new_v)
    session.commit()
    session.refresh(new_v)

    # Add details if present
    # Within the loop over the details, also create the sums of mwst_netto and mwst_betrag per mwst_satz
    mwst_summary = {} # for each mwst_satz, store the sum of mwst_netto and mwst_betrag
    for d in verkauf.get("verkauf_details", []) or []:
        d_obj = VerkaufDetails.model_validate(d)
        d_obj.vd_id = None
        d_obj.rechnungs_nr = new_v.rechnungs_nr
        
        # # If position is not provided, set it to the next available position for this sale (max position + 1, or 1 if no details yet)
        # No: A position of None (or NULL in SQL) has a meaning (it means that the table acts as a modifier to the last table row with a position not NULL, which is used for rabatt rows that refer to the previous article row), so we should not auto-assign a position if it is None
        # if d_obj.position is None:
        #     q = select(VerkaufDetails).where(VerkaufDetails.rechnungs_nr == new_v.rechnungs_nr)
        #     existing = session.exec(q).all()
        #     d_obj.position = (max((e.position or 0) for e in existing) + 1) if existing else 1
        
        # Find ges_preis and mwst_satz for the article of this detail, and add to mwst summary
        if d_obj.artikel_id is not None:
            artikel = session.get(Artikel, d_obj.artikel_id)
            if artikel and artikel.mwst_satz is not None:
                d_obj.mwst_satz = artikel.mwst_satz
            if artikel and not artikel.variabler_preis and artikel.vk_preis is not None:
                d_obj.ges_preis = d_obj.stueckzahl * artikel.vk_preis
        elif d_obj.rabatt_id is not None:
            rabattaktion = session.get(Rabattaktion, d_obj.rabatt_id)
            # TODO Continue here
            # if d_obj.mwst_satz is None or d_obj.ges_preis is None:
            #     raise HTTPException(status_code=400, detail="For rabatt details, mwst_satz and ges_preis must be provided")
        # If this detail is not an article, but a rabatt, we cannot determine mwst_satz and ges_preis from an article, so we require that these values are provided in the request (and validate them in the model)
        # If this detail is an article with variable price, we also require that ges_preis is provided in the request
        # If this detail is an article and has no mwst_satz (e.g. in case of discount/Rabatt), we also require that mwst_satz is provided in the request
        # else:
        #     if d_obj.mwst_satz is None or d_obj.ges_preis is None:
        #         raise HTTPException(status_code=400, detail="For rabatt details, mwst_satz and ges_preis must be provided")

        # TODO Add transaction to the Gutschein table if article_id is 6 (Gutschein) or 7 (Gutscheineinlösung)
        # TODO IDs 6 and 7 need to be defined somehwere centrally, e.g. as constants in the Artikel model, and not hardcoded here

        # Add to mwst summary
        if d_obj.mwst_satz is not None and d_obj.ges_preis is not None:
            if d_obj.mwst_satz not in mwst_summary:
                mwst_summary[d_obj.mwst_satz] = {"mwst_netto": 0.0, "mwst_betrag": 0.0}
            mwst_summary[d_obj.mwst_satz]["mwst_netto"] += d_obj.ges_preis / (1 + d_obj.mwst_satz)
            mwst_summary[d_obj.mwst_satz]["mwst_betrag"] += mwst_summary[d_obj.mwst_satz]["mwst_netto"] * d_obj.mwst_satz
        session.add(d_obj)

    # Create VerkaufMwst objects from the summary
    for mwst_satz, summary in mwst_summary.items():
        m_obj = VerkaufMwst(
            rechnungs_nr=new_v.rechnungs_nr,
            mwst_satz=mwst_satz,
            mwst_netto=summary["mwst_netto"],
            mwst_betrag=summary["mwst_betrag"],
        )
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