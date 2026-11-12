import io
import tarfile
from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPAuthorizationCredentials
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import select

from ..models import (
    TSETransaction,
    User,
    Verkauf,
)
from ..schemas import (
    TSETransactionPublic,
    TSETransactionCreate,
)
from ..session import SessionDep
from ..business.tse_signing import (
    abort_transaction as abort_started_transaction,
    start_transaction as start_basket_transaction,
)
from ..utils.tse_client import PIN_LENGTH, PUK_LENGTH, tse_client
from ..dependencies import bearer_scheme, require_user
from ..utils.pagination import paginate

router = APIRouter(
    prefix="/tse",
    tags=["tse"],
    responses={404: {"description": "Not found"}},
)


class TSEExportPartialRequest(BaseModel):
    criterion: str = "sig_counter"  # tx_number | date | sig_counter
    start_tx_number: int | None = None
    end_tx_number: int | None = None
    start_date: str | None = None
    end_date: str | None = None
    last_excluded_signature_counter: int | None = None
    max_records: int | None = None


class TSEInitializeRequest(BaseModel):
    """The four values the admin enters once for a brand-new TSE (`TSEInitDialog`)."""

    admin_pin: str
    admin_puk: str
    time_admin_pin: str
    time_admin_puk: str


class TSEExportDeleteRequest(BaseModel):
    last_excluded_signature_counter: int | None = None
    max_records: int | None = None


def _make_tar_bytes(name: str) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w") as tf:
        data = b"TSE export placeholder"
        ti = tarfile.TarInfo(name="export.txt")
        ti.size = len(data)
        tf.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


@router.get("/transaction/verkauf/{rechnungs_nr}")
def read_tse_transactions_for_verkauf(rechnungs_nr: int, session: SessionDep) -> list[TSETransactionPublic]:
    rows = session.exec(
        select(TSETransaction).where(TSETransaction.rechnungs_nr == rechnungs_nr)
    ).all()
    return [TSETransactionPublic.model_validate(r) for r in rows]


@router.get("/transaction")
def read_tse_transactions(
    session: SessionDep,
    rechnungs_nr: Optional[int] = None,
    offset: int = 0,
    limit: Annotated[int, Query(le=100)] = 100,
) -> list[TSETransactionPublic]:
    selection = select(TSETransaction)
    if rechnungs_nr is not None:
        selection = selection.where(TSETransaction.rechnungs_nr == rechnungs_nr)
    rows = paginate(session, selection, offset, limit, TSETransaction.transaction_id)
    return [TSETransactionPublic.model_validate(r) for r in rows]


@router.get("/transaction/{transaction_id}")
def read_single_tse_transaction(transaction_id: int, session: SessionDep) -> TSETransactionPublic:
    t = session.get(TSETransaction, transaction_id)
    if not t:
        raise HTTPException(status_code=404, detail="TSETransaction not found")
    return TSETransactionPublic.model_validate(t)


@router.post("/transaction", response_model=TSETransactionPublic)
def create_tse_transaction(payload: TSETransactionCreate, session: SessionDep, credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme), _user=Depends(require_user)):
    if payload.rechnungs_nr is not None:
        v = session.get(Verkauf, payload.rechnungs_nr)
        if not v:
            raise HTTPException(status_code=400, detail="Verkauf not found")
    user_id = payload.user_id if hasattr(payload, "user_id") else None
    if user_id is None and credentials is not None and credentials.credentials:
        from ..utils.auth import decode_token
        tok = decode_token(credentials.credentials)
        if tok:
            user_id = tok.get("user_id")
    # Use client to "sign"
    signed = tse_client.create_transaction(
        process_type=payload.process_type,
        process_data=payload.process_data,
        training=payload.training,
    )
    new_t = TSETransaction(
        transaction_number=payload.transaction_number if payload.transaction_number is not None else signed["transaction_number"],
        rechnungs_nr=payload.rechnungs_nr,
        training=payload.training,
        transaction_start=payload.transaction_start if payload.transaction_start is not None else signed["transaction_start"],
        transaction_end=payload.transaction_end if payload.transaction_end is not None else signed["transaction_end"],
        process_type=payload.process_type,
        signature_counter=payload.signature_counter if payload.signature_counter is not None else signed["signature_counter"],
        signature_base64=payload.signature_base64 if payload.signature_base64 is not None else signed["signature_base64"],
        tse_error=payload.tse_error if payload.tse_error is not None else signed["tse_error"],
        process_data=payload.process_data,
        user_id=user_id,
    )
    new_t.transaction_id = None
    session.add(new_t)
    session.commit()
    session.refresh(new_t)
    return TSETransactionPublic.model_validate(new_t)


