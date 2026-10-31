from decimal import Decimal

import pytest

from python.business.vat_calculator import (
    VATCalculator,
    _to_decimal,
    calculate_mwst_values_in_rechnung,
    calculate_netto,
    calculate_total,
    calculate_vat,
    get_all_current_mwst_values_by_id,
    vat_rounding_method,
)


# --------------------------------------------------------------- conversion

def test_to_decimal_accepts_common_types():
    assert _to_decimal(None) is None
    assert _to_decimal(Decimal("1.23")) == Decimal("1.23")
    assert _to_decimal(True) == Decimal("1")
    assert _to_decimal(7) == Decimal("7")
    assert _to_decimal(1.5) == Decimal("1.5")
    assert _to_decimal(" 12,50 ") == Decimal("12.50")
    assert _to_decimal("1.234,56") == Decimal("1234.56")
    assert _to_decimal("") is None
    assert _to_decimal("19%") == Decimal("0.19")


def test_to_decimal_rejects_garbage():
    with pytest.raises(Exception):
        _to_decimal("keine Zahl")


def test_to_decimal_handles_both_separators():
    # thousands separator "." before decimal comma
    assert _to_decimal("1.234,56") == Decimal("1234.56")
    # thousands separator "," before decimal point
    assert _to_decimal("1,234.56") == Decimal("1234.56")


def test_to_decimal_returns_none_for_unknown_objects():
    assert _to_decimal(object()) is None


# ------------------------------------------------------------------ VAT calc

def test_calculate_vat_basic():
    # 19% VAT on 119.00 -> 19.00
    assert calculate_vat(Decimal("119.00"), Decimal("0.19")) == Decimal("19.00")


def test_calculate_vat_zero_rate():
    assert calculate_vat(Decimal("100.00"), Decimal("0")) == Decimal("0.00")


def test_calculate_vat_rounds_half_up():
    # 0.03 at 20 % -> exactly 0.005 -> must round up to 0.01
    assert calculate_vat(Decimal("0.03"), Decimal("0.20")) == Decimal("0.01")


def test_calculate_vat_storno_is_negative():
    assert calculate_vat(Decimal("-119.00"), Decimal("0.19")) == Decimal("-19.00")


def test_calculate_vat_accepts_strings_and_percent():
    assert calculate_vat("119,00", "19%") == Decimal("19.00")


def test_calculate_vat_handles_missing_values():
    assert calculate_vat(None, Decimal("0.19")) == Decimal("0.00")
    assert calculate_vat(Decimal("10.00"), None) == Decimal("0.00")


def test_calculate_netto():
    assert calculate_netto(Decimal("119.00"), Decimal("0.19")) == Decimal("100.00")


def test_calculate_netto_with_rounding():
    assert calculate_netto(Decimal("0.03"), Decimal("0.20")) == Decimal("0.02")


# --------------------------------------------------------------------- total

def test_calculate_total_with_dicts():
    items = [{"ges_preis": 10.0}, {"ges_preis": 20.0}]
    assert calculate_total(items) == Decimal("30.00")


def test_calculate_total_accepts_tuples_lists_and_objects():
    class Item:
        ges_preis = Decimal("5.00")

    items = [("10.00", 0.19), ["2.50"], Item()]
    assert calculate_total(items) == Decimal("17.50")


def test_calculate_total_skips_missing_and_handles_strings():
    items = [{"ges_preis": None}, {"ges_preis": "1.234,56"}, {"brutto": 0.44}]
    assert calculate_total(items) == Decimal("1235.00")


def test_calculate_total_empty():
    assert calculate_total(None) == Decimal("0.00")
    assert calculate_total([]) == Decimal("0.00")


def test_calculate_total_skips_object_with_none_attributes():
    class Item:
        ges_preis = None
        brutto = None

    assert calculate_total([Item()]) == Decimal("0.00")


# ------------------------------------------------------------ receipt values

def test_calculate_mwst_values_in_rechnung():
    items = [{"ges_preis": 119.0, "mwst_satz": 0.19}]
    res = calculate_mwst_values_in_rechnung(items)
    assert Decimal("0.19") in res
    netto, betrag, brutto = res[Decimal("0.19")]
    assert netto == Decimal("100.00")
    assert betrag == Decimal("19.00")
    assert brutto == Decimal("119.00")


def test_calculate_mwst_values_aggregates_and_sorts_by_rate():
    items = [
        {"ges_preis": 107.0, "mwst_satz": 0.07},
        {"ges_preis": 119.0, "mwst_satz": 0.19},
        {"ges_preis": 119.0, "mwst_satz": 0.19},
    ]
    res = calculate_mwst_values_in_rechnung(items)
    assert list(res.keys()) == [Decimal("0.07"), Decimal("0.19")]
    assert res[Decimal("0.07")] == [Decimal("100.00"), Decimal("7.00"), Decimal("107.00")]
    assert res[Decimal("0.19")] == [Decimal("200.00"), Decimal("38.00"), Decimal("238.00")]


def test_calculate_mwst_values_books_missing_rate_as_zero():
    res = calculate_mwst_values_in_rechnung([{"ges_preis": 50.0}])
    assert res[Decimal("0")] == [Decimal("50.00"), Decimal("0.00"), Decimal("50.00")]


def test_calculate_mwst_values_ignores_items_without_price():
    res = calculate_mwst_values_in_rechnung([{"mwst_satz": 0.19}, None])
    assert res == {}


