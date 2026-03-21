"""Invoice stream — shipped / eligible payloads only (no HTTP)."""

from __future__ import annotations

from decimal import Decimal

from etail_marketplaces_sdk.aggregators.channelengine.mappers import (
    map_invoice as ce_map_invoice_shipment,
    map_invoice_from_orders_api,
)
from etail_marketplaces_sdk.aggregators.lengow.mappers import map_invoice as lengow_map_invoice
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_invoice as sf_map_invoice
from etail_marketplaces_sdk.marketplaces.manomano.mappers import map_invoice as manomano_map_invoice
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_invoice as mirakl_map_invoice
from etail_marketplaces_sdk.models.brand import Brand

from tests.support import load_fixture


def test_lengow_map_invoice_when_shipped(brand: Brand):
    raw = load_fixture("invoices", "lengow_shipped.json")
    inv = lengow_map_invoice(raw, aggregator_id=3, marketplace_id=6, brand=brand)

    assert inv is not None
    assert inv.invoice_number == "INV-LG-100"
    assert inv.order_reference == "LO-INV-1"
    assert inv.total_amount == Decimal("100.00")
    assert inv.payment_method == "card"
    assert len(inv.items) == 1


def test_shoppingfeed_map_invoice_when_shipped(brand: Brand):
    raw = load_fixture("invoices", "shoppingfeed_shipped.json")
    inv = sf_map_invoice(raw, aggregator_id=5, brand=brand)

    assert inv is not None
    assert inv.invoice_number == "200"
    assert inv.order_reference == "SF-INV"
    assert inv.marketplace_id == 3
    assert inv.payment_method == "paypal"


def test_mirakl_map_invoice_when_shipped(brand: Brand):
    raw = load_fixture("invoices", "mirakl_shipped.json")
    inv = mirakl_map_invoice(raw, marketplace_id=9, brand=brand)

    assert inv is not None
    assert inv.order_reference == "M-INV-1"
    assert inv.total_amount == Decimal("60.00")


def test_manomano_map_invoice_when_shipped(brand: Brand):
    raw = load_fixture("invoices", "manomano_shipped.json")
    inv = manomano_map_invoice(raw, marketplace_id=12, brand=brand)

    assert inv is not None
    assert inv.order_reference == "MM-INV"
    assert inv.items[0].sku == "MM-I"


def test_channelengine_map_invoice_from_shipment(brand: Brand):
    raw = load_fixture("invoices", "channelengine_shipment_invoice.json")
    inv = ce_map_invoice_shipment(raw, aggregator_id=6, marketplace_id=0, brand=brand)

    assert inv is not None
    assert inv.invoice_number == "SHIP-42"
    assert inv.order_reference == "CE-INV-SHIP"
    assert len(inv.items) == 1


def test_channelengine_map_invoice_from_orders_api(brand: Brand):
    raw = load_fixture("invoices", "channelengine_orders_shipped.json")
    inv = map_invoice_from_orders_api(raw, aggregator_id=6, marketplace_id=0, brand=brand)

    assert inv is not None
    assert inv.order_reference == "CE-INV-ORD"
    assert inv.total_amount == Decimal("120")
    assert inv.billing_address.country == "NL"
    assert str(inv.invoice_number) == "7001"


def test_non_shipped_returns_none(brand: Brand):
    raw = load_fixture("orders", "shoppingfeed_minimal.json")
    assert sf_map_invoice(raw, aggregator_id=5, brand=brand) is None
