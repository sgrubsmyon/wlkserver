from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import or_
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Artikel, Produktgruppe, Rabattaktion, RabattaktionPublic, RabattaktionCreate, RabattaktionUpdate
from ..session import SessionDep
from ..utils.validation import ensure_non_negative, ensure_positive, ensure_range


router = APIRouter(
    prefix="/rabattaktion",
    tags=["rabattaktion"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)

def _validate_discounts(values: dict):
    """Cross-field validation of the discount configuration.

    Single-field ranges are enforced by the models; this checks the business
    rules that span several fields (also for PATCH, where the merged state counts).
    """
    ensure_range(values.get("rabatt_relativ"), 0, 1, "rabatt_relativ")
    ensure_non_negative(values.get("rabatt_absolut"), "rabatt_absolut")
    ensure_positive(values.get("mengenrabatt_schwelle"), "mengenrabatt_schwelle")
    ensure_positive(
        values.get("mengenrabatt_anzahl_kostenlos"), "mengenrabatt_anzahl_kostenlos"
    )
    ensure_range(values.get("mengenrabatt_relativ"), 0, 1, "mengenrabatt_relativ")

    if values.get("mengenrabatt_anzahl_kostenlos") is not None and values.get("mengenrabatt_schwelle") is None:
        raise HTTPException(
            status_code=400,
            detail="mengenrabatt_anzahl_kostenlos requires mengenrabatt_schwelle",
        )
    if values.get("mengenrabatt_relativ") is not None and values.get("mengenrabatt_schwelle") is None:
        raise HTTPException(
            status_code=400,
            detail="mengenrabatt_relativ requires mengenrabatt_schwelle",
        )

    von, bis = values.get("von"), values.get("bis")
    if von is not None and bis is not None and bis <= von:
        raise HTTPException(
            status_code=400,
            detail="Invalid dates: 'bis' must be after 'von' or null",
        )


@router.get("/")
def read_rabattaktionen(
    session: SessionDep,
    von: Optional[datetime] = None,
    bis: Optional[datetime] = None,
    artikel_id: Optional[int] = None,
    produktgruppen_id: Optional[int] = None,
    search_string: str = "",
    current_only: bool = False,
    exclude_deleted: bool = True,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[RabattaktionPublic]:
    selection = select(Rabattaktion).outerjoin(Artikel).outerjoin(Produktgruppe)

    # Add a where clause if parameters are provided
    if von is not None:
        # open-ended actions (bis IS NULL) run forever and must stay included
        selection = selection.where(
            or_(Rabattaktion.bis.is_(None), Rabattaktion.bis >= von)
        )
    if bis is not None:
        selection = selection.where(Rabattaktion.von <= bis)
    if artikel_id is not None:
        selection = selection.where(Rabattaktion.artikel_id == artikel_id)
    if produktgruppen_id is not None:
        selection = selection.where(Rabattaktion.produktgruppen_id == produktgruppen_id)
    if current_only:
        now = datetime.now(timezone.utc)
        selection = selection.where(
            Rabattaktion.von <= now,
            or_(Rabattaktion.bis.is_(None), Rabattaktion.bis >= now),
        )
    if exclude_deleted:
        # Java Rabattaktionen filter: "bis != von OR bis IS NULL"
        selection = selection.where(
            or_(Rabattaktion.bis.is_(None), Rabattaktion.bis > Rabattaktion.von)
        )
    for term in search_string.split():
        selection = selection.where(Rabattaktion.aktionsname.contains(term))

    # Execute the query with offset and limit
    rabattaktionen = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Rabattaktion.von, Rabattaktion.bis)).all()
    
    # Prepare the response
    # (add data from the joined tables)
    return_obj = []
    for ra in rabattaktionen:
        obj = RabattaktionPublic.model_validate(ra, update={
            "produktgruppen_name": ra.produktgruppe.produktgruppen_name if ra.produktgruppe else None,
            "artikel_name": ra.artikel.artikel_name if ra.artikel else None
        })
        return_obj.append(obj)
    
    return return_obj


@router.get("/{rabattaktion_id}")
def read_single_rabattaktion(rabattaktion_id: int, session: SessionDep) -> RabattaktionPublic:
    rabattaktion = session.get(Rabattaktion, rabattaktion_id)
    if not rabattaktion:
        raise HTTPException(status_code=404, detail="Rabattaktion not found")
    rabattaktion = RabattaktionPublic.model_validate(rabattaktion, update={
        "produktgruppen_name": rabattaktion.produktgruppe.produktgruppen_name if rabattaktion.produktgruppe else None,
        "artikel_name": rabattaktion.artikel.artikel_name if rabattaktion.artikel else None
    })
    return rabattaktion


