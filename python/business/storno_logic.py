"""Advanced storno (refund) logic."""
from __future__ import annotations

from contextlib import ExitStack
from datetime import datetime, timezone
from typing import Any, Optional

from .errors import DomainError, NotFoundError
from sqlmodel import Session, select

from ..models import (
    AbrechnungTag,
    Verkauf,
    VerkaufDetails,
    VerkaufMwst,
)
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
        settled = session.exec(
            select(AbrechnungTag).where(
                AbrechnungTag.rechnungs_nr_von <= verkauf.rechnungs_nr,
                AbrechnungTag.rechnungs_nr_bis >= verkauf.rechnungs_nr,
            )
        ).first()
        if settled is not None:
            return False, (
                f"Verkauf {verkauf.rechnungs_nr} is already part of the completed "
                f"Tagesabschluss {settled.id} and can no longer be storniert"
            )
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
        raise NotFoundError(detail="Original Verkauf not found")
    ok, msg = can_storno(original, session)
    if not ok:
        raise DomainError(detail=msg)
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
    user_id = kwargs.get("user_id")
    # `commit=False` lets the caller (the storno endpoint) book the whole storno -
    # receipt, voucher/installment reversal and cash payout - in one transaction.
    commit = kwargs.get("commit", True)
    original = validate_storno(rechnungs_nr, session)
    # The storno receipt mirrors the original payment mode (Java
    # HeutigeRechnungen.insertStornoIntoVerkauf: ec_zahlung = !zahlMod.equals("Bar")).
    # Whether the customer is paid out in cash is decided by the caller.
    storno_sale = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=original.ec_zahlung,
        kunde_gibt=None,
        storno_von=rechnungs_nr,
        user_id=user_id,
    )
    storno_sale.rechnungs_nr = None
    session.add(storno_sale)
    try:
        session.flush()  # assigns the new rechnungs_nr without committing
        for d in original.verkauf_details or []:
            session.add(invert_detail(d, storno_sale.rechnungs_nr))
        for m in original.verkauf_mwst or []:
            session.add(invert_mwst(m, storno_sale.rechnungs_nr))
        session.flush()
        if commit:
            session.commit()
            session.refresh(storno_sale)
    except Exception:
        # never leave a half-written storno behind
        session.rollback()
        raise
    return storno_sale


# voucher/installment handling hooks (placeholders for integration)
def handle_storno_voucher(session: Session, original: Verkauf, commit: bool = True) -> None:
    """Reverse voucher side-effects caused by the sale (best-effort)."""
    from datetime import datetime, timezone
    from ..models import (
        Gutschein,
        VerkaufDetails,
    )
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
    if gutscheine and commit:
        session.commit()


def handle_storno_installment(session: Session, original: Verkauf, commit: bool = True) -> None:
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
    if open_anz and commit:
        session.commit()


create_storno_sale = create_storno
storno_verkauf_logic = create_storno


def storno_sale(
    session: Session,
    rechnungs_nr: int,
    user_id=None,
    cash_refund: bool = True,
) -> Verkauf:
    """Storno a receipt: reversing receipt, voucher/installment reversal, cash payout.

    The shop can only refund in cash (Java `HeutigeRechnungen.insertStornoIntoTSE`
    sends "Bar" even for EC sales), so the payout happens for cash and EC sales
    unless `cash_refund` says the card was not charged.
    """
    from .cash_register import (
        KASSENSTAND_LOCK,
        is_training_mode,
        update_kassenstand_for_sale,
    )
    from .voucher_logic import VOUCHER_LOCK

    original = session.get(Verkauf, rechnungs_nr)
    if not original:
        raise NotFoundError(detail="Verkauf not found")
    payout_cash = (not original.ec_zahlung) or cash_refund
    try:
        # The whole storno is one transaction: receipt, voucher and installment
        # reversals, cash payout. Lock order matches the sale (voucher, then
        # Kassenstand).
        with ExitStack() as locks:
            locks.enter_context(VOUCHER_LOCK)
            if payout_cash:
                locks.enter_context(KASSENSTAND_LOCK)
            storno = create_storno(session, rechnungs_nr, user_id=user_id, commit=False)
            handle_storno_voucher(session, original, commit=False)
            handle_storno_installment(session, original, commit=False)
            if payout_cash:
                update_kassenstand_for_sale(
                    session=session,
                    rechnungs_nr=storno.rechnungs_nr,
                    kommentar="Storno",
                    commit=False,
                    lock=False,
                )
            session.commit()
    except Exception:
        session.rollback()
        raise

    # TSE transaction for the storno (best-effort, no TSE in training mode).
    # Signed after the commit: the signature needs the receipt number.
    if not is_training_mode():
        try:
            from ..models import TSETransaction
            from ..utils.tse_client import tse_client

            signed = tse_client.create_transaction(
                process_type="Kassenbeleg-Storno", process_data=None, training=False
            )
            tse = TSETransaction(
                transaction_number=signed.get("transaction_number"),
                rechnungs_nr=storno.rechnungs_nr,
                training=False,
                transaction_start=signed.get("transaction_start"),
                transaction_end=signed.get("transaction_end"),
                process_type="Kassenbeleg-Storno",
                signature_counter=signed.get("signature_counter"),
                signature_base64=signed.get("signature_base64"),
                tse_error=signed.get("tse_error"),
                process_data=None,
                user_id=user_id,
            )
            tse.transaction_id = None
            session.add(tse)
            session.commit()
        except Exception:
            pass
    return storno


__all__ = [
    "can_storno",
    "validate_storno",
    "invert_detail",
    "invert_mwst",
    "create_storno",
    "create_storno_sale",
    "storno_verkauf_logic",
    "storno_sale",
    "handle_storno_voucher",
    "handle_storno_installment",
]
