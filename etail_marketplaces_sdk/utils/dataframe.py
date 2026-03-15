"""
DataFrame conversion utility.

Works with any list of SDK canonical models (Order, Invoice, Shipment, …) because
they all expose a ``to_dict()`` method.  pandas is an optional dependency — install
it with:

    pip install etail-marketplaces-sdk[pandas]
    # or
    uv add pandas

Usage::

    from etail_marketplaces_sdk.utils import to_dataframe

    orders = client.fetch_orders(days_ago=30)

    # One row per order
    df = to_dataframe(orders)

    # One row per order line item (order fields repeated on every row)
    df_items = to_dataframe(orders, mode="items")

    # Raw platform payloads
    raw = client.fetch_raw_orders(days_ago=30)
    df_raw = to_dataframe(raw)
"""

from __future__ import annotations

import json
from typing import Any, Literal


def to_dataframe(
    records: list[Any],
    mode: Literal["records", "items"] = "records",
    items_field: str = "items",
):
    """Convert a list of SDK models (or plain dicts) to a pandas DataFrame.

    Args:
        records:      List of SDK canonical model instances or plain dicts.
                      Every SDK model exposes ``to_dict()``; raw payloads from
                      ``fetch_raw_*`` methods are already dicts and work directly.
        mode:         ``"records"`` — one row per record (default).
                      ``"items"``   — one row per line item; parent record fields
                      are repeated on every item row.  Useful for per-SKU sales
                      analysis.  Requires the record to have an ``items`` (or
                      *items_field*) key that holds a list of dicts.
        items_field:  Name of the nested list key when ``mode="items"``.
                      Defaults to ``"items"``.

    Returns:
        pandas.DataFrame

    Raises:
        ImportError: if pandas is not installed.
    """
    try:
        import pandas as pd
    except ImportError as exc:
        raise ImportError(
            "pandas is required for to_dataframe(). "
            "Install it with: pip install pandas"
        ) from exc

    if not records:
        return pd.DataFrame()

    rows = [r.to_dict() if hasattr(r, "to_dict") else r for r in records]

    if mode == "records":
        return _records_to_df(rows, pd)

    if mode == "items":
        return _items_to_df(rows, items_field, pd)

    raise ValueError(f"Unknown mode {mode!r}. Use 'records' or 'items'.")


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _records_to_df(rows: list[dict], pd):
    """One row per record.  Nested objects are JSON-serialised into string columns."""
    flat_rows = [_flatten_record(row) for row in rows]
    return pd.DataFrame(flat_rows)


def _items_to_df(rows: list[dict], items_field: str, pd):
    """One row per line item, with parent fields repeated."""
    expanded = []
    for row in rows:
        parent = {k: v for k, v in _flatten_record(row).items() if k != items_field}
        items = row.get(items_field) or []
        if not items:
            # Keep the order row even if it has no items
            expanded.append(parent)
            continue
        for item in items:
            item_dict = item if isinstance(item, dict) else {}
            expanded.append({**parent, **{f"item_{k}": v for k, v in item_dict.items()}})
    return pd.DataFrame(expanded)


def _flatten_record(row: dict) -> dict:
    """Serialise nested dicts/lists to JSON strings so every value is scalar."""
    out = {}
    for key, value in row.items():
        if isinstance(value, dict):
            out[key] = json.dumps(value, default=str)
        elif isinstance(value, list):
            out[key] = json.dumps(value, default=str)
        else:
            out[key] = value
    return out
