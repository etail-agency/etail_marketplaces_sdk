"""Canonical Advertising / Sponsored product model."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from enum import Enum
from typing import Optional


class AdStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    ENDED = "ended"
    PENDING = "pending"


@dataclass
class AdCampaign:
    campaign_id: str
    name: str
    status: str = AdStatus.ACTIVE
    budget: Optional[Decimal] = None
    currency: str = "EUR"
    start_date: Optional[date] = None
    end_date: Optional[date] = None

    def to_dict(self) -> dict:
        return {
            "campaign_id": self.campaign_id,
            "name": self.name,
            "status": self.status,
            "budget": str(self.budget) if self.budget else None,
            "currency": self.currency,
            "start_date": self.start_date.isoformat() if self.start_date else None,
            "end_date": self.end_date.isoformat() if self.end_date else None,
        }


@dataclass
class AdRecord:
    """
    A single advertising performance record for a date + SKU combination.
    """

    report_date: date
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    campaign: Optional[AdCampaign] = None
    sku: Optional[str] = None
    impressions: Optional[int] = None
    clicks: Optional[int] = None
    spend: Optional[Decimal] = None
    attributed_revenue: Optional[Decimal] = None
    attributed_orders: Optional[int] = None
    attributed_units: Optional[int] = None
    acos: Optional[Decimal] = None
    roas: Optional[Decimal] = None
    currency: str = "EUR"
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "report_date": self.report_date.isoformat(),
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "campaign": self.campaign.to_dict() if self.campaign else None,
            "sku": self.sku,
            "impressions": self.impressions,
            "clicks": self.clicks,
            "spend": str(self.spend) if self.spend else None,
            "attributed_revenue": str(self.attributed_revenue) if self.attributed_revenue else None,
            "attributed_orders": self.attributed_orders,
            "attributed_units": self.attributed_units,
            "acos": str(self.acos) if self.acos else None,
            "roas": str(self.roas) if self.roas else None,
            "currency": self.currency,
        }
