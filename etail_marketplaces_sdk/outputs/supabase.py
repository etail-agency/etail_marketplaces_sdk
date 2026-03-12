"""
SupabaseSinkConnector

Writes canonical SDK models to a Supabase project via the supabase-py client.

Usage:
    from supabase import create_client
    from etail_marketplaces_sdk.outputs.supabase import SupabaseSinkConnector

    supabase = create_client(url=SUPABASE_URL, key=SUPABASE_KEY)
    sink = SupabaseSinkConnector(client=supabase)
    result = sink.write_orders(orders)

Requires:
    pip install supabase
    (or uv add supabase, or install etail-marketplaces-sdk[supabase])
"""

from __future__ import annotations

import json
import logging
from typing import Any

from etail_marketplaces_sdk.outputs.base import BaseSinkConnector, WriteResult

logger = logging.getLogger(__name__)

BATCH_SIZE = 20


class SupabaseSinkConnector(BaseSinkConnector):
    """
    Supabase sink using the supabase-py client.

    Uses upsert on all tables so re-runs are idempotent.
    """

    def __init__(self, client: Any) -> None:
        self.client = client

    def _upsert_batch(self, table: str, rows: list[dict]) -> WriteResult:
        inserted = 0
        failed = 0
        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            try:
                self.client.table(table).upsert(batch).execute()
                inserted += len(batch)
            except Exception as exc:
                failed += len(batch)
                logger.error("Supabase upsert failed on table %s at index %d: %s", table, i, exc)
        return WriteResult(inserted=inserted, failed=failed)

    def write_orders(self, orders: list) -> WriteResult:
        rows = []
        for o in orders:
            d = o.to_dict()
            d["raw_order_data"] = json.dumps(o.raw) if o.raw else None
            rows.append(d)
        return self._upsert_batch("order", rows)

    def write_invoices(self, invoices: list) -> WriteResult:
        rows = [inv.to_dict() for inv in invoices if inv is not None]
        return self._upsert_batch("invoice", rows)

    def write_stock(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._upsert_batch("stock_level", rows)

    def write_catalogue(self, products: list) -> WriteResult:
        rows = [p.to_dict() for p in products]
        return self._upsert_batch("product", rows)

    def write_shipments(self, shipments: list) -> WriteResult:
        rows = [s.to_dict() for s in shipments]
        return self._upsert_batch("shipment", rows)

    def write_returns(self, returns: list) -> WriteResult:
        rows = [r.to_dict() for r in returns]
        return self._upsert_batch("return", rows)

    def write_analytics(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._upsert_batch("analytics_record", rows)

    def write_ads(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._upsert_batch("ad_record", rows)

    def write_settlements(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._upsert_batch("settlement", rows)

    def write_reviews(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._upsert_batch("review", rows)
