from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.models import Gutschein, Verkauf, VerkaufDetails
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


def _create_voucher(session, nr=1, value=10.0):
    # Numbers are assigned by the backend when creating through the API, so
    # tests that need a specific number insert the creation row directly.
    g = Gutschein(
        gutschein_nr=nr, datum=datetime.now(timezone.utc),
        gutschein_in_vd_id=None, einloesung_in_vd_id=None, restbetrag=value,
    )
    session.add(g)
    session.commit()
    session.refresh(g)
    return g.gutschein_id


def _sale_detail(session, price=-4.0):
    v = Verkauf(verkaufsdatum=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    session.add(v)
    session.commit()
    session.refresh(v)
    d = VerkaufDetails(
        position=1, stueckzahl=1, ges_preis=price, mwst_satz=0.19,
        rechnungs_nr=v.rechnungs_nr,
    )
    session.add(d)
    session.commit()
    session.refresh(d)
    return d


def test_create_and_read(client, session):
    gid = _create_voucher(session)
    r = client.get(f"/gutschein/{gid}")
    assert r.status_code == 200


def test_ausstehend_eingeloest(client, session):
    gid = _create_voucher(session, nr=2, value=5.0)
    r = client.get("/gutschein/ausstehend")
    assert r.status_code == 200
    assert any(g["gutschein_id"] == gid for g in r.json())
    client.post(f"/gutschein/{gid}/einloesen", json={"restbetrag": 0.0})
    r = client.get("/gutschein/eingeloest")
    assert r.status_code == 200
    assert any(g["gutschein_id"] == gid or g["restbetrag"] <= 0 for g in r.json())


def test_negative_restbetrag_rejected(client):
    r = client.post("/gutschein/", json={"restbetrag": -1.0})
    assert r.status_code == 422


# ------------------------------------------------------------- redemption

def test_redeem_partial_by_betrag(client, session):
    gid = _create_voucher(session, nr=10, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 3.0})
    assert r.status_code == 200
    assert r.json()["restbetrag"] == 7.0

    # append-only: a second row with the same voucher number
    rows = session.exec(select(Gutschein).where(Gutschein.gutschein_nr == 10)).all()
    assert len(rows) == 2
    assert min(row.restbetrag for row in rows) == 7.0


def test_redeem_partial_by_new_restbetrag(client, session):
    gid = _create_voucher(session, nr=11, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={"restbetrag": 4.0})
    assert r.status_code == 200
    assert r.json()["restbetrag"] == 4.0


def test_redeem_uses_current_balance_across_rows(client, session):
    gid = _create_voucher(session, nr=12, value=10.0)
    client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 3.0})
    # redeem from the *creation* row again: balance is 7, not 10
    r = client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 7.0})
    assert r.status_code == 200
    assert r.json()["restbetrag"] == 0.0


def test_redeem_amount_from_sale_position(client, session):
    gid = _create_voucher(session, nr=13, value=10.0)
    detail = _sale_detail(session, price=-4.5)
    r = client.post(f"/gutschein/{gid}/einloesen", json={
        "einloesung_in_vd_id": detail.vd_id,
    })
    assert r.status_code == 200
    assert r.json()["restbetrag"] == 5.5
    assert r.json()["einloesung_in_vd_id"] == detail.vd_id
    # Java copies the original voucher sale position onto redemption rows
    assert r.json()["gutschein_in_vd_id"] == client.get(f"/gutschein/{gid}").json()["gutschein_in_vd_id"]


def test_redeem_amount_must_match_sale_position(client, session):
    gid = _create_voucher(session, nr=14, value=10.0)
    detail = _sale_detail(session, price=-4.5)
    r = client.post(f"/gutschein/{gid}/einloesen", json={
        "einloesung_in_vd_id": detail.vd_id, "betrag": 3.0,
    })
    assert r.status_code == 400


