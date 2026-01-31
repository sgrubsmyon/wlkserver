from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Artikel, Produktgruppe, Rabattaktion, RabattaktionPublic, RabattaktionCreate #, RabattaktionUpdate
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
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[RabattaktionPublic]:
    selection = select(Rabattaktion).join(Artikel).join(Produktgruppe)
    
    # Add a where clause if since or until is provided
    if since:
        selection = selection.where(Rabattaktion.bis >= since)
    if until:
        selection = selection.where(Rabattaktion.von <= until)
    
    # Execute the query with offset and limit
    rabattaktionen = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Rabattaktion.von)).all()
    
    # Prepare the response
    # (add data from the joined tables)
    return_obj = []
    for ra in rabattaktionen:
        obj = RabattaktionPublic.model_validate(ra, update={
            "produktgruppen_name": None if ra.produktgruppe is None else ra.produktgruppe.produktgruppen_name,
            "artikel_name": ra.artikel.artikel_name if ra.artikel else None
        })
        return_obj.append(obj)
    
    return return_obj


@router.get("/{rabattaktion_id}")
def read_single_rabattaktion(rabattaktion_id: int, session: SessionDep) -> Rabattaktion:
    rabattaktion = session.get(Rabattaktion, rabattaktion_id)
    if not rabattaktion:
        raise HTTPException(status_code=404, detail="Rabattaktion not found")
    return 


@router.post("/", response_model=RabattaktionPublic)
def create_rabattaktion(rabattaktion: RabattaktionCreate, session: SessionDep):
    new_rabattaktion = Rabattaktion.model_validate(rabattaktion)
    session.add(new_rabattaktion)
    session.commit()
    session.refresh(new_rabattaktion)
    return new_rabattaktion