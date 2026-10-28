import pytest
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException
from pydantic import ValidationError

from python.models import ArtikelCreate, RabattaktionCreate, ZaehlprotokollDetailsCreate
from python.routers.rabattaktion import create_rabattaktion
from python.utils.csv_import import import_artikel_from_csv
from python.utils.validation import ensure_non_negative, ensure_positive, ensure_range


def test_non_negative_accepts_none_zero_and_positive():
    assert ensure_non_negative(None) is None
    assert ensure_non_negative(0) is None
    assert ensure_non_negative(0.0) is None
    assert ensure_non_negative("12.50") is None


def test_non_negative_rejects_negative():
    with pytest.raises(HTTPException) as exc:
        ensure_non_negative(-0.01, field="betrag")
    assert exc.value.status_code == 400
    assert exc.value.detail == "betrag must not be negative"


def test_non_negative_rejects_invalid_value():
    with pytest.raises(HTTPException) as exc:
        ensure_non_negative("abc", field="betrag")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid betrag"


def test_positive_accepts_none_and_positive():
    assert ensure_positive(None) is None
    assert ensure_positive(0.01) is None
    assert ensure_positive("3") is None


@pytest.mark.parametrize("value", [0, 0.0, -1])
def test_positive_rejects_zero_and_negative(value):
    with pytest.raises(HTTPException) as exc:
        ensure_positive(value, field="stueckzahl")
    assert exc.value.status_code == 400
    assert exc.value.detail == "stueckzahl must be positive"


def test_positive_rejects_invalid_value():
    with pytest.raises(HTTPException) as exc:
        ensure_positive("x", field="stueckzahl")
    assert exc.value.detail == "Invalid stueckzahl"


def test_range_accepts_none_and_bounds():
    assert ensure_range(None, 0, 1) is None
    assert ensure_range(0, 0, 1) is None
    assert ensure_range(1, 0, 1) is None
    assert ensure_range("0.19", 0, 1) is None


@pytest.mark.parametrize("value", [-0.01, 1.01])
def test_range_rejects_outside_bounds(value):
    with pytest.raises(HTTPException) as exc:
        ensure_range(value, 0, 1, field="mwst_satz")
    assert exc.value.status_code == 400
    assert exc.value.detail == "mwst_satz must be between 0 and 1"


def test_range_rejects_invalid_value():
    with pytest.raises(HTTPException) as exc:
        ensure_range("abc", 0, 1, field="mwst_satz")
    assert exc.value.status_code == 400
    assert exc.value.detail == "Invalid mwst_satz"


# ------------------------------------------------- model constraints
def test_artikel_rejects_negative_price_and_setgroesse():
    with pytest.raises(ValidationError):
        ArtikelCreate(artikel_nr="A1", artikel_name="x", vk_preis=-1)
    with pytest.raises(ValidationError):
        ArtikelCreate(artikel_nr="A1", artikel_name="x", setgroesse=0)


def test_zaehlprotokoll_details_reject_negative_count_and_zero_unit():
    with pytest.raises(ValidationError):
        ZaehlprotokollDetailsCreate(anzahl=-1, einheit=1)
    with pytest.raises(ValidationError):
        ZaehlprotokollDetailsCreate(anzahl=1, einheit=0)


# --------------------------------------------- cross-field rules (router)
def test_rabattaktion_quantity_discount_requires_schwelle(session):
    now = datetime.now(timezone.utc)
    with pytest.raises(HTTPException) as exc:
        create_rabattaktion(
            RabattaktionCreate(aktionsname="x", von=now, mengenrabatt_relativ=0.1),
            session,
        )
    assert exc.value.detail == "mengenrabatt_relativ requires mengenrabatt_schwelle"


def test_rabattaktion_rejects_bis_before_von(session):
    now = datetime.now(timezone.utc)
    with pytest.raises(HTTPException) as exc:
        create_rabattaktion(
            RabattaktionCreate(aktionsname="x", von=now, bis=now - timedelta(days=1)),
            session,
        )
    assert exc.value.detail == "Invalid dates: 'bis' must be after 'von' or null"


# ------------------------------------------------- CSV import boundary
def test_import_artikel_rejects_negative_price(session):
    csv = "artikel_nr,artikel_name,vk_preis\nA1,Test,-1.00\n"
    with pytest.raises(HTTPException) as exc:
        import_artikel_from_csv(csv, session)
    assert exc.value.detail == "vk_preis must not be negative"


def test_import_artikel_rejects_invalid_ek_rabatt(session):
    csv = "artikel_nr,artikel_name,ek_rabatt\nA1,Test,1.5\n"
    with pytest.raises(HTTPException) as exc:
        import_artikel_from_csv(csv, session)
    assert exc.value.detail == "ek_rabatt must be between 0 and 1"
