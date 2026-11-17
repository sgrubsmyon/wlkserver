"""Fill the Java POS spreadsheet templates (ODS).

The templates live in `VORLAGEN_DIR` (default: the Java POS `git/vorlagen`
directory next to this repository) and are ordinary LibreOffice files. Cell
positions and column layout mirror `BestellAnzeige.java` (orders and inventory)
and `Abrechnungen.java`/`AbrechnungenTag.java` (daily/monthly/yearly
settlements), so an existing template can be edited in LibreOffice without
touching this module.

The ODT text documents (price tags, receipts) are not exported yet: their
templates still contain jOpenDocument fields. They will use placeholder strings
and `utils.odt.render_odt_template` once reworked (see `concepts/TODO.md`).
"""
from __future__ import annotations

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path

from sqlmodel import select

from .. import config
from ..models import (
    AbrechnungJahr,
    AbrechnungJahrMwst,
    AbrechnungMonat,
    AbrechnungMonatMwst,
    AbrechnungTag,
    AbrechnungTagMwst,
    Artikel,
    Bestellung,
    BestellungDetails,
    Kassenstand,
    Verkauf,
    VerkaufDetails,
    VerkaufMwst,
    Zaehlprotokoll,
    ZaehlprotokollDetails,
)
from ..utils import ods
from .errors import NotFoundError
from .vat_calculator import calculate_vat

CENT = Decimal("0.01")
MONTHS = ("Januar", "Februar", "März", "April", "Mai", "Juni", "Juli",
          "August", "September", "Oktober", "November", "Dezember")
CURRENCY = "€"
INTERNAL_GROUPS = (1, 6, 7, 8)  # Java: no Retoure for Rabatt/Gutschein/Pfand


def _decimal(value) -> Decimal:
    return Decimal(str(value)) if value is not None else Decimal("0")


def _template(name: str) -> bytes:
    path = Path(config.templates_dir()) / name
    if not path.exists():
        raise RuntimeError(f"ODS template not found: {path} (set VORLAGEN_DIR)")
    return path.read_bytes()


def _writer(name: str, model_row: int):
    return ods.load_sheet(_template(name), model_row)


def _vat_label(rate) -> str:
    percent = (_decimal(rate) * 100).normalize()
    return f"{format(percent, 'f').replace('.', ',')}%"


def _money_label(value) -> str:
    return format(_decimal(value).quantize(CENT, rounding=ROUND_HALF_UP), "f").replace(".", ",")


def _order_details(session, bestell_nr: int, typ: str):
    order = session.get(Bestellung, bestell_nr)
    if not order or order.typ != typ:
        raise NotFoundError(f"Bestellung {bestell_nr}/{typ} not found")
    details = session.exec(
        select(BestellungDetails).where(
            BestellungDetails.bestell_nr == bestell_nr,
            BestellungDetails.typ == typ,
        )
    ).all()
    rows = []
    for detail in details:
        artikel = session.get(Artikel, detail.artikel_id)
        if artikel is None:
            continue
        rows.append((detail, artikel, artikel.produktgruppe, artikel.lieferant))
    rows.sort(key=lambda item: (
        item[2].toplevel_id if item[2] and item[2].toplevel_id is not None else 0,
        item[2].sub_id if item[2] and item[2].sub_id is not None else 0,
        item[2].subsub_id if item[2] and item[2].subsub_id is not None else 0,
        item[1].artikel_name,
    ))
    return order, rows


