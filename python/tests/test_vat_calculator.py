from decimal import Decimal

from python.business.vat_calculator import (
    calculate_vat,
    calculate_netto,
    calculate_total,
    calculate_mwst_values_in_rechnung,
)


def test_calculate_vat_basic():
    # 19% VAT on 119.00 -> 19.00
    assert calculate_vat(Decimal("119.00"), Decimal("0.19")) == Decimal("19.00")


def test_calculate_vat_zero_rate():
    assert calculate_vat(Decimal("100.00"), Decimal("0")) == Decimal("0.00")


def test_calculate_netto():
    assert calculate_netto(Decimal("119.00"), Decimal("0.19")) == Decimal("100.00")


def test_calculate_total():
    items = [{"ges_preis": 10.0}, {"ges_preis": 20.0}]
    assert calculate_total(items) == Decimal("30.00")


def test_calculate_mwst_values_in_rechnung():
    items = [{"ges_preis": 119.0, "mwst_satz": 0.19}]
    res = calculate_mwst_values_in_rechnung(items)
    assert Decimal("0.19") in res
    netto, betrag, brutto = res[Decimal("0.19")]
    assert netto == Decimal("100.00")
    assert betrag == Decimal("19.00")
    assert brutto == Decimal("119.00")