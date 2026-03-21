"""
ChannelEngine mappers — raw API response dict → canonical SDK models.

Two API sources are supported:

  /v2/shipments  (legacy, CLOSED shipments only — no address data)
      map_order()       → Order
      map_invoice()     → Invoice
      map_shipment()    → Shipment

  /v2/orders  (orders API — full address, explicit VAT, all statuses)
      map_order_from_orders_api()    → Order
      map_invoice_from_orders_api()  → Optional[Invoice]  (SHIPPED/CLOSED only)

  /v2/products  (catalogue)
      map_product()     → Product

This is the ONLY file that should be updated when the ChannelEngine OpenAPI spec changes.
Cross-reference with: specs/aggregators/channelengine/openapi.json

ChannelEngine API reference: https://api.channelengine.net/merchant
"""

from __future__ import annotations

import logging
import random
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Optional

from etail_marketplaces_sdk.core.decimal_utils import optional_decimal
from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem
from etail_marketplaces_sdk.models.product import Product, ProductAttribute, ProductImage
from etail_marketplaces_sdk.models.shipment import Shipment, ShipmentLine, ShipmentStatus
from etail_marketplaces_sdk.models.stock import StockLevel

logger = logging.getLogger(__name__)

# Statuses from /v2/orders that represent a fully shipped order and should
# trigger invoice creation.
_SHIPPED_STATUSES = {"SHIPPED", "CLOSED"}


def _ce_orders_api_marketplace_name(order: dict[str, Any]) -> Optional[str]:
    """``ChannelName`` (tenant-specific) or ``GlobalChannelName`` from ``GET /v2/orders``."""
    return order.get("ChannelName") or order.get("GlobalChannelName")


def _ce_sum_line_fee_fixed(lines: Optional[list[dict[str, Any]]]) -> Optional[Decimal]:
    """Sum ``FeeFixed`` from order/shipment lines (on line or nested ``OrderLine``)."""
    if not lines:
        return None
    total = Decimal("0")
    saw = False
    for line in lines:
        fee = line.get("FeeFixed")
        if fee is None:
            ol = line.get("OrderLine") or {}
            fee = ol.get("FeeFixed")
        d = optional_decimal(fee)
        if d is not None:
            total += d
            saw = True
    return total if saw else None


def _ce_orders_api_commission(order: dict[str, Any]) -> Optional[Decimal]:
    """Prefer header ``TotalFee``; otherwise sum per-line ``FeeFixed``."""
    if order.get("TotalFee") is not None:
        return optional_decimal(order.get("TotalFee"))
    return _ce_sum_line_fee_fixed(order.get("Lines"))


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def map_stock_level(
    record: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    location_name: Optional[str] = None,
) -> StockLevel:
    """Map a single ``GET /v2/offer/stock`` record to a canonical :class:`StockLevel`.

    Args:
        record:         One item from the ``Content`` array of the stock response.
                        Fields: MerchantProductNo, StockLocationId, Stock, UpdatedAt.
        aggregator_id:  Numeric aggregator ID.
        marketplace_id: Optional static marketplace ID.
        location_name:  Human-readable name of the stock location (from
                        ``GET /v2/stocklocations``), enriched at call time.

    Returns:
        A populated :class:`~etail_marketplaces_sdk.models.stock.StockLevel`.
    """
    location_id = record.get("StockLocationId")
    raw = {**record}
    if location_name:
        raw["StockLocationName"] = location_name
    return StockLevel(
        sku=record.get("MerchantProductNo") or "",
        quantity_available=int(record.get("Stock") or 0),
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id,
        warehouse_id=str(location_id) if location_id is not None else None,
        last_updated=_parse_dt(record.get("UpdatedAt")),
        raw=raw,
    )


