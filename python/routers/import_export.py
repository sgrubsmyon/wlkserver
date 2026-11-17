"""CSV and DSFinV-K import/export endpoints.

Imports decode the uploaded file as UTF-8 and delegate the row handling to
`utils.csv_import`; exports stream generated CSV as a download. The DSFinV-K
export bundles one Tagesabschluss as a ZIP archive.
"""
from typing import Annotated, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import Response
from sqlmodel import Session, select

from ..models import (
    Artikel,
    Bestellung,
    BestellungDetails,
    AbrechnungTag,
)
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
    """Import articles from an uploaded CSV and report how many were created."""
    content = file.file.read().decode("utf-8", errors="replace")
    created = import_artikel_from_csv(content, session)
    return {"imported": len(created)}


@router.get("/export/artikel")
def export_artikel(session: SessionDep):
    """Download all articles as a CSV file."""
    csv = export_artikel_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=artikel.csv"})


@router.post("/import/bestellung")
def import_bestellung(session: SessionDep, file: UploadFile = File(...)):
    """Import orders from an uploaded CSV and report how many were created."""
    content = file.file.read().decode("utf-8", errors="replace")
    created = import_bestellung_from_csv(content, session)
    return {"imported": len(created)}


@router.get("/export/abrechnung")
def export_abrechnung(session: SessionDep):
    """Download the settlements as a CSV file."""
    csv = export_abrechnung_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=abrechnung.csv"})


@router.get("/export/bestellung")
def export_bestellung(session: SessionDep):
    """Download the orders as a CSV file."""
    csv = export_bestellung_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=bestellung.csv"})


@router.get("/export/inventur")
def export_inventur(session: SessionDep):
    """Download the stock-taking (Inventur) list as a CSV file."""
    csv = export_inventur_to_csv(session)
    return Response(content=csv, media_type="text/csv", headers={"Content-Disposition": "attachment; filename=inventur.csv"})


@router.get("/export/dsfinvk/{abrechnung_tag_id}")
def export_dsfinvk_zip(abrechnung_tag_id: int, session: SessionDep):
    """DSFinV-K export of one Tagesabschluss as a ZIP archive."""
    from ..business.dsfinvk_export import export_dsfinvk

    data = export_dsfinvk(session, abrechnung_tag_id)
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename=dsfinvk_{abrechnung_tag_id}.zip"},
    )


ODS_MEDIA_TYPE = "application/vnd.oasis.opendocument.spreadsheet"


@router.get("/export/bestellung/{bestell_nr}/ods")
def export_bestellung_ods(
    bestell_nr: int,
    session: SessionDep,
    typ: Annotated[str, Query(pattern="^(LM|KHW)$")] = "LM",
):
    """Fill the ODS order template (`Bestellvorlage_<typ>.ods`) for one order."""
    from ..business.template_export import export_bestellung

    data = export_bestellung(session, bestell_nr, typ)
    return Response(
        content=data,
        media_type=ODS_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename=Bestellvorlage_{typ}_{bestell_nr}.ods"},
    )


@router.get("/export/inventur/{bestell_nr}/ods")
def export_inventur_ods(bestell_nr: int, session: SessionDep):
    """Fill `Inventur.ods` with the counted stock of one inventory order."""
    from ..business.template_export import export_inventur

    data = export_inventur(session, bestell_nr, "IVT")
    return Response(
        content=data,
        media_type=ODS_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename=Inventur_{bestell_nr}.ods"},
    )


@router.get("/export/abrechnung/{kind}/{settlement_id}/ods")
def export_abrechnung_ods(kind: Literal["tag", "monat", "jahr"], settlement_id: int, session: SessionDep):
    """Fill Tages-/Monats-/Jahresabrechnung.ods for one settlement."""
    from ..business.template_export import export_settlement

    data = export_settlement(session, kind, settlement_id)
    names = {"tag": "Tagesabrechnung", "monat": "Monatsabrechnung", "jahr": "Jahresabrechnung"}
    return Response(
        content=data,
        media_type=ODS_MEDIA_TYPE,
        headers={"Content-Disposition": f"attachment; filename={names[kind]}_{settlement_id}.ods"},
    )
