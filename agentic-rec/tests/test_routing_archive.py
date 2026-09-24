import numpy as np
import pytest

from src.routing_data import load_routing_matrix, save_routing_matrix
from src.utils import digest


def test_derived_router_archive_preserves_weights_and_cannot_be_test_training(tmp_path):
    path = tmp_path / "train.json.gz"
    data = {"ids": ["q1", "q2"], "features": [{"x": 0}, {"x": 1}],
        "source_config": {"evaluation": {"partition": "policy_train"},
                          "evidence": {"plans": ["R1"]}},
        "label_physical_cost": .001, "feature_ms": {"q1": 1, "q2": 1},
        "outcome_sha256": "original_outcomes", "calls_sha256": "original_calls",
        "quality": np.array([[0, 1.0], [0.5, 0]]), "costs": np.array([[0, .001], [0, .002]]),
        "fit_weights": np.array([.5, 1.5])}
    save_routing_matrix(path, data)
    settings = {"path": path.name, "sha256": digest(path)}
    restored = load_routing_matrix(tmp_path, settings, "policy_train", ["R0", "R1"])
    np.testing.assert_array_equal(restored["fit_weights"], data["fit_weights"])
    np.testing.assert_array_equal(restored["quality"], data["quality"])
    with pytest.raises(ValueError, match="partition"):
        load_routing_matrix(tmp_path, settings, "test", ["R0", "R1"])
    path.write_bytes(path.read_bytes() + b"changed")
    with pytest.raises(ValueError, match="changed"):
        load_routing_matrix(tmp_path, settings, "policy_train", ["R0", "R1"])
