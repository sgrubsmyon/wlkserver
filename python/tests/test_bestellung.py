import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.models import Artikel, BestellungDetails
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


def test_crud(client, session):
    r = client.post("/bestellung/", json={"typ": "LM", "jahr": 2026, "kw": 1})
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


def test_positions_roundtrip(client, session):
    a = Artikel(artikel_nr="A1", artikel_name="Testartikel")
    session.add(a)
    session.commit()
    session.refresh(a)

    r = client.post("/bestellung/", json={
        "typ": "LM", "jahr": 2026, "kw": 1,
        "details": [{"position": 1, "artikel_id": a.artikel_id, "stueckzahl": 3}],
    })
    assert r.status_code == 200
    bid = r.json()["bestell_nr"]
    r = client.get(f"/bestellung/{bid}")
    assert [(d["position"], d["stueckzahl"]) for d in r.json()["details"]] == [(1, 3)]

    # PATCH replaces all positions
    r = client.patch(f"/bestellung/{bid}", json={
        "details": [{"position": 1, "artikel_id": a.artikel_id, "stueckzahl": 2}],
    })
    assert r.status_code == 200
    r = client.get(f"/bestellung/{bid}")
    assert [(d["position"], d["stueckzahl"]) for d in r.json()["details"]] == [(1, 2)]

    # changing typ keeps the positions consistent
    r = client.patch(f"/bestellung/{bid}", json={"typ": "KHW"})
    assert r.status_code == 200
    assert session.exec(select(BestellungDetails).where(BestellungDetails.bestell_nr == bid)).one().typ == "KHW"

    r = client.delete(f"/bestellung/{bid}")
    assert r.status_code == 200
    assert session.exec(select(BestellungDetails).where(BestellungDetails.bestell_nr == bid)).all() == []


def test_invalid_typ_rejected(client):
    r = client.post("/bestellung/", json={"typ": "EINKAUF", "jahr": 2026, "kw": 1})
    assert r.status_code == 422
    r = client.post("/bestellung/", json={"typ": "IVT", "jahr": 2026, "kw": 1})
    assert r.status_code == 200
    r = client.patch(f"/bestellung/{r.json()['bestell_nr']}", json={"typ": "EINKAUF"})
    assert r.status_code == 422


def test_positions_validation(client, session):
    r = client.post("/bestellung/", json={
        "details": [{"position": 1, "artikel_id": 999999}],
    })
    assert r.status_code == 400
    assert client.get("/bestellung/").json() == []

    a = Artikel(artikel_nr="A2", artikel_name="Testartikel 2")
    session.add(a)
    session.commit()
    session.refresh(a)
    r = client.post("/bestellung/", json={
        "details": [
            {"position": 1, "artikel_id": a.artikel_id},
            {"position": 1, "artikel_id": a.artikel_id},
        ],
    })
    assert r.status_code == 400
