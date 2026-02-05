from datetime import datetime
import pytest
from fastapi import HTTPException

from sqlmodel import select

from routers.verkauf import storno_verkauf, read_single_verkauf
from models import Verkauf, VerkaufDetails, VerkaufMwst


def test_storno_creates_inverted_entries(session):
    # Create original sale
    original = Verkauf(verkaufsdatum=datetime.now(), ec_zahlung=False, kunde_gibt=20.0)
    session.add(original)
    session.commit()
    session.refresh(original)

    # Add one detail and one mwst
    d = VerkaufDetails(
        position=1,
        stueckzahl=2,
        ges_preis=10.0,
        mwst_satz=0.19,
        rechnungs_nr=original.rechnungs_nr,
    )
    m = VerkaufMwst(
        rechnungs_nr=original.rechnungs_nr,
        mwst_satz=0.19,
        mwst_netto=16.8,
        mwst_betrag=3.2,
    )
    session.add_all([d, m])
    session.commit()

    # Perform storno
    storno = storno_verkauf(original.rechnungs_nr, session)

    # Basic checks
    assert storno["storno_von"] == original.rechnungs_nr
    assert storno["rechnungs_nr"] != original.rechnungs_nr

    # Details should be inverted
    details = storno["verkauf_details"]
    assert len(details) == 1
    assert details[0]["stueckzahl"] == -2
    assert details[0]["ges_preis"] == -10.0

    # MwSt should be inverted
    mwsts = storno["verkauf_mwst"]
    assert len(mwsts) == 1
    assert mwsts[0]["mwst_netto"] == -16.8
    assert mwsts[0]["mwst_betrag"] == -3.2


def test_duplicate_storno_is_prevented(session):
    original = Verkauf(verkaufsdatum=datetime.now(), ec_zahlung=False)
    session.add(original)
    session.commit()
    session.refresh(original)

    # First storno succeeds
    s = storno_verkauf(original.rechnungs_nr, session)
    assert s["storno_von"] == original.rechnungs_nr

    # Second storno attempt should raise HTTPException (400)
    with pytest.raises(HTTPException) as exc:
        storno_verkauf(original.rechnungs_nr, session)
    assert exc.value.status_code == 400