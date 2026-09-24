import pytest

from src.policy_analysis import compare_additional_baselines, evaluate_decisions


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
    assert result['failure_attribution']['fixed_R1']['unrecalled_targets'] == 1
    assert result['failure_attribution']['fixed_R1']['baseline_misses_rescued'] == 1
    assert result['failure_attribution']['fixed_R1']['api_usd_on_unrecalled_targets'] == .001
    assert result['comparisons']['fixed_R1_minus_fixed_R0']['noninferiority']['supported'] is False
    decisions['actions'].update({'learned_0.25': ['R1'] * 3, 'random_0.25': ['R0'] * 3})
    decisions['random_parameters'] = {'random_0.25': {'probabilities': [.5, .5], 'seed': 1729}}
    config['random_sensitivity_seeds'] = [11, 97]
    result, _ = evaluate_decisions(outcomes, calls, decisions, ['R0', 'R1'], config)
    diagnostic = result['random_control_diagnostics']['random_0.25']
    assert diagnostic['expected_ndcg'] == pytest.approx(1 / 6)
    assert diagnostic['expected_accounted_usd'] == pytest.approx(.002)
    assert diagnostic['learned_minus_expected_random_ndcg']['difference'] == pytest.approx(1 / 6)
    assert len(diagnostic['allocation_seed_sensitivity']) == 2
    decisions['request_ids'].pop()
    with pytest.raises(ValueError, match='complete'):
        evaluate_decisions(outcomes, calls, decisions, ['R0', 'R1'], config)


def test_additional_base_comparison_aligns_requests_and_keeps_cold_targets():
    rows = {'fixed_R0': [{'request_id': 'q1', 'ndcg': 0.0}, {'request_id': 'q2', 'ndcg': 0.0}]}
    extra = [{'request_id': q, 'plan': 'sequence', 'ndcg': value, 'hr': value,
              'candidate_recall': value, 'cold_item': not value} for q, value in [('q2', 1.0), ('q1', 0.0)]]
    settings = {'bootstrap_repetitions': 50, 'confidence': .95, 'seed': 42}
    result = compare_additional_baselines(extra, rows, settings)['sequence']
    assert result['mean_ndcg'] == .5
    assert result['cold_targets'] == 1
    assert result['ndcg_minus_main_base']['difference'] == .5
    with pytest.raises(ValueError, match='exactly once'):
        compare_additional_baselines(extra + extra[:1], rows, settings)
