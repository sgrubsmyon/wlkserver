"""DSFinV-K export (port of the Java POS `kasse/DSFinVKCSV.java`).

The Java POS writes a subset of the DSFinV-K modules after every Tagesabschluss:
the Stammdaten (`cashpointclosing.csv`, `location.csv`, `cashregister.csv`,
`slaves.csv`, `pa.csv`, `vat.csv`, `tse.csv`), the Kassenabschluss
(`businesscases.csv`) and the TSE transactions (`transactions_tse.csv`).
`build_dsfinvk_files()` produces the same files in memory and
`export_dsfinvk()` bundles them with the official `index.xml` and DTD as a ZIP.
`write_dsfinvk_export()` additionally writes the archive to
`DSFINVK_EXPORT_DIR` after a settlement, mirroring the Java POS.

The Stammdaten are taken from `DSFINVK_*` environment variables (the defaults
match `BaseClass` in the Java POS); empty values are exported as empty fields,
so a deployment must set at least the shop's name, address and tax numbers.
"""
from __future__ import annotations

import io
import logging
import os
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from functools import lru_cache
from pathlib import Path

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import (
    AbrechnungTag,
    AbrechnungTagMwst,
    AbrechnungTagTse,
    Kassenstand,
    Mwst,
    Pfand,
    TSETransaction,
    Verkauf,
)
from .sale_workflow import SPECIAL_ARTIKEL
from .vat_calculator import _to_decimal

logger = logging.getLogger(__name__)

ASSETS = Path(__file__).resolve().parents[1] / "assets" / "dsfinvk"

CENT = Decimal("0.01")
RABATT_NRS = {SPECIAL_ARTIKEL["rabatt"], SPECIAL_ARTIKEL["rechnung_rabatt"]}
AUFSCHLAG_NR = SPECIAL_ARTIKEL["preisanpassung"]
GUTSCHEIN_KAUF_NR = "GUTSCHEIN"
GUTSCHEIN_EINLOESUNG_NR = SPECIAL_ARTIKEL["gutschein_einloesung"]

# GV_Typ buckets in the order the Java POS writes them. The Java POS also has
# (unused) comments for Anzahlungseinstellung/-aufloesung, Geldtransit and
# DifferenzSollIst, so they are not written here either.
GV_TYPES = (
    "Pfand",
    "PfandRueckzahlung",
    "Rabatt",
    "Aufschlag",
    "MehrzweckgutscheinKauf",
    "MehrzweckgutscheinEinloesung",
)

_MISSING = object()

_DEFAULTS = {
    "Z_KASSE_ID": "YLUE036019",
    "TAXONOMIE_VERSION": "2.2",
    "KASSE_SW_BRAND": "Weltladenkasse",
    "KASSE_BASISWAEH_CODE": "EUR",
    "TERMINAL_SW_BRAND": "Weltladenkasse",
}
_CONFIG_KEYS = (
    "Z_KASSE_ID", "TAXONOMIE_VERSION",
    "NAME", "STRASSE", "PLZ", "ORT", "LAND", "STNR", "USTID",
    "LOC_NAME", "LOC_STRASSE", "LOC_PLZ", "LOC_ORT", "LOC_LAND", "LOC_USTID",
    "KASSE_BRAND", "KASSE_MODELL", "KASSE_SERIENNR", "KASSE_SW_BRAND",
    "KASSE_SW_VERSION", "KASSE_BASISWAEH_CODE",
    "TERMINAL_ID", "TERMINAL_BRAND", "TERMINAL_MODELL", "TERMINAL_SERIENNR",
    "TERMINAL_SW_BRAND", "TERMINAL_SW_VERSION",
)


@dataclass(frozen=True)
class _Column:
    name: str
    numeric: bool
    max_length: int | None
    accuracy: int | None


@dataclass(frozen=True)
class _Table:
    delimiter: str
    record: str
    encapsulator: str
    decimal: str
    grouping: str
    columns: tuple[_Column, ...]


