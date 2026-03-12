"""Canonical Product / Seller Review model."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional


class ReviewStatus(str, Enum):
    PUBLISHED = "published"
    PENDING = "pending"
    REJECTED = "rejected"
    REMOVED = "removed"


@dataclass
class Review:
    review_id: str
    aggregator_id: Optional[int] = None
    marketplace_id: Optional[int] = None
    sku: Optional[str] = None
    order_id: Optional[str] = None
    rating: Optional[float] = None
    title: Optional[str] = None
    body: Optional[str] = None
    reviewer_name: Optional[str] = None
    status: str = ReviewStatus.PUBLISHED
    is_verified_purchase: bool = False
    published_at: Optional[datetime] = None
    raw: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "review_id": self.review_id,
            "aggregator_id": self.aggregator_id,
            "marketplace_id": self.marketplace_id,
            "sku": self.sku,
            "order_id": self.order_id,
            "rating": self.rating,
            "title": self.title,
            "body": self.body,
            "reviewer_name": self.reviewer_name,
            "status": self.status,
            "is_verified_purchase": self.is_verified_purchase,
            "published_at": self.published_at.isoformat() if self.published_at else None,
        }
