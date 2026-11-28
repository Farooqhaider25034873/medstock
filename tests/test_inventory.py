import unittest
from datetime import date

from stock.inventory import Inventory, StockError, UNDO_LIMIT
from stock.models import Item

TODAY = date(2026, 11, 22)


def make_item(code, name="Item", quantity=20, price=1.0, expiry=date(2028, 1, 1),
              category="Painkillers", reorder_level=10):
    return Item(code, name, category, quantity, price, expiry, reorder_level)


class InventoryTestCase(unittest.TestCase):
    def setUp(self):
        self.inv = Inventory([
            make_item("PAN-001", "Paracetamol", 100, 0.99),
            make_item("PAN-002", "Ibuprofen", 10, 1.49, date(2026, 12, 1)),
            make_item("VIT-001", "Vitamin C", 0, 3.50, category="Vitamins"),
            make_item("VIT-002", "Old Gummies", 40, 7.50, date(2026, 11, 1), "Vitamins"),
        ])


class AddEditDeleteTests(InventoryTestCase):
    def test_add_and_get(self):
        self.inv.add(make_item("FAD-001", "Plasters"))
        self.assertEqual(self.inv.get("FAD-001").name, "Plasters")
        self.assertEqual(len(self.inv), 5)
        self.assertTrue(self.inv.unsaved)

    def test_duplicate_code_rejected(self):
        with self.assertRaises(StockError):
            self.inv.add(make_item("PAN-001"))

    def test_update_replaces_item(self):
        self.inv.update(make_item("PAN-001", "Paracetamol 500mg", 90))
        self.assertEqual(self.inv.get("PAN-001").quantity, 90)

    def test_missing_code(self):
        for action in (lambda: self.inv.get("XX-999"),
                       lambda: self.inv.remove("XX-999"),
                       lambda: self.inv.update(make_item("XX-999"))):
            with self.assertRaises(StockError):
                action()

    def test_remove(self):
        self.inv.remove("PAN-002")
        self.assertNotIn("PAN-002", self.inv)


class SaleAndRestockTests(InventoryTestCase):
    def test_normal_sale(self):
        sale = self.inv.sell("PAN-001", 3, TODAY)
        self.assertEqual(self.inv.get("PAN-001").quantity, 97)
        self.assertAlmostEqual(sale.total, 2.97)
        self.assertEqual(len(self.inv.sales), 1)

    def test_sell_entire_stock(self):
        self.inv.sell("PAN-002", 10, TODAY)
        self.assertEqual(self.inv.get("PAN-002").quantity, 0)

    def test_sell_more_than_stock(self):
        with self.assertRaises(StockError):
            self.inv.sell("PAN-002", 11, TODAY)
        self.assertEqual(self.inv.get("PAN-002").quantity, 10)

    def test_sell_zero_or_negative(self):
        for qty in (0, -1):
            with self.subTest(qty=qty), self.assertRaises(StockError):
                self.inv.sell("PAN-001", qty, TODAY)

    def test_cannot_sell_expired(self):
        with self.assertRaises(StockError):
            self.inv.sell("VIT-002", 1, TODAY)

    def test_restock_with_new_expiry(self):
        self.inv.restock("VIT-001", 25, date(2029, 1, 1))
        item = self.inv.get("VIT-001")
        self.assertEqual((item.quantity, item.expiry), (25, date(2029, 1, 1)))

    def test_restock_keeps_expiry_if_none_given(self):
        self.inv.restock("PAN-001", 5)
        self.assertEqual(self.inv.get("PAN-001").expiry, date(2028, 1, 1))

    def test_restock_zero_rejected(self):
        with self.assertRaises(StockError):
            self.inv.restock("PAN-001", 0)


class UndoTests(InventoryTestCase):
    def test_undo_each_kind_of_change(self):
        original = self.inv.get("PAN-001")
        self.inv.add(make_item("NEW-001"))
        self.inv.update(make_item("PAN-001", "Changed"))
        self.inv.sell("PAN-002", 2, TODAY)
        self.inv.restock("VIT-001", 5)
        self.inv.remove("PAN-001")

        self.inv.undo()  # delete
        self.assertIn("PAN-001", self.inv)
        self.inv.undo()  # restock
        self.assertEqual(self.inv.get("VIT-001").quantity, 0)
        self.inv.undo()  # sale
        self.assertEqual(self.inv.get("PAN-002").quantity, 10)
        self.assertEqual(self.inv.sales, [])
        self.inv.undo()  # edit
        self.assertEqual(self.inv.get("PAN-001"), original)
        self.inv.undo()  # add
        self.assertNotIn("NEW-001", self.inv)

        self.assertFalse(self.inv.can_undo())
        with self.assertRaises(StockError):
            self.inv.undo()

    def test_undo_history_is_capped(self):
        for _ in range(UNDO_LIMIT + 10):
            self.inv.restock("PAN-001", 1)
        undone = 0
        while self.inv.can_undo():
            self.inv.undo()
            undone += 1
        self.assertEqual(undone, UNDO_LIMIT)


