"""Daily settlement (Tagesabschluss) use case."""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..models import (
    AbrechnungJahr,
    AbrechnungJahrMwst,
    AbrechnungMonat,
    AbrechnungMonatMwst,
    AbrechnungTag,
    AbrechnungTagMwst,
    AbrechnungTagTse,
    Kassenstand,
    Mwst,
    TSETransaction,
)
from ..schemas import (
    AbrechnungTagCreate,
    AbrechnungTagPublic,
)
from .cash_register import aggregate_period, is_training_mode, open_period_range
from .count_protocol import insert_count_protocol
from .errors import DomainError, NotFoundError
from .vat_calculator import get_all_current_mwst_values_by_id

logger = logging.getLogger(__name__)


def last_settlement(session: Session) -> AbrechnungTag | None:
    return session.exec(select(AbrechnungTag).order_by(AbrechnungTag.id.desc())).first()


def _configured_tse_id() -> int | None:
    """`bc.TSE_ID` of the Java POS: the TSE number stored in `abrechnung_tag_tse`."""
    value = os.getenv("TSE_ID")
    if not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _last_settled_tx_number(session: Session, last: AbrechnungTag | None) -> int:
    """TX number of the previous settlement's last receipt (Java `previousLastTxNumber`).

    Used as the start of the fallback export by transaction number. Java also
    returns 1 when the lookup is empty (which then starts at TX 2); we start at
    TX 1 instead so no transaction is skipped.
    """
    if last is None:
        return 0
    row = session.exec(
        select(TSETransaction)
        .where(TSETransaction.rechnungs_nr == last.rechnungs_nr_bis)
        .order_by(TSETransaction.transaction_id.desc())
    ).first()
    if row is None or row.transaction_number is None:
        return 0
    return row.transaction_number


def invalidate_period_settlements(session: Session, zeitpunkt: datetime) -> None:
    """Drop month/year settlements covering a (re)opened daily settlement.

    Mirrors Java `AbrechnungenTag.deleteAbrechnungIfNeedBe()`: a backdated daily
    settlement makes the enclosing month and year settlements outdated, so they
    must be recreated by the next `POST /abrechnung/monat|jahr`. The caller owns
    the transaction.
    """
    month = zeitpunkt.date().replace(day=1)
    for row in session.exec(
        select(AbrechnungMonat).where(AbrechnungMonat.monat == month)
    ).all():
        for m in session.exec(
            select(AbrechnungMonatMwst).where(AbrechnungMonatMwst.id == row.id)
        ).all():
            session.delete(m)
        session.delete(row)
    for row in session.exec(
        select(AbrechnungJahr).where(AbrechnungJahr.jahr == zeitpunkt.year)
    ).all():
        for m in session.exec(
            select(AbrechnungJahrMwst).where(AbrechnungJahrMwst.id == row.id)
        ).all():
            session.delete(m)
        session.delete(row)
    session.flush()


def _export_tse_log(session: Session, last: AbrechnungTag | None, prev_sig: int) -> int | None:
    """Incremental TSE export by signature counter, falling back to the TX range.

    Mirrors Java `AbrechnungenTag.exportTSELog()`. Returns the counter *after* the
    export (Java `lastSigCounter = tse.getSignatureCounter()`), which is where the
    next settlement continues.
    """
    if is_training_mode():  # Java: no TSE exports in training mode
        return None
    try:
        from ..utils.tse_client import tse_client

        if not tse_client.export_partial(last_excluded_signature_counter=prev_sig):
            tse_client.export_partial(
                start_tx_number=_last_settled_tx_number(session, last) + 1
            )
        return tse_client.get_signature_counter()
    except Exception:
        logger.exception("TSE export for the Tagesabschluss failed")
        return None


