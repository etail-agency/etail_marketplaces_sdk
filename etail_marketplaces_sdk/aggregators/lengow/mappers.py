"""
Lengow mappers — raw API response dict → canonical SDK models.

This is the ONLY file that should be updated when the Lengow OpenAPI spec changes.
Cross-reference with: specs/aggregators/lengow/openapi.json

Catalogue source: GET /v1.0/report/export (pipe-separated CSV).
Column names are feed-specific; map_product() uses a best-effort lookup over
common Lengow export field name patterns.

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
from etail_marketplaces_sdk.models.product import Product, ProductAttribute, ProductImage

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


def _parse_currency(value: Any) -> str:
    """Extract ISO 4217 code from either a plain string or the object the API actually returns.

    The spec declares ``currency`` as a string, but the live API returns an object
    like ``{"iso_a3": "EUR", "symbol": "€", "name": "Euro"}``.  This handles both.
    """
    if isinstance(value, dict):
        return value.get("iso_a3") or "EUR"
    return value or "EUR"


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _build_name(data: dict[str, Any]) -> str:
    """Prefer `full_name` from the API; fall back to first+last, then include company."""
    name = (
        data.get("full_name")
        or f"{data.get('first_name', '')} {data.get('last_name', '')}".strip()
    )
    company = data.get("company") or ""
    if company and name:
        return f"{name} ({company})"
    return company or name


def _map_address(data: dict[str, Any]) -> Address:
    line2 = data.get("second_line") or data.get("complement") or None
    return Address(
        name=_build_name(data),
        address_line1=data.get("first_line") or "",
        address_line2=line2,
        postal_code=data.get("zipcode") or "",
        city=data.get("city") or "",
        country=data.get("common_country_iso_a2") or "",
        phone=data.get("phone_mobile") or data.get("phone_office") or data.get("phone_home"),
        email=data.get("email"),
    )


def _map_invoice_address(data: dict[str, Any]) -> InvoiceAddress:
    line1 = data.get("first_line") or ""
    line2 = data.get("second_line") or data.get("complement") or ""
    full_street = f"{line1}, {line2}".strip(", ") if line2 else line1
    return InvoiceAddress(
        name=_build_name(data),
        address=full_street,
        postal_code=data.get("zipcode") or "",
        city=data.get("city") or "",
        country=data.get("common_country_iso_a2") or "",
        phone=data.get("phone_mobile") or data.get("phone_office") or data.get("phone_home"),
        email=data.get("email"),
    )


def map_order(
    raw: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
) -> Order:
    currency = _parse_currency(raw.get("currency"))
    original_currency = _parse_currency(raw.get("original_currency")) if raw.get("original_currency") else currency

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
        original_currency=original_currency,
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

    currency = _parse_currency(raw.get("currency"))

    shipping_incl = Decimal(str(raw.get("shipping", 0)))
    shipping_excl = (shipping_incl * 100) / (100 + tax_rate)

    payments = raw.get("payments", [])
    payment_info = payments[0] if payments else {}
    payment_method = payment_info.get("type", "")

    # Use the order-level invoice_number from Lengow if present (spec: Order.invoice_number)
    invoice_number = (
        raw.get("invoice_number")
        or str(payment_info.get("id") or random.randint(3_500_000, 4_999_999))
    )

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
        currency=currency,
        payment_plan_commission=Decimal("0"),
    )


def _pick(row: dict[str, Any], *candidates: str) -> Optional[str]:
    """Return the first non-empty value matching any candidate key (case-insensitive)."""
    lower = {k.lower(): v for k, v in row.items()}
    for c in candidates:
        val = lower.get(c.lower())
        if val not in (None, "", "N/A", "n/a"):
            return str(val)
    return None


def map_product(
    row: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
) -> Product:
    """Map a Lengow report CSV row (pipe-separated) to a canonical :class:`Product`.

    Lengow's ``GET /v1.0/report/export`` returns feed-specific CSV columns.
    This mapper performs a best-effort lookup over common export field name
    patterns.  The original row is always preserved in ``product.raw``.

    Args:
        row:            A dict built from one CSV row (keys are header columns).
        aggregator_id:  Internal aggregator identifier.
        marketplace_id: Internal marketplace identifier (optional).

    Returns:
        :class:`~etail_marketplaces_sdk.models.product.Product`
    """
    sku = _pick(row, "sku", "merchant_sku", "id_product", "product_id", "reference", "id") or ""
    name = _pick(row, "name", "title", "product_title", "product_name", "nom") or ""
    ean = _pick(row, "ean", "ean13", "gtin", "barcode", "upc", "isbn")
    brand = _pick(row, "brand", "brand_name", "product_brand", "marque")
    description = _pick(row, "description", "product_description", "short_description")
    category = _pick(row, "category", "product_category", "google_product_category", "categorie")

    price_raw = _pick(row, "price", "selling_price", "product_price", "prix")
    try:
        price = Decimal(str(price_raw).replace(",", ".")) if price_raw else None
    except Exception:
        price = None

    # Images — try common column patterns up to 5 extra slots
    images: list[ProductImage] = []
    for pos, key in enumerate(
        ["image", "image_url", "image1", "url_image", "image2", "image3", "image4", "image5"],
        start=0,
    ):
        url = _pick(row, key)
        if url and url.startswith("http"):
            images.append(ProductImage(url=url, position=pos))

    # Remaining non-empty columns become attributes
    known = {
        "sku", "merchant_sku", "id_product", "product_id", "reference", "id",
        "name", "title", "product_title", "product_name", "nom",
        "ean", "ean13", "gtin", "barcode", "upc", "isbn",
        "brand", "brand_name", "product_brand", "marque",
        "description", "product_description", "short_description",
        "category", "product_category", "google_product_category", "categorie",
        "price", "selling_price", "product_price", "prix",
        "image", "image_url", "image1", "url_image",
        "image2", "image3", "image4", "image5",
    }
    attributes = [
        ProductAttribute(name=k, value=str(v))
        for k, v in row.items()
        if k.lower() not in known and v not in (None, "", "N/A", "n/a")
    ]

    return Product(
        sku=sku,
        name=name,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id,
        ean=ean,
        description=description,
        price_incl_vat=price,
        brand=brand,
        category=category,
        images=images,
        attributes=attributes,
        raw=row,
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
