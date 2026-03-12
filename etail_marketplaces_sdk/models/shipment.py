"""Canonical Shipment / Tracking model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ShipmentStatus(str, Enum):
    PENDING = "pending"
    IN_TRANSIT = "in_transit"
    OUT_FOR_DELIVERY = "out_for_delivery"
    DELIVERED = "delivered"
    FAILED = "failed"
    RETURNED = "returned"
    UNKNOWN = "unknown"


@dataclass
class ShipmentLine:
    sku: str
    quantity: int
    platform_product_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "quantity": self.quantity,
            "platform_product_id": self.platform_product_id,
        }


@dataclass
class Shipment:
    shipment_id: str
    order_id: str
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    carrier: Optional[str] = None
    tracking_number: Optional[str] = None
    tracking_url: Optional[str] = None
    status: str = ShipmentStatus.UNKNOWN
    shipped_at: Optional[datetime] = None
    estimated_delivery: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    lines: list[ShipmentLine] = field(default_factory=list)
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "shipment_id": self.shipment_id,
            "order_id": self.order_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "carrier": self.carrier,
            "tracking_number": self.tracking_number,
            "tracking_url": self.tracking_url,
            "status": self.status,
            "shipped_at": self.shipped_at.isoformat() if self.shipped_at else None,
            "estimated_delivery": self.estimated_delivery.isoformat() if self.estimated_delivery else None,
            "delivered_at": self.delivered_at.isoformat() if self.delivered_at else None,
            "lines": [l.to_dict() for l in self.lines],
        }
