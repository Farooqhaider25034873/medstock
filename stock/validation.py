"""Input checks shared by both front ends.

Each parser takes raw text from the user and either returns a clean value
or raises ValueError with a message that can be shown to the user as-is.
"""

import math
import re
from datetime import date, datetime

from .models import Item

CODE_RULE = re.compile(r"^[A-Z]{2,4}-\d{3,5}$")
MAX_QUANTITY = 100_000
MAX_PRICE = 100_000


class FormError(ValueError):
    """Holds one error message per field that failed."""

    def __init__(self, errors):
        super().__init__("; ".join(errors.values()))
        self.errors = errors


def clean_code(text):
    code = text.strip().upper()
    if not CODE_RULE.match(code):
        raise ValueError("Code must look like PAN-001 (2-4 letters, a dash, then 3-5 digits).")
    return code


def clean_text(text, field, max_length=50):
    value = " ".join(text.split())
    if not value:
        raise ValueError(f"{field} cannot be empty.")
    if len(value) > max_length:
        raise ValueError(f"{field} must be {max_length} characters or fewer.")
    return value


def clean_category(text):
    return clean_text(text, "Category", max_length=30).title()


def parse_int(text, field, low=0, high=MAX_QUANTITY):
    try:
        number = int(str(text).strip())
    except ValueError:
        raise ValueError(f"{field} must be a whole number.") from None
    if not low <= number <= high:
        raise ValueError(f"{field} must be between {low} and {high}.")
    return number


def parse_price(text):
    try:
        price = float(str(text).strip())
    except ValueError:
        raise ValueError("Price must be a number, e.g. 4.50.") from None
    # float() accepts "nan" and "inf", so those need catching too
    if not math.isfinite(price) or price <= 0 or price > MAX_PRICE:
        raise ValueError(f"Price must be more than 0 and no more than {MAX_PRICE}.")
    return round(price, 2)


def parse_date(text):
    try:
        return datetime.strptime(text.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise ValueError("Date must be a real date in YYYY-MM-DD format, e.g. 2027-03-15.") from None


def parse_expiry(text, today=None):
    """Like parse_date, but the date has to be after today."""
    expiry = parse_date(text)
    if expiry <= (today or date.today()):
        raise ValueError("Expiry date must be in the future.")
    return expiry


# (field, label, parser) for every field on the item form.
# Both interfaces loop over this, so the rules live in one place.
FIELDS = [
    ("code", "Code", clean_code),
    ("name", "Name", lambda t: clean_text(t, "Name")),
    ("category", "Category", clean_category),
    ("quantity", "Quantity", lambda t: parse_int(t, "Quantity")),
    ("price", "Unit price", parse_price),
    ("expiry", "Expiry date", parse_expiry),
    ("reorder_level", "Reorder level", lambda t: parse_int(t, "Reorder level", high=10_000)),
]


def build_item(values, is_new=True):
    """Check a dict of raw form text and return an Item, or raise FormError.

    When editing (is_new=False) a past expiry date is allowed, so a typo in
    an existing record can still be corrected.
    """
    clean, errors = {}, {}
    for field, _, parse in FIELDS:
        if field == "expiry" and not is_new:
            parse = parse_date
        try:
            clean[field] = parse(values.get(field, ""))
        except ValueError as e:
            errors[field] = str(e)
    if errors:
        raise FormError(errors)
    return Item(**clean)


def item_to_text(item):
    """Turn an Item back into form text (the reverse of build_item)."""
    return {
        "code": item.code,
        "name": item.name,
        "category": item.category,
        "quantity": str(item.quantity),
        "price": f"{item.price:.2f}",
        "expiry": item.expiry.isoformat(),
        "reorder_level": str(item.reorder_level),
    }
