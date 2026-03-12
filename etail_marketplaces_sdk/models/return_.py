"""Canonical Return / Refund model."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class ReturnStatus(str, Enum):
    REQUESTED = "requested"
    APPROVED = "approved"
    RECEIVED = "received"
    REFUNDED = "refunded"
    REJECTED = "rejected"
    UNKNOWN = "unknown"


class ReturnReason(str, Enum):
    DEFECTIVE = "defective"
    NOT_AS_DESCRIBED = "not_as_described"
    WRONG_ITEM = "wrong_item"
    CHANGED_MIND = "changed_mind"
    LATE_DELIVERY = "late_delivery"
    DAMAGED = "damaged"
    OTHER = "other"


@dataclass
class ReturnLine:
    sku: str
    quantity: int
    reason: str = ReturnReason.OTHER
    refund_amount: Optional[Decimal] = None
    platform_product_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "quantity": self.quantity,
            "reason": self.reason,
            "refund_amount": str(self.refund_amount) if self.refund_amount else None,
            "platform_product_id": self.platform_product_id,
        }


@dataclass
class Return:
    return_id: str
    order_id: str
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    status: str = ReturnStatus.UNKNOWN
    total_refund_amount: Optional[Decimal] = None
    currency: str = "EUR"
    requested_at: Optional[datetime] = None
    processed_at: Optional[datetime] = None
    lines: list[ReturnLine] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "return_id": self.return_id,
            "order_id": self.order_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "status": self.status,
            "total_refund_amount": str(self.total_refund_amount) if self.total_refund_amount else None,
            "currency": self.currency,
            "requested_at": self.requested_at.isoformat() if self.requested_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "lines": [line.to_dict() for line in self.lines],
        }
