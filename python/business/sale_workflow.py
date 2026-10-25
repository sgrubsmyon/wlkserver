"""Sale creation workflow helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Artikel, Mwst, Rabattaktion, VerkaufDetails, VerkaufDetailsCreate
from .cash_register import EC_THRESHOLD, ec_payment_threshold_check
from .vat_calculator import calculate_mwst_values_in_rechnung


def _resolve(a, b):
    if isinstance(a, Session) and not isinstance(b, Session):
        return a, b
    if isinstance(b, Session) and not isinstance(a, Session):
        return b, a
    return a, b


def _field(detail, name, default=None):
    """Read a detail field from a model instance or a plain dict."""
    value = getattr(detail, name, None)
    if value is None and isinstance(detail, dict):
        value = detail.get(name)
    return default if value is None else value


def validate_detail(*args, **kwargs):
    detail = kwargs.get("detail")
    session = kwargs.get("session")
    if detail is None and len(args) >= 1:
        # guess: if first is Session, second detail
        if len(args) >= 2 and isinstance(args[0], Session):
            session, detail = args[0], args[1]
        else:
            detail = args[0]
            session = args[1] if len(args) > 1 else session
    stueckzahl = _field(detail, "stueckzahl", 1)
    if stueckzahl == 0:
        raise HTTPException(status_code=400, detail="stueckzahl must not be zero")
    if session is None:
        return
    artikel_id = _field(detail, "artikel_id")
    if artikel_id is not None and session.get(Artikel, artikel_id) is None:
        raise HTTPException(status_code=400, detail=f"Artikel {artikel_id} not found")
    rabatt_id = _field(detail, "rabatt_id")
    if rabatt_id is not None and session.get(Rabattaktion, rabatt_id) is None:
        raise HTTPException(status_code=400, detail=f"Rabattaktion {rabatt_id} not found")


def determine_mwst_satz(*args, **kwargs):
    session = kwargs.get("session")
    detail = kwargs.get("detail")
    if session is None or detail is None:
        if len(args) >= 2:
            session, detail = _resolve(args[0], args[1])
        elif len(args) == 1:
            detail = args[0]
    artikel_id = getattr(detail, "artikel_id", None)
    if artikel_id is None and isinstance(detail, dict):
        artikel_id = detail.get("artikel_id")
    if artikel_id is not None and session is not None:
        artikel = session.get(Artikel, artikel_id)
        if artikel is not None:
            pg = artikel.produktgruppe
            if pg is not None and pg.mwst_id is not None:
                mwst = session.get(Mwst, pg.mwst_id)
                if mwst is not None and mwst.mwst_satz is not None:
                    return float(mwst.mwst_satz)
    mwst_satz = getattr(detail, "mwst_satz", None)
    if mwst_satz is None and isinstance(detail, dict):
        mwst_satz = detail.get("mwst_satz")
    return mwst_satz


def _rabatt_matches(rabatt: Rabattaktion, artikel: Artikel) -> bool:
    """True if the action targets the article directly or its product group.

    Mirrors the Java POS group matching: a NULL sub/subsub id acts as a wildcard
    so an action can be attached to a higher-level group.
    """
    if rabatt.artikel_id is not None:
        return rabatt.artikel_id == artikel.artikel_id
    if rabatt.produktgruppen_id is None:
        return False
    pg = artikel.produktgruppe
    action_pg = rabatt.produktgruppe
    if pg is None or action_pg is None:
        return False
    if action_pg.toplevel_id != pg.toplevel_id:
        return False
    if action_pg.sub_id is not None and action_pg.sub_id != pg.sub_id:
        return False
    if action_pg.subsub_id is not None and action_pg.subsub_id != pg.subsub_id:
        return False
    return True


def _active_rabattaktionen(session: Session, artikel: Artikel, rabatt_id=None):
    """Discount actions to apply: an explicit one, or all currently active ones.

    Automatic selection mirrors the Java POS (`Kassieren.checkForRabatt`): the
    action must be within its `von..bis` window and target the article or its
    product group.
    """
    now = datetime.now(timezone.utc)
    if rabatt_id is not None:
        rabatt = session.get(Rabattaktion, rabatt_id)
        if rabatt is None:
            raise HTTPException(status_code=400, detail=f"Rabattaktion {rabatt_id} not found")
        if rabatt.von is not None and rabatt.von > now:
            raise HTTPException(status_code=400, detail="Rabattaktion is not active yet")
        if rabatt.bis is not None and rabatt.bis < now:
            raise HTTPException(status_code=400, detail="Rabattaktion has expired")
        if not _rabatt_matches(rabatt, artikel):
            raise HTTPException(status_code=400, detail="Rabattaktion does not apply to this article")
        return [rabatt]

    rows = session.exec(
        select(Rabattaktion)
        .where(
            Rabattaktion.von <= now,
            (Rabattaktion.bis.is_(None)) | (Rabattaktion.bis >= now),
        )
        .order_by(Rabattaktion.rabatt_id)
    ).all()
    return [r for r in rows if _rabatt_matches(r, artikel)]


def _apply_rabattaktionen(base_unit, stueckzahl, aktionen):
    """Final line price with the given discounts.

    Java order (`Kassieren.checkForRabatt`): absolute, relative, free items,
    quantity-relative. Each stage works on the unit price left by the previous one.
    """
    qty = Decimal(str(stueckzahl))
    unit = Decimal(str(base_unit))
    reduction = Decimal("0")

    for r in aktionen:
        if r.rabatt_absolut is not None:
            reduction += qty * Decimal(str(r.rabatt_absolut))
            unit -= Decimal(str(r.rabatt_absolut))
    for r in aktionen:
        if r.rabatt_relativ is not None:
            reduction += qty * Decimal(str(r.rabatt_relativ)) * unit
            unit -= Decimal(str(r.rabatt_relativ)) * unit
    for r in aktionen:
        if (r.mengenrabatt_schwelle and r.mengenrabatt_anzahl_kostenlos
                and stueckzahl >= r.mengenrabatt_schwelle):
            free = (stueckzahl // r.mengenrabatt_schwelle) * r.mengenrabatt_anzahl_kostenlos
            reduction += free * unit
    for r in aktionen:
        if (r.mengenrabatt_relativ is not None and r.mengenrabatt_schwelle
                and stueckzahl >= r.mengenrabatt_schwelle):
            reduction += qty * Decimal(str(r.mengenrabatt_relativ)) * unit
            unit -= Decimal(str(r.mengenrabatt_relativ)) * unit

    total = qty * Decimal(str(base_unit)) - reduction
    if total < 0:
        raise HTTPException(status_code=400, detail="Rabattaktion exceeds the line price")
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def determine_ges_preis(*args, **kwargs):
    session = kwargs.get("session")
    detail = kwargs.get("detail")
    if session is None or detail is None:
        if len(args) >= 2:
            session, detail = _resolve(args[0], args[1])
        elif len(args) == 1:
            detail = args[0]
    artikel_id = _field(detail, "artikel_id")
    stueckzahl = _field(detail, "stueckzahl", 1)
    ges_preis = _field(detail, "ges_preis")
    if ges_preis is not None:
        return float(ges_preis)
    if artikel_id is not None and session is not None:
        artikel = session.get(Artikel, artikel_id)
        if artikel is not None and not getattr(artikel, "variabler_preis", False) and artikel.vk_preis is not None:
            if stueckzahl <= 0:
                return float((Decimal(str(artikel.vk_preis)) * Decimal(str(stueckzahl))).quantize(
                    Decimal("0.01"), rounding=ROUND_HALF_UP))
            aktionen = _active_rabattaktionen(session, artikel, _field(detail, "rabatt_id"))
            if aktionen:
                return float(_apply_rabattaktionen(artikel.vk_preis, stueckzahl, aktionen))
            return float((Decimal(str(artikel.vk_preis)) * Decimal(str(stueckzahl))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP))
    return None


def prepare_detail(*args, **kwargs):
    session = kwargs.get("session")
    detail = kwargs.get("detail")
    if session is None or detail is None:
        if len(args) >= 2:
            session, detail = _resolve(args[0], args[1])
        elif len(args) == 1:
            detail = args[0]
    # Normalize to a dict so we can derive missing fields uniformly.
    if isinstance(detail, dict):
        data = detail
    elif hasattr(detail, "model_dump"):
        data = {k: v for k, v in detail.model_dump().items() if v is not None}
    else:
        data = {}

    stueckzahl = data.get("stueckzahl", 1)
    mwst_satz = data.get("mwst_satz")
    ges_preis = data.get("ges_preis")
    explicit_price = ges_preis is not None

    if mwst_satz is None:
        derived = determine_mwst_satz(session, data) if session is not None else determine_mwst_satz(data)
        if derived is not None:
            mwst_satz = derived
    if ges_preis is None:
        derived = determine_ges_preis(session, data) if session is not None else determine_ges_preis(data)
        if derived is not None:
            ges_preis = derived

    rabatt_id = data.get("rabatt_id")
    if (rabatt_id is None and not explicit_price and session is not None
            and data.get("artikel_id") is not None):
        artikel = session.get(Artikel, data["artikel_id"])
        if artikel is not None and not getattr(artikel, "variabler_preis", False):
            aktionen = _active_rabattaktionen(session, artikel)
            if len(aktionen) == 1:
                rabatt_id = aktionen[0].rabatt_id

    return VerkaufDetails(
        position=data.get("position"),
        stueckzahl=stueckzahl,
        ges_preis=ges_preis if ges_preis is not None else 0.0,
        mwst_satz=mwst_satz if mwst_satz is not None else 0.0,
        rechnungs_nr=data.get("rechnungs_nr", 0),
        artikel_id=data.get("artikel_id"),
        rabatt_id=rabatt_id,
    )


def calculate_mwst_summary(details):
    """VAT summary per rate for the given positions.

    Delegates to `calculate_mwst_values_in_rechnung`, so the receipt rounding
    method configured via `VAT_ROUNDING_METHOD` (horizontal/vertical) applies.
    """
    items = [
        {"ges_preis": d.ges_preis, "mwst_satz": d.mwst_satz}
        for d in details
        if getattr(d, "mwst_satz", None) is not None and getattr(d, "ges_preis", None) is not None
    ]
    return {
        rate: {"mwst_netto": values[0], "mwst_betrag": values[1], "brutto": values[2]}
        for rate, values in calculate_mwst_values_in_rechnung(items).items()
    }


def check_ec_payment_threshold(total, ec_zahlung=None):
    """EC card warning below the 10 EUR threshold (delegates to cash_register)."""
    if isinstance(total, bool):
        total, ec_zahlung = ec_zahlung, total
    return ec_payment_threshold_check(total, bool(ec_zahlung))


__all__ = [
    "EC_THRESHOLD",
    "validate_detail",
    "determine_mwst_satz",
    "determine_ges_preis",
    "prepare_detail",
    "calculate_mwst_summary",
    "check_ec_payment_threshold",
]
