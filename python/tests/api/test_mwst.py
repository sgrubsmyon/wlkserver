import pytest

from fastapi.testclient import TestClient

from python.main import app

from python.session import get_session

from python.models import (
    Mwst,
    Produktgruppe,
    User,
)

from python.utils.auth import hash_password


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def test_post_mwst_requires_admin(client, session):
    payload = {"mwst_satz": 0.19, "dsfinvk_ust_schluessel": 1, "dsfinvk_ust_beschr": "19%"}
    r = client.post("/mwst/", json=payload)
    assert r.status_code == 403

    admin = User(username="admin", password_hash=hash_password("admin"), role="admin", active=True)
    admin.user_id = None
    session.add(admin)
    session.commit()
    r = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    headers = {"Authorization": "Bearer " + r.json()["access_token"]}
    r = client.post("/mwst/", json=payload, headers=headers)
    assert r.status_code == 200
