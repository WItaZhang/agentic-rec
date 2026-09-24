import pytest

from src.policy_analysis import evaluate_decisions


def test_policy_replay_retains_failed_and_unrecalled_users_and_unknown_costs():
    outcomes = [{"request_id": f"q{i}", "user_id": f"u{i}", "plan": plan,
        "candidate_hash": f"c{i}", "ndcg": float(i == 1 and plan == 'R1'),
        "hr": float(i == 1 and plan == 'R1'), "candidate_recall": float(i != 0),
        "history_count": i, "repair_errors": ["failed"] if i == 2 and plan == 'R1' else []}
        for i in range(3) for plan in ('R0', 'R1')]
    calls = [{"request_id": f"q{i}", "plan": 'R1', 'actual_known_usd': None if i == 2 else .001,
        'reserved_usd': .01, 'usage': None if i == 2 else {'input_tokens': 100},
        'status': 'generation_error' if i == 2 else 'completed'} for i in range(3)]
    decisions = {'request_ids': ['q0', 'q1', 'q2'], 'label_access': False,
        'actions': {'fixed_R0': ['R0'] * 3, 'fixed_R1': ['R1'] * 3}}
    config = {'seed': 42, 'bootstrap_repetitions': 50, 'confidence': .95,
        'minimum_group_users_for_interval': 30, 'noninferiority_tolerance': .002,
        'comparisons': [['fixed_R1', 'fixed_R0']], 'group_boundaries': [['zero', 0, 1]],
        'primary_comparison': ['fixed_R1', 'fixed_R0']}
    result, _ = evaluate_decisions(outcomes, calls, decisions, ['R0', 'R1'], config)
    row = result['methods']['fixed_R1']
    assert row['users'] == 3
    assert row['mean_ndcg'] == pytest.approx(1 / 3)
    assert row['mean_accounted_usd'] == pytest.approx(.012 / 3)
    assert row['unknown_usage_requests'] == 1
    assert row['mean_failed'] == pytest.approx(1 / 3)
    assert row['p95_service_ms'] is None
    assert result['comparisons']['fixed_R1_minus_fixed_R0']['noninferiority']['supported'] is False
    decisions['request_ids'].pop()
    with pytest.raises(ValueError, match='complete'):
        evaluate_decisions(outcomes, calls, decisions, ['R0', 'R1'], config)
