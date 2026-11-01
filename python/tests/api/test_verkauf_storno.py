from datetime import datetime, timezone

import pytest

from fastapi.testclient import TestClient

from sqlmodel import select

from python.main import app

from python.models import (
    TSETransaction,
    Verkauf,
    VerkaufDetails,
    VerkaufMwst,
)

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


def _sale_with_detail(session, ec_zahlung):
    v = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=ec_zahlung)
    session.add(v)
    session.commit()
    session.refresh(v)
    session.add(VerkaufDetails(position=1, stueckzahl=2, ges_preis=20.0,
                               mwst_satz=0.19, rechnungs_nr=v.rechnungs_nr))
    session.add(VerkaufMwst(rechnungs_nr=v.rechnungs_nr, mwst_satz=0.19,
                            mwst_netto=16.81, mwst_betrag=3.19))
    session.commit()
    return v


def test_storno_rejected_for_sale_in_completed_settlement(session, client):
    original = _sale_with_detail(session, ec_zahlung=False)

    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tag_id = r.json()["id"]

    r = client.post(f"/verkauf/{original.rechnungs_nr}/storno")
    assert r.status_code == 400
    assert str(tag_id) in r.json()["detail"]
    assert "Tagesabschluss" in r.json()["detail"]

    # nothing was written
    assert session.exec(
        select(Verkauf).where(Verkauf.storno_von == original.rechnungs_nr)
    ).first() is None


def test_storno_signs_the_tse_refund_as_cash_even_for_ec_sales(session, client):
    original = _sale_with_detail(session, ec_zahlung=True)

    r = client.post(f"/verkauf/{original.rechnungs_nr}/storno")
    assert r.status_code == 200
    storno_nr = r.json()["rechnungs_nr"]

    tx = session.exec(
        select(TSETransaction).where(TSETransaction.rechnungs_nr == storno_nr)
    ).one()
    assert tx.process_type == "Kassenbeleg-V1"
    assert tx.process_data.startswith("Beleg^")
    assert tx.process_data.endswith(":Bar")  # Java: refund is always cash
    assert tx.training is False


def test_storno_allowed_for_sales_after_a_settlement(session, client):
    settled = _sale_with_detail(session, ec_zahlung=False)
    assert client.post("/abrechnung/tag/", json={}).status_code == 200

    later = _sale_with_detail(session, ec_zahlung=False)
    r = client.post(f"/verkauf/{later.rechnungs_nr}/storno")
    assert r.status_code == 200
    assert r.json()["storno_von"] == later.rechnungs_nr
    # the settled sale is still untouched
    assert session.exec(
        select(Verkauf).where(Verkauf.storno_von == settled.rechnungs_nr)
    ).first() is None
