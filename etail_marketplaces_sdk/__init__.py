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

__version__ = "0.3.0"

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

# Aggregators
from etail_marketplaces_sdk.aggregators.lengow.client import LengowClient
from etail_marketplaces_sdk.aggregators.shopping_feed.client import ShoppingFeedClient
from etail_marketplaces_sdk.aggregators.channelengine.client import ChannelEngineClient

# Marketplaces
from etail_marketplaces_sdk.marketplaces.manomano.client import ManomanoClient
from etail_marketplaces_sdk.marketplaces.mirakl.client import MiraklClient

# Sinks
from etail_marketplaces_sdk.outputs.base import BaseSinkConnector
from etail_marketplaces_sdk.outputs.postgres import PostgresSinkConnector
from etail_marketplaces_sdk.outputs.supabase import SupabaseSinkConnector
from etail_marketplaces_sdk.outputs.bigquery import BigQuerySinkConnector

__all__ = [
    "__version__",
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
    "LengowClient",
    "ShoppingFeedClient",
    "ChannelEngineClient",
    "ManomanoClient",
    "MiraklClient",
    "BaseSinkConnector",
    "PostgresSinkConnector",
    "SupabaseSinkConnector",
    "BigQuerySinkConnector",
]
