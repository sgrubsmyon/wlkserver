import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.session import get_session
from python.models import Artikel


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def test_import_artikel_csv(client):
    csv_content = (
        "artikel_nr,artikel_name,vk_preis,variabler_preis\n"
        "001,Test Artikel,10.00,false\n"
        "002,Other Artikel,20.00,true\n"
    )
    r = client.post(
        "/import/artikel",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 2


def test_export_artikel_csv(client):
    # Import some articles first
    csv_content = "artikel_nr,artikel_name,vk_preis\n001,Test,10.00\n"
    client.post(
        "/import/artikel",
        files={"file": ("test.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    r = client.get("/export/artikel")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "artikel_id" in r.text
    assert "001" in r.text


def test_import_bestellung_csv(client):
    csv_content = (
        "typ,bestell_datum,jahr,kw\n"
        "LM,2026-01-15T00:00:00,2026,3\n"
    )
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1


def test_import_bestellung_csv_defaults_to_lm(client):
    csv_content = "typ,bestell_datum,jahr,kw\n,2026-01-15T00:00:00,2026,3\n"
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert client.get("/bestellung/").json()[0]["typ"] == "LM"


def test_import_bestellung_invalid_typ(client):
    csv_content = "typ,bestell_datum,jahr,kw\nEINKAUF,2026-01-15T00:00:00,2026,3\n"
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 400


def test_import_bestellung_with_positions(client, session):
    csv_content = (
        "artikel_nr,artikel_name,vk_preis\n"
        "001,Erster Artikel,10.00\n"
        "002,Zweiter Artikel,20.00\n"
    )
    client.post(
        "/import/artikel",
        files={"file": ("artikel.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    ids = [a.artikel_id for a in session.exec(select(Artikel).order_by(Artikel.artikel_id)).all()]

    bestellung_csv = (
        "typ,bestell_datum,jahr,kw,artikel_id,stueckzahl,position\n"
        f"KHW,2026-01-15T00:00:00,2026,3,{ids[0]},5,1\n"
        f"KHW,2026-01-15T00:00:00,2026,3,{ids[1]},2,2\n"
    )
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", bestellung_csv.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1

    bestell_nr = client.get("/bestellung/").json()[0]["bestell_nr"]
    r = client.get(f"/bestellung/{bestell_nr}")
    assert r.status_code == 200
    details = r.json()["details"]
    assert len(details) == 2
    assert details[0]["artikel_id"] == ids[0]
    assert details[0]["stueckzahl"] == 5
    assert details[1]["position"] == 2


def test_import_bestellung_unknown_artikel(client):
    csv_content = (
        "typ,bestell_datum,jahr,kw,artikel_id,stueckzahl\n"
        "LM,2026-01-15T00:00:00,2026,3,99999,1\n"
    )
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 400


def test_export_bestellung_csv(client, session):
    csv_content = (
        "artikel_nr,artikel_name,vk_preis,empf_vk_preis,ek_preis\n"
        "001,Erster Artikel,10.00,11.00,5.00\n"
        "002,Zweiter Artikel,20.00,,8.00\n"
    )
    client.post(
        "/import/artikel",
        files={"file": ("artikel.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    ids = [a.artikel_id for a in session.exec(select(Artikel).order_by(Artikel.artikel_id)).all()]
    r = client.post("/bestellung/", json={
        "typ": "LM", "jahr": 2026, "kw": 3,
        "details": [{"position": 1, "artikel_id": ids[0], "stueckzahl": 4}],
    })
    assert r.status_code == 200

    r = client.get("/export/bestellung")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("bestell_nr,typ,bestell_datum")
    assert "001" in lines[1]
    # recommended VK price wins over vk_preis, like the Java POS
    assert "11.0" in lines[1]
    assert lines[1].endswith(",4")


def test_export_inventur_csv(client, session):
    from python.models import Mwst, Produktgruppe, Lieferant

    m = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name="Test PG", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    l = Lieferant(lieferant_name="Test Lieferant", lieferant_kurzname="TL")
    session.add(l)
    session.commit()
    session.refresh(l)
    a = Artikel(
        artikel_nr="IV1", artikel_name="Inventur Artikel",
        produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
        vk_preis=2.00, ek_preis=11.90, setgroesse=10, ek_rabatt=0.10,
    )
    session.add(a)
    session.commit()
    session.refresh(a)

    r = client.post("/bestellung/", json={
        "typ": "IVT", "jahr": 2026, "kw": 52,
        "details": [{"position": 1, "artikel_id": a.artikel_id, "stueckzahl": 5}],
    })
    assert r.status_code == 200

    r = client.get("/export/inventur")
    assert r.status_code == 200
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("bestell_nr,typ,jahr,lieferant")
    row = lines[1].split(",")
    # ek_preis 11.90 / setgroesse 10 = 1.19; 19 % VAT -> 0.19 tax, 1.00 net
    assert row[3] == "TL"
    assert row[8] == "10"          # setgroesse
    assert row[9] == "10.0"        # ek_rabatt in percent
    assert row[11] == "1.19"       # ek_preis per piece
    assert row[12] == "19.00"      # mwst percent
    assert row[13] == "1.00"       # netto per piece
    assert row[14] == "0.19"       # mwst per piece
    assert row[15] == "5"          # stueckzahl
    assert row[16] == "5.00"       # netto total
    assert row[17] == "0.95"       # mwst total
    assert row[18] == "5.95"       # ek brutto total
    assert row[19] == "10.00"      # vk brutto total
    # Inventur rows must not show up in the order export
    assert "Inventur Artikel" not in client.get("/export/bestellung").text


def test_export_abrechnung_csv(client):
    # Create a sale and day settlement so there's data to export
    client.post("/verkauf/", json={})
    client.post("/abrechnung/tag/", json={})
    r = client.get("/export/abrechnung")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/csv")
    assert "abrechnung_tag_id" in r.text


def test_import_artikel_empty_csv(client):
    csv_content = "artikel_nr,artikel_name,vk_preis\n"
    r = client.post(
        "/import/artikel",
        files={"file": ("empty.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 0
