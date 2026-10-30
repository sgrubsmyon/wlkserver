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


def test_flow(client):
    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tid = r.json()["id"]
    r = client.get(f"/abrechnung/tag/{tid}")
    assert r.status_code == 200
    r = client.get("/abrechnung/tag/")
    assert r.status_code == 200
    assert len(r.json()) == 1
    r = client.get("/abrechnung/tag/offen")
    assert r.status_code == 200


def test_preview_without_sales(client):
    r = client.get("/abrechnung/tag/vorschau")
    assert r.status_code == 200
    body = r.json()
    assert body["open"] is False
    assert body["sales"] == 0
    assert body["expected_balance"] == 0.0
    assert body["mwst"] == []


def _seed_artikel(session, vk_preis=10.0, mwst_satz=0.19):
    from python.models import Artikel, Lieferant, Mwst, Produktgruppe

    m = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name="Abrechnung PG", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    l = Lieferant(lieferant_name="Abrechnung Lieferant")
    session.add(l)
    session.commit()
    session.refresh(l)
    a = Artikel(artikel_nr="AB1", artikel_name="Abrechnungsartikel",
                produktgruppen_id=pg.produktgruppen_id, lieferant_id=l.lieferant_id,
                vk_preis=vk_preis)
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_preview_before_and_after_settlement(client, session):
    a = _seed_artikel(session)
    nr = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 2}],
    }).json()["rechnungs_nr"]

    r = client.get("/abrechnung/tag/vorschau")
    body = r.json()
    assert body["open"] is True
    assert body["sales"] == 1
    assert body["cash_sales"] == 1
    assert body["ec_sales"] == 0
    assert body["rechnungs_nr_von"] == body["rechnungs_nr_bis"] == nr
    assert body["mwst"][0]["bar_brutto"] == 20.0
    assert body["expected_balance"] == body["current_balance"] == 20.0

    # the settlement matches the preview and only links the current Kassenstand
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tag = client.get(f"/abrechnung/tag/{r.json()['id']}").json()
    assert float(tag["mwst"][0]["bar_brutto"]) == body["mwst"][0]["bar_brutto"]
    assert tag["kassenstand_id"] == client.get("/kassenstand/aktuell").json()["kassenstand_id"]

    # nothing left open afterwards
    after = client.get("/abrechnung/tag/vorschau").json()
    assert after["open"] is False
    assert after["sales"] == 0
    assert after["expected_balance"] == body["expected_balance"]


def test_preview_counts_storno_and_retoure(client, session):
    from datetime import datetime, timezone
    from python.models import Verkauf, VerkaufDetails, VerkaufMwst

    r = client.post("/verkauf/", json={})
    assert r.status_code == 200
    nr = r.json()["rechnungs_nr"]
    session.add(VerkaufDetails(position=1, stueckzahl=2, ges_preis=20.0,
                               mwst_satz=0.19, rechnungs_nr=nr))
    session.add(VerkaufMwst(rechnungs_nr=nr, mwst_satz=0.19,
                            mwst_netto=16.81, mwst_betrag=3.19))
    session.commit()
    assert client.post(f"/verkauf/{nr}/storno").status_code == 200

    # a return (negative position) in a separate cash receipt
    retoure = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=False)
    session.add(retoure)
    session.commit()
    session.refresh(retoure)
    session.add(VerkaufDetails(position=1, stueckzahl=-1, ges_preis=-5.0,
                               mwst_satz=0.19, rechnungs_nr=retoure.rechnungs_nr))
    session.commit()

    body = client.get("/abrechnung/tag/vorschau").json()
    assert body["sales"] == 3
    assert body["stornos"] == 1
    assert body["retouren_summe"] == -5.0
    # cancelled original (19.00 gross) is reported positively
    assert body["storno_summe"] == 20.0
    # sale + storno net to zero cash, plus the -5.00 return
    assert body["mwst"][0]["bar_brutto"] == -5.0


def test_preview_subtracts_entnahmen(client):
    client.post("/kassenstand/", json={"neuer_kassenstand": 10.0, "manuell": True})
    r = client.post("/kassenstand/", json={"neuer_kassenstand": 7.0, "manuell": True, "entnahme": True})
    assert r.status_code == 200

    body = client.get("/abrechnung/tag/vorschau").json()
    assert body["current_balance"] == 7.0
    # Entnahmen are reported for the day sheet; the ledger balance already includes them
    assert body["entnahmen"] == 3.0
    assert body["expected_balance"] == 7.0


