"""
ShoppingFeed aggregator client.

Handles authentication, page-based pagination, and HTTP calls.
Returns raw dict responses — all field mapping lives in mappers.py.

OpenAPI specs: specs/aggregators/shopping_feed/order.yml  (orders / list / filter)
               specs/aggregators/shopping_feed/auth.yml   (Bearer token auth)
API base URL:  https://api.shopping-feed.com/v1/
Docs:          https://developer.shopping-feed.com/order-api
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import requests

from etail_marketplaces_sdk.aggregators.base import BaseAggregator
from etail_marketplaces_sdk.aggregators.shopping_feed.mappers import map_order, map_invoice, map_stock_level
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
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES, StreamType.STOCK}

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

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return ShoppingFeed order payloads without normalisation.

        Each dict is the raw ShoppingFeed API record — identical to the ``raw``
        field on each :class:`~etail_marketplaces_sdk.models.order.Order` returned
        by :meth:`fetch_orders`.

        Args:
            days_ago: Fetch orders from the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_orders(days_ago)

    def fetch_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list:
        """Fetch inventory levels as canonical :class:`StockLevel` objects.

        Calls ``GET /v1/catalog/{catalogId}/inventory`` — the same catalog ID
        as the store ID passed to the constructor.

        Args:
            skus: Optional list of product references (SKUs) to filter on.

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.stock.StockLevel`]
        """
        raw = self._fetch_raw_stock(skus=skus)
        return [map_stock_level(r, self.aggregator_id, self.store_id) for r in raw]

    def fetch_raw_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list[dict]:
        """Return raw inventory records from ``GET /v1/catalog/{catalogId}/inventory``.

        Each dict contains ``id`` (inventory ID), ``reference`` (SKU),
        ``quantity``, and ``updatedAt``.

        Args:
            skus: Optional list of product references to filter on.

        Returns:
            list[dict]
        """
        return self._fetch_raw_stock(skus=skus)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        orders: list[dict] = []
        params: dict = {"page": 1, "limit": 100}

        if days_ago is not None:
            since = datetime.now(timezone.utc) - timedelta(days=days_ago)
            # The spec's `since` param accepts ISO 8601 (order.yml: GET /v1/store/{storeId}/order)
            params["since"] = since.strftime("%Y-%m-%dT%H:%M:%S")

        while True:
            response = requests.get(self._api_url, headers=self._headers, params=params, timeout=30)
            if response.status_code == 429:
                raise RateLimitError()
            response.raise_for_status()
            data = response.json()

            orders.extend(data.get("_embedded", {}).get("order", []))

            if params["page"] >= data.get("pages", 1):
                break
            params["page"] += 1

        return orders

    def _fetch_raw_stock(self, skus: Optional[list[str]] = None) -> list[dict]:
        """Paginate through ``GET /v1/catalog/{catalogId}/inventory`` and return all records."""
        inventory: list[dict] = []
        url = f"https://api.shopping-feed.com/v1/catalog/{self.store_id}/inventory"
        params: dict = {"page": 1, "limit": 100}
        if skus:
            params["reference"] = ",".join(skus)

        while True:
            response = requests.get(url, headers=self._headers, params=params, timeout=30)
            if response.status_code == 429:
                raise RateLimitError()
            response.raise_for_status()
            data = response.json()

            inventory.extend(data.get("_embedded", {}).get("inventory", []))

            if params["page"] >= data.get("pages", 1):
                break
            params["page"] += 1

        return inventory

    def _fetch_raw_specific_order(self, order_id: str) -> dict:
        params = {"page": 1, "limit": 100, "reference": order_id}
        response = requests.get(self._api_url, headers=self._headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        orders = data.get("_embedded", {}).get("order", [])
        if not orders:
            raise ResourceNotFoundError("Order", order_id)
        return orders[0]
