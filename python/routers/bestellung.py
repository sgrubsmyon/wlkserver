from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Bestellung,
    BestellungPublic,
    BestellungCreate,
    BestellungUpdate,
    Artikel,
)
from ..session import SessionDep

router = APIRouter(
    prefix="/bestellung",
    tags=["bestellung"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_bestellungen(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[BestellungPublic]:
    rows = session.exec(
        select(Bestellung).offset(offset).limit(limit).order_by(Bestellung.bestell_nr)
    ).all()
    return [BestellungPublic.model_validate(r) for r in rows]


@router.get("/{bestell_nr}")
def read_single_bestellung(bestell_nr: int, session: SessionDep) -> BestellungPublic:
    b = session.get(Bestellung, bestell_nr)
    if not b:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    return BestellungPublic.model_validate(b)


@router.post("/", response_model=BestellungPublic)
def create_bestellung(bestellung: BestellungCreate, session: SessionDep):
    now = datetime.now(timezone.utc)
    new_b = Bestellung(
        typ=bestellung.typ if bestellung.typ is not None else "",
        bestell_datum=bestellung.bestell_datum if bestellung.bestell_datum is not None else now,
        jahr=bestellung.jahr if bestellung.jahr is not None else now.year,
        kw=bestellung.kw if bestellung.kw is not None else 1,
    )
    new_b.bestell_nr = None
    session.add(new_b)
    session.commit()
    session.refresh(new_b)
    return BestellungPublic.model_validate(new_b)


@router.patch("/{bestell_nr}", response_model=BestellungPublic)
def update_bestellung(bestell_nr: int, bestellung: BestellungUpdate, session: SessionDep):
    old = session.get(Bestellung, bestell_nr)
    if not old:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    data = bestellung.model_dump(exclude_unset=True)
    for key, value in data.items():
        setattr(old, key, value)
    session.add(old)
    session.commit()
    session.refresh(old)
    return BestellungPublic.model_validate(old)


@router.delete("/{bestell_nr}")
def delete_bestellung(bestell_nr: int, session: SessionDep):
    b = session.get(Bestellung, bestell_nr)
    if not b:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    session.delete(b)
    session.commit()
    return {"message": "Bestellung deleted"}


# Aliases
read_bestellung = read_bestellungen
create_bestellung_entry = create_bestellung