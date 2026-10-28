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


def test_crud(client):
    client.post("/verkauf/", json={})
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tid = r.json()["id"]
    r = client.post("/zaehlprotokoll/", json={"abrechnung_tag_id": tid, "kommentar": "Zählung"})
    assert r.status_code == 200
    zid = r.json()["id"]
    r = client.get(f"/zaehlprotokoll/{zid}")
    assert r.status_code == 200
    r = client.get(f"/zaehlprotokoll/abrechnung/{tid}")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = client.patch(f"/zaehlprotokoll/{zid}", json={"kommentar": "updated"})
    assert r.status_code == 200
    assert r.json()["kommentar"] == "updated"


def test_count_is_submitted_with_the_settlement(client, session):
    from sqlmodel import select
    from python.models import Zaehlprotokoll, ZaehlprotokollDetails

    client.post("/verkauf/", json={})
    r = client.post("/abrechnung/tag/", json={
        "zaehlprotokoll": {
            "kommentar": "Kassenzählung",
            "details": [
                {"anzahl": 2, "einheit": 0.5},
                {"anzahl": 1, "einheit": 2.0},
            ],
        },
    })
    assert r.status_code == 200
    tid = r.json()["id"]

    rows = session.exec(select(Zaehlprotokoll)).all()
    assert len(rows) == 1
    assert rows[0].abrechnung_tag_id == tid
    assert rows[0].aktiv is True
    assert rows[0].kommentar == "Kassenzählung"
    details = session.exec(select(ZaehlprotokollDetails)).all()
    assert sorted((d.anzahl, d.einheit) for d in details) == [(1, 2.0), (2, 0.5)]


def test_new_count_deactivates_the_previous_one(client, session):
    from sqlmodel import select
    from python.models import Zaehlprotokoll

    client.post("/verkauf/", json={})
    tid = client.post("/abrechnung/tag/", json={
        "zaehlprotokoll": {"kommentar": "Zählung 1"},
    }).json()["id"]

    r = client.post("/zaehlprotokoll/", json={
        "abrechnung_tag_id": tid, "kommentar": "Zählung 2",
    })
    assert r.status_code == 200

    rows = session.exec(
        select(Zaehlprotokoll).order_by(Zaehlprotokoll.id)
    ).all()
    assert [r.aktiv for r in rows] == [False, True]
    assert [r.kommentar for r in rows] == ["Zählung 1", "Zählung 2"]


def test_count_requires_a_settlement(client):
    r = client.post("/zaehlprotokoll/", json={"kommentar": "Ohne Abrechnung"})
    assert r.status_code == 400
    assert "abrechnung_tag_id" in r.json()["detail"]