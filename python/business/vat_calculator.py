"""VAT (MwSt) calculation and aggregation helpers."""
from decimal import Decimal, ROUND_HALF_UP
from collections import OrderedDict
from typing import Any, Iterable, Mapping, Optional


CENT = Decimal("0.01")
ONE = Decimal("1")


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
    b = _to_decimal(brutto)
    s = _to_decimal(steuersatz)
    if b is None:
        b = Decimal("0")
    if s is None:
        s = Decimal("0")
    vat = (b / (ONE + s)) * s
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
    result = OrderedDict()
    for item in (items or []):
        brutto, steuersatz = _normalize_item(item)
        if brutto is None:
            continue
        if steuersatz is None:
            steuersatz = Decimal("0")
        steuer = calculate_vat(brutto, steuersatz)
        netto = (brutto - steuer).quantize(CENT, rounding=ROUND_HALF_UP)
        brutto_q = brutto.quantize(CENT, rounding=ROUND_HALF_UP)
        if steuersatz not in result:
            result[steuersatz] = [Decimal("0"), Decimal("0"), Decimal("0")]
        result[steuersatz][0] = (result[steuersatz][0] + netto).quantize(CENT, rounding=ROUND_HALF_UP)
        result[steuersatz][1] = (result[steuersatz][1] + steuer).quantize(CENT, rounding=ROUND_HALF_UP)
        result[steuersatz][2] = (result[steuersatz][2] + brutto_q).quantize(CENT, rounding=ROUND_HALF_UP)
    return result


calculateMwStValuesInRechnung = calculate_mwst_values_in_rechnung
calculate_mwst_values = calculate_mwst_values_in_rechnung
calculateMwstValuesInRechnung = calculate_mwst_values_in_rechnung


def get_all_current_mwst_values_by_id(mwst_rates, mwst_values=None, items=None):
    if mwst_values is None:
        mwst_values = calculate_mwst_values_in_rechnung(items or [])
    normalised = {}
    for k, v in (mwst_values or {}).items():
        kd = _to_decimal(k)
        key = format(kd, "f") if kd is not None else str(k)
        normalised[key] = list(v)
    result = OrderedDict()
    for mwst_id, rate in (mwst_rates or {}).items():
        rd = _to_decimal(rate)
        key = format(rd, "f") if rd is not None else str(rate)
        if key in normalised:
            vals = normalised[key]
            result[mwst_id] = [rd] + [Decimal(x) for x in vals[:3]]
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
