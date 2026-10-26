"""Tests for the list filtering, search and sorting parameters."""
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from python.main import app
from python.models import (
    Artikel, Lieferant, Mwst, Produktgruppe, Rabattaktion, User,
)
from python.session import get_session
from python.utils.auth import hash_password


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _seed_artikel(session, nr="F1", name="Filter Artikel"):
    m = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name=f"PG {nr}", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    l = Lieferant(lieferant_name=f"L {nr}")
    session.add(l)
    session.commit()
    session.refresh(l)
    a = Artikel(artikel_nr=nr, artikel_name=name,
                produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=10.0)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a, pg


def _seed_rabatt(session, name, von, bis=None, artikel_id=None, produktgruppen_id=None):
    r = Rabattaktion(aktionsname=name, von=von, bis=bis, rabatt_relativ=0.1,
                     artikel_id=artikel_id, produktgruppen_id=produktgruppen_id)
    r.rabatt_id = None
    session.add(r)
    session.commit()
    session.refresh(r)
    return r


# ------------------------------------------------------------ rabattaktion

def test_rabattaktion_open_ended_is_listed_by_default(client, session):
    # regression: "bis > von" used to drop rows with bis IS NULL
    now = datetime.now(timezone.utc)
    r = _seed_rabatt(session, "Daueraktion", von=now - timedelta(days=1), bis=None)
    body = client.get("/rabattaktion/").json()
    assert [x["rabatt_id"] for x in body] == [r.rabatt_id]


def test_rabattaktion_current_only(client, session):
    now = datetime.now(timezone.utc)
    active = _seed_rabatt(session, "Aktiv", von=now - timedelta(days=1))
    _seed_rabatt(session, "Abgelaufen", von=now - timedelta(days=10), bis=now - timedelta(days=5))
    _seed_rabatt(session, "Zukunft", von=now + timedelta(days=5))

    body = client.get("/rabattaktion/", params={"current_only": True}).json()
    assert [x["rabatt_id"] for x in body] == [active.rabatt_id]


def test_rabattaktion_filters_by_article_and_group(client, session):
    a, pg = _seed_artikel(session)
    now = datetime.now(timezone.utc)
    by_article = _seed_rabatt(session, "Artikelaktion", von=now - timedelta(days=1),
                              artikel_id=a.artikel_id)
    by_group = _seed_rabatt(session, "Gruppenaktion", von=now - timedelta(days=1),
                            produktgruppen_id=pg.produktgruppen_id)

    body = client.get("/rabattaktion/", params={"artikel_id": a.artikel_id}).json()
    assert [x["rabatt_id"] for x in body] == [by_article.rabatt_id]

    body = client.get("/rabattaktion/", params={"produktgruppen_id": pg.produktgruppen_id}).json()
    assert [x["rabatt_id"] for x in body] == [by_group.rabatt_id]


def test_rabattaktion_search_and_date_window(client, session):
    now = datetime.now(timezone.utc)
    _seed_rabatt(session, "Sommerfest", von=now - timedelta(days=1))
    _seed_rabatt(session, "Winteraktion", von=now - timedelta(days=400), bis=now - timedelta(days=1))

    body = client.get("/rabattaktion/", params={"search_string": "Sommer"}).json()
    assert [x["aktionsname"] for x in body] == ["Sommerfest"]

    # "since" includes open-ended actions; the expired one is excluded
    body = client.get("/rabattaktion/", params={"since": now.isoformat()}).json()
    assert [x["aktionsname"] for x in body] == ["Sommerfest"]

    body = client.get("/rabattaktion/", params={"until": (now - timedelta(days=300)).isoformat()}).json()
    assert [x["aktionsname"] for x in body] == ["Winteraktion"]


# ------------------------------------------------------------------ users

def test_user_filters(client, session):
    session.add_all([
        User(username="anna", password_hash=hash_password("x"), role="admin", active=True),
        User(username="bernd", password_hash=hash_password("x"), role="mitarbeiter", active=True),
        User(username="clara", password_hash=hash_password("x"), role="mitarbeiter", active=False),
    ])
    session.commit()

    names = [u["username"] for u in client.get("/users/").json()]
    assert names == sorted(names)

    body = client.get("/users/", params={"role": "admin"}).json()
    assert [u["username"] for u in body] == ["anna"]

    body = client.get("/users/", params={"active": False}).json()
    assert [u["username"] for u in body] == ["clara"]

    body = client.get("/users/", params={"search_string": "ber"}).json()
    assert [u["username"] for u in body] == ["bernd"]


