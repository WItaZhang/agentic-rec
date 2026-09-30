import pytest

from src.operational_accounting import incremental_polls, summarize_operations


def test_resumed_polling_counts_only_new_invocations():
    assert incremental_polls({'poll_calls': 100}) == 100
    assert incremental_polls({'poll_calls': 180}, {'poll_calls': 100}) == 80
    with pytest.raises(ValueError, match='regressed'):
        incremental_polls({'poll_calls': 99}, {'poll_calls': 100})


def test_counterfactual_aliases_and_copied_journals_do_not_inflate_operations():
    entries = {'ok': {'status': 'completed'}, 'failed': {'status': 'generation_error'},
               'rejected': {'status': 'submission_rejected_before_generation'}}
    good = {'call_id': 'ok', 'generation_attempts': 1, 'count_endpoint_calls': 1,
            'usage': {'input_tokens': 100, 'output_tokens': 36}, 'evidence': {'tool_calls': 3}}
    alias = {**good, 'generation_attempts': 0, 'count_endpoint_calls': 0, 'reused_generation': True}
    failed = {'call_id': 'failed', 'generation_attempts': 1, 'count_endpoint_calls': 1,
              'usage': None, 'evidence': {'tool_calls': 2}, 'repair_errors': ['empty_ranking']}
    count_only = {'status': 'count_error', 'generation_attempts': 0, 'count_endpoint_calls': 1,
                  'usage': None, 'total_latency_ms': 10.123}
    records = [good, good, alias, failed, failed, count_only, count_only,
               {'call_id': 'rejected', 'generation_attempts': 0, 'usage': None}]
    result = summarize_operations(entries, records, {'ok'}, {'ok'})
    assert result['physical_generation_attempts_recorded'] == 2
    assert result['generation_status_failures_or_incomplete'] == 1
    assert result['synchronous_token_count_calls_with_reserved_identity'] == 2
    assert result['count_only_error_operations'] == 1
    assert result['logical_local_evidence_accesses_for_generations'] == 5
    assert result['generated_calls_with_ranking_validation'] == 2
    assert result['physical_outputs_repaired_or_replaced_by_fallback'] == 2


def test_legacy_usage_without_explicit_counter_is_observed_but_not_fabricated_tool_coverage():
    result = summarize_operations({'a': {'status': 'completed'}},
                                  [{'call_id': 'a', 'usage': {'input_tokens': 10, 'output_tokens': 1}}], set(), set())
    assert result['physical_generation_attempts_recorded'] == 1
    assert result['generated_calls_with_local_evidence_counter'] == 0
    assert result['generated_calls_with_ranking_validation'] == 0
    with pytest.raises(ValueError, match='conflicting'):
        summarize_operations({'a': {}}, [{'call_id': 'a', 'evidence': {'tool_calls': 2}},
                                         {'call_id': 'a', 'evidence': {'tool_calls': 3}}], set(), set())
