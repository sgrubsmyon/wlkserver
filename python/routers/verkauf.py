from datetime import datetime, timezone
from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from sqlmodel import select

from ..models import (
    Artikel,
    Rabattaktion,
    Verkauf,
    VerkaufPublic,
    VerkaufCreate,
    VerkaufMwst,
    VerkaufMwstPublic,
    # VerkaufMwstCreate,
    VerkaufDetails,
    VerkaufDetailsPublic,
    # VerkaufDetailsCreate,
)
from ..session import SessionDep
from ..dependencies import bearer_scheme, require_user
from ..models import User
from ..business.vat_calculator import calculate_vat
from ..business.sale_workflow import (
    apply_anzahlung,
    build_sale_details,
    calculate_mwst_summary,
    write_anzahlung,
)

router = APIRouter(
    prefix="/verkauf",
    tags=["verkauf"],
    responses={404: {"description": "Not found"}},
)


@router.get("/")
def read_verkaeufe(
    session: SessionDep,
    von: Optional[str] = None,
    bis: Optional[str] = None,
    only_storno: bool = False,
    include_details: bool = False,
    include_mwst: bool = False,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
    desc: bool = False,
) -> List[dict]:
    selection = select(Verkauf)
    if von:
        von_dt = datetime.fromisoformat(von)
        if von_dt.tzinfo is None:
            von_dt = von_dt.replace(tzinfo=timezone.utc)
        selection = selection.where(Verkauf.verkaufsdatum >= von_dt)
    if bis:
        bis_dt = datetime.fromisoformat(bis)
        if bis_dt.tzinfo is None:
            bis_dt = bis_dt.replace(tzinfo=timezone.utc)
        selection = selection.where(Verkauf.verkaufsdatum <= bis_dt)
    if only_storno:
        selection = selection.where(Verkauf.storno_von.is_not(None))
    verkaeufe = session.exec(
        selection.offset(offset).limit(limit).order_by(Verkauf.verkaufsdatum.desc() if desc else Verkauf.verkaufsdatum)
    ).all()
    # return verkaeufe

    results = []
    for v in verkaeufe:
        v_obj = VerkaufPublic.model_validate(v).model_dump()
        if include_details:
            details = []
            for d in v.verkauf_details or []:
                d_obj = VerkaufDetailsPublic.model_validate(d, update={
                    "artikel_name": d.artikel.artikel_name if d.artikel else None,
                    "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                    "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
                })
                details.append(d_obj)
            v_obj["verkauf_details"] = details
        if include_mwst:
            mwsts = [VerkaufMwstPublic.model_validate(m).model_dump() for m in (v.verkauf_mwst or [])]
            v_obj["verkauf_mwst"] = mwsts
        results.append(v_obj)
    return results


@router.get("/{rechnungs_nr}")
def read_single_verkauf(
    rechnungs_nr: int,
    session: SessionDep,
    include_details: bool = True,
    include_mwst: bool = True,
) -> dict:
    v = session.get(Verkauf, rechnungs_nr)
    if not v:
        raise HTTPException(status_code=404, detail="Verkauf not found")
    v_obj = VerkaufPublic.model_validate(v).model_dump()
    if include_details:
        v_obj["verkauf_details"] = [
            VerkaufDetailsPublic.model_validate(d, update={
                "artikel_name": d.artikel.artikel_name if d.artikel else None,
                "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
                "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
            }) for d in (v.verkauf_details or [])
        ]
    if include_mwst:
        v_obj["verkauf_mwst"] = [VerkaufMwstPublic.model_validate(m).model_dump() for m in (v.verkauf_mwst or [])]
    return v_obj


