import pytest
from fastapi.testclient import TestClient
from python.main import app
from python.session import get_session


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_abrechnung_tag_flow(client):
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tid = r.json()["id"]
    r = client.get(f"/abrechnung/tag/{tid}")
    assert r.status_code == 200
    r = client.get("/abrechnung/tag/")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = client.get("/abrechnung/tag/offen")
    assert r.status_code == 200


def test_abrechnung_monat_flow(client):
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 200
    mid = r.json()["id"]
    r = client.get(f"/abrechnung/monat/{mid}")
    assert r.status_code == 200
    r = client.get("/abrechnung/monat/offen")
    assert r.status_code == 200


def test_abrechnung_jahr_flow(client):
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/jahr/", json={})
    assert r.status_code == 200
    jid = r.json()["id"]
    r = client.get(f"/abrechnung/jahr/{jid}")
    assert r.status_code == 200
    r = client.get("/abrechnung/jahr/offen")
    assert r.status_code == 200