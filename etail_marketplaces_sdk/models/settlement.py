"""Canonical Financial Settlement / Payout model."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class SettlementType(str, Enum):
    ORDER = "order"
    REFUND = "refund"
    FEE = "fee"
    ADJUSTMENT = "adjustment"
    ADVERTISING = "advertising"
    SHIPPING = "shipping"
    OTHER = "other"


@dataclass
class SettlementLine:
    type: str
    description: str
    amount: Decimal
    order_id: Optional[str] = None
    sku: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "type": self.type,
            "description": self.description,
            "amount": str(self.amount),
            "order_id": self.order_id,
            "sku": self.sku,
        }


@dataclass
class Settlement:
    """
    A financial settlement statement from a platform covering a date range.
    """

    settlement_id: str
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    total_amount: Optional[Decimal] = None
    currency: str = "EUR"
    lines: list[SettlementLine] = field(default_factory=list)
    paid_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    @property
    def computed_total(self) -> Decimal:
        return sum((line.amount for line in self.lines), Decimal("0"))

    def to_dict(self) -> dict:
        return {
            "settlement_id": self.settlement_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "period_start": self.period_start.isoformat() if self.period_start else None,
            "period_end": self.period_end.isoformat() if self.period_end else None,
            "total_amount": str(self.total_amount) if self.total_amount else None,
            "computed_total": str(self.computed_total),
            "currency": self.currency,
            "lines": [l.to_dict() for l in self.lines],
            "paid_at": self.paid_at.isoformat() if self.paid_at else None,
        }