class SearchSortTests(InventoryTestCase):
    def test_search_is_case_insensitive_and_partial(self):
        codes = {i.code for i in self.inv.search("vit")}
        self.assertEqual(codes, {"VIT-001", "VIT-002"})
        self.assertEqual([i.code for i in self.inv.search("IBU")], ["PAN-002"])

    def test_search_with_category_filter(self):
        self.assertEqual(len(self.inv.search("", "Vitamins")), 2)
        self.assertEqual(self.inv.search("paracetamol", "Vitamins"), [])

    def test_blank_search_returns_everything(self):
        self.assertEqual(len(self.inv.search("  ")), 4)

    def test_no_match(self):
        self.assertEqual(self.inv.search("zzz"), [])

    def test_sort_by_quantity_both_ways(self):
        asc = [i.quantity for i in self.inv.sorted_by("quantity")]
        self.assertEqual(asc, [0, 10, 40, 100])
        desc = [i.quantity for i in self.inv.sorted_by("quantity", descending=True)]
        self.assertEqual(desc, [100, 40, 10, 0])

    def test_sort_by_name_ignores_case(self):
        self.inv.add(make_item("ABC-001", "aspirin"))
        self.assertEqual(self.inv.sorted_by("name")[0].name, "aspirin")

    def test_bad_sort_field(self):
        with self.assertRaises(StockError):
            self.inv.sorted_by("colour")


class ReportTests(InventoryTestCase):
    def test_low_stock_includes_boundary(self):
        # PAN-002 has exactly its reorder level (10), so it counts as low
        self.assertEqual([i.code for i in self.inv.low_stock()], ["VIT-001", "PAN-002"])

    def test_expiring_within(self):
        found = [i.code for i in self.inv.expiring_within(30, TODAY)]
        self.assertEqual(found, ["VIT-002", "PAN-002"])
        self.assertEqual([i.code for i in self.inv.expiring_within(0, TODAY)], ["VIT-002"])

    def test_expiring_boundary_day(self):
        # PAN-002 expires on 2026-12-01, which is 9 days after TODAY
        self.assertIn(self.inv.get("PAN-002"), self.inv.expiring_within(9, TODAY))
        self.assertNotIn(self.inv.get("PAN-002"), self.inv.expiring_within(8, TODAY))

    def test_category_summary_and_total(self):
        summary = self.inv.category_summary()
        self.assertEqual(list(summary), ["Painkillers", "Vitamins"])
        self.assertEqual(summary["Vitamins"], (2, 40, 300.0))
        self.assertAlmostEqual(self.inv.total_value(), 99 + 14.9 + 300)

    def test_best_sellers(self):
        self.inv.sell("PAN-001", 2, TODAY)
        self.inv.sell("PAN-002", 5, TODAY)
        self.inv.sell("PAN-001", 1, TODAY)
        self.assertEqual(self.inv.best_sellers(), [("Ibuprofen", 5, 7.45),
                                                   ("Paracetamol", 3, 2.97)])
        self.assertAlmostEqual(self.inv.total_revenue(), 10.42)

    def test_empty_inventory_reports(self):
        empty = Inventory()
        self.assertEqual(empty.low_stock(), [])
        self.assertEqual(empty.expiring_within(30), [])
        self.assertEqual(empty.category_summary(), {})
        self.assertEqual(empty.total_value(), 0)
        self.assertEqual(empty.best_sellers(), [])


class ItemStatusTests(unittest.TestCase):
    def test_status_labels(self):
        self.assertEqual(make_item("A-1", expiry=date(2026, 11, 21)).status(TODAY), "EXPIRED")
        self.assertEqual(make_item("A-1", expiry=TODAY).status(TODAY), "Expiring")
        self.assertEqual(make_item("A-1", quantity=10).status(TODAY), "Low stock")
        self.assertEqual(make_item("A-1", quantity=11).status(TODAY), "OK")


if __name__ == "__main__":
    unittest.main()
