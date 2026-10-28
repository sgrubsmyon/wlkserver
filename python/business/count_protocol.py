"""Zählprotokoll lifecycle.

Mirrors the Java cashier: the count is recorded while the Tagesabschluss is
submitted (`AbrechnungenTag.insertZaehlprotokoll`), and a later count for the
same settlement deactivates the previous one
(`AbrechnungenTag.setZaehlprotokollInactive`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlmodel import select

from ..models import Zaehlprotokoll, ZaehlprotokollDetails


def insert_count_protocol(session, abrechnung_tag_id: int, payload, user_id=None):
    for old in session.exec(
        select(Zaehlprotokoll).where(
            Zaehlprotokoll.abrechnung_tag_id == abrechnung_tag_id,
            Zaehlprotokoll.aktiv == True,
        )
    ).all():
        old.aktiv = False

    new_zp = Zaehlprotokoll(
        abrechnung_tag_id=abrechnung_tag_id,
        zeitpunkt=payload.zeitpunkt if payload.zeitpunkt is not None else datetime.now(timezone.utc),
        kommentar=payload.kommentar,
        aktiv=payload.aktiv,
        user_id=user_id,
    )
    new_zp.id = None
    session.add(new_zp)
    session.commit()
    session.refresh(new_zp)

    for d in (payload.details or []):
        dd = ZaehlprotokollDetails(
            zaehlprotokoll_id=new_zp.id,
            anzahl=d.anzahl,
            einheit=d.einheit,
        )
        dd.id = None
        session.add(dd)
    if payload.details:
        session.commit()
    return new_zp


__all__ = ["insert_count_protocol"]