@router.post("/", response_model=RabattaktionPublic)
def create_rabattaktion(rabattaktion: RabattaktionCreate, session: SessionDep):
    values = rabattaktion.model_dump()
    _validate_discounts(values)
    new_rabattaktion = Rabattaktion.model_validate(rabattaktion)
    # Normalize naive datetimes to UTC
    if new_rabattaktion.von.tzinfo is None:
        new_rabattaktion.von = new_rabattaktion.von.replace(tzinfo=timezone.utc)
    if new_rabattaktion.bis is not None and new_rabattaktion.bis.tzinfo is None:
        new_rabattaktion.bis = new_rabattaktion.bis.replace(tzinfo=timezone.utc)

    session.add(new_rabattaktion)
    session.commit()
    session.refresh(new_rabattaktion)
    new_rabattaktion = RabattaktionPublic.model_validate(new_rabattaktion, update={
        "produktgruppen_name": new_rabattaktion.produktgruppe.produktgruppen_name if new_rabattaktion.produktgruppe else None,
        "artikel_name": new_rabattaktion.artikel.artikel_name if new_rabattaktion.artikel else None
    })
    return new_rabattaktion


@router.delete("/{rabattaktion_id}")
def delete_rabattaktion(rabattaktion_id: int, session: SessionDep):
    rabattaktion = session.get(Rabattaktion, rabattaktion_id)
    if not rabattaktion:
        raise HTTPException(status_code=404, detail="Rabattaktion not found")
    if rabattaktion.bis is not None and rabattaktion.bis <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Rabattaktion already ended")
    # There are two cases: if rabattaktion has started (von in the past), we set bis to now to end the rabattaktion
    # If rabattaktion has not started (von in the future), we set bis to von (we have no SQL permissions to just delete it)
    if rabattaktion.von <= datetime.now(timezone.utc):
        rabattaktion.bis = datetime.now(timezone.utc)
        session.add(rabattaktion)
        session.commit()
        return {"message": "Rabattaktion's bis date set to now to end it"}
    else:
        rabattaktion.bis = rabattaktion.von
        session.add(rabattaktion)
        session.commit()
        return {"message": "Rabattaktion's bis date set to von date to delete it"}


@router.patch("/{rabattaktion_id}", response_model=RabattaktionPublic)
def update_rabattaktion(rabattaktion_id: int, rabattaktion: RabattaktionUpdate, session: SessionDep):
    old_rabattaktion = session.get(Rabattaktion, rabattaktion_id)
    
    if not old_rabattaktion:
        raise HTTPException(status_code=404, detail="Rabattaktion not found")
    if old_rabattaktion.bis is not None and old_rabattaktion.bis <= datetime.now(timezone.utc):
        raise HTTPException(status_code=400, detail="Rabattaktion already ended, cannot update ended Rabattaktion")

    # There are two cases:
    # 1. If rabattaktion has already started (von in the past), we only allow changing name and bis date
    # 2. If rabattaktion has not started yet (von in the future), we allow changing all fields

    rabattaktion_data = rabattaktion.model_dump(exclude_unset=True)
    if (old_rabattaktion.von <= datetime.now(timezone.utc)):
        # Case 1: Rabattaktion hase already started, only allow changing name and bis date
        allowed_fields = {"aktionsname", "bis"}
        for key in list(rabattaktion_data.keys()):
            if key not in allowed_fields:
                raise HTTPException(status_code=400, detail=f"Cannot change field '{key}' of started Rabattaktion, only 'aktionsname' and 'bis' can be changed")
    # validate the resulting state, not just the supplied fields
    merged = {
        "von": old_rabattaktion.von,
        "bis": old_rabattaktion.bis,
        "rabatt_relativ": old_rabattaktion.rabatt_relativ,
        "rabatt_absolut": old_rabattaktion.rabatt_absolut,
        "mengenrabatt_schwelle": old_rabattaktion.mengenrabatt_schwelle,
        "mengenrabatt_anzahl_kostenlos": old_rabattaktion.mengenrabatt_anzahl_kostenlos,
        "mengenrabatt_relativ": old_rabattaktion.mengenrabatt_relativ,
    }
    merged.update(rabattaktion_data)
    _validate_discounts(merged)

    # Case 1 passed the checks or it is Case 2: Rabattaktion has not started yet, all fields can be changed
    for key, value in rabattaktion_data.items():
        if isinstance(value, datetime) and value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        setattr(old_rabattaktion, key, value)
    session.add(old_rabattaktion)
    session.commit()
    session.refresh(old_rabattaktion)
    old_rabattaktion = RabattaktionPublic.model_validate(old_rabattaktion, update={
        "produktgruppen_name": old_rabattaktion.produktgruppe.produktgruppen_name if old_rabattaktion.produktgruppe else None,
        "artikel_name": old_rabattaktion.artikel.artikel_name if old_rabattaktion.artikel else None
    })
    return old_rabattaktion