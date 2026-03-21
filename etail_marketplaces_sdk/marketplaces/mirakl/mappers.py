"""
Mirakl mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the Mirakl OpenAPI spec changes.
Cross-reference with: specs/marketplaces/mirakl/seller_openapi.json

Mirakl Seller API reference: https://developer.mirakl.com/content/product/mmp/rest/seller/openapi3

Each Mirakl operator (Galeries Lafayette, Leroy Merlin, etc.) runs the same API
surface; only credentials and the base URL differ.  Operator-specific custom
fields (``order_additional_fields``) are preserved in the ``raw`` dict on each
canonical model.
"""

from __future__ import annotations

import json
import random
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from etail_marketplaces_sdk.core.decimal_utils import optional_decimal
from etail_marketplaces_sdk.models.address import Address
from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem
from etail_marketplaces_sdk.models.product import Product, ProductAttribute
from etail_marketplaces_sdk.models.stock import StockLevel

# OR11 order states that mean the order has been shipped and an invoice
# should be generated.
SHIPPED_STATUSES = {"SHIPPING", "SHIPPED", "TO_COLLECT", "RECEIVED", "CLOSED"}


def _mirakl_marketplace_name(raw: dict[str, Any]) -> Optional[str]:
    """OR11 ``channel.label`` (preferred) or ``channel.code``; handles dict or JSON string."""
    ch = raw.get("channel")
    if isinstance(ch, str) and ch.strip().startswith("{"):
        try:
            ch = json.loads(ch)
        except (json.JSONDecodeError, TypeError):
            ch = None
    if isinstance(ch, dict):
        return ch.get("label") or ch.get("code")
    return None


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _build_name(data: dict[str, Any]) -> str:
    """Combine first name, last name, and company into a display name."""
    first = data.get("firstname") or ""
    last = data.get("lastname") or ""
    full = f"{first} {last}".strip()
    company = data.get("company") or ""
    if company and full:
        return f"{full} ({company})"
    return company or full


