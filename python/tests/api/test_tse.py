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


def test_tse_init(client):
    r = client.post("/tse/init")
    assert r.status_code == 200
    assert "status" in r.json()


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
