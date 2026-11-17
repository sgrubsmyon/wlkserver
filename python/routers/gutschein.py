"""Vouchers (Gutschein): list, read, issue and redeem.

The `gutschein` table is append-only: issuance writes the start value, each
redemption appends a row with the reduced balance, so the current balance is the
minimum `restbetrag` of a voucher's rows (see `business.voucher_logic`).
"""
from datetime import datetime, timezone
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select, func

from ..models import (
    Gutschein,
    VerkaufDetails,
)
from ..schemas import (
    GutscheinPublic,
    GutscheinCreate,
    GutscheinEinloesen,
)
from ..session import SessionDep
from ..dependencies import require_user
from fastapi import Depends
from ..utils.pagination import paginate

router = APIRouter(
    prefix="/gutschein",
    tags=["gutschein"],
    responses={404: {"description": "Not found"}},
)


def _latest_ids_per_nr(session: SessionDep):
    """Map `gutschein_nr` to its newest row's `gutschein_id`."""
    # latest gutschein_id per gutschein_nr
    sub = (
        select(Gutschein.gutschein_nr, func.max(Gutschein.gutschein_id).label("max_id"))
        .group_by(Gutschein.gutschein_nr)
    )
    return {row[0]: row[1] for row in session.exec(sub).all()}


@router.get("/")
def read_gutscheine(
    session: SessionDep,
    gutschein_nr: Optional[int] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[GutscheinPublic]:
    """List voucher rows with pagination, optionally filtered by voucher number."""
    selection = select(Gutschein)
    if gutschein_nr is not None:
        selection = selection.where(Gutschein.gutschein_nr == gutschein_nr)
    gutscheine = paginate(session, selection, offset, limit, Gutschein.gutschein_id)
    return [GutscheinPublic.model_validate(g) for g in gutscheine]


@router.get("/ausstehend")
def read_ausstehende_gutscheine(session: SessionDep) -> list[GutscheinPublic]:
    """Vouchers that still carry a balance, with their original start value."""
    from ..business.voucher_logic import voucher_start_value

    latest = _latest_ids_per_nr(session)
    if not latest:
        return []
    ids = list(latest.values())
    rows = session.exec(
        select(Gutschein).where(Gutschein.gutschein_id.in_(ids), Gutschein.restbetrag > 0)
    ).all()
    result = []
    for g in rows:
        obj = GutscheinPublic.model_validate(g)
        obj.restbetrag_anfang = float(voucher_start_value(session, g.gutschein_nr))
        result.append(obj)
    return result


@router.get("/eingeloest")
def read_eingeloeste_gutscheine(session: SessionDep) -> list[GutscheinPublic]:
    """Vouchers whose remaining balance is zero (fully redeemed)."""
    latest = _latest_ids_per_nr(session)
    if not latest:
        return []
    ids = list(latest.values())
    rows = session.exec(
        select(Gutschein).where(Gutschein.gutschein_id.in_(ids), Gutschein.restbetrag <= 0)
    ).all()
    return [GutscheinPublic.model_validate(g) for g in rows]


@router.get("/{gutschein_id}")
def read_single_gutschein(gutschein_id: int, session: SessionDep) -> GutscheinPublic:
    """Read one voucher row by id; 404 when it does not exist."""
    g = session.get(Gutschein, gutschein_id)
    if not g:
        raise HTTPException(status_code=404, detail="Gutschein not found")
    return GutscheinPublic.model_validate(g)


@router.post("/", response_model=GutscheinPublic)
def create_gutschein(gutschein: GutscheinCreate, session: SessionDep, _user=Depends(require_user)):
    """Issue a voucher: allocate the next voucher number and append the start row.

    The number is drawn under `VOUCHER_LOCK` so parallel issuances cannot collide.
    Referenced sale positions (`gutschein_in_vd_id`, `einloesung_in_vd_id`) must
    exist, otherwise the request fails with 400.
    """
    from ..business.voucher_logic import VOUCHER_LOCK, next_gutschein_nr

    user_id = getattr(gutschein, "user_id", None) or getattr(_user, "user_id", None)
    if gutschein.gutschein_in_vd_id is not None:
        vd = session.get(VerkaufDetails, gutschein.gutschein_in_vd_id)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    if gutschein.einloesung_in_vd_id is not None:
        vd = session.get(VerkaufDetails, gutschein.einloesung_in_vd_id)
        if not vd:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")
    with VOUCHER_LOCK:
        new_g = Gutschein(
            gutschein_nr=next_gutschein_nr(session, lock=False),
            datum=gutschein.datum if gutschein.datum is not None else datetime.now(timezone.utc),
            gutschein_in_vd_id=gutschein.gutschein_in_vd_id,
            einloesung_in_vd_id=gutschein.einloesung_in_vd_id,
            restbetrag=gutschein.restbetrag,
            user_id=user_id,
        )
        new_g.gutschein_id = None
        session.add(new_g)
        session.commit()
        session.refresh(new_g)
    return GutscheinPublic.model_validate(new_g)


@router.post("/{gutschein_id}/einloesen", response_model=GutscheinPublic)
def einloesen_gutschein(
    gutschein_id: int,
    session: SessionDep,
    payload: Optional[GutscheinEinloesen] = None,
    einloesung_in_vd_id: Optional[int] = Query(default=None),
    restbetrag: Optional[float] = Query(default=None),
    betrag: Optional[float] = Query(default=None),
    gutschein_in_vd_id: Optional[int] = Query(default=None),
    _user=Depends(require_user),
):
    """Redeem (part of) a voucher and return the new balance row.

    The amount comes from the linked sale position `einloesung_in_vd_id`, the
    explicit `betrag` or the requested new `restbetrag`, which may be sent either
    in the body or as query parameters. `redeem_voucher` rejects non-positive
    amounts, amounts above the balance and a sale position used twice.
    """
    from ..business.voucher_logic import redeem_voucher

    p = payload
    datum = None
    if p is not None:
        if einloesung_in_vd_id is None:
            einloesung_in_vd_id = p.einloesung_in_vd_id
        if gutschein_in_vd_id is None:
            gutschein_in_vd_id = p.gutschein_in_vd_id
        if restbetrag is None:
            restbetrag = p.restbetrag
        if betrag is None:
            betrag = p.betrag
        datum = p.datum

    new_g = redeem_voucher(
        session,
        gutschein_id,
        betrag=betrag,
        einloesung_in_vd_id=einloesung_in_vd_id,
        gutschein_in_vd_id=gutschein_in_vd_id,
        restbetrag=restbetrag,
        datum=datum,
        user_id=_user.user_id,
    )
    return GutscheinPublic.model_validate(new_g)


# Aliases
read_gutschein = read_gutscheine
read_single_gutschein_alias = read_single_gutschein
create_gutschein_entry = create_gutschein
redeem_gutschein = einloesen_gutschein
read_ausstehend = read_ausstehende_gutscheine
read_ausstehende = read_ausstehende_gutscheine
read_eingeloest = read_eingeloeste_gutscheine