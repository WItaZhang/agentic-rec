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


def test_ambiguous_submit_cannot_be_reissued_on_resume(tmp_path, monkeypatch):
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
    (previous / "scheduler_state.json").write_text(json.dumps({"input_sha256": fingerprint,
                                                              "chunks": [{"state": "submitting"}]}))
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config))
    monkeypatch.setattr("src.batch_scheduler.client_for", lambda *_: pytest.fail("Must not make an API request"))
    with pytest.raises(ValueError, match="ambiguous"):
        run_batch_schedule(config, config_path, tmp_path)
