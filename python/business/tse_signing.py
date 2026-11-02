"""TSE signing of a basket (Java `WeltladenTSE.startTransaction`/`finishTransaction`).

A Vorgang is started when the first article is scanned and stays open until the
customer pays (finished with `Kassenbeleg-V1`) or leaves without buying (aborted
with `AVBelegabbruch`). Transactions must not be started and finished at the
same moment: the TSE logs are the audit trail of the cashier process.
"""
import logging
from datetime import datetime, timedelta
from decimal import Decimal, ROUND_HALF_UP

from sqlmodel import Session, select

from ..config import training_mode
from ..models import TSETransaction
from ..utils.tse_client import ABORT_PROCESS_DATA, now_iso, tse_client
from .errors import DomainError, NotFoundError
from .vat_calculator import _to_decimal

logger = logging.getLogger(__name__)

PROCESS_TYPE = "Kassenbeleg-V1"  # Java `WeltladenTSE.defaultProcessType`
# Gross totals in the process data, in DSFinV-K order (Anhang I, S. 110):
# steuer_allgemein, steuer_ermaessigt, steuer_durchschnitt_nr3, -nr1, steuer_null.
VAT_RATES = (Decimal("0.19"), Decimal("0.07"), Decimal("0.107"), Decimal("0.055"), Decimal("0"))


def _cents(value) -> Decimal:
    return (value if isinstance(value, Decimal) else _to_decimal(value) or Decimal("0")).quantize(
        Decimal("0.01"), rounding=ROUND_HALF_UP
    )


def _end_after(start: str | None, end: str | None) -> str | None:
    """TSE_TA_ENDE after TSE_TA_START (DSFinV-K); a transaction spans time."""
    try:
        started = datetime.fromisoformat(start)
    except (TypeError, ValueError):
        return end
    try:
        ended = datetime.fromisoformat(end)
    except (TypeError, ValueError):
        ended = started
    if ended <= started:
        ended = started + timedelta(milliseconds=1)
    return ended.isoformat(timespec="milliseconds")


def render_process_data(gross_by_rate, ec_zahlung: bool, training: bool = False) -> str:
    """`Beleg^<gross per VAT rate>^<amount>:<Bar|Unbar>` (Java `renderProcessData`)."""
    gross = {_to_decimal(rate): _cents(value) for rate, value in (gross_by_rate or {}).items()}
    taxes = "_".join(f"{gross.get(rate, Decimal('0')):.2f}" for rate in VAT_RATES)
    total = sum(gross.values(), Decimal("0"))
    payment = f"{_cents(total):.2f}:{'Unbar' if ec_zahlung else 'Bar'}"
    return f"AVTraining^{taxes}^{payment}" if training else f"Beleg^{taxes}^{payment}"


def open_transactions(session: Session) -> list[TSETransaction]:
    """Transactions started but neither finished nor aborted."""
    return list(session.exec(
        select(TSETransaction).where(
            TSETransaction.transaction_end.is_(None),
            TSETransaction.transaction_number.is_not(None),
        ).order_by(TSETransaction.transaction_id)
    ).all())


def get_open_transaction(session: Session, transaction_id: int) -> TSETransaction:
    row = session.get(TSETransaction, transaction_id)
    if row is None:
        raise NotFoundError(detail="TSETransaction not found")
    if row.transaction_end is not None:
        raise DomainError(detail="TSE transaction is already finished")
    return row


def start_transaction(session: Session, user_id=None) -> TSETransaction:
    """Start the Vorgang of a new basket (first article added to the cart)."""
    # Java `startTransaction()` aborts a leftover transaction before starting.
    for leftover in open_transactions(session):
        abort_transaction(session, leftover.transaction_id)
    started = tse_client.start_transaction()
    row = TSETransaction(
        transaction_number=started.get("transaction_number"),
        training=training_mode(),
        transaction_start=started.get("transaction_start"),
        tse_error=started.get("tse_error"),
        user_id=user_id,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def abort_transaction(session: Session, transaction_id: int) -> TSETransaction:
    """Abort a started transaction: the sale did not happen (`AVBelegabbruch`)."""
    row = get_open_transaction(session, transaction_id)
    if row.transaction_number is None:
        # The Vorgang never reached the TSE; only the times are ours to record.
        ended = {"transaction_end": now_iso()}
    else:
        ended = tse_client.abort_transaction(row.transaction_number, PROCESS_TYPE)
    row.transaction_end = _end_after(row.transaction_start, ended.get("transaction_end"))
    row.signature_counter = ended.get("signature_counter")
    row.signature_base64 = ended.get("signature_base64")
    row.process_type = PROCESS_TYPE
    row.process_data = ABORT_PROCESS_DATA
    row.tse_error = ended.get("tse_error") or row.tse_error
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def sign_receipt(session, rechnungs_nr: int, gross_by_rate, ec_zahlung: bool,
                 user_id=None, transaction_id: int | None = None) -> None:
    """Sign one receipt and store its `tse_transaction` row.

    With `transaction_id` the basket's open transaction is finished. Without it
    a transaction is started and finished in one go (stornos, scripted sales).

    Best-effort like Java: a missing or failing TSE must not block the receipt;
    the problem is recorded in `tse_error`.
    """
    training = training_mode()
    process_data = render_process_data(gross_by_rate, ec_zahlung, training)
    try:
        row = session.get(TSETransaction, transaction_id) if transaction_id is not None else None
        if row is not None:
            finished = tse_client.finish_transaction(
                row.transaction_number, PROCESS_TYPE, process_data
            )
            row.rechnungs_nr = rechnungs_nr
            row.transaction_end = _end_after(row.transaction_start, finished.get("transaction_end"))
            row.process_type = PROCESS_TYPE
            row.process_data = process_data
            row.signature_counter = finished.get("signature_counter")
            row.signature_base64 = finished.get("signature_base64")
            row.tse_error = finished.get("tse_error") or row.tse_error
            row.user_id = row.user_id or user_id
            session.add(row)
        else:
            signed = tse_client.create_transaction(PROCESS_TYPE, process_data, training)
            session.add(TSETransaction(
                transaction_number=signed.get("transaction_number"),
                rechnungs_nr=rechnungs_nr,
                training=training,
                transaction_start=signed.get("transaction_start"),
                transaction_end=_end_after(
                    signed.get("transaction_start"), signed.get("transaction_end")
                ),
                process_type=PROCESS_TYPE,
                signature_counter=signed.get("signature_counter"),
                signature_base64=signed.get("signature_base64"),
                tse_error=signed.get("tse_error"),
                process_data=process_data,
                user_id=user_id,
            ))
        session.commit()
    except Exception:
        session.rollback()
        logger.exception("TSE signing of receipt %s failed", rechnungs_nr)
