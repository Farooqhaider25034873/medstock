import random
import unittest

from stock.sorting import merge_sort


class MergeSortTests(unittest.TestCase):
    def test_empty_and_single(self):
        self.assertEqual(merge_sort([]), [])
        self.assertEqual(merge_sort([7]), [7])

    def test_matches_sorted_on_random_data(self):
        random.seed(1)
        for size in (2, 3, 10, 101, 1000):
            data = [random.randint(-50, 50) for _ in range(size)]
            with self.subTest(size=size):
                self.assertEqual(merge_sort(data), sorted(data))
                self.assertEqual(merge_sort(data, reverse=True), sorted(data, reverse=True))

    def test_already_sorted_and_reversed(self):
        data = list(range(20))
        self.assertEqual(merge_sort(data), data)
        self.assertEqual(merge_sort(data[::-1]), data)

    def test_original_list_unchanged(self):
        data = [3, 1, 2]
        merge_sort(data)
        self.assertEqual(data, [3, 1, 2])

    def test_stable_for_equal_keys(self):
        pairs = [("b", 1), ("a", 2), ("c", 1), ("d", 2)]
        self.assertEqual(merge_sort(pairs, key=lambda p: p[1]),
                         [("b", 1), ("c", 1), ("a", 2), ("d", 2)])
        # descending should still keep equal items in their original order
        self.assertEqual(merge_sort(pairs, key=lambda p: p[1], reverse=True),
                         [("a", 2), ("d", 2), ("b", 1), ("c", 1)])


if __name__ == "__main__":
    unittest.main()
