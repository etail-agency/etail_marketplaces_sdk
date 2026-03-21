"""Catalogue stream — ``map_product`` mappers (no HTTP)."""

from __future__ import annotations

from decimal import Decimal

from etail_marketplaces_sdk.aggregators.channelengine.mappers import map_product as ce_map_product
from etail_marketplaces_sdk.aggregators.lengow.mappers import map_product as lengow_map_product
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_product as sf_map_product
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_product as mirakl_map_product

from tests.support import load_fixture


def test_channelengine_map_product_images_and_extra_data():
    raw = load_fixture("catalogue", "channelengine_product.json")
    p = ce_map_product(raw, aggregator_id=6, marketplace_id=0)

    assert p.sku == "P-SKU"
    assert p.name == "CE Product"
    assert p.ean == "1234567890123"
    assert p.price_incl_vat == Decimal("29.99")
    assert p.brand == "Acme"
    assert len(p.images) == 1
    assert p.images[0].url == "https://example.com/a.jpg"
    assert any(a.name == "foo" and a.value == "bar" for a in p.attributes)


def test_shoppingfeed_map_product_embedded_brand_category():
    raw = load_fixture("catalogue", "shoppingfeed_product.json")
    p = sf_map_product(raw, aggregator_id=5, store_id="st1")

    assert p.sku == "CAT-SF"
    assert p.ean == "5901234123457"
    assert p.brand == "SFBrand"
    assert p.category == "Tools"
    assert p.is_active is True
    assert len(p.images) == 1


def test_lengow_map_product_csv_row_picks_common_columns():
    raw = load_fixture("catalogue", "lengow_product_row.json")
    p = lengow_map_product(raw, aggregator_id=3, marketplace_id=1)

    assert p.sku == "LG-1"
    assert p.name == "Lengow item"
    assert p.ean == "4006381333931"
    assert p.price_incl_vat == Decimal("12.50")
    assert p.brand == "LenBrand"
    assert any(attr.name == "custom_attr" for attr in p.attributes)


def test_mirakl_map_product_ean_from_references():
    raw = load_fixture("catalogue", "mirakl_offer.json")
    p = mirakl_map_product(raw, marketplace_id=2)

    assert p.sku == "MRK-P"
    assert p.platform_id == "PLATFORM-REF"
    assert p.ean == "111"
    assert p.price_incl_vat == Decimal("9.99")
    assert p.category == "CAT"
