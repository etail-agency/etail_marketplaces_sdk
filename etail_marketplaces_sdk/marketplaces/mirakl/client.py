"""
Mirakl marketplace client — Seller API.

Mirakl powers many white-label marketplaces (Galeries Lafayette, Leroy Merlin,
Fnac, Darty, …).  Each operator has their own base URL; auth is via a shop API
key sent in the ``Authorization`` header.

OpenAPI spec: specs/marketplaces/mirakl/seller_openapi.json
API base URL:  https://{operator}.mirakl.net/api
Docs:          https://developer.mirakl.com/content/product/mmp/rest/seller/openapi3

Streams implemented:
  ORDERS    — OR11  GET /api/orders         (offset pagination, max 100)
  INVOICES  — OR11  GET /api/orders         (same feed; filters for shipped states)
  STOCK     — OF21  GET /api/offers         (offset pagination, max 100)
  CATALOGUE — OF21  GET /api/offers         (same feed; maps to Product model)

Notes:
  - All four streams share the same underlying paginator; only the mapper differs
    for STOCK vs CATALOGUE.
  - For large volumes Mirakl recommends the async export APIs (OR13/OF52).  The
    synchronous endpoints are fine for regular differential polling (≤ 5 min) and
    for catalogues with fewer than a few thousand offers.
  - ``start_update_date`` on OR11 is the recommended differential filter; Mirakl
    applies an internal delta to avoid missed orders due to clock skew.
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
from etail_marketplaces_sdk.marketplaces.mirakl.mappers import (
    map_invoice,
    map_order,
    map_product,
    map_stock_level,
)
from etail_marketplaces_sdk.models.brand import Brand

logger = logging.getLogger(__name__)


class MiraklClient(BaseMarketplace):
    """
    Generic Mirakl marketplace client (Seller API).

    One instance = one Mirakl operator (e.g. Galeries Lafayette).
    Pass the operator-specific ``base_url`` and ``marketplace_id``.

    Supported streams: ORDERS, INVOICES, STOCK, CATALOGUE

    Args:
        credentials:    ApiKeyCredentials(api_key=<shop_api_key>)
        base_url:       Operator API base, e.g.
                        ``'https://galerieslafayette.mirakl.net/api'``
        marketplace_id: Internal DB marketplace ID for this operator.
        brand:          Brand object (used for invoice metadata).
        name:           Operator display name (e.g. 'Galeries Lafayette').
        country:        ISO-3166-1 alpha-2 country code (default ``'FR'``).
        tax_rate:       Default VAT rate as a percentage (e.g. ``Decimal('20')``).
    """

    supported_streams = {
        StreamType.ORDERS,
        StreamType.INVOICES,
        StreamType.STOCK,
        StreamType.CATALOGUE,
    }

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
    # Public stream methods
    # ------------------------------------------------------------------

    def fetch_orders(self, days_ago: Optional[int] = None, **kwargs) -> list:
        """Fetch normalised orders via OR11 ``GET /api/orders``."""
        raw_orders = self._fetch_raw_orders(days_ago)
        return [map_order(raw, self.marketplace_id, self.brand) for raw in raw_orders]

    def fetch_invoices(self, days_ago: Optional[int] = None, **kwargs) -> list:
        """Fetch invoices (shipped orders only) via OR11 ``GET /api/orders``."""
        raw_orders = self._fetch_raw_orders(days_ago)
        return [
            inv
            for raw in raw_orders
            if (inv := map_invoice(raw, self.marketplace_id, self.brand, self.tax_rate)) is not None
        ]

    def fetch_order(self, order_id: str) -> object:
        """Fetch a single order by ``order_id`` via OR11."""
        response = requests.get(
            f"{self.base_url}/orders",
            headers=self._headers(),
            params={"order_ids": order_id, "max": 1},
            timeout=30,
        )
        if response.status_code == 404:
            raise ResourceNotFoundError("Order", order_id)
        response.raise_for_status()
        orders = response.json().get("orders", [])
        if not orders:
            raise ResourceNotFoundError("Order", order_id)
        return map_order(orders[0], self.marketplace_id, self.brand)

    def fetch_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list:
        """Fetch inventory levels via OF21 ``GET /api/offers``.

        Each offer's ``quantity`` field is the total available quantity across
        all warehouses.

        Args:
            skus: Optional list of ``shop_sku`` values to filter on.

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.stock.StockLevel`]
        """
        raw = self._fetch_raw_offers(skus=skus)
        return [map_stock_level(r, self.marketplace_id) for r in raw]

    def fetch_catalogue(
        self,
        updated_since=None,
        skus: Optional[list[str]] = None,
        **kwargs,
    ) -> list:
        """Fetch product listings via OF21 ``GET /api/offers``.

        OF21 is used for both stock and catalogue because it is the richest
        per-offer endpoint available to sellers.  It returns ``product_title``,
        ``product_brand``, ``product_description``, ``product_sku``,
        ``shop_sku``, ``price``, ``quantity``, ``active``, ``category_code``,
        and ``product_references`` (EAN/UPC etc.).

        ``updated_since`` is not supported by OF21 and is ignored.  Use the
        async export APIs (OF52/OF53) if you need a differential catalogue
        export.

        Args:
            updated_since: Ignored (OF21 has no date filter).
            skus:          Optional list of ``shop_sku`` values to filter on.

        Returns:
            list[:class:`~etail_marketplaces_sdk.models.product.Product`]
        """
        raw = self._fetch_raw_offers(skus=skus)
        return [map_product(r, self.marketplace_id) for r in raw]

    def fetch_raw_orders(self, days_ago: Optional[int] = None, **kwargs) -> list[dict]:
        """Return raw OR11 order payloads without normalisation.

        Each dict is identical to the ``raw`` field on each
        :class:`~etail_marketplaces_sdk.models.order.Order` returned by
        :meth:`fetch_orders`.

        Args:
            days_ago: Fetch orders updated in the last N days.

        Returns:
            list[dict]
        """
        return self._fetch_raw_orders(days_ago)

    def fetch_raw_stock(self, skus: Optional[list[str]] = None, **kwargs) -> list[dict]:
        """Return raw OF21 offer payloads without normalisation.

        Each dict matches ``OF21_Response_200_Offers`` in the seller OpenAPI
        spec.  Key fields: ``shop_sku``, ``offer_id``, ``quantity``, ``price``,
        ``active``, ``product_title``, ``product_sku``.

        Args:
            skus: Optional list of ``shop_sku`` values to filter on.

        Returns:
            list[dict]
        """
        return self._fetch_raw_offers(skus=skus)

    def fetch_raw_catalogue(
        self,
        updated_since=None,
        skus: Optional[list[str]] = None,
        **kwargs,
    ) -> list[dict]:
        """Return raw OF21 offer payloads without normalisation.

        Identical payload to :meth:`fetch_raw_stock` — both use OF21.  The
        difference is in the downstream mapper (Product vs StockLevel).

        Args:
            updated_since: Ignored (OF21 has no date filter).
            skus:          Optional list of ``shop_sku`` values to filter on.

        Returns:
            list[dict]
        """
        return self._fetch_raw_offers(skus=skus)

    # ------------------------------------------------------------------
    # Private HTTP methods
    # ------------------------------------------------------------------

    def _fetch_raw_orders(self, days_ago: Optional[int] = None) -> list[dict]:
        """Paginate through OR11 ``GET /api/orders`` with offset pagination.

        Spec: OR11 uses ``max`` (≤ 100) + ``offset`` pagination, returning
        ``{ orders: [...], total_count: int }``.  The recommended differential
        filter is ``start_update_date``.
        """
        orders: list[dict] = []
        params: dict = {"max": 100, "offset": 0}
        if days_ago:
            from_date = datetime.now(timezone.utc) - timedelta(days=days_ago)
            params["start_update_date"] = from_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")

        while True:
            try:
                response = requests.get(
                    f"{self.base_url}/orders",
                    headers=self._headers(),
                    params=params,
                    timeout=30,
                )
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                batch = data.get("orders") or []
                orders.extend(batch)

                total = data.get("total_count") or 0
                if len(orders) >= total or not batch:
                    break
                params["offset"] = len(orders)
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("Mirakl fetch_orders error: %s", exc)
                break

        return orders

    def _fetch_raw_offers(self, skus: Optional[list[str]] = None) -> list[dict]:
        """Paginate through OF21 ``GET /api/offers`` with offset pagination.

        Spec: OF21 uses ``max`` (≤ 100) + ``offset`` pagination, returning
        ``{ offers: [...], total_count: int }``.  SKU filter uses the ``sku``
        param (the offer's ``shop_sku``).
        """
        offers: list[dict] = []
        params: dict = {"max": 100, "offset": 0}
        if skus:
            params["sku"] = ",".join(skus)

        while True:
            try:
                response = requests.get(
                    f"{self.base_url}/offers",
                    headers=self._headers(),
                    params=params,
                    timeout=30,
                )
                if response.status_code == 429:
                    raise RateLimitError()
                response.raise_for_status()
                data = response.json()
                batch = data.get("offers") or []
                offers.extend(batch)

                total = data.get("total_count") or 0
                if len(offers) >= total or not batch:
                    break
                params["offset"] = len(offers)
            except RateLimitError:
                raise
            except requests.RequestException as exc:
                logger.error("Mirakl fetch_offers error: %s", exc)
                break

        return offers
