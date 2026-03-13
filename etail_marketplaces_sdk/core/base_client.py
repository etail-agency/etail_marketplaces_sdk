"""
BaseClient — abstract interface shared by all aggregator and marketplace clients.

Design principles:
- Every stream method has a default implementation that raises StreamNotSupportedError.
  Concrete clients override only the streams they actually support.
- Each canonical stream (fetch_orders, fetch_stock, …) has a raw counterpart
  (fetch_raw_orders, fetch_raw_stock, …) that returns the unmodified platform
  payload as a list[dict].  This lets callers access platform-specific fields
  that the canonical model does not expose.
- `supported_streams` is a class-level set that each concrete client declares,
  making it easy to introspect at runtime.
- No I/O, no credentials fetching, no DB logic lives here — pure interface.
"""

from __future__ import annotations

from abc import ABC
from datetime import date
from typing import Optional, Set

from etail_marketplaces_sdk.core.exceptions import StreamNotSupportedError
from etail_marketplaces_sdk.core.streams import StreamType


class BaseClient(ABC):
    """
    Abstract base for every platform client (aggregator or marketplace).

    Subclasses must:
      1. Declare `supported_streams` with the StreamType values they implement.
      2. Accept a credentials object (appropriate subclass) as `credentials`.
      3. Override any `fetch_*` method they support.
    """

    supported_streams: Set[StreamType] = set()

    def __init__(self, credentials: object) -> None:
        self.credentials = credentials

    # ------------------------------------------------------------------
    # Orders
    # ------------------------------------------------------------------

    def fetch_orders(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch a list of normalised Order objects.

        Args:
            days_ago:  Convenience shortcut — fetch orders from the last N days.
            date_from: Explicit start date (overrides days_ago when provided).
            date_to:   Explicit end date (defaults to today when not provided).

        Returns:
            list[Order]
        """
        raise StreamNotSupportedError(StreamType.ORDERS.name, type(self).__name__)

    def fetch_raw_orders(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[dict]:
        """
        Fetch orders as unmodified platform payloads (no normalisation).

        Useful when you need platform-specific fields that the canonical
        :class:`~etail_marketplaces_sdk.models.order.Order` model does not expose.
        The returned dicts are identical to the ``raw`` field on each ``Order``
        returned by :meth:`fetch_orders`.

        Args:
            days_ago:  Convenience shortcut — fetch orders from the last N days.
            date_from: Explicit start date.
            date_to:   Explicit end date.

        Returns:
            list[dict] — one dict per order, exactly as returned by the platform API.
        """
        raise StreamNotSupportedError(StreamType.ORDERS.name, type(self).__name__)

    def fetch_order(self, order_id: str) -> object:
        """Fetch a single normalised Order by its platform order ID."""
        raise StreamNotSupportedError(StreamType.ORDERS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Stock
    # ------------------------------------------------------------------

    def fetch_stock(self, skus: Optional[list[str]] = None) -> list:
        """
        Fetch normalised stock levels.

        Args:
            skus: Optional list of SKUs to filter. Fetches all if omitted.

        Returns:
            list[StockLevel]
        """
        raise StreamNotSupportedError(StreamType.STOCK.name, type(self).__name__)

    def fetch_raw_stock(self, skus: Optional[list[str]] = None) -> list[dict]:
        """
        Fetch stock levels as unmodified platform payloads.

        Args:
            skus: Optional list of SKUs to filter. Fetches all if omitted.

        Returns:
            list[dict]
        """
        raise StreamNotSupportedError(StreamType.STOCK.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Catalogue
    # ------------------------------------------------------------------

    def fetch_catalogue(
        self,
        updated_since: Optional[date] = None,
    ) -> list:
        """
        Fetch normalised product catalogue listings.

        Args:
            updated_since: Only return products updated after this date.

        Returns:
            list[Product]
        """
        raise StreamNotSupportedError(StreamType.CATALOGUE.name, type(self).__name__)

    def fetch_raw_catalogue(
        self,
        updated_since: Optional[date] = None,
    ) -> list[dict]:
        """
        Fetch product catalogue listings as unmodified platform payloads.

        Args:
            updated_since: Only return products updated after this date.

        Returns:
            list[dict]
        """
        raise StreamNotSupportedError(StreamType.CATALOGUE.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Shipments
    # ------------------------------------------------------------------

    def fetch_shipments(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch normalised shipment / tracking records.

        Returns:
            list[Shipment]
        """
        raise StreamNotSupportedError(StreamType.SHIPMENTS.name, type(self).__name__)

    def fetch_raw_shipments(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list[dict]:
        """
        Fetch shipment records as unmodified platform payloads.

        Returns:
            list[dict]
        """
        raise StreamNotSupportedError(StreamType.SHIPMENTS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Returns
    # ------------------------------------------------------------------

    def fetch_returns(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch return / refund records.

        Returns:
            list[Return]
        """
        raise StreamNotSupportedError(StreamType.RETURNS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def fetch_invoices(
        self,
        days_ago: Optional[int] = None,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch invoice documents.

        Returns:
            list[Invoice]
        """
        raise StreamNotSupportedError(StreamType.INVOICES.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def fetch_analytics(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch performance analytics / reporting records.

        Returns:
            list[AnalyticsRecord]
        """
        raise StreamNotSupportedError(StreamType.ANALYTICS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Ads
    # ------------------------------------------------------------------

    def fetch_ads(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch sponsored-product / advertising campaign records.

        Returns:
            list[AdRecord]
        """
        raise StreamNotSupportedError(StreamType.ADS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Settlements
    # ------------------------------------------------------------------

    def fetch_settlements(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch financial settlement / payout records.

        Returns:
            list[Settlement]
        """
        raise StreamNotSupportedError(StreamType.SETTLEMENTS.name, type(self).__name__)

    # ------------------------------------------------------------------
    # Reviews
    # ------------------------------------------------------------------

    def fetch_reviews(
        self,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
    ) -> list:
        """
        Fetch product or seller review records.

        Returns:
            list[Review]
        """
        raise StreamNotSupportedError(StreamType.REVIEWS.name, type(self).__name__)
