"""
ManoMano mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the ManoMano OpenAPI spec changes.
Cross-reference with: specs/marketplaces/manomano/openapi.json

ManoMano Partner API reference: https://developer.manomano.com/
"""

from __future__ import annotations

import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from etail_marketplaces_sdk.core.decimal_utils import optional_decimal
from etail_marketplaces_sdk.models.address import Address
from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem

# ManoMano statuses that indicate the order has been fulfilled
SHIPPED_STATUSES = {"SHIPPED", "DELIVERED", "COMPLETED"}


def _manomano_marketplace_name(raw: dict[str, Any]) -> Optional[str]:
    """Human-readable channel / marketplace label when present in the payload."""
    for key in ("marketplace_name", "channel_name", "sales_channel", "channel_label"):
        v = raw.get(key)
        if v:
            return str(v)
    ch = raw.get("channel")
    if isinstance(ch, dict):
        return ch.get("name") or ch.get("label") or ch.get("code")
    return None


def _manomano_order_commission(raw: dict[str, Any]) -> Optional[Decimal]:
    """Order-level ``commission`` or sum of ``products[].commission`` / ``commission_amount``."""
    top = optional_decimal(raw.get("commission"))
    if top is not None:
        return top
    total = Decimal("0")
    found = False
    for p in raw.get("products", []) or []:
        for key in ("commission", "commission_amount", "marketplace_commission"):
            c = optional_decimal(p.get(key))
            if c is not None:
                total += c
                found = True
                break
    return total if found else None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _map_address(data: dict[str, Any]) -> Address:
    return Address(
        name=f"{data.get('firstname', '')} {data.get('lastname', '')}".strip(),
        address_line1=data.get("address_line1", ""),
        address_line2=data.get("address_line2"),
        postal_code=data.get("zipcode", ""),
        city=data.get("city", ""),
        country=data.get("country", ""),
        phone=data.get("phone"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    return InvoiceAddress(
        name=f"{data.get('firstname', '')} {data.get('lastname', '')}".strip(),
        address=data.get("address_line1", ""),
        postal_code=data.get("zipcode", ""),
        city=data.get("city", ""),
        country=data.get("country", ""),
        phone=data.get("phone"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
) -> Order:
    created_at = _parse_dt(raw.get("created_at")) or datetime.now()
    updated_at = _parse_dt(raw.get("status_updated_at") or raw.get("created_at"))

    total_price = raw.get("total_price", {})
    shipping_price = raw.get("shipping_price", {})

    billing = raw.get("addresses", {}).get("billing", {})
    shipping = raw.get("addresses", {}).get("shipping", {})

    items = _map_order_items(raw)

    return Order(
        aggregator_order_id=raw.get("order_reference", ""),
        marketplace_order_id=raw.get("order_reference", ""),
        aggregator_id=0,
        marketplace_id=marketplace_id,
        brand_id=brand.id,
        order_date=created_at,
        status=raw.get("status", ""),
        eur_amount_excl_vat=Decimal("0"),
        eur_amount_incl_vat=Decimal(str(total_price.get("amount", "0"))),
        eur_shipping_fee_excl_vat=Decimal("0"),
        eur_shipping_fee_incl_vat=Decimal(str(shipping_price.get("amount", "0"))),
        original_currency=total_price.get("currency", "EUR"),
        original_amount=Decimal(str(total_price.get("amount", "0"))),
        original_shipping_fee=Decimal(str(shipping_price.get("amount", "0"))),
        items=items,
        billing_address=_map_address(billing) if billing else None,
        shipping_address=_map_address(shipping) if shipping and shipping != billing else None,
        created_date=created_at,
        updated_date=updated_at,
        marketplace_name=_manomano_marketplace_name(raw),
        commission=_manomano_order_commission(raw),
        raw=raw,
    )


def _map_order_items(raw: dict[str, Any]) -> list[OrderItem]:
    items = []
    for p in raw.get("products", []):
        quantity = int(p.get("quantity", 0))
        unit_excl = Decimal(str(p.get("price_excluding_vat", {}).get("amount", "0")))
        vat_rate = Decimal(str(p.get("vat_rate", "20.00")))
        unit_incl = unit_excl * (1 + vat_rate / 100)
        items.append(
            OrderItem(
                reference=p.get("seller_sku", ""),
                name=p.get("title", ""),
                quantity=quantity,
                unit_price_excl_vat=unit_excl,
                unit_price_incl_vat=unit_incl,
                vat_rate=vat_rate,
                total_price_excl_vat=unit_excl * quantity,
                total_price_incl_vat=unit_incl * quantity,
                sku=p.get("seller_sku", ""),
            )
        )
    return items


def map_invoice(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    if raw.get("status") not in SHIPPED_STATUSES:
        return None

    billing = raw.get("addresses", {}).get("billing", {})
    shipping = raw.get("addresses", {}).get("shipping", {})

    billing_address = _map_invoice_address(billing)
    shipping_address = _map_invoice_address(shipping) if shipping and shipping != billing else None

    items, subtotal, _ = _map_invoice_items(raw)

    shipping_excl_vat = raw.get("shipping_price_excluding_vat", {})
    shipping_cost = Decimal(str(shipping_excl_vat.get("amount", "0")))

    total_amount = Decimal(str(raw.get("total_price", {}).get("amount", "0")))
    invoice_number = str(random.randint(3_500_000, 4_999_999))

    return Invoice(
        invoice_number=invoice_number,
        order_reference=raw.get("order_reference", ""),
        order_date=_parse_dt(raw.get("created_at")) or datetime.now(),
        brand_id=brand.id,
        aggregator_id=0,
        marketplace_id=marketplace_id,
        company_info=brand.company_info,
        logo_path=brand.logo_url,
        footer_text=brand.invoice_footer_text,
        brand_initials=brand.initials,
        billing_address=billing_address,
        shipping_address=shipping_address,
        subtotal=subtotal,
        vat_rate=tax_rate,
        total_amount=total_amount,
        items=items,
        shipping_cost=shipping_cost,
        payment_method="ManoMano Platform",
        invoice_status="paid" if raw.get("status") == "DELIVERED" else "pending",
        currency=raw.get("total_price", {}).get("currency", "EUR"),
        payment_plan_commission=Decimal("0"),
    )


def _map_invoice_items(raw: dict[str, Any]) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for p in raw.get("products", []):
        quantity = int(p.get("quantity", 0))
        unit_excl = Decimal(str(p.get("price_excluding_vat", {}).get("amount", "0")))
        vat_rate = Decimal(str(p.get("vat_rate", "20.00")))
        total_price = unit_excl * quantity
        tax_amount = total_price * vat_rate / 100

        items.append(
            InvoiceItem(
                reference=p.get("seller_sku", ""),
                name=p.get("title", ""),
                quantity=quantity,
                unit_price=unit_excl,
                total_price=total_price,
                tax_rate=vat_rate,
                sku=p.get("seller_sku", ""),
            )
        )
        subtotal += total_price
        total_tax += tax_amount

    return items, subtotal, total_tax
