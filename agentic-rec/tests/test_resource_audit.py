import pytest

pytest.importorskip("filelock")

from src.resource_audit import is_scheduler_child, reconcile_usage


def test_usage_counts_shared_resumed_calls_once_and_retains_unknown_failures():
    entries = {"a": {"run_id": "labels", "event": "settle", "actual_usd": 0.001, "reserved_usd": 0.002},
               "b": {"run_id": "labels", "event": "settle", "actual_usd": None, "reserved_usd": 0.003}}
    row = {"call_id": "a", "usage": {"input_tokens": 100, "output_tokens": 10,
                                      "input_tokens_details": {"cached_tokens": 20}}}
    result = reconcile_usage(entries, [row, row, {"call_id": "b", "usage": None}])["labels"]
    assert result["input_tokens"] == 100
    assert result["physical_attempts"] == 2
    assert result["accounted_usd"] == 0.004
    assert result["unknown_settled"] == 1
    with pytest.raises(ValueError, match="Conflicting"):
        reconcile_usage(entries, [row, {**row, "usage": None}])
    with pytest.raises(ValueError, match="lacks"):
        reconcile_usage(entries, [])


def test_standalone_recovery_collection_is_not_hidden_as_nested_cpu():
    parent = {'stage': 'batch_schedule', 'experiment_name': 'amazon_policy_batch'}
    assert is_scheduler_child(parent, 'logs/20260925_072000_amazon_policy_batch_c011')
    assert not is_scheduler_child(parent, 'logs/20260925_073041_amazon_policy_batch_billing_collect')
    checkpoint = {**parent, 'stage': 'batch_recovery_checkpoint'}
    assert not is_scheduler_child(checkpoint, 'logs/20260925_072000_amazon_policy_batch_c011')
