"""
Lengow mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the Lengow OpenAPI spec changes.
Cross-reference with: specs/aggregators/lengow/openapi.json

Lengow API reference: https://developers.lengow.com/
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

# ---------------------------------------------------------------------------
# Marketplace → internal ID + VAT rate mapping
# Sourced from backend/app/services/order_integration/mappings/marketplace_mappings.py
# ---------------------------------------------------------------------------
LENGOW_MARKETPLACE_MAPPING: dict[str, dict] = {
    "galeries_lafayette": {"marketplace_id": 590, "tva": Decimal("20")},
    "la_redoute": {"marketplace_id": 15, "tva": Decimal("20")},
    "veepee_fr": {"marketplace_id": 35639, "tva": Decimal("20")},
    "veepee_de": {"marketplace_id": 35640, "tva": Decimal("19")},
    "veepee_es": {"marketplace_id": 35641, "tva": Decimal("21")},
    "veepee_it": {"marketplace_id": 35642, "tva": Decimal("22")},
    "zalando_fr": {"marketplace_id": 589, "tva": Decimal("20")},
    "zalando_de": {"marketplace_id": 588, "tva": Decimal("19")},
    "zalando_es": {"marketplace_id": 591, "tva": Decimal("21")},
    "zalando_it": {"marketplace_id": 592, "tva": Decimal("22")},
    "zalando_nl": {"marketplace_id": 593, "tva": Decimal("21")},
    "amazon_fr": {"marketplace_id": 6, "tva": Decimal("20")},
    "cdiscount": {"marketplace_id": 111, "tva": Decimal("20")},
}


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _map_address(data: dict[str, Any]) -> Address:
    return Address(
        name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
        address_line1=data.get("first_line", ""),
        postal_code=data.get("zipcode", ""),
        city=data.get("city", ""),
        country=data.get("common_country_iso_a2", ""),
        phone=data.get("phone_mobile") or data.get("phone_office") or data.get("phone_home"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    return InvoiceAddress(
        name=f"{data.get('first_name', '')} {data.get('last_name', '')}".strip(),
        address=data.get("first_line", ""),
        postal_code=data.get("zipcode", ""),
        city=data.get("city", ""),
        country=data.get("common_country_iso_a2", ""),
        phone=data.get("phone_mobile") or data.get("phone_office") or data.get("phone_home"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
) -> Order:
    currency_info = raw.get("currency", {})
    order_date = _parse_dt(raw.get("marketplace_order_date")) or datetime.now()
    updated_at = _parse_dt(raw.get("updated_at"))

    billing = raw.get("billing_address", {})
    delivery = raw.get("packages", [{}])[0].get("delivery", {})

    total_incl = Decimal(str(raw.get("total_order", "0")))
    shipping_incl = Decimal(str(raw.get("shipping", "0")))

    items = _map_order_items(raw)

    return Order(
        aggregator_order_id=raw.get("marketplace_order_id", ""),
        marketplace_order_id=raw.get("marketplace_order_id", ""),
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id or 0,
        brand_id=brand.id,
        order_date=order_date,
        status=raw.get("lengow_status", ""),
        eur_amount_excl_vat=Decimal("0"),
        eur_amount_incl_vat=total_incl,
        eur_shipping_fee_excl_vat=Decimal("0"),
        eur_shipping_fee_incl_vat=shipping_incl,
        original_currency=currency_info.get("iso_a3", "EUR"),
        original_amount=Decimal(str(raw.get("original_total_order", "0"))),
        original_shipping_fee=Decimal(str(raw.get("original_shipping", "0"))),
        items=items,
        billing_address=_map_address(billing) if billing else None,
        shipping_address=_map_address(delivery) if delivery and delivery != billing else None,
        created_date=order_date,
        updated_date=updated_at,
        raw=raw,
    )


def _map_order_items(raw: dict[str, Any]) -> list[OrderItem]:
    items = []
    for package in raw.get("packages", []):
        for item in package.get("cart", []):
            price_incl = Decimal(str(item.get("amount", "0")))
            quantity = int(item.get("quantity", 0))
            items.append(
                OrderItem(
                    reference=item.get("marketplace_product_id", ""),
                    name=item.get("title", ""),
                    quantity=quantity,
                    unit_price_excl_vat=Decimal("0"),
                    unit_price_incl_vat=price_incl,
                    vat_rate=Decimal("0"),
                    total_price_excl_vat=Decimal("0"),
                    total_price_incl_vat=price_incl * quantity,
                    sku=item.get("merchant_product_id", {}).get("id", "") if isinstance(item.get("merchant_product_id"), dict) else "",
                )
            )
    return items


def map_invoice(
    raw: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    if raw.get("lengow_status") != "shipped":
        return None

    billing = raw.get("billing_address", {})
    billing_address = _map_invoice_address(billing)

    delivery = raw.get("packages", [{}])[0].get("delivery", {})
    shipping_address = _map_invoice_address(delivery) if delivery and delivery != billing else None

    items, subtotal, _ = _map_invoice_items(raw, tax_rate)

    shipping_incl = Decimal(str(raw.get("shipping", 0)))
    shipping_excl = (shipping_incl * 100) / (100 + tax_rate)

    payments = raw.get("payments", [])
    payment_info = payments[0] if payments else {}
    payment_method = payment_info.get("type", "")
    invoice_number = str(payment_info.get("id") or random.randint(3_500_000, 4_999_999))

    return Invoice(
        invoice_number=invoice_number,
        order_reference=raw.get("marketplace_order_id", ""),
        order_date=_parse_dt(raw.get("marketplace_order_date")) or datetime.now(),
        brand_id=brand.id,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id or 0,
        company_info=brand.company_info,
        logo_path=brand.logo_url,
        footer_text=brand.invoice_footer_text,
        brand_initials=brand.initials,
        billing_address=billing_address,
        shipping_address=shipping_address,
        subtotal=subtotal,
        vat_rate=tax_rate,
        total_amount=Decimal(str(raw.get("total_order", "0"))),
        items=items,
        shipping_cost=shipping_excl,
        payment_method=payment_method,
        invoice_status="paid",
        currency=raw.get("currency", {}).get("iso_a3", "EUR"),
        payment_plan_commission=Decimal("0"),
    )


def _map_invoice_items(
    raw: dict[str, Any], tax_rate: Decimal
) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for package in raw.get("packages", []):
        for item in package.get("cart", []):
            price_incl = Decimal(str(item.get("amount", "0")))
            quantity = int(item.get("quantity", 0))
            price_excl = (price_incl * 100) / (100 + tax_rate)
            item_total = price_excl * quantity
            item_tax = item_total * (tax_rate / 100)

            sku = ""
            mp_id = item.get("merchant_product_id")
            if isinstance(mp_id, dict):
                sku = mp_id.get("id", "")
            elif isinstance(mp_id, str):
                sku = mp_id

            items.append(
                InvoiceItem(
                    reference=item.get("marketplace_product_id", ""),
                    name=item.get("title", ""),
                    quantity=quantity,
                    unit_price=price_excl,
                    total_price=item_total,
                    tax_rate=tax_rate,
                    sku=sku,
                )
            )
            subtotal += item_total
            total_tax += item_tax

    return items, subtotal, total_tax
