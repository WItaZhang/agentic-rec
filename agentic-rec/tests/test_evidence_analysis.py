import pytest

from src.evidence_analysis import analyze_matrix, validate_table


def test_missing_method_cannot_be_silently_dropped():
    row = {"request_id": "q", "user_id": "u", "plan": "R0"}
    with pytest.raises(ValueError, match="Incomplete"):
        validate_table([row], [], ["R0", "R1"])


def test_base_candidate_snapshot_must_match_when_recorded():
    outcomes = [{"request_id": "q", "user_id": "u", "plan": plan, "candidate_hash": plan}
                for plan in ("R0", "R1")]
    with pytest.raises(ValueError, match="Unpaired"):
        validate_table(outcomes, [{"request_id": "q", "plan": "R1"}], ["R0", "R1"])


def test_failure_keeps_denominator_and_conservative_cost():
    outcomes = [{"request_id": "q", "user_id": "u", "plan": plan, "ndcg": 0.0, "hr": 0.0,
                 "candidate_recall": 0.0, "candidate_hash": "frozen", "history_count": 0,
                 "service_latency_ms": 1.0, "repair_errors": ["short_output"] if plan == "R1" else []}
                for plan in ("R0", "R1")]
    calls = [{"request_id": "q", "plan": "R1", "actual_known_usd": None, "reserved_usd": 0.01,
              "usage": None, "generation_attempts": 1}]
    result = analyze_matrix(outcomes, calls, {"plans": ["R0", "R1"], "comparisons": [["R1", "R0"]],
        "history_groups": [["zero", 0, 1]], "bootstrap_repetitions": 50, "seed": 42,
        "confidence": 0.95, "normal_z_alpha": 1.96, "normal_z_power": .84,
        "minimum_detectable_difference": .01})
    assert result["methods"]["R1"]["requests"] == 1
    assert result["methods"]["R1"]["mean_accounted_usd"] == 0.01
    assert result["methods"]["R1"]["unknown_usage_attempts"] == 1
    assert result["methods"]["R1"]["fallback_or_repair_requests"] == 1
