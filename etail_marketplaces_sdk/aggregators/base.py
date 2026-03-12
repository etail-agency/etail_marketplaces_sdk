"""
BaseAggregator — abstract base class for all aggregator clients.

An aggregator is a middleware platform (Lengow, ShoppingFeed, ChannelEngine…)
that connects a merchant to multiple marketplaces. Aggregators have an
internal numeric ID that maps to the `aggregator` table in the database.
"""

from __future__ import annotations

from etail_marketplaces_sdk.core.base_client import BaseClient


class BaseAggregator(BaseClient):
    """
    Extends BaseClient with aggregator-specific metadata.

    Subclasses must set:
        aggregator_id: int    — internal DB identifier
        name: str             — human-readable aggregator name
    """

    aggregator_id: int
    name: str

    def __init__(self, credentials: object) -> None:
        super().__init__(credentials)