@router.post("/", response_model=VerkaufPublic)
def create_verkauf(verkauf: VerkaufCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user: User = Depends(require_user)):
    # Resolve user_id from token if present (transaction attribution)
    user_id = getattr(verkauf, "user_id", None)
    if user_id is None and credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        payload = decode_token(credentials.credentials)
        if payload:
            user_id = payload.get("user_id")
    # Expand auxiliary lines (Pfand, discounts, price adjustment, voucher
    # redemption, Anzahlung) and validate before writing anything.
    prepared = build_sale_details(session, verkauf)
    anzahlung = apply_anzahlung(session, verkauf, prepared)
    # base = VerkaufCreate.model_validate(verkauf)
    new_v = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=verkauf.ec_zahlung,
        kunde_gibt=verkauf.kunde_gibt,
        storno_von=verkauf.storno_von,
        user_id=user_id,
    )
    new_v.rechnungs_nr = None
    session.add(new_v)
    session.commit()
    session.refresh(new_v)

    # Add details if present
    for d_obj in prepared:
        d_obj.rechnungs_nr = new_v.rechnungs_nr
        session.add(d_obj)
    session.commit()
    for d_obj in prepared:
        session.refresh(d_obj)

    # Deposit bookkeeping: the anzahlung row and the original prices of the
    # zeroed positions / the resolution entry for an open deposit.
    write_anzahlung(session, anzahlung, new_v.rechnungs_nr, new_v.verkaufsdatum, user_id)

    # Aggregate VAT per tax rate using Decimal-safe calculation
    mwst_summary = calculate_mwst_summary(prepared)

    for mwst_satz, summary in mwst_summary.items():
        m_obj = VerkaufMwst(
            rechnungs_nr=new_v.rechnungs_nr,
            mwst_satz=float(mwst_satz),
            mwst_netto=float(summary["mwst_netto"]),
            mwst_betrag=float(summary["mwst_betrag"]),
        )
        session.add(m_obj)

    session.commit()
    session.refresh(new_v)

    # Voucher handling: selling article 6 (GUTSCHEIN) creates a new voucher
    # (mirrors Java Kassieren.maybeInsertIntoGutschein).
    from ..models import Artikel, Gutschein
    max_nr = session.exec(select(Gutschein.gutschein_nr)).all()
    next_nr = (max(max_nr) if max_nr else 199) + 1
    for d in prepared:
        art = session.get(Artikel, d.artikel_id) if d.artikel_id is not None else None
        if art is not None and art.artikel_nr == "GUTSCHEIN":
            g = Gutschein(
                gutschein_nr=next_nr,
                datum=new_v.verkaufsdatum,
                gutschein_in_vd_id=d.vd_id,
                einloesung_in_vd_id=None,
                restbetrag=d.ges_preis if d.ges_preis is not None else 0.0,
            )
            g.gutschein_id = None
            session.add(g)
            next_nr += 1
    session.commit()

    # Voucher redemption as a sale position (mirrors Java
    # Kassieren.maybeInsertEinloesungIntoGutschein): the negative position is
    # booked with the receipt and reduces the voucher's remaining balance.
    if verkauf.gutschein_einloesung_nr is not None:
        from ..models import Gutschein
        from ..business.voucher_logic import redeem_voucher
        einloesung = next(
            (d for d in prepared if d.artikel_id is not None
             and session.get(Artikel, d.artikel_id).artikel_nr == "GUTSCHEINEINLOES"),
            None,
        )
        voucher = session.exec(
            select(Gutschein)
            .where(Gutschein.gutschein_nr == verkauf.gutschein_einloesung_nr)
            .order_by(Gutschein.gutschein_id)
        ).first()
        if einloesung is None or voucher is None:
            raise HTTPException(status_code=400, detail="Gutschein not found")
        redeem_voucher(session, voucher.gutschein_id,
                       einloesung_in_vd_id=einloesung.vd_id, user_id=user_id)

    # Cash register side-effect: only cash (non-EC) sales add money to the register
    # (mirrors Java Kassieren.insertIntoKassenstand, called when ec == false).
    ec_warning = None
    change = None
    total = sum((d.ges_preis or 0) for d in prepared)
    if not verkauf.ec_zahlung:
        from ..business.cash_register import update_kassenstand_for_sale, process_payment
        update_kassenstand_for_sale(session=session, rechnungs_nr=new_v.rechnungs_nr)
        change, _ = process_payment(total, ec_zahlung=False, kunde_gibt=verkauf.kunde_gibt)
    else:
        # EC payment threshold check (Java: ecSchwelle = 10.00)
        from ..business.cash_register import process_payment
        change, ec_warning = process_payment(total, ec_zahlung=True, kunde_gibt=verkauf.kunde_gibt)

    result = read_single_verkauf(new_v.rechnungs_nr, session)
    if isinstance(result, dict):
        result["ec_warning"] = ec_warning
        result["change"] = float(change) if change is not None else None
    return result


# --- Storno endpoint ---


