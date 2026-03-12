"""
Mirakl mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the Mirakl OpenAPI spec changes.
Cross-reference with: specs/marketplaces/mirakl/openapi.json

Mirakl Operator API reference: https://help.mirakl.net/help/api-doc/operator/
Each Mirakl operator (Galeries Lafayette, Leroy Merlin, etc.) may have
customised field names — add operator-specific constants here.

NOTE: This is a scaffold. Fields are based on the standard Mirakl OR11
      Orders API response structure. Verify against the target operator's
      actual spec before using in production.
"""

from __future__ import annotations

import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from etail_marketplaces_sdk.models.address import Address
from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem
from etail_marketplaces_sdk.models.product import Product, ProductAttribute
from etail_marketplaces_sdk.models.stock import StockLevel

SHIPPED_STATUSES = {"SHIPPING", "SHIPPED", "TO_COLLECT", "RECEIVED", "CLOSED"}


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _map_address(data: dict[str, Any]) -> Address:
    return Address(
        name=f"{data.get('firstname', '')} {data.get('lastname', '')}".strip(),
        address_line1=data.get("street_1", ""),
        address_line2=data.get("street_2"),
        postal_code=data.get("zip_code", ""),
        city=data.get("city", ""),
        country=data.get("country", {}).get("iso_code", "") if isinstance(data.get("country"), dict) else data.get("country", ""),
        phone=data.get("phone") or data.get("phone_secondary"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    return InvoiceAddress(
        name=f"{data.get('firstname', '')} {data.get('lastname', '')}".strip(),
        address=data.get("street_1", ""),
        postal_code=data.get("zip_code", ""),
        city=data.get("city", ""),
        country=data.get("country", {}).get("iso_code", "") if isinstance(data.get("country"), dict) else data.get("country", ""),
        phone=data.get("phone") or data.get("phone_secondary"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
) -> Order:
    created_at = _parse_dt(raw.get("created_date")) or datetime.now()
    updated_at = _parse_dt(raw.get("last_updated_date"))

    currency = raw.get("currency_iso_code", "EUR")
    total_price = Decimal(str(raw.get("total_price", "0")))
    total_shipping = Decimal(str(raw.get("total_shipping_price", "0")))

    billing = raw.get("customer", {}).get("billing_address", {})
    shipping = raw.get("customer", {}).get("shipping_address", {})

    items = _map_order_items(raw)

    return Order(
        aggregator_order_id=raw.get("order_id", ""),
        marketplace_order_id=raw.get("order_id", ""),
        aggregator_id=0,
        marketplace_id=marketplace_id,
        brand_id=brand.id,
        order_date=created_at,
        status=raw.get("order_state", ""),
        eur_amount_excl_vat=Decimal("0"),
        eur_amount_incl_vat=total_price,
        eur_shipping_fee_excl_vat=Decimal("0"),
        eur_shipping_fee_incl_vat=total_shipping,
        original_currency=currency,
        original_amount=total_price,
        original_shipping_fee=total_shipping,
        items=items,
        billing_address=_map_address(billing) if billing else None,
        shipping_address=_map_address(shipping) if shipping else None,
        created_date=created_at,
        updated_date=updated_at,
        raw=raw,
    )


def _map_order_items(raw: dict[str, Any]) -> list[OrderItem]:
    items = []
    for line in raw.get("order_lines", []):
        quantity = int(line.get("quantity", 0))
        unit_incl = Decimal(str(line.get("unit_price", "0")))
        items.append(
            OrderItem(
                reference=line.get("offer_sku", ""),
                name=line.get("offer_title", ""),
                quantity=quantity,
                unit_price_excl_vat=Decimal("0"),
                unit_price_incl_vat=unit_incl,
                vat_rate=Decimal(str(line.get("taxes", [{}])[0].get("rate", "0") if line.get("taxes") else "0")),
                total_price_excl_vat=Decimal("0"),
                total_price_incl_vat=unit_incl * quantity,
                sku=line.get("offer_sku", ""),
            )
        )
    return items


def map_invoice(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    if raw.get("order_state") not in SHIPPED_STATUSES:
        return None

    billing = raw.get("customer", {}).get("billing_address", {})
    shipping = raw.get("customer", {}).get("shipping_address", {})

    items, subtotal, _ = _map_invoice_items(raw, tax_rate)
    total_amount = Decimal(str(raw.get("total_price", "0")))
    shipping_incl = Decimal(str(raw.get("total_shipping_price", "0")))
    shipping_excl = (shipping_incl * 100) / (100 + tax_rate)
    invoice_number = str(random.randint(3_500_000, 4_999_999))

    return Invoice(
        invoice_number=invoice_number,
        order_reference=raw.get("order_id", ""),
        order_date=_parse_dt(raw.get("created_date")) or datetime.now(),
        brand_id=brand.id,
        aggregator_id=0,
        marketplace_id=marketplace_id,
        company_info=brand.company_info,
        logo_path=brand.logo_url,
        footer_text=brand.invoice_footer_text,
        brand_initials=brand.initials,
        billing_address=_map_invoice_address(billing),
        shipping_address=_map_invoice_address(shipping) if shipping else None,
        subtotal=subtotal,
        vat_rate=tax_rate,
        total_amount=total_amount,
        items=items,
        shipping_cost=shipping_excl,
        payment_method="",
        invoice_status="paid" if raw.get("order_state") in {"RECEIVED", "CLOSED"} else "pending",
        currency=raw.get("currency_iso_code", "EUR"),
        payment_plan_commission=Decimal("0"),
    )


def _map_invoice_items(
    raw: dict[str, Any], tax_rate: Decimal
) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for line in raw.get("order_lines", []):
        quantity = int(line.get("quantity", 0))
        unit_incl = Decimal(str(line.get("unit_price", "0")))
        price_excl = (unit_incl * 100) / (100 + tax_rate)
        item_total = price_excl * quantity
        item_tax = item_total * (tax_rate / 100)

        items.append(
            InvoiceItem(
                reference=line.get("offer_sku", ""),
                name=line.get("offer_title", ""),
                quantity=quantity,
                unit_price=price_excl,
                total_price=item_total,
                tax_rate=tax_rate,
                sku=line.get("offer_sku", ""),
            )
        )
        subtotal += item_total
        total_tax += item_tax

    return items, subtotal, total_tax


def map_stock_level(raw: dict[str, Any], marketplace_id: int) -> StockLevel:
    """Map a Mirakl offer (OF21) response to a StockLevel."""
    return StockLevel(
        sku=raw.get("shop_sku", ""),
        platform_id=raw.get("offer_id"),
        marketplace_id=marketplace_id,
        quantity_available=int(raw.get("quantity", 0)),
    )


def map_product(raw: dict[str, Any], marketplace_id: int) -> Product:
    """Map a Mirakl product (P11) response to a canonical Product."""
    attrs = [
        ProductAttribute(name=a.get("code", ""), value=str(a.get("value", "")))
        for a in raw.get("attributes", [])
    ]
    return Product(
        sku=raw.get("shop_sku", ""),
        name=raw.get("title", ""),
        platform_id=raw.get("product_sku"),
        marketplace_id=marketplace_id,
        ean=raw.get("ean"),
        description=raw.get("description"),
        brand=raw.get("brand"),
        category=raw.get("category_code"),
        attributes=attrs,
        is_active=raw.get("state") == "ACTIVE",
        raw=raw,
    )
