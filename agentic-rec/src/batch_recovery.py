"""Reconcile a failed upload without repeating generation or changing reservations."""

import hashlib
import json
import os

from .batch_experiment import client_for
from .frozen_protocol import verify_final_config
from .paid_budget import PaidBudget
from .utils import digest, managed_run, verified_run_config, write_json

# Reviewed pre-stage-logging implementation: the upload receipt is written before
# batch creation. With this exact source and no receipt, APIConnectionError can
# only have come from file upload. Other legacy sources remain fail-closed.
LEGACY_UPLOAD_RECEIPT_SOURCE = "afc86395c9aceaca2137444b50dc7e30992ad2a25379d3d260f556199cf69bfa"


class UploadRecoveryInterrupted(RuntimeError):
    def __init__(self, run_dir):
        super().__init__("Recovery interrupted; reservations and intent retained for reconciliation")
        self.run_dir = run_dir


def validate_interrupted_upload_recovery(source, previous, root):
    prior_config = verified_run_config(previous)
    state = json.loads((previous / "manifest.json").read_text())
    error = json.loads((previous / "recovery_error.json").read_text())
    if (state["status"] != "failed" or prior_config["stage"] != "batch_upload_recovery"
            or root / prior_config["recovery"]["submission_run"].replace("\\", "/") != source):
        raise ValueError("Interrupted recovery belongs to a different or nonfailed submission")
    if any((previous / name).exists() for name in ("upload.json", "submission.json", "upload_retry_intent.json")):
        raise ValueError("Upload receipt or previous retry intent exists; reconcile rather than reupload")
    proven_stage = error.get("stage") == "file_upload" or (
        error.get("stage") is None and state["source_sha256"].get("src/batch_recovery.py") == LEGACY_UPLOAD_RECEIPT_SOURCE)
    if error.get("type") != "APIConnectionError" or error.get("http_status") is not None or not proven_stage:
        raise ValueError("Only a proven pre-create upload connection failure can continue")
    first = json.loads((source / "upload_recovery_intent.json").read_text())
    linked = first
    if root / first["recovery_run"].replace("\\", "/") != previous:
        predecessor = prior_config["recovery"].get("resume_upload_recovery_run")
        if predecessor is None:
            raise ValueError("Interrupted recovery is not linked to the original intent")
        linked = json.loads((root / predecessor.replace("\\", "/") / "upload_retry_intent.json").read_text())
    fingerprint = digest(source / "batch_input.jsonl")
    if (root / linked["recovery_run"].replace("\\", "/") != previous
            or any(record["input_sha256"] != fingerprint for record in (first, linked))):
        raise ValueError("Interrupted recovery intent or input changed")
    return {"previous_recovery": previous.relative_to(root).as_posix(),
            "previous_manifest_sha256": digest(previous / "manifest.json"),
            "previous_error_sha256": digest(previous / "recovery_error.json"),
            "input_sha256": fingerprint, "proven_stage": "file_upload",
            "legacy_source_proof": error.get("stage") is None}


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
            previous = config["recovery"].get("resume_upload_recovery_run")
            if previous is not None:
                prior_run = root / previous.replace("\\", "/")
                proof = validate_interrupted_upload_recovery(source, prior_run, root)
                write_json(run_dir / "recovery_resume_proof.json", proof)
                intent = prior_run / "upload_retry_intent.json"
            with intent.open("x", encoding="utf-8") as stream:
                json.dump({"recovery_run": str(run_dir.relative_to(root)),
                           "input_sha256": digest(source / "batch_input.jsonl")}, stream)
                stream.flush()
                os.fsync(stream.fileno())
            recovery_stage = "file_upload"
            try:
                with (source / "batch_input.jsonl").open("rb") as stream:
                    uploaded = client.files.create(file=stream, purpose="batch")
                write_json(run_dir / "upload.json", {"file_id": uploaded.id})
                recovery_stage = "batch_create"
                batch = client.batches.create(input_file_id=uploaded.id, endpoint="/v1/responses", completion_window="24h",
                    metadata={"research_run": source.name}, extra_headers={"Idempotency-Key": source.name})
            except Exception as error:
                write_json(run_dir / "recovery_error.json", {"type": type(error).__name__,
                    "http_status": getattr(error, "status_code", None), "stage": recovery_stage})
                raise UploadRecoveryInterrupted(run_dir) from None
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


