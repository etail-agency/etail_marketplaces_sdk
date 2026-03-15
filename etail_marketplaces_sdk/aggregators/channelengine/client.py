"""
ChannelEngine aggregator client.

Two operating modes, controlled by the ``orders_api`` constructor flag:

  orders_api=False  (default)
      Uses GET /v2/shipments — only CLOSED shipments are returned.
      Address data is not available in the response.
      Suitable for tenants that have /v2/shipments access.

  orders_api=True
      Uses GET /v2/orders — all statuses, full address, explicit VAT per line.
      Invoices are generated only for SHIPPED/CLOSED orders.
      Suitable for tenants (e.g. VNB) whose API key lacks /v2/shipments access.

Authentication is via an ``apikey`` query parameter.

OpenAPI spec: specs/aggregators/channelengine/openapi.json
API base URL:  https://{tenant}.channelengine.net/api
Docs:          https://api.channelengine.net/merchant
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import requests

from etail_marketplaces_sdk.aggregators.base import BaseAggregator
from etail_marketplaces_sdk.aggregators.channelengine.mappers import (
    map_invoice,
    map_invoice_from_orders_api,
    map_order,
    map_order_from_orders_api,
    map_product,
    map_stock_level,
)
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.core.exceptions import RateLimitError, ResourceNotFoundError
from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)


class ChannelEngineClient(BaseAggregator):
    """
    ChannelEngine aggregator client.

    Supported streams: ORDERS, INVOICES, SHIPMENTS, STOCK, CATALOGUE

    Args:
        credentials:       ApiKeyCredentials(api_key=...)
        base_url:          Tenant API base, e.g. 'https://demo.channelengine.net/api'
        brand:             Brand object (used for invoice metadata)
        marketplace_id:    Optional static marketplace ID
        marketplace_name:  Optional marketplace label
        tax_rate:          Default VAT rate as a percentage (e.g. Decimal('20'))
        orders_api:        When True, use /v2/orders instead of /v2/shipments
    """

    aggregator_id = 6
    name = "ChannelEngine"
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES, StreamType.SHIPMENTS, StreamType.STOCK, StreamType.CATALOGUE}

    def __init__(
        self,
        credentials: ApiKeyCredentials,
        base_url: str,
        brand: Brand,
        marketplace_id: Optional[int] = None,
        marketplace_name: Optional[str] = None,
        tax_rate: Optional[Decimal] = None,
        orders_api: bool = False,
    ) -> None:
        super().__init__(credentials)
        self.base_url = base_url.rstrip("/")
        self.brand = brand
        self.marketplace_id = marketplace_id
        self.marketplace_name = marketplace_name or "ChannelEngine"
        self.tax_rate = tax_rate if tax_rate is not None else Decimal("20")
        self.orders_api = orders_api

    # ------------------------------------------------------------------
    # Public stream methods
    # ------------------------------------------------------------------

    def fetch_orders(self, days_ago: Optional[int] = None, **kwargs) -> list:
        if self.orders_api:
            raw = self._fetch_raw_orders(days_ago)
            return [
                o
                for r in raw
                if (o := map_order_from_orders_api(r, self.aggregator_id, self.marketplace_id, self.brand)) is not None
            ]
        raw_shipments = self._fetch_raw_shipments(days_ago)
        return [
            order
            for s in raw_shipments
            if (order := map_order(s, self.aggregator_id, self.marketplace_id, self.brand)) is not None
        ]

    def fetch_invoices(self, days_ago: Optional[int] = None, **kwargs) -> list:
        if self.orders_api:
            raw = self._fetch_raw_orders(days_ago)
            return [
                inv
                for r in raw
                if (inv := map_invoice_from_orders_api(
                    r, self.aggregator_id, self.marketplace_id, self.brand, self.tax_rate
                )) is not None
            ]
        raw_shipments = self._fetch_raw_shipments(days_ago)
        return [
            inv
            for s in raw_shipments
            if (inv := map_invoice(s, self.aggregator_id, self.marketplace_id, self.brand, self.tax_rate)) is not None
        ]

    def fetch_shipments(self, days_ago: Optional[int] = None, **kwargs) -> list:
        from etail_marketplaces_sdk.aggregators.channelengine.mappers import map_shipment
        raw_shipments = self._fetch_raw_shipments(days_ago)
        return [
            s
            for raw in raw_shipments
            if (s := map_shipment(raw, self.aggregator_id, self.marketplace_id)) is not None
        ]

    def fetch_order(self, order_id: str) -> object:
        if self.orders_api:
            raw = self._fetch_order_by_channel_order_no(order_id)
            if not raw:
                raise ResourceNotFoundError("Order", order_id)
            return map_order_from_orders_api(raw, self.aggregator_id, self.marketplace_id, self.brand)
        raw = self._fetch_shipment_by_order_no(order_id)
        if not raw:
            raise ResourceNotFoundError("Order", order_id)
        return map_order(raw, self.aggregator_id, self.marketplace_id, self.brand)

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return ChannelEngine order payloads without normalisation.

        Respects the ``orders_api`` flag set at construction time:

        - ``orders_api=False``: returns records from ``GET /v2/shipments``.
        - ``orders_api=True``:  returns records from ``GET /v2/orders``.

        Each dict is identical to the ``raw`` field on each
        :class:`~etail_marketplaces_sdk.models.order.Order` returned by
        :meth:`fetch_orders`.

        Args:
            days_ago: Fetch records from the last N days.

        Returns:
            list[dict]
        """
        if self.orders_api:
            return self._fetch_raw_orders(days_ago)
        return self._fetch_raw_shipments(days_ago)

    def fetch_raw_shipments(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return ChannelEngine shipment payloads from ``GET /v2/shipments`` without normalisation.

        Always uses the ``/v2/shipments`` endpoint regardless of the ``orders_api``
        flag.  Useful when you need the raw shipment record even on a tenant that
        has ``orders_api=True`` set.

        Args:
            days_ago: Fetch shipments from the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_shipments(days_ago)

    def fetch_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list:
        """Fetch stock levels across all warehouses as canonical :class:`StockLevel` objects.

        Automatically lists all configured stock locations first, then queries
        ``GET /v2/offer/stock`` for each, enriching each record with the
        location name.

        Args:
            skus: Optional list of merchant SKUs to filter on.  Omit to fetch
                  stock for every product.

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.stock.StockLevel`]
        """
        locations = self._fetch_stock_locations()
        location_map = {loc["Id"]: loc.get("Name") for loc in locations}
        raw_records = self._fetch_raw_stock(
            skus=skus,
            stock_location_ids=list(location_map.keys()),
        )
        return [
            map_stock_level(r, self.aggregator_id, self.marketplace_id, location_map.get(r.get("StockLocationId")))
            for r in raw_records
        ]

    def fetch_raw_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list[dict]:
        """Return raw stock records from ``GET /v2/offer/stock`` without normalisation.

        Each dict matches the ``MerchantOfferGetStockResponse`` schema:
        ``MerchantProductNo``, ``StockLocationId``, ``Stock``, ``UpdatedAt``.
        A ``StockLocationName`` key is added from ``GET /v2/stocklocations``.

        Args:
            skus: Optional list of merchant SKUs to filter on.

        Returns:
            list[dict]
        """
        locations = self._fetch_stock_locations()
        location_map = {loc["Id"]: loc.get("Name") for loc in locations}
        raw = self._fetch_raw_stock(
            skus=skus,
            stock_location_ids=list(location_map.keys()),
        )
        for record in raw:
            loc_id = record.get("StockLocationId")
            record["StockLocationName"] = location_map.get(loc_id)
        return raw

    def fetch_catalogue(
        self,
        updated_since=None,
        skus: Optional[list[str]] = None,
        **kwargs,
    ) -> list:
        """Fetch all merchant products as canonical :class:`Product` objects.

        Calls ``GET /v2/products`` and paginates through all pages.

        Args:
            updated_since: Ignored by the ChannelEngine products endpoint (no
                           server-side date filter is available). Pass ``skus``
                           to narrow the result set instead.
            skus:          Optional list of ``MerchantProductNo`` values to
                           retrieve.

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.product.Product`]
        """
        raw = self._fetch_raw_catalogue(skus=skus)
        return [map_product(r, self.aggregator_id, self.marketplace_id) for r in raw]

    def fetch_raw_catalogue(
        self,
        updated_since=None,
        skus: Optional[list[str]] = None,
        **kwargs,
    ) -> list[dict]:
        """Return raw product records from ``GET /v2/products`` without normalisation.

        Each dict matches the ``MerchantProductResponse`` schema — see the
        OpenAPI spec at ``specs/aggregators/channelengine/openapi.json``.

        Args:
            updated_since: Ignored (no server-side date filter available).
            skus:          Optional list of ``MerchantProductNo`` values.

        Returns:
            list[dict]
        """
        return self._fetch_raw_catalogue(skus=skus)

    def fetch_invoice_for_order(self, order_id: str) -> Optional[object]:
        """Fetch a single order and return its Invoice, or None if not yet shipped."""
        if self.orders_api:
            raw = self._fetch_order_by_channel_order_no(order_id)
            if not raw:
                raise ResourceNotFoundError("Order", order_id)
            return map_invoice_from_orders_api(
                raw, self.aggregator_id, self.marketplace_id, self.brand, self.tax_rate
            )
        raw = self._fetch_shipment_by_order_no(order_id)
        if not raw:
            raise ResourceNotFoundError("Order", order_id)
        return map_invoice(raw, self.aggregator_id, self.marketplace_id, self.brand, self.tax_rate)

    # ------------------------------------------------------------------
    # Private HTTP helpers — /v2/shipments/merchant
    # ------------------------------------------------------------------

    def _fetch_raw_shipments(self, days_ago: Optional[int] = None) -> list[dict]:
        shipments: list[dict] = []
        from_date = datetime.now(timezone.utc) - timedelta(days=days_ago or 30)
        page = 1

        while True:
            params: dict = {
                "apikey": self.credentials.api_key,
                "fromShipmentDate": from_date.isoformat(),
                "page": page,
            }
            try:
                response = requests.get(
                    f"{self.base_url}/v2/shipments/merchant", params=params, timeout=30
                )
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()

                batch = data.get("Content", [])
                shipments.extend(batch)

                total = data.get("TotalCount", 0)
                if len(shipments) >= total or not batch:
                    break
                page += 1
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("ChannelEngine fetch_shipments error: %s", exc)
                break

        return shipments

    def _fetch_shipment_by_order_no(self, order_no: str) -> Optional[dict]:
        params = {"apikey": self.credentials.api_key, "channelOrderNos": [order_no]}
        try:
            response = requests.get(
                f"{self.base_url}/v2/shipments/merchant", params=params, timeout=30
            )
            response.raise_for_status()
            content = response.json().get("Content", [])
            return content[0] if content else None
        except requests.RequestException as exc:
            logger.error("ChannelEngine fetch_shipment_by_order_no error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private HTTP helpers — /v2/orders
    # ------------------------------------------------------------------

    def _fetch_raw_orders(
        self,
        days_ago: Optional[int] = None,
        statuses: Optional[list[str]] = None,
    ) -> list[dict]:
        """Paginate through GET /v2/orders and return all records."""
        results: list[dict] = []
        from_date = datetime.now(timezone.utc) - timedelta(days=days_ago or 30)

        params: dict = {
            "apikey": self.credentials.api_key,
            "fromDate": from_date.isoformat(),
            "page": 1,
        }
        if statuses:
            params["statuses"] = statuses

        while True:
            try:
                response = requests.get(f"{self.base_url}/v2/orders", params=params, timeout=30)
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                batch = data.get("Content", [])
                results.extend(batch)

                total = data.get("TotalCount", 0)
                if len(results) >= total or not batch:
                    break
                params = {"apikey": self.credentials.api_key, "page": params["page"] + 1}
                if statuses:
                    params["statuses"] = statuses
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("ChannelEngine fetch_orders error: %s", exc)
                break

        return results

    def _fetch_order_by_channel_order_no(self, order_no: str) -> Optional[dict]:
        params = {"apikey": self.credentials.api_key, "channelOrderNos": [order_no]}
        try:
            response = requests.get(f"{self.base_url}/v2/orders", params=params, timeout=30)
            response.raise_for_status()
            content = response.json().get("Content", [])
            return content[0] if content else None
        except requests.RequestException as exc:
            logger.error("ChannelEngine fetch_order_by_channel_order_no error: %s", exc)
            return None

    # ------------------------------------------------------------------
    # Private HTTP helpers — stock
    # ------------------------------------------------------------------

    def _fetch_stock_locations(self) -> list[dict]:
        """Return all configured stock locations from ``GET /v2/stocklocations``.

        Each dict has ``Id``, ``Name``, ``CountryIso``.  The IDs are required
        as a parameter when calling ``GET /v2/offer/stock``.
        """
        try:
            response = requests.get(
                f"{self.base_url}/v2/stocklocations",
                params={"apikey": self.credentials.api_key},
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("Content", [])
        except requests.RequestException as exc:
            logger.error("ChannelEngine fetch_stock_locations error: %s", exc)
            return []

    def _fetch_raw_stock(
        self,
        skus: Optional[list[str]] = None,
        stock_location_ids: Optional[list[int]] = None,
    ) -> list[dict]:
        """Paginate through ``GET /v2/offer/stock`` and return all records.

        ``stockLocationIds`` is required by the API — pass an explicit list or
        call :meth:`_fetch_stock_locations` first.  ``pageIndex`` is 0-based,
        ``pageSize`` is capped at 500 by the API.
        """
        if not stock_location_ids:
            return []

        records: list[dict] = []
        page_index = 0
        page_size = 500

        while True:
            params: dict = {
                "apikey": self.credentials.api_key,
                "stockLocationIds": stock_location_ids,
                "pageIndex": page_index,
                "pageSize": page_size,
            }
            if skus:
                params["skus"] = skus

            try:
                response = requests.get(
                    f"{self.base_url}/v2/offer/stock", params=params, timeout=60
                )
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()

                batch = data.get("Content", [])
                records.extend(batch)

                total = data.get("TotalCount", 0)
                if len(records) >= total or not batch:
                    break
                page_index += 1
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("ChannelEngine fetch_stock error: %s", exc)
                break

        return records

    # ------------------------------------------------------------------
    # Private HTTP helpers — /v2/products
    # ------------------------------------------------------------------

    def _fetch_raw_catalogue(
        self,
        skus: Optional[list[str]] = None,
    ) -> list[dict]:
        """Paginate through ``GET /v2/products`` and return all product records.

        ``page`` is 1-based.  ``pageSize`` defaults to 100 (max allowed by the
        API is not specified; 100 is safe).

        Args:
            skus: Optional list of ``MerchantProductNo`` values to filter on.
        """
        products: list[dict] = []
        params: dict = {
            "apikey": self.credentials.api_key,
            "pageSize": 100,
            "page": 1,
        }
        if skus:
            params["merchantProductNoList"] = skus

        while True:
            try:
                response = requests.get(
                    f"{self.base_url}/v2/products",
                    params=params,
                    timeout=30,
                )
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()

                batch = data.get("Content", [])
                products.extend(batch)

                total = data.get("TotalCount", 0)
                if len(products) >= total or not batch:
                    break
                params["page"] += 1
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("ChannelEngine fetch_catalogue error: %s", exc)
                break

        return products
