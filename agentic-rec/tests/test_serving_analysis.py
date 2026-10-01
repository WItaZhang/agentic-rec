import pytest

from src.serving_analysis import public_serving_records, summarize_serving


def test_latency_replay_retains_failures_costs_and_rare_generation_branch():
    rows = [{"request_id": f"q{i}", "method": "adaptive", "status": "completed" if i else "generation_error",
        "service_ms": 10.0 if i else 1000.0, "generation_attempts": int(i == 0),
        "count_endpoint_calls": int(i == 0), "usage": None,
        "actual_known_usd": 0.0 if i else None, "reserved_usd": .01,
        "repair_errors": [] if i else ["fallback"], "review": "private", "text": "private",
        "response_id": "private", "user_id": "private"} for i in range(100)]
    public = public_serving_records(rows)
    assert all(not ({"review", "text", "response_id", "user_id"} & set(row)) for row in public)
    result = summarize_serving(public, ["adaptive"], 100)["adaptive"]
    assert result["requests"] == 100
    assert result["mean_service_ms"] == 19.9
    assert result["p95_service_ms"] == 10.0
    assert result["generation_service_observations"] == 1
    assert result["mean_generation_service_ms"] == 1000.0
    assert result["repairs"] == 1
    assert result["mean_api_usd"] == pytest.approx(.0001)
    with pytest.raises(ValueError, match="Incomplete"):
        summarize_serving(public[:-1], ["adaptive"], 100)
    with pytest.raises(ValueError, match="duplicated"):
        summarize_serving(public + public[:1], ["adaptive"], 100)
    with pytest.raises(ValueError, match="Incomplete"):
        summarize_serving(public, ["adaptive", "base"], 100)