def _map_address(data: dict[str, Any]) -> Address:
    """Map an OR11 billing/shipping address dict to a canonical Address.

    Field reference: ``OR11_Response_200_Orders_Customer_BillingAddress``
    and ``OR11_Response_200_Orders_Customer_ShippingAddress`` in
    ``seller_openapi.json``.  The ISO country code is in the dedicated
    ``country_iso_code`` field — NOT inside a nested ``country`` object.
    """
    return Address(
        name=_build_name(data),
        address_line1=data.get("street_1") or "",
        address_line2=data.get("street_2"),
        postal_code=data.get("zip_code") or "",
        city=data.get("city") or "",
        country=data.get("country_iso_code") or "",
        phone=data.get("phone") or data.get("phone_secondary"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    street = data.get("street_1") or ""
    street2 = data.get("street_2") or ""
    full_street = f"{street}, {street2}".strip(", ") if street2 else street
    return InvoiceAddress(
        name=_build_name(data),
        address=full_street,
        postal_code=data.get("zip_code") or "",
        city=data.get("city") or "",
        country=data.get("country_iso_code") or "",
        phone=data.get("phone") or data.get("phone_secondary"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
) -> Order:
    """Map a single OR11 order dict to a canonical Order.

    Key field mappings (spec: ``OR11_Response_200_Orders``):
      - ``price``          → eur_amount_incl_vat   (order total excl. shipping)
      - ``shipping_price`` → eur_shipping_fee_incl_vat
    """
    created_at = _parse_dt(raw.get("created_date")) or datetime.now()
    updated_at = _parse_dt(raw.get("last_updated_date"))

    currency = raw.get("currency_iso_code") or "EUR"
    total_price = Decimal(str(raw.get("price") or "0"))
    total_shipping = Decimal(str(raw.get("shipping_price") or "0"))

    billing = (raw.get("customer") or {}).get("billing_address") or {}
    shipping = (raw.get("customer") or {}).get("shipping_address") or {}

    items = _map_order_items(raw)

    return Order(
        aggregator_order_id=raw.get("order_id") or "",
        marketplace_order_id=raw.get("order_id") or "",
        aggregator_id=0,
        marketplace_id=marketplace_id,
        brand_id=brand.id,
        order_date=created_at,
        status=raw.get("order_state") or "",
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
        marketplace_name=_mirakl_marketplace_name(raw),
        commission=optional_decimal(raw.get("total_commission")),
        raw=raw,
    )


def _map_order_items(raw: dict[str, Any]) -> list[OrderItem]:
    """Map order_lines from OR11 to canonical OrderItems.

    Field reference: ``OR11_Response_200_Orders_OrderLines``:
      - ``price_unit``     → unit price (NOT ``unit_price``)
      - ``price``          → line total excl. shipping
      - ``product_title``  → display name (NOT ``offer_title``)
      - ``offer_sku``      → merchant SKU for the offer
      - ``taxes[].rate``   → tax rate (as a number, e.g. 20.0 for 20 %)
    """
    items = []
    for line in raw.get("order_lines") or []:
        quantity = int(line.get("quantity") or 0)
        unit_incl = Decimal(str(line.get("price_unit") or "0"))
        line_total = Decimal(str(line.get("price") or "0"))

        taxes = line.get("taxes") or []
        vat_rate = Decimal(str(taxes[0].get("rate") or "0")) if taxes else Decimal("0")

        items.append(
            OrderItem(
                reference=line.get("offer_sku") or "",
                name=line.get("product_title") or "",
                quantity=quantity,
                unit_price_excl_vat=Decimal("0"),
                unit_price_incl_vat=unit_incl,
                vat_rate=vat_rate,
                total_price_excl_vat=Decimal("0"),
                total_price_incl_vat=line_total if line_total else unit_incl * quantity,
                sku=line.get("offer_sku") or "",
            )
        )
    return items


def map_invoice(
    raw: dict[str, Any],
    marketplace_id: int,
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    """Map an OR11 order to a canonical Invoice (only for shipped orders)."""
    if raw.get("order_state") not in SHIPPED_STATUSES:
        return None

    billing = (raw.get("customer") or {}).get("billing_address") or {}
    shipping = (raw.get("customer") or {}).get("shipping_address") or {}

    items, subtotal, _ = _map_invoice_items(raw, tax_rate)
    total_amount = Decimal(str(raw.get("price") or "0"))
    shipping_incl = Decimal(str(raw.get("shipping_price") or "0"))
    shipping_excl = (shipping_incl * 100) / (100 + tax_rate)
    invoice_number = str(random.randint(3_500_000, 4_999_999))

    return Invoice(
        invoice_number=invoice_number,
        order_reference=raw.get("order_id") or "",
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
        payment_method=raw.get("payment_type") or "",
        invoice_status="paid" if raw.get("order_state") in {"RECEIVED", "CLOSED"} else "pending",
        currency=raw.get("currency_iso_code") or "EUR",
        payment_plan_commission=Decimal("0"),
    )


def _map_invoice_items(
    raw: dict[str, Any], tax_rate: Decimal
) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for line in raw.get("order_lines") or []:
        quantity = int(line.get("quantity") or 0)
        unit_incl = Decimal(str(line.get("price_unit") or "0"))
        price_excl = (unit_incl * 100) / (100 + tax_rate)
        item_total = price_excl * quantity
        item_tax = item_total * (tax_rate / 100)

        items.append(
            InvoiceItem(
                reference=line.get("offer_sku") or "",
                name=line.get("product_title") or "",
                quantity=quantity,
                unit_price=price_excl,
                total_price=item_total,
                tax_rate=tax_rate,
                sku=line.get("offer_sku") or "",
            )
        )
        subtotal += item_total
        total_tax += item_tax

    return items, subtotal, total_tax


def map_stock_level(raw: dict[str, Any], marketplace_id: int) -> StockLevel:
    """Map a single OF21 offer record to a canonical StockLevel.

    Field reference: ``OF21_Response_200_Offers``:
      - ``shop_sku``  → sku
      - ``offer_id``  → platform_id
      - ``quantity``  → quantity_available (total available across all warehouses)
    """
    return StockLevel(
        sku=raw.get("shop_sku") or "",
        platform_id=str(raw.get("offer_id")) if raw.get("offer_id") is not None else None,
        marketplace_id=marketplace_id,
        quantity_available=int(raw.get("quantity") or 0),
        raw=raw,
    )


def map_product(raw: dict[str, Any], marketplace_id: int) -> Product:
    """Map a single OF21 offer record to a canonical Product.

    The Mirakl Seller API (OF21) is the richest source for catalogue data:
    it includes ``product_title``, ``product_brand``, ``product_description``,
    ``product_sku`` (platform SKU), ``shop_sku`` (merchant SKU), ``price``,
    ``quantity``, ``active``, ``category_code``, and ``product_references``
    (EAN etc.).

    Field reference: ``OF21_Response_200_Offers`` in ``seller_openapi.json``.
    """
    refs = raw.get("product_references") or []
    ean: Optional[str] = None
    for ref in refs:
        if (ref.get("type") or "").upper() in {"EAN", "EAN13", "UPC", "GTIN"}:
            ean = ref.get("value")
            break

    attrs: list[ProductAttribute] = []
    for attr_name, attr_value in [
        ("state_code", raw.get("state_code")),
        ("shipping_deadline", raw.get("shipping_deadline")),
    ]:
        if attr_value is not None:
            attrs.append(ProductAttribute(name=attr_name, value=str(attr_value)))

    price_raw = raw.get("price")
    price = Decimal(str(price_raw)) if price_raw is not None else None

    return Product(
        sku=raw.get("shop_sku") or "",
        name=raw.get("product_title") or "",
        platform_id=raw.get("product_sku"),
        marketplace_id=marketplace_id,
        ean=ean,
        description=raw.get("product_description"),
        price_incl_vat=price,
        brand=raw.get("product_brand"),
        category=raw.get("category_code"),
        attributes=attrs,
        is_active=bool(raw.get("active", True)),
        raw=raw,
    )
