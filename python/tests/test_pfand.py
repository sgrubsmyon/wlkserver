import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from python.main import app
from python.session import get_session
from python.models import Artikel, Pfand, PfandCreate, PfandUpdate, Produktgruppe
from python.routers.pfand import create_pfand, update_pfand, delete_pfand, read_pfands


def make_artikel(session, artikel_nr, artikel_name, vk_preis):
    artikel = Artikel(artikel_nr=artikel_nr, artikel_name=artikel_name, vk_preis=vk_preis)
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    return artikel


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


# --- Create ---


def test_create_pfand(session):
    artikel = make_artikel(session, "8", "Pfand 0,25", 0.25)
    pfand = create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    assert pfand.pfand_id is not None
    assert pfand.artikel_id == artikel.artikel_id
    assert pfand.wert == 0.25  # value is the selling price of the pfand article


def test_create_pfand_unknown_artikel_rejected(session):
    with pytest.raises(HTTPException) as exc:
        create_pfand(PfandCreate(artikel_id=999), session)
    assert exc.value.status_code == 400


def test_create_pfand_duplicate_rejected(session):
    artikel = make_artikel(session, "8", "Pfand 0,25", 0.25)
    create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    with pytest.raises(HTTPException) as exc:
        create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    assert exc.value.status_code == 400


def test_post_pfand_requires_admin(client):
    r = client.post("/pfand/", json={"artikel_id": 1})
    assert r.status_code == 403
    r = client.post("/pfand/", json={"artikel_id": 1}, headers={"Authorization": "Bearer wrong"})
    assert r.status_code == 401


# --- Update ---


def test_update_pfand(session):
    artikel1 = make_artikel(session, "8", "Pfand 0,25", 0.25)
    artikel2 = make_artikel(session, "9", "Pfand 0,15", 0.15)
    pfand = create_pfand(PfandCreate(artikel_id=artikel1.artikel_id), session)
    updated = update_pfand(pfand.pfand_id, PfandUpdate(artikel_id=artikel2.artikel_id), session)
    assert updated.artikel_id == artikel2.artikel_id
    assert updated.wert == 0.15


def test_update_pfand_not_found(session):
    with pytest.raises(HTTPException) as exc:
        update_pfand(999, PfandUpdate(artikel_id=1), session)
    assert exc.value.status_code == 404


def test_update_pfand_unknown_artikel_rejected(session):
    artikel = make_artikel(session, "8", "Pfand 0,25", 0.25)
    pfand = create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    with pytest.raises(HTTPException) as exc:
        update_pfand(pfand.pfand_id, PfandUpdate(artikel_id=999), session)
    assert exc.value.status_code == 400


def test_update_pfand_duplicate_rejected(session):
    artikel1 = make_artikel(session, "8", "Pfand 0,25", 0.25)
    artikel2 = make_artikel(session, "9", "Pfand 0,15", 0.15)
    p1 = create_pfand(PfandCreate(artikel_id=artikel1.artikel_id), session)
    create_pfand(PfandCreate(artikel_id=artikel2.artikel_id), session)
    with pytest.raises(HTTPException) as exc:
        update_pfand(p1.pfand_id, PfandUpdate(artikel_id=artikel2.artikel_id), session)
    assert exc.value.status_code == 400


# --- Delete ---


def test_delete_pfand(session):
    artikel = make_artikel(session, "8", "Pfand 0,25", 0.25)
    pfand = create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    result = delete_pfand(pfand.pfand_id, session)
    assert result["message"] == "Pfand deleted"
    assert session.get(Pfand, pfand.pfand_id) is None


def test_delete_pfand_not_found(session):
    with pytest.raises(HTTPException) as exc:
        delete_pfand(999, session)
    assert exc.value.status_code == 404


def test_delete_pfand_in_use_rejected(session):
    artikel = make_artikel(session, "8", "Pfand 0,25", 0.25)
    pfand = create_pfand(PfandCreate(artikel_id=artikel.artikel_id), session)
    pg = Produktgruppe(
        toplevel_id=1, sub_id=2, produktgruppen_name="Test",
        pfand_id=pfand.pfand_id, aktiv=True, n_artikel=0, n_artikel_rekursiv=0,
    )
    session.add(pg)
    session.commit()
    with pytest.raises(HTTPException) as exc:
        delete_pfand(pfand.pfand_id, session)
    assert exc.value.status_code == 409


# --- Read (regression) ---


def test_read_pfands_filters_by_wert(session):
    artikel1 = make_artikel(session, "8", "Pfand 0,25", 0.25)
    artikel2 = make_artikel(session, "9", "Pfand 0,15", 0.15)
    create_pfand(PfandCreate(artikel_id=artikel1.artikel_id), session)
    create_pfand(PfandCreate(artikel_id=artikel2.artikel_id), session)
    all_pfands = read_pfands(session)
    assert len(all_pfands) == 2
    pfands_25 = read_pfands(session, wert=0.25)
    assert len(pfands_25) == 1
    assert pfands_25[0].artikel_id == artikel1.artikel_id
