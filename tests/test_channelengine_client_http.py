"""ChannelEngine client — HTTP behaviour with ``responses`` (no live API)."""

from __future__ import annotations

import json
from urllib.parse import parse_qs, urlparse

import pytest
import responses

from etail_marketplaces_sdk.aggregators.channelengine.client import ChannelEngineClient
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.core.exceptions import RateLimitError
from etail_marketplaces_sdk.models.brand import Brand


@pytest.fixture
def ce_orders_client(brand: Brand) -> ChannelEngineClient:
    return ChannelEngineClient(
        credentials=ApiKeyCredentials(api_key="test-key"),
        base_url="https://tenant.example/api",
        brand=brand,
        orders_api=True,
    )


@pytest.fixture
def ce_catalogue_client(brand: Brand) -> ChannelEngineClient:
    return ChannelEngineClient(
        credentials=ApiKeyCredentials(api_key="test-key"),
        base_url="https://tenant.example/api",
        brand=brand,
        orders_api=False,
    )


@responses.activate
def test_fetch_raw_orders_follows_pagination(ce_orders_client: ChannelEngineClient) -> None:
    """Second request is issued when ``TotalCount`` is greater than first batch."""

    def callback(request):
        qs = parse_qs(urlparse(request.url).query)
        page = qs.get("page", ["1"])[0]
        if page == "1":
            body = {"Content": [{"ChannelOrderNo": "first"}], "TotalCount": 2}
        else:
            body = {"Content": [{"ChannelOrderNo": "second"}], "TotalCount": 2}
        return (200, {}, json.dumps(body))

    responses.add_callback(
        responses.GET,
        f"{ce_orders_client.base_url}/v2/orders",
        callback=callback,
        content_type="application/json",
    )

    rows = ce_orders_client._fetch_raw_orders(days_ago=1)

    assert len(rows) == 2
    assert rows[0]["ChannelOrderNo"] == "first"
    assert rows[1]["ChannelOrderNo"] == "second"
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_raw_orders_raises_on_429(ce_orders_client: ChannelEngineClient) -> None:
    responses.get(
        f"{ce_orders_client.base_url}/v2/orders",
        status=429,
    )

    with pytest.raises(RateLimitError):
        ce_orders_client._fetch_raw_orders(days_ago=1)


@responses.activate
def test_fetch_raw_catalogue_follows_pagination(ce_catalogue_client: ChannelEngineClient) -> None:
    """``GET /v2/products`` uses page + TotalCount like orders."""

    def callback(request):
        qs = parse_qs(urlparse(request.url).query)
        page = qs.get("page", ["1"])[0]
        if page == "1":
            body = {"Content": [{"MerchantProductNo": "p1"}], "TotalCount": 2}
        else:
            body = {"Content": [{"MerchantProductNo": "p2"}], "TotalCount": 2}
        return (200, {}, json.dumps(body))

    responses.add_callback(
        responses.GET,
        f"{ce_catalogue_client.base_url}/v2/products",
        callback=callback,
        content_type="application/json",
    )

    rows = ce_catalogue_client._fetch_raw_catalogue()

    assert len(rows) == 2
    assert rows[0]["MerchantProductNo"] == "p1"
    assert rows[1]["MerchantProductNo"] == "p2"
    assert len(responses.calls) == 2


@responses.activate
def test_fetch_raw_catalogue_raises_on_429(ce_catalogue_client: ChannelEngineClient) -> None:
    responses.get(
        f"{ce_catalogue_client.base_url}/v2/products",
        status=429,
    )

    with pytest.raises(RateLimitError):
        ce_catalogue_client._fetch_raw_catalogue()
