import copy
import json

import pytest

from src.cost_alignment import calibrate, evaluate, verified_archive
from src.utils import digest


def example():
    ids, plans, actions = ["q0", "q1"], ["R0", "R1"], ["R0", "R1"]
    calls = [{"request_id": q, "plan": "R1", "actual_known_usd": cost, "usage": {"input_tokens": 1}}
             for q, cost in zip(ids, [.001, .003], strict=True)]
    rows = [{"request_id": q, "plan": plan, "user_id": q, "candidate_hash": q,
             "ndcg": float(plan == "R1"), "hr": float(plan == "R1")} for q in ids for plan in plans]
    return ids, plans, actions, calls, rows


def test_cost_calibration_is_invariant_to_quality_but_evaluation_is_not():
    ids, plans, actions, calls, rows = example()
    receipt, costs = calibrate(ids, actions, calls, plans, 1e-14)
    assert receipt["probabilities"] == pytest.approx([.25, .75])
    assert receipt["learner_mean_usd"] == pytest.approx(receipt["random_expected_mean_usd"])
    settings = {"bootstrap_repetitions": 50, "confidence": .95, "seed": 42}
    before = evaluate(rows, calls, ids, actions, plans, receipt, costs, settings, [1729])
    changed = copy.deepcopy(rows)
    changed[-1]["ndcg"] = 0.0
    after = evaluate(changed, calls, ids, actions, plans, receipt, costs, settings, [1729])
    assert before["quality"] != after["quality"]
    assert receipt == calibrate(ids, actions, calls, plans, 1e-14)[0]
    with pytest.raises(ValueError, match="Incomplete"):
        evaluate(rows[:-1], calls, ids, actions, plans, receipt, costs, settings, [1729])
    rows[-1]["user_id"] = "q0"
    rows[-2]["user_id"] = "q0"
    with pytest.raises(ValueError, match="independent"):
        evaluate(rows, calls, ids, actions, plans, receipt, costs, settings, [1729])


def test_missing_unknown_and_infeasible_costs_fail_instead_of_silent_mismatch():
    ids, plans, actions, calls, _ = example()
    with pytest.raises(ValueError, match="Complete cost"):
        calibrate(ids, actions, calls[:-1], plans, 1e-14)
    calls[0]["actual_known_usd"] = None
    with pytest.raises(ValueError, match="known observed"):
        calibrate(ids, actions, calls, plans, 1e-14)
    # Selecting each request's expensive action can exceed the maximum random
    # expectation attainable with that fixed conditional mixture.
    calls = [{"request_id": q, "plan": plan, "actual_known_usd": cost, "usage": {}}
             for q, plan, cost in [("q0", "R1", 9.), ("q0", "R2", 1.), ("q1", "R1", 1.), ("q1", "R2", 9.)]]
    with pytest.raises(ValueError, match="infeasible"):
        calibrate(ids, ["R1", "R2"], calls, ["R0", "R1", "R2"], 1e-14)


def test_changed_archive_is_rejected(tmp_path):
    payload = tmp_path / "calls.jsonl.gz"
    payload.write_bytes(b"archived bytes")
    manifest = tmp_path / "archive_manifest.json"
    manifest.write_text(json.dumps({"status": "completed", "kind": "policy", "files": {payload.name: digest(payload)}}))
    checksum = digest(manifest)
    verified_archive(tmp_path, checksum)
    payload.write_bytes(b"changed")
    with pytest.raises(ValueError, match="Archive file changed"):
        verified_archive(tmp_path, checksum)
    with pytest.raises(ValueError, match="manifest changed"):
        verified_archive(tmp_path, "0" * 64)
