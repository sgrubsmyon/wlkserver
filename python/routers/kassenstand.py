from datetime import datetime, timezone
from decimal import Decimal
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    Kassenstand,
    Verkauf,
)
from ..schemas import (
    KassenstandCreate,
    KassenstandPublic,
    ZaehlprotokollDetailsCreate,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends
from ..utils.pagination import paginate

router = APIRouter(
    prefix="/kassenstand",
    tags=["kassenstand"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_kassenstaende(
    session: SessionDep,
    rechnungen: bool = False,
    von: Optional[datetime] = None,
    bis: Optional[datetime] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[KassenstandPublic]:
    selection = select(Kassenstand)
    if not rechnungen:
        selection = selection.where(Kassenstand.manuell == True)
    if von is not None:
        selection = selection.where(Kassenstand.buchungsdatum >= von)
    if bis is not None:
        selection = selection.where(Kassenstand.buchungsdatum <= bis)
    kassenstaende = paginate(session, selection, offset, limit, Kassenstand.buchungsdatum.desc())
    return [KassenstandPublic.model_validate(k) for k in kassenstaende]


@router.get("/aktuell")
def read_kassenstand_aktuell(session: SessionDep) -> KassenstandPublic | None:
    ks = session.exec(
        select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())
    ).first()
    if not ks:
        return None
    return KassenstandPublic.model_validate(ks)


@router.get("/{kassenstand_id}")
def read_single_kassenstand(kassenstand_id: int, session: SessionDep) -> KassenstandPublic:
    ks = session.get(Kassenstand, kassenstand_id)
    if not ks:
        raise HTTPException(status_code=404, detail="Kassenstand not found")
    return KassenstandPublic.model_validate(ks)


@router.post("/zuruecksetzen/vorschau")
def read_kassenstand_reset_suggestion(details: list[ZaehlprotokollDetailsCreate]) -> dict:
    """Suggestion for bringing the counted drawer back to its target stock.

    Read-only: takes the count in the same shape as the `zaehlprotokoll` detail
    rows of `POST /abrechnung/tag`. The reset itself is the manual
    `POST /kassenstand/` entry, exactly like the Java dialogue's
    `insertIntoKassenstand`.
    """
    from ..business.cash_register import kassenstand_reset_suggestion

    counts: dict[Decimal, int] = {}
    for d in details:
        key = Decimal(str(d.einheit))
        counts[key] = counts.get(key, 0) + d.anzahl
    # money as JSON numbers, like the other endpoints
    return {key: float(value) for key, value in kassenstand_reset_suggestion(counts).items()}


@router.post("/", response_model=KassenstandPublic)
def create_kassenstand(kassenstand: KassenstandCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    user_id = kassenstand.user_id if hasattr(kassenstand, "user_id") else None
    if user_id is None and credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        p = decode_token(credentials.credentials)
        if p:
            user_id = p.get("user_id")
    if kassenstand.rechnungs_nr is not None:
        v = session.get(Verkauf, kassenstand.rechnungs_nr)
        if not v:
            raise HTTPException(status_code=400, detail="Verkauf not found")
    from ..business.cash_register import get_current_balance, validate_balance_change, KASSENSTAND_LOCK
    with KASSENSTAND_LOCK:
        validate_balance_change(
            get_current_balance(session),
            kassenstand.neuer_kassenstand,
            kassenstand.entnahme,
        )
        new_ks = Kassenstand(
            buchungsdatum=kassenstand.buchungsdatum if kassenstand.buchungsdatum is not None else datetime.now(timezone.utc),
            neuer_kassenstand=kassenstand.neuer_kassenstand,
            manuell=kassenstand.manuell,
            entnahme=kassenstand.entnahme,
            rechnungs_nr=kassenstand.rechnungs_nr,
            kommentar=kassenstand.kommentar,
            user_id=user_id,
        )
        new_ks.kassenstand_id = None
        session.add(new_ks)
        session.commit()
        session.refresh(new_ks)
    return KassenstandPublic.model_validate(new_ks)


# Aliases for compatibility with possible test naming
read_kassenstands = read_kassenstaende
read_kassenstand = read_kassenstaende
read_single_kassenstand_by_id = read_single_kassenstand
create_kassenstand_entry = create_kassenstand
read_aktuell = read_kassenstand_aktuell
read_kassenstand_aktuell_alias = read_kassenstand_aktuell
get_aktuell = read_kassenstand_aktuell
get_kassenstand_aktuell = read_kassenstand_aktuell
read_aktuell_kassenstand = read_kassenstand_aktuell