def test_explicit_settlement_range(client):
    # regression: the explicit-range path used to reference an unset variable
    first = client.post("/verkauf/", json={}).json()["rechnungs_nr"]
    second = client.post("/verkauf/", json={}).json()["rechnungs_nr"]

    r = client.post("/abrechnung/tag/", json={
        "rechnungs_nr_von": first, "rechnungs_nr_bis": first,
    })
    assert r.status_code == 200
    assert r.json()["rechnungs_nr_von"] == first
    assert r.json()["rechnungs_nr_bis"] == first

    # the second receipt is still open and can be settled later
    preview = client.get("/abrechnung/tag/vorschau").json()
    assert preview["open"] is True
    assert preview["rechnungs_nr_von"] == second


def test_backdated_daily_settlement_reopens_month_and_year(client, session):
    a = _seed_artikel(session)
    first = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    }).json()["rechnungs_nr"]
    r = client.post("/abrechnung/tag/", json={
        "zeitpunkt": "2026-08-15T12:00:00+00:00",
        "rechnungs_nr_von": first, "rechnungs_nr_bis": first,
    })
    assert r.status_code == 200
    assert client.post("/abrechnung/monat/", json={"monat": "2026-08"}).status_code == 200
    assert client.post("/abrechnung/jahr/", json={"jahr": 2026}).status_code == 200
    assert client.get("/abrechnung/monat/offen").json() == []
    assert client.get("/abrechnung/jahr/offen").json() == []

    # a backdated daily settlement inside the settled month invalidates both
    second = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    }).json()["rechnungs_nr"]
    r = client.post("/abrechnung/tag/", json={
        "zeitpunkt": "2026-08-20T12:00:00+00:00",
        "rechnungs_nr_von": second, "rechnungs_nr_bis": second,
    })
    assert r.status_code == 200

    assert client.get("/abrechnung/monat/offen").json() == ["2026-08"]
    assert client.get("/abrechnung/monat/").json() == []
    assert client.get("/abrechnung/jahr/").json() == []
    # after recreating the month, the year is due again
    assert client.post("/abrechnung/monat/", json={"monat": "2026-08"}).status_code == 200
    assert client.get("/abrechnung/jahr/offen").json() == [2026]


def test_settlement_writes_abrechnung_tag_tse_row(client, session, monkeypatch):
    from python.models import AbrechnungTagTse

    monkeypatch.setenv("TSE_ID", "7")
    a = _seed_artikel(session)
    client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200

    row = session.get(AbrechnungTagTse, r.json()["id"])
    assert row is not None
    assert row.tse_id == 7
    # status columns stay NULL while the SEAPI status getters are not wrapped
    assert row.tse_serial is None
    assert row.tse_cert_i is None


def test_settlement_stores_current_tse_signature_counter(client, session, monkeypatch):
    from python.utils.tse_client import tse_client

    monkeypatch.setattr(tse_client, "get_signature_counter", lambda: 99)
    a = _seed_artikel(session)
    client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tag = client.get(f"/abrechnung/tag/{r.json()['id']}").json()
    assert tag["last_tse_sig_counter"] == 99


def test_settlement_without_tse_stores_no_signature_counter(client, session):
    a = _seed_artikel(session)
    client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    r = client.post("/abrechnung/tag/", json={})
    assert r.status_code == 200
    tag = client.get(f"/abrechnung/tag/{r.json()['id']}").json()
    assert tag["last_tse_sig_counter"] is None


def test_tse_export_falls_back_to_tx_number(client, session, monkeypatch):
    from python.models import TSETransaction
    from python.utils.tse_client import tse_client

    calls = []
    monkeypatch.setattr(tse_client, "export_partial", lambda **kwargs: calls.append(kwargs) or b"")
    a = _seed_artikel(session)

    first_nr = client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    }).json()["rechnungs_nr"]
    assert client.post("/abrechnung/tag/", json={}).status_code == 200
    calls.clear()

    session.add(TSETransaction(
        transaction_number=41, rechnungs_nr=first_nr, training=False,
        transaction_start="2026-01-01T12:00:00.000+01:00",
        process_type="Kassenbeleg-V1",
    ))
    session.commit()
    client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    assert client.post("/abrechnung/tag/", json={}).status_code == 200

    assert calls[0] == {"last_excluded_signature_counter": 0}
    assert calls[1] == {"start_tx_number": 42}


def test_settlement_accepts_explicit_signature_counter_override(client, session, monkeypatch):
    from python.utils.tse_client import tse_client

    monkeypatch.setattr(tse_client, "get_signature_counter", lambda: 99)
    a = _seed_artikel(session)
    client.post("/verkauf/", json={
        "verkauf_details": [{"artikel_id": a.artikel_id, "stueckzahl": 1}],
    })
    r = client.post("/abrechnung/tag/", json={"last_tse_sig_counter": 5})
    assert r.status_code == 200
    tag = client.get(f"/abrechnung/tag/{r.json()['id']}").json()
    assert tag["last_tse_sig_counter"] == 5
