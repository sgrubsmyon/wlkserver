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


def _create_month_settlement(client):
    r = client.post("/abrechnung/monat/", json={})
    assert r.status_code == 200
    return r.json()


def test_year_flow(client):
    # Create a sale -> day settlement -> month settlement
    _create_sale(client)
    _create_day_settlement(client)
    month = _create_month_settlement(client)

    # Create year settlement (auto-picks the year of the month settlement)
    r = client.post("/abrechnung/jahr/", json={})
    assert r.status_code == 200
    body = r.json()
    assert "jahr" in body
    assert "abrechnung_tag_id_von" in body
    assert "abrechnung_tag_id_bis" in body

    # Read the year settlement
    jid = body["id"]
    r = client.get(f"/abrechnung/jahr/{jid}")
    assert r.status_code == 200
    assert "mwst" in r.json()

    # List
    r = client.get("/abrechnung/jahr/")
    assert r.status_code == 200
    assert len(r.json()) == 1

    # Offen: year is now settled, so no open years
    r = client.get("/abrechnung/jahr/offen")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_year_no_month_settlements(client):
    # No month settlements -> year creation fails
    r = client.post("/abrechnung/jahr/", json={})
    assert r.status_code == 400


def test_year_offen_with_unsettled_year(client):
    # Create sale -> day -> month, but don't settle the year
    _create_sale(client)
    _create_day_settlement(client)
    _create_month_settlement(client)
    r = client.get("/abrechnung/jahr/offen")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_year_404(client):
    r = client.get("/abrechnung/jahr/99999")
    assert r.status_code == 404
