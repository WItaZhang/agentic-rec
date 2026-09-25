import copy

import pytest

from src.failure_analysis import choose_case_ids, development_fixed_decisions, error_tags


def test_error_classes_separate_candidate_misses_from_reranking_losses():
    base = {"hr": 1, "ndcg": 0.5}
    outcome = {"hr": 0, "ndcg": 0, "candidate_recall": 1, "history_count": 2}
    assert error_tags(base, outcome, {"status": "completed"}) == ["baseline_hit_lost", "rank_quality_loss"]
    base = {"hr": 0, "ndcg": 0}
    outcome.update(candidate_recall=0, cold_item=True, history_count=0, repair_errors=["short_output"])
    assert error_tags(base, outcome, {"status": "batch_error"}) == [
        "cold_target", "retrieval_miss", "no_history_miss", "api_failure", "ranking_repair"]


def test_example_selection_does_not_prefer_bigger_quality_losses():
    tagged = {f"q{i}": ["loss"] for i in range(40)}
    selected = choose_case_ids(tagged, 3, 42)
    assert selected == choose_case_ids(dict(reversed(list(tagged.items()))), 3, 42)
    assert len(selected["loss"]) == 3


def test_development_diagnostics_reject_test_partial_or_selected_policy_inputs():
    source = {'evaluation': {'partition': 'validation'}, 'sampling': {'mode': 'uniform_users'},
              'evidence': {'plans': ['R1', 'R4']}}
    status = {'status': 'completed', 'test_scored': False}
    result = development_fixed_decisions(source, status, ['q2', 'q1'], ['fixed_R1', 'fixed_R4'])
    assert result['request_ids'] == ['q1', 'q2']
    assert result['actions']['fixed_R1'] == ['R1', 'R1'] and result['label_access'] is False
    for changed in ({'status': 'running'}, {'test_scored': True}):
        with pytest.raises(ValueError, match='population validation'):
            development_fixed_decisions(source, {**status, **changed}, ['q'], ['fixed_R1'])
    for section, key, value in [('evaluation', 'partition', 'test'), ('sampling', 'mode', 'history_strata')]:
        wrong = copy.deepcopy(source)
        wrong[section][key] = value
        with pytest.raises(ValueError, match='population validation'):
            development_fixed_decisions(wrong, status, ['q'], ['fixed_R1'])
    with pytest.raises(ValueError, match='fixed evidence'):
        development_fixed_decisions(source, status, ['q'], ['learned_0.25'])
