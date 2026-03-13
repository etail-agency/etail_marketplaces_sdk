"""
ManoMano marketplace client.

ManoMano is a direct marketplace (not an aggregator) — it has its own Partner
API authenticated via an x-api-key header.

OpenAPI spec: specs/marketplaces/manomano/openapi.json
API base URL:  https://partnersapi.manomano.com
Docs:          https://developer.manomano.com/
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Optional

import requests

from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials
from etail_marketplaces_sdk.core.exceptions import RateLimitError, ResourceNotFoundError
from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.marketplaces.base import BaseMarketplace
from etail_marketplaces_sdk.marketplaces.manomano.mappers import map_order, map_invoice
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)

BASE_URL = "https://partnersapi.manomano.com"


class ManomanoClient(BaseMarketplace):
    """
    ManoMano marketplace client.

    Migrated from backend/app/services/order_integration/aggregators/manomano.py
    and reclassified as a Marketplace (not an aggregator).

    Supported streams: ORDERS, INVOICES

    Args:
        credentials:   ApiKeyCredentials(api_key=...)
        contract_id:   ManoMano seller contract ID
        brand:         Brand object (used for invoice metadata)
        tax_rate:      Default VAT rate as a percentage (e.g. Decimal('20'))
        country:       ISO-3166-1 alpha-2 country code (default 'FR')
    """

    marketplace_id = 259
    name = "ManoMano"
    supported_streams = {StreamType.ORDERS, StreamType.INVOICES}

    def __init__(
        self,
        credentials: ApiKeyCredentials,
        contract_id: str,
        brand: Brand,
        tax_rate: Optional[Decimal] = None,
        country: str = "FR",
    ) -> None:
        super().__init__(credentials)
        self.contract_id = contract_id
        self.brand = brand
        self.tax_rate = tax_rate if tax_rate is not None else Decimal("20")
        self.country = country

    # ------------------------------------------------------------------
    # Public stream methods
    # ------------------------------------------------------------------

    def fetch_orders(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [map_order(raw, self.marketplace_id, self.brand) for raw in raw_orders]

    def fetch_invoices(self, days_ago: Optional[int] = None, **kwargs) -> list:
        raw_orders = self._fetch_raw_orders(days_ago)
        return [
            inv
            for raw in raw_orders
            if (inv := map_invoice(raw, self.marketplace_id, self.brand, self.tax_rate)) is not None
        ]

    def fetch_order(self, order_id: str) -> object:
        raw_list = self._fetch_raw_specific_order(order_id)
        if not raw_list:
            raise ResourceNotFoundError("Order", order_id)
        raw = raw_list[0] if isinstance(raw_list, list) else raw_list
        return map_order(raw, self.marketplace_id, self.brand)

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return ManoMano order payloads without normalisation.

        Each dict is the raw ManoMano Partner API record — identical to the ``raw``
        field on each :class:`~etail_marketplaces_sdk.models.order.Order` returned
        by :meth:`fetch_orders`.

        Args:
            days_ago: Fetch orders from the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_orders(days_ago)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _build_headers(self) -> dict:
        return {
            "Accept": "application/json",
            "x-thirdparty-name": "etail-marketplaces-sdk",
            "x-api-key": self.credentials.api_key,
        }

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        orders: list[dict] = []
        now_utc = datetime.now(timezone.utc)
        date_from = (now_utc - timedelta(days=days_ago or 7)).replace(microsecond=0)
        date_from_str = date_from.isoformat().replace("+00:00", "Z")

        params: dict = {
            "seller_contract_id": self.contract_id,
            "created_at_start": date_from_str,
            "limit": 30,
        }
        url: Optional[str] = f"{BASE_URL}/orders/v1/orders"

        while url:
            try:
                response = requests.get(url, headers=self._build_headers(), params=params, timeout=30)
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                orders.extend(data.get("content", []))

                next_link = data.get("pagination", {}).get("links", {}).get("next")
                url = f"{BASE_URL}{next_link}" if next_link else None
                params = {}
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("ManoMano fetch_orders error: %s", exc)
                break

        return orders

    def _fetch_raw_specific_order(self, order_id: str) -> list[dict]:
        params = {
            "seller_contract_id": self.contract_id,
            "order_reference": order_id,
        }
        try:
            response = requests.get(
                f"{BASE_URL}/orders/v1/orders",
                headers=self._build_headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("content", [])
        except requests.RequestException as exc:
            logger.error("ManoMano fetch_specific_order error: %s", exc)
            return []
