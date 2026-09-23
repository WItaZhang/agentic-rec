"""Leakage, input integrity and hand-computable ranking checks."""

import math

import pytest

from src.data import Rating, load_ratings, temporal_split
from src.trainer import evaluate, fit
from src.utils import prepare_paths, utc_seconds


def test_global_split_keeps_boundary_ties_together():
    rows = [Rating(t, t, 1, 5) for t in (29, 20, 19, 10, 9, 20)]
    parts = temporal_split(rows, 10, 20)
    assert [r.timestamp for r in parts["train"]] == [9]
    assert [r.timestamp for r in parts["validation"]] == [10, 19]
    assert [r.timestamp for r in parts["test"]] == [20, 20, 29]
    assert parts == temporal_split(list(reversed(rows)), 10, 20)


def test_future_popularity_never_enters_model_and_cold_items_are_misses():
    train = [Rating(1, 1, 1, 5), Rating(2, 2, 2, 5)]
    model, seen = fit(train, 4)
    future = [Rating(10, 1, 2, 5), Rating(11, 1, 99, 5)]
    metrics = evaluate(model, seen, future, 4, 2)
    assert model.recommend(seen[1], 2) == [2]
    assert metrics["recall_at_k"] == 0.5
    assert metrics["ndcg_at_k"] == pytest.approx(1 / (1 + 1 / math.log2(3)))
    assert metrics["cold_item_positives_counted_as_misses"] == 1


def test_cold_users_included_and_no_positives_reported():
    model, seen = fit([Rating(1, 1, 1, 5)], 4)
    metrics = evaluate(model, seen, [Rating(9, 2, 1, 5), Rating(9, 3, 1, 1)], 4, 1)
    assert metrics["cold_users_included"] == 1
    assert metrics["users_without_eligible_positives"] == 1
    assert metrics["recall_at_k"] == 1
    assert evaluate(model, seen, [Rating(9, 3, 1, 1)], 4, 1)["recall_at_k"] is None


@pytest.mark.parametrize("content", ["", "1 2 9 10", "1 2 3", "1 2 3 10\n1 2 4 11"])
def test_loader_rejects_corrupt_or_duplicate_data_without_writing(tmp_path, content):
    path = tmp_path / "u.data"
    path.write_text(content)
    before = path.read_bytes()
    with pytest.raises(ValueError):
        load_ratings(path)
    assert path.read_bytes() == before


def test_invalid_temporal_protocol_rejected():
    with pytest.raises(ValueError):
        temporal_split([Rating(1, 1, 1, 5)], 20, 10)
    with pytest.raises(ValueError):
        temporal_split([Rating(1, 1, 1, 5)], 10, 20)
    with pytest.raises(ValueError):
        utc_seconds("1998-01-01")


def test_output_cannot_touch_raw_or_source(tmp_path):
    config = {"data": {"raw_path": "data/raw/u.data", "processed_path": "data/raw/cache",
                       "staging_path": "data/staging"}, "logging": {"path": "logs"}}
    with pytest.raises(ValueError):
        prepare_paths(config, tmp_path)
    config["data"]["processed_path"] = "src/generated"
    with pytest.raises(ValueError):
        prepare_paths(config, tmp_path)
