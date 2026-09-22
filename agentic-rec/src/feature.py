"""Stateless transformations. No I/O and no model access."""

from collections import Counter, defaultdict

from .data import Rating


def popularity_features(rows: list[Rating], positive_rating: int):
    scores: Counter[int] = Counter()
    seen: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        seen[row.user].add(row.item)
        scores[row.item] += int(row.rating >= positive_rating)
    return dict(scores), dict(seen)


def relevant_items(rows: list[Rating], positive_rating: int):
    relevant: dict[int, set[int]] = defaultdict(set)
    for row in rows:
        if row.rating >= positive_rating:
            relevant[row.user].add(row.item)
    return dict(relevant)
