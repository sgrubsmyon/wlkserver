from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.pool import StaticPool
from sqlmodel import SQLModel, Session, create_engine, select

from python import session as db
from python.main import app
from python.session import get_session
from python.models import (
    AbrechnungTag,
    Artikel,
    Kassenstand,
    Mwst,
    Pfand,
    Produktgruppe,
    Rabattaktion,
    User,
    Verkauf,
)
from python.utils.auth import hash_password
from python.business.training import (
    SPECIAL_ARTIKEL,
    TEST_ARTIKEL,
    seed_catalog,
)


@pytest.fixture
def production_client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def sandbox(monkeypatch):
    """Two engines (production + training) with the training instance active."""
    production = _engine()
    training = _engine()
    with Session(production) as s:
        s.add(User(
            username="admin", password_hash=hash_password("admin"),
            role="admin", active=True,
        ))
        s.commit()
    db._engines.clear()
    db._engines["production"] = production
    db._engines["training"] = training
    monkeypatch.setenv("TRAINING_MODE", "1")
    monkeypatch.setenv("TRAINING_DB_URL", "sqlite://")
    with TestClient(app) as client:  # startup creates/mirrors/seeds the sandbox
        yield client, production, training
    db._engines.clear()


def _engine():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    SQLModel.metadata.create_all(engine)
    return engine


def _login(client):
    r = client.post("/auth/login", json={"username": "admin", "password": "admin"})
    assert r.status_code == 200
    client.headers["Authorization"] = "Bearer " + r.json()["access_token"]


def _artikel_id(engine, nr):
    with Session(engine) as session:
        return session.exec(select(Artikel).where(Artikel.artikel_nr == nr)).one().artikel_id


def test_status_without_training_mode(production_client):
    r = production_client.get("/training/status")
    assert r.status_code == 200
    assert r.json() == {"training_mode": False}


def test_seed_catalog_covers_pos_aspects():
    engine = _engine()
    with Session(engine) as session:
        seed_catalog(session)
        seed_catalog(session)  # idempotent

    with Session(engine) as session:
        rates = {
            round(float(m.mwst_satz), 2): m.dsfinvk_ust_schluessel
            for m in session.exec(select(Mwst)).all()
        }
        assert rates == {0.0: 6, 0.07: 2, 0.19: 1}

        articles = {a.artikel_nr: a for a in session.exec(select(Artikel)).all()}
        assert set(SPECIAL_ARTIKEL) <= set(articles)
        assert set(TEST_ARTIKEL) <= set(articles)
        assert articles["T-19"].vk_preis == 10.0
        assert articles["T-19"].variabler_preis is False
        assert articles["T-VAR"].variabler_preis is True

        pfand = session.exec(select(Pfand)).one()
        assert pfand.artikel_id == articles["PFAND"].artikel_id
        group = session.get(Produktgruppe, articles["T-PFAND"].produktgruppen_id)
        assert group.pfand_id == pfand.pfand_id

        action = session.exec(select(Rabattaktion)).one()
        assert action.artikel_id == articles["T-AKTION"].artikel_id
        assert action.rabatt_relativ == 0.10
        assert action.bis is None
        assert action.von < datetime.now(action.von.tzinfo)


def test_training_mode_sandboxes_sales_storno_and_settlements(sandbox):
    client, production, training = sandbox
    _login(client)

    normal_id = _artikel_id(training, "T-19")
    sale = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": normal_id, "stueckzahl": 1}],
    })
    assert sale.status_code == 200
    nr = sale.json()["rechnungs_nr"]

    variable_id = _artikel_id(training, "T-VAR")
    variable = client.post("/verkauf/", json={
        "verkauf_details": [
            {"artikel_id": variable_id, "stueckzahl": 2, "ges_preis": 12.34},
        ],
    })
    assert variable.status_code == 200
    nr_variable = variable.json()["rechnungs_nr"]
    detail = client.get(f"/verkauf/{nr_variable}").json()["verkauf_details"][0]
    assert detail["ges_preis"] == 12.34

    assert client.post(f"/verkauf/{nr}/storno").status_code == 200
    assert client.post("/abrechnung/tag/", json={}).status_code == 200

    with Session(training) as session:
        assert len(session.exec(select(Verkauf)).all()) == 3  # sale, variable, storno
        assert len(session.exec(select(AbrechnungTag)).all()) == 1
    with Session(production) as session:
        assert session.exec(select(Verkauf)).all() == []
        assert session.exec(select(Kassenstand)).all() == []


def test_reset_clears_transactions_and_reseeds_catalog(sandbox):
    client, production, training = sandbox
    _login(client)

    artikel_id = _artikel_id(training, "T-7")
    assert client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": artikel_id, "stueckzahl": 1}],
    }).status_code == 200

    r = client.post("/training/reset")
    assert r.status_code == 200
    assert r.json() == {"status": "reset"}

    with Session(training) as session:
        assert session.exec(select(Verkauf)).all() == []
        assert session.exec(select(AbrechnungTag)).all() == []
        assert len(session.exec(select(Artikel)).all()) == (
            len(SPECIAL_ARTIKEL) + len(TEST_ARTIKEL)
        )
    with Session(production) as session:
        assert session.exec(select(Verkauf)).all() == []
