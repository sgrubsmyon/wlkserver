"""Spreadsheet (ODS) exports: template filling and the download endpoints."""
import io
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from odf.opendocument import OpenDocumentSpreadsheet, load
from odf.table import Table, TableCell, TableRow
from odf.text import P
from sqlmodel import delete, select

from python.main import app
from python.models import (
    AbrechnungTag,
    AbrechnungTagMwst,
    Artikel,
    Bestellung,
    BestellungDetails,
    Kassenstand,
    Lieferant,
    Mwst,
    Produktgruppe,
    Verkauf,
    Zaehlprotokoll,
    ZaehlprotokollDetails,
)
from python.session import get_session

TEMPLATES = ("Bestellvorlage_LM.ods", "Bestellvorlage_KHW.ods", "Inventur.ods",
             "Tagesabrechnung.ods", "Monatsabrechnung.ods", "Jahresabrechnung.ods")


def _write_template(path):
    """Minimal ODS with a header-style row above a data row."""
    document = OpenDocumentSpreadsheet()
    table = Table(name="Sheet1")
    for _ in range(32):
        row = TableRow()
        row.addElement(TableCell(numbercolumnsrepeated=50))
        table.addElement(row)
    document.spreadsheet.addElement(table)
    document.save(str(path))


@pytest.fixture
def templates(tmp_path, monkeypatch):
    for name in TEMPLATES:
        _write_template(tmp_path / name)
    monkeypatch.setenv("VORLAGEN_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _cells(ods_bytes, row_index):
    document = load(io.BytesIO(ods_bytes))
    rows = document.getElementsByType(Table)[0].getElementsByType(TableRow)
    result = []
    for cell in rows[row_index].getElementsByType(TableCell):
        text = "".join(n.data for p in cell.getElementsByType(P)
                       for n in p.childNodes if hasattr(n, "data"))
        result.append((text, cell.getAttribute("value")))
    return result


def _seed_artikel(session, nr="A1", vk=2.0, ek=11.9, mwst_satz=0.19):
    mwst = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    lieferant = Lieferant(lieferant_name=f"Lieferant {nr}", lieferant_kurzname=nr)
    session.add(mwst)
    session.add(lieferant)
    session.commit()
    session.refresh(mwst)
    session.refresh(lieferant)
    group = Produktgruppe(produktgruppen_name=f"Gruppe {nr}", mwst_id=mwst.mwst_id)
    session.add(group)
    session.commit()
    session.refresh(group)
    artikel = Artikel(artikel_nr=nr, artikel_name=f"Artikel {nr}", vk_preis=vk,
                      ek_preis=ek, setgroesse=10, ek_rabatt=0.10, vpe=6,
                      produktgruppen_id=group.produktgruppen_id,
                      lieferant_id=lieferant.lieferant_id)
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    return artikel


def _seed_order(session, artikel, typ="LM", stueckzahl=5):
    order = Bestellung(typ=typ, bestell_datum=datetime(2026, 11, 17, 12, tzinfo=timezone.utc),
                       jahr=2026, kw=46)
    session.add(order)
    session.commit()
    session.refresh(order)
    session.add(BestellungDetails(bestell_nr=order.bestell_nr, typ=typ, position=1,
                                  artikel_id=artikel.artikel_id, stueckzahl=stueckzahl))
    session.commit()
    return order


def test_bestellung_ods_export(client, session, templates):
    artikel = _seed_artikel(session)
    order = _seed_order(session, artikel)

    r = client.get(f"/export/bestellung/{order.bestell_nr}/ods?typ=LM")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith(
        "application/vnd.oasis.opendocument.spreadsheet")

    header = _cells(r.content, 1)
    assert header[2][0] == "17.11.2026"   # C2
    assert header[8][1] == "46"           # I2 (KW)

    row = _cells(r.content, 8)            # data starts at row 8
    assert row[0][0] == "Lieferant A1"
    assert row[1][0] == "A1"
    assert row[2][0] == "Artikel A1"
    assert row[3][1] == "6"               # VPE
    assert row[4][1] == "2"               # VK price (no recommended price)
    assert row[5][1] == "11.9"            # EK price
    assert row[6][1] == "0.19"            # VAT rate
    assert row[7][1] == "5"               # quantity


def test_inventur_ods_export(client, session, templates):
    artikel = _seed_artikel(session)
    order = _seed_order(session, artikel, typ="IVT")

    r = client.get(f"/export/inventur/{order.bestell_nr}/ods")
    assert r.status_code == 200

    assert _cells(r.content, 0)[0][0] == "Inventur 31.12.2026"
    row = _cells(r.content, 3)
    assert row[0][0] == "A1"              # supplier short name
    assert row[1][0] == "A1"
    assert row[5][1] == "10"              # set size
    assert row[6][1] == "10"              # EK discount in percent
    assert row[7][1] == "11.9"            # EK price per set
    assert row[8][1] == "1.19"            # EK price per piece
    assert row[9][1] == "19"              # VAT in percent
    assert row[10][1] == "1"              # net per piece
    assert row[11][1] == "0.19"           # VAT per piece
    assert row[12][1] == "5"              # quantity
    assert row[13][1] == "5"              # net total
    assert row[14][1] == "0.95"           # VAT total
    assert row[15][1] == "5.95"           # gross total
    assert row[16][1] == "10"             # VK total


def test_missing_order_is_404(client, templates):
    assert client.get("/export/bestellung/999/ods?typ=LM").status_code == 404


def _seed_settlement(session):
    for _ in range(2):
        sale = Verkauf(verkaufsdatum=datetime(2026, 11, 17, 10, tzinfo=timezone.utc),
                       ec_zahlung=False)
        session.add(sale)
        session.commit()
    kassenstand = Kassenstand(buchungsdatum=datetime(2026, 11, 17, 20, tzinfo=timezone.utc),
                              neuer_kassenstand=5.0, manuell=True)
    session.add(kassenstand)
    session.commit()
    session.refresh(kassenstand)
    settlement = AbrechnungTag(z_kasse_id="1",
                              zeitpunkt=datetime(2026, 11, 17, 20, tzinfo=timezone.utc),
                              zeitpunkt_real=datetime(2026, 11, 17, 20, tzinfo=timezone.utc),
                              kassenstand_id=kassenstand.kassenstand_id,
                              rechnungs_nr_von=1, rechnungs_nr_bis=2)
    session.add(settlement)
    session.commit()
    session.refresh(settlement)
    session.add(AbrechnungTagMwst(id=settlement.id, mwst_satz=0.19, mwst_netto=10.0,
                                  mwst_betrag=1.9, bar_brutto=11.9))
    session.add(AbrechnungTagMwst(id=settlement.id, mwst_satz=0.07, mwst_netto=20.0,
                                  mwst_betrag=1.4, bar_brutto=0.0))
    session.commit()

    protocol = Zaehlprotokoll(abrechnung_tag_id=settlement.id,
                              zeitpunkt=datetime(2026, 11, 17, 19, 30, tzinfo=timezone.utc),
                              kommentar="passt", aktiv=True)
    session.add(protocol)
    session.commit()
    session.refresh(protocol)
    session.add(ZaehlprotokollDetails(zaehlprotokoll_id=protocol.id, anzahl=4, einheit=0.5))
    session.add(ZaehlprotokollDetails(zaehlprotokoll_id=protocol.id, anzahl=3, einheit=1.0))
    session.commit()
    return settlement


def test_tag_ods_export(client, session, templates):
    settlement = _seed_settlement(session)

    r = client.get(f"/export/abrechnung/tag/{settlement.id}/ods")
    assert r.status_code == 200
    assert _cells(r.content, 6)[1][0] == "17.11.2026"   # B7
    assert _cells(r.content, 7)[1][1] == str(settlement.id)  # B8

    totals = [_cells(r.content, i)[1][1] for i in (9, 10, 11)]
    assert totals == ["33.3", "11.9", "21.4"]           # brutto, bar, EC

    # VAT block starts at row 13, sorted by rate, one blank row between rates
    assert _cells(r.content, 13)[0][0] == "7% MwSt. Brutto:"
    assert _cells(r.content, 13)[1][1] == "21.4"
    assert _cells(r.content, 17)[0][0] == "19% MwSt. Brutto:"

    # stornos/retouren are reset per VAT rate in use, then the withdrawals
    assert _cells(r.content, 21)[0][0] == "Storno (7%)"
    assert _cells(r.content, 21)[1][1] == "0"
    assert _cells(r.content, 23)[0][0] == "Retouren (7%)"
    assert _cells(r.content, 25)[0][0] == "Entnahmen"

    # count protocol block sits at the fixed row 27
    row = _cells(r.content, 27)
    assert row[0][0] == "Zählprotokoll:"
    assert row[1][0].startswith("17.11.2026")
    assert _cells(r.content, 28)[0][0] == "0,50 €, Anzahl:"
    assert _cells(r.content, 28)[1][1] == "4"
    assert _cells(r.content, 30)[0][0] == "Zähl-Kassenstand:"
    assert _cells(r.content, 30)[1][1] == "5"
    assert _cells(r.content, 31)[0][0] == "Soll-Kassenstand:"
    assert _cells(r.content, 32)[0][0] == "Differenz"
    assert _cells(r.content, 33)[0][0] == "Kommentar"
    assert _cells(r.content, 33)[1][0] == "passt"


def test_settlement_ods_without_count_protocol(client, session, templates):
    settlement = _seed_settlement(session)
    session.exec(delete(ZaehlprotokollDetails))
    session.exec(delete(Zaehlprotokoll))
    session.commit()

    r = client.get(f"/export/abrechnung/tag/{settlement.id}/ods")
    assert r.status_code == 200
    assert _cells(r.content, 9)[1][1] == "33.3"


def test_unknown_settlement_is_404(client, templates):
    assert client.get("/export/abrechnung/tag/999/ods").status_code == 404
