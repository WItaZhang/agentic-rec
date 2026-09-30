import pytest

from src.metrics import service_latency_summary
from src.policy_inference import serving_policy_bindings


@pytest.fixture
def selected():
    return {'chosen': {
        'rule_0.25': {'policy': {'kind': 'rule', 'rule': 'base'}},
        'learned_0.25': {'policy': {'kind': 'learned', 'estimator_id': 0, 'cost_weight': .3},
                         'random_control': {'probabilities': [1, 0], 'seed': 17}},
        'rule_1.5': {'policy': {'kind': 'rule', 'rule': 'recent_if_no_history'}},
        'learned_1.5': {'policy': {'kind': 'learned', 'estimator_id': 1, 'cost_weight': .01},
                        'random_control': {'probabilities': [.9, .1], 'seed': 19}}}}


def test_secondary_serving_preserves_primary_and_uses_its_own_matched_control(selected):
    primary = serving_policy_bindings(selected, .25)
    both = serving_policy_bindings(selected, .25, [1.5])
    assert {name: both[name] for name in primary} == primary
    assert both['learned_1.5']['specification']['estimator_id'] == 1
    assert both['learned_1.5']['specification']['cost_weight'] == .01
    assert both['rule_1.5']['specification']['rule'] == 'recent_if_no_history'
    assert both['random_1.5']['selected_policy'] == 'learned_1.5'
    assert both['random_1.5']['specification'] == {'kind': 'random', 'probabilities': [.9, .1], 'seed': 19}
    assert primary['random']['specification']['probabilities'] == [1, 0]


@pytest.mark.parametrize('budgets', [[.25], [1.5, 1.5]])
def test_duplicate_serving_points_cannot_duplicate_audit_requests(selected, budgets):
    with pytest.raises(ValueError, match='distinct'):
        serving_policy_bindings(selected, .25, budgets)


def test_unselected_serving_budget_cannot_create_a_new_policy(selected):
    with pytest.raises(ValueError, match='already frozen'):
        serving_policy_bindings(selected, .25, [123])


def test_rare_slow_generation_remains_visible_without_changing_request_denominator():
    rows = [{'service_ms': 1, 'generation_attempts': 0}] * 124
    rows += [{'service_ms': 10000, 'generation_attempts': 1}] * 4
    result = service_latency_summary(rows)
    assert result['mean_service_ms'] == 313.46875
    assert result['p95_service_ms'] == 1
    assert result['generation_service_observations'] == 4
    assert result['mean_generation_service_ms'] == result['p95_generation_service_ms'] == 10000


def test_zero_generation_branch_is_unobserved_not_invented_zero_latency():
    result = service_latency_summary([{'service_ms': 2, 'generation_attempts': 0}])
    assert result['generation_service_observations'] == 0
    assert result['p95_generation_service_ms'] is None and result['mean_generation_service_ms'] is None
    with pytest.raises(ValueError, match='observed requests'):
        service_latency_summary([])
