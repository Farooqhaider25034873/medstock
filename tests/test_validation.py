import unittest
from datetime import date

from stock.validation import (FormError, build_item, clean_code, clean_text, parse_date,
                              parse_expiry, parse_int, parse_price)

TODAY = date(2026, 11, 22)


class CodeTests(unittest.TestCase):
    def test_valid_code_is_upper_cased(self):
        self.assertEqual(clean_code("  pan-001 "), "PAN-001")

    def test_boundary_lengths(self):
        self.assertEqual(clean_code("AB-123"), "AB-123")
        self.assertEqual(clean_code("ABCD-12345"), "ABCD-12345")

    def test_invalid_codes(self):
        for bad in ["", "PAN001", "P-001", "PANEL-001", "PAN-01", "PAN-123456", "12-345"]:
            with self.subTest(code=bad), self.assertRaises(ValueError):
                clean_code(bad)


class TextTests(unittest.TestCase):
    def test_extra_spaces_removed(self):
        self.assertEqual(clean_text("  Vitamin   C  ", "Name"), "Vitamin C")

    def test_empty_rejected(self):
        with self.assertRaises(ValueError):
            clean_text("   ", "Name")

    def test_length_limit(self):
        self.assertEqual(len(clean_text("a" * 50, "Name")), 50)
        with self.assertRaises(ValueError):
            clean_text("a" * 51, "Name")


class NumberTests(unittest.TestCase):
    def test_int_range_edges(self):
        self.assertEqual(parse_int("0", "Qty"), 0)
        self.assertEqual(parse_int("100000", "Qty"), 100000)
        with self.assertRaises(ValueError):
            parse_int("-1", "Qty")
        with self.assertRaises(ValueError):
            parse_int("100001", "Qty")

    def test_int_rejects_non_numbers(self):
        for bad in ["", "abc", "2.5", "1e3"]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                parse_int(bad, "Qty")

    def test_price_rounded(self):
        self.assertEqual(parse_price("4.499"), 4.5)
        self.assertEqual(parse_price("0.01"), 0.01)

    def test_price_rejects_bad_values(self):
        for bad in ["0", "-2", "abc", "nan", "inf", "100000.01"]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                parse_price(bad)


class DateTests(unittest.TestCase):
    def test_valid_date(self):
        self.assertEqual(parse_date("2028-02-29"), date(2028, 2, 29))

    def test_impossible_or_badly_formatted_dates(self):
        for bad in ["2027-02-29", "2027-13-01", "31/12/2027", "tomorrow", ""]:
            with self.subTest(value=bad), self.assertRaises(ValueError):
                parse_date(bad)

    def test_expiry_must_be_after_today(self):
        self.assertEqual(parse_expiry("2026-11-23", TODAY), date(2026, 11, 23))
        with self.assertRaises(ValueError):
            parse_expiry("2026-11-22", TODAY)


class BuildItemTests(unittest.TestCase):
    def form(self, **changes):
        values = {"code": "abc-123", "name": "Test Tablets", "category": "first aid",
                  "quantity": "10", "price": "2.5", "expiry": "2030-01-01",
                  "reorder_level": "5"}
        values.update(changes)
        return values

    def test_good_form_builds_item(self):
        item = build_item(self.form())
        self.assertEqual(item.code, "ABC-123")
        self.assertEqual(item.category, "First Aid")
        self.assertEqual(item.expiry, date(2030, 1, 1))

    def test_every_bad_field_is_reported(self):
        with self.assertRaises(FormError) as ctx:
            build_item(self.form(code="x", quantity="many", price="0"))
        self.assertEqual(set(ctx.exception.errors), {"code", "quantity", "price"})

    def test_edit_allows_past_expiry(self):
        item = build_item(self.form(expiry="2020-01-01"), is_new=False)
        self.assertEqual(item.expiry, date(2020, 1, 1))
        with self.assertRaises(FormError):
            build_item(self.form(expiry="2020-01-01"))


if __name__ == "__main__":
    unittest.main()
