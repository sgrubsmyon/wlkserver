import pytest
from fastapi.testclient import TestClient

from python.main import app
from python.session import get_session


@pytest.fixture
def client(session):
    from sqlmodel import select

    from python.models import User

    # TSE commissioning is admin-only (gap G1), so the shared test user needs the role.
    user = session.exec(select(User).where(User.username == "test")).one()
    user.role = "admin"
    session.add(user)
    session.commit()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _create_sale(client):
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    return r.json()


def test_tse_status(client):
    r = client.get("/tse/status")
    assert r.status_code == 200
    body = r.json()
    assert "initialized" in body
    assert "opened" in body
    assert "library_loaded" in body


def test_tse_init_requires_admin(client, session):
    from python.models import User
    from python.utils.auth import hash_password

    cashier = User(username="kassierer", password_hash=hash_password("pw"), role="mitarbeiter", active=True)
    cashier.user_id = None
    session.add(cashier)
    session.commit()
    token = client.post("/auth/login", json={"username": "kassierer", "password": "pw"}).json()["access_token"]
    r = client.post("/tse/init", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 403


def test_tse_init(client):
    r = client.post("/tse/init")
    assert r.status_code == 200
    assert "status" in r.json()


def test_tse_init_with_pin_values(client, monkeypatch):
    from python.utils.tse_client import tse_client

    monkeypatch.setenv("TSE_TIME_ADMIN_PIN", "87654321")
    monkeypatch.setattr(tse_client, "lib", None)  # no TSE in the test environment
    r = client.post("/tse/init", json={
        "admin_pin": "12345678",
        "admin_puk": "1234567890",
        "time_admin_pin": "87654321",
        "time_admin_puk": "0987654321",
    })
    assert r.status_code == 200
    assert r.json()["status"].startswith("initialized")


def test_tse_init_rejects_time_admin_pin_not_matching_env(client, monkeypatch):
    from python.utils.tse_client import tse_client

    body = {
        "admin_pin": "12345678",
        "admin_puk": "1234567890",
        "time_admin_pin": "87654321",
        "time_admin_puk": "0987654321",
    }
    monkeypatch.setenv("TSE_TIME_ADMIN_PIN", "11111111")
    monkeypatch.setattr(tse_client, "lib", None)
    assert client.post("/tse/init", json=body).status_code == 400
    monkeypatch.delenv("TSE_TIME_ADMIN_PIN")
    assert client.post("/tse/init", json=body).status_code == 400


def test_tse_init_rejects_wrong_pin_and_puk_length(client):
    body = {
        "admin_pin": "1234567",  # 7 instead of 8
        "admin_puk": "1234567890",
        "time_admin_pin": "87654321",
        "time_admin_puk": "0987654321",
    }
    assert client.post("/tse/init", json=body).status_code == 400
    body["admin_pin"] = "12345678"
    body["time_admin_puk"] = "098765432"  # 9 instead of 10
    assert client.post("/tse/init", json=body).status_code == 400


def test_tse_init_rejects_whitespace_control_and_non_ascii(client, monkeypatch):
    from python.utils.tse_client import tse_client

    monkeypatch.setenv("TSE_TIME_ADMIN_PIN", "87654321")
    monkeypatch.setattr(tse_client, "lib", None)
    body = {
        "admin_pin": "12345678",
        "admin_puk": "1234567890",
        "time_admin_pin": "87654321",
        "time_admin_puk": "0987654321",
    }
    # 8 characters each, but none is a plain printable ASCII PIN.
    for bad_pin in ("1234 567", " 1234567", "1234567\n", "1234567é"):
        assert client.post("/tse/init", json={**body, "admin_pin": bad_pin}).status_code == 400


def test_tse_transaction_flow(client):
    # Create a sale first (for the rechnungs_nr FK)
    sale = _create_sale(client)

    # Create a TSE transaction
    r = client.post("/tse/transaction", json={
        "process_type": "RECHNUNG",
        "process_data": "test sale",
        "rechnungs_nr": sale["rechnungs_nr"],
    })
    assert r.status_code == 200
    body = r.json()
    assert "transaction_number" in body
    assert "signature_counter" in body

    # Read single
    tid = body["transaction_id"]
    r = client.get(f"/tse/transaction/{tid}")
    assert r.status_code == 200

    # List
    r = client.get("/tse/transaction")
    assert r.status_code == 200
    rows = r.json()
    assert len(rows) == 2  # the sale signs itself + the manual transaction
    sale_row = next(row for row in rows if row["transaction_id"] != tid)
    assert sale_row["process_type"] == "Kassenbeleg-V1"
    assert sale_row["process_data"].startswith("Beleg^")

    # By verkauf
    r = client.get(f"/tse/transaction/verkauf/{sale['rechnungs_nr']}")
    assert r.status_code == 200
    assert len(r.json()) == 2


def test_tse_transaction_404(client):
    r = client.get("/tse/transaction/99999")
    assert r.status_code == 404


def test_tse_transaction_bad_verkauf(client):
    r = client.post("/tse/transaction", json={
        "process_type": "RECHNUNG",
        "process_data": "test",
        "rechnungs_nr": 99999,
    })
    assert r.status_code == 400


def test_tse_basket_lifecycle_abort(client):
    started = client.post("/tse/transaction/start")
    assert started.status_code == 200
    opened = started.json()
    assert opened["rechnungs_nr"] is None
    assert opened["transaction_end"] is None

    aborted = client.post(f"/tse/transaction/{opened['transaction_id']}/abbruch")
    assert aborted.status_code == 200
    body = aborted.json()
    assert body["process_type"] == "Kassenbeleg-V1"
    assert body["process_data"].startswith("AVBelegabbruch^")
    assert body["transaction_end"] > body["transaction_start"]
    # aborted twice, or after the sale, is an error
    assert client.post(f"/tse/transaction/{opened['transaction_id']}/abbruch").status_code == 400
    assert client.post("/tse/transaction/99999/abbruch").status_code == 404


def test_tse_basket_lifecycle_finish_by_sale(client):
    opened = client.post("/tse/transaction/start").json()

    sale = client.post("/verkauf/", json={"tse_transaction_id": opened["transaction_id"]})
    assert sale.status_code == 200

    row = client.get(f"/tse/transaction/{opened['transaction_id']}").json()
    assert row["rechnungs_nr"] == sale.json()["rechnungs_nr"]
    assert row["transaction_end"] > row["transaction_start"]
    assert row["process_data"].startswith("Beleg^")
    # the sale signs the started transaction, it does not create a second one
    assert len(client.get(f"/tse/transaction/verkauf/{sale.json()['rechnungs_nr']}").json()) == 1

    # a finished transaction cannot be reused
    r = client.post("/verkauf/", json={"tse_transaction_id": opened["transaction_id"]})
    assert r.status_code == 400


def test_tse_export_full(client):
    r = client.post("/tse/export/full")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-tar"
    assert len(r.content) > 0


def test_tse_export_partial(client):
    r = client.post("/tse/export/partial", json={})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-tar"
    assert len(r.content) > 0


def test_tse_export_delete(client):
    r = client.post("/tse/export/delete", json={})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-tar"
    assert len(r.content) > 0


def test_tse_certificates(client):
    r = client.post("/tse/certificates")
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/x-tar"
    assert len(r.content) > 0
