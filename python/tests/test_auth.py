import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.models import Anmeldung, User
from python.routers import auth as auth_router
from python.session import get_session
from python.utils.auth import hash_password, verify_password, create_token, decode_token


@pytest.fixture(autouse=True)
def clear_login_failures():
    auth_router._login_failures.clear()
    yield
    auth_router._login_failures.clear()


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def _login(client, username="test", password="test"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    token = r.json().get("access_token")
    return r, {"Authorization": f"Bearer {token}"} if token else {}


def test_hash_and_verify_password():
    h = hash_password("secret")
    assert verify_password("secret", h)
    assert not verify_password("wrong", h)


def test_create_and_decode_token():
    token = create_token({"user_id": 1, "role": "admin"})
    payload = decode_token(token)
    assert payload is not None
    assert payload["user_id"] == 1
    assert payload["role"] == "admin"


def test_decode_invalid_token():
    assert decode_token("not.a.token") is None
    assert decode_token("") is None


def test_user_model_roundtrip(session):
    u = User(username="alice", password_hash=hash_password("pw"), role="mitarbeiter", active=True)
    u.user_id = None
    session.add(u)
    session.commit()
    session.refresh(u)
    assert u.user_id is not None
    fetched = session.get(User, u.user_id)
    assert fetched.username == "alice"
    assert verify_password("pw", fetched.password_hash)


def test_login_me_refresh_and_logout(client, session):
    r, headers = _login(client)
    assert r.status_code == 200
    assert client.get("/auth/me", headers=headers).status_code == 200

    refreshed = client.post("/auth/refresh", headers=headers)
    assert refreshed.status_code == 200
    new_headers = {"Authorization": "Bearer " + refreshed.json()["access_token"]}
    assert client.get("/auth/me", headers=new_headers).status_code == 200

    assert client.post("/auth/logout", headers=new_headers).status_code == 200
    anmeldung = session.exec(select(Anmeldung)).one()
    assert anmeldung.logout_time is not None
    assert client.get("/auth/me", headers=new_headers).status_code == 401
    assert client.post("/auth/refresh", headers=new_headers).status_code == 401


def test_login_rejects_inactive_user(client, session):
    u = User(username="inactive", password_hash=hash_password("pw"), role="mitarbeiter", active=False)
    u.user_id = None
    session.add(u)
    session.commit()
    r, _ = _login(client, "inactive", "pw")
    assert r.status_code == 401


def test_login_is_rate_limited(client):
    for _ in range(auth_router.LOGIN_MAX_FAILURES):
        r, _ = _login(client, "ratelimit", "wrong")
        assert r.status_code == 401
    r, _ = _login(client, "ratelimit", "wrong")
    assert r.status_code == 429


def test_read_endpoints_require_login(client):
    assert client.get("/artikel/").status_code == 401
    _, headers = _login(client)
    assert client.get("/artikel/", headers=headers).status_code == 200


def test_login_audit_requires_admin(client, session):
    _, headers = _login(client)
    assert client.get("/auth/anmeldungen", headers=headers).status_code == 403

    admin = User(username="admin", password_hash=hash_password("admin"), role="admin", active=True)
    admin.user_id = None
    session.add(admin)
    session.commit()
    _, admin_headers = _login(client, "admin", "admin")
    r = client.get("/auth/anmeldungen", headers=admin_headers)
    assert r.status_code == 200
    assert {row["user_id"] for row in r.json()} == {session.exec(select(User).where(User.username == "test")).one().user_id, admin.user_id}