from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import OperationalError
from sqlmodel import select

# from ..dependencies import get_token_header

from ..dependencies import require_admin
from ..models import Mwst, MwstPublic, MwstCreate, MwstUpdate, Produktgruppe
from ..session import SessionDep


router = APIRouter(
    prefix="/mwst",
    tags=["mwst"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_mwsts(
    session: SessionDep,
    search_string: str = "",
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Mwst]:
    selection = select(Mwst)
    if search_string:
        # Split the search string into space separated terms
        search_terms = search_string.split()
        # Each search term must be present in one of the searchable columns
        for (term) in search_terms:
            selection = selection.where(
                Mwst.dsfinvk_ust_beschr.contains(term) |
                Mwst.dsfinvk_ust_schluessel.contains(term) |
                Mwst.mwst_satz.contains(term)
            )
    mwsts = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Mwst.mwst_satz)).all()
    return mwsts


@router.get("/{mwst_id}")
def read_single_mwst(mwst_id: int, session: SessionDep) -> Mwst:
    mwst = session.get(Mwst, mwst_id)
    if not mwst:
        raise HTTPException(status_code=404, detail="Mwst not found")
    return mwst


@router.post("/", response_model=MwstPublic, dependencies=[Depends(require_admin)])
def create_mwst(mwst: MwstCreate, session: SessionDep):
    # Check if a rate with this mwst_satz already exists
    existing = session.exec(
        select(Mwst).where(Mwst.mwst_satz == mwst.mwst_satz)).first()
    if existing:
        raise HTTPException(status_code=400, detail="MwSt rate already exists")

    new_mwst = Mwst.model_validate(mwst)
    new_mwst.mwst_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    session.add(new_mwst)
    session.commit()
    session.refresh(new_mwst)
    return new_mwst


@router.put("/{mwst_id}", response_model=MwstPublic, dependencies=[Depends(require_admin)])
def replace_mwst(mwst_id: int, mwst: MwstUpdate, session: SessionDep):
    return update_mwst(mwst_id, mwst, session)


@router.patch("/{mwst_id}", response_model=MwstPublic, dependencies=[Depends(require_admin)])
def update_mwst(mwst_id: int, mwst: MwstUpdate, session: SessionDep):
    old_mwst = session.get(Mwst, mwst_id)
    if not old_mwst:
        raise HTTPException(status_code=404, detail="Mwst not found")

    mwst_data = mwst.model_dump(exclude_unset=True)
    if "mwst_satz" in mwst_data:
        existing = session.exec(
            select(Mwst).where(Mwst.mwst_satz == mwst_data["mwst_satz"],
                               Mwst.mwst_id != mwst_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="MwSt rate already exists")
    for key, value in mwst_data.items():
        setattr(old_mwst, key, value)
    session.add(old_mwst)
    session.commit()
    session.refresh(old_mwst)
    return old_mwst


@router.delete("/{mwst_id}", dependencies=[Depends(require_admin)])
def delete_mwst(mwst_id: int, session: SessionDep):
    mwst = session.get(Mwst, mwst_id)
    if not mwst:
        raise HTTPException(status_code=404, detail="Mwst not found")
    n_produktgruppen = len(session.exec(
        select(Produktgruppe).where(Produktgruppe.mwst_id == mwst_id)).all())
    if n_produktgruppen:
        raise HTTPException(
            status_code=409,
            detail=f"MwSt rate is used by {n_produktgruppen} produktgruppe(s) and cannot be deleted")
    session.delete(mwst)
    try:
        session.commit()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Database user lacks DELETE permission on table 'mwst' (run the API as kassenadmin)")
    return {"message": "MwSt deleted"}
