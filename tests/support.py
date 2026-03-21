"""Small helpers for tests — keep fixtures on disk, loading logic in one place."""

from __future__ import annotations

import json
from pathlib import Path

_FIXTURES_ORDERS = Path(__file__).resolve().parent / "fixtures" / "orders"


def load_order_fixture(filename: str) -> dict:
    """Load a trimmed API-shaped order dict from ``tests/fixtures/orders``."""
    path = _FIXTURES_ORDERS / filename
    return json.loads(path.read_text(encoding="utf-8"))
