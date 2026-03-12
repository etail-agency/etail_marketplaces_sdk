"""Canonical Order model."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional

from etail_marketplaces_sdk.models.address import Address


class OrderStatus(str, Enum):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    RETURNED = "returned"
    UNKNOWN = "unknown"


@dataclass
class OrderItem:
    reference: str
    name: str
    quantity: int
    unit_price_excl_vat: Decimal
    unit_price_incl_vat: Decimal
    vat_rate: Decimal
    total_price_excl_vat: Decimal
    total_price_incl_vat: Decimal
    sku: Optional[str] = None
    ean: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "reference": self.reference,
            "name": self.name,
            "quantity": self.quantity,
            "unit_price_excl_vat": str(self.unit_price_excl_vat),
            "unit_price_incl_vat": str(self.unit_price_incl_vat),
            "vat_rate": str(self.vat_rate),
            "total_price_excl_vat": str(self.total_price_excl_vat),
            "total_price_incl_vat": str(self.total_price_incl_vat),
            "sku": self.sku,
            "ean": self.ean,
        }


@dataclass
class Order:
    """
    Canonical order model.

    `raw` always holds the unmodified platform payload for traceability and
    to allow downstream consumers to access fields the SDK doesn't map.
    """

    aggregator_order_id: str
    marketplace_order_id: str
    aggregator_id: int
    marketplace_id: int
    brand_id: int
    order_date: datetime
    status: str
    eur_amount_excl_vat: Decimal
    eur_amount_incl_vat: Decimal
    eur_shipping_fee_excl_vat: Decimal
    eur_shipping_fee_incl_vat: Decimal
    original_currency: str
    original_amount: Decimal
    original_shipping_fee: Decimal
    items: list[OrderItem] = field(default_factory=list)
    billing_address: Optional[Address] = None
    shipping_address: Optional[Address] = None
    vat_rate: Optional[Decimal] = None
    shipping_vat_rate: Optional[Decimal] = None
    payment_method: Optional[str] = None
    oms: Optional[str] = None
    oms_order_id: Optional[str] = None
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None
    id: Optional[int] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "brand_id": self.brand_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "aggregator_order_id": self.aggregator_order_id,
            "marketplace_order_id": self.marketplace_order_id,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "status": self.status,
            "eur_amount_excl_vat": str(self.eur_amount_excl_vat),
            "eur_amount_incl_vat": str(self.eur_amount_incl_vat),
            "eur_shipping_fee_excl_vat": str(self.eur_shipping_fee_excl_vat),
            "eur_shipping_fee_incl_vat": str(self.eur_shipping_fee_incl_vat),
            "original_currency": self.original_currency,
            "original_amount": str(self.original_amount),
            "original_shipping_fee": str(self.original_shipping_fee),
            "vat_rate": str(self.vat_rate) if self.vat_rate is not None else None,
            "shipping_vat_rate": str(self.shipping_vat_rate) if self.shipping_vat_rate is not None else None,
            "payment_method": self.payment_method,
            "oms": self.oms,
            "oms_order_id": self.oms_order_id,
            "billing_address": self.billing_address.to_dict() if self.billing_address else None,
            "shipping_address": self.shipping_address.to_dict() if self.shipping_address else None,
            "items": [i.to_dict() for i in self.items],
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }
