"""
Canonical Invoice model.

Migrated and extended from backend/app/services/order_integration/models/invoice.py.
PDF generation is intentionally kept out of this model — it belongs to a
separate rendering layer so the model stays a plain data container.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Optional


class InvoiceStatus(str, Enum):
    PENDING = "pending"
    PAID = "paid"
    CANCELLED = "cancelled"
    REFUNDED = "refunded"


@dataclass
class InvoiceAddress:
    """Billing or shipping address on an invoice."""

    name: str
    address: str
    postal_code: str
    city: str
    country: str
    phone: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address": self.address,
            "postal_code": self.postal_code,
            "city": self.city,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvoiceAddress":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class InvoiceItem:
    reference: str
    name: str
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    tax_rate: Decimal
    sku: str

    def to_dict(self) -> dict:
        return {
            "reference": self.reference,
            "name": self.name,
            "quantity": self.quantity,
            "unit_price": float(self.unit_price),
            "total_price": float(self.total_price),
            "tax_rate": float(self.tax_rate),
            "sku": self.sku,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "InvoiceItem":
        return cls(
            reference=data["reference"],
            name=data["name"],
            quantity=int(data["quantity"]),
            unit_price=Decimal(str(data["unit_price"])),
            total_price=Decimal(str(data["total_price"])),
            tax_rate=Decimal(str(data["tax_rate"])),
            sku=data["sku"],
        )


@dataclass
class Invoice:
    invoice_number: str
    order_reference: str
    order_date: datetime
    brand_id: int
    aggregator_id: int
    marketplace_id: int
    company_info: str
    logo_path: str
    footer_text: str
    brand_initials: str
    billing_address: InvoiceAddress
    subtotal: Decimal
    vat_rate: Decimal
    total_amount: Decimal
    items: list[InvoiceItem] = field(default_factory=list)
    shipping_address: Optional[InvoiceAddress] = None
    invoice_date: datetime = field(default_factory=datetime.now)
    payment_method: Optional[str] = None
    invoice_status: str = InvoiceStatus.PENDING
    shipping_cost: Decimal = field(default_factory=lambda: Decimal("0"))
    payment_plan_commission: Decimal = field(default_factory=lambda: Decimal("0"))
    notes: Optional[str] = None
    currency: str = "EUR"

    @property
    def vat_amount(self) -> Decimal:
        return (self.total_amount - self.subtotal).quantize(Decimal("0.01"))

    @property
    def invoice_number_str(self) -> str:
        try:
            shortened = int(self.invoice_number) % 1000
            return f"{self.brand_initials}-{shortened:03d}-{self.order_date.strftime('%d%m%Y')}"
        except (ValueError, TypeError):
            return f"{self.brand_initials}-{self.invoice_number}-{self.order_date.strftime('%d%m%Y')}"

    def to_dict(self) -> dict:
        import json

        return {
            "invoice_number": self.invoice_number,
            "order_reference": self.order_reference,
            "order_date": self.order_date.isoformat() if self.order_date else None,
            "invoice_date": self.invoice_date.isoformat() if self.invoice_date else None,
            "brand_id": self.brand_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "company_info": self.company_info,
            "logo_path": self.logo_path,
            "footer_text": self.footer_text,
            "brand_initials": self.brand_initials,
            "billing_address": json.dumps(self.billing_address.to_dict()) if self.billing_address else None,
            "shipping_address": json.dumps(self.shipping_address.to_dict()) if self.shipping_address else None,
            "currency": self.currency,
            "subtotal": str(self.subtotal),
            "vat_rate": str(self.vat_rate),
            "vat_amount": str(self.vat_amount),
            "total_amount": str(self.total_amount),
            "shipping_cost": str(self.shipping_cost),
            "payment_method": self.payment_method,
            "invoice_status": self.invoice_status,
            "items": json.dumps([item.to_dict() for item in self.items]),
            "notes": self.notes,
            "payment_plan_commission": str(self.payment_plan_commission),
        }
