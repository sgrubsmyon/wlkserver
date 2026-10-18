"""Cash register (Kasse/Kassenstand) business logic."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Kassenstand, Verkauf
from .vat_calculator import _to_decimal

EC_THRESHOLD = Decimal("10.00")

def _resolve(a, b):
    from sqlmodel import Session as S
    if isinstance(a, S) and not isinstance(b, S):
        return a, b
    if isinstance(b, S) and not isinstance(a, S):
        return b, a
    return a, b


def get_current_kassenstand(session: Session) -> Optional[Kassenstand]:
    return session.exec(select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())).first()


def get_current_balance(session: Session) -> Decimal:
    ks = get_current_kassenstand(session)
    if ks is None:
        return Decimal("0")
    return _to_decimal(ks.neuer_kassenstand) or Decimal("0")


def calculate_change(total: Any, kunde_gibt: Any) -> Decimal:
    t = _to_decimal(total) or Decimal("0")
    k = _to_decimal(kunde_gibt) or Decimal("0")
    return (k - t).quantize(Decimal("0.01"))


def ec_payment_threshold_check(total: Any, ec_zahlung: bool) -> Optional[str]:
    t = _to_decimal(total) or Decimal("0")
    if ec_zahlung and t < EC_THRESHOLD:
        return "Gesamtbetrag liegt unter 10,00 EUR bei EC-Zahlung"
    return None


def update_kassenstand_for_sale(*args, **kwargs) -> Kassenstand:
    session = kwargs.get('session')
    rechnungs_nr = kwargs.get('rechnungs_nr')
    if session is None or rechnungs_nr is None:
        if len(args) >= 2:
            session, rechnungs_nr = _resolve(args[0], args[1])
        elif len(args) == 1:
            session = args[0]
    v = session.get(Verkauf, rechnungs_nr)
    if v is None:
        raise HTTPException(status_code=404, detail="Verkauf not found")
    # total price = sum of detail ges_preis
    total = Decimal("0")
    for d in (v.verkauf_details or []):
        if d.ges_preis is not None:
            total += _to_decimal(d.ges_preis) or Decimal("0")
    alter = get_current_balance(session)
    neuer = (alter + total).quantize(Decimal("0.01"))
    new_ks = Kassenstand(
        buchungsdatum=v.verkaufsdatum if v.verkaufsdatum is not None else datetime.now(timezone.utc),
        neuer_kassenstand=float(neuer),
        manuell=False,
        entnahme=False,
        rechnungs_nr=rechnungs_nr,
        kommentar=None,
    )
    new_ks.kassenstand_id = None
    session.add(new_ks)
    session.commit()
    session.refresh(new_ks)
    return new_ks



def process_payment(total, ec_zahlung=False, kunde_gibt=None):
    """Process a payment and return (change, warning)."""
    t = _to_decimal(total) or Decimal("0")
    warning = ec_payment_threshold_check(t, bool(ec_zahlung))
    change = calculate_change(t, kunde_gibt) if kunde_gibt is not None else Decimal("0.00")
    return change, warning


def is_training_mode() -> bool:
    # placeholder: no training tables in API yet
    return False


def end_of_day_procedure(session: Session) -> dict:
    return {"message": "End of day procedure not fully implemented"}


# aliases
get_aktuell = get_current_kassenstand
get_current = get_current_kassenstand
retrieve_kassenstand = get_current_balance
cash_register_update_for_sale = update_kassenstand_for_sale


__all__ = [
    "get_current_kassenstand",
    "get_current_balance",
    "calculate_change",
    "ec_payment_threshold_check",
    "update_kassenstand_for_sale",
    "is_training_mode",
    "end_of_day_procedure",
    "EC_THRESHOLD",
]
