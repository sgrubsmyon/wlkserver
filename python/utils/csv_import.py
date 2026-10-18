"""CSV import utilities."""
from __future__ import annotations

import csv
import io
from typing import Any, List

from sqlmodel import Session

from ..models import Artikel


def import_artikel_from_csv(content: str, session: Session) -> List[Artikel]:
    reader = csv.DictReader(io.StringIO(content))
    created = []
    for row in reader:
        artikel = Artikel(
            artikel_nr=row.get("artikel_nr") or row.get("nr"),
            artikel_name=row.get("artikel_name") or row.get("name"),
            vk_preis=_float(row.get("vk_preis")),
        )
        session.add(artikel)
        created.append(artikel)
    session.commit()
    for a in created:
        session.refresh(a)
    return created


def import_bestellung_from_csv(content: str, session: Session) -> List[Any]:
    # placeholder: no full parsing
    return []


def _float(v):
    try:
        return float(v) if v not in (None, "") else None
    except Exception:
        return None
