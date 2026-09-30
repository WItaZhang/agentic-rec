"""Reconcile a failed upload without repeating generation or changing reservations."""

import hashlib
import json
import os

from .batch_experiment import client_for
from .frozen_protocol import verify_final_config
from .paid_budget import PaidBudget
from .utils import digest, managed_run, verified_run_config, write_json


def validate_recovery_inputs(source, config, original, entries):
    error = json.loads((source / "submission_error.json").read_text())
    if error["stage"] != "file_upload" or (source / "submission.json").exists():
        raise ValueError("Recovery only supports an unsubmitted file-upload failure")
    reservations = json.loads((source / "reservations.json").read_text())
    rows = [json.loads(line) for line in (source / "batch_input.jsonl").read_text().splitlines()]
    if len(rows) != len(reservations) or {r["custom_id"] for r in rows} != set(reservations):
        raise ValueError("Recovery input IDs differ from the existing reservations")
    for row in rows:
        reservation = reservations[row["custom_id"]]
        entry = entries[reservation["call_id"]]
        if (entry["event"] != "reserve" or entry["run_id"] != source.name
                or entry["reserved_usd"] != reservation["reserved_usd"]):
            raise ValueError("Recovery requires the intact original pending reservations")
        body = row["body"]
        common = {k: body[k] for k in ("model", "input", "text")}
        if hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest() != reservation["prompt_sha256"]:
            raise ValueError("Recovery payload changed")
        if (row["method"] != "POST" or row["url"] != "/v1/responses" or body["store"] is not False
                or any(body[k] != original["llm"][k] for k in ("model", "temperature", "max_output_tokens"))):
            raise ValueError("Recovery inference settings changed")
    if sum(r["reserved_usd"] for r in reservations.values()) > config["budget"]["per_run_paid_usd"]:
        raise ValueError("Recovery exceeds the original round budget")
    return rows


def run_upload_recovery(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["recovery"]["submission_run"]
        submitted = verified_run_config(source)
        original = verified_run_config(root / submitted["batch"]["source_run"])
        if original["evaluation"]["partition"] == "test":
            verify_final_config(original, root)
        limits = submitted["budget"]
        ledger = PaidBudget(root / limits["ledger_path"], source.name, limits["total_paid_usd"],
                            limits["per_run_paid_usd"], limits["stop_at_usd"])
        rows = validate_recovery_inputs(source, submitted, original, ledger.entries())
        if ledger.snapshot()["campaign_accounted_usd"] > limits["stop_at_usd"]:
            raise ValueError("Campaign already exceeds its planning stop")
        client = client_for(original["llm"], root)
        matches = [batch for batch in client.batches.list(limit=100)
                   if (batch.metadata or {}).get("research_run") == source.name]
        write_json(run_dir / "provider_reconciliation.json", {"matches": [b.model_dump() for b in matches]})
        if len(matches) > 1:
            raise ValueError("Multiple matching batches; do not dispatch another")
        if matches:
            batch = matches[0]
        else:
            # Exclusive durable intent prevents repeated upload/create after an
            # interrupted recovery. A later matching Batch may still be adopted.
            intent = source / "upload_recovery_intent.json"
            with intent.open("x", encoding="utf-8") as stream:
                json.dump({"recovery_run": str(run_dir.relative_to(root)),
                           "input_sha256": digest(source / "batch_input.jsonl")}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            try:
                with (source / "batch_input.jsonl").open("rb") as stream:
                    uploaded = client.files.create(file=stream, purpose="batch")
                write_json(run_dir / "upload.json", {"file_id": uploaded.id})
                batch = client.batches.create(input_file_id=uploaded.id, endpoint="/v1/responses", completion_window="24h",
                    metadata={"research_run": source.name}, extra_headers={"Idempotency-Key": source.name})
            except Exception as error:
                write_json(run_dir / "recovery_error.json", {"type": type(error).__name__,
                    "http_status": getattr(error, "status_code", None)})
                raise RuntimeError("Recovery interrupted; reservations and intent retained for reconciliation") from None
        write_json(run_dir / "submission.json", batch.model_dump())
        # Add a receipt; preserve the original failed manifest/config/error.
        with (source / "submission.json").open("x", encoding="utf-8") as stream:
            json.dump(batch.model_dump(), stream, indent=2)
        manifest.update(test_scored=False, submission_run=config["recovery"]["submission_run"],
            batch_id=batch.id, reused_reservations=len(rows), new_reservations=0,
            submission_sha256=digest(source / "submission.json"), stage_status="submission_reconciled")
        print(f"Reconciled {len(rows)} existing reservations; Batch {batch.id}; no generation retry", flush=True)


def reconcile_scheduler_state(state, index, submission_run, submission):
    # Pure transition: every other pending, accepted and collected shard is kept.
    state = json.loads(json.dumps(state))
    if state["chunks"][index]["state"] != "submitting":
        raise ValueError("Only the ambiguous submitting shard can be reconciled")
    if (submission.get("metadata") or {}).get("research_run") != submission_run.replace("\\", "/").split("/")[-1]:
        raise ValueError("Provider receipt belongs to a different shard")
    state["chunks"][index].update(state="submitted", submit_run=submission_run, batch_id=submission["id"])
    return state


def run_scheduler_checkpoint(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config["recovery"]
        parent = root / settings["scheduler_run"]
        previous = verified_run_config(parent)
        if any(config[key] != previous[key] for key in ("scheduler", "budget")):
            raise ValueError("Checkpoint changed scheduler or budget settings")
        source = root / settings["submission_run"]
        submitted = verified_run_config(source)
        state = json.loads((parent / "scheduler_state.json").read_text())
        chunk = state["chunks"][settings["shard_index"]]
        if (submitted["batch"]["source_run"] != previous["scheduler"]["prepared_run"]
                or submitted["batch"]["request_offset"] != chunk["offset"]
                or submitted["batch"]["request_count"] != chunk["count"]):
            raise ValueError("Reconciled submission differs from scheduler intent")
        receipt = json.loads((source / "submission.json").read_text())
        state = reconcile_scheduler_state(state, settings["shard_index"], settings["submission_run"], receipt)
        write_json(run_dir / "scheduler_state.json", state)
        write_json(run_dir / "recovery_evidence.json", {"scheduler_state_sha256": digest(parent / "scheduler_state.json"),
            "submission_sha256": digest(source / "submission.json"), "original_failure_preserved": True})
        manifest.update(test_scored=False, stage_status="recovery_checkpoint", paid_api_usd=0)
        print(f"Recovery checkpoint: {run_dir.relative_to(root)}", flush=True)
