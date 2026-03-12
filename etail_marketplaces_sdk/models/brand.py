"""Brand / seller entity — migrated from backend/app/services/order_integration/models/brand.py."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Brand:
    id: int
    name: str
    slug: str
    initials: str
    logo_url: str
    company_info: str
    invoice_footer_text: str
    created_date: Optional[datetime] = None
    updated_date: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "slug": self.slug,
            "initials": self.initials,
            "logo_url": self.logo_url,
            "company_info": self.company_info,
            "invoice_footer_text": self.invoice_footer_text,
            "created_date": self.created_date.isoformat() if self.created_date else None,
            "updated_date": self.updated_date.isoformat() if self.updated_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Brand":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
