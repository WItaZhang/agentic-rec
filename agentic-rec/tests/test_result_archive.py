from src.result_archive import public_outcomes


def test_public_rows_strip_user_ids_and_text_while_preserving_bootstrap_order():
    source = [{'user_id': user, 'request_id': f'q{i}', 'ndcg': i / 10,
               'review': 'private review', 'input': 'prompt', 'credential': 'secret'}
              for i, user in enumerate(['z_user', 'a_user', 'z_user', 'm_user'])]
    result = public_outcomes(source)
    assert [r['user_id'] for r in result] == ['user_00000002', 'user_00000000', 'user_00000002', 'user_00000001']
    assert [r['request_id'] for r in result] == ['q0', 'q1', 'q2', 'q3']
    assert all(set(r) == {'user_id', 'request_id', 'ndcg'} for r in result)
