from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.exc import OperationalError
from sqlmodel import select

# from ..dependencies import get_token_header

from ..dependencies import require_admin
from ..models import Artikel, Pfand, PfandPublic, PfandCreate, PfandUpdate, Produktgruppe
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
def read_single_pfand(pfand_id: int, session: SessionDep) -> PfandPublic:
    pfand = session.get(Pfand, pfand_id)
    if not pfand:
        raise HTTPException(status_code=404, detail="Pfand not found")
    pfand = PfandPublic.model_validate(pfand, update={"wert": pfand.artikel.vk_preis})
    return pfand


@router.post("/", response_model=PfandPublic, dependencies=[Depends(require_admin)])
def create_pfand(pfand: PfandCreate, session: SessionDep):
    artikel = session.get(Artikel, pfand.artikel_id)
    if not artikel:
        raise HTTPException(status_code=400, detail="Artikel not found")
    existing = session.exec(
        select(Pfand).where(Pfand.artikel_id == pfand.artikel_id)).first()
    if existing:
        raise HTTPException(status_code=400, detail="Pfand for this article already exists")

    new_pfand = Pfand.model_validate(pfand)
    new_pfand.pfand_id = None # whatever has been set here, unset it so that the ID will be set by the DB
    session.add(new_pfand)
    session.commit()
    session.refresh(new_pfand)
    return PfandPublic.model_validate(new_pfand, update={"wert": new_pfand.artikel.vk_preis})


@router.patch("/{pfand_id}", response_model=PfandPublic, dependencies=[Depends(require_admin)])
def update_pfand(pfand_id: int, pfand: PfandUpdate, session: SessionDep):
    old_pfand = session.get(Pfand, pfand_id)
    if not old_pfand:
        raise HTTPException(status_code=404, detail="Pfand not found")

    pfand_data = pfand.model_dump(exclude_unset=True)
    if "artikel_id" in pfand_data:
        artikel = session.get(Artikel, pfand_data["artikel_id"])
        if not artikel:
            raise HTTPException(status_code=400, detail="Artikel not found")
        existing = session.exec(
            select(Pfand).where(Pfand.artikel_id == pfand_data["artikel_id"],
                                Pfand.pfand_id != pfand_id)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Pfand for this article already exists")
    for key, value in pfand_data.items():
        setattr(old_pfand, key, value)
    session.add(old_pfand)
    session.commit()
    session.refresh(old_pfand)
    return PfandPublic.model_validate(old_pfand, update={"wert": old_pfand.artikel.vk_preis})


@router.delete("/{pfand_id}", dependencies=[Depends(require_admin)])
def delete_pfand(pfand_id: int, session: SessionDep):
    pfand = session.get(Pfand, pfand_id)
    if not pfand:
        raise HTTPException(status_code=404, detail="Pfand not found")
    n_produktgruppen = len(session.exec(
        select(Produktgruppe).where(Produktgruppe.pfand_id == pfand_id)).all())
    if n_produktgruppen:
        raise HTTPException(
            status_code=409,
            detail=f"Pfand is used by {n_produktgruppen} produktgruppe(s) and cannot be deleted")
    session.delete(pfand)
    try:
        session.commit()
    except OperationalError:
        raise HTTPException(
            status_code=503,
            detail="Database user lacks DELETE permission on table 'pfand' (run the API as kassenadmin)")
    return {"message": "Pfand deleted"}
