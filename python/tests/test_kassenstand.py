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


def test_create_and_read(client):
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    assert r.status_code == 200
    ks_id = r.json()["kassenstand_id"]
    r = client.get(f"/kassenstand/{ks_id}")
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 100.0
    r = client.get("/kassenstand/aktuell")
    assert r.status_code == 200


def test_rechnungen_filter(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 50.0, "manuell": True})
    client.post("/kassenstand/", json={"neuer_kassenstand": 60.0, "manuell": False})
    r = client.get("/kassenstand/")
    assert all(k["manuell"] for k in r.json())
    r = client.get("/kassenstand/?rechnungen=true")
    assert len(r.json()) >= 2


def test_negative_rejected(client):
    r = client.post("/kassenstand/", json={"neuer_kassenstand": -1.0, "manuell": True})
    assert r.status_code == 422


def test_entnahme_must_not_increase_balance(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 150.0, "manuell": True, "entnahme": True})
    assert r.status_code == 400


def test_entnahme_below_zero_rejected(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 20.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": -5.0, "manuell": True, "entnahme": True})
    assert r.status_code == 422


def test_validate_balance_change_entnahme_exceeds_balance(session):
    from fastapi import HTTPException
    from python.business.cash_register import validate_balance_change
    with pytest.raises(HTTPException):
        validate_balance_change(10.0, -5.0, entnahme=True)


def test_valid_entnahme_accepted(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 40.0, "manuell": True, "entnahme": True})
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 40.0