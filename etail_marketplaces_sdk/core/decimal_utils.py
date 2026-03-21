"""Shared helpers for mapping API payloads to Decimal / optional numeric fields."""

from __future__ import annotations

from decimal import Decimal
from typing import Any, Optional


def optional_decimal(value: Any) -> Optional[Decimal]:
    """Parse a numeric API value to Decimal, or return None if missing / invalid."""
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value))
    except (ArithmeticError, ValueError, TypeError):
        return None
