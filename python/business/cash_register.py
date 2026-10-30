"""Cash register (Kasse/Kassenstand) business logic."""
from __future__ import annotations

import threading
from contextlib import nullcontext
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Kassenstand, Verkauf
from ..session import is_training_mode
from .vat_calculator import _to_decimal
EC_THRESHOLD = Decimal("10.00")

# Balance updates are read-modify-write; serialize them in this process and lock
# the balance row on databases that support SELECT ... FOR UPDATE (MariaDB).
KASSENSTAND_LOCK = threading.Lock()

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


def validate_balance_change(alter, neuer, entnahme: bool = False) -> Decimal:
    """Validate a new cash balance against the previous one.

    An Entnahme (cash withdrawal) must lower the balance and must not exceed
    the cash in the drawer. Regular sales/storno entries may go negative, which
    mirrors the Java POS (a refund can exceed the current balance).
    """
    previous = _to_decimal(alter) or Decimal("0")
    new = _to_decimal(neuer) or Decimal("0")
    if entnahme:
        if new > previous:
            raise HTTPException(status_code=400, detail="Entnahme must not increase the Kassenstand")
        if new < 0:
            raise HTTPException(status_code=400, detail="Entnahme exceeds the current Kassenstand")
    return new


def update_kassenstand_for_sale(*args, **kwargs) -> Kassenstand:
    session = kwargs.get('session')
    rechnungs_nr = kwargs.get('rechnungs_nr')
    if session is None or rechnungs_nr is None:
        if len(args) >= 2:
            session, rechnungs_nr = _resolve(args[0], args[1])
        elif len(args) == 1:
            session = args[0]
    manuell = kwargs.get('manuell', False)
    entnahme = kwargs.get('entnahme', False)
    kommentar = kwargs.get('kommentar', None)
    buchungsdatum = kwargs.get('buchungsdatum', None)
    # `commit=False` lets the caller commit the whole sale in one transaction;
    # it must keep `KASSENSTAND_LOCK` (pass `lock=False` only inside it) so the
    # read-modify-write stays serialized until that commit.
    commit = kwargs.get('commit', True)
    lock = kwargs.get('lock', True)
    with (KASSENSTAND_LOCK if lock else nullcontext()):
        v = session.get(Verkauf, rechnungs_nr)
        if v is None:
            raise HTTPException(status_code=404, detail="Verkauf not found")
        # total price = sum of detail ges_preis
        total = Decimal("0")
        for d in (v.verkauf_details or []):
            if d.ges_preis is not None:
                total += _to_decimal(d.ges_preis) or Decimal("0")
        last = session.exec(
            select(Kassenstand)
            .order_by(Kassenstand.kassenstand_id.desc())
            .with_for_update()
        ).first()
        alter = _to_decimal(last.neuer_kassenstand) if last is not None else Decimal("0")
        alter = alter or Decimal("0")
        neuer = (alter + total).quantize(Decimal("0.01"))
        validate_balance_change(alter, neuer, entnahme)
        new_ks = Kassenstand(
            buchungsdatum=buchungsdatum if buchungsdatum is not None else (v.verkaufsdatum if v.verkaufsdatum is not None else datetime.now(timezone.utc)),
            neuer_kassenstand=float(neuer),
            manuell=manuell,
            entnahme=entnahme,
            rechnungs_nr=rechnungs_nr,
            kommentar=kommentar,
        )
        new_ks.kassenstand_id = None
        session.add(new_ks)
        session.flush()
        if commit:
            session.commit()
            session.refresh(new_ks)
    return new_ks



def process_payment(total, ec_zahlung=False, kunde_gibt=None):
    """Process a payment and return (change, warning)."""
    t = _to_decimal(total) or Decimal("0")
    warning = ec_payment_threshold_check(t, bool(ec_zahlung))
    change = calculate_change(t, kunde_gibt) if kunde_gibt is not None else Decimal("0.00")
    return change, warning


def last_settlement(session: Session):
    from ..models import AbrechnungTag
    return session.exec(select(AbrechnungTag).order_by(AbrechnungTag.id.desc())).first()


def open_period_range(session: Session):
    """Receipt-number range since the last Tagesabschluss (None if no open sales)."""
    last = last_settlement(session)
    last_bis = last.rechnungs_nr_bis if last is not None else 0
    first_sale = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.rechnungs_nr)
    ).first()
    if first_sale is None:
        return None
    last_sale = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.rechnungs_nr.desc())
    ).first()
    return first_sale.rechnungs_nr, last_sale.rechnungs_nr


