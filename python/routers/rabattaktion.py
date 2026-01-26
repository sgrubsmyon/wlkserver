from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Rabattaktion, RabattaktionPublic, RabattaktionBase #, RabattaktionUpdate
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
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[RabattaktionPublic]:
    selection = select(Rabattaktion)
    rabattaktionen = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Rabattaktion.von)).all()
    return rabattaktionen