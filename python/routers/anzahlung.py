from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Anzahlung,
    AnzahlungPublic,
    AnzahlungCreate,
    AnzahlungDetails,
    AnzahlungDetailsPublic,
    AnzahlungDetailsCreate,
    AnzahlungAufloesen,
    Verkauf,
    VerkaufDetails,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

router = APIRouter(
    prefix="/anzahlung",
    tags=["anzahlung"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_anzahlungen(
    session: SessionDep,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AnzahlungPublic]:
    rows = session.exec(
        select(Anzahlung).offset(offset).limit(limit).order_by(Anzahlung.anzahlung_id)
    ).all()
    return [AnzahlungPublic.model_validate(a) for a in rows]


@router.get("/offen")
def read_offene_anzahlungen(session: SessionDep) -> list[AnzahlungPublic]:
    # Append-only table: a resolution adds a second row for the same
    # anzahlung_in_rech_nr, so an installment is open while it has no
    # resolution entry (Java: GROUP BY anzahlung_in_rech_nr HAVING COUNT(*) = 1).
    resolved = select(Anzahlung.anzahlung_in_rech_nr).where(
        Anzahlung.aufloesung_in_rech_nr.is_not(None)
    )
    rows = session.exec(
        select(Anzahlung).where(
            Anzahlung.aufloesung_in_rech_nr.is_(None),
            ~Anzahlung.anzahlung_in_rech_nr.in_(resolved),
        ).order_by(Anzahlung.anzahlung_id)
    ).all()
    return [AnzahlungPublic.model_validate(a) for a in rows]


@router.get("/aufgeloest")
def read_aufgeloeste_anzahlungen(session: SessionDep) -> list[AnzahlungPublic]:
    rows = session.exec(
        select(Anzahlung).where(Anzahlung.aufloesung_in_rech_nr.is_not(None))
    ).all()
    return [AnzahlungPublic.model_validate(a) for a in rows]


@router.get("/{anzahlung_id}")
def read_single_anzahlung(anzahlung_id: int, session: SessionDep) -> AnzahlungPublic:
    a = session.get(Anzahlung, anzahlung_id)
    if not a:
        raise HTTPException(status_code=404, detail="Anzahlung not found")
    return AnzahlungPublic.model_validate(a)


@router.post("/", response_model=AnzahlungPublic)
def create_anzahlung(anzahlung: AnzahlungCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    user_id = getattr(anzahlung, "user_id", None)
    if user_id is None and credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        p = decode_token(credentials.credentials)
        if p:
            user_id = p.get("user_id")
    # validate sales
    v = session.get(Verkauf, anzahlung.anzahlung_in_rech_nr)
    if not v:
        raise HTTPException(status_code=400, detail="Verkauf (anzahlung_in_rech_nr) not found")
    if anzahlung.aufloesung_in_rech_nr is not None:
        v2 = session.get(Verkauf, anzahlung.aufloesung_in_rech_nr)
        if not v2:
            raise HTTPException(status_code=400, detail="Verkauf (aufloesung_in_rech_nr) not found")

    new_a = Anzahlung(
        anzahlung_in_rech_nr=anzahlung.anzahlung_in_rech_nr,
        aufloesung_in_rech_nr=anzahlung.aufloesung_in_rech_nr,
        datum=anzahlung.datum if anzahlung.datum is not None else datetime.now(timezone.utc),
        user_id=user_id,
    )
    new_a.anzahlung_id = None
    session.add(new_a)
    session.commit()
    session.refresh(new_a)

    for d in (anzahlung.details or []):
        dd = AnzahlungDetails(
            rechnungs_nr=d.rechnungs_nr if d.rechnungs_nr is not None else anzahlung.anzahlung_in_rech_nr,
            vd_id=d.vd_id,
            ges_preis=d.ges_preis,
        )
        dd.ad_id = None
        session.add(dd)
    if anzahlung.details:
        session.commit()

    return AnzahlungPublic.model_validate(new_a)


@router.post("/{anzahlung_id}/aufloesen", response_model=AnzahlungPublic)
def aufloesen_anzahlung(
    anzahlung_id: int,
    session: SessionDep,
    payload: Optional[AnzahlungAufloesen] = None,
    aufloesung_in_rech_nr: Optional[int] = Query(default=None),
    datum: Optional[datetime] = Query(default=None),
    _user=Depends(require_user),
):
    original = session.get(Anzahlung, anzahlung_id)
    if not original:
        raise HTTPException(status_code=404, detail="Anzahlung not found")

    auf_nr = aufloesung_in_rech_nr
    dt = datum
    if payload is not None:
        if auf_nr is None:
            auf_nr = payload.aufloesung_in_rech_nr
        if dt is None:
            dt = payload.datum

    if auf_nr is None:
        raise HTTPException(status_code=400, detail="aufloesung_in_rech_nr is required")
    v = session.get(Verkauf, auf_nr)
    if not v:
        raise HTTPException(status_code=400, detail="Verkauf not found")

    new_a = Anzahlung(
        datum=dt if dt is not None else datetime.now(timezone.utc),
        anzahlung_in_rech_nr=original.anzahlung_in_rech_nr,
        aufloesung_in_rech_nr=auf_nr,
    )
    new_a.anzahlung_id = None
    session.add(new_a)
    session.commit()
    session.refresh(new_a)
    return AnzahlungPublic.model_validate(new_a)


# Details endpoints (optional convenience)
@router.get("/{anzahlung_id}/details", response_model=list[AnzahlungDetailsPublic])
def read_anzahlung_details(anzahlung_id: int, session: SessionDep):
    a = session.get(Anzahlung, anzahlung_id)
    if not a:
        raise HTTPException(status_code=404, detail="Anzahlung not found")
    rows = session.exec(
        select(AnzahlungDetails).where(AnzahlungDetails.rechnungs_nr == a.anzahlung_in_rech_nr)
    ).all()
    return [AnzahlungDetailsPublic.model_validate(r) for r in rows]


@router.post("/details", response_model=AnzahlungDetailsPublic)
def create_anzahlung_detail(detail: AnzahlungDetailsCreate, session: SessionDep):
    v = session.get(Verkauf, detail.rechnungs_nr)
    if not v:
        raise HTTPException(status_code=400, detail="Verkauf not found")
    vd = session.get(VerkaufDetails, detail.vd_id)
    if not vd:
        raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    new_d = AnzahlungDetails.model_validate(detail)
    new_d.ad_id = None
    session.add(new_d)
    session.commit()
    session.refresh(new_d)
    return AnzahlungDetailsPublic.model_validate(new_d)


# Aliases
read_anzahlung = read_anzahlungen
create_anzahlung_entry = create_anzahlung
resolve_anzahlung = aufloesen_anzahlung
aufloesen = aufloesen_anzahlung
read_offen = read_offene_anzahlungen
read_offene = read_offene_anzahlungen
read_aufgeloest = read_aufgeloeste_anzahlungen
read_aufgeloeste = read_aufgeloeste_anzahlungen
resolve_anzahlung = aufloesen_anzahlung