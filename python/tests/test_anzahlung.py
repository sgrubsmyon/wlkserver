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


def test_flow(client):
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
    r2 = client.post("/verkauf/", json={})
    rn2 = r2.json()["rechnungs_nr"]
    r = client.post(f"/anzahlung/{aid}/aufloesen", json={"aufloesung_in_rech_nr": rn2})
    assert r.status_code == 200
    r = client.get("/anzahlung/aufgeloest")
    assert r.status_code == 200
    assert len(r.json()) >= 1