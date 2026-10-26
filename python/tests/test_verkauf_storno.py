from datetime import datetime, timezone
import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from sqlmodel import select

from python.main import app
from python.routers.verkauf import storno_verkauf, read_single_verkauf
from python.models import Verkauf, VerkaufDetails, VerkaufMwst
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


def test_storno_creates_inverted_entries(session):
    # Create original sale
    original = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=False, kunde_gibt=20.0)
    session.add(original)
    session.commit()
    session.refresh(original)

    # Add one detail and one mwst
    d = VerkaufDetails(
        position=1,
        stueckzahl=2,
        ges_preis=10.0,
        mwst_satz=0.19,
        rechnungs_nr=original.rechnungs_nr,
    )
    m = VerkaufMwst(
        rechnungs_nr=original.rechnungs_nr,
        mwst_satz=0.19,
        mwst_netto=16.8,
        mwst_betrag=3.2,
    )
    session.add_all([d, m])
    session.commit()

    # Perform storno
    storno = storno_verkauf(original.rechnungs_nr, session)

    # Basic checks
    assert storno["storno_von"] == original.rechnungs_nr
    assert storno["rechnungs_nr"] != original.rechnungs_nr

    # Details should be inverted
    details = storno["verkauf_details"]
    assert len(details) == 1
    assert details[0].stueckzahl == -2
    assert details[0].ges_preis == -10.0

    # MwSt should be inverted
    mwsts = storno["verkauf_mwst"]
    assert len(mwsts) == 1
    assert mwsts[0]["mwst_netto"] == -16.8
    assert mwsts[0]["mwst_betrag"] == -3.2


def test_create_verkauf_rejects_zero_stueckzahl(session):
    from python.routers.verkauf import create_verkauf
    from python.models import VerkaufCreate
    payload = VerkaufCreate(verkauf_details=[{"artikel_id": 1, "stueckzahl": 0}])
    with pytest.raises(HTTPException) as exc:
        create_verkauf(payload, session, None, None)
    assert exc.value.status_code == 400
    # no empty sale row must be left behind
    assert session.exec(select(Verkauf)).all() == []


def test_duplicate_storno_is_prevented(session):
    original = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=False)
    session.add(original)
    session.commit()
    session.refresh(original)

    # First storno succeeds
    s = storno_verkauf(original.rechnungs_nr, session)
    assert s["storno_von"] == original.rechnungs_nr

    # Second storno attempt should raise HTTPException (400)
    with pytest.raises(HTTPException) as exc:
        storno_verkauf(original.rechnungs_nr, session)
    assert exc.value.status_code == 400


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


def test_storno_of_ec_sale_keeps_ec_mode_but_pays_cash(session):
    # Java: storno receipt mirrors the original payment mode, but the shop can only
    # refund in cash, so the Kassenstand is reduced.
    original = _sale_with_detail(session, ec_zahlung=True)
    result = storno_verkauf(original.rechnungs_nr, session)
    assert result["ec_zahlung"] is True
    from python.models import Kassenstand
    entries = session.exec(select(Kassenstand)).all()
    assert len(entries) == 1
    assert entries[0].neuer_kassenstand == -20.0


def test_storno_of_ec_sale_without_payout(session):
    # only for the edge case that the card was not charged: no cash movement
    original = _sale_with_detail(session, ec_zahlung=True)
    result = storno_verkauf(original.rechnungs_nr, session, cash_refund=False)
    assert result["ec_zahlung"] is True
    from python.models import Kassenstand
    assert session.exec(select(Kassenstand)).all() == []


def test_storno_of_cash_sale_is_cash_refund(session):
    original = _sale_with_detail(session, ec_zahlung=False)
    result = storno_verkauf(original.rechnungs_nr, session)
    assert result["ec_zahlung"] is False
    from python.models import Kassenstand
    assert len(session.exec(select(Kassenstand)).all()) == 1


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


def test_storno_is_attributed_to_user(session):
    from python.models import User

    user = User(username="storno_user", password_hash="x", role="mitarbeiter", active=True)
    session.add(user)
    session.commit()
    session.refresh(user)

    original = _sale_with_detail(session, ec_zahlung=False)
    result = storno_verkauf(original.rechnungs_nr, session, _user=user)

    row = session.get(Verkauf, result["rechnungs_nr"])
    assert row.user_id == user.user_id