"""Cart endpoint tests: Pfand expansion, discounts, totals."""
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from python.main import app
from python.models import Artikel, Lieferant, Mwst, Pfand, Produktgruppe
from python.session import get_session


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _seed(session):
    m = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    l = Lieferant(lieferant_name="Lieferant", lieferant_kurzname="L1")
    session.add(l)
    session.commit()
    session.refresh(l)

    def pg(name):
        row = Produktgruppe(produktgruppen_name=name, mwst_id=m.mwst_id)
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    def artikel(nr, preis, produktgruppe, name=None, variabel=False):
        row = Artikel(
            artikel_nr=nr, artikel_name=name or f"Artikel {nr}",
            produktgruppen_id=produktgruppe.produktgruppen_id,
            lieferant_id=l.lieferant_id, vk_preis=preis, variabler_preis=variabel,
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row

    pfand_pg = pg("Pfand")
    pfand_artikel = artikel("PFAND1", 1.5, pfand_pg, name="Pfandflasche")
    pfand = Pfand(artikel_id=pfand_artikel.artikel_id)
    session.add(pfand)
    session.commit()
    session.refresh(pfand)
    pfand_pg.pfand_id = pfand.pfand_id
    session.add(pfand_pg)
    session.commit()

    with_pfand = artikel("A1", 10.0, pfand_pg)
    without_pfand = artikel("A2", 4.0, pg("Normal"))
    variabel = artikel("VAR", None, pg("Variabel"), variabel=True)
    # Special articles used by the discount lines.
    artikel("RABATT1", None, pg("Rabatt"), name="Rabatt")
    artikel("RABATT2", None, pg("Rabatt"), name="Rabatt auf Rechnung")
    artikel("ANZAHLUNG", None, pg("Anzahlung"), name="Anzahlung")
    return with_pfand, without_pfand, variabel


def test_hinzufuegen_adds_pfand_child(client, session):
    with_pfand, _, _ = _seed(session)
    r = client.post("/warenkorb/hinzufuegen", json={
        "artikel_id": with_pfand.artikel_id, "stueckzahl": 3, "ref": "r1"})
    assert r.status_code == 200
    rows = r.json()
    assert [row["kind"] for row in rows] == ["artikel", "pfand"]
    assert rows[0]["ges_preis"] == 30.0
    assert rows[1]["parent_ref"] == "r1"
    assert rows[1]["stueckzahl"] == 3
    assert rows[1]["ges_preis"] == 4.5
    assert rows[1]["lieferant_kurzname"] == "L1"


def test_hinzufuegen_without_pfand(client, session):
    _, without_pfand, _ = _seed(session)
    rows = client.post("/warenkorb/hinzufuegen", json={
        "artikel_id": without_pfand.artikel_id}).json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "artikel"
    assert rows[0]["ges_preis"] == 4.0


def test_hinzufuegen_variable_price(client, session):
    _, _, variabel = _seed(session)
    rows = client.post("/warenkorb/hinzufuegen", json={
        "artikel_id": variabel.artikel_id, "preis": 7.5}).json()
    assert rows[0]["ges_preis"] == 7.5
    assert rows[0]["einzelpreis"] == 7.5


def test_leergut_returns_negative_pfand(client, session):
    with_pfand, _, _ = _seed(session)
    r = client.post("/warenkorb/leergut", json={
        "artikel_id": with_pfand.artikel_id, "stueckzahl": 2})
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "leergut"
    assert rows[0]["ges_preis"] == -3.0
    assert rows[0]["stueckzahl"] == 2


def test_leergut_without_pfand_rejected(client, session):
    _, without_pfand, _ = _seed(session)
    r = client.post("/warenkorb/leergut", json={"artikel_id": without_pfand.artikel_id})
    assert r.status_code == 400


def test_rabatt_returns_synced_rows(client, session):
    with_pfand, _, _ = _seed(session)
    r = client.post("/warenkorb/rabatt", json={
        "positionen": [{
            "ref": "r1", "artikel_id": with_pfand.artikel_id,
            "stueckzahl": 2, "ges_preis": 20.0,
        }],
        "rabatt": {"art": "relativ", "wert": 0.1},
    })
    assert r.status_code == 200
    rows = r.json()
    echoed = rows[0]
    assert echoed["ref"] == "r1"
    assert echoed["rabatt_absolut"] == 1.0
    assert echoed["hat_rabatt"] is True
    rabatt_rows = [row for row in rows if row["kind"] == "rabatt"]
    assert len(rabatt_rows) == 1
    assert rabatt_rows[0]["ges_preis"] == -2.0
    assert rabatt_rows[0]["stueckzahl"] == 2
    assert rabatt_rows[0]["parent_ref"] == "r1"


def test_rabatt_exceeding_line_rejected(client, session):
    _, without_pfand, _ = _seed(session)
    r = client.post("/warenkorb/rabatt", json={
        "positionen": [{
            "ref": "r1", "artikel_id": without_pfand.artikel_id,
            "stueckzahl": 1, "ges_preis": 4.0,
        }],
        "rabatt": {"art": "absolut", "wert": 5.0},
    })
    assert r.status_code == 400


def test_rechnung_rabatt_one_row_per_vat_rate(client, session):
    with_pfand, without_pfand, _ = _seed(session)
    r = client.post("/warenkorb/rabatt", json={
        "positionen": [
            {"ref": "r1", "artikel_id": with_pfand.artikel_id, "stueckzahl": 1},
            {"ref": "r2", "artikel_id": without_pfand.artikel_id, "stueckzahl": 1},
        ],
        "rabatt": {"art": "relativ", "wert": 0.1},
        "rechnung": True,
    })
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 1
    assert rows[0]["kind"] == "rechnung_rabatt"
    # 10 % of the article rows (Pfand is not discounted): 10.00 + 4.00
    assert rows[0]["ges_preis"] == -1.40


def test_summen(client, session):
    with_pfand, _, _ = _seed(session)
    rows = client.post("/warenkorb/hinzufuegen", json={
        "artikel_id": with_pfand.artikel_id}).json()
    r = client.post("/warenkorb/summen", json={"positionen": rows, "kunde_gibt": 20.0})
    assert r.status_code == 200
    totals = r.json()
    assert totals["zwischensumme"] == 11.5
    assert totals["zu_zahlen"] == 11.5
    assert totals["rueckgeld"] == 8.5
    assert len(totals["mwst"]) == 1
    assert totals["mwst"][0]["mwst_satz"] == 0.19
    assert totals["mwst"][0]["brutto"] == 11.5
    assert Decimal(str(totals["mwst"][0]["mwst_betrag"])) == Decimal("1.84")


def test_summen_with_discount_rows(client, session):
    _, without_pfand, _ = _seed(session)
    rows = client.post("/warenkorb/hinzufuegen", json={
        "artikel_id": without_pfand.artikel_id}).json()
    discounted = client.post("/warenkorb/rabatt", json={
        "positionen": [{
            "ref": "r1", "artikel_id": without_pfand.artikel_id,
            "stueckzahl": 1, "ges_preis": 4.0,
        }],
        "rabatt": {"art": "relativ", "wert": 0.25},
    }).json()
    all_rows = rows + [row for row in discounted if row["kind"] == "rabatt"]
    totals = client.post("/warenkorb/summen", json={"positionen": all_rows}).json()
    assert totals["zwischensumme"] == 4.0
    assert totals["rabatte"] == 1.0
    assert totals["zu_zahlen"] == 3.0


def test_anzahlung_preview_zeroes_articles_and_adds_deposit_rows(client, session):
    _, without_pfand, _ = _seed(session)
    r = client.post("/warenkorb/anzahlung", json={
        "positionen": [{
            "ref": "r1", "artikel_id": without_pfand.artikel_id,
            "stueckzahl": 1, "ges_preis": 4.0,
        }],
        "betrag": 3.0,
    })
    assert r.status_code == 200, r.json()
    rows = r.json()
    assert rows[0]["ges_preis"] == 0.0
    anzahlung_rows = [row for row in rows if row["kind"] == "anzahlung"]
    assert len(anzahlung_rows) == 1
    assert anzahlung_rows[0]["ges_preis"] == 3.0
