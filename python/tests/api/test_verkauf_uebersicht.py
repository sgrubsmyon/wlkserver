"""Sales overview endpoint for the Verkäufe page."""
from datetime import datetime, timezone

import pytest
from fastapi.testclient import TestClient
from sqlmodel import select

from python.main import app
from python.models import (
    AbrechnungTag,
    Artikel,
    Lieferant,
    Mwst,
    Produktgruppe,
    User,
    Verkauf,
    VerkaufDetails,
    VerkaufMwst,
)
from python.session import get_session


@pytest.fixture
def client(session):
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"username": "test", "password": "test"})
        c.headers["Authorization"] = "Bearer " + r.json()["access_token"]
        yield c
    app.dependency_overrides.clear()


def _seed_verkauf(session, nummer, ges_preis=10.0, mwst_satz=0.19, ec=False,
                  kunde_gibt=None, user_id=None, mwst_betrag=1.6):
    v = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=ec,
        kunde_gibt=kunde_gibt,
        user_id=user_id,
    )
    v.rechnungs_nr = nummer
    session.add(v)
    session.add(VerkaufDetails(
        position=1, stueckzahl=1, ges_preis=ges_preis, mwst_satz=mwst_satz,
        rechnungs_nr=nummer,
    ))
    session.add(VerkaufMwst(
        rechnungs_nr=nummer, mwst_satz=mwst_satz,
        mwst_netto=ges_preis - mwst_betrag, mwst_betrag=mwst_betrag,
    ))
    session.commit()
    return v


def _settle(session, bis):
    row = AbrechnungTag(
        zeitpunkt=datetime.now(timezone.utc),
        zeitpunkt_real=datetime.now(timezone.utc),
        rechnungs_nr_von=1,
        rechnungs_nr_bis=bis,
    )
    row.id = None
    session.add(row)
    session.commit()


def test_uebersicht_splits_at_last_settlement(client, session):
    user = session.exec(select(User).where(User.username == "test")).first()
    _seed_verkauf(session, 1, ges_preis=10.0, mwst_satz=0.19, kunde_gibt=20.0,
                  user_id=user.user_id, mwst_betrag=1.6)
    _seed_verkauf(session, 2, ges_preis=5.0, mwst_satz=0.07, ec=True,
                  user_id=user.user_id, mwst_betrag=0.33)

    body = client.get("/verkauf/uebersicht", params={"nur_heute": True}).json()
    assert [row["rechnungs_nr"] for row in body] == [2, 1]
    assert body[1]["summe"] == 10.0
    assert body[1]["mwst_19"] == 1.6
    assert body[1]["username"] == "test"
    assert body[1]["kunde_gibt"] == 20.0
    assert body[0]["mwst_7"] == 0.33
    assert body[0]["ec_zahlung"] is True
    assert client.get("/verkauf/uebersicht", params={"nur_heute": False}).json() == []

    _settle(session, bis=1)
    old = client.get("/verkauf/uebersicht", params={"nur_heute": False}).json()
    assert [row["rechnungs_nr"] for row in old] == [1]
    today = client.get("/verkauf/uebersicht", params={"nur_heute": True}).json()
    assert [row["rechnungs_nr"] for row in today] == [2]


def test_sale_details_carry_article_number_and_supplier(client, session):
    m = Mwst(mwst_satz=0.19, dsfinvk_ust_schluessel=1)
    session.add(m)
    session.commit()
    session.refresh(m)
    pg = Produktgruppe(produktgruppen_name="PG", mwst_id=m.mwst_id)
    session.add(pg)
    session.commit()
    session.refresh(pg)
    lieferant = Lieferant(lieferant_name="Hofladen", lieferant_kurzname="HOF")
    session.add(lieferant)
    session.commit()
    session.refresh(lieferant)
    artikel = Artikel(
        artikel_nr="A1", artikel_name="Apfel", produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=lieferant.lieferant_id, vk_preis=2.0,
    )
    session.add(artikel)
    session.commit()
    session.refresh(artikel)

    v = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=False)
    session.add(v)
    session.commit()
    session.refresh(v)
    session.add(VerkaufDetails(
        position=1, stueckzahl=2, ges_preis=4.0, mwst_satz=0.19,
        rechnungs_nr=v.rechnungs_nr, artikel_id=artikel.artikel_id,
    ))
    session.commit()

    detail = client.get(f"/verkauf/{v.rechnungs_nr}").json()["verkauf_details"][0]
    assert detail["artikel_nr"] == "A1"
    assert detail["lieferant_kurzname"] == "HOF"
    assert detail["artikel_vk_preis"] == 2.0
