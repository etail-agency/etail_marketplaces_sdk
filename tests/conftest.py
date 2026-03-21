"""Shared pytest fixtures."""

from __future__ import annotations

import pytest

from etail_marketplaces_sdk.models.brand import Brand


@pytest.fixture
def brand() -> Brand:
    """Minimal brand used by all order mappers."""
    return Brand(id=1, name="Test Brand")
