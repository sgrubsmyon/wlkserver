"""Voucher (Gutschein) balance and redemption logic.

The `gutschein` table is append-only: creating a voucher inserts a row with the
start value, each redemption inserts another row with the reduced balance. The
current balance is therefore the minimum `restbetrag` of all rows with the same
`gutschein_nr` (mirrors Java `GutscheinEinloesenDialog.queryForGutschein` and
`Kassieren.maybeInsertEinloesungIntoGutschein`).
"""
from __future__ import annotations

import threading
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlmodel import func, select

from ..models import Gutschein, GutscheinCounter, VerkaufDetails
from ..utils.validation import ensure_positive
from .vat_calculator import _to_decimal

CENT = Decimal("0.01")

# Balance is read-modify-write; serialize redemptions in this process and lock
# the voucher rows on databases that support SELECT ... FOR UPDATE (MariaDB).
VOUCHER_LOCK = threading.Lock()


def voucher_balance(session, gutschein_nr: int) -> Decimal:
    """Current remaining balance (minimum restbetrag over the voucher's rows)."""
    value = session.exec(
        select(func.min(Gutschein.restbetrag)).where(Gutschein.gutschein_nr == gutschein_nr)
    ).one()
    return (_to_decimal(value) or Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def voucher_start_value(session, gutschein_nr: int) -> Decimal:
    """Original value of the voucher (maximum restbetrag over its rows)."""
    value = session.exec(
        select(func.max(Gutschein.restbetrag)).where(Gutschein.gutschein_nr == gutschein_nr)
    ).one()
    return (_to_decimal(value) or Decimal("0")).quantize(CENT, rounding=ROUND_HALF_UP)


def next_gutschein_nr(session, lock: bool = True) -> int:
    """Next voucher number from the locked counter row, starting at 200.

    The single `gutschein_counter` row is read `FOR UPDATE`, so concurrent
    creators (several cash registers, the standalone endpoint) serialize on it
    until the caller commits; the number is then assigned exactly once. The
    counter is seeded from `MAX(gutschein_nr)` when missing (the production
    migration does this too, so the first call is not a race).

    `lock=False` is for callers already holding `VOUCHER_LOCK` across their
    commit (sale creation, standalone creation).
    """
    with (VOUCHER_LOCK if lock else nullcontext()):
        counter = session.exec(
            select(GutscheinCounter)
            .where(GutscheinCounter.id == 1)
            .with_for_update()
        ).first()
        if counter is None:
            highest = session.exec(select(func.max(Gutschein.gutschein_nr))).one()
            counter = GutscheinCounter(
                id=1, last_nr=int(highest) if highest is not None else 199
            )
            session.add(counter)
        counter.last_nr += 1
        session.flush()
        return counter.last_nr


def _creation_row(session, gutschein_nr: int) -> Gutschein | None:
    return session.exec(
        select(Gutschein)
        .where(
            Gutschein.gutschein_nr == gutschein_nr,
            Gutschein.einloesung_in_vd_id.is_(None),
            Gutschein.gutschein_in_vd_id.is_not(None),
        )
        .order_by(Gutschein.gutschein_id)
    ).first()


def redeem_voucher(
    session,
    gutschein_id: int,
    *,
    betrag=None,
    einloesung_in_vd_id=None,
    gutschein_in_vd_id=None,
    restbetrag=None,
    datum=None,
    user_id=None,
    commit=True,
    lock=True,
) -> Gutschein:
    """Redeem (part of) a voucher and append the new balance row.

    The redeemed amount is derived from, in order: the linked sale position
    (`einloesung_in_vd_id`, absolute price), the explicit `betrag`, or the
    requested new `restbetrag`. The amount must be positive and must not exceed
    the current balance; a sale position can only redeem once.

    `commit=False` keeps the new row in the caller's sale transaction; the
    caller must then hold `VOUCHER_LOCK` (pass `lock=False` only inside it)
    until its commit so the balance cannot be spent twice.
    """
    original = session.get(Gutschein, gutschein_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Gutschein not found")
    nr = original.gutschein_nr

    with (VOUCHER_LOCK if lock else nullcontext()):
        session.exec(
            select(Gutschein)
            .where(Gutschein.gutschein_nr == nr)
            .order_by(Gutschein.gutschein_id)
            .with_for_update()
        ).all()

        vd = None
        if einloesung_in_vd_id is not None:
            vd = session.get(VerkaufDetails, einloesung_in_vd_id)
            if vd is None:
                raise HTTPException(status_code=400, detail="VerkaufDetails not found")
            already = session.exec(
                select(Gutschein).where(Gutschein.einloesung_in_vd_id == einloesung_in_vd_id)
            ).first()
            if already is not None:
                raise HTTPException(
                    status_code=400,
                    detail="This sale position already redeemed a voucher",
                )

        balance = voucher_balance(session, nr)
        if balance <= 0:
            raise HTTPException(status_code=400, detail="Gutschein has no remaining balance")

        if vd is not None:
            amount = abs(_to_decimal(vd.ges_preis) or Decimal("0"))
            if betrag is not None and (_to_decimal(betrag) or Decimal("0")) != amount:
                raise HTTPException(
                    status_code=400,
                    detail="betrag does not match the sale position price",
                )
        elif betrag is not None:
            amount = _to_decimal(betrag) or Decimal("0")
        elif restbetrag is not None:
            amount = balance - (_to_decimal(restbetrag) or Decimal("0"))
        else:
            raise HTTPException(
                status_code=400,
                detail="betrag or einloesung_in_vd_id is required",
            )

        amount = amount.quantize(CENT, rounding=ROUND_HALF_UP)
        ensure_positive(amount, "betrag")
        new_balance = (balance - amount).quantize(CENT, rounding=ROUND_HALF_UP)
        if new_balance < 0:
            raise HTTPException(
                status_code=400,
                detail=f"betrag exceeds the remaining balance of {balance}",
            )
        if restbetrag is not None:
            requested = _to_decimal(restbetrag)
            if requested is not None and requested.quantize(CENT, rounding=ROUND_HALF_UP) != new_balance:
                raise HTTPException(
                    status_code=400,
                    detail=f"restbetrag does not match the calculated balance of {new_balance}",
                )

        if gutschein_in_vd_id is None:
            # Java copies the original sale position onto every redemption row
            gutschein_in_vd_id = original.gutschein_in_vd_id
            if gutschein_in_vd_id is None:
                creation = _creation_row(session, nr)
                if creation is not None:
                    gutschein_in_vd_id = creation.gutschein_in_vd_id
        if gutschein_in_vd_id is not None and session.get(VerkaufDetails, gutschein_in_vd_id) is None:
            raise HTTPException(status_code=400, detail="VerkaufDetails not found")

        new_g = Gutschein(
            gutschein_nr=nr,
            datum=datum if datum is not None else datetime.now(timezone.utc),
            gutschein_in_vd_id=gutschein_in_vd_id,
            einloesung_in_vd_id=einloesung_in_vd_id,
            restbetrag=float(new_balance),
            user_id=user_id,
        )
        new_g.gutschein_id = None
        session.add(new_g)
        session.flush()
        if commit:
            session.commit()
            session.refresh(new_g)
    return new_g


__all__ = [
    "VOUCHER_LOCK",
    "voucher_balance",
    "voucher_start_value",
    "next_gutschein_nr",
    "redeem_voucher",
]
