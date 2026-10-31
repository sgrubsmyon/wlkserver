import pytest

from fastapi.testclient import TestClient

from python.main import app

from python.session import get_session

from decimal import Decimal


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        if r.status_code == 200:
            c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _counts(notes, coins):
    """Build a Zählprotokoll that amounts to the given note/coin totals."""
    out = []
    for wert in (100, 50, 20, 10, 5):
        while notes >= wert:
            notes -= wert
            out.append({"einheit": wert, "anzahl": 1})
    for wert in ("2.00", "1.00", "0.50", "0.20", "0.10", "0.05", "0.02", "0.01"):
        while coins >= Decimal(wert):
            coins -= Decimal(wert)
            out.append({"einheit": float(wert), "anzahl": 1})
    assert Decimal(str(notes)) == 0 and coins == 0
    return out


def _apply(details, suggestion):
    """Physical outcome of the suggestion: exchange first, then both deltas."""
    counts = {}
    for d in details:
        counts[Decimal(str(d["einheit"]))] = counts.get(Decimal(str(d["einheit"])), 0) + d["anzahl"]
    coins = sum((w * counts.get(w, 0) for w in
                 (Decimal("0.01"), Decimal("0.02"), Decimal("0.05"), Decimal("0.10"),
                  Decimal("0.20"), Decimal("0.50"), Decimal("1.00"), Decimal("2.00"))), Decimal("0"))
    notes = sum((w * counts.get(w, 0) for w in
                 (Decimal("5"), Decimal("10"), Decimal("20"), Decimal("50"),
                  Decimal("100"), Decimal("200"))), Decimal("0"))
    tausch = Decimal(str(suggestion["tausch"]))
    return (notes - tausch + Decimal(str(suggestion["scheine_delta"])),
            coins + tausch + Decimal(str(suggestion["muenzen_delta"])))


def test_create_and_read(client):
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    assert r.status_code == 200
    ks_id = r.json()["kassenstand_id"]
    r = client.get(f"/kassenstand/{ks_id}")
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 100.0
    r = client.get("/kassenstand/aktuell")
    assert r.status_code == 200


def test_rechnungen_filter(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 50.0, "manuell": True})
    client.post("/kassenstand/", json={"neuer_kassenstand": 60.0, "manuell": False})
    r = client.get("/kassenstand/")
    assert all(k["manuell"] for k in r.json())
    r = client.get("/kassenstand/?rechnungen=true")
    assert len(r.json()) >= 2


def test_negative_rejected(client):
    r = client.post("/kassenstand/", json={"neuer_kassenstand": -1.0, "manuell": True})
    assert r.status_code == 422


def test_entnahme_must_not_increase_balance(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 150.0, "manuell": True, "entnahme": True})
    assert r.status_code == 400


def test_entnahme_below_zero_rejected(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 20.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": -5.0, "manuell": True, "entnahme": True})
    assert r.status_code == 422


def test_valid_entnahme_accepted(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 100.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 40.0, "manuell": True, "entnahme": True})
    assert r.status_code == 200
    assert r.json()["neuer_kassenstand"] == 40.0


def test_reset_suggestion_cases(client):
    # (notes, coins) -> (tausch, scheine_delta, muenzen_delta)
    cases = {
        (130, "42.35"): ("10.00", "-20.00", "-2.35"),   # Java dialogue example
        (110, "20"): ("10.00", "0.00", "20.00"),        # under-filled drawer, notes too many
        (90, "70"): ("-10.00", "0.00", "-10.00"),       # notes short, coins over
        (120, "60"): ("0.00", "-20.00", "-10.00"),      # both over
        (90, "40"): ("0.00", "10.00", "10.00"),         # both short
    }
    for (notes, coins), (tausch, scheine, muenzen) in cases.items():
        details = _counts(Decimal(str(notes)), Decimal(str(coins)))
        r = client.post("/kassenstand/zuruecksetzen/vorschau", json=details)
        assert r.status_code == 200, (notes, coins, r.json())
        body = r.json()
        assert Decimal(str(body["tausch"])) == Decimal(tausch)
        assert Decimal(str(body["scheine_delta"])) == Decimal(scheine)
        assert Decimal(str(body["muenzen_delta"])) == Decimal(muenzen)
        end_notes, end_coins = _apply(details, body)
        assert (end_notes, end_coins) == (Decimal("100"), Decimal("50")), (notes, coins)


def test_reset_suggestion_always_reaches_the_target(client, monkeypatch):
    # property: every drawer state ends at 100 EUR notes / 50 EUR coins, with
    # whole-note movements only and no removal beyond the counted stock
    monkeypatch.setenv("SOLL_MUENZ_KASSENSTAND", "50.00")
    monkeypatch.setenv("SOLL_SCHEIN_KASSENSTAND", "100.00")
    for notes in range(0, 205, 15):
        for cents in range(0, 10001, 375):
            coins = Decimal(cents) / 100
            details = _counts(Decimal(notes), coins)
            r = client.post("/kassenstand/zuruecksetzen/vorschau", json=details)
            assert r.status_code == 200
            body = r.json()
            end_notes, end_coins = _apply(details, body)
            assert (end_notes, end_coins) == (Decimal("100"), Decimal("50")), (notes, coins, body)
            assert Decimal(str(body["scheine_delta"])) % 5 == 0
            assert Decimal(str(body["tausch"])) % 5 == 0
            assert Decimal(str(body["scheine_delta"])) >= -Decimal(notes)
            assert Decimal(str(body["muenzen_delta"])) >= -coins
            assert Decimal(str(body["gezaehlt_kassenstand"])) == Decimal(notes) + coins
            assert Decimal(str(body["entnahme"])) == Decimal(notes) + coins - Decimal("150")


def test_reset_suggestion_rejects_unknown_denomination(client):
    r = client.post("/kassenstand/zuruecksetzen/vorschau", json=[{"einheit": 3.0, "anzahl": 1}])
    assert r.status_code == 400
    # a missing denomination just counts as zero
    r = client.post("/kassenstand/zuruecksetzen/vorschau", json=[{"einheit": 10.0, "anzahl": 3}])
    assert r.status_code == 200
    assert r.json()["gezaehlt_muenzen"] == 0
    assert r.json()["gezaehlt_scheine"] == 30.0


def test_reset_suggestion_uses_configured_targets(client, monkeypatch):
    monkeypatch.setenv("SOLL_MUENZ_KASSENSTAND", "20.00")
    monkeypatch.setenv("SOLL_SCHEIN_KASSENSTAND", "80.00")
    r = client.post("/kassenstand/zuruecksetzen/vorschau", json=[{"einheit": 10.0, "anzahl": 10}])
    assert r.status_code == 200
    body = r.json()
    assert body["soll_kassenstand"] == 100.0
    assert body["entnahme"] == 0.0          # 100 EUR counted, 100 EUR target
    # 100 EUR in notes, 0 EUR in coins: swap 20 EUR notes into coins
    assert body["tausch"] == 20.0
    assert body["scheine_delta"] == 0.0
    assert body["muenzen_delta"] == 0.0
    details = [{"einheit": 10.0, "anzahl": 10}]
    assert _apply(details, body) == (Decimal("80"), Decimal("20"))
