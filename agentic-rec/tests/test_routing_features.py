import numpy as np

from src.data import ReviewEvent
from src.feature import routing_features
from src.protocol import CandidateSnapshot, RequestView
from src.routing_model import UtilityRouter


def test_features_ignore_user_identity_and_text():
    one = RequestView("q", "u", 86400002, (ReviewEvent(1, "u", "a", 5, "e1", "secret text"),), "policy_train")
    two = RequestView("q", "v", 86400002, (ReviewEvent(1, "v", "a", 5, "e2", "different text"),), "validation")
    snapshot = CandidateSnapshot("q", ("b", "c"), (0., 0.), "m", 86400002)
    assert routing_features(one, snapshot, {"a", "b", "c"}, 4) == routing_features(two, snapshot, {"a", "b", "c"}, 4)
    assert routing_features(one, snapshot, {"a"}, 4)["base_score_entropy_proxy"] == 1.0


def test_router_accounts_cost_and_ties_without_any_labels():
    class Estimator:
        def predict(self, x):
            return np.array([[0.02, 0.025] for _ in x])
    policy = UtilityRouter(Estimator(), ("R0", "R1", "R4"), ("has_history",), (0, .001, .003), .01)
    assert policy.decide([{"has_history": 1}]) == ["R1"]
    policy.cost_weight = .1
    assert policy.decide([{"has_history": 1}]) == ["R0"]