def export_bestellung(session, bestell_nr: int, typ: str) -> bytes:
    """Fill `Bestellvorlage_<typ>.ods` with one order (date, KW, positions)."""
    order, rows = _order_details(session, bestell_nr, typ)
    document, sheet = _writer(f"Bestellvorlage_{typ}.ods", model_row=8)
    sheet.set(1, 2, order.bestell_datum.strftime("%d.%m.%Y"))  # C2
    sheet.set(1, 8, order.kw)  # I2
    for index, (detail, artikel, _, lieferant) in enumerate(rows):
        vk_preis = artikel.empf_vk_preis if artikel.empf_vk_preis is not None else artikel.vk_preis
        sheet.set(8 + index, 0, lieferant.lieferant_name if lieferant else None)
        sheet.set(8 + index, 1, artikel.artikel_nr)
        sheet.set(8 + index, 2, artikel.artikel_name)
        sheet.set(8 + index, 3, artikel.vpe)
        sheet.set(8 + index, 4, vk_preis)
        sheet.set(8 + index, 5, artikel.ek_preis)
        sheet.set(8 + index, 6, artikel.produktgruppe.mwst.mwst_satz if artikel.produktgruppe and artikel.produktgruppe.mwst else None)
        sheet.set(8 + index, 7, detail.stueckzahl)
    return ods.save(document)


def export_inventur(session, bestell_nr: int, typ: str = "IVT") -> bytes:
    """Fill `Inventur.ods` with the counted stock of one inventory order."""
    order, rows = _order_details(session, bestell_nr, typ)
    document, sheet = _writer("Inventur.ods", model_row=3)
    sheet.set(0, 0, f"Inventur 31.12.{order.jahr}")
    for index, (detail, artikel, _, lieferant) in enumerate(rows):
        setgroesse = Decimal(str(artikel.setgroesse or 1))
        ek_preis_set = _decimal(artikel.ek_preis) if artikel.ek_preis is not None else None
        mwst = _decimal(artikel.produktgruppe.mwst.mwst_satz) if artikel.produktgruppe and artikel.produktgruppe.mwst else Decimal("0")
        stueck = Decimal(str(detail.stueckzahl))
        ek_preis = single_mwst = single_netto = total_brutto = total_mwst = total_netto = None
        if ek_preis_set is not None:
            ek_preis = (ek_preis_set / setgroesse).quantize(CENT, rounding=ROUND_HALF_UP)
            single_mwst = calculate_vat(ek_preis, mwst)
            single_netto = ek_preis - single_mwst
            total_brutto = ek_preis * stueck
            total_mwst = single_mwst * stueck
            total_netto = single_netto * stueck
        total_vkp = (_decimal(artikel.vk_preis) * stueck) if artikel.vk_preis is not None else None
        values = (
            lieferant.lieferant_kurzname if lieferant else None,
            artikel.artikel_nr,
            artikel.artikel_name,
            artikel.vk_preis,
            artikel.empf_vk_preis,
            artikel.setgroesse,
            (_decimal(artikel.ek_rabatt) * 100) if artikel.ek_rabatt is not None else None,
            ek_preis_set,
            ek_preis,
            mwst * 100,
            single_netto,
            single_mwst,
            detail.stueckzahl,
            total_netto,
            total_mwst,
            total_brutto,
            total_vkp,
        )
        for column, value in enumerate(values):
            sheet.set(3 + index, column, value)
    return ods.save(document)


def _settlement_rows(session, kind: str, settlement_id: int):
    if kind == "tag":
        row = session.get(AbrechnungTag, settlement_id)
        vat_model = AbrechnungTagMwst
        label = row.zeitpunkt.strftime("%d.%m.%Y") if row else None
        template = "Tagesabrechnung.ods"
    elif kind == "monat":
        row = session.get(AbrechnungMonat, settlement_id)
        vat_model = AbrechnungMonatMwst
        label = f"{MONTHS[row.monat.month - 1]} {row.monat.year}" if row else None
        template = "Monatsabrechnung.ods"
    elif kind == "jahr":
        row = session.get(AbrechnungJahr, settlement_id)
        vat_model = AbrechnungJahrMwst
        label = str(row.jahr) if row else None
        template = "Jahresabrechnung.ods"
    else:
        raise NotFoundError(f"Unknown settlement kind: {kind}")
    if row is None:
        raise NotFoundError(f"{kind} settlement {settlement_id} not found")
    vat_rows = session.exec(
        select(vat_model).where(vat_model.id == settlement_id).order_by(vat_model.mwst_satz)
    ).all()
    return row, vat_rows, label, template


