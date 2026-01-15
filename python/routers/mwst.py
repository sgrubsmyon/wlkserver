from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Mwst, MwstPublic, MwstBase
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