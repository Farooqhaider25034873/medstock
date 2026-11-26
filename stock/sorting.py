"""Merge sort used for every sorted view in the app."""


def merge_sort(items, key=lambda x: x, reverse=False):
    """Return a new sorted list. Stable, so ties keep their original order."""
    if len(items) <= 1:
        return list(items)

    middle = len(items) // 2
    left = merge_sort(items[:middle], key, reverse)
    right = merge_sort(items[middle:], key, reverse)
    return _merge(left, right, key, reverse)


def _merge(left, right, key, reverse):
    merged = []
    i = j = 0

    while i < len(left) and j < len(right):
        a, b = key(left[i]), key(right[j])
        # taking from the left on a tie is what keeps the sort stable
        take_left = a >= b if reverse else a <= b
        if take_left:
            merged.append(left[i])
            i += 1
        else:
            merged.append(right[j])
            j += 1

    merged.extend(left[i:])
    merged.extend(right[j:])
    return merged
