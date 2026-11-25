"""Data classes for stock items and sales."""

from dataclasses import dataclass, asdict
from datetime import date

EXPIRY_WARNING_DAYS = 30
CURRENCY = "£"


def money(amount):
    return f"{CURRENCY}{amount:,.2f}"


@dataclass
class Item:
    """A single product line held in the pharmacy."""

    code: str
    name: str
    category: str
    quantity: int
    price: float
    expiry: date
    reorder_level: int = 10

    @property
    def value(self):
        return round(self.quantity * self.price, 2)

    def is_low(self):
        return self.quantity <= self.reorder_level

    def days_left(self, today=None):
        today = today or date.today()
        return (self.expiry - today).days

    def status(self, today=None):
        """Short label used by both interfaces to flag problems."""
        days = self.days_left(today)
        if days < 0:
            return "EXPIRED"
        if days <= EXPIRY_WARNING_DAYS:
            return "Expiring"
        if self.is_low():
            return "Low stock"
        return "OK"

    def to_dict(self):
        data = asdict(self)
        data["expiry"] = self.expiry.isoformat()
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            code=data["code"],
            name=data["name"],
            category=data["category"],
            quantity=int(data["quantity"]),
            price=float(data["price"]),
            expiry=date.fromisoformat(data["expiry"]),
            reorder_level=int(data.get("reorder_level", 10)),
        )


@dataclass
class Sale:
    """One recorded sale of an item."""

    code: str
    name: str
    quantity: int
    unit_price: float
    sold_on: date

    @property
    def total(self):
        return round(self.quantity * self.unit_price, 2)

    def to_dict(self):
        data = asdict(self)
        data["sold_on"] = self.sold_on.isoformat()
        return data

    @classmethod
    def from_dict(cls, data):
        return cls(
            code=data["code"],
            name=data["name"],
            quantity=int(data["quantity"]),
            unit_price=float(data["unit_price"]),
            sold_on=date.fromisoformat(data["sold_on"]),
        )