def aggregate_period(session: Session, von: int, bis: int) -> dict:
    """Aggregate sales of a receipt range for the Tagesabschluss.

    Mirrors the Java queries: VAT net/tax per rate from `verkauf_mwst`,
    `bar_brutto` from the detail prices of cash (non-EC) receipts only, plus the
    separate storno (original amounts) and retouren reporting.
    """
    sales = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr >= von, Verkauf.rechnungs_nr <= bis)
    ).all()

    stornoed_numbers = {v.storno_von for v in sales if v.storno_von is not None}
    storno_summe = 0.0
    retouren_summe = 0.0
    for v in sales:
        if v.rechnungs_nr in stornoed_numbers:
            # report the amounts of the cancelled original receipts (positive)
            for m in v.verkauf_mwst or []:
                storno_summe += (m.mwst_netto or 0) + (m.mwst_betrag or 0)
        if v.storno_von is None:
            for d in v.verkauf_details or []:
                if d.stueckzahl is not None and d.stueckzahl < 0 and d.ges_preis is not None:
                    retouren_summe += d.ges_preis

    mwst_map = {}
    for v in sales:
        for m in v.verkauf_mwst or []:
            entry = mwst_map.setdefault(m.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["netto"] += m.mwst_netto
            entry["betrag"] += m.mwst_betrag
    # Storno/retour receipts have negative ges_preis and are included (nets out).
    for v in sales:
        if v.ec_zahlung:
            continue
        for d in v.verkauf_details or []:
            if d.mwst_satz is None or d.ges_preis is None:
                continue
            entry = mwst_map.setdefault(d.mwst_satz, {"netto": 0.0, "betrag": 0.0, "bar": 0.0})
            entry["bar"] += d.ges_preis

    return {
        "sales": sales,
        "storno_summe": storno_summe,
        "retouren_summe": retouren_summe,
        "mwst_map": mwst_map,
        "cash_sales": [v for v in sales if not v.ec_zahlung],
        "ec_sales": [v for v in sales if v.ec_zahlung],
    }


def cash_withdrawals(session: Session, last_kassenstand_id: int | None = None) -> float:
    """Sum of Entnahmen since the previous settlement (neuer = previous - amount)."""
    current_balance = float(get_current_balance(session))
    total = 0.0
    previous = None
    for ks in session.exec(select(Kassenstand).order_by(Kassenstand.kassenstand_id)).all():
        if ks.kassenstand_id is None or (
            last_kassenstand_id is not None and ks.kassenstand_id <= last_kassenstand_id
        ):
            previous = ks.neuer_kassenstand
            continue
        if ks.entnahme:
            base = previous if previous is not None else current_balance
            total += (base - ks.neuer_kassenstand)
        previous = ks.neuer_kassenstand
    return total


def end_of_day_procedure(session: Session) -> dict:
    """Read-only preview of the open Tagesabschluss (nothing is written).

    Same calculation as `POST /abrechnung/tag`, so the cashier can compare the
    expected drawer with the counted cash before closing the day.
    """
    last = last_settlement(session)
    current_balance = get_current_balance(session)
    entnahmen = cash_withdrawals(
        session, last.kassenstand_id if last is not None else None
    )
    period = open_period_range(session)
    if period is None:
        return {
            "open": False,
            "rechnungs_nr_von": None,
            "rechnungs_nr_bis": None,
            "sales": 0,
            "cash_sales": 0,
            "ec_sales": 0,
            "stornos": 0,
            "storno_summe": 0.0,
            "retouren_summe": 0.0,
            "mwst": [],
            "current_balance": float(current_balance),
            "entnahmen": round(entnahmen, 2),
            "expected_balance": float(current_balance),
        }

    von, bis = period
    agg = aggregate_period(session, von, bis)
    return {
        "open": True,
        "rechnungs_nr_von": von,
        "rechnungs_nr_bis": bis,
        "sales": len(agg["sales"]),
        "cash_sales": len(agg["cash_sales"]),
        "ec_sales": len(agg["ec_sales"]),
        "stornos": sum(1 for v in agg["sales"] if v.storno_von is not None),
        "storno_summe": round(agg["storno_summe"], 2),
        "retouren_summe": round(agg["retouren_summe"], 2),
        "mwst": [
            {
                "mwst_satz": satz,
                "mwst_netto": round(values["netto"], 2),
                "mwst_betrag": round(values["betrag"], 2),
                "bar_brutto": round(values["bar"], 2),
            }
            for satz, values in sorted(agg["mwst_map"].items())
        ],
        "current_balance": float(current_balance),
        "entnahmen": round(entnahmen, 2),
        # the ledger balance already contains all cash movements of the period
        "expected_balance": float(current_balance),
    }


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
    "validate_balance_change",
    "is_training_mode",
    "last_settlement",
    "open_period_range",
    "aggregate_period",
    "cash_withdrawals",
    "end_of_day_procedure",
    "EC_THRESHOLD",
]