@router.post("/transaction/start", response_model=TSETransactionPublic)
def start_tse_transaction(session: SessionDep, _user: User = Depends(require_user)):
    """Start the TSE transaction of a new basket (first article scanned)."""
    row = start_basket_transaction(session, user_id=getattr(_user, "user_id", None))
    return TSETransactionPublic.model_validate(row)


@router.post("/transaction/{transaction_id}/abbruch", response_model=TSETransactionPublic)
def abort_tse_transaction(transaction_id: int, session: SessionDep, _user: User = Depends(require_user)):
    """Abort a started transaction: the sale did not happen (`AVBelegabbruch`)."""
    row = abort_started_transaction(session, transaction_id)
    return TSETransactionPublic.model_validate(row)


@router.get("/status")
def get_tse_status():
    return tse_client.status()


@router.post("/init")
def init_tse(payload: Optional[TSEInitializeRequest] = None, _user: User = Depends(require_user)):
    """Commission a brand-new TSE, or keep the time of a running one set.

    With a body: sets both PINs and both PUKs while the TSE is still in transport
    state, initializes it, sets its time and registers this client id
    (`se_initializePuk` + `se_unblockUser`, `se_initialize`, `se_updateTime`,
    `se_registerClient`; v3.1 replaces the deprecated `se_initializePinValues`).
    Without a body: opens the device and keeps its time set.
    """
    if payload is None:
        return tse_client.ensure_ready()
    for name in ("admin_pin", "time_admin_pin"):
        if len(getattr(payload, name)) != PIN_LENGTH:
            raise HTTPException(status_code=400, detail=f"{name} must be {PIN_LENGTH} characters")
    for name in ("admin_puk", "time_admin_puk"):
        if len(getattr(payload, name)) != PUK_LENGTH:
            raise HTTPException(status_code=400, detail=f"{name} must be {PUK_LENGTH} characters")
    return tse_client.initialize(
        payload.admin_pin.encode(), payload.admin_puk.encode(),
        payload.time_admin_pin.encode(), payload.time_admin_puk.encode(),
    )


@router.post("/certificates")
def export_certificates():
    try:
        data = tse_client.export_certificates()
    except Exception:
        data = b""
    if not data:
        data = _make_tar_bytes("certificates")
    return Response(
        content=data,
        media_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="tse_certificates.tar"'},
    )


@router.post("/export/full")
def export_full():
    try:
        data = tse_client.export_full()
    except Exception:
        data = b""
    if not data:
        data = _make_tar_bytes("full")
    return Response(
        content=data,
        media_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="tse_export_full.tar"'},
    )


@router.post("/export/partial")
def export_partial(payload: Optional[TSEExportPartialRequest] = None):
    p = payload or TSEExportPartialRequest()
    kwargs = {
        "criterion": p.criterion,
        "start_tx_number": p.start_tx_number,
        "end_tx_number": p.end_tx_number,
        "start_date": p.start_date,
        "end_date": p.end_date,
        "last_excluded_signature_counter": p.last_excluded_signature_counter,
        "max_records": p.max_records,
    }
    try:
        data = tse_client.export_partial(**kwargs)
    except Exception:
        data = b""
    if not data:
        data = _make_tar_bytes("partial")
    return Response(
        content=data,
        media_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="tse_export_partial.tar"'},
    )


@router.post("/export/delete")
def export_delete(payload: Optional[TSEExportDeleteRequest] = None):
    p = payload or TSEExportDeleteRequest()
    kwargs = {
        "last_excluded_signature_counter": p.last_excluded_signature_counter,
        "max_records": p.max_records,
    }
    try:
        data = tse_client.export_and_delete(**kwargs)
    except Exception:
        data = b""
    if not data:
        data = _make_tar_bytes("delete")
    return Response(
        content=data,
        media_type="application/x-tar",
        headers={"Content-Disposition": 'attachment; filename="tse_export_delete.tar"'},
    )


# Aliases
read_tse_transaction = read_tse_transactions
read_tse_transactions_alias = read_tse_transactions
create_tse_transaction_entry = create_tse_transaction