def run_queue_recovery(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config['recovery']
        parent = root / settings['scheduler_run']
        previous = verified_run_config(parent)
        expected = {**previous['scheduler'], 'max_inflight_input_tokens': config['scheduler']['max_inflight_input_tokens']}
        if (config['scheduler'] != expected or config['budget'] != previous['budget']
                or not previous['scheduler']['max_batch_input_tokens'] <= expected['max_inflight_input_tokens']
                < previous['scheduler']['max_inflight_input_tokens']):
            raise ValueError('Queue recovery may only reduce the inflight limit; inputs/prices/budget remain frozen')
        state = json.loads((parent/'scheduler_state.json').read_text())
        index = settings['shard_index']
        chunk = state['chunks'][index]
        if chunk['state'] != 'collected' or chunk.get('provider_status') != 'failed':
            raise ValueError('Queue rejection must be collected before reconciliation')
        collected = root/chunk['collection_run']
        if verified_run_config(collected)['batch_run'] != chunk['submit_run']:
            raise ValueError('Queue receipt belongs to a different submitted shard')
        receipt = json.loads((collected/'batch_status.json').read_text())
        submitted = root/chunk['submit_run']
        original = verified_run_config(submitted)
        if (receipt.get('id') != chunk['batch_id']
                or original['batch']['source_run'] != previous['scheduler']['prepared_run']
                or original['batch']['request_offset'] != chunk['offset']
                or original['batch']['request_count'] != chunk['count']):
            raise ValueError('Queue rejection does not match the immutable shard intent')
        reservations = json.loads((submitted/'reservations.json').read_text())
        rows = json.loads((collected/'results.json').read_text())
        if (len(rows) != len(reservations) or len(rows) != chunk['count']
                or {r['call_id'] for r in rows} != {r['call_id'] for r in reservations.values()}
                or any(r.get('usage') is not None or r['status'] != 'missing_batch_result' for r in rows)):
            raise ValueError('Queue receipt and original reservations differ')
        limits = original['budget']
        ledger = PaidBudget(root/limits['ledger_path'], submitted.name, limits['total_paid_usd'],
                            limits['per_run_paid_usd'], limits['stop_at_usd'])
        rejected = [{**r, 'actual_known_usd': 0.0, 'usage': None, 'generation_attempts': 0,
                     'status': 'submission_rejected_before_generation', 'provider_code': 'token_limit_exceeded',
                     'rejection_stage': 'batch_validation'} for r in rows]
        # Durably preserve valid proof and zero-generation records before releasing
        # reservations. Repeating the same proof after an interruption is idempotent.
        from .batch_scheduler import persist_state

        ledger.validate_queue_rejection(receipt)
        persist_state(run_dir/'provider_receipt.json', receipt)
        persist_state(run_dir/'results.json', rejected)
        ledger.reconcile_queue_rejection([r['call_id'] for r in rows], receipt)
        history = chunk.get('rejected_attempts', []) + [{key: chunk[key] for key in ('submit_run', 'collection_run', 'batch_id')}]
        state['chunks'][index] = {key: chunk[key] for key in ('offset', 'count', 'input_tokens')}
        state['chunks'][index].update(state='pending', rejected_attempts=history)
        persist_state(run_dir/'scheduler_state.json', state)
        write_json(run_dir/'recovery_evidence.json', {'provider_code': 'token_limit_exceeded',
            'source_receipt_sha256': digest(collected/'batch_status.json'), 'requests_requeued': len(rows),
            'observed_batch_input_tokens': receipt['usage']['input_tokens'],
            'observed_batch_output_tokens': receipt['usage']['output_tokens'],
            'note': 'Provider batch usage is zero; no per-request zero-token usage is fabricated'})
        manifest.update(test_scored=False, paid_api_usd=0, stage_status='queue_recovery_checkpoint')
        print(f'Queue checkpoint: {run_dir.relative_to(root)}; {len(rows)} unexecuted requests requeued', flush=True)
