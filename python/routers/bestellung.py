from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Bestellung,
    BestellungPublic,
    BestellungCreate,
    BestellungUpdate,
    BestellungDetails,
    BestellungDetailsPublic,
    BestellungDetailsCreate,
    Artikel,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

router = APIRouter(
    prefix="/bestellung",
    tags=["bestellung"],
    responses={404: {"description": "Not found"}},
)


def _validated_details(session: SessionDep, details: list[BestellungDetailsCreate]):
    """Check positions are unique and articles exist before touching the DB."""
    positions = [d.position for d in details]
    if len(positions) != len(set(positions)):
        raise HTTPException(status_code=400, detail="Duplicate position in details")
    for d in details:
        if not session.get(Artikel, d.artikel_id):
            raise HTTPException(status_code=400, detail=f"Artikel {d.artikel_id} not found")


def _add_details(session: SessionDep, bestell_nr: int, typ: str, details: list[BestellungDetailsCreate]):
    for d in details:
        row = BestellungDetails(
            bestell_nr=bestell_nr,
            typ=typ,
            position=d.position,
            artikel_id=d.artikel_id,
            stueckzahl=d.stueckzahl,
        )
        session.add(row)


def _delete_details(session: SessionDep, bestell_nr: int, typ: str):
    rows = session.exec(
        select(BestellungDetails).where(BestellungDetails.bestell_nr == bestell_nr, BestellungDetails.typ == typ)
    ).all()
    for row in rows:
        session.delete(row)


@router.get("/")
def read_bestellungen(
    session: SessionDep,
    since: Optional[str] = None,
    until: Optional[str] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[BestellungPublic]:
    selection = select(Bestellung)
    if since:
        since_dt = datetime.fromisoformat(since)
        if since_dt.tzinfo is None:
            since_dt = since_dt.replace(tzinfo=timezone.utc)
        selection = selection.where(Bestellung.bestell_datum >= since_dt)
    if until:
        until_dt = datetime.fromisoformat(until)
        if until_dt.tzinfo is None:
            until_dt = until_dt.replace(tzinfo=timezone.utc)
        selection = selection.where(Bestellung.bestell_datum <= until_dt)
    rows = session.exec(
        selection.offset(offset).limit(limit).order_by(Bestellung.bestell_nr)
    ).all()
    return [BestellungPublic.model_validate(r) for r in rows]


@router.get("/{bestell_nr}")
def read_single_bestellung(bestell_nr: int, session: SessionDep) -> dict:
    b = session.get(Bestellung, bestell_nr)
    if not b:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    details = session.exec(
        select(BestellungDetails)
        .where(BestellungDetails.bestell_nr == bestell_nr, BestellungDetails.typ == b.typ)
        .order_by(BestellungDetails.position)
    ).all()
    obj = BestellungPublic.model_validate(b).model_dump()
    obj["details"] = [BestellungDetailsPublic.model_validate(d).model_dump() for d in details]
    return obj


@router.post("/", response_model=BestellungPublic)
def create_bestellung(bestellung: BestellungCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    user_id = None
    if credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        tok = decode_token(credentials.credentials)
        if tok:
            user_id = tok.get("user_id")
    if bestellung.details:
        _validated_details(session, bestellung.details)
    now = datetime.now(timezone.utc)
    new_b = Bestellung(
        typ=bestellung.typ if bestellung.typ is not None else "LM",
        bestell_datum=bestellung.bestell_datum if bestellung.bestell_datum is not None else now,
        jahr=bestellung.jahr if bestellung.jahr is not None else now.year,
        kw=bestellung.kw if bestellung.kw is not None else 1,
        user_id=user_id,
    )
    new_b.bestell_nr = None
    session.add(new_b)
    session.commit()
    session.refresh(new_b)
    if bestellung.details:
        _add_details(session, new_b.bestell_nr, new_b.typ, bestellung.details)
        session.commit()
    return BestellungPublic.model_validate(new_b)


@router.patch("/{bestell_nr}", response_model=BestellungPublic)
def update_bestellung(bestell_nr: int, bestellung: BestellungUpdate, session: SessionDep, _user=Depends(require_user)):
    old = session.get(Bestellung, bestell_nr)
    if not old:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    data = bestellung.model_dump(exclude_unset=True)
    details = bestellung.details
    data.pop("details", None)
    if details is not None:
        _validated_details(session, details)
    old_typ = old.typ
    for key, value in data.items():
        setattr(old, key, value)
    session.add(old)
    if details is not None:
        _delete_details(session, bestell_nr, old_typ)
        _add_details(session, bestell_nr, old.typ, details)
    elif old.typ != old_typ:
        # typ is part of the detail primary key, keep the children consistent
        rows = session.exec(
            select(BestellungDetails).where(BestellungDetails.bestell_nr == bestell_nr, BestellungDetails.typ == old_typ)
        ).all()
        for row in rows:
            row.typ = old.typ
            session.add(row)
    session.commit()
    session.refresh(old)
    return BestellungPublic.model_validate(old)


@router.delete("/{bestell_nr}")
def delete_bestellung(bestell_nr: int, session: SessionDep, _user=Depends(require_user)):
    b = session.get(Bestellung, bestell_nr)
    if not b:
        raise HTTPException(status_code=404, detail="Bestellung not found")
    _delete_details(session, bestell_nr, b.typ)
    session.delete(b)
    session.commit()
    return {"message": "Bestellung deleted"}


# Aliases
read_bestellung = read_bestellungen
create_bestellung_entry = create_bestellung
