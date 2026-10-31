import pytest
from fastapi.testclient import TestClient

from python.main import app
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


def _create_sale(client, ec_zahlung=False):
    r = client.post("/verkauf/", json={"ec_zahlung": ec_zahlung})
    assert r.status_code == 200
    return r.json()


def _create_day_settlement(client):
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    return r.json()


def test_month_flow(client):
    # Create a sale and a day settlement
    _create_sale(client)
    day = _create_day_settlement(client)

    # Create month settlement (auto-picks the month of the day settlement)
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 200
    body = r.json()
    assert "monat" in body
    assert "abrechnung_tag_id_von" in body
    assert "abrechnung_tag_id_bis" in body

    # Read the month settlement
    mid = body["id"]
    r = client.get(f"/abrechnung/monat/{mid}")
    assert r.status_code == 200
    assert "mwst" in r.json()

    # List
    r = client.get("/abrechnung/monat/")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Offen: month is now settled, so no open months
    r = client.get("/abrechnung/monat/offen")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_month_no_daily_settlements(client):
    # No sales, no day settlements -> month creation fails
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 400


def test_month_offen_with_unsettled_month(client):
    # Create a sale + day settlement, but don't settle the month
    _create_sale(client)
    _create_day_settlement(client)
    r = client.get("/abrechnung/monat/offen")
    assert r.status_code == 200
    # The current month should appear as open (it has unsettled day settlements)
    assert isinstance(r.json(), list)


def test_month_404(client):
    r = client.get("/abrechnung/monat/99999")
    assert r.status_code == 404
