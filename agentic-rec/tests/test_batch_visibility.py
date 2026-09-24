import pytest

pytest.importorskip("filelock")

from src.batch_matrix import canonicalize_plans


def test_common_draw_reuse_never_crosses_request_or_candidate_visibility():
    rows = [{"request_id": q, "plan": plan, "prompt_sha256": "same",
             "evidence": {"candidate_hash": candidate}}
            for q, plan, candidate in [("q1", "R1", "c"), ("q1", "R2", "c"),
                                       ("q2", "R1", "c"), ("q1", "R3", "different")]]
    logical, physical = canonicalize_plans(rows, True)
    assert len(physical) == 3
    assert logical[1]["canonical_id"] == "q1_R1"
    assert logical[2]["canonical_id"] == "q2_R1"
    assert len(canonicalize_plans(rows, False)[1]) == 4
