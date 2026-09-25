import json

import pytest

pytest.importorskip("filelock")

from src.batch_experiment import settle_billing_rejection
from src.paid_budget import PaidBudget
from src.resource_audit import reconcile_usage


def test_only_definitive_pre_generation_billing_rejection_releases_reservations(tmp_path):
    budget = PaidBudget(tmp_path / 'ledger.jsonl', 'test', 50, 1, 45)
    identity = budget.reserve(.01, {'kind': 'batch_replication'})
    reservations = {'q_R1': {'call_id': identity, 'reserved_usd': .01}}
    error = {'stage': 'batch_create', 'http_status': 400, 'provider_code': 'billing_hard_limit_reached'}
    for changed in ({'http_status': None}, {'stage': 'file_upload'}, {'provider_code': None}):
        assert not settle_billing_rejection(budget, reservations, tmp_path, {**error, **changed})
        assert budget.snapshot()['pending_reservations'] == 1
    assert settle_billing_rejection(budget, reservations, tmp_path, error)
    assert budget.snapshot()['campaign_accounted_usd'] == 0
    rows = json.loads((tmp_path / 'results.json').read_text())
    assert rows[0]['usage'] is None
    summary = reconcile_usage(budget.entries(), rows)['test']
    assert summary['rejected_before_generation'] == 1
    assert summary['usage_observed_attempts'] == summary['input_tokens'] == 0
    assert summary['known_usage_priced_usd'] == 0
    rows[0]['http_status'] = 500
    with pytest.raises(ValueError, match='lacks'):
        reconcile_usage(budget.entries(), rows)