def map_product(
    record: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
) -> Product:
    """Map a single ``GET /v2/products`` record to a canonical :class:`Product`.

    Fields sourced from ``MerchantProductResponse`` in the OpenAPI spec.
    ``ExtraData`` name/value pairs become :class:`ProductAttribute` objects.
    ``ImageUrl`` + ``ExtraImageUrl1–9`` are collected into :class:`ProductImage` objects.

    Args:
        record:         One item from the ``Content`` array of the products response.
        aggregator_id:  Numeric aggregator ID.
        marketplace_id: Optional static marketplace ID.

    Returns:
        A populated :class:`~etail_marketplaces_sdk.models.product.Product`.
    """
    images: list[ProductImage] = []
    for pos, key in enumerate(
        ["ImageUrl", "ExtraImageUrl1", "ExtraImageUrl2", "ExtraImageUrl3",
         "ExtraImageUrl4", "ExtraImageUrl5", "ExtraImageUrl6",
         "ExtraImageUrl7", "ExtraImageUrl8", "ExtraImageUrl9"],
        start=0,
    ):
        url = record.get(key)
        if url:
            images.append(ProductImage(url=url, position=pos))

    attributes: list[ProductAttribute] = []
    for extra in record.get("ExtraData") or []:
        name = extra.get("Key") or extra.get("key") or ""
        value = extra.get("Value") or extra.get("value") or ""
        if name:
            attributes.append(ProductAttribute(name=name, value=str(value)))

    for attr_key in ("Size", "Color", "ManufacturerProductNumber",
                     "ParentMerchantProductNo", "ParentMerchantProductNo2",
                     "ShippingTime"):
        val = record.get(attr_key)
        if val is not None:
            attributes.append(ProductAttribute(name=attr_key, value=str(val)))

    price_raw = record.get("Price")
    price = Decimal(str(price_raw)) if price_raw is not None else None

    return Product(
        sku=record.get("MerchantProductNo") or "",
        name=record.get("Name") or "",
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id,
        platform_id=record.get("MerchantProductNo"),
        ean=record.get("Ean"),
        description=record.get("Description"),
        price_incl_vat=price,
        brand=record.get("Brand"),
        images=images,
        attributes=attributes,
        is_active=bool(record.get("IsActive", True)),
        raw=record,
    )


def map_order(
    shipment: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
) -> Optional[Order]:
    channel_order_no = shipment.get("ChannelOrderNo", "")
    if not channel_order_no:
        return None

    order_date = _parse_dt(shipment.get("CreatedAt")) or datetime.now(timezone.utc)
    updated_at = _parse_dt(shipment.get("UpdatedAt"))

    lines = shipment.get("Lines", [])
    total_incl = Decimal("0")
    items = []

    for line in lines:
        quantity = line.get("Quantity", 0)
        order_line = line.get("OrderLine", {})
        unit_price_incl = Decimal(str(order_line.get("UnitPriceInclVat", 0)))
        line_total = unit_price_incl * quantity
        total_incl += line_total

        items.append(
            OrderItem(
                reference=line.get("ChannelProductNo", "") or line.get("MerchantProductNo", ""),
                name=order_line.get("Description", ""),
                quantity=quantity,
                unit_price_excl_vat=Decimal("0"),
                unit_price_incl_vat=unit_price_incl,
                vat_rate=Decimal("0"),
                total_price_excl_vat=Decimal("0"),
                total_price_incl_vat=line_total,
                sku=line.get("MerchantProductNo", "") or line.get("ChannelProductNo", ""),
            )
        )

    return Order(
        aggregator_order_id=channel_order_no,
        marketplace_order_id=channel_order_no,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id or 0,
        brand_id=brand.id,
        order_date=order_date,
        status="SHIPPED",
        eur_amount_excl_vat=Decimal("0"),
        eur_amount_incl_vat=total_incl,
        eur_shipping_fee_excl_vat=Decimal("0"),
        eur_shipping_fee_incl_vat=Decimal("0"),
        original_currency="EUR",
        original_amount=total_incl,
        original_shipping_fee=Decimal("0"),
        items=items,
        created_date=order_date,
        updated_date=updated_at,
        marketplace_name=shipment.get("ChannelName") or shipment.get("GlobalChannelName"),
        commission=_ce_sum_line_fee_fixed(lines),
        raw=shipment,
    )