def create_daily_settlement(
    session: Session,
    payload: AbrechnungTagCreate | None = None,
    user_id=None,
) -> AbrechnungTagPublic:
    """Settle the open period and return the created Tagesabschluss.

    Includes the incremental TSE export, the month/year invalidation, the count
    protocol and the DSFinV-K file write, like Java `insertTagesAbrechnung`.
    """
    p = payload or AbrechnungTagCreate()
    now = datetime.now(timezone.utc)
    last = last_settlement(session)

    if p.rechnungs_nr_von is not None and p.rechnungs_nr_bis is not None:
        von, bis = p.rechnungs_nr_von, p.rechnungs_nr_bis
    else:
        period = open_period_range(session)
        if period is None:
            raise DomainError(detail="No sales to settle")
        von, bis = period

    agg = aggregate_period(session, von, bis)
    sales = agg["sales"]
    if not sales:
        raise DomainError(detail="No sales in range")
    mwst_map = agg["mwst_map"]

    # Link the settlement to the current Kassenstand entry (Java
    # AbrechnungenTag.insertTagesAbrechnung uses the highest kassenstand_id).
    # A closing balance is not invented here: the cashier records the counted cash
    # as a manual Kassenstand entry beforehand.
    ks_id = p.kassenstand_id
    if ks_id is not None and not session.get(Kassenstand, ks_id):
        raise DomainError(detail="Kassenstand not found")
    if ks_id is None:
        last_ks = session.exec(
            select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())
        ).first()
        ks_id = last_ks.kassenstand_id if last_ks is not None else None

    prev_sig = p.last_tse_sig_counter
    if prev_sig is None and last is not None:
        prev_sig = last.last_tse_sig_counter
    if prev_sig is None:
        prev_sig = 0
    last_sig = _export_tse_log(session, last, prev_sig)
    if p.last_tse_sig_counter is not None:
        last_sig = p.last_tse_sig_counter  # explicit override (scripts/manual export)

    at = AbrechnungTag(
        z_kasse_id=p.z_kasse_id or "1",
        zeitpunkt=p.zeitpunkt or now,
        zeitpunkt_real=p.zeitpunkt_real or now,
        kassenstand_id=ks_id,
        rechnungs_nr_von=von,
        rechnungs_nr_bis=bis,
        last_tse_sig_counter=last_sig,
        user_id=user_id,
    )
    at.id = None
    try:
        # The settlement, its VAT rows, the TSE status row, the reopened month/year
        # and the count protocol are one transaction: no partial settlement.
        session.add(at)
        session.flush()

        for satz, vals in mwst_map.items():
            session.add(AbrechnungTagMwst(
                id=at.id,
                mwst_satz=satz,
                mwst_netto=vals["netto"],
                mwst_betrag=vals["betrag"],
                bar_brutto=vals["bar"],
            ))

        # One TSE status row per settlement (Java
        # AbrechnungenTag.insertTagesAbrechnung always inserts it, with NULL status
        # columns when the TSE is not operational).
        session.add(AbrechnungTagTse(id=at.id, tse_id=_configured_tse_id()))

        # A backdated daily settlement reopens its month and year.
        invalidate_period_settlements(session, at.zeitpunkt)

        # The cashier counts the drawer while submitting; insert it afterwards and
        # deactivate any previous count of the same settlement (Java
        # AbrechnungenTag.insertZaehlprotokoll / setZaehlprotokollInactive).
        if p.zaehlprotokoll is not None:
            insert_count_protocol(session, at.id, p.zaehlprotokoll, user_id, commit=False)

        session.commit()
    except Exception:
        session.rollback()
        raise

    # DSFinV-K export (Java AbrechnungenTag.writeIntoDSFinVKCSVFiles): written
    # to DSFINVK_EXPORT_DIR when configured, otherwise on demand via
    # GET /export/dsfinvk/{id}. Training data never writes production files.
    if not is_training_mode():
        try:
            from .dsfinvk_export import write_dsfinvk_export

            write_dsfinvk_export(session, at.id)
        except Exception:
            logger.exception("DSFinV-K export for AbrechnungTag %s failed", at.id)

    # mwst values by ID (Java getAllCurrentMwstValuesByID)
    mwst_rates = {
        m.mwst_id: m.mwst_satz
        for m in session.exec(select(Mwst)).all()
        if m.mwst_id is not None
    }
    items = [
        {"ges_preis": d.ges_preis, "mwst_satz": d.mwst_satz}
        for v in sales
        for d in (v.verkauf_details or [])
    ]
    try:
        vals = get_all_current_mwst_values_by_id(mwst_rates, items=items)
        mwst_nach_id = {str(k): [float(x) for x in v] for k, v in vals.items()}
    except Exception:
        mwst_nach_id = None

    obj = AbrechnungTagPublic.model_validate(at)
    obj.storno_summe = agg["storno_summe"]
    obj.retouren_summe = agg["retouren_summe"]
    obj.mwst_nach_id = mwst_nach_id
    return obj
