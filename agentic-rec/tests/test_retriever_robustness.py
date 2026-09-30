from copy import deepcopy

import pytest

from src.retriever_robustness import compare_retrievers


def tables():
    first, second = {}, {}
    for q in ('a', 'b', 'cold'):
        for table, base, rerank, pool in ((first, .2, .1, 'knn'), (second, .4, .5, 'sequence')):
            table[q] = {plan: {'user_id': q, 'history_count': 0, 'cold_item': q == 'cold',
                              'candidate_hash': pool, 'ndcg': value if q != 'cold' else 0,
                              'hr': int(q != 'cold'), 'candidate_recall': int(q != 'cold')}
                        for plan, value in [('R0', base), ('R1', rerank)]}
    settings = {'plans': ['R0', 'R1'], 'history_groups': [('empty', 0, 1), ('warm', 1, 1000)],
                'minimum_group_users_for_interval': 30, 'bootstrap_repetitions': 1000, 'seed': 42, 'confidence': .95}
    return first, second, settings


def test_interaction_uses_each_retrievers_own_baseline_and_keeps_misses():
    first, second, settings = tables()
    result = compare_retrievers(first, second, settings)
    assert result['overall']['users'] == 3
    effect = result['overall']['evidence_effect_interactions']['R1']['ndcg']
    assert effect['difference'] == pytest.approx(.2 * 2 / 3)
    assert result['identical_candidate_pools'] == 0
    assert result['history_groups']['warm']['users'] == 0
    assert result['history_groups']['empty']['base_second_minus_first']['ndcg']['ci_low'] is None


def test_cross_pool_analysis_rejects_unpaired_users_or_partial_actions():
    first, second, settings = tables()
    changed = deepcopy(second)
    changed.pop('cold')
    with pytest.raises(ValueError, match='complete request population'):
        compare_retrievers(first, changed, settings)
    changed = deepcopy(second)
    changed['a']['R0']['history_count'] = 2
    with pytest.raises(ValueError, match='Request identity'):
        compare_retrievers(first, changed, settings)
    changed = deepcopy(second)
    changed['a'].pop('R1')
    with pytest.raises(ValueError, match='Incomplete'):
        compare_retrievers(first, changed, settings)
