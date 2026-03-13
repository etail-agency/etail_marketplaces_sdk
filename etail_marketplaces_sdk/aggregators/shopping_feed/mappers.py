"""
ShoppingFeed mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the ShoppingFeed OpenAPI spec changes.
Cross-reference with: specs/aggregators/shopping_feed/order.yml

ShoppingFeed API reference: https://developer.shopping-feed.com/order-api
"""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from etail_marketplaces_sdk.models.address import Address
from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_name(data: dict[str, Any]) -> str:
    """Combine first name, last name, and company into a display name."""
    first = data.get("firstName") or ""
    last = data.get("lastName") or ""
    full = f"{first} {last}".strip()
    company = data.get("company") or ""
    if company and full:
        return f"{full} ({company})"
    return company or full


def _map_address(data: dict[str, Any]) -> Address:
    return Address(
        name=_build_name(data),
        address_line1=data.get("street") or "",
        address_line2=data.get("street2") or None,
        postal_code=data.get("postalCode") or "",
        city=data.get("city") or "",
        country=data.get("country") or "",
        phone=data.get("phone") or data.get("mobilePhone"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    street = data.get("street") or ""
    street2 = data.get("street2") or ""
    full_street = f"{street}, {street2}".strip(", ") if street2 else street
    return InvoiceAddress(
        name=_build_name(data),
        address=full_street,
        postal_code=data.get("postalCode") or "",
        city=data.get("city") or "",
        country=data.get("country") or "",
        phone=data.get("phone") or data.get("mobilePhone"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    aggregator_id: int,
    brand: Brand,
) -> Order:
    created_at = _parse_dt(raw.get("createdAt")) or datetime.now()
    updated_at = _parse_dt(raw.get("updatedAt"))
    payment = raw.get("payment", {})
    total_incl = Decimal(str(payment.get("totalAmount", "0")))
    shipping_incl = Decimal(str(payment.get("shippingAmount", "0")))

    billing = raw.get("billingAddress", {})
    shipping = raw.get("shippingAddress", {})

    items = _map_order_items(raw)

    return Order(
        aggregator_order_id=str(raw.get("id", "")),
        marketplace_order_id=raw.get("reference", ""),
        aggregator_id=aggregator_id,
        marketplace_id=raw.get("_embedded", {}).get("channel", {}).get("id") or raw.get("channelId") or 0,
        brand_id=brand.id,
        order_date=created_at,
        status=raw.get("status", ""),
        eur_amount_excl_vat=Decimal("0"),
        eur_amount_incl_vat=total_incl,
        eur_shipping_fee_excl_vat=Decimal("0"),
        eur_shipping_fee_incl_vat=shipping_incl,
        original_currency=payment.get("currency", "EUR"),
        original_amount=total_incl,
        original_shipping_fee=shipping_incl,
        items=items,
        billing_address=_map_address(billing) if billing else None,
        shipping_address=_map_address(shipping) if shipping and shipping != billing else None,
        created_date=created_at,
        updated_date=updated_at,
        raw=raw,
    )


def _map_order_items(raw: dict[str, Any]) -> list[OrderItem]:
    items = []
    for item in raw.get("items", []):
        price_incl = Decimal(str(item.get("price", "0")))
        quantity = int(item.get("quantity", 0))
        items.append(
            OrderItem(
                reference=item.get("reference", ""),
                name=item.get("name", ""),
                quantity=quantity,
                unit_price_excl_vat=Decimal("0"),
                unit_price_incl_vat=price_incl,
                vat_rate=Decimal("0"),
                total_price_excl_vat=Decimal("0"),
                total_price_incl_vat=price_incl * quantity,
                sku=item.get("reference", ""),
            )
        )
    return items


def map_invoice(
    raw: dict[str, Any],
    aggregator_id: int,
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    if raw.get("status") != "shipped":
        return None

    billing = raw.get("billingAddress", {})
    shipping = raw.get("shippingAddress", {})

    billing_address = _map_invoice_address(billing)
    shipping_address = _map_invoice_address(shipping) if shipping and shipping != billing else None

    items, subtotal, _ = _map_invoice_items(raw, tax_rate)

    payment = raw.get("payment", {})
    shipping_incl = Decimal(str(payment.get("shippingAmount", "0")))
    shipping_excl = (shipping_incl * 100) / (100 + tax_rate)
    payment_method = payment.get("method", "")

    return Invoice(
        invoice_number=str(raw["id"]),
        order_reference=raw.get("reference", ""),
        order_date=_parse_dt(raw.get("createdAt")) or datetime.now(),
        brand_id=brand.id,
        aggregator_id=aggregator_id,
        marketplace_id=raw.get("_embedded", {}).get("channel", {}).get("id") or raw.get("channelId") or 0,
        company_info=brand.company_info,
        logo_path=brand.logo_url,
        footer_text=brand.invoice_footer_text,
        brand_initials=brand.initials,
        billing_address=billing_address,
        shipping_address=shipping_address,
        subtotal=subtotal,
        vat_rate=tax_rate,
        total_amount=Decimal(str(payment.get("totalAmount", "0"))),
        items=items,
        shipping_cost=shipping_excl,
        payment_method=payment_method,
        invoice_status="paid",
        currency=payment.get("currency", "EUR"),
        payment_plan_commission=Decimal("0"),
    )


def _map_invoice_items(
    raw: dict[str, Any], tax_rate: Decimal
) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for item in raw.get("items", []):
        price_incl = Decimal(str(item.get("price", "0")))
        quantity = int(item.get("quantity", 0))
        price_excl = (price_incl * 100) / (100 + tax_rate)
        item_total = price_excl * quantity
        item_tax = item_total * (tax_rate / 100)

        items.append(
            InvoiceItem(
                reference=item.get("reference", ""),
                name=item.get("name", ""),
                quantity=quantity,
                unit_price=price_excl,
                total_price=item_total,
                tax_rate=tax_rate,
                sku=item.get("reference", ""),
            )
        )
        subtotal += item_total
        total_tax += item_tax

    return items, subtotal, total_tax
