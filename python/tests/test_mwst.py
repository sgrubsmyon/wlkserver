import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from pydantic import ValidationError

from python.main import app
from python.session import get_session
from python.models import Mwst, MwstCreate, MwstUpdate, Produktgruppe, User
from python.routers.mwst import create_mwst, update_mwst, delete_mwst, read_mwsts
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


# --- Create ---


def test_create_mwst(session):
    mwst = create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1, dsfinvk_ust_beschr="19%"), session)
    assert mwst.mwst_id is not None
    assert session.get(Mwst, mwst.mwst_id).mwst_satz == 0.19


def test_create_mwst_duplicate_rate_rejected(session):
    create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1), session)
    with pytest.raises(HTTPException) as exc:
        create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=8), session)
    assert exc.value.status_code == 400


def test_create_mwst_invalid_satz_rejected():
    with pytest.raises(ValidationError):
        MwstCreate(mwst_satz=1.5, dsfinvk_ust_schluessel=1)
    with pytest.raises(ValidationError):
        MwstCreate(mwst_satz=-0.1, dsfinvk_ust_schluessel=1)


# --- Update ---


def test_update_mwst(session):
    created = create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1, dsfinvk_ust_beschr="old"), session)
    updated = update_mwst(created.mwst_id, MwstUpdate(mwst_satz=0.07, dsfinvk_ust_beschr="new"), session)
    assert updated.mwst_satz == 0.07
    assert updated.dsfinvk_ust_beschr == "new"
    assert updated.dsfinvk_ust_schluessel == 1  # unchanged field stays as it was


def test_update_mwst_not_found(session):
    with pytest.raises(HTTPException) as exc:
        update_mwst(999, MwstUpdate(mwst_satz=0.07), session)
    assert exc.value.status_code == 404


def test_update_mwst_duplicate_rate_rejected(session):
    create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1), session)
    b = create_mwst(MwstCreate(mwst_satz=0.07, dsfinvk_ust_schluessel=2), session)
    with pytest.raises(HTTPException) as exc:
        update_mwst(b.mwst_id, MwstUpdate(mwst_satz=0.19), session)
    assert exc.value.status_code == 400


# --- Delete ---


def test_delete_mwst(session):
    created = create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1), session)
    result = delete_mwst(created.mwst_id, session)
    assert result["message"] == "MwSt deleted"
    assert session.get(Mwst, created.mwst_id) is None


def test_delete_mwst_not_found(session):
    with pytest.raises(HTTPException) as exc:
        delete_mwst(999, session)
    assert exc.value.status_code == 404


def test_delete_mwst_in_use_rejected(session):
    created = create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1), session)
    pg = Produktgruppe(
        toplevel_id=1, sub_id=2, produktgruppen_name="Test",
        mwst_id=created.mwst_id, aktiv=True, n_artikel=0, n_artikel_rekursiv=0,
    )
    session.add(pg)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        delete_mwst(created.mwst_id, session)
    assert exc.value.status_code == 409


# --- Read (regression) ---


def test_read_mwsts(session):
    create_mwst(MwstCreate(mwst_satz=0.19, dsfinvk_ust_schluessel=1), session)
    create_mwst(MwstCreate(mwst_satz=0.07, dsfinvk_ust_schluessel=2), session)
    mwsts = read_mwsts(session)
    assert len(mwsts) == 2
    assert mwsts[0].mwst_satz == 0.07  # ordered by mwst_satz
