"""
BaseSinkConnector — abstract interface for all output destinations.

Every concrete sink (Postgres, Supabase, BigQuery …) implements this interface
so that pipeline code stays portable across destinations.

Usage pattern:
    from etail_marketplaces_sdk.outputs.postgres import PostgresSinkConnector

    sink = PostgresSinkConnector(connection=engine)
    result = sink.write_orders(orders)
    print(result.inserted, result.updated, result.failed)
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class WriteResult:
    """Outcome of a single write_* call."""

    inserted: int = 0
    updated: int = 0
    skipped: int = 0
    failed: int = 0

    @property
    def total_attempted(self) -> int:
        return self.inserted + self.updated + self.skipped + self.failed

    def __add__(self, other: "WriteResult") -> "WriteResult":
        return WriteResult(
            inserted=self.inserted + other.inserted,
            updated=self.updated + other.updated,
            skipped=self.skipped + other.skipped,
            failed=self.failed + other.failed,
        )


class BaseSinkConnector(ABC):
    """
    Abstract sink connector.

    Concrete implementations must override the streams they support.
    All methods default to raising NotImplementedError.
    """

    def write_orders(self, orders: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_orders")

    def write_invoices(self, invoices: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_invoices")

    def write_stock(self, records: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_stock")

    def write_catalogue(self, products: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_catalogue")

    def write_shipments(self, shipments: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_shipments")

    def write_returns(self, returns: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_returns")

    def write_analytics(self, records: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_analytics")

    def write_ads(self, records: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_ads")

    def write_settlements(self, records: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_settlements")

    def write_reviews(self, records: list) -> WriteResult:
        raise NotImplementedError(f"{type(self).__name__} does not support write_reviews")
