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


def test_crud(client):
    r = client.post("/bestellung/", json={"typ": "L", "jahr": 2026, "kw": 1})
    assert r.status_code == 200
    bid = r.json()["bestell_nr"]
    r = client.get(f"/bestellung/{bid}")
    assert r.status_code == 200
    r = client.patch(f"/bestellung/{bid}", json={"kw": 3})
    assert r.status_code == 200
    assert r.json()["kw"] == 3
    r = client.delete(f"/bestellung/{bid}")
    assert r.status_code == 200
    r = client.get(f"/bestellung/{bid}")
    assert r.status_code == 404