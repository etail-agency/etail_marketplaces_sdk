"""
StreamType enum — every eCommerce data stream the SDK can represent.

Not every platform supports every stream. Calling an unsupported stream method
on a client raises `StreamNotSupportedError`. Use `client.supported_streams`
to inspect what a concrete client has implemented.
"""

from enum import Enum, auto


class StreamType(Enum):
    ORDERS = auto()
    STOCK = auto()
    CATALOGUE = auto()
    SHIPMENTS = auto()
    RETURNS = auto()
    INVOICES = auto()
    ANALYTICS = auto()
    ADS = auto()
    SETTLEMENTS = auto()
    REVIEWS = auto()
