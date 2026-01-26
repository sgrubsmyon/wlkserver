from typing import Annotated

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

# from ..dependencies import get_token_header

from ..models import Artikel, Pfand, PfandPublic
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
    wert: float | None = None,
    offset: int = 0, limit: Annotated[int, Query(le=100)] = 100
    ) -> list[PfandPublic]:
    selection = select(Pfand).join(Artikel)

    # Add a where clause if wert is provided
    if wert is not None:
        selection = selection.where(Artikel.vk_preis == wert)

    # Execute the query with offset and limit
    pfands = session.exec(
        selection.offset(offset).limit(limit)
            .order_by(Pfand.pfand_id)).all()
    
    # Prepare the response
    return_obj = []
    for pfand in pfands:
        obj = PfandPublic.model_validate(pfand, update={"wert": pfand.artikel.vk_preis})
        return_obj.append(obj)

    return return_obj


@router.get("/{pfand_id}")
def read_single_pfand(pfand_id: int, session: SessionDep) -> Pfand:
    pfand = session.get(Pfand, pfand_id)
    if not pfand:
        raise HTTPException(status_code=404, detail="Pfand not found")
    return pfand