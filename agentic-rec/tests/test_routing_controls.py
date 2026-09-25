import numpy as np
import pytest

from src.routing_trainer import random_actions, random_probabilities, rule_actions


def test_random_allocation_matches_cost_in_expectation_and_is_order_invariant():
    plans = ("R0", "R1", "R4")
    costs = np.array([[0., .001, .003], [0., .002, .004]])
    random = random_probabilities(["R0", "R4"], costs, plans)
    assert sum(random["probabilities"]) == pytest.approx(1)
    assert random["expected_validation_usd"] == pytest.approx(random["target_validation_usd"])
    a = random_actions(["q1", "q2"], random["probabilities"], plans, 42)
    b = random_actions(["q2", "q1"], random["probabilities"], plans, 42)
    assert a == b[::-1]
    all_base = random_probabilities(["R0", "R0"], costs, plans)
    assert random_actions(["q1", "q2"], all_base["probabilities"], plans, 42) == ["R0", "R0"]


def test_history_rule_skips_empty_history_and_unknown_rules_fail():
    features = [{"has_history": 0, "has_older_history": 0, "positive_fraction": 0},
                {"has_history": 1, "has_older_history": 1, "positive_fraction": .5}]
    assert rule_actions(features, "full_if_older") == ["R0", "R4"]
    with pytest.raises(ValueError):
        rule_actions(features[:1], "typo")


def test_development_justified_rules_can_choose_empty_history_without_labels():
    features = [{"has_history": 0, "has_older_history": 0},
                {"has_history": 1, "has_older_history": 0},
                {"has_history": 1, "has_older_history": 1}]
    assert rule_actions(features, "recent_if_no_history") == ["R1", "R0", "R0"]
    assert rule_actions(features, "recent_unless_older") == ["R1", "R1", "R0"]
