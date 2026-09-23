from dataclasses import replace

import pytest

from src.data import ReviewEvent
from src.metrics import aggregate_requests, single_target_metrics
from src.protocol import (
    CandidateSnapshot,
    RequestView,
    hash_sample,
    replay_requests,
    validate_ranking,
)


def test_batch_visibility_and_boundary_isolation():
    events = [ReviewEvent(1, "u", "a", 5, "e1"), ReviewEvent(2, "u", "b", 5, "e2"),
              ReviewEvent(2, "u", "c", 5, "e3"), ReviewEvent(3, "u", "a", 5, "e4"),
              ReviewEvent(4, "u", "d", 5, "e5")]
    rows = list(replay_requests(events, [("train", 2), ("validation", 4), ("test", 5)], 4))
    assert len(rows) == 4  # repeated positive a is excluded
    assert [r.partition for r, _ in rows] == ["train", "validation", "validation", "test"]
    assert rows[1][0].history == rows[2][0].history == (events[0],)
    assert len(rows[3][0].history) == 4
    assert not hasattr(rows[1][0], "item_id")


def test_future_perturbation_cannot_change_prior_request_views():
    events = [ReviewEvent(1, "u", "a", 5, "e1"), ReviewEvent(2, "u", "b", 5, "e2")]
    boundaries = [("train", 2), ("test", 4)]
    before = list(replay_requests(events, boundaries, 4))
    after = list(replay_requests(events + [ReviewEvent(3, "u", "c", 5, "e3", "future")], boundaries, 4))
    assert before == after[:len(before)]
    # Current target identity/text changes labels, not current inference inputs.
    changed = [events[0], replace(events[1], item="secret", text="secret label")]
    assert before[-1][0] == list(replay_requests(changed, boundaries, 4))[-1][0]
    with pytest.raises(ValueError):
        RequestView("q", "u", 1, (events[0],), "test")


def test_fixed_candidates_repair_and_miss_denominator():
    candidates = CandidateSnapshot("q", ("a", "b"), (2., 1.), "model", 9)
    ranking, errors = validate_ranking(["secret", "b", "b"], candidates, 2)
    assert ranking == ("b", "a") and errors == ["duplicate", "outside_candidate", "short_output"]
    rows = [{"user_id": "u", **single_target_metrics(list(ranking), target, candidates.item_ids, 2)}
            for target in ("a", "cold")]
    metrics = aggregate_requests(rows)
    assert metrics["user_macro"]["hr"] == .5 and metrics["requests"] == 2
    assert candidates.item_ids == ("a", "b")


def test_sampling_order_independent_and_label_free():
    requests = [RequestView(f"q{i}", f"u{i // 2}", i, (), "test") for i in range(10)]
    sample, audit = hash_sample(requests, 3, 42)
    assert sample == hash_sample(list(reversed(requests)), 3, 42)[0]
    assert len(sample) == len({request.user_id for request in sample}) == 3
    assert audit["user_inclusion_probability"] == .6