def _int_or_none(value: str | None) -> int | None:
    return int(value) if value else None


@lru_cache(maxsize=1)
def _schema() -> dict[str, _Table]:
    """Per-file CSV settings and column order from the official `index.xml`."""
    root = ET.parse(ASSETS / "index.xml").getroot()
    tables: dict[str, _Table] = {}
    for table in root.iter("Table"):
        variable = table.find("VariableLength")
        columns = tuple(
            _Column(
                c.findtext("Name"),
                c.find("Numeric") is not None,
                _int_or_none(c.findtext("MaxLength")),
                _int_or_none(c.findtext("Numeric/Accuracy")),
            )
            for c in variable.iter("VariableColumn")
        )
        tables[table.findtext("URL")] = _Table(
            delimiter=variable.findtext("ColumnDelimiter"),
            record=variable.findtext("RecordDelimiter"),
            encapsulator=variable.findtext("TextEncapsulator"),
            decimal=table.findtext("DecimalSymbol"),
            grouping=table.findtext("DigitGroupingSymbol"),
            columns=columns,
        )
    return tables


def _config() -> dict[str, str]:
    return {key: os.getenv("DSFINVK_" + key, _DEFAULTS.get(key, "")) for key in _CONFIG_KEYS}


def _format_number(value, accuracy: int, table: _Table) -> str:
    number = _to_decimal(value)
    if number is None:
        return ""
    quantized = number.quantize(Decimal(1).scaleb(-accuracy), rounding=ROUND_HALF_UP)
    text = f"{quantized:,.{accuracy}f}"
    return text.replace(",", "\x00").replace(".", table.decimal).replace("\x00", table.grouping)


def _render(table: _Table, rows: list[dict]) -> bytes:
    """Render one CSV like Java `DSFinVKCSV.writeToCSV` (header + data rows)."""
    header = table.delimiter.join(c.name for c in table.columns)
    lines = [header]
    for row in rows:
        cells = []
        for column in table.columns:
            value = row.get(column.name, _MISSING)
            if value is _MISSING or value is None:
                cells.append("")
            elif column.numeric:
                if column.accuracy:
                    cells.append(_format_number(value, column.accuracy, table))
                else:
                    cells.append(str(value))
            else:
                text = str(value)
                if column.max_length is not None:
                    text = text[:column.max_length]
                text = text.replace(table.encapsulator, table.encapsulator * 2)
                cells.append(table.encapsulator + text + table.encapsulator)
        lines.append(table.delimiter.join(cells))
    return (table.record.join(lines) + table.record).encode("utf-8")


