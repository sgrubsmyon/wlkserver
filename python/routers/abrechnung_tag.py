from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import select

from ..models import (
    AbrechnungTag,
    AbrechnungTagPublic,
    AbrechnungTagCreate,
    AbrechnungTagMwst,
    AbrechnungTagMwstPublic,
    Verkauf,
)
from ..session import SessionDep
from ..dependencies import require_user
from ..business.cash_register import end_of_day_procedure
from ..business.settlement import create_daily_settlement, last_settlement

router = APIRouter(
    prefix="/abrechnung/tag",
    tags=["abrechnung_tag"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_abrechnung_tags(
    session: SessionDep,
    desc: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AbrechnungTagPublic]:
    order = AbrechnungTag.id.desc() if desc else AbrechnungTag.id
    rows = session.exec(
        select(AbrechnungTag).offset(offset).limit(limit).order_by(order)
    ).all()
    return [AbrechnungTagPublic.model_validate(r) for r in rows]


@router.get("/offen")
def read_offene_abrechnung_tags(session: SessionDep) -> list[str]:
    last = last_settlement(session)
    last_bis = last.rechnungs_nr_bis if last else 0
    sales = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.verkaufsdatum)
    ).all()
    dates = []
    seen = set()
    for s in sales:
        d = s.verkaufsdatum.date().isoformat()
        if d not in seen:
            seen.add(d)
            dates.append(d)
    return dates


@router.get("/vorschau")
def read_abrechnung_tag_preview(session: SessionDep) -> dict:
    """Preview the open Tagesabschluss without writing anything."""
    return end_of_day_procedure(session)


@router.get("/{tag_id}")
def read_single_abrechnung_tag(tag_id: int, session: SessionDep) -> dict:
    t = session.get(AbrechnungTag, tag_id)
    if not t:
        raise HTTPException(status_code=404, detail="AbrechnungTag not found")
    mwsts = session.exec(
        select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == tag_id)
    ).all()
    obj = AbrechnungTagPublic.model_validate(t).model_dump()
    obj["mwst"] = [AbrechnungTagMwstPublic.model_validate(m).model_dump() for m in mwsts]
    return obj


@router.post("/", response_model=AbrechnungTagPublic)
def create_abrechnung_tag(
    payload: Optional[AbrechnungTagCreate],
    session: SessionDep,
    _user=Depends(require_user),
):
    return create_daily_settlement(
        session, payload, user_id=getattr(_user, "user_id", None)
    )


# Aliases
read_abrechnung_tag = read_abrechnung_tags
read_abrechnung_tags_alias = read_abrechnung_tags
create_abrechnung_tag_entry = create_abrechnung_tag
