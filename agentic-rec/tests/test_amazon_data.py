import gzip
import json

import pytest

from src.data import ReviewEvent, load_amazon_metadata, load_amazon_reviews
from src.feature import training_profile


def test_amazon_loader_uses_parent_id_and_deduplicates(tmp_path):
    row = {"user_id": "u", "parent_asin": "p", "asin": "variant", "rating": 4,
           "timestamp": 123, "text": "history"}
    path = tmp_path / "review.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        for value in (row, row, {**row, "rating": 7}):
            stream.write(json.dumps(value) + "\n")
    events, audit = load_amazon_reviews(path)
    assert events[0].item == "p"
    assert len(events) == 1 and events[0].timestamp == 123
    assert audit["exact_duplicates_removed"] == 1 and audit["invalid_rows"] == 1


def test_metadata_future_statistics_cannot_enter(tmp_path):
    path = tmp_path / "meta.gz"
    with gzip.open(path, "wt", encoding="utf-8") as stream:
        stream.write(json.dumps({"parent_asin": "p", "title": "Title", "rating_number": 999}))
    assert load_amazon_metadata(path, ["title"])["p"] == {"title": "Title"}
    with pytest.raises(ValueError):
        load_amazon_metadata(path, ["rating_number"])


def test_profile_future_perturbation_and_timestamp_batch():
    rows = [ReviewEvent(1, "u", "a", 5, "e1"), ReviewEvent(1, "u", "b", 5, "e2"),
            ReviewEvent(2, "u", "c", 5, "e3")]
    before = training_profile(rows, {}, 3, 4, [1, 2])
    after = training_profile(rows + [ReviewEvent(9, "v", "future", 5, "e4")], {}, 3, 4, [1, 2])
    assert before == after
    assert before["eligible_with_prefix_at_least_n"] == {"1": 1, "2": 1}
    assert before["same_user_timestamp_tied_events"] == 2
