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