def test_sale_position_cannot_redeem_twice(client, session):
    gid = _create_voucher(session, nr=15, value=10.0)
    detail = _sale_detail(session, price=-4.0)
    assert client.post(f"/gutschein/{gid}/einloesen", json={
        "einloesung_in_vd_id": detail.vd_id,
    }).status_code == 200
    r = client.post(f"/gutschein/{gid}/einloesen", json={
        "einloesung_in_vd_id": detail.vd_id,
    })
    assert r.status_code == 400


def test_redeem_more_than_balance_rejected(client, session):
    gid = _create_voucher(session, nr=16, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 11.0})
    assert r.status_code == 400
    # nothing was written
    rows = session.exec(select(Gutschein).where(Gutschein.gutschein_nr == 16)).all()
    assert len(rows) == 1
    assert client.get(f"/gutschein/{gid}").json()["restbetrag"] == 10.0


def test_redeem_zero_or_negative_rejected(client, session):
    gid = _create_voucher(session, nr=17, value=10.0)
    assert client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 0}).status_code == 400
    assert client.post(f"/gutschein/{gid}/einloesen", json={"betrag": -2.0}).status_code == 400
    # redeeming the full balance twice is rejected the second time
    assert client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 10.0}).status_code == 200
    assert client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 1.0}).status_code == 400


def test_redeem_without_amount_rejected(client, session):
    gid = _create_voucher(session, nr=18, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={})
    assert r.status_code == 400


def test_redeem_inconsistent_restbetrag_rejected(client, session):
    gid = _create_voucher(session, nr=19, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 3.0, "restbetrag": 4.0})
    assert r.status_code == 400


def test_redeem_unknown_voucher(client, session):
    r = client.post("/gutschein/99999/einloesen", json={"betrag": 1.0})
    assert r.status_code == 404


def test_redeem_unknown_sale_position(client, session):
    gid = _create_voucher(session, nr=20, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={"einloesung_in_vd_id": 999999})
    assert r.status_code == 400


def test_redeem_copies_original_position_from_creation_row(client, session):
    detail = _sale_detail(session, price=-10.0)
    creation = Gutschein(
        gutschein_nr=22, datum=detail.verkauf.verkaufsdatum,
        gutschein_in_vd_id=detail.vd_id, einloesung_in_vd_id=None, restbetrag=10.0,
    )
    session.add(creation)
    session.commit()
    session.refresh(creation)
    # an intermediate row without the position link (e.g. legacy data)
    legacy = Gutschein(gutschein_nr=22, datum=detail.verkauf.verkaufsdatum,
                       gutschein_in_vd_id=None, einloesung_in_vd_id=None, restbetrag=10.0)
    session.add(legacy)
    session.commit()
    session.refresh(legacy)

    res = client.post(f"/gutschein/{legacy.gutschein_id}/einloesen", json={"betrag": 2.0})
    assert res.status_code == 200
    assert res.json()["gutschein_in_vd_id"] == detail.vd_id


def test_redeem_with_unknown_original_position_rejected(client, session):
    gid = _create_voucher(session, nr=23, value=10.0)
    r = client.post(f"/gutschein/{gid}/einloesen", json={
        "betrag": 1.0, "gutschein_in_vd_id": 999999,
    })
    assert r.status_code == 400


def test_ausstehend_shows_reduced_balance(client, session):
    gid = _create_voucher(session, nr=21, value=10.0)
    client.post(f"/gutschein/{gid}/einloesen", json={"betrag": 6.0})
    r = client.get("/gutschein/ausstehend")
    row = next(g for g in r.json() if g["gutschein_nr"] == 21)
    assert row["restbetrag"] == 4.0
    assert row["restbetrag_anfang"] == 10.0


def test_create_assigns_gutschein_nr_from_backend(client):
    r = client.post("/gutschein/", json={"restbetrag": 10.0})
    assert r.status_code == 200
    assert r.json()["gutschein_nr"] == 200

    # a client-supplied number must not be used
    r = client.post("/gutschein/", json={"gutschein_nr": 999, "restbetrag": 5.0})
    assert r.status_code == 200
    assert r.json()["gutschein_nr"] == 201
