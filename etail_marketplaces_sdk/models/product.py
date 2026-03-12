"""Canonical Product / Catalogue model."""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Optional


@dataclass
class ProductImage:
    url: str
    position: int = 0
    alt_text: Optional[str] = None

    def to_dict(self) -> dict:
        return {"url": self.url, "position": self.position, "alt_text": self.alt_text}


@dataclass
class ProductAttribute:
    name: str
    value: str

    def to_dict(self) -> dict:
        return {"name": self.name, "value": self.value}


@dataclass
class Product:
    """
    A product listing on a platform.

    `sku` is the merchant's internal reference. `platform_id` is the
    platform's own identifier for the listing (may differ per channel).
    """

    sku: str
    name: str
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    platform_id: Optional[str] = None
    ean: Optional[str] = None
    description: Optional[str] = None
    price_excl_vat: Optional[Decimal] = None
    price_incl_vat: Optional[Decimal] = None
    vat_rate: Optional[Decimal] = None
    currency: str = "EUR"
    brand: Optional[str] = None
    category: Optional[str] = None
    images: list[ProductImage] = field(default_factory=list)
    attributes: list[ProductAttribute] = field(default_factory=list)
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "sku": self.sku,
            "name": self.name,
            "platform_id": self.platform_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "ean": self.ean,
            "description": self.description,
            "price_excl_vat": str(self.price_excl_vat) if self.price_excl_vat else None,
            "price_incl_vat": str(self.price_incl_vat) if self.price_incl_vat else None,
            "vat_rate": str(self.vat_rate) if self.vat_rate else None,
            "currency": self.currency,
            "brand": self.brand,
            "category": self.category,
            "images": [i.to_dict() for i in self.images],
            "attributes": [a.to_dict() for a in self.attributes],
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
