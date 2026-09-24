import pytest

from src.result_archive import numeric_reproduction, public_outcomes


def test_public_rows_strip_user_ids_and_text_while_preserving_bootstrap_order():
    source = [{'user_id': user, 'request_id': f'q{i}', 'ndcg': i / 10,
               'review': 'private review', 'input': 'prompt', 'credential': 'secret'}
              for i, user in enumerate(['z_user', 'a_user', 'z_user', 'm_user'])]
    result = public_outcomes(source)
    assert [r['user_id'] for r in result] == ['user_00000002', 'user_00000000', 'user_00000002', 'user_00000001']
    assert [r['request_id'] for r in result] == ['q0', 'q1', 'q2', 'q3']
    assert all(set(r) == {'user_id', 'request_id', 'ndcg'} for r in result)


def test_reanalysis_tolerance_cannot_hide_changed_users_or_meaningful_metric_changes():
    assert numeric_reproduction({'n': 5, 'q': .1 + 1e-17}, {'n': 5, 'q': .1}, 1e-14)['matches']
    assert not numeric_reproduction({'n': 6, 'q': .1}, {'n': 5, 'q': .1}, 1e-14)['matches']
    assert not numeric_reproduction({'q': .101}, {'q': .1}, 1e-14)['matches']
    with pytest.raises(ValueError):
        numeric_reproduction(.101, .1, .01)
