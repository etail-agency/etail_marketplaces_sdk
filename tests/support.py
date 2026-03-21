"""Small helpers for tests — keep fixtures on disk, loading logic in one place."""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def load_fixture(*parts: str) -> dict:
    """Load JSON from ``tests/fixtures/{parts}`` (e.g. ``("orders", "x.json")``)."""
    path = _FIXTURES.joinpath(*parts)
    return json.loads(path.read_text(encoding="utf-8"))


def load_order_fixture(filename: str) -> dict:
    """Load a trimmed order-shaped dict from ``tests/fixtures/orders``."""
    return load_fixture("orders", filename)
