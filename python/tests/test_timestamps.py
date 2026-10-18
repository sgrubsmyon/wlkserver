import pytest
from datetime import datetime, timezone, timedelta

from sqlmodel import select

from python.models import (
    Artikel, ArtikelCreate, Lieferant, Produktgruppe,
    Rabattaktion, RabattaktionCreate,
    Verkauf,
)
from python.routers.artikel import create_artikel
from python.routers.rabattaktion import create_rabattaktion


# --- Verkauf (verkaufsdatum) ---

def test_verkauf_verkaufsdatum_is_utc_aware(session):
    v = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=False)
    session.add(v)
    session.commit()
    session.refresh(v)

    assert v.verkaufsdatum.tzinfo is not None
    assert v.verkaufsdatum.utcoffset() == timedelta(0)

    # round-trip through the database preserves tzinfo
    v2 = session.get(Verkauf, v.rechnungs_nr)
    assert v2.verkaufsdatum.tzinfo is not None
    assert v2.verkaufsdatum.utcoffset() == timedelta(0)


def test_verkauf_stores_utc_value_unchanged(session):
    dt = datetime(2024, 6, 15, 10, 30, 0, tzinfo=timezone.utc)
    v = Verkauf(verkaufsdatum=dt, ec_zahlung=False, kunde_gibt=5.0)
    session.add(v)
    session.commit()
    session.refresh(v)

    v2 = session.get(Verkauf, v.rechnungs_nr)
    assert v2.verkaufsdatum == dt
    assert v2.verkaufsdatum.utcoffset() == timedelta(0)


# --- Rabattaktion (von / bis) ---

def test_rabattaktion_von_bis_are_utc_aware(session):
    now = datetime.now(timezone.utc)
    ra = Rabattaktion(aktionsname="test", von=now, bis=now + timedelta(days=1))
    session.add(ra)
    session.commit()
    session.refresh(ra)

    assert ra.von.tzinfo is not None and ra.von.utcoffset() == timedelta(0)
    assert ra.bis.tzinfo is not None and ra.bis.utcoffset() == timedelta(0)

    ra2 = session.get(Rabattaktion, ra.rabatt_id)
    assert ra2.von.utcoffset() == timedelta(0)
    assert ra2.bis.utcoffset() == timedelta(0)


def test_create_rabattaktion_normalizes_naive_von_to_utc(session):
    naive_von = datetime(2024, 1, 1, 12, 0, 0)  # naive -> treated as UTC
    ra = create_rabattaktion(
        RabattaktionCreate(aktionsname="naive", von=naive_von), session
    )
    assert ra.von.tzinfo is not None
    assert ra.von.utcoffset() == timedelta(0)
    # value preserved, only tzinfo attached
    assert ra.von.replace(tzinfo=None) == naive_von


def test_rabattaktion_bis_none_allowed(session):
    ra = Rabattaktion(aktionsname="open", von=datetime.now(timezone.utc), bis=None)
    session.add(ra)
    session.commit()
    session.refresh(ra)
    assert ra.bis is None
    ra2 = session.get(Rabattaktion, ra.rabatt_id)
    assert ra2.bis is None


# --- Artikel (von / bis) ---

def _make_lieferant_and_pg(session):
    lieferant = Lieferant(lieferant_name="L", aktiv=True)
    session.add(lieferant)
    session.commit()
    session.refresh(lieferant)

    pg = Produktgruppe(
        toplevel_id=1, sub_id=None, subsub_id=None,
        produktgruppen_name="PG", std_einheit=None,
        aktiv=True, n_artikel=0, n_artikel_rekursiv=0,
    )
    session.add(pg)
    session.commit()
    session.refresh(pg)
    return lieferant, pg


def test_artikel_von_is_utc_aware_on_create(session):
    lieferant, pg = _make_lieferant_and_pg(session)

    ac = ArtikelCreate(
        artikel_nr="T1", artikel_name="Test Artikel",
        produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=lieferant.lieferant_id,
    )
    art = create_artikel(ac, session)

    assert art.von is not None
    assert art.von.tzinfo is not None
    assert art.von.utcoffset() == timedelta(0)
    assert art.bis is None

    # round-trip
    art2 = session.get(Artikel, art.artikel_id)
    assert art2.von is not None
    assert art2.von.utcoffset() == timedelta(0)


def test_artikel_deactivation_sets_bis_utc(session):
    lieferant, pg = _make_lieferant_and_pg(session)
    ac = ArtikelCreate(
        artikel_nr="T2", artikel_name="Test Artikel 2",
        produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=lieferant.lieferant_id,
    )
    art = create_artikel(ac, session)
    from python.routers.artikel import delete_artikel_intern
    deleted = delete_artikel_intern(art.artikel_id, session)

    assert deleted.bis is not None
    assert deleted.bis.tzinfo is not None
    assert deleted.bis.utcoffset() == timedelta(0)


# --- Model-level: naive datetimes are not silently accepted as aware? ---
# (sanity check that aware values survive model_validate)

def test_verkauf_model_validate_preserves_aware_utc(session):
    dt = datetime.now(timezone.utc)
    v = Verkauf.model_validate({"verkaufsdatum": dt, "ec_zahlung": False})
    assert v.verkaufsdatum.tzinfo is not None
    assert v.verkaufsdatum.utcoffset() == timedelta(0)
