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


def test_zaehlprotokoll_crud(client):
    # create abrechnung tag first
    client.post("/verkauf/", json={})
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tid = r.json()["id"]
    r = client.post("/zaehlprotokoll/", json={"abrechnung_tag_id": tid, "kommentar": "Zählung"})
    assert r.status_code == 200
    zid = r.json()["id"]
    r = client.get(f"/zaehlprotokoll/{zid}")
    assert r.status_code == 200
    r = client.get(f"/zaehlprotokoll/abrechnung/{tid}")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = client.patch(f"/zaehlprotokoll/{zid}", json={"kommentar": "updated"})
    assert r.status_code == 200
    assert r.json()["kommentar"] == "updated"


def test_bestellung_crud(client):
    r = client.post("/bestellung/", json={"typ": "L", "jahr": 2026, "kw": 1})
    assert r.status_code == 200
    bid = r.json()["bestell_nr"]
    r = client.get(f"/bestellung/{bid}")
    assert r.status_code == 200
    r = client.patch(f"/bestellung/{bid}", json={"kw": 2})
    assert r.status_code == 200
    assert r.json()["kw"] == 2
    r = client.delete(f"/bestellung/{bid}")
    assert r.status_code == 200
    r = client.get(f"/bestellung/{bid}")
    assert r.status_code == 404