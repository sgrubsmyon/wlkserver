"""Concurrency against MariaDB: the row locks, not just the in-process lock.

The process lock (`KASSENSTAND_LOCK`, `VOUCHER_LOCK`) only serializes callers
inside one worker. A second API process or a script writes to the same database
and relies on `SELECT ... FOR UPDATE`; these tests disable the process locks so
MariaDB's row locks alone have to keep the balance and the voucher counter
consistent. They are skipped unless `TEST_DATABASE_URL` points at the test
database (SQLite ignores `FOR UPDATE`).
"""
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError
from sqlmodel import Session

from python.business import cash_register, voucher_logic
from python.repositories import latest_kassenstand
from python.models import (
    Artikel,
    GutscheinCounter,
    Kassenstand,
    Lieferant,
    Mwst,
    Produktgruppe,
)
from python.main import app
from python.session import get_session


@pytest.fixture
def client(session, mariadb_engine):
    """TestClient whose requests each use their own MariaDB session."""
    def _session_per_request():
        with Session(mariadb_engine) as request_session:
            yield request_session

    app.dependency_overrides[get_session] = _session_per_request
    with TestClient(app) as c:
        response = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + response.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _seed_sale_data(session, preis=10.0):
    mwst = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    lieferant = Lieferant(lieferant_name="Test")
    session.add(mwst)
    session.add(lieferant)
    session.commit()
    session.refresh(mwst)
    session.refresh(lieferant)
    group = Produktgruppe(produktgruppen_name="Test", mwst_id=mwst.mwst_id)
    session.add(group)
    session.commit()
    session.refresh(group)
    artikel = Artikel(artikel_nr="K1", artikel_name="Artikel", vk_preis=preis,
                      produktgruppen_id=group.produktgruppen_id,
                      lieferant_id=lieferant.lieferant_id)
    session.add(artikel)
    session.commit()
    session.refresh(artikel)
    return artikel


def test_parallel_sales_keep_the_balance_with_only_the_db_lock(
        client, session, monkeypatch):
    artikel = _seed_sale_data(session)
    artikel_id = artikel.artikel_id  # read before the session expires it
    # An existing row to lock; without one, concurrent first sales could all
    # start from an empty ledger.
    session.add(Kassenstand(buchungsdatum=datetime.now(timezone.utc),
                            neuer_kassenstand=100.0, manuell=True))
    session.commit()
    # Disable the per-process lock: the DB row lock has to do the work.
    monkeypatch.setattr(cash_register, "KASSENSTAND_LOCK", nullcontext())

    def sell(_):
        return client.post("/verkauf/", json={
            "ec_zahlung": False,
            "verkauf_details": [{"artikel_id": artikel_id, "stueckzahl": 1}],
        })

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(sell, range(4)))

    assert [r.status_code for r in responses] == [200] * 4
    assert len({r.json()["rechnungs_nr"] for r in responses}) == 4
    assert client.get("/kassenstand/aktuell").json()["neuer_kassenstand"] == 140.0


def test_parallel_vouchers_get_distinct_numbers_with_only_the_db_lock(
        client, session, monkeypatch):
    session.add(GutscheinCounter(id=1, last_nr=199))
    session.commit()
    monkeypatch.setattr(voucher_logic, "VOUCHER_LOCK", nullcontext())

    def issue(_):
        return client.post("/gutschein/", json={"restbetrag": 10.0})

    with ThreadPoolExecutor(max_workers=4) as pool:
        responses = list(pool.map(issue, range(4)))

    assert [r.status_code for r in responses] == [200] * 4
    numbers = sorted(r.json()["gutschein_nr"] for r in responses)
    assert numbers == [200, 201, 202, 203]


def test_latest_kassenstand_for_update_blocks_a_second_connection(
        session, mariadb_engine):
    """The repository's locking read must actually lock on MariaDB."""
    session.add(Kassenstand(buchungsdatum=datetime.now(timezone.utc),
                            neuer_kassenstand=50.0, manuell=True))
    session.commit()

    first, second = Session(mariadb_engine), Session(mariadb_engine)
    try:
        assert latest_kassenstand(first, for_update=True) is not None
        second.connection().exec_driver_sql("SET SESSION innodb_lock_wait_timeout = 1")
        with pytest.raises(OperationalError) as error:
            latest_kassenstand(second, for_update=True)
        assert "Lock wait timeout" in str(error.value)
        first.rollback()
        second.rollback()
        assert latest_kassenstand(second, for_update=True) is not None
    finally:
        first.close()
        second.close()
