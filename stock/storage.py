"""Saving and loading the inventory as JSON, plus CSV export."""

import csv
import json
import os
from pathlib import Path

from .inventory import Inventory
from .models import Item, Sale


class StorageError(Exception):
    """Raised when a data file cannot be read or written."""


def load(path):
    """Load an inventory from a JSON file. A missing file gives an empty inventory."""
    path = Path(path)
    if not path.exists():
        return Inventory()

    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise StorageError(f"Could not read {path.name}: {e}") from None

    items, sales = [], []
    current = "file layout"
    try:
        for i, row in enumerate(data.get("items", []), start=1):
            current = f"item {i}"
            items.append(Item.from_dict(row))
        for i, row in enumerate(data.get("sales", []), start=1):
            current = f"sale {i}"
            sales.append(Sale.from_dict(row))
    except (KeyError, ValueError, TypeError, AttributeError) as e:
        raise StorageError(f"{path.name} has a bad record ({current}): {e}") from None

    codes = [item.code for item in items]
    if len(codes) != len(set(codes)):
        raise StorageError(f"{path.name} contains duplicate item codes.")

    return Inventory(items, sales)


def save(inventory, path):
    """Write the inventory to JSON. Writes to a temp file first so a crash can't corrupt the data."""
    path = Path(path)
    data = {
        "items": [item.to_dict() for item in inventory.sorted_by("code")],
        "sales": [sale.to_dict() for sale in inventory.sales],
    }
    temp = path.with_suffix(".tmp")
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(temp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(temp, path)
    except OSError as e:
        raise StorageError(f"Could not save to {path}: {e}") from None
    inventory.unsaved = False


def export_csv(items, path, today=None):
    """Write a list of items to a CSV file that opens in Excel."""
    headers = ["Code", "Name", "Category", "Quantity", "Price", "Expiry",
               "Reorder level", "Value", "Status"]
    try:
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(headers)
            for item in items:
                writer.writerow([
                    item.code, item.name, item.category, item.quantity,
                    f"{item.price:.2f}", item.expiry.isoformat(), item.reorder_level,
                    f"{item.value:.2f}", item.status(today),
                ])
    except OSError as e:
        raise StorageError(f"Could not export to {path}: {e}") from None
