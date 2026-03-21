"""Shipment stream — ChannelEngine ``map_shipment`` (shipments API shape)."""

from __future__ import annotations

from etail_marketplaces_sdk.aggregators.channelengine.mappers import map_shipment
from etail_marketplaces_sdk.models.shipment import ShipmentStatus

from tests.support import load_fixture


def test_channelengine_map_shipment_carrier_and_lines():
    raw = load_fixture("shipments", "channelengine_shipment.json")
    sh = map_shipment(raw, aggregator_id=6, marketplace_id=0)

    assert sh is not None
    assert sh.shipment_id == "MS-TRK-1"
    assert sh.order_id == "CE-TRK"
    assert sh.carrier == "DHL"
    assert sh.tracking_number == "JJD123"
    assert sh.status == ShipmentStatus.DELIVERED
    assert sh.lines[0].sku == "W-SKU"
    assert sh.lines[0].platform_product_id == "CHAN-1"
