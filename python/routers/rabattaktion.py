from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Artikel, Produktgruppe, Rabattaktion, RabattaktionPublic, RabattaktionCreate, RabattaktionUpdate
from ..session import SessionDep


router = APIRouter(
    prefix="/rabattaktion",
    tags=["rabattaktion"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def get_rabattaktionen(
    session: SessionDep,
    since: str | None = None,
    until: str | None = None,
    exclude_deleted: bool = True,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[RabattaktionPublic]:
    selection = select(Rabattaktion).outerjoin(Artikel).outerjoin(Produktgruppe)
    
    # Add a where clause if parameters are provided
    if since:
        selection = selection.where(Rabattaktion.bis >= since)
    if until:
        selection = selection.where(Rabattaktion.von <= until)
    if exclude_deleted:
        selection = selection.where(Rabattaktion.bis > Rabattaktion.von)
    
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
    new_rabattaktion = Rabattaktion.model_validate(rabattaktion)
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
    if rabattaktion.bis is not None and rabattaktion.bis <= datetime.now():
        raise HTTPException(status_code=400, detail="Rabattaktion already ended")
    # There are two cases: if rabattaktion has started (von in the past), we set bis to now to end the rabattaktion
    # If rabattaktion has not started (von in the future), we set bis to von (we have no SQL permissions to just delete it)
    if rabattaktion.von <= datetime.now():
        rabattaktion.bis = datetime.now()
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
    if old_rabattaktion.bis is not None and old_rabattaktion.bis <= datetime.now():
        raise HTTPException(status_code=400, detail="Rabattaktion already ended, cannot update ended Rabattaktion")

    # There are two cases:
    # 1. If rabattaktion has already started (von in the past), we only allow changing name and bis date
    # 2. If rabattaktion has not started yet (von in the future), we allow changing all fields

    rabattaktion_data = rabattaktion.model_dump(exclude_unset=True)
    if (old_rabattaktion.von <= datetime.now()):
        # Case 1: Rabattaktion hase already started, only allow changing name and bis date
        allowed_fields = {"aktionsname", "bis"}
        for key in list(rabattaktion_data.keys()):
            if key not in allowed_fields:
                raise HTTPException(status_code=400, detail=f"Cannot change field '{key}' of started Rabattaktion, only 'aktionsname' and 'bis' can be changed")
    # Case 1 passed the checks or it is Case 2: Rabattaktion has not started yet, all fields can be changed
    for key, value in rabattaktion_data.items():
        setattr(old_rabattaktion, key, value)
    session.add(old_rabattaktion)
    session.commit()
    session.refresh(old_rabattaktion)
    old_rabattaktion = RabattaktionPublic.model_validate(old_rabattaktion, update={
        "produktgruppen_name": old_rabattaktion.produktgruppe.produktgruppen_name if old_rabattaktion.produktgruppe else None,
        "artikel_name": old_rabattaktion.artikel.artikel_name if old_rabattaktion.artikel else None
    })
    return old_rabattaktion