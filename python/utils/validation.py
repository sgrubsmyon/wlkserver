"""Validation helpers."""
from __future__ import annotations

from decimal import Decimal
from typing import Any

from fastapi import HTTPException


def ensure_non_negative(value: Any, field: str = "value"):
    if value is None:
        return
    try:
        if Decimal(str(value)) < 0:
            raise HTTPException(status_code=400, detail=f"{field} must not be negative")
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


def ensure_positive(value: Any, field: str = "value"):
    if value is None:
        return
    try:
        if Decimal(str(value)) <= 0:
            raise HTTPException(status_code=400, detail=f"{field} must be positive")
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")


def ensure_range(value: Any, lo: Any, hi: Any, field: str = "value"):
    if value is None:
        return
    try:
        v = Decimal(str(value))
        if v < Decimal(str(lo)) or v > Decimal(str(hi)):
            raise HTTPException(status_code=400, detail=f"{field} must be between {lo} and {hi}")
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=400, detail=f"Invalid {field}")
