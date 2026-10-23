import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.session import get_session
from python.models import (
    Artikel, Mwst, Produktgruppe, Lieferant,
    Kassenstand, TrainingKassenstand, TrainingVerkauf, TrainingVerkaufDetails,
    TrainingVerkaufMwst, Verkauf,
)


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _seed_artikel(session, vk_preis=10.0, mwst_satz=0.19):
    m = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name="Training PG", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    l = Lieferant(lieferant_name="Training Lieferant")
    session.add(l)
    session.commit()
    session.refresh(l)
    a = Artikel(
        artikel_nr="T1", artikel_name="Trainingsartikel",
        produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
        vk_preis=vk_preis,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_training_status(client):
    r = client.get("/training/status")
    assert r.status_code == 200
    assert "training_mode" in r.json()


def test_create_training_sale_writes_only_training_tables(client, session):
    a = _seed_artikel(session)
    r = client.post("/training/verkauf", json={
        "ec_zahlung": False,
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 2}],
    })
    assert r.status_code == 200
    body = r.json()
    assert body["rechnungs_nr"] is not None
    assert body["verkauf_details"][0]["ges_preis"] == 20.0
    assert float(body["verkauf_mwst"][0]["mwst_satz"]) == 0.19

    # training tables are written ...
    assert len(session.exec(select(TrainingVerkauf)).all()) == 1
    assert len(session.exec(select(TrainingVerkaufDetails)).all()) == 1
    assert len(session.exec(select(TrainingVerkaufMwst)).all()) == 1
    ks = session.exec(select(TrainingKassenstand)).all()
    assert len(ks) == 1
    assert ks[0].neuer_kassenstand == 20.0

    # ... and the real bookkeeping stays untouched
    assert session.exec(select(Verkauf)).all() == []
    assert session.exec(select(Kassenstand)).all() == []


def test_ec_training_sale_skips_kassenstand(client, session):
    a = _seed_artikel(session)
    r = client.post("/training/verkauf", json={
        "ec_zahlung": True,
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    assert r.status_code == 200
    assert session.exec(select(TrainingKassenstand)).all() == []


def test_training_sale_listing(client, session):
    a = _seed_artikel(session)
    client.post("/training/verkauf", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    r = client.get("/training/verkauf")
    assert r.status_code == 200
    assert len(r.json()) == 1
    nr = r.json()[0]["rechnungs_nr"]

    r = client.get(f"/training/verkauf/{nr}")
    assert r.status_code == 200
    assert r.json()["rechnungs_nr"] == nr

    r = client.get("/training/verkauf/99999")
    assert r.status_code == 404


def test_training_sale_rejects_zero_stueckzahl(client, session):
    a = _seed_artikel(session)
    r = client.post("/training/verkauf", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 0}],
    })
    assert r.status_code == 400
    assert session.exec(select(TrainingVerkauf)).all() == []


def test_training_sale_requires_auth(session):
    app.dependency_overrides[get_session] = lambda: session
    try:
        with TestClient(app) as c:
            r = c.post("/training/verkauf", json={})
            assert r.status_code == 401
    finally:
        app.dependency_overrides.clear()
