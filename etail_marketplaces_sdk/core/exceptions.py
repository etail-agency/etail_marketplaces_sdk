"""
SDK-level exception hierarchy.

All exceptions inherit from SDKError so callers can catch broadly or narrowly.

    try:
        orders = client.fetch_orders(days_ago=7)
    except RateLimitError as e:
        time.sleep(e.retry_after)
    except AuthError:
        # refresh credentials and retry
    except SDKError as e:
        logger.error("SDK error: %s", e)
"""


class SDKError(Exception):
    """Base class for all SDK errors."""


class AuthError(SDKError):
    """Raised when authentication fails (401 / 403 responses)."""


class RateLimitError(SDKError):
    """Raised when the upstream API returns a 429 response."""

    def __init__(self, message: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(message)
        self.retry_after = retry_after


class StreamNotSupportedError(SDKError):
    """
    Raised when a stream method is called on a client that has not
    implemented it.

    Example:
        client.fetch_ads()  # raises if ads are not supported
    """

    def __init__(self, stream: str, client: str):
        super().__init__(
            f"Stream '{stream}' is not supported by {client}. "
            "Check client.supported_streams for available streams."
        )
        self.stream = stream
        self.client = client


class ResourceNotFoundError(SDKError):
    """Raised when a specific resource (e.g. an order ID) does not exist."""

    def __init__(self, resource_type: str, identifier: str):
        super().__init__(f"{resource_type} '{identifier}' not found.")
        self.resource_type = resource_type
        self.identifier = identifier


class MappingError(SDKError):
    """
    Raised when a mapper cannot translate an API response field into a
    canonical model (e.g. unexpected null, type mismatch).
    """
