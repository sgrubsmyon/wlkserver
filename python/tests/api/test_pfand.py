import pytest

from fastapi.testclient import TestClient

from python.main import app

from python.session import get_session


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def test_post_pfand_requires_admin(client):
    r = client.post("/pfand/", json={"artikel_id": 1})
    assert r.status_code == 403
    r = client.post("/pfand/", json={"artikel_id": 1}, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401