# ------------------------------------------------------------- bestellung

def test_bestellung_typ_filter(client):
    client.post("/bestellung/", json={"typ": "LM", "jahr": 2026, "kw": 1})
    client.post("/bestellung/", json={"typ": "KHW", "jahr": 2026, "kw": 1})
    client.post("/bestellung/", json={"typ": "IVT", "jahr": 2026, "kw": 1})

    body = client.get("/bestellung/", params={"typ": "KHW"}).json()
    assert [b["typ"] for b in body] == ["KHW"]

    # invalid types are rejected instead of silently returning nothing
    assert client.get("/bestellung/", params={"typ": "EINKAUF"}).status_code == 422


# ------------------------------------------------------------- kassenstand

def test_kassenstand_date_range(client):
    client.post("/kassenstand/", json={
        "neuer_kassenstand": 100.0, "manuell": True, "kommentar": "alt",
        "buchungsdatum": "2026-01-10T10:00:00Z",
    })
    client.post("/kassenstand/", json={
        "neuer_kassenstand": 80.0, "manuell": True, "kommentar": "neu",
        "buchungsdatum": "2026-02-10T10:00:00Z",
    })

    body = client.get("/kassenstand/", params={"since": "2026-02-01T00:00:00Z"}).json()
    assert [k["kommentar"] for k in body] == ["neu"]

    body = client.get("/kassenstand/", params={"until": "2026-01-31T00:00:00Z"}).json()
    assert [k["kommentar"] for k in body] == ["alt"]


# --------------------------------------------------------------- anzahlung

def test_anzahlung_filters_by_sale(client, session):
    nr1 = client.post("/verkauf/", json={}).json()["rechnungs_nr"]
    nr2 = client.post("/verkauf/", json={}).json()["rechnungs_nr"]
    client.post("/anzahlung/", json={"anzahlung_in_rech_nr": nr1})
    client.post("/anzahlung/", json={"anzahlung_in_rech_nr": nr2})
    client.post(f"/anzahlung/{1}/aufloesen", json={"aufloesung_in_rech_nr": nr2})

    body = client.get("/anzahlung/", params={"anzahlung_in_rech_nr": nr1}).json()
    # the resolution is an additional append-only row for the same sale
    assert len(body) == 2
    assert all(a["anzahlung_in_rech_nr"] == nr1 for a in body)

    body = client.get("/anzahlung/", params={"aufloesung_in_rech_nr": nr2}).json()
    assert len(body) == 1
    assert body[0]["aufloesung_in_rech_nr"] == nr2


# ------------------------------------------------------------ zaehlprotokoll

def test_zaehlprotokoll_filter_by_settlement(client):
    client.post("/verkauf/", json={})
    tag1 = client.post("/abrechnung/tag/", json={}).json()["id"]
    client.post("/verkauf/", json={})
    tag2 = client.post("/abrechnung/tag/", json={}).json()["id"]
    client.post("/zaehlprotokoll/", json={"abrechnung_tag_id": tag1, "kommentar": "eins"})
    client.post("/zaehlprotokoll/", json={"abrechnung_tag_id": tag2, "kommentar": "zwei"})

    body = client.get("/zaehlprotokoll/", params={"abrechnung_tag_id": tag1}).json()
    assert [z["kommentar"] for z in body] == ["eins"]


# --------------------------------------------------------------------- tse

def test_tse_transaction_filter_and_limit(client):
    nr = client.post("/verkauf/", json={}).json()["rechnungs_nr"]
    client.post("/tse/transaction", json={
        "process_type": "RECHNUNG", "process_data": "x", "rechnungs_nr": nr,
    })

    body = client.get("/tse/transaction", params={"rechnungs_nr": nr}).json()
    assert len(body) == 1
    assert body[0]["rechnungs_nr"] == nr

    assert client.get("/tse/transaction", params={"rechnungs_nr": 99999}).json() == []
    assert client.get("/tse/transaction", params={"limit": 101}).status_code == 422


# --------------------------------------------------------- settlement order

def test_settlement_lists_can_be_sorted_newest_first(client):
    client.post("/verkauf/", json={})
    first = client.post("/abrechnung/tag/", json={}).json()["id"]
    client.post("/verkauf/", json={})
    second = client.post("/abrechnung/tag/", json={}).json()["id"]

    asc = client.get("/abrechnung/tag/").json()
    assert [t["id"] for t in asc] == [first, second]

    desc = client.get("/abrechnung/tag/", params={"desc": True}).json()
    assert [t["id"] for t in desc] == [second, first]