@router.post("/{rechnungs_nr}/storno", response_model=dict)
def storno_verkauf(rechnungs_nr: int, session: SessionDep, cash_refund: bool = True, _user: User = Depends(require_user)):
    """Storno a receipt that is not yet part of a completed Tagesabschluss.

    The shop can only refund in cash (Java `HeutigeRechnungen.insertStornoIntoTSE`
    sends "Bar" even for EC sales), so `cash_refund` defaults to true. Set it to
    false only when an EC charge was not actually executed and nothing is paid out.
    """
    from ..business.storno_logic import create_storno
    original = session.get(Verkauf, rechnungs_nr)
    if not original:
        raise HTTPException(status_code=404, detail="Verkauf not found")
    user_id = getattr(_user, "user_id", None)
    storno_sale = create_storno(
        session,
        rechnungs_nr,
        user_id=user_id,
    )
    # voucher/installment handling hooks
    from ..business.storno_logic import handle_storno_voucher, handle_storno_installment
    handle_storno_voucher(session, original)
    handle_storno_installment(session, original)
    # TSE transaction handling for storno (best-effort; no TSE in training mode)
    from ..business.cash_register import is_training_mode
    if not is_training_mode():
        try:
            from ..utils.tse_client import tse_client
            from ..models import TSETransaction
            signed = tse_client.create_transaction(process_type="Kassenbeleg-Storno", process_data=None, training=False)
            tse = TSETransaction(
                transaction_number=signed.get("transaction_number"),
                rechnungs_nr=storno_sale.rechnungs_nr,
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
    # Cash payout: a cash sale is always refunded in cash; an EC sale too unless the
    # caller says the card was not charged (Java asks this in a dialog).
    payout_cash = (not original.ec_zahlung) or cash_refund
    if payout_cash:
        from ..business.cash_register import update_kassenstand_for_sale
        update_kassenstand_for_sale(
            session=session,
            rechnungs_nr=storno_sale.rechnungs_nr,
            kommentar="Storno",
        )
    return read_single_verkauf(storno_sale.rechnungs_nr, session)


# --- VerkaufMwst subroutes ---


# @router.get("/{rechnungs_nr}/mwst")
# def read_verkauf_mwst(rechnungs_nr: int, session: SessionDep) -> List[VerkaufMwstPublic]:
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     return [VerkaufMwstPublic.model_validate(m) for m in (v.verkauf_mwst or [])]


# @router.post("/{rechnungs_nr}/mwst", response_model=List[VerkaufMwstPublic])
# def create_verkauf_mwst(rechnungs_nr: int, mwst: List[VerkaufMwstCreate], session: SessionDep):
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     created = []
#     for m in mwst:
#         m_obj = VerkaufMwst.model_validate(m)
#         m_obj.rechnungs_nr = rechnungs_nr
#         session.add(m_obj)
#         created.append(m_obj)
#     session.commit()
#     for c in created:
#         session.refresh(c)
#     return [VerkaufMwstPublic.model_validate(c) for c in created]


## @router.delete("/{rechnungs_nr}/mwst/{mwst_satz}")
## def delete_verkauf_mwst(rechnungs_nr: int, mwst_satz: float, session: SessionDep):
##     key = (rechnungs_nr, mwst_satz)
##     stmt = select(VerkaufMwst).where(
##         VerkaufMwst.rechnungs_nr == rechnungs_nr,
##         VerkaufMwst.mwst_satz == mwst_satz,
##     )
##     row = session.exec(stmt).one_or_none()
##     if not row:
##         raise HTTPException(status_code=404, detail="VerkaufMwst not found")
##     session.delete(row)
##     session.commit()
##     return {"message": "VerkaufMwst deleted"}


# --- VerkaufDetails subroutes ---


# @router.get("/{rechnungs_nr}/details")
# def read_verkauf_details(rechnungs_nr: int, session: SessionDep) -> List[dict]:
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     out = []
#     for d in (v.verkauf_details or []):
#         d_obj = VerkaufDetailsPublic.model_validate(d).model_dump(update={
#             "artikel_name": d.artikel.artikel_name if d.artikel else None,
#             "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
#             "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
#         })
#         out.append(d_obj)
#     return out


# @router.post("/{rechnungs_nr}/details", response_model=VerkaufDetailsPublic)
# def create_verkauf_detail(rechnungs_nr: int, detail: VerkaufDetailsCreate, session: SessionDep):
#     v = session.get(Verkauf, rechnungs_nr)
#     if not v:
#         raise HTTPException(status_code=404, detail="Verkauf not found")
#     d = VerkaufDetails.model_validate(detail)
#     d.vd_id = None
#     d.rechnungs_nr = rechnungs_nr
#     if d.position is None:
#         q = select(VerkaufDetails).where(VerkaufDetails.rechnungs_nr == rechnungs_nr)
#         existing = session.exec(q).all()
#         d.position = (max((e.position or 0) for e in existing) + 1) if existing else 1
#     session.add(d)
#     session.commit()
#     session.refresh(d)
#     # enrich with artikel info
#     d_out = VerkaufDetailsPublic.model_validate(d).model_dump(update={
#         "artikel_name": d.artikel.artikel_name if d.artikel else None,
#         "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
#         "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
#     })
#     return d_out


## @router.delete("/{rechnungs_nr}/details/{vd_id}")
## def delete_verkauf_detail(rechnungs_nr: int, vd_id: int, session: SessionDep):
##     d = session.get(VerkaufDetails, vd_id)
##     if not d or d.rechnungs_nr != rechnungs_nr:
##         raise HTTPException(status_code=404, detail="VerkaufDetails not found")
##     session.delete(d)
##     session.commit()
##     return {"message": "VerkaufDetails deleted"}


## @router.patch("/{rechnungs_nr}/details/{vd_id}", response_model=VerkaufDetailsPublic)
## def update_verkauf_detail(rechnungs_nr: int, vd_id: int, detail: VerkaufDetailsCreate, session: SessionDep):
##     d = session.get(VerkaufDetails, vd_id)
##     if not d or d.rechnungs_nr != rechnungs_nr:
##         raise HTTPException(status_code=404, detail="VerkaufDetails not found")
##     data = detail.model_dump(exclude_unset=True)
##     for k, v in data.items():
##         setattr(d, k, v)
##     session.add(d)
##     session.commit()
##     session.refresh(d)
##     d_out = VerkaufDetailsPublic.model_validate(d).model_dump(update={
##         "artikel_name": d.artikel.artikel_name if d.artikel else None,
##         "artikel_kurzname": d.artikel.kurzname if d.artikel else None,
##         "artikel_vk_preis": d.artikel.vk_preis if d.artikel else None,
##     })
##     return d_out