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


def test_kassenstand_crud(client):
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    assert r.status_code == 200
    ks_id = r.json()["kassenstand_id"]
    r = client.get("/kassenstand/aktuell")
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 100.0
    r = client.get(f"/kassenstand/{ks_id}")
    assert r.status_code == 200
    r = client.get("/kassenstand/")
    assert r.status_code == 200
    assert len(r.json()) == 1


def test_gutschein_crud(client):
    r = client.post("/gutschein/", json={"gutschein_nr": 1, "restbetrag": 10.0})
    assert r.status_code == 200
    gid = r.json()["gutschein_id"]
    r = client.get(f"/gutschein/{gid}")
    assert r.status_code == 200
    r = client.get("/gutschein/ausstehend")
    assert r.status_code == 200
    assert len(r.json()) == 1
    # redeem
    r = client.post(f"/gutschein/{gid}/einloesen", json={"restbetrag": 0.0})
    assert r.status_code == 200
    r = client.get("/gutschein/eingeloest")
    assert r.status_code == 200
    assert len(r.json()) >= 1


def test_anzahlung_crud(client):
    # need verkauf row
    from python.models import Verkauf
    from datetime import datetime, timezone
    # use session? client only; create verkauf via endpoint
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    rn = r.json()["rechnungs_nr"]
    r = client.post("/anzahlung/", json={"anzahlung_in_rech_nr": rn})
    assert r.status_code == 200
    aid = r.json()["anzahlung_id"]
    r = client.get(f"/anzahlung/{aid}")
    assert r.status_code == 200
    r = client.get("/anzahlung/offen")
    assert r.status_code == 200
    # resolve
    r2 = client.post("/verkauf/", json={})
    rn2 = r2.json()["rechnungs_nr"]
    r = client.post(f"/anzahlung/{aid}/aufloesen", json={"aufloesung_in_rech_nr": rn2})
    assert r.status_code == 200
    r = client.get("/anzahlung/aufgeloest")
    assert r.status_code == 200
    assert len(r.json()) >= 1