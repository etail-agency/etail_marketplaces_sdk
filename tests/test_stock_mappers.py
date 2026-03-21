"""Stock stream — ``map_stock_level`` only (no HTTP)."""

from __future__ import annotations

from etail_marketplaces_sdk.aggregators.channelengine.mappers import map_stock_level as ce_map_stock
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_stock_level as sf_map_stock
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_stock_level as mirakl_map_stock

from tests.support import load_fixture


def test_channelengine_map_stock_enriches_location_name():
    raw = load_fixture("stock", "channelengine_stock.json")
    level = ce_map_stock(raw, aggregator_id=6, marketplace_id=0, location_name="Main DC")

    assert level.sku == "SKU-CE"
    assert level.quantity_available == 42
    assert level.aggregator_id == 6
    assert level.warehouse_id == "7"
    assert level.raw.get("StockLocationName") == "Main DC"


def test_shoppingfeed_map_stock_uses_store_as_warehouse():
    raw = load_fixture("stock", "shoppingfeed_stock.json")
    level = sf_map_stock(raw, aggregator_id=5, store_id="store-9")

    assert level.sku == "SF-SKU"
    assert level.quantity_available == 15
    assert level.warehouse_id == "store-9"
    assert level.platform_id == "9001"


def test_mirakl_map_stock_offer_fields():
    raw = load_fixture("stock", "mirakl_offer.json")
    level = mirakl_map_stock(raw, marketplace_id=44)

    assert level.sku == "MIR-SKU"
    assert level.quantity_available == 8
    assert level.platform_id == "555"
    assert level.marketplace_id == 44
