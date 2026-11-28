"""The Inventory class holds all items and sales and enforces the stock rules."""

import heapq
from collections import deque
from dataclasses import replace
from datetime import date

from .models import Sale
from .sorting import merge_sort

UNDO_LIMIT = 50

SORT_KEYS = {
    "code": lambda item: item.code,
    "name": lambda item: item.name.lower(),
    "category": lambda item: (item.category.lower(), item.name.lower()),
    "quantity": lambda item: item.quantity,
    "price": lambda item: item.price,
    "expiry": lambda item: item.expiry,
    "value": lambda item: item.value,
}


class StockError(Exception):
    """Raised when an action would break a stock rule."""


class Inventory:
    def __init__(self, items=None, sales=None):
        # dict keyed by code gives O(1) lookup, edit and delete
        self._items = {}
        for item in items or []:
            self._items[item.code] = item
        self.sales = list(sales or [])
        # deque with maxlen drops the oldest entry once the limit is hit
        self._history = deque(maxlen=UNDO_LIMIT)
        self.unsaved = False

    def __len__(self):
        return len(self._items)

    def __contains__(self, code):
        return code in self._items

    def get(self, code):
        item = self._items.get(code)
        if item is None:
            raise StockError(f"No item found with code {code}.")
        return item

    def items(self):
        return list(self._items.values())

    def categories(self):
        return sorted({item.category for item in self._items.values()})

    # ---- changes (all undoable) ----

    def add(self, item):
        if item.code in self._items:
            raise StockError(f"Code {item.code} is already used by {self._items[item.code].name}.")
        self._items[item.code] = item
        self._record("add", item.code, None)

    def update(self, item):
        old = self.get(item.code)
        self._items[item.code] = item
        self._record("edit", item.code, old)

    def remove(self, code):
        old = self.get(code)
        del self._items[code]
        self._record("delete", code, old)
        return old

    def sell(self, code, quantity, today=None):
        today = today or date.today()
        item = self.get(code)
        if quantity <= 0:
            raise StockError("Quantity sold must be at least 1.")
        if item.days_left(today) < 0:
            raise StockError(f"{item.name} has expired and cannot be sold.")
        if quantity > item.quantity:
            raise StockError(f"Only {item.quantity} of {item.name} in stock.")

        self._items[code] = replace(item, quantity=item.quantity - quantity)
        sale = Sale(item.code, item.name, quantity, item.price, today)
        self.sales.append(sale)
        self._record("sale", code, item)
        return sale

    def restock(self, code, quantity, new_expiry=None):
        item = self.get(code)
        if quantity <= 0:
            raise StockError("Restock quantity must be at least 1.")
        self._items[code] = replace(
            item,
            quantity=item.quantity + quantity,
            expiry=new_expiry or item.expiry,
        )
        self._record("restock", code, item)

    def can_undo(self):
        return bool(self._history)

    def undo(self):
        """Reverse the last change and return a short description of it."""
        if not self._history:
            raise StockError("Nothing to undo.")
        action, code, old = self._history.pop()

        if action == "add":
            del self._items[code]
        else:
            self._items[code] = old
        if action == "sale":
            self.sales.pop()

        self.unsaved = True
        return f"Undid {action} of {code}"

    def _record(self, action, code, old):
        # items are replaced rather than edited in place, so keeping
        # the old object is enough to restore it later
        self._history.append((action, code, old))
        self.unsaved = True

    # ---- searching and sorting ----

    def search(self, text, category=None):
        """Case-insensitive match on code, name or category."""
        text = text.strip().lower()
        found = []
        for item in self._items.values():
            if category and item.category != category:
                continue
            fields = (item.code, item.name, item.category)
            if not text or any(text in f.lower() for f in fields):
                found.append(item)
        return found

    def sorted_by(self, field, descending=False, items=None):
        if field not in SORT_KEYS:
            raise StockError(f"Cannot sort by {field}.")
        if items is None:
            items = self.items()
        return merge_sort(items, key=SORT_KEYS[field], reverse=descending)

    # ---- reports ----

    def low_stock(self):
        """Items at or below their reorder level, worst shortfall first."""
        low = [item for item in self._items.values() if item.is_low()]
        return merge_sort(low, key=lambda item: item.quantity - item.reorder_level)

    def expiring_within(self, days, today=None):
        """Items expiring in the next `days` days (expired ones included), soonest first."""
        today = today or date.today()
        heap = [(item.expiry, item.code) for item in self._items.values()]
        heapq.heapify(heap)

        result = []
        # stop popping as soon as we pass the cut-off, so only matching
        # items cost a log n pop
        while heap and (heap[0][0] - today).days <= days:
            _, code = heapq.heappop(heap)
            result.append(self._items[code])
        return result

    def category_summary(self):
        """Return {category: (lines, units, value)} sorted by category name."""
        totals = {}
        for item in self._items.values():
            lines, units, value = totals.get(item.category, (0, 0, 0.0))
            totals[item.category] = (lines + 1, units + item.quantity, value + item.value)
        return {cat: (n, u, round(v, 2)) for cat, (n, u, v) in sorted(totals.items())}

    def total_value(self):
        return round(sum(item.value for item in self._items.values()), 2)

    def best_sellers(self, limit=5):
        """Return [(name, units sold, revenue)] for the top sellers."""
        totals = {}
        for sale in self.sales:
            units, revenue = totals.get(sale.name, (0, 0.0))
            totals[sale.name] = (units + sale.quantity, revenue + sale.total)
        rows = [(name, units, round(rev, 2)) for name, (units, rev) in totals.items()]
        return merge_sort(rows, key=lambda row: row[1], reverse=True)[:limit]

    def total_revenue(self):
        return round(sum(sale.total for sale in self.sales), 2)