def export_settlement(session, kind: str, settlement_id: int) -> bytes:
    """Fill Tages-/Monats-/Jahresabrechnung.ods like the Java POS export.

    Daily settlements also carry the per-rate stornos/retouren, the withdrawals
    and the most recent count protocol with its balance checks.
    """
    row, vat_rows, label, template = _settlement_rows(session, kind, settlement_id)
    document, sheet = _writer(template, model_row=13)
    sheet.set(6, 1, label)  # B7
    sheet.set(7, 1, settlement_id)  # B8

    totals = [_decimal(v.mwst_netto) + _decimal(v.mwst_betrag) for v in vat_rows]
    bar = [_decimal(v.bar_brutto) for v in vat_rows]
    total_brutto = sum(totals, Decimal("0"))
    total_bar = sum(bar, Decimal("0"))
    for offset, value in enumerate((total_brutto, total_bar, total_brutto - total_bar)):
        sheet.set(9 + offset, 1, value)

    line = 13  # Java: totals, one empty row, then the VAT block
    for vat in vat_rows:
        rate = _vat_label(vat.mwst_satz)
        brutto = _decimal(vat.mwst_netto) + _decimal(vat.mwst_betrag)
        for offset, (suffix, value) in enumerate((
            ("MwSt. Brutto:", brutto),
            ("MwSt. Netto:", _decimal(vat.mwst_netto)),
            ("MwSt. Betrag:", _decimal(vat.mwst_betrag)),
        )):
            sheet.set(line + offset, 0, f"{rate} {suffix}")
            sheet.set(line + offset, 1, value)
        line += 4

    if kind == "tag":
        rates = [_decimal(vat.mwst_satz) for vat in vat_rows]
        stornos = dict(_storno_sums(session, row))
        retouren = dict(_retoure_sums(session, row))
        for rate in rates:
            sheet.set(line, 0, f"Storno ({_vat_label(rate)})")
            sheet.set(line, 1, stornos.get(rate, Decimal("0")))
            line += 1
        for rate in rates:
            sheet.set(line, 0, f"Retouren ({_vat_label(rate)})")
            sheet.set(line, 1, retouren.get(rate, Decimal("0")))
            line += 1
        sheet.set(line, 0, "Entnahmen")
        sheet.set(line, 1, _withdrawals(session, row))
        _write_count_protocol(session, sheet, row)

    return ods.save(document)


def _storno_sums(session, settlement) -> list[tuple[float, Decimal]]:
    """VAT totals of the original receipts that were cancelled in this period."""
    storno_von = select(Verkauf.storno_von).where(Verkauf.storno_von.is_not(None))
    rows = session.exec(
        select(VerkaufMwst).where(
            VerkaufMwst.rechnungs_nr.in_(storno_von),
            VerkaufMwst.rechnungs_nr >= settlement.rechnungs_nr_von,
            VerkaufMwst.rechnungs_nr <= settlement.rechnungs_nr_bis,
        )
    ).all()
    sums: dict[Decimal, Decimal] = {}
    for row in rows:
        rate = _decimal(row.mwst_satz)
        sums[rate] = sums.get(rate, Decimal("0")) + _decimal(row.mwst_netto) + _decimal(row.mwst_betrag)
    return sorted(sums.items())


def _retoure_sums(session, settlement) -> list[tuple[float, Decimal]]:
    """Gross sums of returned goods (negative positions, no discount/voucher/Pfand)."""
    details = session.exec(
        select(VerkaufDetails).where(
            VerkaufDetails.rechnungs_nr >= settlement.rechnungs_nr_von,
            VerkaufDetails.rechnungs_nr <= settlement.rechnungs_nr_bis,
            VerkaufDetails.stueckzahl < 0,
        )
    ).all()
    sums: dict[Decimal, Decimal] = {}
    for detail in details:
        sale = session.get(Verkauf, detail.rechnungs_nr)
        if sale is None or sale.storno_von is not None:
            continue
        artikel = session.get(Artikel, detail.artikel_id) if detail.artikel_id else None
        group_id = artikel.produktgruppen_id if artikel else None
        if group_id in INTERNAL_GROUPS:
            continue
        rate = _decimal(detail.mwst_satz)
        sums[rate] = sums.get(rate, Decimal("0")) + _decimal(detail.ges_preis)
    return sorted(sums.items())


