from datetime import datetime, timezone, date
from typing import Annotated, Optional
import calendar

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import select

from ..models import (
    AbrechnungJahr,
    AbrechnungJahrPublic,
    AbrechnungJahrCreate,
    AbrechnungJahrMwst,
    AbrechnungJahrMwstPublic,
    AbrechnungMonat,
    AbrechnungMonatMwst,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user

router = APIRouter(
    prefix="/abrechnung/jahr",
    tags=["abrechnung_jahr"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_abrechnung_jahre(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AbrechnungJahrPublic]:
    rows = session.exec(
        select(AbrechnungJahr).offset(offset).limit(limit).order_by(AbrechnungJahr.id)
    ).all()
    return [AbrechnungJahrPublic.model_validate(r) for r in rows]


@router.get("/offen")
def read_offene_abrechnung_jahre(session: SessionDep) -> list[int]:
    monate = session.exec(select(AbrechnungMonat)).all()
    years_present = set(m.monat.year for m in monate)
    settled = session.exec(select(AbrechnungJahr)).all()
    settled_set = set(a.jahr for a in settled)
    now = datetime.now(timezone.utc)
    result = []
    for y in years_present:
        if y in settled_set:
            continue
        if y > now.year:
            continue
        result.append(y)
    result.sort()
    return result


@router.get("/{jahr_id}")
def read_single_abrechnung_jahr(jahr_id: int, session: SessionDep) -> dict:
    j = session.get(AbrechnungJahr, jahr_id)
    if not j:
        raise HTTPException(status_code=404, detail="AbrechnungJahr not found")
    mwsts = session.exec(
        select(AbrechnungJahrMwst).where(AbrechnungJahrMwst.id == jahr_id)
    ).all()
    obj = AbrechnungJahrPublic.model_validate(j).model_dump()
    obj["mwst"] = [AbrechnungJahrMwstPublic.model_validate(x).model_dump() for x in mwsts]
    return obj


@router.post("/", response_model=AbrechnungJahrPublic)
def create_abrechnung_jahr(payload: Optional[AbrechnungJahrCreate], session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    p = payload or AbrechnungJahrCreate()

    if p.jahr is not None:
        target_year = p.jahr
    else:
        monate = session.exec(select(AbrechnungMonat).order_by(AbrechnungMonat.id)).all()
        settled = session.exec(select(AbrechnungJahr)).all()
        settled_set = set(a.jahr for a in settled)
        chosen = None
        for m in monate:
            if m.monat.year not in settled_set:
                chosen = m.monat.year
                break
        if chosen is None:
            now = datetime.now(timezone.utc)
            chosen = now.year
        target_year = chosen

    monate_in_year = session.exec(select(AbrechnungMonat)).all()
    monate_in_year = [m for m in monate_in_year if m.monat.year == target_year]
    if not monate_in_year:
        raise HTTPException(status_code=400, detail="No monthly settlements for this year")

    von_id = min(m.id for m in monate_in_year)
    bis_id = max(m.id for m in monate_in_year)

    if p.abrechnung_tag_id_von is not None:
        von_id = p.abrechnung_tag_id_von
    if p.abrechnung_tag_id_bis is not None:
        bis_id = p.abrechnung_tag_id_bis

    # map monthly -> tag ids: use provided or from monate
    tag_von = min(m.abrechnung_tag_id_von for m in monate_in_year)
    tag_bis = max(m.abrechnung_tag_id_bis for m in monate_in_year)
    if p.abrechnung_tag_id_von is not None:
        tag_von = p.abrechnung_tag_id_von
    if p.abrechnung_tag_id_bis is not None:
        tag_bis = p.abrechnung_tag_id_bis

    existing = session.exec(
        select(AbrechnungJahr).where(AbrechnungJahr.jahr == target_year)
    ).first()
    if existing:
        for m in session.exec(select(AbrechnungJahrMwst).where(AbrechnungJahrMwst.id == existing.id)).all():
            session.delete(m)
        session.delete(existing)
        session.commit()

    mwst_map = {}
    for m in monate_in_year:
        for x in session.exec(select(AbrechnungMonatMwst).where(AbrechnungMonatMwst.id == m.id)).all():
            entry = mwst_map.setdefault(x.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["netto"] += x.mwst_netto
            entry["betrag"] += x.mwst_betrag
            entry["bar"] += x.bar_brutto

    aj = AbrechnungJahr(
        jahr=target_year,
        abrechnung_tag_id_von=tag_von,
        abrechnung_tag_id_bis=tag_bis,
    )
    aj.id = None
    session.add(aj)
    session.commit()
    session.refresh(aj)

    for satz, vals in mwst_map.items():
        row = AbrechnungJahrMwst(
            id=aj.id,
            mwst_satz=satz,
            mwst_netto=vals["netto"],
            mwst_betrag=vals["betrag"],
            bar_brutto=vals["bar"],
        )
        session.add(row)
    session.commit()

    return AbrechnungJahrPublic.model_validate(aj)


# Aliases
read_abrechnung_jahr = read_abrechnung_jahre
create_abrechnung_jahr_entry = create_abrechnung_jahr