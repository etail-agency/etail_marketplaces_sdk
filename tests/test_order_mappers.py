"""
Order mapper smoke tests — dict → :class:`Order` with no HTTP.

Each test loads a small JSON fixture (reviewable in PRs) and asserts the
fields that differ most across integrations: ids, marketplace label, commission.
"""

from __future__ import annotations

from decimal import Decimal

from etail_marketplaces_sdk.aggregators.channelengine.mappers import map_order, map_order_from_orders_api
from etail_marketplaces_sdk.aggregators.lengow.mappers import map_order as lengow_map_order
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_order as shoppingfeed_map_order
from etail_marketplaces_sdk.marketplaces.manomano.mappers import map_order as manomano_map_order
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_order as mirakl_map_order
from etail_marketplaces_sdk.models.brand import Brand

from tests.support import load_order_fixture


def test_lengow_map_order_commission_and_items(brand: Brand):
    raw = load_order_fixture("lengow_minimal.json")
    order = lengow_map_order(raw, aggregator_id=3, marketplace_id=6, brand=brand)

    assert order.aggregator_order_id == "LO-1"
    assert order.marketplace_name == "amazon_fr"
    assert order.commission == Decimal("12.50")
    assert len(order.items) == 1
    assert order.items[0].sku == "SKU-W"
    assert order.items[0].commission == Decimal("1.25")


def test_shoppingfeed_map_order_uses_embedded_channel(brand: Brand):
    raw = load_order_fixture("shoppingfeed_minimal.json")
    order = shoppingfeed_map_order(raw, aggregator_id=5, brand=brand)

    assert order.marketplace_order_id == "SF-REF"
    assert order.marketplace_id == 7
    assert order.marketplace_name == "Cool Channel"
    assert order.commission == Decimal("3.00")
    assert order.items[0].commission == Decimal("1.00")


def test_mirakl_map_order_channel_and_line_commission(brand: Brand):
    raw = load_order_fixture("mirakl_minimal.json")
    order = mirakl_map_order(raw, marketplace_id=99, brand=brand)

    assert order.marketplace_order_id == "M-ORD-1"
    assert order.marketplace_name == "Mirakl Shop"
    assert order.commission == Decimal("7.50")
    assert order.items[0].commission == Decimal("2.00")


def test_channelengine_map_order_from_orders_api_total_fee(brand: Brand):
    raw = load_order_fixture("channelengine_orders_api_minimal.json")
    order = map_order_from_orders_api(raw, aggregator_id=6, marketplace_id=0, brand=brand)

    assert order is not None
    assert order.marketplace_order_id == "M-1"
    assert order.marketplace_name == "Bol"
    assert order.commission == Decimal("10")
    assert order.items[0].commission == Decimal("5")


def test_channelengine_map_order_from_shipment_sums_nested_fee_fixed(brand: Brand):
    raw = load_order_fixture("channelengine_shipment_minimal.json")
    order = map_order(raw, aggregator_id=6, marketplace_id=0, brand=brand)

    assert order is not None
    assert order.aggregator_order_id == "CE-SHIP-1"
    assert order.marketplace_name == "Amazon DE"
    assert order.commission == Decimal("2.5")
    assert order.items[0].commission == Decimal("2.5")


def test_manomano_map_order_line_commission_roll_up(brand: Brand):
    raw = load_order_fixture("manomano_minimal.json")
    order = manomano_map_order(raw, marketplace_id=12, brand=brand)

    assert order.marketplace_order_id == "MM-1"
    assert order.marketplace_name == "ManoMano FR"
    assert order.commission == Decimal("4.50")
    assert order.items[0].commission == Decimal("4.50")
