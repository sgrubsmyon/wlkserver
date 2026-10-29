import io
import zipfile
from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from python.main import app
from python.session import get_session
from python.models import (
    AbrechnungTag,
    AbrechnungTagMwst,
    AbrechnungTagTse,
    Artikel,
    Kassenstand,
    Lieferant,
    Mwst,
    Pfand,
    Produktgruppe,
    TSETransaction,
    Verkauf,
    VerkaufDetails,
    VerkaufMwst,
)
from python.business.dsfinvk_export import build_dsfinvk_files


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


EXPORT_FILES = {
    "cashpointclosing.csv",
    "location.csv",
    "cashregister.csv",
    "slaves.csv",
    "pa.csv",
    "vat.csv",
    "tse.csv",
    "businesscases.csv",
    "transactions_tse.csv",
}


def _rows(content: bytes) -> list[dict]:
    lines = content.decode("utf-8").split("\r\n")[:-1]

    def cell(value: str) -> str:
        if len(value) >= 2 and value[0] == '"' and value[-1] == '"':
            return value[1:-1].replace('""', '"')
        return value

    header = [cell(v) for v in lines[0].split(";")]
    return [dict(zip(header, (cell(v) for v in line.split(";")))) for line in lines[1:]]


def _seed_export(session, monkeypatch):
    monkeypatch.setenv("DSFINVK_NAME", "Weltladen")
    monkeypatch.setenv("DSFINVK_ORT", "Bonn")
    monkeypatch.setenv("DSFINVK_STRASSE", "Markt 1")
    monkeypatch.setenv("DSFINVK_LOC_STRASSE", "Markt 1")
    monkeypatch.setenv("DSFINVK_PLZ", "53111")
    monkeypatch.setenv("DSFINVK_LAND", "DEU")
    monkeypatch.setenv("DSFINVK_STNR", "123/456/789")

    mwst0 = Mwst(mwst_satz=0.0, dsfinvk_ust_schluessel=0, dsfinvk_ust_beschr="0%")
    mwst19 = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1, dsfinvk_ust_beschr="19%")
    mwst7 = Mwst(mwst_satz=0.07, dsfinvk_ust_schluessel=2, dsfinvk_ust_beschr="7%")
    session.add_all([mwst0, mwst19, mwst7])
    session.commit()
    for row in (mwst0, mwst19, mwst7):
        session.refresh(row)

    pg19 = Produktgruppe(produktgruppen_name="Normale Ware", mwst_id=mwst19.mwst_id)
    pg0 = Produktgruppe(produktgruppen_name="Gutschein", mwst_id=mwst0.mwst_id)
    lieferant = Lieferant(lieferant_name="Testlieferant")
    session.add_all([pg19, pg0, lieferant])
    session.commit()
    for row in (pg19, pg0, lieferant):
        session.refresh(row)

    def artikel(nr, name, pg, preis=10.0):
        row = Artikel(
            artikel_nr=nr, artikel_name=name, produktgruppen_id=pg.produktgruppen_id,
            lieferant_id=lieferant.lieferant_id, vk_preis=preis,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    normal = artikel("A1", "Artikel", pg19)
    pfand_artikel = artikel("PF1", "Pfand", pg19, 2.0)
    rabatt = artikel("RABATT1", "Rabatt", pg19)
    aufschlag = artikel("ANPASSUNG", "Anpassung", pg19)
    gutschein = artikel("GUTSCHEIN", "Gutschein", pg0, 10.0)
    einloesung = artikel("GUTSCHEINEINLOES", "Gutscheineinlösung", pg0)
    session.add(Pfand(artikel_id=pfand_artikel.artikel_id))
    session.commit()

    opening = Kassenstand(
        buchungsdatum=datetime(2026, 10, 28, 9, 0),
        neuer_kassenstand=200.0,
        manuell=True,
        entnahme=False,
        kommentar="Tagesabschluss",
    )
    session.add(opening)
    session.commit()
    session.refresh(opening)

    sale = Verkauf(verkaufsdatum=datetime(2026, 10, 28, 12, 0), ec_zahlung=False)
    session.add(sale)
    session.commit()
    session.refresh(sale)

    positions = [
        (1, 2, 20.0, 0.19, normal.artikel_id),
        (2, 2, 4.0, 0.19, pfand_artikel.artikel_id),
        (3, -1, -2.0, 0.19, pfand_artikel.artikel_id),
        (None, 1, -2.0, 0.19, rabatt.artikel_id),
        (None, 1, 1.0, 0.19, aufschlag.artikel_id),
        (4, 1, 10.0, 0.0, gutschein.artikel_id),
        (None, 1, -5.0, 0.0, einloesung.artikel_id),
    ]
    for position, stueckzahl, preis, satz, artikel_id in positions:
        session.add(VerkaufDetails(
            rechnungs_nr=sale.rechnungs_nr, position=position, stueckzahl=stueckzahl,
            ges_preis=preis, mwst_satz=satz, artikel_id=artikel_id,
        ))
    session.add_all([
        VerkaufMwst(rechnungs_nr=sale.rechnungs_nr, mwst_satz=0.19,
                    mwst_netto=17.65, mwst_betrag=3.35),
        VerkaufMwst(rechnungs_nr=sale.rechnungs_nr, mwst_satz=0.0,
                    mwst_netto=5.0, mwst_betrag=0.0),
    ])
    session.commit()

    # A previous settlement bounds the TSE transaction window and the opening balance.
    previous = AbrechnungTag(
        z_kasse_id="K1",
        zeitpunkt=datetime(2026, 10, 27, 18, 0),
        zeitpunkt_real=datetime(2026, 10, 27, 18, 0),
        kassenstand_id=None,
        rechnungs_nr_von=sale.rechnungs_nr,
        rechnungs_nr_bis=sale.rechnungs_nr,
    )
    session.add(previous)
    session.commit()

    tag = AbrechnungTag(
        z_kasse_id="K1",
        zeitpunkt=datetime(2026, 10, 28, 18, 0),
        zeitpunkt_real=datetime(2026, 10, 28, 18, 0),
        kassenstand_id=opening.kassenstand_id,
        rechnungs_nr_von=sale.rechnungs_nr,
        rechnungs_nr_bis=sale.rechnungs_nr,
    )
    session.add(tag)
    session.commit()
    session.refresh(tag)

    session.add_all([
        AbrechnungTagMwst(id=tag.id, mwst_satz=0.19, mwst_netto=17.65,
                          mwst_betrag=3.35, bar_brutto=21.0),
        AbrechnungTagMwst(id=tag.id, mwst_satz=0.0, mwst_netto=5.0,
                          mwst_betrag=0.0, bar_brutto=5.0),
        AbrechnungTagTse(id=tag.id, tse_id=7, tse_serial="SER-1",
                         tse_sig_algo="ecdsa-plain-SHA256", tse_pd_encoding="UTF-8"),
        TSETransaction(
            rechnungs_nr=sale.rechnungs_nr, transaction_number=42,
            transaction_start="2026-10-28T12:00:00.000+01:00",
            transaction_end="2026-10-28T12:00:01.000+01:00",
            process_type="Kassenbeleg-V1", signature_counter=5,
            signature_base64="c2ln", process_data="pd",
        ),
        TSETransaction(
            rechnungs_nr=sale.rechnungs_nr, transaction_number=41,
            transaction_start="2026-10-27T12:00:00.000+01:00",
            process_type="Kassenbeleg-V1", signature_counter=4,
        ),
    ])
    session.commit()
    return tag, sale


def test_builds_all_files_with_index_header(session, monkeypatch):
    tag, _ = _seed_export(session, monkeypatch)
    files = build_dsfinvk_files(session, tag.id)

    assert set(files) == EXPORT_FILES
    assert files["pa.csv"].decode() == (
        "Z_KASSE_ID;Z_ERSTELLUNG;Z_NR;AGENTUR_ID;AGENTUR_NAME;AGENTUR_STRASSE;"
        "AGENTUR_PLZ;AGENTUR_ORT;AGENTUR_LAND;AGENTUR_STNR;AGENTUR_USTID\r\n"
    )
    assert files["businesscases.csv"].decode().startswith(
        "Z_KASSE_ID;Z_ERSTELLUNG;Z_NR;GV_TYP;GV_NAME;AGENTUR_ID;"
        "UST_SCHLUESSEL;Z_UMS_BRUTTO;Z_UMS_NETTO;Z_UST\r\n"
    )


def test_businesscases_follow_java_buckets(session, monkeypatch):
    tag, _ = _seed_export(session, monkeypatch)
    rows = _rows(build_dsfinvk_files(session, tag.id)["businesscases.csv"])

    opening = [r for r in rows if r["GV_TYP"] == "Anfangsbestand"]
    assert len(opening) == 1
    assert opening[0]["Z_UMS_BRUTTO"] == "200,00000"
    assert opening[0]["Z_UMS_NETTO"] == "200,00000"
    assert opening[0]["UST_SCHLUESSEL"] == "0"

    umsatz = {r["UST_SCHLUESSEL"]: r for r in rows if r["GV_TYP"] == "Umsatz"}
    assert umsatz["1"]["Z_UMS_BRUTTO"] == "21,00000"
    assert umsatz["1"]["Z_UMS_NETTO"] == "17,65000"
    assert umsatz["1"]["Z_UST"] == "3,35000"
    assert umsatz["0"]["Z_UMS_BRUTTO"] == "5,00000"

    pfand = [r for r in rows if r["GV_TYP"] == "Pfand"]
    assert pfand[0]["Z_UMS_BRUTTO"] == "4,00000"
    assert pfand[0]["Z_UMS_NETTO"] == "3,36000"
    assert pfand[0]["Z_UST"] == "0,64000"
    rueckzahlung = [r for r in rows if r["GV_TYP"] == "PfandRueckzahlung"]
    assert rueckzahlung[0]["Z_UMS_BRUTTO"] == "-2,00000"
    assert rueckzahlung[0]["Z_UMS_NETTO"] == "-1,68000"

    rabatt = [r for r in rows if r["GV_TYP"] == "Rabatt"]
    assert rabatt[0]["Z_UMS_BRUTTO"] == "-2,00000"
    aufschlag = [r for r in rows if r["GV_TYP"] == "Aufschlag"]
    assert aufschlag[0]["Z_UMS_BRUTTO"] == "1,00000"
    kauf = [r for r in rows if r["GV_TYP"] == "MehrzweckgutscheinKauf"]
    assert kauf[0]["Z_UMS_BRUTTO"] == "10,00000"
    einloesung = [r for r in rows if r["GV_TYP"] == "MehrzweckgutscheinEinloesung"]
    assert einloesung[0]["Z_UMS_BRUTTO"] == "-5,00000"


def test_stammdaten_and_vat_files(session, monkeypatch):
    tag, _ = _seed_export(session, monkeypatch)
    files = build_dsfinvk_files(session, tag.id)

    vat = _rows(files["vat.csv"])
    assert [r["UST_SCHLUESSEL"] for r in vat] == ["0", "1", "2"]
    assert [r["UST_SATZ"] for r in vat] == ["0,00", "19,00", "7,00"]
    assert vat[1]["UST_BESCHR"] == "19%"

    closing = _rows(files["cashpointclosing.csv"])[0]
    assert closing["NAME"] == "Weltladen"
    assert closing["ORT"] == "Bonn"
    assert closing["Z_BUCHUNGSTAG"] == "2026-10-28"
    assert closing["Z_SE_ZAHLUNGEN"] == "26,00"
    assert closing["Z_SE_BARZAHLUNGEN"] == "26,00"

    location = _rows(files["location.csv"])[0]
    assert location["LOC_STRASSE"] == "Markt 1"
    assert location["LOC_USTID"] == ""  # not configured -> empty field

    cashregister = _rows(files["cashregister.csv"])[0]
    assert cashregister["KEINE_UST_ZUORDNUNG"] == "0"


def test_tse_files(session, monkeypatch):
    tag, sale = _seed_export(session, monkeypatch)
    files = build_dsfinvk_files(session, tag.id)

    tse = _rows(files["tse.csv"])[0]
    assert tse["TSE_ID"] == "7"
    assert tse["TSE_SERIAL"] == "SER-1"

    transactions = _rows(files["transactions_tse.csv"])
    assert len(transactions) == 1
    assert transactions[0]["BON_ID"] == str(sale.rechnungs_nr)
    assert transactions[0]["TSE_TANR"] == "42"
    assert transactions[0]["TSE_ID"] == "7"
    assert transactions[0]["TSE_TA_SIG"] == "c2ln"


def test_export_endpoint_returns_zip(session, monkeypatch, client):
    tag, _ = _seed_export(session, monkeypatch)
    response = client.get(f"/export/dsfinvk/{tag.id}")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        names = set(archive.namelist())
    assert {"index.xml", "gdpdu-01-09-2004.dtd"} | EXPORT_FILES <= names

    assert client.get("/export/dsfinvk/9999").status_code == 404


def test_settlement_writes_export_to_configured_dir(session, monkeypatch, client, tmp_path):
    monkeypatch.setenv("DSFINVK_EXPORT_DIR", str(tmp_path))
    monkeypatch.setenv("DSFINVK_NAME", "Weltladen")

    mwst = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    session.add(mwst)
    session.commit()
    session.refresh(mwst)
    pg = Produktgruppe(produktgruppen_name="Ware", mwst_id=mwst.mwst_id)
    lieferant = Lieferant(lieferant_name="Lieferant")
    session.add_all([pg, lieferant])
    session.commit()
    session.refresh(pg)
    session.refresh(lieferant)
    artikel = Artikel(
        artikel_nr="A1", artikel_name="Artikel",
        produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=lieferant.lieferant_id, vk_preis=10.0,
    )
    session.add(artikel)
    session.commit()
    session.refresh(artikel)

    sale = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": artikel.artikel_id, "stueckzahl": 2}],
    })
    assert sale.status_code == 200
    settlement = client.post("/abrechnung/tag/", json={})
    assert settlement.status_code == 200

    path = tmp_path / f"dsfinvk_{settlement.json()['id']}.zip"
    assert path.exists()
    with zipfile.ZipFile(path) as archive:
        cases = archive.read("businesscases.csv").decode()
    assert "Umsatz" in cases
