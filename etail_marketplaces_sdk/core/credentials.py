"""
Credential models for the SDK.

All credentials are plain dataclasses — no env-var reading, no secret-manager
calls. The caller is responsible for supplying values (e.g. from env vars,
Google Secret Manager, or a secrets store). This keeps the SDK portable and
testable.

Usage:
    from etail_marketplaces_sdk.core.credentials import ApiKeyCredentials

    creds = ApiKeyCredentials(api_key=os.environ["MY_API_KEY"])
    client = ShoppingFeedClient(store_id="12345", credentials=creds)
"""

from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class ApiKeyCredentials:
    """Single API key passed as a query parameter or header."""

    api_key: str


@dataclass(frozen=True)
class BearerCredentials:
    """Static Bearer / JWT token passed in the Authorization header."""

    token: str


@dataclass(frozen=True)
class OAuth2Credentials:
    """
    OAuth 2.0 client-credentials flow.

    The SDK will POST to `token_url` with `client_id` / `client_secret`
    to obtain an access token. Set `auto_refresh=True` (default) to have
    the client refresh automatically on 401 responses.
    """

    client_id: str
    client_secret: str
    token_url: str
    auto_refresh: bool = True
    scope: Optional[str] = None


@dataclass(frozen=True)
class LengowCredentials:
    """
    Lengow-specific credentials.

    Lengow uses a two-step auth: first exchange (access_token, secret) for
    a short-lived bearer token via POST /access/get_token.
    """

    access_token: str
    secret: str
