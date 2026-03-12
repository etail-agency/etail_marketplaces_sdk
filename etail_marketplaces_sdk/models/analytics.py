"""Canonical Analytics / Performance reporting model."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class AnalyticsMetric(str, Enum):
    IMPRESSIONS = "impressions"
    CLICKS = "clicks"
    ORDERS = "orders"
    REVENUE = "revenue"
    UNITS_SOLD = "units_sold"
    CONVERSION_RATE = "conversion_rate"
    AVERAGE_ORDER_VALUE = "average_order_value"
    RETURN_RATE = "return_rate"
    CANCELLATION_RATE = "cancellation_rate"


@dataclass
class AnalyticsRecord:
    """
    A single analytics data point for a given date, platform, and optionally SKU.

    Designed to be flexible — populate only the metrics available from each
    platform. Use `metrics` dict for platform-specific values beyond the
    typed fields.
    """

    report_date: date
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    sku: Optional[str] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    orders: Optional[int] = None
    units_sold: Optional[int] = None
    revenue: Optional[Decimal] = None
    currency: str = "EUR"
    conversion_rate: Optional[Decimal] = None
    average_order_value: Optional[Decimal] = None
    return_rate: Optional[Decimal] = None
    cancellation_rate: Optional[Decimal] = None
    metrics: dict = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "report_date": self.report_date.isoformat(),
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "sku": self.sku,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "orders": self.orders,
            "units_sold": self.units_sold,
            "revenue": str(self.revenue) if self.revenue else None,
            "currency": self.currency,
            "conversion_rate": str(self.conversion_rate) if self.conversion_rate else None,
            "average_order_value": str(self.average_order_value) if self.average_order_value else None,
            "return_rate": str(self.return_rate) if self.return_rate else None,
            "cancellation_rate": str(self.cancellation_rate) if self.cancellation_rate else None,
            "metrics": self.metrics,
        }
