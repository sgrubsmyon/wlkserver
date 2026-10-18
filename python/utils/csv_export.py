"""CSV export utilities."""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlmodel import Session, select

from ..models import Artikel, AbrechnungTag


def export_artikel_to_csv(session: Session) -> str:
    rows = session.exec(select(Artikel)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["artikel_id", "artikel_nr", "artikel_name", "vk_preis"])
    for a in rows:
        writer.writerow([a.artikel_id, a.artikel_nr, a.artikel_name, a.vk_preis])
    return buf.getvalue()


def export_abrechnung_to_csv(session: Session) -> str:
    rows = session.exec(select(AbrechnungTag)).all()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["abrechnung_tag_id", "datum"])
    for a in rows:
        writer.writerow([getattr(a, "abrechnung_tag_id", None), getattr(a, "datum", None)])
    return buf.getvalue()