def _round2(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def _classify(detail, pfand_artikel_ids: set) -> str | None:
    """GV_Typ bucket of a sale position, mirroring the Java SQL conditions."""
    quantity = detail.stueckzahl or 0
    if detail.artikel_id in pfand_artikel_ids:
        if quantity > 0:
            return "Pfand"
        if quantity < 0:
            return "PfandRueckzahlung"
        return None
    artikel_nr = detail.artikel.artikel_nr if detail.artikel is not None else None
    if artikel_nr in RABATT_NRS or (
        detail.rabatt_id is not None and (detail.ges_preis or 0) < 0
    ):
        return "Rabatt"
    if artikel_nr == AUFSCHLAG_NR:
        return "Aufschlag"
    if artikel_nr == GUTSCHEIN_KAUF_NR:
        return "MehrzweckgutscheinKauf"
    if artikel_nr == GUTSCHEIN_EINLOESUNG_NR:
        return "MehrzweckgutscheinEinloesung"
    return None


def _case(zvalues: dict, gv_typ: str, brutto, netto, ust, ust_schluessel) -> dict:
    return {
        **zvalues,
        "GV_TYP": gv_typ,
        "GV_NAME": gv_typ,
        "AGENTUR_ID": 0,
        "UST_SCHLUESSEL": ust_schluessel,
        "Z_UMS_BRUTTO": brutto,
        "Z_UMS_NETTO": netto,
        "Z_UST": ust,
    }


def _ust_key(rate, mwst_by_rate: dict):
    mwst = mwst_by_rate.get(rate)
    return mwst.dsfinvk_ust_schluessel if mwst is not None else None


def _sorted_totals(totals: dict, mwst_by_rate: dict):
    def key(rate):
        ust_key = _ust_key(rate, mwst_by_rate)
        return (ust_key is None, ust_key if ust_key is not None else 0, rate)

    return [(rate, totals[rate]) for rate in sorted(totals, key=key)]


def _opening_balance(session: Session, previous: AbrechnungTag | None) -> Decimal:
    """First manual cash-in after the previous settlement (Java "Anfangsbestand")."""
    selection = select(Kassenstand).where(
        Kassenstand.rechnungs_nr.is_(None),
        Kassenstand.manuell == True,  # noqa: E712 - SQL expression
        Kassenstand.entnahme == False,  # noqa: E712
    )
    if previous is not None and previous.kassenstand_id is not None:
        selection = selection.where(Kassenstand.kassenstand_id > previous.kassenstand_id)
    row = session.exec(selection.order_by(Kassenstand.kassenstand_id)).first()
    if row is None:
        return Decimal("150.00")  # Java fallback
    return _to_decimal(row.neuer_kassenstand) or Decimal("150.00")


def _parse_tse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        try:
            parsed = datetime.strptime(value[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _tse_row(zvalues: dict, tse: AbrechnungTagTse | None) -> dict:
    if tse is None:
        return {}
    row = dict(zvalues)
    for source, target in (
        ("tse_id", "TSE_ID"),
        ("tse_serial", "TSE_SERIAL"),
        ("tse_sig_algo", "TSE_SIG_ALGO"),
        ("tse_time_format", "TSE_ZEITFORMAT"),
        ("tse_pd_encoding", "TSE_PD_ENCODING"),
        ("tse_public_key", "TSE_PUBLIC_KEY"),
        ("tse_cert_i", "TSE_ZERTIFIKAT_I"),
        ("tse_cert_ii", "TSE_ZERTIFIKAT_II"),
    ):
        value = getattr(tse, source)
        if value is not None:
            row[target] = value
    return row


def build_dsfinvk_files(session: Session, abrechnung_tag_id: int) -> dict[str, bytes]:
    """Build the DSFinV-K CSV files of one Tagesabschluss (filename -> bytes)."""
    at = session.get(AbrechnungTag, abrechnung_tag_id)
    if at is None:
        raise HTTPException(status_code=404, detail="AbrechnungTag not found")

    previous = session.exec(
        select(AbrechnungTag)
        .where(AbrechnungTag.id < abrechnung_tag_id)
        .order_by(AbrechnungTag.id.desc())
    ).first()
    cfg = _config()
    zvalues = {
        "Z_KASSE_ID": at.z_kasse_id or cfg["Z_KASSE_ID"],
        "Z_ERSTELLUNG": at.zeitpunkt_real.strftime("%Y-%m-%dT%H:%M:%S"),
        "Z_NR": at.id,
    }

    mwst_rows = session.exec(select(Mwst).order_by(Mwst.dsfinvk_ust_schluessel)).all()
    mwst_by_rate = {_to_decimal(m.mwst_satz): m for m in mwst_rows}
    vat_rows = [
        {
            **zvalues,
            "UST_SCHLUESSEL": mwst.dsfinvk_ust_schluessel,
            "UST_SATZ": (_to_decimal(mwst.mwst_satz) or Decimal("0")) * 100,
            "UST_BESCHR": mwst.dsfinvk_ust_beschr,
        }
        for mwst in mwst_rows
    ]

    settlement_mwst = session.exec(
        select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == abrechnung_tag_id)
    ).all()
    payment_total = sum(
        (_to_decimal(m.mwst_netto) or Decimal("0")) + (_to_decimal(m.mwst_betrag) or Decimal("0"))
        for m in settlement_mwst
    )
    cash_total = sum((_to_decimal(m.bar_brutto) or Decimal("0")) for m in settlement_mwst)

    closing = {
        **zvalues,
        "Z_BUCHUNGSTAG": at.zeitpunkt.date().isoformat(),
        "TAXONOMIE_VERSION": cfg["TAXONOMIE_VERSION"],
        "Z_START_ID": str(at.rechnungs_nr_von),
        "Z_ENDE_ID": str(at.rechnungs_nr_bis),
        "NAME": cfg["NAME"],
        "STRASSE": cfg["STRASSE"],
        "PLZ": cfg["PLZ"],
        "ORT": cfg["ORT"],
        "LAND": cfg["LAND"],
        "STNR": cfg["STNR"],
        "USTID": cfg["USTID"],
        "Z_SE_ZAHLUNGEN": payment_total,
        "Z_SE_BARZAHLUNGEN": cash_total,
    }
    location = {
        **zvalues,
        "LOC_NAME": cfg["LOC_NAME"],
        "LOC_STRASSE": cfg["LOC_STRASSE"],
        "LOC_PLZ": cfg["LOC_PLZ"],
        "LOC_ORT": cfg["LOC_ORT"],
        "LOC_LAND": cfg["LOC_LAND"],
        "LOC_USTID": cfg["LOC_USTID"],
    }
    cashregister = {
        **zvalues,
        "KASSE_BRAND": cfg["KASSE_BRAND"],
        "KASSE_MODELL": cfg["KASSE_MODELL"],
        "KASSE_SERIENNR": cfg["KASSE_SERIENNR"],
        "KASSE_SW_BRAND": cfg["KASSE_SW_BRAND"],
        "KASSE_SW_VERSION": cfg["KASSE_SW_VERSION"],
        "KASSE_BASISWAEH_CODE": cfg["KASSE_BASISWAEH_CODE"],
        "KEINE_UST_ZUORDNUNG": "0",
    }
    slaves = {
        **zvalues,
        "TERMINAL_ID": cfg["TERMINAL_ID"],
        "TERMINAL_BRAND": cfg["TERMINAL_BRAND"],
        "TERMINAL_MODELL": cfg["TERMINAL_MODELL"],
        "TERMINAL_SERIENNR": cfg["TERMINAL_SERIENNR"],
        "TERMINAL_SW_BRAND": cfg["TERMINAL_SW_BRAND"],
        "TERMINAL_SW_VERSION": cfg["TERMINAL_SW_VERSION"],
    }

    cases = []
    opening = _opening_balance(session, previous)
    zero_rate = mwst_by_rate.get(Decimal("0"))
    cases.append(_case(
        zvalues, "Anfangsbestand", opening, opening, Decimal("0.00"),
        zero_rate.dsfinvk_ust_schluessel if zero_rate is not None else None,
    ))

    sales = session.exec(
        select(Verkauf).where(
            Verkauf.rechnungs_nr >= at.rechnungs_nr_von,
            Verkauf.rechnungs_nr <= at.rechnungs_nr_bis,
        )
    ).all()

    umsatz: dict[Decimal, list[Decimal]] = {}
    for sale in sales:
        for mwst in sale.verkauf_mwst:
            rate = _to_decimal(mwst.mwst_satz) or Decimal("0")
            netto = _to_decimal(mwst.mwst_netto) or Decimal("0")
            betrag = _to_decimal(mwst.mwst_betrag) or Decimal("0")
            totals = umsatz.setdefault(rate, [Decimal("0"), Decimal("0"), Decimal("0")])
            totals[0] += netto + betrag
            totals[1] += netto
            totals[2] += betrag
    for rate, (brutto, netto, betrag) in _sorted_totals(umsatz, mwst_by_rate):
        cases.append(_case(zvalues, "Umsatz", brutto, netto, betrag, _ust_key(rate, mwst_by_rate)))

    pfand_artikel_ids = {
        p.artikel_id for p in session.exec(select(Pfand)).all() if p.artikel_id is not None
    }
    details = [
        (detail, _classify(detail, pfand_artikel_ids))
        for sale in sales
        for detail in sale.verkauf_details
    ]
    for gv_typ in GV_TYPES:
        totals_by_rate: dict[Decimal, list[Decimal]] = {}
        for detail, kind in details:
            if kind != gv_typ:
                continue
            rate = _to_decimal(detail.mwst_satz) or Decimal("0")
            brutto = _to_decimal(detail.ges_preis) or Decimal("0")
            netto = _round2(brutto / (1 + rate))
            ust = _round2(rate * brutto / (1 + rate))
            totals = totals_by_rate.setdefault(
                rate, [Decimal("0"), Decimal("0"), Decimal("0")]
            )
            totals[0] += brutto
            totals[1] += netto
            totals[2] += ust
        for rate, (brutto, netto, ust) in _sorted_totals(totals_by_rate, mwst_by_rate):
            cases.append(_case(
                zvalues, gv_typ, brutto, netto, ust, _ust_key(rate, mwst_by_rate)
            ))

    tse = _tse_row(zvalues, session.get(AbrechnungTagTse, abrechnung_tag_id))

    window_start = previous.zeitpunkt_real if previous is not None else None
    transactions = []
    for tx in session.exec(
        select(TSETransaction).order_by(TSETransaction.transaction_id)
    ).all():
        started = _parse_tse_time(tx.transaction_start)
        if started is None or started > at.zeitpunkt_real:
            continue
        if window_start is not None and started <= window_start:
            continue
        row = {
            "Z_KASSE_ID": zvalues["Z_KASSE_ID"],
            "Z_ERSTELLUNG": zvalues["Z_ERSTELLUNG"],
            "Z_NR": zvalues["Z_NR"],
            "BON_ID": tx.rechnungs_nr,
            "TSE_ID": tse.get("TSE_ID"),
            "TSE_TANR": tx.transaction_number,
            "TSE_TA_START": tx.transaction_start,
            "TSE_TA_ENDE": tx.transaction_end,
            "TSE_TA_VORGANGSART": tx.process_type,
            "TSE_TA_SIGZ": tx.signature_counter,
            "TSE_TA_SIG": tx.signature_base64,
            "TSE_TA_FEHLER": tx.tse_error,
            "TSE_VORGANGSDATEN": tx.process_data,
        }
        transactions.append(row)

    schema = _schema()
    content = {
        "cashpointclosing.csv": [closing],
        "location.csv": [location],
        "cashregister.csv": [cashregister],
        "slaves.csv": [slaves],
        "pa.csv": [],  # Java only writes the header
        "vat.csv": vat_rows,
        "tse.csv": [tse] if tse else [],
        "businesscases.csv": cases,
        "transactions_tse.csv": transactions,
    }
    return {name: _render(schema[name], rows) for name, rows in content.items()}


def export_dsfinvk(session: Session, abrechnung_tag_id: int) -> bytes:
    """Bundle the DSFinV-K files of one settlement as a ZIP archive."""
    files = build_dsfinvk_files(session, abrechnung_tag_id)
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("index.xml", (ASSETS / "index.xml").read_bytes())
        archive.writestr("gdpdu-01-09-2004.dtd", (ASSETS / "gdpdu-01-09-2004.dtd").read_bytes())
        for name, data in files.items():
            archive.writestr(name, data)
    return buffer.getvalue()


def write_dsfinvk_export(session: Session, abrechnung_tag_id: int) -> Path | None:
    """Write the archive to `DSFINVK_EXPORT_DIR` (no-op when unset)."""
    directory = os.getenv("DSFINVK_EXPORT_DIR")
    if not directory:
        return None
    target = Path(directory)
    target.mkdir(parents=True, exist_ok=True)
    path = target / f"dsfinvk_{abrechnung_tag_id}.zip"
    path.write_bytes(export_dsfinvk(session, abrechnung_tag_id))
    return path


__all__ = ["build_dsfinvk_files", "export_dsfinvk", "write_dsfinvk_export", "GV_TYPES"]
