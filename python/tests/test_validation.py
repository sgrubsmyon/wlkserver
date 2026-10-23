import pytest
from fastapi import HTTPException

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
