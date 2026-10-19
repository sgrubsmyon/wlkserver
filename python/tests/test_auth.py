import pytest

from python.utils.auth import hash_password, verify_password, create_token, decode_token
from python.models import User


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