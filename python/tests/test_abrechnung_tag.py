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