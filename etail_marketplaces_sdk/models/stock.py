"""Canonical Stock / Inventory level model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class StockLevel:
    """
    Stock level for a single SKU on a given platform.

    `platform_id` is the internal product ID on the aggregator/marketplace side.
    `sku` is the merchant's own reference.
    """

    sku: str
    quantity_available: int
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    platform_id: Optional[str] = None
    quantity_reserved: int = 0
    warehouse_id: Optional[str] = None
    last_updated: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    @property
    def quantity_total(self) -> int:
        return self.quantity_available + self.quantity_reserved

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "platform_id": self.platform_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "quantity_available": self.quantity_available,
            "quantity_reserved": self.quantity_reserved,
            "quantity_total": self.quantity_total,
            "warehouse_id": self.warehouse_id,
            "last_updated": self.last_updated.isoformat() if self.last_updated else None,
        }
