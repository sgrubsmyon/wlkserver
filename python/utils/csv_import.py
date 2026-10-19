"""CSV import utilities."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, List

from sqlmodel import Session

from ..models import Artikel, Bestellung


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None


def _int(v):
    try:
        return int(v) if v not in (None, "") else None
    except Exception:
        return None


def _bool(v):
    if v is None or v == "":
        return False
    return str(v).strip().lower() in ("1", "true", "yes", "ja", "x")


def import_artikel_from_csv(content: str, session: Session) -> List[Artikel]:
    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        artikel = Artikel(
            artikel_nr=row.get("artikel_nr") or row.get("nr") or "",
            artikel_name=row.get("artikel_name") or row.get("name") or "",
            kurzname=row.get("kurzname") or row.get("shortname"),
            menge=_float(row.get("menge")),
            einheit=row.get("einheit"),
            barcode=row.get("barcode"),
            herkunft=row.get("herkunft"),
            vpe=_int(row.get("vpe")),
            setgroesse=_int(row.get("setgroesse")) or 1,
            vk_preis=_float(row.get("vk_preis")),
            empf_vk_preis=_float(row.get("empf_vk_preis")),
            ek_rabatt=_float(row.get("ek_rabatt")),
            ek_preis=_float(row.get("ek_preis")),
            variabler_preis=_bool(row.get("variabler_preis")),
            sortiment=_bool(row.get("sortiment")),
            lieferbar=_bool(row.get("lieferbar")),
            beliebtheit=_int(row.get("beliebtheit")) or 0,
            bestand=_int(row.get("bestand")),
        )
        session.add(artikel)
        created.append(artikel)
    session.commit()
    for a in created:
        session.refresh(a)
    return created


def import_bestellung_from_csv(content: str, session: Session) -> List[Bestellung]:
    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        now = datetime.now(timezone.utc)
        bd = row.get("bestell_datum")
        try:
            bestell_datum = datetime.fromisoformat(bd) if bd else now
            if bestell_datum.tzinfo is None:
                bestell_datum = bestell_datum.replace(tzinfo=timezone.utc)
        except Exception:
            bestell_datum = now
        b = Bestellung(
            typ=row.get("typ") or "",
            bestell_datum=bestell_datum,
            jahr=_int(row.get("jahr")) or now.year,
            kw=_int(row.get("kw")) or 1,
        )
        session.add(b)
        created.append(b)
    session.commit()
    for b in created:
        session.refresh(b)
    return created