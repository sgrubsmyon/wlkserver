import pytest
from decimal import Decimal
from sqlmodel import select

from python.models import (
    Artikel, Produktgruppe, Lieferant, Mwst,
    Verkauf, VerkaufDetails, VerkaufDetailsCreate, VerkaufMwst,
)
from python.business.sale_workflow import (
    validate_detail,
    determine_mwst_satz,
    determine_ges_preis,
    prepare_detail,
    calculate_mwst_summary,
    check_ec_payment_threshold,
    create_verkauf,
)


def _seed_mwst(session, mwst_satz=0.19):
    m = Mwst(mwst_satz=mwst_satz, dsfinvk_ust_schluessel=1)
    m.mwst_id = None
    session.add(m)
    session.commit()
    session.refresh(m)
    return m


def _seed_pg(session, mwst_satz=0.19):
    m = _seed_mwst(session, mwst_satz=mwst_satz)
    pg = Produktgruppe(produktgruppen_name="Test PG", mwst_id=m.mwst_id)
    pg.produktgruppen_id = None
    session.add(pg)
    session.commit()
    session.refresh(pg)
    return pg


def _seed_lieferant(session):
    l = Lieferant(lieferant_name="Test Lieferant")
    l.lieferant_id = None
    session.add(l)
    session.commit()
    session.refresh(l)
    return l


def _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0, variabler_preis=False):
    pg = _seed_pg(session, mwst_satz=mwst_satz)
    l = _seed_lieferant(session)
    a = Artikel(
        artikel_nr="001",
        artikel_name="Test Artikel",
        produktgruppen_id=pg.produktgruppen_id,
        lieferant_id=l.lieferant_id,
        vk_preis=vk_preis,
        variabler_preis=variabler_preis,
    )
    a.artikel_id = None
    session.add(a)
    session.commit()
    session.refresh(a)
    return a


def test_validate_detail_zero_stueckzahl(session):
    with pytest.raises(Exception) as exc:
        validate_detail(session, {"stueckzahl": 0})
    assert "stueckzahl" in str(exc.value)


def test_validate_detail_positive_stueckzahl(session):
    validate_detail(session, {"stueckzahl": 2})


def test_determine_mwst_satz_explicit(session):
    satz = determine_mwst_satz(session, {"mwst_satz": 0.07, "stueckzahl": 1})
    assert satz == 0.07


def test_determine_mwst_satz_none(session):
    satz = determine_mwst_satz(session, {"stueckzahl": 1})
    assert satz is None


def test_determine_ges_preis_explicit(session):
    preis = determine_ges_preis(session, {"ges_preis": 25.50, "stueckzahl": 1})
    assert preis == 25.50


def test_determine_ges_preis_from_artikel(session):
    artikel = _seed_artikel(session, vk_preis=10.0)
    preis = determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 3})
    assert preis == 30.0


def test_determine_ges_preis_variabler_preis_returns_none(session):
    artikel = _seed_artikel(session, vk_preis=10.0, variabler_preis=True)
    preis = determine_ges_preis(session, {"artikel_id": artikel.artikel_id, "stueckzahl": 2})
    assert preis is None


def test_prepare_detail_fills_mwst_and_preis(session):
    artikel = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0)
    d = {"artikel_id": artikel.artikel_id, "stueckzahl": 2}
    vd = prepare_detail(session, d)
    assert vd.mwst_satz == 0.19
    assert vd.ges_preis == 20.0
    assert vd.stueckzahl == 2


def test_prepare_detail_from_verkaufdetailscreate(session):
    artikel = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0)
    d = VerkaufDetailsCreate(
        artikel_id=artikel.artikel_id, stueckzahl=2,
        mwst_satz=None, ges_preis=None, rechnungs_nr=1,
    )
    vd = prepare_detail(session, d)
    assert vd.mwst_satz == 0.19
    assert vd.ges_preis == 20.0
    assert vd.stueckzahl == 2


def test_calculate_mwst_summary(session):
    details = [
        VerkaufDetails(ges_preis=119.00, mwst_satz=0.19, rechnungs_nr=1, position=1, stueckzahl=1),
        VerkaufDetails(ges_preis=119.00, mwst_satz=0.19, rechnungs_nr=1, position=2, stueckzahl=1),
    ]
    summary = calculate_mwst_summary(details)
    rate = Decimal("0.19")
    assert rate in summary
    assert summary[rate]["brutto"] == Decimal("238.00")
    assert summary[rate]["mwst_betrag"] == Decimal("38.00")
    assert summary[rate]["mwst_netto"] == Decimal("200.00")


def test_check_ec_threshold_below(session):
    warning = check_ec_payment_threshold(Decimal("5.00"), True)
    assert warning is not None
    assert "10,00" in warning


def test_check_ec_threshold_above(session):
    warning = check_ec_payment_threshold(Decimal("15.00"), True)
    assert warning is None


def test_check_ec_threshold_cash(session):
    warning = check_ec_payment_threshold(Decimal("5.00"), False)
    assert warning is None


def test_create_verkauf_with_details(session):
    artikel = _seed_artikel(session, mwst_satz=0.19, vk_preis=10.0)
    v = create_verkauf(session, {
        "ec_zahlung": False,
        "verkauf_details": [
            {"artikel_id": artikel.artikel_id, "stueckzahl": 2},
        ],
    })
    assert v.rechnungs_nr is not None
    assert len(v.verkauf_details) == 1
    assert v.verkauf_details[0].ges_preis == 20.0
    assert len(v.verkauf_mwst) == 1
    assert v.verkauf_mwst[0].mwst_satz == 0.19
