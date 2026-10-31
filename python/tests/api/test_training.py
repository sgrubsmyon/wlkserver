import pytest

from fastapi.testclient import TestClient

from python.main import app

from python.session import get_session


@pytest.fixture
def production_client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def test_status_without_training_mode(production_client):
    r = production_client.get("/training/status")
    assert r.status_code == 200
    assert r.json() == {"training_mode": False}