def map_invoice(
    shipment: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    channel_order_no = shipment.get("ChannelOrderNo", "")
    if not channel_order_no:
        return None

    order_date = _parse_dt(shipment.get("CreatedAt")) or datetime.now(timezone.utc)

    # ChannelEngine shipments do not include full address data — placeholder
    billing_address = InvoiceAddress(name="", address="", postal_code="", city="", country="")

    items, subtotal, _ = _map_invoice_items(shipment, tax_rate)
    if not items:
        return None

    merchant_shipment_no = shipment.get("MerchantShipmentNo", "")
    invoice_number = merchant_shipment_no or str(random.randint(3_500_000, 4_999_999))

    total_amount = subtotal * (1 + tax_rate / 100)

    return Invoice(
        invoice_number=invoice_number,
        order_reference=channel_order_no,
        order_date=order_date,
        brand_id=brand.id,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id or 0,
        company_info=brand.company_info,
        logo_path=brand.logo_url,
        footer_text=brand.invoice_footer_text,
        brand_initials=brand.initials,
        billing_address=billing_address,
        shipping_address=None,
        subtotal=subtotal,
        vat_rate=tax_rate,
        total_amount=total_amount,
        items=items,
        shipping_cost=Decimal("0"),
        payment_method="",
        invoice_status="paid",
        currency="EUR",
        payment_plan_commission=Decimal("0"),
    )


def map_shipment(
    shipment: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
) -> Optional[Shipment]:
    channel_order_no = shipment.get("ChannelOrderNo", "")
    merchant_shipment_no = shipment.get("MerchantShipmentNo", "")
    shipment_id = merchant_shipment_no or channel_order_no
    if not shipment_id:
        return None

    lines = [
        ShipmentLine(
            sku=line.get("MerchantProductNo", "") or line.get("ChannelProductNo", ""),
            quantity=line.get("Quantity", 0),
            platform_product_id=line.get("ChannelProductNo"),
        )
        for line in shipment.get("Lines", [])
    ]

    return Shipment(
        shipment_id=shipment_id,
        order_id=channel_order_no,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id,
        carrier=shipment.get("Method"),
        tracking_number=shipment.get("TrackTraceNo"),
        status=ShipmentStatus.DELIVERED,
        shipped_at=_parse_dt(shipment.get("CreatedAt")),
        lines=lines,
        raw=shipment,
    )


def _map_invoice_items(
    shipment: dict[str, Any], tax_rate: Decimal
) -> tuple[list[InvoiceItem], Decimal, Decimal]:
    items = []
    subtotal = Decimal("0")
    total_tax = Decimal("0")

    for line in shipment.get("Lines", []):
        quantity = line.get("Quantity", 0)
        if quantity <= 0:
            continue

        order_line = line.get("OrderLine", {})
        unit_price_incl = Decimal(str(order_line.get("UnitPriceInclVat", 0)))
        price_excl = (unit_price_incl * 100) / (100 + tax_rate)
        item_total = price_excl * quantity
        item_tax = item_total * (tax_rate / 100)

        channel_product_no = line.get("ChannelProductNo", "")
        merchant_product_no = line.get("MerchantProductNo", "")

        items.append(
            InvoiceItem(
                reference=channel_product_no or merchant_product_no,
                name=order_line.get("Description", ""),
                quantity=quantity,
                unit_price=price_excl,
                total_price=item_total,
                tax_rate=tax_rate,
                sku=merchant_product_no or channel_product_no,
            )
        )
        subtotal += item_total
        total_tax += item_tax

    return items, subtotal, total_tax


# ──────────────────────────────────────────────────────────────────────────────
# /v2/orders  mappers
# ──────────────────────────────────────────────────────────────────────────────

def _map_address(addr: Optional[dict[str, Any]]) -> InvoiceAddress:
    """Build an InvoiceAddress from a ChannelEngine address block."""
    if not addr:
        return InvoiceAddress(name="", address="", postal_code="", city="", country="")
    first = addr.get("FirstName") or ""
    last = addr.get("LastName") or ""
    full_name = f"{first} {last}".strip()
    company = addr.get("CompanyName") or ""
    if company and full_name:
        full_name = f"{full_name} ({company})"
    elif company:
        full_name = company
    return InvoiceAddress(
        name=full_name,
        address=addr.get("Line1") or "",
        postal_code=addr.get("ZipCode") or "",
        city=addr.get("City") or "",
        country=addr.get("CountryIso") or "",
    )


def map_order_from_orders_api(
    order: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
) -> Optional[Order]:
    """Map a single record from ``GET /v2/orders`` to a canonical :class:`Order`.

    Unlike :func:`map_order` (which reads from ``/v2/shipments`` and only sees
    ``CLOSED`` records), this function works with the full orders feed and
    therefore reflects every status (``NEW``, ``IN_PROGRESS``, ``SHIPPED``,
    ``CLOSED``, ``CANCELLED``, …).

    All price fields are taken directly from the API response — no
    back-calculation is needed because ``/v2/orders`` includes both excl- and
    incl-VAT amounts and explicit per-line ``VatRate``.

    Args:
        order:          Raw order dict from the ``Content`` array of the
                        ``GET /v2/orders`` response.
        aggregator_id:  Numeric ID of the ChannelEngine aggregator record in
                        your data store (``ChannelEngineClient.aggregator_id``
                        is ``6`` by default).
        marketplace_id: Static marketplace ID to attach to every order.  Pass
                        ``None`` to fall back to ``0``.
        brand:          :class:`~etail_marketplaces_sdk.models.brand.Brand`
                        instance associated with this tenant.

    Returns:
        A populated :class:`~etail_marketplaces_sdk.models.order.Order`, or
        ``None`` if the record has no ``ChannelOrderNo``.
    """
    channel_order_no = order.get("ChannelOrderNo", "")
    if not channel_order_no:
        return None

    merchant_order_no = order.get("MerchantOrderNo") or channel_order_no
    order_date = _parse_dt(order.get("CreatedAt")) or datetime.now(timezone.utc)
    updated_at = _parse_dt(order.get("UpdatedAt"))

    items: list[OrderItem] = []
    for line in order.get("Lines", []):
        qty = line.get("Quantity", 0)
        if qty <= 0:
            continue
        items.append(
            OrderItem(
                reference=line.get("MerchantProductNo") or line.get("ChannelProductNo") or "",
                name=line.get("Description") or "",
                quantity=qty,
                unit_price_excl_vat=Decimal(str(line.get("UnitPriceExclVat", 0))),
                unit_price_incl_vat=Decimal(str(line.get("UnitPriceInclVat", 0))),
                vat_rate=Decimal(str(line.get("VatRate", 0))),
                total_price_excl_vat=Decimal(str(line.get("LineTotalExclVat", 0))),
                total_price_incl_vat=Decimal(str(line.get("LineTotalInclVat", 0))),
                sku=line.get("MerchantProductNo") or line.get("ChannelProductNo") or "",
                ean=line.get("Gtin"),
            )
        )

    return Order(
        aggregator_order_id=channel_order_no,
        marketplace_order_id=merchant_order_no,
        aggregator_id=aggregator_id,
        marketplace_id=marketplace_id or 0,
        brand_id=brand.id,
        order_date=order_date,
        status=order.get("Status") or "",
        eur_amount_excl_vat=Decimal(str(order.get("TotalExclVat", 0))),
        eur_amount_incl_vat=Decimal(str(order.get("TotalInclVat", 0))),
        eur_shipping_fee_excl_vat=Decimal(str(order.get("ShippingCostsExclVat", 0))),
        eur_shipping_fee_incl_vat=Decimal(str(order.get("ShippingCostsInclVat", 0))),
        original_currency=order.get("CurrencyCode") or "EUR",
        original_amount=Decimal(str(order.get("OriginalTotalInclVat") or order.get("TotalInclVat", 0))),
        original_shipping_fee=Decimal(
            str(order.get("OriginalShippingCostsInclVat") or order.get("ShippingCostsInclVat", 0))
        ),
        items=items,
        payment_method=order.get("PaymentMethod"),
        created_date=order_date,
        updated_date=updated_at,
        marketplace_name=_ce_orders_api_marketplace_name(order),
        commission=_ce_orders_api_commission(order),
        raw=order,
    )


def map_invoice_from_orders_api(
    order: dict[str, Any],
    aggregator_id: int,
    marketplace_id: Optional[int],
    brand: Brand,
    tax_rate: Decimal = Decimal("20"),
) -> Optional[Invoice]:
    """Map a single record from ``GET /v2/orders`` to a canonical :class:`Invoice`.

    Unlike :func:`map_invoice` (which uses ``/v2/shipments`` and cannot
    populate address fields), this function builds a fully-populated invoice
    including billing and shipping addresses from the order's address blocks.

    Invoice generation is intentionally restricted to orders whose ``Status``
    is ``SHIPPED`` or ``CLOSED``.  All other statuses return ``None`` so that
    callers do not need to filter the result list themselves.

    Subtotals are computed from the per-line ``LineTotalExclVat`` values.
    ``TotalInclVat`` from the order header is used as ``total_amount`` so the
    invoice always matches the amount the customer actually paid.

    Args:
        order:          Raw order dict from the ``Content`` array of the
                        ``GET /v2/orders`` response.
        aggregator_id:  Numeric ID of the ChannelEngine aggregator record.
        marketplace_id: Static marketplace ID; falls back to ``0`` if ``None``.
        brand:          :class:`~etail_marketplaces_sdk.models.brand.Brand`
                        instance used to populate logo, footer, and company
                        metadata on the invoice.
        tax_rate:       Default VAT rate (percentage, e.g. ``Decimal("20")``).
                        Used as a fallback when a line's own ``VatRate`` is
                        zero or absent.

    Returns:
        A populated :class:`~etail_marketplaces_sdk.models.invoice.Invoice`,
        or ``None`` when the order status is not ``SHIPPED``/``CLOSED``, or
        when the order carries no shippable line items.
    """
    channel_order_no = order.get("ChannelOrderNo", "")
    if not channel_order_no:
        return None

    status = order.get("Status") or ""
    if status not in _SHIPPED_STATUSES:
        return None

    order_date = _parse_dt(order.get("CreatedAt")) or datetime.now(timezone.utc)
    billing_address = _map_address(order.get("BillingAddress"))
    shipping_address = _map_address(order.get("ShippingAddress")) if order.get("ShippingAddress") else None

    items: list[InvoiceItem] = []
    subtotal = Decimal("0")

    for line in order.get("Lines", []):
        qty = line.get("Quantity", 0)
        if qty <= 0:
            continue

        unit_excl = Decimal(str(line.get("UnitPriceExclVat", 0)))
        line_excl = Decimal(str(line.get("LineTotalExclVat", 0)))
        line_vat_rate = Decimal(str(line.get("VatRate", 0))) or tax_rate

        items.append(
            InvoiceItem(
                reference=line.get("MerchantProductNo") or line.get("ChannelProductNo") or "",
                name=line.get("Description") or "",
                quantity=qty,
                unit_price=unit_excl,
                total_price=line_excl,
                tax_rate=line_vat_rate,
                sku=line.get("MerchantProductNo") or line.get("ChannelProductNo") or "",
            )
        )
        subtotal += line_excl

    if not items:
        return None

    merchant_order_no = order.get("MerchantOrderNo") or ""
    try:
        invoice_number: Any = int(merchant_order_no)
    except (ValueError, TypeError):
        invoice_number = merchant_order_no or str(random.randint(3_500_000, 4_999_999))

    total_amount = Decimal(str(order.get("TotalInclVat", 0)))
    shipping_cost = Decimal(str(order.get("ShippingCostsExclVat", 0)))

    return Invoice(
        invoice_number=invoice_number,
        order_reference=channel_order_no,
        order_date=order_date,
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
        total_amount=total_amount,
        items=items,
        shipping_cost=shipping_cost,
        payment_method=order.get("PaymentMethod") or "",
        invoice_status="paid",
        currency=order.get("CurrencyCode") or "EUR",
        payment_plan_commission=Decimal("0"),
    )
