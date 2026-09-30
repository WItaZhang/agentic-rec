import hashlib
import json

import pytest

from src.batch_recovery import reconcile_scheduler_state, validate_recovery_inputs


def test_recovery_preserves_collected_and_accepted_shards():
    state = {"chunks": [{"state": "collected", "collection_run": "old"},
                        {"state": "submitting", "offset": 12}, {"state": "submitted", "batch_id": "accepted"}]}
    receipt = {"id": "recovered", "metadata": {"research_run": "failed_upload"}}
    fixed = reconcile_scheduler_state(state, 1, "logs/failed_upload", receipt)
    assert fixed['chunks'][0] == state['chunks'][0]
    assert fixed['chunks'][2] == state['chunks'][2]
    assert fixed['chunks'][1]['batch_id'] == 'recovered'
    assert state['chunks'][1]['state'] == 'submitting'
    with pytest.raises(ValueError, match='different shard'):
        reconcile_scheduler_state(state, 1, 'logs/unrelated', receipt)
    with pytest.raises(ValueError, match='Only the ambiguous'):
        reconcile_scheduler_state(state, 0, 'logs/failed_upload', receipt)


def test_upload_recovery_requires_same_payload_and_pending_ledger(tmp_path):
    common = {'model': 'dated', 'input': [], 'text': {}}
    body = {**common, 'store': False, 'temperature': 0, 'max_output_tokens': 256}
    reservation = {'call_id': 'reserved', 'reserved_usd': .01,
                   'prompt_sha256': hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest()}
    (tmp_path/'reservations.json').write_text(json.dumps({'q_R1': reservation}))
    (tmp_path/'batch_input.jsonl').write_text(json.dumps({'custom_id': 'q_R1', 'method': 'POST',
                                                        'url': '/v1/responses', 'body': body})+'\n')
    (tmp_path/'submission_error.json').write_text(json.dumps({'stage': 'file_upload'}))
    entries = {'reserved': {'event': 'reserve', 'run_id': tmp_path.name, 'reserved_usd': .01}}
    config = {'budget': {'per_run_paid_usd': 1}}
    original = {'llm': {'model': 'dated', 'temperature': 0, 'max_output_tokens': 256}}
    assert len(validate_recovery_inputs(tmp_path, config, original, entries)) == 1
    entries['reserved']['event'] = 'settle'
    with pytest.raises(ValueError, match='original pending'):
        validate_recovery_inputs(tmp_path, config, original, entries)
    entries['reserved']['event'] = 'reserve'
    original['llm']['temperature'] = 1
    with pytest.raises(ValueError, match='inference settings'):
        validate_recovery_inputs(tmp_path, config, original, entries)
    (tmp_path/'submission_error.json').write_text(json.dumps({'stage': 'batch_create'}))
    with pytest.raises(ValueError, match='unsubmitted file-upload'):
        validate_recovery_inputs(tmp_path, config, original, entries)
