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


def training_profile(events, metadata, train_end, positive_rating, history_thresholds):
    """Category selection statistics use only events strictly before the cutoff."""
    from itertools import groupby

    import numpy as np

    train = [event for event in events if event.timestamp < train_end]
    users = Counter(event.user for event in train)
    items = {event.item for event in train}
    histories, prefixes = defaultdict(set), Counter()
    eligible = repeats = tied = 0
    for _, batch in groupby(train, key=lambda event: event.timestamp):
        batch = list(batch)
        by_user = Counter(event.user for event in batch)
        tied += sum(count for count in by_user.values() if count > 1)
        for event in batch:
            if event.rating < positive_rating:
                continue
            if event.item in histories[event.user]:
                repeats += 1
            else:
                eligible += 1
                prefixes[len(histories[event.user])] += 1
        for event in batch:
            histories[event.user].add(event.item)
    return {
        "selection_scope": "base_train_only", "train_end_ms_exclusive": train_end,
        "events": len(train), "users": len(users), "items": len(items),
        "positive_rating_counts": dict(sorted(Counter(event.rating for event in train).items())),
        "users_with_at_least_n_events": {str(n): sum(count >= n for count in users.values())
                                         for n in history_thresholds},
        "history_length_quantiles": {str(q): float(np.quantile(list(users.values()), q))
                                     for q in (0, .25, .5, .75, .9, .99, 1)},
        "eligible_positive_unseen_events": eligible,
        "positive_repeat_events_excluded": repeats,
        "eligible_with_prefix_at_least_n": {str(n): sum(count for length, count in prefixes.items()
                                                        if length >= n) for n in history_thresholds},
        "same_user_timestamp_tied_events": tied,
        "metadata_coverage": {key: sum(bool(metadata.get(item, {}).get(key)) for item in items)
                               / len(items) if items else None
                               for key in ("title", "categories", "features")},
        "dense_item_similarity_float64_gib": len(items) ** 2 * 8 / 2 ** 30,
        "metadata_visibility": "snapshot_assumed_static",
    }
