import logging
from datetime import datetime, timezone, date
from typing import Annotated, Optional

from fastapi import APIRouter, HTTPException, Query
from sqlmodel import select

from ..models import (
    AbrechnungJahr,
    AbrechnungJahrMwst,
    AbrechnungMonat,
    AbrechnungMonatMwst,
    AbrechnungTag,
    AbrechnungTagPublic,
    AbrechnungTagCreate,
    AbrechnungTagMwst,
    AbrechnungTagMwstPublic,
    Kassenstand,
    KassenstandCreate,
    Verkauf,
    VerkaufMwst,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from ..business.cash_register import aggregate_period, end_of_day_procedure, open_period_range
from fastapi.security import HTTPAuthorizationCredentials
from fastapi import Depends

router = APIRouter(
    prefix="/abrechnung/tag",
    tags=["abrechnung_tag"],
    responses={404: {"description": "Not found"}},
)

logger = logging.getLogger(__name__)


def _last_tag(session: SessionDep):
    return session.exec(select(AbrechnungTag).order_by(AbrechnungTag.id.desc())).first()


def _invalidate_period_settlements(session: SessionDep, zeitpunkt: datetime) -> None:
    """Drop month/year settlements covering a (re)opened daily settlement.

    Mirrors Java `AbrechnungenTag.deleteAbrechnungIfNeedBe()`: a backdated daily
    settlement makes the enclosing month and year settlements outdated, so they
    must be recreated by the next `POST /abrechnung/monat|jahr`.
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
    session.commit()


@router.get("/")
def read_abrechnung_tags(
    session: SessionDep,
    desc: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[AbrechnungTagPublic]:
    order = AbrechnungTag.id.desc() if desc else AbrechnungTag.id
    rows = session.exec(
        select(AbrechnungTag).offset(offset).limit(limit).order_by(order)
    ).all()
    return [AbrechnungTagPublic.model_validate(r) for r in rows]


@router.get("/offen")
def read_offene_abrechnung_tags(session: SessionDep) -> list[str]:
    last = _last_tag(session)
    last_bis = last.rechnungs_nr_bis if last else 0
    sales = session.exec(
        select(Verkauf).where(Verkauf.rechnungs_nr > last_bis).order_by(Verkauf.verkaufsdatum)
    ).all()
    dates = []
    seen = set()
    for s in sales:
        d = s.verkaufsdatum.date().isoformat()
        if d not in seen:
            seen.add(d)
            dates.append(d)
    return dates


@router.get("/vorschau")
def read_abrechnung_tag_preview(session: SessionDep) -> dict:
    """Preview the open Tagesabschluss without writing anything."""
    return end_of_day_procedure(session)


@router.get("/{tag_id}")
def read_single_abrechnung_tag(tag_id: int, session: SessionDep) -> dict:
    t = session.get(AbrechnungTag, tag_id)
    if not t:
        raise HTTPException(status_code=404, detail="AbrechnungTag not found")
    mwsts = session.exec(
        select(AbrechnungTagMwst).where(AbrechnungTagMwst.id == tag_id)
    ).all()
    obj = AbrechnungTagPublic.model_validate(t).model_dump()
    obj["mwst"] = [AbrechnungTagMwstPublic.model_validate(m).model_dump() for m in mwsts]
    return obj


@router.post("/", response_model=AbrechnungTagPublic)
def create_abrechnung_tag(payload: Optional[AbrechnungTagCreate], session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    p = payload or AbrechnungTagCreate()
    user_id = None
    if credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        tok = decode_token(credentials.credentials)
        if tok:
            user_id = tok.get("user_id")
    now = datetime.now(timezone.utc)
    last = _last_tag(session)

    # Determine rechnungs range
    if p.rechnungs_nr_von is not None and p.rechnungs_nr_bis is not None:
        von = p.rechnungs_nr_von
        bis = p.rechnungs_nr_bis
    else:
        period = open_period_range(session)
        if period is None:
            raise HTTPException(status_code=400, detail="No sales to settle")
        von, bis = period

    agg = aggregate_period(session, von, bis)
    sales = agg["sales"]
    if not sales:
        raise HTTPException(status_code=400, detail="No sales in range")
    storno_summe = agg["storno_summe"]
    retouren_summe = agg["retouren_summe"]
    mwst_map = agg["mwst_map"]

    # Link the settlement to the current Kassenstand entry (Java
    # AbrechnungenTag.insertTagesAbrechnung uses the highest kassenstand_id).
    # A closing balance is not invented here: the cashier records the counted cash
    # as a manual Kassenstand entry beforehand.
    ks_id = p.kassenstand_id
    if ks_id is not None and not session.get(Kassenstand, ks_id):
        raise HTTPException(status_code=400, detail="Kassenstand not found")
    if ks_id is None:
        last_ks = session.exec(
            select(Kassenstand).order_by(Kassenstand.kassenstand_id.desc())
        ).first()
        ks_id = last_ks.kassenstand_id if last_ks is not None else None

    # Automatic incremental TSE export (best-effort), mirroring Java
    # AbrechnungenTag.exportTSELog(): partial export by signature counter
    # since the previous settlement, with fallback by TX number.
    prev_sig = p.last_tse_sig_counter
    if prev_sig is None and last is not None:
        prev_sig = last.last_tse_sig_counter
    if prev_sig is None:
        prev_sig = 0
    try:
        from ..utils.tse_client import tse_client
        tse_client.export_partial(last_excluded_signature_counter=prev_sig)
    except Exception:
        pass

    at = AbrechnungTag(
        z_kasse_id=p.z_kasse_id or "1",
        zeitpunkt=p.zeitpunkt or now,
        zeitpunkt_real=p.zeitpunkt_real or now,
        kassenstand_id=ks_id,
        rechnungs_nr_von=von,
        rechnungs_nr_bis=bis,
        last_tse_sig_counter=p.last_tse_sig_counter if p.last_tse_sig_counter is not None else prev_sig,
        user_id=user_id,
    )
    at.id = None
    session.add(at)
    session.commit()
    session.refresh(at)

    for satz, vals in mwst_map.items():
        row = AbrechnungTagMwst(
            id=at.id,
            mwst_satz=satz,
            mwst_netto=vals["netto"],
            mwst_betrag=vals["betrag"],
            bar_brutto=vals["bar"],
        )
        session.add(row)
    session.commit()

    # A backdated daily settlement reopens its month and year.
    _invalidate_period_settlements(session, at.zeitpunkt)

    # The cashier counts the drawer while submitting; insert it afterwards and
    # deactivate any previous count of the same settlement (Java
    # AbrechnungenTag.insertZaehlprotokoll / setZaehlprotokollInactive).
    if p.zaehlprotokoll is not None:
        from ..business.count_protocol import insert_count_protocol
        insert_count_protocol(session, at.id, p.zaehlprotokoll, user_id)

    # DSFinV-K export (Java AbrechnungenTag.writeIntoDSFinVKCSVFiles): written
    # to DSFINVK_EXPORT_DIR when configured, otherwise on demand via
    # GET /export/dsfinvk/{id}.
    try:
        from ..business.dsfinvk_export import write_dsfinvk_export
        write_dsfinvk_export(session, at.id)
    except Exception:
        logger.exception("DSFinV-K export for AbrechnungTag %s failed", at.id)

    # mwst values by ID (Java getAllCurrentMwstValuesByID)
    from ..business.vat_calculator import get_all_current_mwst_values_by_id
    from ..models import Mwst
    mwst_rates = {m.mwst_id: m.mwst_satz for m in session.exec(select(Mwst)).all() if m.mwst_id is not None}
    items = []
    for v in sales:
        for d in (v.verkauf_details or []):
            items.append({"ges_preis": d.ges_preis, "mwst_satz": d.mwst_satz})
    try:
        vals = get_all_current_mwst_values_by_id(mwst_rates, items=items)
        mwst_nach_id = {str(k): [float(x) for x in v] for k, v in vals.items()}
    except Exception:
        mwst_nach_id = None

    obj = AbrechnungTagPublic.model_validate(at)
    obj.storno_summe = storno_summe
    obj.retouren_summe = retouren_summe
    obj.mwst_nach_id = mwst_nach_id
    return obj


# Aliases
read_abrechnung_tag = read_abrechnung_tags
read_abrechnung_tags_alias = read_abrechnung_tags
create_abrechnung_tag_entry = create_abrechnung_tag