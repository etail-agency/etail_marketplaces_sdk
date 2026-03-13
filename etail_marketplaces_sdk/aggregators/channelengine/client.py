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
)
from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.core.exceptions import RateLimitError, ResourceNotFoundError
from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)


class ChannelEngineClient(BaseAggregator):
    """
    ChannelEngine aggregator client.

    Supported streams: ORDERS, INVOICES, SHIPMENTS

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
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES, StreamType.SHIPMENTS}

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
