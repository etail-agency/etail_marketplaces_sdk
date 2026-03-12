"""
PostgresSinkConnector

Writes canonical SDK models to a PostgreSQL database via SQLAlchemy.
Migrated and generalised from:
    backend/app/services/order_integration/repositories/order_repository.py

Connection object must be a SQLAlchemy Connection or Engine.

Usage:
    from sqlalchemy import create_engine
    from etail_marketplaces_sdk.outputs.postgres import PostgresSinkConnector

    engine = create_engine("postgresql+psycopg2://...")
    with engine.connect() as conn:
        sink = PostgresSinkConnector(connection=conn)
        result = sink.write_orders(orders)
"""

from __future__ import annotations

import json
import logging
from typing import Any

from sqlalchemy import text

from etail_marketplaces_sdk.outputs.base import BaseSinkConnector, WriteResult

logger = logging.getLogger(__name__)

BATCH_SIZE = 20


def _execute_batch(conn: Any, query: str, values: list[dict]) -> tuple[int, int]:
    """Execute a batch upsert. Returns (successful, failed)."""
    successful = 0
    failed = 0
    for i in range(0, len(values), BATCH_SIZE):
        batch = values[i : i + BATCH_SIZE]
        try:
            with conn.begin_nested():
                conn.execute(text(query), batch)
            successful += len(batch)
        except Exception as exc:
            failed += len(batch)
            logger.error("Batch insert failed at index %d: %s", i, exc)
    return successful, failed


class PostgresSinkConnector(BaseSinkConnector):
    """
    PostgreSQL sink using SQLAlchemy.

    Pass either an Engine or a Connection. For long-running pipelines,
    pass a Connection so you control the transaction boundary.
    """

    def __init__(self, connection: Any) -> None:
        self.db = connection

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def write_orders(self, orders: list) -> WriteResult:
        if not orders:
            return WriteResult()

        valid_marketplace_ids = self._get_valid_marketplace_ids()
        valid, skipped = [], 0

        for order in orders:
            if order.marketplace_id not in valid_marketplace_ids:
                skipped += 1
                logger.warning(
                    "Skipping order %s — invalid marketplace_id %s",
                    order.aggregator_order_id,
                    order.marketplace_id,
                )
                continue
            valid.append(order)

        if not valid:
            return WriteResult(skipped=skipped)

        query = """
            INSERT INTO "order" (
                brand_id, aggregator_id, marketplace_id,
                aggregator_order_id, marketplace_order_id,
                order_date, eur_amount_val, original_amount_val,
                vat_rate, eur_shipping_fee_val, original_shipping_fee_val,
                shipping_vat_rate, original_currency,
                oms, oms_order_id, status,
                created_date, updated_date, raw_order_data
            )
            VALUES (
                :brand_id, :aggregator_id, :marketplace_id,
                :aggregator_order_id, :marketplace_order_id,
                :order_date, :eur_amount_incl_vat, :original_amount,
                :vat_rate, :eur_shipping_fee_incl_vat, :original_shipping_fee,
                :shipping_vat_rate, :original_currency,
                :oms, :oms_order_id, :status,
                :created_date, :updated_date, :raw_order_data
            )
            ON CONFLICT (marketplace_id, aggregator_order_id)
            DO UPDATE SET
                brand_id = EXCLUDED.brand_id,
                aggregator_id = EXCLUDED.aggregator_id,
                marketplace_order_id = EXCLUDED.marketplace_order_id,
                order_date = EXCLUDED.order_date,
                eur_amount_val = EXCLUDED.eur_amount_val,
                original_amount_val = EXCLUDED.original_amount_val,
                vat_rate = EXCLUDED.vat_rate,
                eur_shipping_fee_val = EXCLUDED.eur_shipping_fee_val,
                original_shipping_fee_val = EXCLUDED.original_shipping_fee_val,
                shipping_vat_rate = EXCLUDED.shipping_vat_rate,
                original_currency = EXCLUDED.original_currency,
                oms = EXCLUDED.oms,
                oms_order_id = EXCLUDED.oms_order_id,
                status = EXCLUDED.status,
                updated_date = EXCLUDED.updated_date,
                raw_order_data = EXCLUDED.raw_order_data
        """

        values = []
        for o in valid:
            d = o.to_dict()
            d["raw_order_data"] = json.dumps(o.raw) if o.raw else None
            values.append(d)

        ok, failed = _execute_batch(self.db, query, values)
        return WriteResult(inserted=ok, skipped=skipped, failed=failed)

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def write_invoices(self, invoices: list) -> WriteResult:
        valid = [inv for inv in invoices if inv is not None]
        if not valid:
            return WriteResult()

        query = """
            INSERT INTO invoice (
                invoice_number, order_reference, order_date, invoice_date,
                company_info, logo_path, footer_text, brand_initials,
                billing_address, shipping_address,
                subtotal, vat_rate, total_amount, items,
                payment_method, invoice_status, shipping_cost,
                payment_plan_commission, notes, currency
            )
            VALUES (
                :invoice_number, :order_reference, :order_date, :invoice_date,
                :company_info, :logo_path, :footer_text, :brand_initials,
                :billing_address, :shipping_address,
                :subtotal, :vat_rate, :total_amount, :items,
                :payment_method, :invoice_status, :shipping_cost,
                :payment_plan_commission, :notes, :currency
            )
            ON CONFLICT (invoice_number)
            DO UPDATE SET
                order_reference = EXCLUDED.order_reference,
                order_date = EXCLUDED.order_date,
                invoice_date = EXCLUDED.invoice_date,
                company_info = EXCLUDED.company_info,
                logo_path = EXCLUDED.logo_path,
                footer_text = EXCLUDED.footer_text,
                brand_initials = EXCLUDED.brand_initials,
                billing_address = EXCLUDED.billing_address,
                shipping_address = EXCLUDED.shipping_address,
                subtotal = EXCLUDED.subtotal,
                vat_rate = EXCLUDED.vat_rate,
                total_amount = EXCLUDED.total_amount,
                items = EXCLUDED.items,
                payment_method = EXCLUDED.payment_method,
                invoice_status = EXCLUDED.invoice_status,
                shipping_cost = EXCLUDED.shipping_cost,
                payment_plan_commission = EXCLUDED.payment_plan_commission,
                notes = EXCLUDED.notes,
                currency = EXCLUDED.currency
        """

        values = [inv.to_dict() for inv in valid]
        ok, failed = _execute_batch(self.db, query, values)
        return WriteResult(inserted=ok, failed=failed)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get_valid_marketplace_ids(self) -> set[int]:
        result = self.db.execute(text("SELECT id FROM marketplace"))
        return {row[0] for row in result}
