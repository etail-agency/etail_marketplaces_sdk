"""
Lengow aggregator client.

Handles authentication, pagination, and HTTP calls against the Lengow API.
Returns raw dict responses — all field mapping lives in mappers.py.

OpenAPI spec: specs/aggregators/lengow/openapi.json
API base URL:  https://api.lengow.io/
Docs:          https://developers.lengow.com/

Catalogue source: GET /v1.0/report/export
  Returns a pipe-separated CSV of the last marketplace report after product
  transmission to a marketplace.  Requires a feed_id (set on the constructor
  or passed directly to fetch_catalogue / fetch_raw_catalogue).
  Column names are feed-specific; map_product() does a best-effort mapping.
"""

from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import requests

from etail_marketplaces_sdk.aggregators.base import BaseAggregator
from etail_marketplaces_sdk.aggregators.lengow.mappers import (
    map_order,
    map_invoice,
    map_product,
    LENGOW_MARKETPLACE_MAPPING,
)
from etail_marketplaces_sdk.core.credentials import LengowCredentials
from etail_marketplaces_sdk.core.exceptions import AuthError, RateLimitError, ResourceNotFoundError
from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)

BASE_URL = "https://api.lengow.io/"


class LengowClient(BaseAggregator):
    """
    Lengow aggregator client.

    Supported streams: ORDERS, INVOICES, CATALOGUE

    Args:
        credentials:       LengowCredentials(access_token, secret)
        brand:             Brand object (used for invoice metadata)
        marketplace_id:    Optional static marketplace ID (overrides mapping lookup)
        marketplace_name:  Lengow marketplace slug (e.g. 'zalando_fr')
        tax_rate:          Default VAT rate as a percentage (e.g. Decimal('20'))
        feed_id:           Lengow feed ID used by fetch_catalogue / fetch_raw_catalogue.
                           Can also be passed directly to those methods.
    """

    aggregator_id = 3
    name = "Lengow"
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES, StreamType.CATALOGUE}

    def __init__(
        self,
        credentials: LengowCredentials,
        brand: Brand,
        marketplace_id: Optional[int] = None,
        marketplace_name: Optional[str] = None,
        tax_rate: Optional[Decimal] = None,
        feed_id: Optional[int] = None,
    ) -> None:
        super().__init__(credentials)
        self.brand = brand
        self.marketplace_id = marketplace_id
        self.marketplace_name = marketplace_name
        self.tax_rate = tax_rate if tax_rate is not None else Decimal("20")
        self.feed_id = feed_id

    # ------------------------------------------------------------------
    # Public stream methods
    # ------------------------------------------------------------------

    def fetch_orders(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [
            map_order(raw, self.aggregator_id, self.marketplace_id, self.brand)
            for raw in raw_orders
        ]

    def fetch_invoices(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [
            inv
            for raw in raw_orders
            if (inv := map_invoice(raw, self.aggregator_id, self.marketplace_id, self.brand, self.tax_rate)) is not None
        ]

    def fetch_order(self, order_id: str) -> object:
        raw = self._fetch_raw_specific_order(order_id)
        if not raw:
            raise ResourceNotFoundError("Order", order_id)
        raw = raw[0] if isinstance(raw, list) and raw else raw

        marketplace_name = raw.get("marketplace")
        mapping = LENGOW_MARKETPLACE_MAPPING.get(marketplace_name, {})
        marketplace_id = mapping.get("marketplace_id") or self.marketplace_id

        return map_order(raw, self.aggregator_id, marketplace_id, self.brand)

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return Lengow order payloads without normalisation.

        Each dict is the raw Lengow API record — identical to the ``raw`` field
        on each :class:`~etail_marketplaces_sdk.models.order.Order` returned by
        :meth:`fetch_orders`.

        Args:
            days_ago: Fetch orders from the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_orders(days_ago)

    def fetch_catalogue(
        self,
        feed_id: Optional[int] = None,
        nb_days_to_skip: Optional[int] = None,
        **kwargs,
    ) -> list:
        """Fetch the product catalogue from the Lengow report export.

        Calls ``GET /v1.0/report/export``, which returns the last marketplace
        report (pipe-separated CSV) after product transmission to a feed.
        Column names are feed-specific; mapping is best-effort.

        Args:
            feed_id:         Lengow feed ID.  Falls back to ``self.feed_id``
                             set on the constructor.
            nb_days_to_skip: Days to skip (e.g. ``1`` = yesterday's report).

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.product.Product`]
        """
        raw = self._fetch_raw_catalogue(feed_id=feed_id, nb_days_to_skip=nb_days_to_skip)
        return [map_product(row, self.aggregator_id, self.marketplace_id) for row in raw]

    def fetch_raw_catalogue(
        self,
        feed_id: Optional[int] = None,
        nb_days_to_skip: Optional[int] = None,
        **kwargs,
    ) -> list[dict]:
        """Return Lengow report rows as dicts without normalisation.

        Each dict corresponds to one CSV row from ``GET /v1.0/report/export``.
        Keys are the column headers from the report (feed-specific).

        Args:
            feed_id:         Lengow feed ID.  Falls back to ``self.feed_id``.
            nb_days_to_skip: Days to skip.

        Returns:
            list[dict]
        """
        return self._fetch_raw_catalogue(feed_id=feed_id, nb_days_to_skip=nb_days_to_skip)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _get_token(self) -> tuple[str, str]:
        payload = {
            "access_token": self.credentials.access_token,
            "secret": self.credentials.secret,
        }
        try:
            response = requests.post(BASE_URL + "access/get_token", data=payload, timeout=30)
            if response.status_code == 401:
                raise AuthError("Lengow: invalid credentials")
            response.raise_for_status()
            data = response.json()
            token = data.get("token")
            account_id = data.get("account_id")
            if not token or not account_id:
                raise AuthError("Lengow: token or account_id missing in auth response")
            return token, str(account_id)
        except requests.HTTPError as exc:
            raise AuthError(f"Lengow auth failed: {exc}") from exc

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        orders: list[dict] = []
        token, account_id = self._get_token()
        headers = {"Authorization": token}

        # Spec requires format: date-time (ISO 8601)
        from_dt = (datetime.now() - timedelta(days=days_ago)) if days_ago else None
        params: dict = {
            "account_id": account_id,
            "marketplace": self.marketplace_name,
            "page_size": 100,
        }
        if from_dt:
            params["marketplace_order_date_from"] = from_dt.strftime("%Y-%m-%dT%H:%M:%S")

        url: Optional[str] = BASE_URL + "v3.0/orders/"
        while url:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                orders.extend(data.get("results", []))
                url = data.get("next")
                params = {}
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("Lengow fetch_orders error: %s", exc)
                break

        return orders

    def _fetch_raw_catalogue(
        self,
        feed_id: Optional[int] = None,
        nb_days_to_skip: Optional[int] = None,
    ) -> list[dict]:
        fid = feed_id or self.feed_id
        if not fid:
            raise ValueError(
                "feed_id is required for Lengow catalogue fetch. "
                "Pass it to fetch_catalogue() or set it on the constructor."
            )

        token, account_id = self._get_token()
        headers = {"Authorization": token}
        params: dict = {"account_id": account_id, "feed_id": fid}
        if nb_days_to_skip is not None:
            params["nb_days_to_skip"] = nb_days_to_skip

        try:
            response = requests.get(
                BASE_URL + "v1.0/report/export",
                headers=headers,
                params=params,
                timeout=60,
            )
            if response.status_code == 429:
                raise RateLimitError()
            response.raise_for_status()
        except RateLimitError:
            raise
        except requests.RequestException as exc:
            logger.error("Lengow fetch_catalogue error: %s", exc)
            return []

        text = response.text.strip()
        if not text:
            return []

        reader = csv.DictReader(io.StringIO(text), delimiter="|")
        return [dict(row) for row in reader]

    def _fetch_raw_specific_order(self, order_id: str) -> list[dict]:
        token, account_id = self._get_token()
        headers = {"Authorization": token}
        params = {"account_id": account_id, "marketplace_order_id": order_id}
        orders: list[dict] = []

        url: Optional[str] = BASE_URL + "v3.0/orders/"
        while url:
            try:
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                orders.extend(data.get("results", []))
                url = data.get("next")
                params = {}
            except requests.RequestException as exc:
                logger.error("Lengow fetch_specific_order error: %s", exc)
                break

        return orders
