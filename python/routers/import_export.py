from typing import Annotated, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlmodel import Session, select

from ..models import Artikel, Bestellung, BestellungDetails, AbrechnungTag
from ..session import SessionDep
from ..utils.csv_import import import_artikel_from_csv, import_bestellung_from_csv
from ..utils.csv_export import (
    export_artikel_to_csv,
    export_abrechnung_to_csv,
    export_bestellung_to_csv,
    export_inventur_to_csv,
)

router = APIRouter(tags=["import_export"])


@router.post("/import/artikel")
def import_artikel(session: SessionDep, file: UploadFile = File(...)):
    content = file.file.read().decode("utf-8", errors="replace")
    created = import_artikel_from_csv(content, session)
    return {"imported": len(created)}


@router.get("/export/artikel")
def export_artikel(session: SessionDep):
    csv = export_artikel_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=artikel.csv"})


@router.post("/import/bestellung")
def import_bestellung(session: SessionDep, file: UploadFile = File(...)):
    content = file.file.read().decode("utf-8", errors="replace")
    created = import_bestellung_from_csv(content, session)
    return {"imported": len(created)}


@router.get("/export/abrechnung")
def export_abrechnung(session: SessionDep):
    csv = export_abrechnung_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=abrechnung.csv"})


@router.get("/export/bestellung")
def export_bestellung(session: SessionDep):
    csv = export_bestellung_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bestellung.csv"})


@router.get("/export/inventur")
def export_inventur(session: SessionDep):
    csv = export_inventur_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inventur.csv"})
