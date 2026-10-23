import pytest
from datetime import datetime, timezone
from fastapi import HTTPException
from sqlmodel import select

from python.models import Verkauf, VerkaufDetails, VerkaufMwst, Gutschein, Anzahlung, Artikel, Produktgruppe, Lieferant
from python.business.storno_logic import (
    can_storno,
    validate_storno,
    invert_detail,
    invert_mwst,
    create_storno,
    handle_storno_voucher,
    handle_storno_installment,
)


def _create_sale(session, ec_zahlung=False):
    v = Verkauf(verkaufsdatum=datetime.now(timezone.utc), ec_zahlung=ec_zahlung)
    v.rechnungs_nr = None
    session.add(v)
    session.commit()
    session.refresh(v)
    return v


def _add_details(session, rechnungs_nr, items):
    for pos, (artikel_id, stueckzahl, ges_preis, mwst_satz) in enumerate(items, 1):
        d = VerkaufDetails(
            position=pos,
            stueckzahl=stueckzahl,
            ges_preis=ges_preis,
            mwst_satz=mwst_satz,
            rechnungs_nr=rechnungs_nr,
            artikel_id=artikel_id,
        )
        d.vd_id = None
        session.add(d)
    session.commit()


def _add_mwst(session, rechnungs_nr, mwst_satz, mwst_netto, mwst_betrag):
    m = VerkaufMwst(
        rechnungs_nr=rechnungs_nr,
        mwst_satz=mwst_satz,
        mwst_netto=mwst_netto,
        mwst_betrag=mwst_betrag,
    )
    session.add(m)
    session.commit()


def test_can_storno_ok(session):
    v = _create_sale(session)
    ok, msg = can_storno(v, session)
    assert ok
    assert msg == ""


def test_can_storno_already_storned(session):
    v = _create_sale(session)
    storno = Verkauf(
        verkaufsdatum=datetime.now(timezone.utc),
        ec_zahlung=False,
        storno_von=v.rechnungs_nr,
    )
    storno.rechnungs_nr = None
    session.add(storno)
    session.commit()
    ok, msg = can_storno(v, session)
    assert not ok
    assert "storno" in msg.lower()


def test_validate_storno_not_found(session):
    with pytest.raises(HTTPException) as exc:
        validate_storno(session, 99999)
    assert exc.value.status_code == 404


def test_invert_detail(session):
    d = VerkaufDetails(position=1, stueckzahl=3, ges_preis=30.0, mwst_satz=0.19)
    inv = invert_detail(d, 99)
    assert inv.stueckzahl == -3
    assert inv.ges_preis == -30.0
    assert inv.rechnungs_nr == 99
    assert inv.mwst_satz == 0.19


def test_invert_mwst(session):
    m = VerkaufMwst(rechnungs_nr=1, mwst_satz=0.19, mwst_netto=100.0, mwst_betrag=19.0)
    inv = invert_mwst(m, 99)
    assert inv.mwst_netto == -100.0
    assert inv.mwst_betrag == -19.0
    assert inv.rechnungs_nr == 99


def test_create_storno_flow(session):
    v = _create_sale(session)
    _add_details(session, v.rechnungs_nr, [(1, 2, 20.0, 0.19)])
    _add_mwst(session, v.rechnungs_nr, 0.19, 16.81, 3.19)

    storno = create_storno(session, v.rechnungs_nr)
    assert storno.storno_von == v.rechnungs_nr
    assert len(storno.verkauf_details) == 1
    assert storno.verkauf_details[0].stueckzahl == -2
    assert storno.verkauf_details[0].ges_preis == -20.0
    assert len(storno.verkauf_mwst) == 1
    assert storno.verkauf_mwst[0].mwst_netto == -16.81


def test_create_storno_double_storno_fails(session):
    v = _create_sale(session)
    _add_details(session, v.rechnungs_nr, [(1, 1, 10.0, 0.19)])
    _add_mwst(session, v.rechnungs_nr, 0.19, 8.40, 1.60)

    create_storno(session, v.rechnungs_nr)
    with pytest.raises(HTTPException) as exc:
        create_storno(session, v.rechnungs_nr)
    assert exc.value.status_code == 400


def test_handle_storno_voucher(session):
    v = _create_sale(session)
    _add_details(session, v.rechnungs_nr, [(1, 1, 10.0, 0.19)])
    vd = session.exec(select(VerkaufDetails).where(VerkaufDetails.rechnungs_nr == v.rechnungs_nr)).first()

    g = Gutschein(
        gutschein_nr=1,
        datum=datetime.now(timezone.utc),
        gutschein_in_vd_id=vd.vd_id,
        restbetrag=10.0,
    )
    g.gutschein_id = None
    session.add(g)
    session.commit()

    handle_storno_voucher(session, v)

    entries = session.exec(select(Gutschein).where(Gutschein.gutschein_nr == 1)).all()
    assert len(entries) == 2
    cancelled = [e for e in entries if e.restbetrag == 0.0]
    assert len(cancelled) == 1


def test_handle_storno_installment(session):
    v = _create_sale(session)
    _add_details(session, v.rechnungs_nr, [(1, 1, 10.0, 0.19)])
    _add_mwst(session, v.rechnungs_nr, 0.19, 8.40, 1.60)

    a = Anzahlung(
        datum=datetime.now(timezone.utc),
        anzahlung_in_rech_nr=v.rechnungs_nr,
        aufloesung_in_rech_nr=None,
    )
    a.anzahlung_id = None
    session.add(a)
    session.commit()

    create_storno(session, v.rechnungs_nr)
    handle_storno_installment(session, v)

    entries = session.exec(select(Anzahlung).where(Anzahlung.anzahlung_in_rech_nr == v.rechnungs_nr)).all()
    resolved = [e for e in entries if e.aufloesung_in_rech_nr is not None]
    assert len(resolved) == 1
