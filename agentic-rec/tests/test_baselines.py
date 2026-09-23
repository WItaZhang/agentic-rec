import math

import pytest

from src.baselines import evaluate_users, fit_itemknn
from src.data import Rating
from src.metrics import multipositive_metrics, paired_bootstrap


def test_knn_hand_computed_cosine_and_negative_feedback():
    rows = [Rating(1, 1, 1, 5), Rating(2, 1, 2, 4), Rating(3, 2, 1, 5),
            Rating(4, 2, 3, 5), Rating(5, 3, 2, 5), Rating(6, 3, 4, 1)]
    model, seen, positives = fit_itemknn(rows, 4, 10, 0)
    assert model.similarity[0, 1] == pytest.approx(0.5)
    assert model.similarity[0, 2] == pytest.approx(1 / math.sqrt(2))
    assert model.similarity.diagonal().sum() == 0
    assert model.similarity[3].nnz == 0
    assert 4 in seen[3] and 4 not in positives[3]
    assert model.recommend({1}, 3, {1}) == [3, 2, 4]
    assert model.recommend(set(), 2, set()) == [1, 2]


def test_knn_future_oov_and_miss_denominators():
    rows = [Rating(1, 1, 1, 5), Rating(2, 1, 2, 5), Rating(3, 2, 1, 1)]
    model, seen, positives = fit_itemknn(rows, 4, 1, 10)
    before = model.similarity.toarray().copy()
    future = [Rating(10, 3, 1, 5), Rating(11, 3, 99, 5)]
    outcomes = evaluate_users(model, seen, positives, future, 4, 2, 1)
    assert outcomes[0]["recall_at_k"] == .5
    assert outcomes[0]["cold_targets"] == 1
    assert outcomes[0]["group"] == "cold"
    assert (before == model.similarity.toarray()).all()
    assert model.recommend({99}, 2, {99}) == [1, 2]


def test_multitarget_metric_and_user_paired_intervals():
    assert multipositive_metrics([1, 2], {1, 99}, 2)["ndcg_at_k"] == pytest.approx(
        1 / (1 + 1 / math.log2(3)))
    stats = paired_bootstrap([1, 0], [0, 0], 1000, 42, .95)
    assert stats["difference"] == .5
    assert stats["unit"] == "user" and stats["ci_low"] <= .5 <= stats["ci_high"]
    with pytest.raises(ValueError):
        multipositive_metrics([1, 1], {1}, 2)
