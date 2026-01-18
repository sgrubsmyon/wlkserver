from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Pfand
from ..session import SessionDep


router = APIRouter(
    prefix="/pfand",
    tags=["pfand"],
    # dependencies=[Depends(get_token_header)],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_pfands(
    session: SessionDep,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[Pfand]:
    selection = select(Pfand)
    pfands = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Pfand.pfand_id)).all()
    return pfands


@router.get("/{pfand_id}")
def read_single_pfand(pfand_id: int, session: SessionDep) -> Pfand:
    pfand = session.get(Pfand, pfand_id)
    if not pfand:
        raise HTTPException(status_code=404, detail="Pfand not found")
    return pfand