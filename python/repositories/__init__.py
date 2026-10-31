"""Read-side queries that several services need.

Only queries used in more than one place live here; CRUD and single-table reads
stay in the service that owns them.
"""
from sqlmodel import Session, func, select

from ..models import Gutschein, Kassenstand, Verkauf


def latest_kassenstand(session: Session, for_update: bool = False) -> Kassenstand | None:
    """The current ledger entry (`FOR UPDATE` when a balance is about to change)."""
    selection = select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())
    if for_update:
        selection = selection.with_for_update()
    return session.exec(selection).first()


def open_receipt_range(session: Session, after_nr: int) -> tuple[int, int] | None:
    """First and last receipt number greater than `after_nr` (None when empty)."""
    first, last = session.exec(
        select(func.min(Verkauf.rechnungs_nr), func.max(Verkauf.rechnungs_nr)).where(
            Verkauf.rechnungs_nr > after_nr
        )
    ).one()
    if first is None:
        return None
    return first, last


def sales_between(session: Session, von_nr: int, bis_nr: int) -> list[Verkauf]:
    """Receipts of a receipt-number range."""
    return session.exec(
        select(Verkauf).where(
            Verkauf.rechnungs_nr >= von_nr, Verkauf.rechnungs_nr <= bis_nr
        )
    ).all()


def voucher_rows(session: Session, gutschein_nr: int, for_update: bool = False) -> list[Gutschein]:
    """All rows of the append-only voucher family, oldest first."""
    selection = (
        select(Gutschein)
        .where(Gutschein.gutschein_nr == gutschein_nr)
        .order_by(Gutschein.gutschein_id)
    )
    if for_update:
        selection = selection.with_for_update()
    return session.exec(selection).all()


def storno_of(session: Session, rechnungs_nr: int) -> Verkauf | None:
    """The storno receipt that reverses `rechnungs_nr`, if one exists."""
    return session.exec(
        select(Verkauf).where(Verkauf.storno_von == rechnungs_nr)
    ).first()
