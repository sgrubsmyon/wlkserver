"""Sale creation workflow helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import (
    Anzahlung,
    AnzahlungDetails,
    Artikel,
    Mwst,
    Rabattaktion,
    Verkauf,
    VerkaufDetails,
    VerkaufDetailsCreate,
)
from .cash_register import EC_THRESHOLD, ec_payment_threshold_check
from .vat_calculator import calculate_mwst_values_in_rechnung

CENT = Decimal("0.01")

# Special article numbers from the shop's master data (Java `WindowContent`
# uses the matching fixed IDs 1, 2, 3 and 7).
SPECIAL_ARTIKEL = {
    "rabatt": "RABATT1",
    "rechnung_rabatt": "RABATT2",
    "preisanpassung": "ANPASSUNG",
    "anzahlung": "ANZAHLUNG",
    "anzahlungsaufloesung": "ANZAHLAUFLOES",
    "gutschein_einloesung": "GUTSCHEINEINLOES",
}


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
    """Line price and one discount amount per action.

    Java order (`Kassieren.checkForRabatt`): absolute, relative, free items,
    quantity-relative. Each stage works on the unit price left by the previous
    one. The return value is `(net_total, [(action, reduction), ...])`; each
    reduction becomes its own RABATT position, like Java `addRabattRow`.
    """
    qty = Decimal(str(stueckzahl))
    unit = Decimal(str(base_unit))
    per_action = {}

    def add(r, amount):
        if amount:
            per_action.setdefault(r.rabatt_id, [r, Decimal("0")])[1] += amount

    for r in aktionen:
        if r.rabatt_absolut is not None:
            add(r, qty * Decimal(str(r.rabatt_absolut)))
            unit -= Decimal(str(r.rabatt_absolut))
    for r in aktionen:
        if r.rabatt_relativ is not None:
            add(r, qty * Decimal(str(r.rabatt_relativ)) * unit)
            unit -= Decimal(str(r.rabatt_relativ)) * unit
    for r in aktionen:
        if (r.mengenrabatt_schwelle and r.mengenrabatt_anzahl_kostenlos
                and stueckzahl >= r.mengenrabatt_schwelle):
            free = (stueckzahl // r.mengenrabatt_schwelle) * r.mengenrabatt_anzahl_kostenlos
            add(r, free * unit)
    for r in aktionen:
        if (r.mengenrabatt_relativ is not None and r.mengenrabatt_schwelle
                and stueckzahl >= r.mengenrabatt_schwelle):
            add(r, qty * Decimal(str(r.mengenrabatt_relativ)) * unit)
            unit -= Decimal(str(r.mengenrabatt_relativ)) * unit

    reductions = [(r, amount.quantize(CENT, rounding=ROUND_HALF_UP))
                  for r, amount in per_action.values()]
    total = qty * Decimal(str(base_unit)) - sum((amount for _, amount in reductions), Decimal("0"))
    if total < 0:
        raise HTTPException(status_code=400, detail="Rabattaktion exceeds the line price")
    return total.quantize(CENT, rounding=ROUND_HALF_UP), reductions


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
                return float(_apply_rabattaktionen(artikel.vk_preis, stueckzahl, aktionen)[0])
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


def _special_artikel(session, key) -> Artikel:
    nr = SPECIAL_ARTIKEL[key]
    artikel = session.exec(select(Artikel).where(Artikel.artikel_nr == nr)).first()
    if artikel is None:
        raise HTTPException(status_code=400, detail=f"Special article {nr} not found")
    return artikel


def _mwst_of(artikel: Artikel) -> float:
    pg = artikel.produktgruppe
    if pg is not None and pg.mwst is not None and pg.mwst.mwst_satz is not None:
        return float(pg.mwst.mwst_satz)
    return 0.0


def _aux_line(artikel: Artikel, stueckzahl, ges_preis, mwst_satz, rabatt_id=None):
    return VerkaufDetails(
        position=None,
        stueckzahl=stueckzahl,
        ges_preis=float(ges_preis),
        mwst_satz=mwst_satz,
        artikel_id=artikel.artikel_id,
        rabatt_id=rabatt_id,
    )


def build_sale_details(session, verkauf) -> list[VerkaufDetails]:
    """Expand a sale request into all positions, including auxiliary lines.

    Mirrors the Java cashier: the article line keeps its full price and every
    discount becomes its own negative RABATT line (or positive ANPASSUNG line
    for a price increase). A product-group deposit appends a PFAND position,
    the receipt-level discount adds one RABATT line per VAT rate, and a voucher
    redemption adds a negative GUTSCHEINEINLOES position. Discount lines have no
    position number, like Java `hinzufuegenRaw(addPosition=false)`.
    """
    rows: list[VerkaufDetails] = []
    article_rows = []
    position = 0

    def next_position():
        nonlocal position
        position += 1
        return position

    for detail in getattr(verkauf, "verkauf_details", None) or []:
        validate_detail(session, detail)
        data = detail.model_dump() if hasattr(detail, "model_dump") else dict(detail)
        artikel_id = data.get("artikel_id")
        artikel = session.get(Artikel, artikel_id) if artikel_id is not None else None
        stueckzahl = data.get("stueckzahl", 1)
        qty = Decimal(str(stueckzahl))
        mwst_satz = _mwst_of(artikel) if artikel is not None else 0.0

        unit = Decimal("0")
        if (artikel is not None and not getattr(artikel, "variabler_preis", False)
                and artikel.vk_preis is not None):
            unit = Decimal(str(artikel.vk_preis))
        line = VerkaufDetails(
            position=next_position(),
            stueckzahl=stueckzahl,
            ges_preis=float((unit * qty).quantize(CENT, rounding=ROUND_HALF_UP)),
            mwst_satz=mwst_satz,
            artikel_id=artikel_id,
            rabatt_id=None,
        )
        rows.append(line)
        has_discount = False

        if artikel is not None and stueckzahl > 0:
            aktionen = _active_rabattaktionen(session, artikel, data.get("rabatt_id"))
            if aktionen:
                _, reductions = _apply_rabattaktionen(artikel.vk_preis, stueckzahl, aktionen)
                for rabatt, reduction in reductions:
                    if reduction > 0:
                        rows.append(_aux_line(_special_artikel(session, "rabatt"), stueckzahl,
                                              -reduction, mwst_satz, rabatt.rabatt_id))
                        has_discount = True

            rabatt_absolut = data.get("rabatt_absolut")
            if rabatt_absolut is not None:
                amount = (Decimal(str(rabatt_absolut)) * qty).quantize(CENT, rounding=ROUND_HALF_UP)
                if amount:
                    key = "rabatt" if amount > 0 else "preisanpassung"
                    rows.append(_aux_line(_special_artikel(session, key), stueckzahl,
                                          -amount, mwst_satz))
                    has_discount = True

        article_rows.append((line, mwst_satz, has_discount))

        pfand = artikel.produktgruppe.pfand if artikel is not None and artikel.produktgruppe else None
        pfand_artikel = pfand.artikel if pfand is not None else None
        if stueckzahl and pfand_artikel is not None and pfand_artikel.vk_preis is not None:
            rows.append(VerkaufDetails(
                position=next_position(),
                stueckzahl=stueckzahl,
                ges_preis=float((Decimal(str(pfand_artikel.vk_preis)) * qty).quantize(
                    CENT, rounding=ROUND_HALF_UP)),
                mwst_satz=mwst_satz,
                artikel_id=pfand_artikel.artikel_id,
                rabatt_id=None,
            ))

    rechnung_rabatt = getattr(verkauf, "rechnung_rabatt_relativ", None)
    if rechnung_rabatt:
        factor = Decimal(str(rechnung_rabatt))
        sums: dict[float, Decimal] = {}
        for line, mwst_satz, has_discount in article_rows:
            if not has_discount:
                sums[mwst_satz] = sums.get(mwst_satz, Decimal("0")) + Decimal(str(line.ges_preis))
        rabatt_artikel = _special_artikel(session, "rechnung_rabatt")
        for mwst_satz, summe in sums.items():
            reduction = (factor * summe).quantize(CENT, rounding=ROUND_HALF_UP)
            if reduction > 0:
                rows.append(_aux_line(rabatt_artikel, 1, -reduction, mwst_satz))

    gutschein_nr = getattr(verkauf, "gutschein_einloesung_nr", None)
    if gutschein_nr is not None:
        from .voucher_logic import voucher_balance
        balance = voucher_balance(session, gutschein_nr)
        betrag = getattr(verkauf, "gutschein_einloesung_betrag", None)
        amount = Decimal(str(betrag)) if betrag is not None else balance
        amount = amount.quantize(CENT, rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="Gutschein has no remaining balance")
        if amount > balance:
            raise HTTPException(
                status_code=400,
                detail=f"Gutschein-Einlösung exceeds the remaining balance of {balance}",
            )
        artikel = _special_artikel(session, "gutschein_einloesung")
        rows.append(VerkaufDetails(
            position=next_position(),
            stueckzahl=1,
            ges_preis=float(-amount),
            mwst_satz=_mwst_of(artikel),
            artikel_id=artikel.artikel_id,
            rabatt_id=None,
        ))

    return rows


def apply_anzahlung(session, verkauf, rows) -> dict | None:
    """Apply an Anzahlung (deposit) to the built sale rows.

    Creating one (`anzahlung_betrag`) splits the paid amount across the VAT
    rates of the basket, appends one ANZAHLUNG position per rate and zeroes all
    other positions; their original prices are kept for `anzahlung_details`
    (Java `Kassieren.anzahlungHinzufuegen` / `maybeInsertIntoAnzahlung`).

    Resolving one (`anzahlung_aufloesen_nr`) re-adds the open deposit's
    positions with their original prices and turns each ANZAHLUNG line into a
    negative ANZAHLAUFLOES line (Java `AnzahlungAufloesDialog` /
    `maybeInsertAufloesungIntoAnzahlung`).
    """
    betrag = getattr(verkauf, "anzahlung_betrag", None)
    aufloesen_nr = getattr(verkauf, "anzahlung_aufloesen_nr", None)
    if betrag is not None and aufloesen_nr is not None:
        raise HTTPException(
            status_code=400,
            detail="Cannot create and resolve an Anzahlung in the same sale",
        )

    if betrag is not None:
        total = sum((Decimal(str(r.ges_preis)) for r in rows), Decimal("0"))
        amount = Decimal(str(betrag)).quantize(CENT, rounding=ROUND_HALF_UP)
        if amount <= 0:
            raise HTTPException(status_code=400, detail="anzahlung_betrag must be positive")
        if total <= 0:
            raise HTTPException(status_code=400, detail="Anzahlung requires article positions")
        if amount > total:
            raise HTTPException(
                status_code=400,
                detail="anzahlung_betrag exceeds the sale total",
            )

        summary = calculate_mwst_summary(rows)
        shares = []
        remaining = amount
        items = list(summary.items())
        for index, (rate, values) in enumerate(items):
            if index == len(items) - 1:
                share = remaining
            else:
                share = (values["brutto"] / total * amount).quantize(
                    CENT, rounding=ROUND_HALF_UP)
                remaining -= share
            shares.append((rate, share))

        originals = [(row, row.ges_preis) for row in rows]
        for row in rows:
            row.ges_preis = 0.0

        artikel = _special_artikel(session, "anzahlung")
        position = max((r.position or 0) for r in rows) + 1
        for rate, share in shares:
            rows.append(VerkaufDetails(
                position=position,
                stueckzahl=1,
                ges_preis=float(share),
                mwst_satz=float(rate),
                artikel_id=artikel.artikel_id,
                rabatt_id=None,
            ))
            position += 1
        return {"type": "create", "originals": originals}

    if aufloesen_nr is not None:
        if session.get(Verkauf, aufloesen_nr) is None:
            raise HTTPException(status_code=400, detail="Anzahlung Verkauf not found")
        already = session.exec(
            select(Anzahlung).where(
                Anzahlung.anzahlung_in_rech_nr == aufloesen_nr,
                Anzahlung.aufloesung_in_rech_nr.is_not(None),
            )
        ).first()
        if already is not None:
            raise HTTPException(status_code=400, detail="Anzahlung is already resolved")

        anzahlung_artikel = _special_artikel(session, "anzahlung")
        aufloesung_artikel = _special_artikel(session, "anzahlungsaufloesung")
        original_rows = session.exec(
            select(VerkaufDetails)
            .where(VerkaufDetails.rechnungs_nr == aufloesen_nr)
            .order_by(VerkaufDetails.vd_id)
        ).all()
        anzahlung_rows = [
            r for r in original_rows if r.artikel_id == anzahlung_artikel.artikel_id
        ]
        if not anzahlung_rows:
            raise HTTPException(status_code=400, detail="Verkauf is not an Anzahlung")
        last_vd_id = max(r.vd_id for r in anzahlung_rows)
        original_prices = {
            d.vd_id: d.ges_preis
            for d in session.exec(
                select(AnzahlungDetails).where(
                    AnzahlungDetails.rechnungs_nr == aufloesen_nr)
            ).all()
        }

        position = max((r.position or 0) for r in rows) + 1
        for original in original_rows:
            if original.vd_id > last_vd_id:
                continue
            if original.artikel_id == anzahlung_artikel.artikel_id:
                rows.append(VerkaufDetails(
                    position=position,
                    stueckzahl=1,
                    ges_preis=-original.ges_preis,
                    mwst_satz=original.mwst_satz,
                    artikel_id=aufloesung_artikel.artikel_id,
                    rabatt_id=None,
                ))
            else:
                rows.append(VerkaufDetails(
                    position=position,
                    stueckzahl=original.stueckzahl,
                    ges_preis=original_prices.get(original.vd_id, original.ges_preis),
                    mwst_satz=original.mwst_satz,
                    artikel_id=original.artikel_id,
                    rabatt_id=original.rabatt_id,
                ))
            position += 1
        return {"type": "resolve", "anzahlung_in_rech_nr": aufloesen_nr}

    return None


def write_anzahlung(session, meta, rechnungs_nr, datum, user_id=None):
    """Write the `anzahlung` row(s) after the sale positions are stored."""
    if not meta:
        return None
    if meta["type"] == "create":
        new_a = Anzahlung(
            datum=datum,
            anzahlung_in_rech_nr=rechnungs_nr,
            user_id=user_id,
        )
        new_a.anzahlung_id = None
        session.add(new_a)
        session.commit()
        for source, price in meta["originals"]:
            session.add(AnzahlungDetails(
                rechnungs_nr=rechnungs_nr,
                vd_id=source.vd_id,
                ges_preis=price,
            ))
        session.commit()
        return new_a

    new_a = Anzahlung(
        datum=datum,
        anzahlung_in_rech_nr=meta["anzahlung_in_rech_nr"],
        aufloesung_in_rech_nr=rechnungs_nr,
        user_id=user_id,
    )
    new_a.anzahlung_id = None
    session.add(new_a)
    session.commit()
    return new_a


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
    "build_sale_details",
    "apply_anzahlung",
    "write_anzahlung",
    "calculate_mwst_summary",
    "check_ec_payment_threshold",
]
