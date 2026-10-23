"""Sale creation workflow helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Artikel, Mwst, Rabattaktion, Verkauf, VerkaufCreate, VerkaufDetails, VerkaufDetailsCreate, VerkaufMwst
from .vat_calculator import calculate_vat, _to_decimal

EC_THRESHOLD = Decimal("10.00")


def _resolve(a, b):
    if isinstance(a, Session) and not isinstance(b, Session):
        return a, b
    if isinstance(b, Session) and not isinstance(a, Session):
        return b, a
    return a, b


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
    stueckzahl = getattr(detail, "stueckzahl", None)
    if stueckzahl is None and isinstance(detail, dict):
        stueckzahl = detail.get("stueckzahl", 1)
    if stueckzahl is None:
        stueckzahl = 1
    if stueckzahl == 0:
        raise HTTPException(status_code=400, detail="stueckzahl must not be zero")


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
    rabatt_id = getattr(detail, "rabatt_id", None)
    if rabatt_id is None and isinstance(detail, dict):
        rabatt_id = detail.get("rabatt_id")
    if rabatt_id is not None and session is not None:
        rabatt = session.get(Rabattaktion, rabatt_id)
        if rabatt is not None and getattr(rabatt, "mwst_satz", None) is not None:
            return float(rabatt.mwst_satz)
    mwst_satz = getattr(detail, "mwst_satz", None)
    if mwst_satz is None and isinstance(detail, dict):
        mwst_satz = detail.get("mwst_satz")
    return mwst_satz


def determine_ges_preis(*args, **kwargs):
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
    stueckzahl = getattr(detail, "stueckzahl", None)
    if stueckzahl is None and isinstance(detail, dict):
        stueckzahl = detail.get("stueckzahl", 1)
    if stueckzahl is None:
        stueckzahl = 1
    ges_preis = getattr(detail, "ges_preis", None)
    if ges_preis is None and isinstance(detail, dict):
        ges_preis = detail.get("ges_preis")
    if ges_preis is not None:
        return float(ges_preis)
    if artikel_id is not None and session is not None:
        artikel = session.get(Artikel, artikel_id)
        if artikel is not None and not getattr(artikel, "variabler_preis", False) and artikel.vk_preis is not None:
            base = float(stueckzahl * artikel.vk_preis)
            # Apply discount from Rabattaktion if present (item 4)
            rabatt_id = getattr(detail, "rabatt_id", None)
            if rabatt_id is None and isinstance(detail, dict):
                rabatt_id = detail.get("rabatt_id")
            if rabatt_id is not None:
                rabatt = session.get(Rabattaktion, rabatt_id)
                if rabatt is not None:
                    if getattr(rabatt, "rabatt_relativ", None) is not None:
                        base = base * (1.0 - float(rabatt.rabatt_relativ))
                    elif getattr(rabatt, "rabatt_absolut", None) is not None:
                        base = base - float(rabatt.rabatt_absolut) * stueckzahl
                    if getattr(rabatt, "mengenrabatt_anzahl_kostenlos", None) and stueckzahl >= (rabatt.mengenrabatt_schwelle or 0):
                        # buy X get Y free: reduce by free items
                        free = (stueckzahl // (rabatt.mengenrabatt_schwelle or 1)) * (rabatt.mengenrabatt_anzahl_kostenlos or 0)
                        if artikel.vk_preis is not None:
                            base -= free * float(artikel.vk_preis)
            return round(base, 2)
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

    if mwst_satz is None:
        derived = determine_mwst_satz(session, data) if session is not None else determine_mwst_satz(data)
        if derived is not None:
            mwst_satz = derived
    if ges_preis is None:
        derived = determine_ges_preis(session, data) if session is not None else determine_ges_preis(data)
        if derived is not None:
            ges_preis = derived

    return VerkaufDetails(
        position=data.get("position"),
        stueckzahl=stueckzahl,
        ges_preis=ges_preis if ges_preis is not None else 0.0,
        mwst_satz=mwst_satz if mwst_satz is not None else 0.0,
        rechnungs_nr=data.get("rechnungs_nr", 0),
        artikel_id=data.get("artikel_id"),
        rabatt_id=data.get("rabatt_id"),
    )


def calculate_mwst_summary(details):
    summary = {}
    for d in details:
        if getattr(d, "mwst_satz", None) is None or getattr(d, "ges_preis", None) is None:
            continue
        rate = Decimal(str(d.mwst_satz))
        brutto = Decimal(str(d.ges_preis))
        steuer = calculate_vat(brutto, rate)
        netto = brutto - steuer
        if rate not in summary:
            summary[rate] = {"mwst_netto": Decimal("0"), "mwst_betrag": Decimal("0"), "brutto": Decimal("0")}
        summary[rate]["mwst_netto"] += netto
        summary[rate]["mwst_betrag"] += steuer
        summary[rate]["brutto"] += brutto
    for rate in summary:
        summary[rate]["mwst_netto"] = summary[rate]["mwst_netto"].quantize(Decimal("0.01"))
        summary[rate]["mwst_betrag"] = summary[rate]["mwst_betrag"].quantize(Decimal("0.01"))
        summary[rate]["brutto"] = summary[rate]["brutto"].quantize(Decimal("0.01"))
    return summary


def check_ec_payment_threshold(total, ec_zahlung=None):
    # support (total, ec) or (ec, total)? detect bool
    if isinstance(total, bool):
        total, ec_zahlung = ec_zahlung, total
    t = _to_decimal(total) or Decimal("0")
    if ec_zahlung and t < EC_THRESHOLD:
        return "Gesamtbetrag liegt unter 10,00 EUR bei EC-Zahlung"
    return None


def create_verkauf(*args, **kwargs):
    session = kwargs.get("session")
    verkauf = kwargs.get("verkauf") or kwargs.get("verkauf_create") or kwargs.get("data")
    if session is None or verkauf is None:
        if len(args) >= 2:
            session, verkauf = _resolve(args[0], args[1])
        elif len(args) == 1:
            verkauf = args[0]
    # if only one passed and it's not session, cannot create without session
    from sqlmodel import Session as S
    if not isinstance(session, S):
        # maybe session is second
        pass
    ec_zahlung = getattr(verkauf, "ec_zahlung", None)
    if ec_zahlung is None and isinstance(verkauf, dict):
        ec_zahlung = verkauf.get("ec_zahlung", False)
    if ec_zahlung is None:
        ec_zahlung = False
    kunde_gibt = getattr(verkauf, "kunde_gibt", None)
    if kunde_gibt is None and isinstance(verkauf, dict):
        kunde_gibt = verkauf.get("kunde_gibt", None)
    storno_von = getattr(verkauf, "storno_von", None)
    if storno_von is None and isinstance(verkauf, dict):
        storno_von = verkauf.get("storno_von", None)
    user_id = getattr(verkauf, "user_id", None)
    if user_id is None and isinstance(verkauf, dict):
        user_id = verkauf.get("user_id", None)
    details_in = getattr(verkauf, "verkauf_details", None)
    if details_in is None and isinstance(verkauf, dict):
        details_in = verkauf.get("verkauf_details", []) or []
    if details_in is None:
        details_in = []

    new_v = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=ec_zahlung,
        kunde_gibt=kunde_gibt,
        storno_von=storno_von,
        user_id=user_id,
    )
    new_v.rechnungs_nr = None
    session.add(new_v)
    session.commit()
    session.refresh(new_v)

    prepared = []
    for d in details_in:
        vd = prepare_detail(session, d)
        vd.vd_id = None
        vd.rechnungs_nr = new_v.rechnungs_nr
        session.add(vd)
        prepared.append(vd)
    session.commit()
    for vd in prepared:
        session.refresh(vd)

    summary = calculate_mwst_summary(prepared)
    for rate, vals in summary.items():
        m_obj = VerkaufMwst(
            rechnungs_nr=new_v.rechnungs_nr,
            mwst_satz=float(rate),
            mwst_netto=float(vals["mwst_netto"]),
            mwst_betrag=float(vals["mwst_betrag"]),
        )
        session.add(m_obj)
    session.commit()
    session.refresh(new_v)

    # Cash register side-effect for cash (non-EC) sales, mirroring the router.
    if not ec_zahlung:
        try:
            from .cash_register import update_kassenstand_for_sale
            update_kassenstand_for_sale(session=session, rechnungs_nr=new_v.rechnungs_nr)
        except Exception:
            pass
    return new_v


create_sale = create_verkauf
createVerkauf = create_verkauf


__all__ = [
    "EC_THRESHOLD",
    "validate_detail",
    "determine_mwst_satz",
    "determine_ges_preis",
    "prepare_detail",
    "calculate_mwst_summary",
    "check_ec_payment_threshold",
    "create_verkauf",
    "create_sale",
    "createVerkauf",
]
