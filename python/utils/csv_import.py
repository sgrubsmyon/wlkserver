"""CSV import utilities."""
from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any, List

from fastapi import HTTPException
from sqlmodel import Session

from ..models import BESTELLUNG_TYPEN, Artikel, Bestellung, BestellungDetails


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
    """Import orders from CSV.

    Rows sharing the same typ/bestell_datum/jahr/kw belong to one order. Each
    row may add a position via artikel_id, stueckzahl and (optional) position;
    rows without artikel_id only import the order header.
    """
    reader = csv.DictReader(io.StringIO(content))
    orders: dict[tuple, Bestellung] = {}
    used_positions: dict[tuple, set[int]] = {}
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
        typ = row.get("typ") or "LM"
        if typ not in BESTELLUNG_TYPEN:
            raise HTTPException(
                status_code=400,
                detail=f"typ must be one of {', '.join(BESTELLUNG_TYPEN)}",
            )
        jahr = _int(row.get("jahr")) or now.year
        kw = _int(row.get("kw")) or 1
        key = (typ, bestell_datum, jahr, kw)

        b = orders.get(key)
        if b is None:
            b = Bestellung(typ=typ, bestell_datum=bestell_datum, jahr=jahr, kw=kw)
            session.add(b)
            session.commit()
            session.refresh(b)
            orders[key] = b
            used_positions[key] = set()
            created.append(b)

        artikel_id = _int(row.get("artikel_id"))
        if artikel_id is None:
            continue
        if not session.get(Artikel, artikel_id):
            raise HTTPException(status_code=400, detail=f"Artikel {artikel_id} not found")
        stueckzahl = _int(row.get("stueckzahl"))
        if stueckzahl is None or stueckzahl < 1:
            raise HTTPException(status_code=400, detail="stueckzahl must be at least 1")
        position = _int(row.get("position")) or len(used_positions[key]) + 1
        if position in used_positions[key]:
            raise HTTPException(status_code=400, detail=f"Duplicate position {position}")
        used_positions[key].add(position)
        session.add(BestellungDetails(
            bestell_nr=b.bestell_nr,
            typ=b.typ,
            position=position,
            artikel_id=artikel_id,
            stueckzahl=stueckzahl,
        ))
    session.commit()
    for b in created:
        session.refresh(b)
    return created