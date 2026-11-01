"""TSE signing of a finished receipt (Java `WeltladenTSE.finishTransaction`)."""
import logging
from decimal import Decimal, ROUND_HALF_UP

from ..config import training_mode
from ..models import TSETransaction
from ..utils.tse_client import tse_client
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


def render_process_data(gross_by_rate, ec_zahlung: bool, training: bool = False) -> str:
    """`Beleg^<gross per VAT rate>^<amount>:<Bar|Unbar>` (Java `renderProcessData`)."""
    gross = {_to_decimal(rate): _cents(value) for rate, value in (gross_by_rate or {}).items()}
    taxes = "_".join(f"{gross.get(rate, Decimal('0')):.2f}" for rate in VAT_RATES)
    total = sum(gross.values(), Decimal("0"))
    payment = f"{_cents(total):.2f}:{'Unbar' if ec_zahlung else 'Bar'}"
    return f"AVTraining^{taxes}^{payment}" if training else f"Beleg^{taxes}^{payment}"


def sign_receipt(session, rechnungs_nr: int, gross_by_rate, ec_zahlung: bool, user_id=None) -> None:
    """Sign one receipt and store its `tse_transaction` row.

    Best-effort like Java: a missing or failing TSE must not block the receipt;
    the problem is recorded in `tse_error`.
    """
    training = training_mode()
    process_data = render_process_data(gross_by_rate, ec_zahlung, training)
    try:
        signed = tse_client.create_transaction(
            process_type=PROCESS_TYPE, process_data=process_data, training=training
        )
        session.add(TSETransaction(
            transaction_number=signed.get("transaction_number"),
            rechnungs_nr=rechnungs_nr,
            training=training,
            transaction_start=signed.get("transaction_start"),
            transaction_end=signed.get("transaction_end"),
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


__all__ = ["PROCESS_TYPE", "VAT_RATES", "render_process_data", "sign_receipt"]
