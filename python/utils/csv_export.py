"""CSV export utilities."""
from __future__ import annotations

import csv
import io
from typing import Any

from sqlmodel import Session, select

from ..models import Artikel, AbrechnungTag, AbrechnungTagMwst


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
    writer.writerow(["abrechnung_tag_id", "zeitpunkt", "rechnungs_nr_von", "rechnungs_nr_bis", "kassenstand_id", "mwst_satz", "mwst_netto", "mwst_betrag", "bar_brutto"])
    for a in rows:
        mwsts = session.exec(select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == a.id)).all()
        if mwsts:
            for m in mwsts:
                writer.writerow([a.id, a.zeitpunkt, a.rechnungs_nr_von, a.rechnungs_nr_bis, a.kassenstand_id, m.mwst_satz, m.mwst_netto, m.mwst_betrag, m.bar_brutto])
        else:
            writer.writerow([a.id, a.zeitpunkt, a.rechnungs_nr_von, a.rechnungs_nr_bis, a.kassenstand_id, None, None, None, None])
    return buf.getvalue()
