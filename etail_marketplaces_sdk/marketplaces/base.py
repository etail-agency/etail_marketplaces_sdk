"""
BaseMarketplace — abstract base class for all direct marketplace clients.

A marketplace is a platform that has its own seller API (ManoMano, Mirakl,
Amazon, Zalando …) as opposed to an aggregator which acts as middleware.
Marketplaces carry a `marketplace_id` that maps to the `marketplace` DB table
and a `country` code for multi-country platforms.
"""

from __future__ import annotations

from etail_marketplaces_sdk.core.base_client import BaseClient


class BaseMarketplace(BaseClient):
    """
    Extends BaseClient with marketplace-specific metadata.

    Subclasses must set:
        marketplace_id: int    — internal DB identifier
        name: str              — human-readable marketplace name
        country: str           — ISO-3166-1 alpha-2 country code (e.g. 'FR')
    """

    marketplace_id: int
    name: str
    country: str

    def __init__(self, credentials: object) -> None:
        super().__init__(credentials)
