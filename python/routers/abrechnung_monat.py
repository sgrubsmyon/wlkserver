from datetime import datetime, timezone, date
from typing import Annotated, Optional
import calendar

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    AbrechnungMonat,
    AbrechnungMonatPublic,
    AbrechnungMonatCreate,
    AbrechnungMonatMwst,
    AbrechnungMonatMwstPublic,
    AbrechnungTag,
    AbrechnungTagMwst,
)
from ..session import SessionDep

router = APIRouter(
    prefix="/abrechnung/monat",
    tags=["abrechnung_monat"],
    responses={404: {"description": "Not found"}},
)


def _month_bounds(monat: date):
    first = monat.replace(day=1)
    last_day = calendar.monthrange(first.year, first.month)[1]
    last = first.replace(day=last_day)
    return first, last


def _parse_month(value) -> date:
    if isinstance(value, date):
        return value.replace(day=1)
    if isinstance(value, str):
        # accept YYYY-MM or YYYY-MM-DD
        parts = value.split("-")
        y = int(parts[0])
        m = int(parts[1])
        return date(y, m, 1)
    raise HTTPException(status_code=400, detail="Invalid month format")


@router.get("/")
def read_abrechnung_monate(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AbrechnungMonatPublic]:
    rows = session.exec(
        select(AbrechnungMonat).offset(offset).limit(limit).order_by(AbrechnungMonat.id)
    ).all()
    return [AbrechnungMonatPublic.model_validate(r) for r in rows]


@router.get("/offen")
def read_offene_abrechnung_monate(session: SessionDep) -> list[str]:
    # months present in abrechnung_tag
    tags = session.exec(select(AbrechnungTag)).all()
    months_present = set()
    for t in tags:
        months_present.add((t.zeitpunkt.year, t.zeitpunkt.month))
    # months already settled
    settled = session.exec(select(AbrechnungMonat)).all()
    settled_set = set((m.monat.year, m.monat.month) for m in settled)
    now = datetime.now(timezone.utc)
    result = []
    for (y, m) in months_present:
        if (y, m) in settled_set:
            continue
        # only months that have already passed (<= current month)
        if (y, m) > (now.year, now.month):
            continue
        result.append(f"{y:04d}-{m:02d}")
    result.sort()
    return result


@router.get("/{monat_id}")
def read_single_abrechnung_monat(monat_id: int, session: SessionDep) -> dict:
    m = session.get(AbrechnungMonat, monat_id)
    if not m:
        raise HTTPException(status_code=404, detail="AbrechnungMonat not found")
    mwsts = session.exec(
        select(AbrechnungMonatMwst).where(AbrechnungMonatMwst.id == monat_id)
    ).all()
    obj = AbrechnungMonatPublic.model_validate(m).model_dump()
    obj["mwst"] = [AbrechnungMonatMwstPublic.model_validate(x).model_dump() for x in mwsts]
    return obj


@router.post("/", response_model=AbrechnungMonatPublic)
def create_abrechnung_monat(payload: Optional[AbrechnungMonatCreate], session: SessionDep):
    p = payload or AbrechnungMonatCreate()

    # Determine target month
    if p.monat is not None:
        target_month = _parse_month(p.monat)
    else:
        # find earliest unsettled month from abrechnung_tag
        tags = session.exec(select(AbrechnungTag).order_by(AbrechnungTag.id)).all()
        settled = session.exec(select(AbrechnungMonat)).all()
        settled_set = set((m.monat.year, m.monat.month) for m in settled)
        chosen = None
        for t in tags:
            key = (t.zeitpunkt.year, t.zeitpunkt.month)
            if key not in settled_set:
                chosen = key
                break
        if chosen is None:
            # fallback to current month
            now = datetime.now(timezone.utc)
            chosen = (now.year, now.month)
        target_month = date(chosen[0], chosen[1], 1)

    first, last = _month_bounds(target_month)

    # daily settlements in that month
    daily = session.exec(
        select(AbrechnungTag).where(
            AbrechnungTag.zeitpunkt >= datetime(first.year, first.month, first.day, tzinfo=timezone.utc),
            AbrechnungTag.zeitpunkt <= datetime(last.year, last.month, last.day, 23, 59, 59, tzinfo=timezone.utc),
        )
    ).all()
    if not daily:
        raise HTTPException(status_code=400, detail="No daily settlements for this month")

    von_id = min(d.id for d in daily)
    bis_id = max(d.id for d in daily)

    # If provided, override range
    if p.abrechnung_tag_id_von is not None:
        von_id = p.abrechnung_tag_id_von
    if p.abrechnung_tag_id_bis is not None:
        bis_id = p.abrechnung_tag_id_bis

    # Delete existing settlement for month if present
    existing = session.exec(
        select(AbrechnungMonat).where(AbrechnungMonat.monat == target_month)
    ).first()
    if existing:
        session.exec(
            select(AbrechnungMonatMwst).where(AbrechnungMonatMwst.id == existing.id)
        )
        for m in session.exec(select(AbrechnungMonatMwst).where(AbrechnungMonatMwst.id == existing.id)).all():
            session.delete(m)
        session.delete(existing)
        session.commit()

    # Aggregate mwst from daily settlements in range
    daily_in_range = session.exec(
        select(AbrechnungTag).where(AbrechnungTag.id >= von_id, AbrechnungTag.id <= bis_id)
    ).all()
    mwst_map = {}
    for d in daily_in_range:
        for m in session.exec(select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == d.id)).all():
            entry = mwst_map.setdefault(m.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["netto"] += m.mwst_netto
            entry["betrag"] += m.mwst_betrag
            entry["bar"] += m.bar_brutto

    am = AbrechnungMonat(
        monat=target_month,
        abrechnung_tag_id_von=von_id,
        abrechnung_tag_id_bis=bis_id,
    )
    am.id = None
    session.add(am)
    session.commit()
    session.refresh(am)

    for satz, vals in mwst_map.items():
        row = AbrechnungMonatMwst(
            id=am.id,
            mwst_satz=satz,
            mwst_netto=vals["netto"],
            mwst_betrag=vals["betrag"],
            bar_brutto=vals["bar"],
        )
        session.add(row)
    session.commit()

    return AbrechnungMonatPublic.model_validate(am)


# Aliases
read_abrechnung_monat = read_abrechnung_monate
create_abrechnung_monat_entry = create_abrechnung_monat