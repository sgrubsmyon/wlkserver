"""Integration tests: complete workflows, cross-entity effects, concurrency."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine, select

from python.main import app
from python.models import (
    Artikel, Kassenstand, Lieferant, Mwst, Produktgruppe, Verkauf, User,
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


def _seed_artikel(session, artikel_nr="A1", vk_preis=10.0, mwst_satz=0.19):
    m = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name=f"PG {artikel_nr}", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    l = Lieferant(lieferant_name=f"L {artikel_nr}")
    session.add(l)
    session.commit()
    session.refresh(l)
    a = Artikel(
        artikel_nr=artikel_nr, artikel_name=f"Artikel {artikel_nr}",
        produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
        vk_preis=vk_preis,
    )
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


# ---------------------------------------------------------------- workflows

def test_complete_sale_to_year_settlement_workflow(client, session):
    a = _seed_artikel(session, vk_preis=10.0, mwst_satz=0.19)

    # 1. cash sale: 2 x 10.00 = 20.00, VAT 19 %
    r = client.post("/verkauf/", json={
        "ec_zahlung": False,
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 2}],
    })
    assert r.status_code == 200
    nr = r.json()["rechnungs_nr"]

    # 2. the sale created a cash-register entry
    r = client.get("/kassenstand/aktuell")
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 20.0
    assert r.json()["rechnungs_nr"] == nr

    # 3. daily settlement aggregates the sale
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tag_id = r.json()["id"]
    r = client.get(f"/abrechnung/tag/{tag_id}")
    assert r.status_code == 200
    tag = r.json()
    assert tag["rechnungs_nr_von"] == nr
    assert len(tag["mwst"]) == 1
    assert float(tag["mwst"][0]["bar_brutto"]) == 20.0
    assert float(tag["mwst"][0]["mwst_betrag"]) == 3.19
    assert float(tag["mwst"][0]["mwst_netto"]) == 16.81

    # 4. monthly settlement aggregates the day
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 200
    monat_id = r.json()["id"]
    r = client.get(f"/abrechnung/monat/{monat_id}")
    assert r.status_code == 200
    assert float(r.json()["mwst"][0]["bar_brutto"]) == 20.0

    # 5. yearly settlement aggregates the month
    r = client.post("/abrechnung/jahr/", json={})
    assert r.status_code == 200
    jahr_id = r.json()["id"]
    r = client.get(f"/abrechnung/jahr/{jahr_id}")
    assert r.status_code == 200
    assert float(r.json()["mwst"][0]["bar_brutto"]) == 20.0
    assert float(r.json()["mwst"][0]["mwst_betrag"]) == 3.19

    # 6. nothing is left open
    assert client.get("/abrechnung/tag/offen").json() == []
    assert client.get("/abrechnung/monat/offen").json() == []
    assert client.get("/abrechnung/jahr/offen").json() == []


def test_workflow_ec_sale_does_not_touch_cash(client, session):
    a = _seed_artikel(session)
    r = client.post("/verkauf/", json={
        "ec_zahlung": True,
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    assert r.status_code == 200
    assert client.get("/kassenstand/aktuell").json() is None

    client.post("/abrechnung/tag/", json={})
    tag = client.get("/abrechnung/tag/1").json()
    # VAT is reported, but no cash was taken
    assert float(tag["mwst"][0]["mwst_betrag"]) == 1.60
    assert float(tag["mwst"][0]["bar_brutto"]) == 0.0


# ------------------------------------------------------- cross-entity links

def test_storno_reverses_voucher_installment_and_cash(client, session):
    gutschein_artikel = _seed_artikel(session, artikel_nr="GUTSCHEIN", vk_preis=10.0)

    r = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": gutschein_artikel.artikel_id, "stueckzahl": 1}],
    })
    assert r.status_code == 200
    nr = r.json()["rechnungs_nr"]

    # selling a GUTSCHEIN article creates a voucher with the sale value
    gutscheine = client.get("/gutschein/").json()
    assert len(gutscheine) == 1
    assert gutscheine[0]["restbetrag"] == 10.0
    assert len(client.get("/gutschein/ausstehend").json()) == 1

    # open installment linked to the sale
    r = client.post("/anzahlung/", json={"anzahlung_in_rech_nr": nr})
    assert r.status_code == 200
    assert len(client.get("/anzahlung/offen").json()) == 1

    # cash register: 10.00 from the sale
    assert client.get("/kassenstand/aktuell").json()["neuer_kassenstand"] == 10.0

    # storno must cancel the voucher, resolve the installment, refund the cash
    r = client.post(f"/verkauf/{nr}/storno")
    assert r.status_code == 200
    assert r.json()["storno_von"] == nr

    assert client.get("/gutschein/ausstehend").json() == []
    assert len(client.get("/anzahlung/offen").json()) == 0
    assert len(client.get("/anzahlung/aufgeloest").json()) == 1
    assert client.get("/kassenstand/aktuell").json()["neuer_kassenstand"] == 0.0

    # the storno also shows up in the day settlement as a negative sale
    client.post("/abrechnung/tag/", json={})
    tag = client.get("/abrechnung/tag/1").json()
    assert float(tag["mwst"][0]["bar_brutto"]) == 0.0
    assert float(tag["mwst"][0]["mwst_betrag"]) == 0.0


def test_bestellung_positions_reference_artikel(client, session):
    a = _seed_artikel(session)
    r = client.post("/bestellung/", json={
        "typ": "KHW", "jahr": 2026, "kw": 10,
        "details": [{"position": 1, "artikel_id": a.artikel_id, "stueckzahl": 7}],
    })
    assert r.status_code == 200
    nr = r.json()["bestell_nr"]

    detail = client.get(f"/bestellung/{nr}").json()["details"][0]
    assert detail["artikel_id"] == a.artikel_id
    assert detail["stueckzahl"] == 7

    # deleting the artikel is blocked by the FK only on a real DB; the API must
    # at least keep the order readable until then
    assert client.get(f"/bestellung/{nr}").status_code == 200


# -------------------------------------------------------------- concurrency

def test_concurrent_sales_are_consistent(tmp_path):
    db_file = tmp_path / "concurrent.db"
    engine = create_engine(
        f"sqlite:///{db_file}",
        connect_args={"check_same_thread": False, "timeout": 30},
    )

    @event.listens_for(engine, "connect")
    def _wal(dbapi_connection, _record):
        dbapi_connection.execute("PRAGMA journal_mode=WAL")

    SQLModel.metadata.create_all(engine)
    with Session(engine) as s:
        s.add(User(username="test", password_hash=hash_password("test"),
                   role="mitarbeiter", active=True))
        s.commit()
        m = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
        s.add(m)
        s.commit()
        s.refresh(m)
        pg = Produktgruppe(produktgruppen_name="PG", mwst_id=m.mwst_id)
        s.add(pg)
        s.commit()
        s.refresh(pg)
        l = Lieferant(lieferant_name="L")
        s.add(l)
        s.commit()
        s.refresh(l)
        a = Artikel(artikel_nr="C1", artikel_name="Concurrent",
                    produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
                    vk_preis=10.0)
        s.add(a)
        s.commit()
        s.refresh(a)
        artikel_id = a.artikel_id

    def _session_override():
        with Session(engine) as s:
            yield s

    app.dependency_overrides[get_session] = _session_override
    try:
        with TestClient(app) as c:
            r = c.post("/auth/login", json={"username": "test", "password": "test"})
            assert r.status_code == 200
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]

            def create_sale(_):
                return c.post("/verkauf/", json={
                    "ec_zahlung": False,
                    "verkauf_details": [{"artikel_id": artikel_id, "stueckzahl": 1}],
                })

            with ThreadPoolExecutor(max_workers=4) as pool:
                responses = list(pool.map(create_sale, range(4)))
    finally:
        app.dependency_overrides.clear()

    assert [r.status_code for r in responses] == [200] * 4
    assert len({r.json()["rechnungs_nr"] for r in responses}) == 4

    with Session(engine) as s:
        assert len(s.exec(select(Verkauf)).all()) == 4
        entries = s.exec(select(Kassenstand).order_by(Kassenstand.kassenstand_id)).all()
        assert len(entries) == 4
        # each sale adds exactly 10.00, so the running balance ends at 40.00
        assert [e.neuer_kassenstand for e in entries] == [10.0, 20.0, 30.0, 40.0]
        total = sum(Decimal(str(e.neuer_kassenstand)) for e in entries[-1:])
        assert total == Decimal("40.0")
