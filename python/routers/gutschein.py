from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select, func

from ..models import Gutschein, GutscheinPublic, GutscheinCreate, GutscheinEinloesen, VerkaufDetails
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

router = APIRouter(
    prefix="/gutschein",
    tags=["gutschein"],
    responses={404: {"description": "Not found"}},
)


def _latest_ids_per_nr(session: SessionDep):
    # latest gutschein_id per gutschein_nr
    sub = (
        select(Gutschein.gutschein_nr, func.max(Gutschein.gutschein_id).label("max_id"))
        .group_by(Gutschein.gutschein_nr)
    )
    return {row[0]: row[1] for row in session.exec(sub).all()}


@router.get("/")
def read_gutscheine(
    session: SessionDep,
    gutschein_nr: Optional[int] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[GutscheinPublic]:
    selection = select(Gutschein)
    if gutschein_nr is not None:
        selection = selection.where(Gutschein.gutschein_nr == gutschein_nr)
    gutscheine = session.exec(
        selection.offset(offset).limit(limit).order_by(Gutschein.gutschein_id)
    ).all()
    return [GutscheinPublic.model_validate(g) for g in gutscheine]


@router.get("/ausstehend")
def read_ausstehende_gutscheine(session: SessionDep) -> list[GutscheinPublic]:
    latest = _latest_ids_per_nr(session)
    if not latest:
        return []
    ids = list(latest.values())
    rows = session.exec(
        select(Gutschein).where(Gutschein.gutschein_id.in_(ids), Gutschein.restbetrag > 0)
    ).all()
    result = []
    for g in rows:
        # initial restbetrag = restbetrag of the earliest entry for this gutschein_nr
        first = session.exec(
            select(Gutschein).where(Gutschein.gutschein_nr == g.gutschein_nr).order_by(Gutschein.gutschein_id)
        ).first()
        anfang = first.restbetrag if first is not None else g.restbetrag
        obj = GutscheinPublic.model_validate(g)
        obj.restbetrag_anfang = anfang
        result.append(obj)
    return result


@router.get("/eingeloest")
def read_eingeloeste_gutscheine(session: SessionDep) -> list[GutscheinPublic]:
    latest = _latest_ids_per_nr(session)
    if not latest:
        return []
    ids = list(latest.values())
    rows = session.exec(
        select(Gutschein).where(Gutschein.gutschein_id.in_(ids), Gutschein.restbetrag <= 0)
    ).all()
    return [GutscheinPublic.model_validate(g) for g in rows]


@router.get("/{gutschein_id}")
def read_single_gutschein(gutschein_id: int, session: SessionDep) -> GutscheinPublic:
    g = session.get(Gutschein, gutschein_id)
    if not g:
        raise HTTPException(status_code=404, detail="Gutschein not found")
    return GutscheinPublic.model_validate(g)


@router.post("/", response_model=GutscheinPublic)
def create_gutschein(gutschein: GutscheinCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    user_id = getattr(gutschein, "user_id", None)
    if user_id is None and credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        p = decode_token(credentials.credentials)
        if p:
            user_id = p.get("user_id")
    if gutschein.gutschein_in_vd_id is not None:
        vd = session.get(VerkaufDetails, gutschein.gutschein_in_vd_id)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    if gutschein.einloesung_in_vd_id is not None:
        vd = session.get(VerkaufDetails, gutschein.einloesung_in_vd_id)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    new_g = Gutschein(
        gutschein_nr=gutschein.gutschein_nr,
        datum=gutschein.datum if gutschein.datum is not None else datetime.now(timezone.utc),
        gutschein_in_vd_id=gutschein.gutschein_in_vd_id,
        einloesung_in_vd_id=gutschein.einloesung_in_vd_id,
        restbetrag=gutschein.restbetrag,
        user_id=user_id,
    )
    new_g.gutschein_id = None
    session.add(new_g)
    session.commit()
    session.refresh(new_g)
    return GutscheinPublic.model_validate(new_g)


@router.post("/{gutschein_id}/einloesen", response_model=GutscheinPublic)
def einloesen_gutschein(
    gutschein_id: int,
    session: SessionDep,
    payload: Optional[GutscheinEinloesen] = None,
    einloesung_in_vd_id: Optional[int] = Query(default=None),
    restbetrag: Optional[float] = Query(default=None),
    betrag: Optional[float] = Query(default=None),
    gutschein_in_vd_id: Optional[int] = Query(default=None),
    _user=Depends(require_user),
):
    original = session.get(Gutschein, gutschein_id)
    if not original:
        raise HTTPException(status_code=404, detail="Gutschein not found")

    p = payload
    ei_vd = einloesung_in_vd_id
    gi_vd = gutschein_in_vd_id
    rb = restbetrag
    b = betrag
    datum = None
    if p is not None:
        if ei_vd is None:
            ei_vd = p.einloesung_in_vd_id
        if gi_vd is None:
            gi_vd = p.gutschein_in_vd_id
        if rb is None:
            rb = p.restbetrag
        if b is None:
            b = p.betrag
        if datum is None:
            datum = p.datum

    if ei_vd is not None:
        vd = session.get(VerkaufDetails, ei_vd)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    if gi_vd is not None:
        vd = session.get(VerkaufDetails, gi_vd)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")

    if gi_vd is None:
        gi_vd = original.gutschein_in_vd_id
    if datum is None:
        datum = datetime.now(timezone.utc)
    if rb is None and b is not None:
        rb = original.restbetrag - b
    if rb is None:
        rb = 0.0

    new_g = Gutschein(
        gutschein_nr=original.gutschein_nr,
        datum=datum,
        gutschein_in_vd_id=gi_vd,
        einloesung_in_vd_id=ei_vd,
        restbetrag=rb,
    )
    new_g.gutschein_id = None
    session.add(new_g)
    session.commit()
    session.refresh(new_g)
    return GutscheinPublic.model_validate(new_g)


# Aliases
read_gutschein = read_gutscheine
read_single_gutschein_alias = read_single_gutschein
create_gutschein_entry = create_gutschein
redeem_gutschein = einloesen_gutschein
read_ausstehend = read_ausstehende_gutscheine
read_ausstehende = read_ausstehende_gutscheine
read_eingeloest = read_eingeloeste_gutscheine