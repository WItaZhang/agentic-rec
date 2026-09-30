import json

import pytest
import yaml

pytest.importorskip("filelock")

from src.batch_scheduler import run_batch_schedule, split_batches
from src.utils import digest


def test_shards_preserve_every_request_under_both_limits():
    rows = [{"preflight_input_tokens": value} for value in (400, 700, 200, 300, 100)]
    chunks = split_batches(rows, 2, 1000)
    assert [(c["offset"], c["count"]) for c in chunks] == [(0, 1), (1, 2), (3, 2)]
    assert all(c["input_tokens"] <= 1000 for c in chunks)
    with pytest.raises(ValueError):
        split_batches([{"preflight_input_tokens": 1001}], 2, 1000)


def resume_fixture(tmp_path):
    (tmp_path / "uv.lock").write_text("fixture")
    (tmp_path / "main.py").write_text("")
    source = tmp_path / "logs" / "prepared"
    source.mkdir(parents=True)
    (source / "physical_calls.jsonl").write_text('{"preflight_input_tokens":10}\n')
    fingerprint = digest(source / "physical_calls.jsonl")
    (source / "manifest.json").write_text(json.dumps({"status": "completed", "physical_calls_sha256": fingerprint}))
    (source / "config.yaml").write_text(yaml.safe_dump({"llm": {"model": "m", "input_reservation_margin_tokens": 0,
                                                               "max_output_tokens": 1}}))
    (source / "manifest.json").write_text(json.dumps({"status": "completed", "physical_calls_sha256": fingerprint,
        "config_sha256": digest(source / "config.yaml")}))
    config = {"experiment_name": "resume_test", "seed": 42, "resume_from": "logs/previous",
        "data": {"raw_path": "data/raw/input", "processed_path": "data/processed", "staging_path": "data/staging"},
        "logging": {"path": "logs"},
        "budget": {"ledger_path": "logs/budget/ledger", "total_paid_usd": 50, "per_run_paid_usd": 1, "stop_at_usd": 45},
        "scheduler": {"prepared_run": "logs/prepared", "max_batch_input_tokens": 100,
                      "max_inflight_input_tokens": 200, "max_requests_per_batch": 2, "poll_seconds": 1,
                      "pricing": {"model": "m", "input_per_million_usd": 1, "cached_input_per_million_usd": 0,
                                  "output_per_million_usd": 1}}}
    previous = tmp_path / "logs" / "previous"
    previous.mkdir()
    (previous / "config.yaml").write_text(yaml.safe_dump(config))
    (previous / "manifest.json").write_text(json.dumps({'status': 'failed',
        'config_sha256': digest(previous / 'config.yaml')}))
    (previous / "scheduler_state.json").write_text(json.dumps({"input_sha256": fingerprint,
                                                              "chunks": [{"state": "submitting"}]}))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    return config, config_path, previous


@pytest.mark.parametrize('changed_config', [False, True])
def test_ambiguous_submit_or_changed_predecessor_cannot_be_reissued(tmp_path, monkeypatch, changed_config):
    config, config_path, previous = resume_fixture(tmp_path)
    if changed_config:
        with (previous / 'config.yaml').open('a') as stream:
            stream.write('\n# Changed after execution\n')
    monkeypatch.setattr("src.batch_scheduler.client_for", lambda *_: pytest.fail("Must not make an API request"))
    with pytest.raises(ValueError, match='configuration changed' if changed_config else 'ambiguous'):
        run_batch_schedule(config, config_path, tmp_path)


def test_allowance_amendment_loads_the_original_counter_and_accepted_work(tmp_path, monkeypatch):
    config, config_path, previous = resume_fixture(tmp_path)
    config['scheduler']['upload_recovery_limit'] = 20
    (previous / 'config.yaml').write_text(yaml.safe_dump(config))
    (previous / 'manifest.json').write_text(json.dumps({'status': 'completed',
        'config_sha256': digest(previous / 'config.yaml')}))
    state = json.loads((previous / 'scheduler_state.json').read_text())
    state.update(upload_recovery_attempts=20, poll_calls=123,
                 chunks=[{'state': 'collected', 'collection_run': 'logs/retained', 'batch_id': 'accepted'}])
    (previous / 'scheduler_state.json').write_text(json.dumps(state))
    original_state_hash = digest(previous / 'scheduler_state.json')
    config['scheduler']['upload_recovery_limit'] = 40
    config['resume_upload_recovery_allowance'] = {'previous_limit': 20, 'new_limit': 40, 'reason': 'observed transport errors'}
    config_path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr('src.batch_scheduler.client_for', lambda *_: object())
    result = run_batch_schedule(config, config_path, tmp_path)
    assert json.loads((result / 'scheduler_state.json').read_text()) == state
    amendment = json.loads((result / 'scheduling_amendment.json').read_text())
    assert amendment['cumulative_auto_recoveries_preserved'] == 20
    assert amendment['previous_state_sha256'] == original_state_hash
    assert amendment['budget_changed'] is False
