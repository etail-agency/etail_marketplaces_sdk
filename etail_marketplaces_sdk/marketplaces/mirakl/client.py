"""
Mirakl marketplace client.

Mirakl powers many white-label marketplaces (Galeries Lafayette, Leroy Merlin,
Fnac, Darty, etc.). Each operator has their own base URL; auth is via an
API key header (Authorization: <api_key>).

OpenAPI spec: specs/marketplaces/mirakl/openapi.json
API base URL:  https://{operator}.mirakl.net/api
Docs:          https://help.mirakl.net/help/api-doc/operator/

NOTE: This is a scaffold. Implement mappers.py once the target operator's
      OpenAPI spec has been added to specs/marketplaces/mirakl/.
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
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_order, map_invoice
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)


class MiraklClient(BaseMarketplace):
    """
    Generic Mirakl marketplace client.

    One instance = one Mirakl operator (e.g. Galeries Lafayette).
    Pass the operator-specific `base_url` and `marketplace_id`.

    Supported streams: ORDERS, INVOICES, STOCK, CATALOGUE

    Args:
        credentials:    ApiKeyCredentials(api_key=...)
        base_url:       Operator API base, e.g. 'https://galerieslafayette.mirakl.net/api'
        marketplace_id: Internal DB marketplace ID for this operator
        brand:          Brand object (used for invoice metadata)
        name:           Operator display name (e.g. 'Galeries Lafayette')
        country:        ISO-3166-1 alpha-2 country code (default 'FR')
        tax_rate:       Default VAT rate as a percentage (e.g. Decimal('20'))
    """

    supported_streams = {StreamType.ORDERS, StreamType.INVOICES, StreamType.STOCK, StreamType.CATALOGUE}

    def __init__(
        self,
        credentials: ApiKeyCredentials,
        base_url: str,
        marketplace_id: int,
        brand: Brand,
        name: str = "Mirakl",
        country: str = "FR",
        tax_rate: Optional[Decimal] = None,
    ) -> None:
        super().__init__(credentials)
        self.base_url = base_url.rstrip("/")
        self.marketplace_id = marketplace_id
        self.brand = brand
        self.name = name
        self.country = country
        self.tax_rate = tax_rate if tax_rate is not None else Decimal("20")

    def _headers(self) -> dict:
        return {"Authorization": self.credentials.api_key, "Accept": "application/json"}

    # ------------------------------------------------------------------
    # Orders  (Mirakl Orders API — OR11)
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
        url = f"{self.base_url}/api/orders/{order_id}"
        response = requests.get(url, headers=self._headers(), timeout=30)
        if response.status_code == 404:
            raise ResourceNotFoundError("Order", order_id)
        response.raise_for_status()
        return map_order(response.json(), self.marketplace_id, self.brand)

    def fetch_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list:
        """Fetch inventory levels via Mirakl Offers API (OF21)."""
        from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_stock_level
        raw = self._fetch_raw_offers(skus)
        return [map_stock_level(r, self.marketplace_id) for r in raw]

    def fetch_catalogue(self, updated_since=None, **kwargs) -> list:
        """Fetch product listings via Mirakl Products API (P11)."""
        from etail_marketplaces_sdk.marketplaces.mirakl.mappers import map_product
        raw = self._fetch_raw_products(updated_since)
        return [map_product(r, self.marketplace_id) for r in raw]

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return Mirakl order payloads without normalisation.

        Each dict is the raw Mirakl OR11 API record — identical to the ``raw``
        field on each :class:`~etail_marketplaces_sdk.models.order.Order` returned
        by :meth:`fetch_orders`.

        Args:
            days_ago: Fetch orders from the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_orders(days_ago)

    def fetch_raw_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list[dict]:
        """Return Mirakl offer payloads without normalisation (Offers API OF21).

        Args:
            skus: Optional list of SKUs to filter. Fetches all if omitted.

        Returns:
            list[dict]
        """
        return self._fetch_raw_offers(skus)

    def fetch_raw_catalogue(self, updated_since=None, **kwargs) -> list[dict]:
        """Return Mirakl product payloads without normalisation (Products API P11).

        Args:
            updated_since: Only return products updated after this date.

        Returns:
            list[dict]
        """
        return self._fetch_raw_products(updated_since)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        orders: list[dict] = []
        params: dict = {"max": 100, "paginate": "true"}
        if days_ago:
            from_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            params["start_update_date"] = from_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        url: Optional[str] = f"{self.base_url}/api/orders"
        while url:
            try:
                response = requests.get(url, headers=self._headers(), params=params, timeout=30)
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                orders.extend(data.get("orders", []))
                url = data.get("next_page_token")
                params = {}
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("Mirakl fetch_orders error: %s", exc)
                break
        return orders

    def _fetch_raw_offers(self, skus: Optional[list[str]] = None) -> list[dict]:
        params: dict = {"max": 100}
        if skus:
            params["shop_sku"] = ",".join(skus)
        try:
            response = requests.get(
                f"{self.base_url}/api/offers",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("offers", [])
        except requests.RequestException as exc:
            logger.error("Mirakl fetch_offers error: %s", exc)
            return []

    def _fetch_raw_products(self, updated_since=None) -> list[dict]:
        params: dict = {"max": 100}
        if updated_since:
            params["last_update_date"] = updated_since.isoformat()
        try:
            response = requests.get(
                f"{self.base_url}/api/products",
                headers=self._headers(),
                params=params,
                timeout=30,
            )
            response.raise_for_status()
            return response.json().get("products", [])
        except requests.RequestException as exc:
            logger.error("Mirakl fetch_products error: %s", exc)
            return []
