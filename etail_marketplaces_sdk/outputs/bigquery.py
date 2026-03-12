"""
BigQuerySinkConnector

Writes canonical SDK models to Google BigQuery.

Usage:
    from google.cloud import bigquery
    from etail_marketplaces_sdk.outputs.bigquery import BigQuerySinkConnector

    bq_client = bigquery.Client(project="my-gcp-project")
    sink = BigQuerySinkConnector(
        client=bq_client,
        dataset_id="ecommerce",
    )
    result = sink.write_orders(orders)

Requires:
    pip install google-cloud-bigquery
    (or uv add google-cloud-bigquery, or install etail-marketplaces-sdk[bigquery])

Table IDs follow the pattern: `{project}.{dataset_id}.{table_name}`.
Tables must exist; the connector does not create them automatically.
Use INSERT or MERGE depending on whether the table has a unique key.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

from etail_marketplaces_sdk.outputs.base import BaseSinkConnector, WriteResult

logger = logging.getLogger(__name__)

BATCH_SIZE = 500  # BigQuery streaming insert supports larger batches


class BigQuerySinkConnector(BaseSinkConnector):
    """
    BigQuery sink using the google-cloud-bigquery client.

    Uses streaming inserts (insert_rows_json) for low-latency pipelines.
    Switch to load_table_from_json for high-volume batch loads.
    """

    TABLE_MAP = {
        "orders": "order",
        "invoices": "invoice",
        "stock": "stock_level",
        "catalogue": "product",
        "shipments": "shipment",
        "returns": "return",
        "analytics": "analytics_record",
        "ads": "ad_record",
        "settlements": "settlement",
        "reviews": "review",
    }

    def __init__(self, client: Any, dataset_id: str, project_id: Optional[str] = None) -> None:
        self.client = client
        self.dataset_id = dataset_id
        self.project_id = project_id or client.project

    def _table_ref(self, table_name: str) -> str:
        return f"{self.project_id}.{self.dataset_id}.{table_name}"

    def _stream_rows(self, table_name: str, rows: list[dict]) -> WriteResult:
        table_ref = self._table_ref(table_name)
        inserted = 0
        failed = 0

        for i in range(0, len(rows), BATCH_SIZE):
            batch = rows[i : i + BATCH_SIZE]
            try:
                errors = self.client.insert_rows_json(table_ref, batch)
                if errors:
                    failed += len(batch)
                    logger.error(
                        "BigQuery insert errors on table %s at index %d: %s",
                        table_ref,
                        i,
                        errors,
                    )
                else:
                    inserted += len(batch)
            except Exception as exc:
                failed += len(batch)
                logger.error(
                    "BigQuery insert failed on table %s at index %d: %s",
                    table_ref,
                    i,
                    exc,
                )

        return WriteResult(inserted=inserted, failed=failed)

    def write_orders(self, orders: list) -> WriteResult:
        rows = [o.to_dict() for o in orders]
        return self._stream_rows(self.TABLE_MAP["orders"], rows)

    def write_invoices(self, invoices: list) -> WriteResult:
        rows = [inv.to_dict() for inv in invoices if inv is not None]
        return self._stream_rows(self.TABLE_MAP["invoices"], rows)

    def write_stock(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._stream_rows(self.TABLE_MAP["stock"], rows)

    def write_catalogue(self, products: list) -> WriteResult:
        rows = [p.to_dict() for p in products]
        return self._stream_rows(self.TABLE_MAP["catalogue"], rows)

    def write_shipments(self, shipments: list) -> WriteResult:
        rows = [s.to_dict() for s in shipments]
        return self._stream_rows(self.TABLE_MAP["shipments"], rows)

    def write_returns(self, returns: list) -> WriteResult:
        rows = [r.to_dict() for r in returns]
        return self._stream_rows(self.TABLE_MAP["returns"], rows)

    def write_analytics(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._stream_rows(self.TABLE_MAP["analytics"], rows)

    def write_ads(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._stream_rows(self.TABLE_MAP["ads"], rows)

    def write_settlements(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._stream_rows(self.TABLE_MAP["settlements"], rows)

    def write_reviews(self, records: list) -> WriteResult:
        rows = [r.to_dict() for r in records]
        return self._stream_rows(self.TABLE_MAP["reviews"], rows)
