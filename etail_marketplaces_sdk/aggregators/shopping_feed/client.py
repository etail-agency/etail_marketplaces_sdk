"""
ShoppingFeed aggregator client.

Handles authentication, page-based pagination, and HTTP calls.
Returns raw dict responses — all field mapping lives in mappers.py.

OpenAPI spec: specs/aggregators/shopping_feed/openapi.json
API base URL:  https://api.shopping-feed.com/v1/
Docs:          https://merchant-api-doc.shopping-feed.com/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import requests

from etail_marketplaces_sdk.aggregators.base import BaseAggregator
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_order, map_invoice
from etail_marketplaces_sdk.core.credentials import BearerCredentials
from etail_marketplaces_sdk.core.exceptions import RateLimitError, ResourceNotFoundError
from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)


class ShoppingFeedClient(BaseAggregator):
    """
    ShoppingFeed aggregator client.

    Supported streams: ORDERS, INVOICES

    Args:
        credentials:  BearerCredentials(token=api_token)
        store_id:     ShoppingFeed store identifier
        brand:        Brand object (used for invoice metadata)
        tax_rate:     Default VAT rate as a percentage (e.g. Decimal('20'))
    """

    aggregator_id = 4
    name = "ShoppingFeed"
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES}

    def __init__(
        self,
        credentials: BearerCredentials,
        store_id: str,
        brand: Brand,
        tax_rate: Decimal = Decimal("20"),
    ) -> None:
        super().__init__(credentials)
        self.store_id = store_id
        self.brand = brand
        self.tax_rate = tax_rate
        self._api_url = f"https://api.shopping-feed.com/v1/store/{store_id}/order"
        self._headers = {"Authorization": f"Bearer {credentials.token}"}

    # ------------------------------------------------------------------
    # Public stream methods
    # ------------------------------------------------------------------

    def fetch_orders(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [map_order(raw, self.aggregator_id, self.brand) for raw in raw_orders]

    def fetch_invoices(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [
            inv
            for raw in raw_orders
            if (inv := map_invoice(raw, self.aggregator_id, self.brand, self.tax_rate)) is not None
        ]

    def fetch_order(self, order_id: str) -> object:
        raw = self._fetch_raw_specific_order(order_id)
        return map_order(raw, self.aggregator_id, self.brand)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        orders: list[dict] = []
        cutoff: Optional[datetime] = None
        if days_ago is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(days=days_ago)

        params: dict = {"page": 1, "limit": 100}

        while True:
            response = requests.get(self._api_url, headers=self._headers, params=params, timeout=30)
            if response.status_code == 429:
                raise RateLimitError()
            response.raise_for_status()
            data = response.json()

            page_orders = data.get("_embedded", {}).get("order", [])

            if cutoff:
                for order in page_orders:
                    created_at = datetime.fromisoformat(order["createdAt"].replace("Z", "+00:00"))
                    if created_at >= cutoff:
                        orders.append(order)
                    else:
                        return orders
            else:
                orders.extend(page_orders)

            if params["page"] >= data.get("pages", 1):
                break
            params["page"] += 1

        return orders

    def _fetch_raw_specific_order(self, order_id: str) -> dict:
        params = {"page": 1, "limit": 100, "reference": order_id}
        response = requests.get(self._api_url, headers=self._headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        orders = data.get("_embedded", {}).get("order", [])
        if not orders:
            raise ResourceNotFoundError("Order", order_id)
        return orders[0]
