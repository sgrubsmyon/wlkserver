from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Lieferant, LieferantPublic, LieferantCreate, LieferantUpdate
from ..session import SessionDep


router = APIRouter(
    prefix="/lieferant",
    tags=["lieferant"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_lieferanten(
    session: SessionDep, aktiv_only: bool = True,
    search_string: str = "",
    lieferant_name: str = "",
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Lieferant]:
    selection = select(Lieferant)
    if aktiv_only:
        selection = selection.where(Lieferant.aktiv == True)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Lieferant.lieferant_name.contains(term)
            )
    elif lieferant_name:
        selection = selection.where(Lieferant.lieferant_name == lieferant_name)
    lieferanten = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Lieferant.lieferant_name)).all()
    return lieferanten


@router.get("/{lieferant_id}")
def read_single_lieferant(lieferant_id: int, session: SessionDep) -> Lieferant:
    lieferant = session.get(Lieferant, lieferant_id)
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant not found")
    return lieferant


@router.post("/", response_model=LieferantPublic)
def create_lieferant(lieferant: LieferantCreate, session: SessionDep):
    new_lieferant = Lieferant.model_validate(lieferant)

    # Check if this product group already exists
    lieferant_list = read_lieferanten(
        session,
        aktiv_only=True,
        lieferant_name=new_lieferant.lieferant_name
    )
    if len(lieferant_list) > 0:
        raise HTTPException(status_code=400, detail="Lieferant already exists")

    new_lieferant.lieferant_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    new_lieferant.aktiv = True
    new_lieferant.n_artikel = 0
    new_lieferant.n_artikel_rekursiv = 0

    session.add(new_lieferant)
    session.commit()
    session.refresh(new_lieferant)
    return new_lieferant


def delete_lieferant_intern(lieferant_id: int, session: SessionDep):
    lieferant = session.get(Lieferant, lieferant_id)
    if not lieferant:
        raise HTTPException(status_code=404, detail="Lieferant not found")
    lieferant.aktiv = False
    session.add(lieferant)
    session.commit()
    session.refresh(lieferant) # needed, or returned lieferant will be empty
    return lieferant


@router.delete("/{lieferant_id}")
def delete_lieferant(lieferant_id: int, session: SessionDep):
    delete_lieferant_intern(lieferant_id, session)
    return {"message": "Lieferant deactivated"}


@router.patch("/{lieferant_id}", response_model=LieferantPublic)
def update_lieferant(lieferant_id: int, lieferant: LieferantUpdate, session: SessionDep):
    # This would be the code if we would want to really update a product group
    #
    # old_lieferant = session.get(Lieferant, lieferant_id)
    # if not old_lieferant:
    #     raise HTTPException(status_code=404, detail="Lieferant not found")
    # lieferant_data = lieferant.model_dump(exclude_unset=True)
    # for key, value in lieferant_data.items():
    #     setattr(old_lieferant, key, value)
    # session.add(old_lieferant)
    # session.commit()
    # session.refresh(old_lieferant)
    # return q
    #
    # Instead we just deactivate the article and create a new one

    old_lieferant = delete_lieferant_intern(lieferant_id, session)
    old_lieferant_data = old_lieferant.model_dump(exclude_unset=False)
    lieferant_data = lieferant.model_dump(exclude_unset=True)
    for key, value in lieferant_data.items():
        old_lieferant_data[key] = value
    new_lieferant = create_lieferant(old_lieferant_data, session)

    return new_lieferant
