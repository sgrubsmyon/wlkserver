import pytest
from fastapi.testclient import TestClient
from python.main import app
from python.session import get_session


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_tse_flow(client):
    r = client.get("/tse/status")
    assert r.status_code == 200
    r = client.post("/tse/init")
    assert r.status_code == 200
    # create a sale and tse transaction
    vr = client.post("/verkauf/", json={})
    assert vr.status_code == 200
    rn = vr.json()["rechnungs_nr"]
    r = client.post("/tse/transaction", json={"rechnungs_nr": rn, "process_type": "Kassenbeleg-V1"})
    assert r.status_code == 200
    tid = r.json()["transaction_id"]
    r = client.get(f"/tse/transaction/{tid}")
    assert r.status_code == 200
    r = client.get("/tse/transaction")
    assert r.status_code == 200
    assert len(r.json()) == 1
    # exports
    r = client.post("/tse/export/full")
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("application/x-tar")
    r = client.post("/tse/export/partial", json={"criterion": "sig_counter", "last_excluded_signature_counter": 0})
    assert r.status_code == 200
    r = client.post("/tse/export/delete", json={})
    assert r.status_code == 200