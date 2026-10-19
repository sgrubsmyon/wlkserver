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
    r = client.post("/gutschein/", json={"gutschein_nr": 1, "restbetrag": 10.0})
    assert r.status_code == 200
    gid = r.json()["gutschein_id"]
    r = client.get(f"/gutschein/{gid}")
    assert r.status_code == 200


def test_ausstehend_eingeloest(client):
    r = client.post("/gutschein/", json={"gutschein_nr": 2, "restbetrag": 5.0})
    gid = r.json()["gutschein_id"]
    r = client.get("/gutschein/ausstehend")
    assert r.status_code == 200
    assert any(g["gutschein_id"] == gid for g in r.json())
    client.post(f"/gutschein/{gid}/einloesen", json={"restbetrag": 0.0})
    r = client.get("/gutschein/eingeloest")
    assert any(g["gutschein_id"] == gid or g["restbetrag"] <= 0 for g in r.json())


def test_negative_restbetrag_rejected(client):
    r = client.post("/gutschein/", json={"gutschein_nr": 3, "restbetrag": -1.0})
    assert r.status_code == 422