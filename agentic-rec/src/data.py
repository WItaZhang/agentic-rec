"""Read-only MovieLens loading, validation and global temporal splitting."""

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, order=True)
class Rating:
    timestamp: int
    user: int
    item: int
    rating: int


def load_ratings(path: Path) -> list[Rating]:
    rows, pairs = [], set()
    with path.open(encoding="utf-8") as stream:
        for number, line in enumerate(stream, 1):
            try:
                user, item, rating, timestamp = map(int, line.split())
            except ValueError as error:
                raise ValueError(f"Invalid four-column rating at line {number}") from error
            if min(user, item, timestamp) <= 0 or not 1 <= rating <= 5:
                raise ValueError(f"Invalid rating value at line {number}")
            if (user, item) in pairs:
                raise ValueError(f"Duplicate user/item at line {number}")
            pairs.add((user, item))
            rows.append(Rating(timestamp, user, item, rating))
    if not rows:
        raise ValueError("Ratings file is empty")
    return sorted(rows)


def temporal_split(rows: list[Rating], train_end: int, validation_end: int):
    if train_end >= validation_end:
        raise ValueError("train_end must precede validation_end")
    splits = {"train": [], "validation": [], "test": []}
    for row in sorted(rows):
        name = "train" if row.timestamp < train_end else (
            "validation" if row.timestamp < validation_end else "test"
        )
        splits[name].append(row)
    if any(not split for split in splits.values()):
        raise ValueError("All three temporal partitions must contain ratings")
    return splits


@dataclass(frozen=True)
class ReviewEvent:
    timestamp: int
    user: str
    item: str
    rating: float
    event_id: str
    text: str = ""


def load_amazon_reviews(path):
    """Read full immutable gzipped JSONL; IDs join through parent_asin, time is ms."""
    import gzip
    import hashlib
    import json
    import math
    from collections import Counter

    events, exact, audit = [], set(), Counter()
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line_number, line in enumerate(stream, 1):
            audit["raw_rows"] += 1
            try:
                row = json.loads(line)
                user, item = row["user_id"], row["parent_asin"]
                timestamp, rating = row["timestamp"], float(row["rating"])
                if not isinstance(user, str) or not user or not isinstance(item, str) or not item:
                    raise ValueError("Invalid ID")
                if not isinstance(timestamp, int) or isinstance(timestamp, bool) or timestamp <= 0:
                    raise ValueError("Invalid millisecond timestamp")
                if not math.isfinite(rating) or not 1 <= rating <= 5:
                    raise ValueError("Invalid rating")
                text = row.get("text", "")
                if not isinstance(text, str):
                    raise ValueError("Invalid review text")
            except (ValueError, KeyError, TypeError):
                audit["invalid_rows"] += 1
                continue
            identity = hashlib.sha256(json.dumps(row, sort_keys=True).encode()).digest()
            if identity in exact:
                audit["exact_duplicates_removed"] += 1
                continue
            exact.add(identity)
            events.append(ReviewEvent(timestamp, user, item, rating, f"e{line_number:09d}", text))
    audit["valid_events"] = len(events)
    if not events:
        raise ValueError("No valid review events")
    return sorted(events, key=lambda r: (r.timestamp, r.event_id)), dict(audit)


def load_amazon_metadata(path, allowed_fields):
    import gzip
    import json

    if set(allowed_fields) - {"title", "categories", "features", "description"}:
        raise ValueError("Metadata fields must be static text allowlist; snapshot statistics forbidden")
    metadata = {}
    with gzip.open(path, "rt", encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            item = row["parent_asin"]
            if item in metadata:
                raise ValueError(f"Duplicate parent metadata: {item}")
            metadata[item] = {key: row.get(key) for key in allowed_fields}
    return metadata
