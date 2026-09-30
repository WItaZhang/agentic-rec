import hashlib
import json

import pytest

from src.batch_recovery import (
    LEGACY_UPLOAD_RECEIPT_SOURCE,
    reconcile_scheduler_state,
    validate_interrupted_upload_recovery,
    validate_recovery_inputs,
)
from src.utils import digest, write_json


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


@pytest.fixture
def interrupted_recovery(tmp_path):
    source, previous = tmp_path / 'source', tmp_path / 'previous'
    source.mkdir()
    previous.mkdir()
    (source / 'batch_input.jsonl').write_text('immutable payload')
    write_json(source / 'upload_recovery_intent.json', {
        'recovery_run': 'previous', 'input_sha256': digest(source / 'batch_input.jsonl')})
    write_json(previous / 'config.yaml', {'stage': 'batch_upload_recovery',
        'recovery': {'submission_run': 'source'}})
    write_json(previous / 'manifest.json', {'status': 'failed',
        'config_sha256': digest(previous / 'config.yaml'),
        'source_sha256': {'src/batch_recovery.py': LEGACY_UPLOAD_RECEIPT_SOURCE}})
    write_json(previous / 'recovery_error.json', {'type': 'APIConnectionError', 'http_status': None})
    return source, previous, tmp_path


def test_interrupted_upload_uses_source_proof_and_preserves_original_intent(interrupted_recovery):
    source, previous, root = interrupted_recovery
    before = (source / 'upload_recovery_intent.json').read_bytes()
    proof = validate_interrupted_upload_recovery(source, previous, root)
    assert proof['legacy_source_proof'] and proof['proven_stage'] == 'file_upload'
    assert (source / 'upload_recovery_intent.json').read_bytes() == before
    write_json(previous / 'recovery_error.json', {
        'type': 'APIConnectionError', 'http_status': None, 'stage': 'file_upload'})
    assert not validate_interrupted_upload_recovery(source, previous, root)['legacy_source_proof']


@pytest.mark.parametrize('change', ['accepted_upload', 'retry_intent', 'create_error', 'unknown_source', 'changed_payload'])
def test_interrupted_upload_refuses_ambiguous_or_repeated_dispatch(interrupted_recovery, change):
    source, previous, root = interrupted_recovery
    if change in ('accepted_upload', 'retry_intent'):
        write_json(previous / ('upload.json' if change == 'accepted_upload' else 'upload_retry_intent.json'), {})
    elif change == 'create_error':
        write_json(previous / 'recovery_error.json', {
            'type': 'APIConnectionError', 'http_status': None, 'stage': 'batch_create'})
    elif change == 'unknown_source':
        state = json.loads((previous / 'manifest.json').read_text())
        state['source_sha256']['src/batch_recovery.py'] = 'unreviewed'
        write_json(previous / 'manifest.json', state)
    else:
        (source / 'batch_input.jsonl').write_text('changed payload')
    with pytest.raises(ValueError):
        validate_interrupted_upload_recovery(source, previous, root)


def test_repeated_transport_failure_requires_an_explicit_unchanged_intent_chain(interrupted_recovery):
    source, previous, root = interrupted_recovery
    following = root / 'following'
    following.mkdir()
    write_json(previous / 'upload_retry_intent.json', {
        'recovery_run': 'following', 'input_sha256': digest(source / 'batch_input.jsonl')})
    write_json(following / 'config.yaml', {'stage': 'batch_upload_recovery', 'recovery': {
        'submission_run': 'source', 'resume_upload_recovery_run': 'previous'}})
    write_json(following / 'manifest.json', {'status': 'failed', 'config_sha256': digest(following / 'config.yaml')})
    write_json(following / 'recovery_error.json', {
        'type': 'APIConnectionError', 'http_status': None, 'stage': 'file_upload'})
    assert validate_interrupted_upload_recovery(source, following, root)['previous_recovery'] == 'following'
    write_json(previous / 'upload_retry_intent.json', {'recovery_run': 'unrelated', 'input_sha256': 'wrong'})
    with pytest.raises(ValueError, match='intent or input changed'):
        validate_interrupted_upload_recovery(source, following, root)
