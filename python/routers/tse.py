import io
import tarfile
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlmodel import select

from ..models import TSETransaction, TSETransactionPublic, TSETransactionCreate, Verkauf
from ..session import SessionDep
from ..utils.tse_client import tse_client

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


@router.get("/transaction")
def read_tse_transactions(
    session: SessionDep,
    offset: int = 0,
    limit: int = 100,
) -> list[TSETransactionPublic]:
    rows = session.exec(
        select(TSETransaction).offset(offset).limit(limit).order_by(TSETransaction.transaction_id)
    ).all()
    return [TSETransactionPublic.model_validate(r) for r in rows]


@router.get("/transaction/{transaction_id}")
def read_single_tse_transaction(transaction_id: int, session: SessionDep) -> TSETransactionPublic:
    t = session.get(TSETransaction, transaction_id)
    if not t:
        raise HTTPException(status_code=404, detail="TSETransaction not found")
    return TSETransactionPublic.model_validate(t)


@router.post("/transaction", response_model=TSETransactionPublic)
def create_tse_transaction(payload: TSETransactionCreate, session: SessionDep):
    if payload.rechnungs_nr is not None:
        v = session.get(Verkauf, payload.rechnungs_nr)
        if not v:
            raise HTTPException(status_code=400, detail="Verkauf not found")
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
    )
    new_t.transaction_id = None
    session.add(new_t)
    session.commit()
    session.refresh(new_t)
    return TSETransactionPublic.model_validate(new_t)


@router.get("/status")
def get_tse_status():
    return tse_client.status()


@router.post("/init")
def init_tse():
    return tse_client.init()


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