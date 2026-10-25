"""VAT (MwSt) calculation and aggregation helpers."""
from decimal import Decimal, ROUND_HALF_UP
from collections import OrderedDict
from typing import Any, Iterable, Mapping, Optional


CENT = Decimal("0.01")
ONE = Decimal("1")
TEN_PLACES = Decimal("0.0000000001")


def _to_decimal(value):
    if value is None:
        return None
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        return Decimal(int(value))
    if isinstance(value, int):
        return Decimal(value)
    if isinstance(value, float):
        return Decimal(repr(value))
    if isinstance(value, str):
        s = value.strip().replace(" ", "")
        if s == "":
            return None
        if "," in s and "." in s:
            if s.rfind(",") > s.rfind("."):
                s = s.replace(".", "").replace(",", ".")
            else:
                s = s.replace(",", "")
        else:
            s = s.replace(",", ".")
        if s.endswith("%"):
            s = s[:-1]
            return Decimal(s) / Decimal(100)
        return Decimal(s)
    try:
        return Decimal(str(value))
    except Exception:
        return None


def _attr(obj, *names):
    if isinstance(obj, Mapping):
        for name in names:
            if name in obj:
                return obj[name]
        return None
    for name in names:
        if hasattr(obj, name):
            val = getattr(obj, name)
            if val is not None:
                return val
    for name in names:
        if hasattr(obj, name):
            return getattr(obj, name)
    return None


def _normalize_item(item):
    if isinstance(item, (tuple, list)):
        if len(item) >= 2:
            return _to_decimal(item[0]), _to_decimal(item[1])
        if len(item) == 1:
            return _to_decimal(item[0]), None
    brutto = _attr(item, "ges_preis", "brutto", "total_price", "totalPrice", "preis", "amount", "bruttopreis")
    steuersatz = _attr(item, "mwst_satz", "mwst", "steuersatz", "vat_rate", "tax_rate", "ust_satz")
    return _to_decimal(brutto), _to_decimal(steuersatz)


def calculate_vat(brutto, steuersatz):
    """VAT contained in a gross amount.

    Mirrors the Java POS (`WindowContent.calculateVAT`): divide by `1 + rate`
    to 10 decimal places (HALF_UP), multiply by the rate, then round the result
    to cents (HALF_UP, like `BaseClass.priceFormatterIntern`).
    """
    b = _to_decimal(brutto)
    s = _to_decimal(steuersatz)
    if b is None:
        b = Decimal("0")
    if s is None:
        s = Decimal("0")
    quotient = (b / (ONE + s)).quantize(TEN_PLACES, rounding=ROUND_HALF_UP)
    vat = quotient * s
    return vat.quantize(CENT, rounding=ROUND_HALF_UP)


calculateVAT = calculate_vat


def calculate_netto(brutto, steuersatz):
    b = _to_decimal(brutto) or Decimal("0")
    return (b - calculate_vat(b, steuersatz)).quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_total(items):
    total = Decimal("0")
    for item in (items or []):
        b, _ = _normalize_item(item)
        if b is not None:
            total += b
    return total.quantize(CENT, rounding=ROUND_HALF_UP)


def calculate_mwst_values_in_rechnung(items=None):
    """Aggregate netto/VAT/gross per VAT rate for one receipt.

    Mirrors Java `RechnungsGrundlage.calculateMwStValuesInRechnung`: rates are
    returned sorted ascending (Java uses a TreeMap) and items without a VAT
    rate are booked at 0 %.
    """
    sums = {}
    for item in (items or []):
        brutto, steuersatz = _normalize_item(item)
        if brutto is None:
            continue
        if steuersatz is None:
            steuersatz = Decimal("0")
        steuer = calculate_vat(brutto, steuersatz)
        netto = brutto - steuer
        if steuersatz not in sums:
            sums[steuersatz] = [Decimal("0"), Decimal("0"), Decimal("0")]
        sums[steuersatz][0] += netto
        sums[steuersatz][1] += steuer
        sums[steuersatz][2] += brutto

    result = OrderedDict()
    for steuersatz in sorted(sums):
        result[steuersatz] = [
            value.quantize(CENT, rounding=ROUND_HALF_UP) for value in sums[steuersatz]
        ]
    return result


calculateMwStValuesInRechnung = calculate_mwst_values_in_rechnung
calculate_mwst_values = calculate_mwst_values_in_rechnung
calculateMwstValuesInRechnung = calculate_mwst_values_in_rechnung


def get_all_current_mwst_values_by_id(mwst_rates, mwst_values=None, items=None):
    """Map MwSt IDs to [rate, netto, betrag, brutto] for the current receipt.

    Mirrors Java `getAllCurrentMwstValuesByID()`. Rates are matched
    numerically, so a DB rate like `0.19000` also matches `0.19`.
    """
    if mwst_values is None:
        mwst_values = calculate_mwst_values_in_rechnung(items or [])
    by_rate = {}
    for rate, values in (mwst_values or {}).items():
        rate_decimal = _to_decimal(rate)
        if rate_decimal is not None:
            by_rate[rate_decimal] = list(values)
    result = OrderedDict()
    for mwst_id, rate in (mwst_rates or {}).items():
        rate_decimal = _to_decimal(rate)
        if rate_decimal is not None and rate_decimal in by_rate:
            values = by_rate[rate_decimal]
            result[mwst_id] = [rate_decimal] + [Decimal(str(x)) for x in values[:3]]
    return result


getAllCurrentMwstValuesByID = get_all_current_mwst_values_by_id


class VATCalculator:
    @staticmethod
    def calculate_vat(brutto, steuersatz):
        return calculate_vat(brutto, steuersatz)
    calculateVAT = calculate_vat

    @staticmethod
    def calculate_mwst_values_in_rechnung(items=None):
        return calculate_mwst_values_in_rechnung(items)
    calculateMwStValuesInRechnung = calculate_mwst_values_in_rechnung

    @staticmethod
    def get_all_current_mwst_values_by_id(mwst_rates, mwst_values=None, items=None):
        return get_all_current_mwst_values_by_id(mwst_rates, mwst_values=mwst_values, items=items)
    getAllCurrentMwstValuesByID = get_all_current_mwst_values_by_id


__all__ = [
    "calculate_vat", "calculateVAT", "calculate_netto", "calculate_total",
    "calculate_mwst_values_in_rechnung", "calculateMwStValuesInRechnung",
    "calculate_mwst_values", "calculateMwstValuesInRechnung",
    "get_all_current_mwst_values_by_id", "getAllCurrentMwstValuesByID",
    "VATCalculator", "_to_decimal",
]
