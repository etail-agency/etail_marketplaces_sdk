"""Shared postal address used across multiple models."""

from dataclasses import dataclass
from typing import Optional


@dataclass
class Address:
    name: str
    address_line1: str
    postal_code: str
    city: str
    country: str
    address_line2: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "address_line1": self.address_line1,
            "address_line2": self.address_line2,
            "postal_code": self.postal_code,
            "city": self.city,
            "country": self.country,
            "phone": self.phone,
            "email": self.email,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Address":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
