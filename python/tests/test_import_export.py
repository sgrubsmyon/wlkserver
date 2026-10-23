import pytest
from fastapi.testclient import TestClient

from python.main import app
from python.session import get_session


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
        "EINKAUF,2026-01-15T00:00:00,2026,3\n"
    )
    r = client.post(
        "/import/bestellung",
        files={"file": ("bestellung.csv", csv_content.encode("utf-8"), "text/csv")},
    )
    assert r.status_code == 200
    assert r.json()["imported"] == 1


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
