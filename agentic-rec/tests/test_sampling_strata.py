import pytest

pytest.importorskip("filelock")

from src.data import ReviewEvent
from src.llm_experiment import choose_views


def test_training_strata_select_request_before_grouping_and_refuse_validation():
    rows = [ReviewEvent(1, "u", "a", 5, "e0"), ReviewEvent(2, "u", "b", 5, "e1"),
            ReviewEvent(1, "v", "a", 5, "e2")]
    config = {"data": {"base_train_end": "1970-01-01T00:00:00Z",
              "policy_train_end": "1970-01-01T00:00:01Z", "validation_end": "1970-01-01T00:00:02Z",
              "test_end": "1970-01-01T00:00:03Z"}, "protocol": {"positive_rating": 4},
              "evaluation": {"partition": "policy_train"}, "seed": 42,
              "sampling": {"mode": "policy_history_strata", "strata": [["zero", 0, 1, 1], ["warm", 1, 100, None]]}}
    views, audit, _ = choose_views(rows, config)
    assert len({v.user_id for v in views}) == len(views)
    assert all(0 < p <= 1 for p in audit["user_inclusion_probability_by_request"].values())
    config["evaluation"]["partition"] = "validation"
    with pytest.raises(ValueError, match="Training-only"):
        choose_views(rows, config)
