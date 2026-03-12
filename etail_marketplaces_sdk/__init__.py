"""
etail-marketplaces-sdk

Unified Python SDK for eCommerce marketplace and aggregator APIs.
Provides a consistent interface to fetch, normalise and sink data streams
across aggregators (Lengow, ShoppingFeed, ChannelEngine) and direct
marketplaces (ManoMano, Mirakl).

Supported streams:
    orders, stock, catalogue, shipments, returns,
    invoices, analytics, ads, settlements, reviews
"""

from etail_marketplaces_sdk.core.streams import StreamType
from etail_marketplaces_sdk.core.credentials import (
    ApiKeyCredentials,
    OAuth2Credentials,
    BearerCredentials,
    LengowCredentials,
)
from etail_marketplaces_sdk.core.exceptions import (
    SDKError,
    AuthError,
    RateLimitError,
    StreamNotSupportedError,
    ResourceNotFoundError,
    MappingError,
)

__all__ = [
    "StreamType",
    "ApiKeyCredentials",
    "OAuth2Credentials",
    "BearerCredentials",
    "LengowCredentials",
    "SDKError",
    "AuthError",
    "RateLimitError",
    "StreamNotSupportedError",
    "ResourceNotFoundError",
    "MappingError",
]
