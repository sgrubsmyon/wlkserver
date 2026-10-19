"""Advanced storno (refund) logic."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import HTTPException
from sqlmodel import Session, select

from ..models import Verkauf, VerkaufDetails, VerkaufMwst
from .vat_calculator import _to_decimal


def can_storno(verkauf: Verkauf, session: Optional[Session] = None) -> tuple[bool, str]:
    if verkauf is None:
        return False, "Verkauf not found"
    if getattr(verkauf, "storno_von", None) is not None:
        return False, "Cannot storno a storno"
    if session is not None:
        existing = session.exec(select(Verkauf).where(Verkauf.storno_von == verkauf.rechnungs_nr)).first()
        if existing is not None:
            return False, "This Verkauf already has a storno"
    return True, ""


def validate_storno(*args, **kwargs):
    session = kwargs.get('session')
    rechnungs_nr = kwargs.get('rechnungs_nr')
    if session is None or rechnungs_nr is None:
        if len(args) >= 2:
            if isinstance(args[0], Session):
                session, rechnungs_nr = args[0], args[1]
            elif isinstance(args[1], Session):
                rechnungs_nr, session = args[0], args[1]
            else:
                rechnungs_nr, session = args[0], args[1]
    original = session.get(Verkauf, rechnungs_nr)
    if not original:
        raise HTTPException(status_code=404, detail="Original Verkauf not found")
    ok, msg = can_storno(original, session)
    if not ok:
        raise HTTPException(status_code=400, detail=msg)
    return original

def invert_detail(detail: VerkaufDetails, storno_rechnungs_nr: int) -> VerkaufDetails:
    inv = VerkaufDetails(
        position=detail.position,
        stueckzahl=-detail.stueckzahl,
        ges_preis=-detail.ges_preis if detail.ges_preis is not None else None,
        mwst_satz=detail.mwst_satz,
        rechnungs_nr=storno_rechnungs_nr,
        artikel_id=detail.artikel_id,
        rabatt_id=detail.rabatt_id,
    )
    return inv


def invert_mwst(mwst: VerkaufMwst, storno_rechnungs_nr: int) -> VerkaufMwst:
    inv = VerkaufMwst(
        rechnungs_nr=storno_rechnungs_nr,
        mwst_satz=mwst.mwst_satz,
        mwst_netto=-mwst.mwst_netto,
        mwst_betrag=-mwst.mwst_betrag,
    )
    return inv


def create_storno(*args, **kwargs):
    session = kwargs.get("session")
    rechnungs_nr = kwargs.get("rechnungs_nr")
    if session is None or rechnungs_nr is None:
        if len(args) >= 2:
            if isinstance(args[0], Session):
                session, rechnungs_nr = args[0], args[1]
            elif isinstance(args[1], Session):
                rechnungs_nr, session = args[0], args[1]
            else:
                session, rechnungs_nr = args[0], args[1]
    original = validate_storno(rechnungs_nr, session)
    storno_sale = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=False,
        kunde_gibt=None,
        storno_von=rechnungs_nr,
    )
    storno_sale.rechnungs_nr = None
    session.add(storno_sale)
    session.commit()
    session.refresh(storno_sale)

    for d in original.verkauf_details or []:
        session.add(invert_detail(d, storno_sale.rechnungs_nr))
    for m in original.verkauf_mwst or []:
        session.add(invert_mwst(m, storno_sale.rechnungs_nr))
    session.commit()
    session.refresh(storno_sale)
    return storno_sale


# voucher/installment handling hooks (placeholders for integration)
def handle_storno_voucher(session: Session, original: Verkauf) -> None:
    """Reverse voucher side-effects caused by the sale (best-effort)."""
    from datetime import datetime, timezone
    from ..models import Gutschein, VerkaufDetails
    from sqlmodel import select
    vd_ids = [d.vd_id for d in (original.verkauf_details or []) if d.vd_id is not None]
    if not vd_ids:
        return
    gutscheine = session.exec(
        select(Gutschein).where(Gutschein.gutschein_in_vd_id.in_(vd_ids))
    ).all()
    for g in gutscheine:
        # Cancel the voucher by creating a new entry with restbetrag 0
        new_g = Gutschein(
            gutschein_nr=g.gutschein_nr,
            datum=datetime.now(timezone.utc),
            gutschein_in_vd_id=g.gutschein_in_vd_id,
            einloesung_in_vd_id=None,
            restbetrag=0.0,
        )
        new_g.gutschein_id = None
        session.add(new_g)
    if gutscheine:
        session.commit()


def handle_storno_installment(session: Session, original: Verkauf) -> None:
    """Reverse installment (Anzahlung) handling: resolve open installments against storno."""
    from datetime import datetime, timezone
    from ..models import Anzahlung
    from sqlmodel import select
    open_anz = session.exec(
        select(Anzahlung).where(
            Anzahlung.anzahlung_in_rech_nr == original.rechnungs_nr,
            Anzahlung.aufloesung_in_rech_nr.is_(None),
        )
    ).all()
    # Find the storno sale created for original
    from ..models import Verkauf
    storno_sale = session.exec(
        select(Verkauf).where(Verkauf.storno_von == original.rechnungs_nr)
    ).first()
    target_nr = storno_sale.rechnungs_nr if storno_sale is not None else original.rechnungs_nr
    for a in open_anz:
        new_a = Anzahlung(
            datum=datetime.now(timezone.utc),
            anzahlung_in_rech_nr=a.anzahlung_in_rech_nr,
            aufloesung_in_rech_nr=target_nr,
        )
        new_a.anzahlung_id = None
        session.add(new_a)
    if open_anz:
        session.commit()


create_storno_sale = create_storno
storno_verkauf_logic = create_storno


__all__ = [
    "can_storno",
    "validate_storno",
    "invert_detail",
    "invert_mwst",
    "create_storno",
    "create_storno_sale",
    "storno_verkauf_logic",
    "handle_storno_voucher",
    "handle_storno_installment",
]
