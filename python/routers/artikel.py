from datetime import datetime

from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Artikel, ArtikelPublic, ArtikelCreate, ArtikelUpdate
from ..session import SessionDep


router = APIRouter(
    prefix="/artikel",
    tags=["artikel"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_artikel(
    session: SessionDep, aktiv_only: bool = True,
    search_string: str = "",
    barcode: str = "", artikel_nr: str = "", artikel_name: str = "",
    lieferant_id: int = 0,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Artikel]:
    selection = select(Artikel)
    if aktiv_only:
        selection = selection.where(Artikel.aktiv == True)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Artikel.artikel_name.contains(term) |
                Artikel.kurzname.contains(term) |
                Artikel.artikel_nr.contains(term) |
                Artikel.herkunft.contains(term) |
                Artikel.barcode.contains(term)
            )
    elif barcode:
        selection = selection.where(Artikel.barcode == barcode)
    elif artikel_nr and lieferant_id:
        selection = selection.where(Artikel.artikel_nr == artikel_nr).where(Artikel.lieferant_id == lieferant_id)
    elif artikel_nr:
        selection = selection.where(Artikel.artikel_nr.contains(artikel_nr))
    elif lieferant_id:
        selection = selection.where(Artikel.lieferant_id == lieferant_id)
    elif artikel_name:
        selection = selection.where(Artikel.artikel_name.contains(artikel_name) | Artikel.kurzname.contains(artikel_name))
    artikel = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Artikel.artikel_name, Artikel.lieferant_id)).all()
    return artikel


@router.get("/{artikel_id}")
def read_single_artikel(artikel_id: int, session: SessionDep) -> Artikel:
    artikel = session.get(Artikel, artikel_id)
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    return artikel


@router.post("/", response_model=ArtikelPublic)
def create_artikel(artikel: ArtikelCreate, session: SessionDep):
    new_artikel = Artikel.model_validate(artikel)

    # Check if this article already exists (combination of lieferant_id and artikel_nr)
    # artikel = session.get(Artikel, (new_artikel.lieferant_id, new_artikel.artikel_nr))
    # if artikel:
    #     raise HTTPException(status_code=400, detail="Artikel already exists")
    artikel_list = read_artikel(
        session,
        aktiv_only=True,
        artikel_nr=new_artikel.artikel_nr, lieferant_id=new_artikel.lieferant_id
    )
    if len(artikel_list) > 0:
        raise HTTPException(status_code=400, detail="Artikel already exists")

    new_artikel.artikel_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    new_artikel.von = datetime.now()
    new_artikel.bis = None
    new_artikel.aktiv = True

    session.add(new_artikel)
    session.commit()
    session.refresh(new_artikel)
    return new_artikel


def delete_artikel_intern(artikel_id: int, session: SessionDep):
    artikel = session.get(Artikel, artikel_id)
    if not artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    if artikel.aktiv == False:
        raise HTTPException(status_code=400, detail="Artikel already deactivated")
    artikel.aktiv = False
    artikel.bis = datetime.now()
    session.add(artikel)
    session.commit()
    session.refresh(artikel) # needed, or returned article will be empty
    return artikel


@router.delete("/{artikel_id}")
def delete_artikel(artikel_id: int, session: SessionDep):
    delete_artikel_intern(artikel_id, session)
    return {"message": "Artikel deactivated"}


@router.patch("/{artikel_id}", response_model=ArtikelPublic)
def update_artikel(artikel_id: int, artikel: ArtikelUpdate, session: SessionDep):
    print("Update artikel:", artikel_id, artikel)

    old_artikel = session.get(Artikel, artikel_id)
    if not old_artikel:
        raise HTTPException(status_code=404, detail="Artikel not found")
    if old_artikel.aktiv == False:
        raise HTTPException(status_code=400, detail="Cannot update deactivated artikel")
    artikel_data = artikel.model_dump(exclude_unset=True)

    changed_keys = []
    for key, value in artikel_data.items():
        if value is not None:
            print(f"  {key} = {value}")
            old_value = old_artikel.__dict__.get(key, None)
            print(f"    old value: {old_value}")
            if old_value != value:
                print("    value of", key, "changed")
                changed_keys.append(key)

    # If there are no changes, just return the old article
    if len(changed_keys) == 0:
        # return old_artikel
        raise HTTPException(status_code=400, detail="No changes to artikel")

    # If the changes were only to fields that do not require a new article, just update the article
    non_versioned_fields = ['bestand', 'beliebtheit', 'lieferbar', 'sortiment']
    if all(key in non_versioned_fields for key in changed_keys):
        for key, value in artikel_data.items():
            setattr(old_artikel, key, value)
        session.add(old_artikel)
        session.commit()
        session.refresh(old_artikel)
        return old_artikel
    
    # Instead we just deactivate the article and create a new one
    old_artikel = delete_artikel_intern(artikel_id, session)
    old_artikel_data = old_artikel.model_dump(exclude_unset=False)
    for key, value in artikel_data.items():
        old_artikel_data[key] = value
    new_artikel = create_artikel(old_artikel_data, session)

    return new_artikel
