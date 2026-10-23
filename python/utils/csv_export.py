"""CSV export utilities."""
from __future__ import annotations

import csv
import io
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from sqlmodel import Session, select

from ..models import Artikel, AbrechnungTag, AbrechnungTagMwst, Bestellung, BestellungDetails
from ..business.vat_calculator import calculate_vat, _to_decimal


def export_artikel_to_csv(session: Session) -> str:
    rows = session.exec(select(Artikel)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["artikel_id", "artikel_nr", "artikel_name", "vk_preis"])
    for a in rows:
        writer.writerow([a.artikel_id, a.artikel_nr, a.artikel_name, a.vk_preis])
    return buf.getvalue()


def _order_details(session: Session, typen):
    """Yield (Bestellung, BestellungDetails, Artikel) sorted like the Java export."""
    orders = session.exec(
        select(Bestellung).where(Bestellung.typ.in_(typen)).order_by(Bestellung.bestell_nr)
    ).all()
    for b in orders:
        details = session.exec(
            select(BestellungDetails).where(
                BestellungDetails.bestell_nr == b.bestell_nr,
                BestellungDetails.typ == b.typ,
            )
        ).all()
        rows = []
        for d in details:
            a = session.get(Artikel, d.artikel_id)
            pg = a.produktgruppe if a is not None else None
            key = (
                pg.toplevel_id if pg is not None else 0,
                pg.sub_id or 0 if pg is not None else 0,
                pg.subsub_id or 0 if pg is not None else 0,
                a.artikel_name if a is not None else "",
            )
            rows.append((key, d, a))
        rows.sort(key=lambda r: r[0])
        for _, d, a in rows:
            yield b, d, a


def _mwst_satz(artikel: Artikel | None):
    if artikel is None or artikel.produktgruppe is None or artikel.produktgruppe.mwst is None:
        return None
    return artikel.produktgruppe.mwst.mwst_satz


def export_bestellung_to_csv(session: Session, typen=("LM", "KHW")) -> str:
    """Order export like the Java POS: one row per position, VK prices."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "bestell_nr", "typ", "bestell_datum", "jahr", "kw", "position",
        "lieferant", "artikel_nr", "artikel_name", "vpe",
        "vk_preis", "ek_preis", "mwst_satz", "stueckzahl",
    ])
    for b, d, a in _order_details(session, typen):
        lieferant = a.lieferant if a is not None else None
        # Java uses the recommended VK price when present, else the actual one
        vk_preis = None
        if a is not None:
            vk_preis = a.empf_vk_preis if a.empf_vk_preis is not None else a.vk_preis
        writer.writerow([
            b.bestell_nr, b.typ, b.bestell_datum.isoformat(), b.jahr, b.kw, d.position,
            lieferant.lieferant_name if lieferant is not None else None,
            a.artikel_nr if a is not None else None,
            a.artikel_name if a is not None else None,
            a.vpe if a is not None else None,
            vk_preis,
            a.ek_preis if a is not None else None,
            _mwst_satz(a),
            d.stueckzahl,
        ])
    return buf.getvalue()


def export_inventur_to_csv(session: Session, typ: str = "IVT") -> str:
    """Inventory export like the Java POS: EK valuation per position."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "bestell_nr", "typ", "jahr", "lieferant", "artikel_nr", "artikel_name",
        "vk_preis", "empf_vk_preis", "setgroesse", "ek_rabatt_prozent",
        "ek_preis_set", "ek_preis_stueck", "mwst_prozent",
        "netto_stueck", "mwst_stueck", "stueckzahl",
        "netto_gesamt", "mwst_gesamt", "ek_brutto_gesamt", "vk_brutto_gesamt",
    ])
    cent = Decimal("0.01")
    for b, d, a in _order_details(session, (typ,)):
        lieferant = a.lieferant if a is not None else None
        setgroesse = (a.setgroesse or 1) if a is not None else None
        ek_preis_set = _to_decimal(a.ek_preis) if a is not None else None
        mwst = _to_decimal(_mwst_satz(a))
        vk_preis = _to_decimal(a.vk_preis) if a is not None else None
        empf_vk_preis = _to_decimal(a.empf_vk_preis) if a is not None else None
        ek_rabatt = _to_decimal(a.ek_rabatt) if a is not None else None
        stueckzahl = Decimal(str(d.stueckzahl))

        ek_preis = netto_stueck = mwst_stueck = None
        netto_gesamt = mwst_gesamt = ek_brutto_gesamt = None
        if ek_preis_set is not None and setgroesse:
            ek_preis = (ek_preis_set / Decimal(str(setgroesse))).quantize(cent, rounding=ROUND_HALF_UP)
            mwst_stueck = calculate_vat(ek_preis, mwst or 0)
            netto_stueck = ek_preis - mwst_stueck
            ek_brutto_gesamt = (ek_preis * stueckzahl).quantize(cent, rounding=ROUND_HALF_UP)
            mwst_gesamt = (mwst_stueck * stueckzahl).quantize(cent, rounding=ROUND_HALF_UP)
            netto_gesamt = (netto_stueck * stueckzahl).quantize(cent, rounding=ROUND_HALF_UP)
        vk_brutto_gesamt = (
            (vk_preis * stueckzahl).quantize(cent, rounding=ROUND_HALF_UP)
            if vk_preis is not None else None
        )
        writer.writerow([
            b.bestell_nr, b.typ, b.jahr,
            lieferant.lieferant_kurzname if lieferant is not None else None,
            a.artikel_nr if a is not None else None,
            a.artikel_name if a is not None else None,
            vk_preis, empf_vk_preis, setgroesse,
            (ek_rabatt * 100) if ek_rabatt is not None else None,
            ek_preis_set, ek_preis,
            (mwst * 100) if mwst is not None else None,
            netto_stueck, mwst_stueck, d.stueckzahl,
            netto_gesamt, mwst_gesamt, ek_brutto_gesamt, vk_brutto_gesamt,
        ])
    return buf.getvalue()


def export_abrechnung_to_csv(session: Session) -> str:
    rows = session.exec(select(AbrechnungTag)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["abrechnung_tag_id", "zeitpunkt", "rechnungs_nr_von", "rechnungs_nr_bis", "kassenstand_id", "mwst_satz", "mwst_netto", "mwst_betrag", "bar_brutto"])
    for a in rows:
        mwsts = session.exec(select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == a.id)).all()
        if mwsts:
            for m in mwsts:
                writer.writerow([a.id, a.zeitpunkt, a.rechnungs_nr_von, a.rechnungs_nr_bis, a.kassenstand_id, m.mwst_satz, m.mwst_netto, m.mwst_betrag, m.bar_brutto])
        else:
            writer.writerow([a.id, a.zeitpunkt, a.rechnungs_nr_von, a.rechnungs_nr_bis, a.kassenstand_id, None, None, None, None])
    return buf.getvalue()
