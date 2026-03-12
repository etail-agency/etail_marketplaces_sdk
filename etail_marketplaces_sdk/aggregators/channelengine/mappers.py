"""
ChannelEngine mappers — raw API response dict → canonical SDK models.

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

from etail_marketplaces_sdk.models.brand import Brand
from etail_marketplaces_sdk.models.invoice import Invoice, InvoiceAddress, InvoiceItem
from etail_marketplaces_sdk.models.order import Order, OrderItem
from etail_marketplaces_sdk.models.shipment import Shipment, ShipmentLine, ShipmentStatus

logger = logging.getLogger(__name__)


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


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
        tracking_number=shipment.get("TrackAndTrace"),
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
