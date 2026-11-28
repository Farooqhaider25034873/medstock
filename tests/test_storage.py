import csv
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from stock import storage
from stock.inventory import Inventory
from stock.models import Item
from stock.storage import StorageError


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.dir = Path(self.folder.name)
        self.inv = Inventory([
            Item("PAN-001", "Paracetamol", "Painkillers", 100, 0.99, date(2028, 1, 1), 20),
            Item("VIT-001", "Vitamin C", "Vitamins", 5, 3.5, date(2027, 6, 1), 10),
        ])
        self.inv.sell("PAN-001", 2, date(2026, 11, 22))

    def tearDown(self):
        self.folder.cleanup()

    def write(self, name, text):
        path = self.dir / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_save_then_load_round_trip(self):
        path = self.dir / "stock.json"
        storage.save(self.inv, path)
        self.assertFalse(self.inv.unsaved)

        loaded = storage.load(path)
        self.assertEqual(loaded.items(), self.inv.sorted_by("code"))
        self.assertEqual(loaded.sales, self.inv.sales)
        self.assertFalse(loaded.unsaved)
        self.assertFalse(path.with_suffix(".tmp").exists())

    def test_save_creates_missing_folder(self):
        path = self.dir / "new" / "stock.json"
        storage.save(self.inv, path)
        self.assertTrue(path.exists())

    def test_missing_file_gives_empty_inventory(self):
        self.assertEqual(len(storage.load(self.dir / "nothing.json")), 0)

    def test_corrupt_json(self):
        with self.assertRaises(StorageError):
            storage.load(self.write("bad.json", "{ not json"))

    def test_wrong_layout(self):
        with self.assertRaises(StorageError):
            storage.load(self.write("list.json", "[1, 2, 3]"))

    def test_bad_record_names_the_record(self):
        data = {"items": [{"code": "A-1", "name": "x", "category": "y",
                           "quantity": "lots", "price": 1, "expiry": "2028-01-01"}]}
        with self.assertRaises(StorageError) as ctx:
            storage.load(self.write("bad.json", json.dumps(data)))
        self.assertIn("item 1", str(ctx.exception))

    def test_duplicate_codes(self):
        row = {"code": "A-1", "name": "x", "category": "y", "quantity": 1,
               "price": 1, "expiry": "2028-01-01"}
        with self.assertRaises(StorageError):
            storage.load(self.write("dup.json", json.dumps({"items": [row, row]})))

    def test_export_csv(self):
        path = self.dir / "report.csv"
        storage.export_csv(self.inv.sorted_by("code"), path, today=date(2026, 11, 22))
        with open(path, newline="", encoding="utf-8") as f:
            rows = list(csv.reader(f))
        self.assertEqual(rows[0][0], "Code")
        self.assertEqual(len(rows), 3)
        self.assertEqual(rows[2][-1], "Low stock")


if __name__ == "__main__":
    unittest.main()