def _withdrawals(session, settlement) -> Decimal:
    """Cash withdrawals (Entnahmen) booked between the previous and this settlement."""
    previous = session.exec(
        select(AbrechnungTag).where(AbrechnungTag.id < settlement.id).order_by(AbrechnungTag.id.desc())
    ).first()
    lower = previous.kassenstand_id if previous and previous.kassenstand_id else 0
    upper = settlement.kassenstand_id if settlement.kassenstand_id else 2**32 - 1
    entries = session.exec(
        select(Kassenstand).where(
            Kassenstand.kassenstand_id > lower,
            Kassenstand.kassenstand_id < upper,
            Kassenstand.entnahme == True,  # noqa: E712 - SQL expression
        )
    ).all()
    total = Decimal("0")
    for entry in entries:
        before = session.get(Kassenstand, entry.kassenstand_id - 1)
        if before is not None:
            total += _decimal(entry.neuer_kassenstand) - _decimal(before.neuer_kassenstand)
    return total


def _write_count_protocol(session, sheet, settlement) -> None:
    """Write the newest count protocol block at the fixed Java row 27."""
    protocol = session.exec(
        select(Zaehlprotokoll)
        .where(Zaehlprotokoll.abrechnung_tag_id == settlement.id)
        .order_by(Zaehlprotokoll.id.desc())
    ).first()
    if protocol is None:
        return
    details = session.exec(
        select(ZaehlprotokollDetails)
        .where(ZaehlprotokollDetails.zaehlprotokoll_id == protocol.id)
        .order_by(ZaehlprotokollDetails.einheit)
    ).all()
    counted = sum((_decimal(d.einheit) * d.anzahl for d in details), Decimal("0"))

    line = 27
    sheet.set(line, 0, "Zählprotokoll:")
    sheet.set(line, 1, protocol.zeitpunkt.strftime("%d.%m.%Y %H:%M"))
    line += 1
    for detail in details:
        sheet.set(line, 0, f"{_money_label(detail.einheit)} {CURRENCY}, Anzahl:")
        sheet.set(line, 1, detail.anzahl)
        sheet.set(line, 2, "Wert:")
        sheet.set(line, 3, _decimal(detail.einheit) * detail.anzahl)
        line += 1
    sheet.set(line, 0, "Zähl-Kassenstand:")
    sheet.set(line, 1, counted)
    line += 1
    if settlement.kassenstand_id is not None:
        target = session.get(Kassenstand, settlement.kassenstand_id)
        if target is not None:
            soll = _decimal(target.neuer_kassenstand)
            sheet.set(line, 0, "Soll-Kassenstand:")
            sheet.set(line, 1, soll)
            line += 1
            sheet.set(line, 0, "Differenz")
            sheet.set(line, 1, counted - soll)
            line += 1
            after = session.exec(
                select(Kassenstand).where(
                    Kassenstand.kassenstand_id > settlement.kassenstand_id,
                    Kassenstand.manuell == True,  # noqa: E712 - SQL expression
                    Kassenstand.entnahme == False,  # noqa: E712 - SQL expression
                    Kassenstand.kommentar == "Tagesabschluss",
                ).order_by(Kassenstand.kassenstand_id)
            ).first()
            if after is not None:
                sheet.set(line, 0, "Bar-Einnahmen")
                sheet.set(line, 1, counted - _decimal(after.neuer_kassenstand))
                line += 1
    sheet.set(line, 0, "Kommentar")
    sheet.set(line, 1, protocol.kommentar)
