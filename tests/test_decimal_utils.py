"""Pure unit tests for :func:`optional_decimal` — no I/O."""

from __future__ import annotations

from decimal import Decimal

import pytest

from etail_marketplaces_sdk.core.decimal_utils import optional_decimal


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        ("", None),
        ("0", Decimal("0")),
        ("12.5", Decimal("12.5")),
        (42, Decimal("42")),
        (3.14, Decimal("3.14")),
    ],
)
def test_optional_decimal_parses_or_none(value, expected):
    assert optional_decimal(value) == expected


@pytest.mark.parametrize("bad", ["not-a-number", {}, []])
def test_optional_decimal_invalid_returns_none(bad):
    assert optional_decimal(bad) is None
