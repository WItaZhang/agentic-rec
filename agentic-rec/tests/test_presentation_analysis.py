from copy import deepcopy

import pytest

from src.presentation_analysis import join_presentations


def test_presentation_join_keeps_failures_and_rejects_candidate_or_population_changes():
    rows = [{'request_id': q, 'user_id': q, 'plan': plan, 'candidate_hash': q,
             'ranking': ['a'], 'ndcg': 0, 'hr': 0, 'candidate_recall': 0,
             'history_count': 0, 'cold_item': True}
            for q in ['q1', 'q2'] for plan in ['R0', 'R1']]
    calls = [{'request_id': q, 'plan': 'R1', 'status': 'failed', 'actual_known_usd': None}
             for q in ['q1', 'q2']]
    combined, attempts = join_presentations(rows, calls, rows, calls, ['R1'])
    assert len(combined) == 6 and len(attempts) == 4
    assert all(r['status'] == 'failed' for r in attempts)
    assert {r['plan'] for r in combined} == {'R0', 'ordered_R1', 'shuffled_R1'}
    changed = deepcopy(rows)
    changed[0]['ranking'] = ['b']
    with pytest.raises(ValueError, match='changed base ranking'):
        join_presentations(rows, calls, changed, calls, ['R1'])
    with pytest.raises(ValueError, match='identical request population'):
        join_presentations(rows, calls, rows[:2], calls[:1], ['R1'])
    changed = deepcopy(rows)
    changed[1]['candidate_hash'] = 'different'
    with pytest.raises(ValueError, match='Unpaired candidates'):
        join_presentations(rows, calls, changed, calls, ['R1'])
