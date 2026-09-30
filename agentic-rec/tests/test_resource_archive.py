from src.operational_accounting import summarize_operations
from src.resource_archive import compact_operation_records, compare_accounting
from src.resource_audit import reconcile_usage


def test_private_response_fields_are_removed_without_changing_accounting():
    entries = {'a': {'run_id': 'labels', 'event': 'settle', 'status': 'completed',
                     'actual_usd': .001, 'reserved_usd': .002}}
    row = {'call_id': 'a', 'status': 'completed', 'usage': {'input_tokens': 100, 'output_tokens': 36},
           'count_endpoint_calls': 1, 'generation_attempts': 1, 'text': 'private response text',
           'response_id': 'private provider id', 'user_id': 'private user',
           'evidence': {'tool_calls': 3, 'history_event_ids': ['private history'], 'review': 'private review'}}
    count_only = {'count_endpoint_calls': 1, 'generation_attempts': 0, 'usage': None,
                  'status': 'count_error', 'text': '', 'total_latency_ms': 123.456}
    records = [row, row, {**row, 'generation_attempts': 0, 'count_endpoint_calls': 0}, count_only, count_only]
    compact = compact_operation_records(records)
    assert len(compact) == 3
    assert 'private' not in str(compact)
    assert reconcile_usage(entries, compact) == reconcile_usage(entries, records)
    assert summarize_operations(entries, compact, {'a'}, set()) == summarize_operations(entries, records, {'a'}, set())


def test_accounting_replay_requires_exact_counts_and_only_float_roundoff():
    assert compare_accounting({'calls': 10, 'usd': .1}, {'calls': 10, 'usd': .1 + 1e-15}, 1e-12)['matches']
    assert not compare_accounting({'calls': 9}, {'calls': 10}, 1e-12)['matches']
    assert not compare_accounting({'calls': 10.0}, {'calls': 10}, 1e-12)['matches']
    assert not compare_accounting({'usd': .1}, {'usd': .2}, 1e-12)['matches']