def test_calculate_mwst_values_with_storno_items():
    items = [
        {"ges_preis": 119.0, "mwst_satz": 0.19},
        {"ges_preis": -119.0, "mwst_satz": 0.19},
    ]
    res = calculate_mwst_values_in_rechnung(items)
    assert res[Decimal("0.19")] == [Decimal("0.00"), Decimal("0.00"), Decimal("0.00")]


# ---------------------------------------------------- rounding method (config)

def test_rounding_method_defaults_to_horizontal(monkeypatch):
    monkeypatch.delenv("VAT_ROUNDING_METHOD", raising=False)
    assert vat_rounding_method() == "horizontal"


def test_rounding_method_is_case_insensitive(monkeypatch):
    monkeypatch.setenv("VAT_ROUNDING_METHOD", " Vertical ")
    assert vat_rounding_method() == "vertical"


def test_rounding_method_rejects_unknown_value(monkeypatch):
    monkeypatch.setenv("VAT_ROUNDING_METHOD", "diagonal")
    with pytest.raises(ValueError):
        vat_rounding_method()


def test_vertical_rounding_uses_rate_total():
    # two positions of 0.03 at 20 %: horizontal -> 0.01 + 0.01 = 0.02 VAT,
    # vertical -> 0.06 gross -> 0.01 VAT
    items = [
        {"ges_preis": "0.03", "mwst_satz": 0.20},
        {"ges_preis": "0.03", "mwst_satz": 0.20},
    ]
    horizontal = calculate_mwst_values_in_rechnung(items, method="horizontal")
    vertical = calculate_mwst_values_in_rechnung(items, method="vertical")
    assert horizontal[Decimal("0.20")] == [Decimal("0.04"), Decimal("0.02"), Decimal("0.06")]
    assert vertical[Decimal("0.20")] == [Decimal("0.05"), Decimal("0.01"), Decimal("0.06")]


def test_rounding_method_from_env_is_used(monkeypatch):
    monkeypatch.setenv("VAT_ROUNDING_METHOD", "vertical")
    items = [{"ges_preis": "0.03", "mwst_satz": 0.20}, {"ges_preis": "0.03", "mwst_satz": 0.20}]
    res = calculate_mwst_values_in_rechnung(items)
    assert res[Decimal("0.20")][1] == Decimal("0.01")

    by_id = get_all_current_mwst_values_by_id({1: Decimal("0.20")}, items=items)
    assert by_id[1] == [Decimal("0.20"), Decimal("0.05"), Decimal("0.01"), Decimal("0.06")]


def test_explicit_method_overrides_env(monkeypatch):
    monkeypatch.setenv("VAT_ROUNDING_METHOD", "vertical")
    items = [{"ges_preis": "0.03", "mwst_satz": 0.20}, {"ges_preis": "0.03", "mwst_satz": 0.20}]
    res = calculate_mwst_values_in_rechnung(items, method="horizontal")
    assert res[Decimal("0.20")][1] == Decimal("0.02")


# ------------------------------------------------- current values by MwSt ID

def test_get_all_current_mwst_values_by_id():
    res = get_all_current_mwst_values_by_id(
        {3: Decimal("0.19"), 1: Decimal("0.07")},
        items=[
            {"ges_preis": 119.0, "mwst_satz": 0.19},
            {"ges_preis": 107.0, "mwst_satz": 0.07},
        ],
    )
    assert list(res.keys()) == [3, 1]
    assert res[3] == [Decimal("0.19"), Decimal("100.00"), Decimal("19.00"), Decimal("119.00")]
    assert res[1] == [Decimal("0.07"), Decimal("100.00"), Decimal("7.00"), Decimal("107.00")]


def test_get_all_current_mwst_values_matches_db_scale():
    # DB rates come back as DECIMAL(6,5), e.g. 0.19000
    res = get_all_current_mwst_values_by_id(
        {1: Decimal("0.19000")},
        mwst_values={Decimal("0.19"): [Decimal("50.00"), Decimal("9.50"), Decimal("59.50")]},
    )
    assert res[1] == [Decimal("0.19000"), Decimal("50.00"), Decimal("9.50"), Decimal("59.50")]


def test_get_all_current_mwst_values_skips_unused_rates():
    res = get_all_current_mwst_values_by_id(
        {1: Decimal("0.19"), 2: Decimal("0.07")},
        items=[{"ges_preis": 119.0, "mwst_satz": 0.19}],
    )
    assert list(res.keys()) == [1]


def test_get_all_current_mwst_values_ignores_missing_rates():
    res = get_all_current_mwst_values_by_id(
        {1: None},
        items=[{"ges_preis": 119.0, "mwst_satz": 0.19}],
    )
    assert res == {}


# ---------------------------------------------------------- VATCalculator API

def test_vat_calculator_class_delegates():
    calc = VATCalculator()
    assert calc.calculate_vat("119.00", "0.19") == Decimal("19.00")
    assert VATCalculator.calculateVAT(Decimal("119.00"), Decimal("0.19")) == Decimal("19.00")

    values = calc.calculate_mwst_values_in_rechnung([{"ges_preis": 119.0, "mwst_satz": 0.19}])
    assert values[Decimal("0.19")][1] == Decimal("19.00")

    by_id = calc.get_all_current_mwst_values_by_id(
        {1: Decimal("0.19")}, items=[{"ges_preis": 119.0, "mwst_satz": 0.19}]
    )
    assert by_id[1][0] == Decimal("0.19")
