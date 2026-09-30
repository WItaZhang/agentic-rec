import json

import pytest

from src.batch_recovery import UploadRecoveryInterrupted
from src.batch_scheduler import may_recover_upload, recover_upload_bounded

CONNECTION = {'stage': 'file_upload', 'type': 'APIConnectionError', 'http_status': None}


def test_only_precreation_connection_errors_receive_bounded_upload_recovery():
    connection = {'stage': 'file_upload', 'type': 'APIConnectionError', 'http_status': None}
    assert may_recover_upload(connection, 0, 2)
    assert not may_recover_upload(connection, 2, 2)
    assert not may_recover_upload(connection, 0, 0)
    assert not may_recover_upload({**connection, 'stage': 'batch_create'}, 0, 2)
    assert not may_recover_upload({**connection, 'type': 'BadRequestError', 'http_status': 400}, 0, 2)


@pytest.fixture
def recovery_schedule(tmp_path, monkeypatch):
    parent, submitted = tmp_path / 'parent', tmp_path / 'original_submission'
    parent.mkdir()
    submitted.mkdir()
    config = {'experiment_name': 'transport', 'seed': 42, 'data': {}, 'logging': {},
              'scheduler': {'upload_recovery_limit': 4, 'upload_recovery_delay_seconds': 0}}
    state = {'upload_recovery_attempts': 1, 'chunks': [{'state': 'submitting'}]}
    monkeypatch.setattr('src.batch_scheduler.time.sleep', lambda _: None)
    return config, parent, tmp_path, state, 0, submitted, CONNECTION


def test_nested_upload_failures_link_prior_intents_and_consume_existing_limit(recovery_schedule, monkeypatch):
    config, parent, root, state, index, submitted, error = recovery_schedule
    calls, proofs = [], []

    def recover(child, path, task_root):
        assert task_root == root and path.exists()
        persisted = json.loads((parent / 'scheduler_state.json').read_text())
        assert persisted['upload_recovery_attempts'] == len(calls) + 2
        calls.append(child)
        if len(calls) <= 2:
            previous = root / f'failed_{len(calls)}'
            previous.mkdir()
            (previous / 'recovery_error.json').write_text(json.dumps(CONNECTION))
            raise UploadRecoveryInterrupted(previous)

    monkeypatch.setattr('src.batch_recovery.run_upload_recovery', recover)
    monkeypatch.setattr('src.batch_recovery.validate_interrupted_upload_recovery',
                        lambda source, previous, task_root: proofs.append((source, previous, task_root)))
    recover_upload_bounded(*recovery_schedule)
    assert state['upload_recovery_attempts'] == 4
    assert state['chunks'] == [{'state': 'submitting'}]
    assert len(calls) == 3 and len(proofs) == 2
    assert all(c['recovery']['submission_run'] == str(submitted.relative_to(root)) for c in calls)
    assert 'resume_upload_recovery_run' not in calls[0]['recovery']
    assert [c['recovery']['resume_upload_recovery_run'] for c in calls[1:]] == ['failed_1', 'failed_2']


def test_exhausted_upload_limit_never_dispatches_an_extra_recovery(recovery_schedule, monkeypatch):
    config, parent, root, state, *_ = recovery_schedule
    config['scheduler']['upload_recovery_limit'] = 2
    dispatched = []

    def recover(*_):
        dispatched.append(True)
        previous = root / 'last_failure'
        previous.mkdir()
        (previous / 'recovery_error.json').write_text(json.dumps(CONNECTION))
        raise UploadRecoveryInterrupted(previous)

    monkeypatch.setattr('src.batch_recovery.run_upload_recovery', recover)
    monkeypatch.setattr('src.batch_recovery.validate_interrupted_upload_recovery', lambda *_: None)
    with pytest.raises(RuntimeError, match='limit reached'):
        recover_upload_bounded(*recovery_schedule)
    assert len(dispatched) == 1 and state['upload_recovery_attempts'] == 2
    with pytest.raises(RuntimeError, match='limit reached'):
        recover_upload_bounded(*recovery_schedule)
    assert len(dispatched) == 1


@pytest.mark.parametrize('failure', ['unproven', 'other'])
def test_ambiguous_or_unexpected_recovery_failure_stops_immediately(recovery_schedule, monkeypatch, failure):
    _, _, root, state, *_ = recovery_schedule
    dispatched = []

    def recover(*_):
        dispatched.append(True)
        if failure == 'other':
            raise RuntimeError('unexpected provider listing failure')
        raise UploadRecoveryInterrupted(root / 'ambiguous')

    def reject(*_):
        raise ValueError('unproven pre-create failure')

    monkeypatch.setattr('src.batch_recovery.run_upload_recovery', recover)
    monkeypatch.setattr('src.batch_recovery.validate_interrupted_upload_recovery', reject)
    with pytest.raises((RuntimeError, ValueError), match='unexpected|unproven'):
        recover_upload_bounded(*recovery_schedule)
    assert len(dispatched) == 1 and state['upload_recovery_attempts'] == 2
