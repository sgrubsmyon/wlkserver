from datetime import datetime

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Produktgruppe, ProduktgruppePublic, ProduktgruppeCreate, ProduktgruppeUpdate
from ..session import SessionDep


router = APIRouter(
    prefix="/produktgruppe",
    tags=["produktgruppe"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_produktgruppen(
    session: SessionDep, aktiv_only: bool = True,
    search_string: str = "",
    toplevel_id: int = 0, sub_id: int = 0, subsub_id: int = 0,
    produktgruppen_name: str = "",
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Produktgruppe]:
    selection = select(Produktgruppe)
    if aktiv_only:
        selection = selection.where(Produktgruppe.aktiv == True)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Produktgruppe.produktgruppen_name.contains(term)
            )
    elif toplevel_id and sub_id and subsub_id:
        selection = selection.where(Produktgruppe.toplevel_id == toplevel_id).where(Produktgruppe.sub_id == sub_id).where(Produktgruppe.subsub_id == subsub_id)
    elif toplevel_id and sub_id:
        selection = selection.where(Produktgruppe.toplevel_id == toplevel_id).where(Produktgruppe.sub_id == sub_id)
    elif toplevel_id:
        selection = selection.where(Produktgruppe.toplevel_id == toplevel_id)
    elif produktgruppen_name:
        selection = selection.where(Produktgruppe.produktgruppen_name == produktgruppen_name)
    produktgruppen = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Produktgruppe.toplevel_id, Produktgruppe.sub_id, Produktgruppe.subsub_id)).all()
    return produktgruppen


@router.get("/{produktgruppen_id}")
def read_single_produktgruppe(produktgruppen_id: int, session: SessionDep) -> Produktgruppe:
    produktgruppe = session.get(Produktgruppe, produktgruppen_id)
    if not produktgruppe:
        raise HTTPException(status_code=404, detail="Produktgruppe not found")
    return produktgruppe


@router.post("/", response_model=ProduktgruppePublic)
def create_produktgruppe(produktgruppe: ProduktgruppeCreate, session: SessionDep):
    new_produktgruppe = Produktgruppe.model_validate(produktgruppe)

    # Check if this product group already exists
    produktgruppe_list = read_produktgruppen(
        session,
        aktiv_only=True,
        produktgruppen_name=new_produktgruppe.produktgruppen_name
    )
    if len(produktgruppe_list) > 0:
        raise HTTPException(status_code=400, detail="Produktgruppe already exists")

    new_produktgruppe.produktgruppen_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    new_produktgruppe.aktiv = True
    new_produktgruppe.n_artikel = 0
    new_produktgruppe.n_artikel_rekursiv = 0

    session.add(new_produktgruppe)
    session.commit()
    session.refresh(new_produktgruppe)
    return new_produktgruppe


def delete_produktgruppe_intern(produktgruppen_id: int, session: SessionDep):
    produktgruppe = session.get(Produktgruppe, produktgruppen_id)
    if not produktgruppe:
        raise HTTPException(status_code=404, detail="Produktgruppe not found")
    produktgruppe.aktiv = False
    session.add(produktgruppe)
    session.commit()
    session.refresh(produktgruppe) # needed, or returned produktgruppe will be empty
    return produktgruppe


@router.delete("/{produktgruppen_id}")
def delete_produktgruppe(produktgruppen_id: int, session: SessionDep):
    delete_produktgruppe_intern(produktgruppen_id, session)
    return {"message": "Produktgruppe deactivated"}


@router.patch("/{produktgruppen_id}", response_model=ProduktgruppePublic)
def update_produktgruppe(produktgruppen_id: int, produktgruppe: ProduktgruppeUpdate, session: SessionDep):
    # This would be the code if we would want to really update a product group
    #
    # old_produktgruppe = session.get(Produktgruppe, produktgruppen_id)
    # if not old_produktgruppe:
    #     raise HTTPException(status_code=404, detail="Produktgruppe not found")
    # produktgruppe_data = produktgruppe.model_dump(exclude_unset=True)
    # for key, value in produktgruppe_data.items():
    #     setattr(old_produktgruppe, key, value)
    # session.add(old_produktgruppe)
    # session.commit()
    # session.refresh(old_produktgruppe)
    # return q
    #
    # Instead we just deactivate the article and create a new one

    old_produktgruppe = delete_produktgruppe_intern(produktgruppen_id, session)
    old_produktgruppe_data = old_produktgruppe.model_dump(exclude_unset=False)
    produktgruppe_data = produktgruppe.model_dump(exclude_unset=True)
    for key, value in produktgruppe_data.items():
        old_produktgruppe_data[key] = value
    new_produktgruppe = create_produktgruppe(old_produktgruppe_data, session)

    return new_produktgruppe
