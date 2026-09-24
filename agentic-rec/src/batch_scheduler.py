"""Bounded batch scheduling with durable submit intents and recoverable provider IDs."""

import json
import os
import time

import yaml

from .batch_experiment import client_for, run_batch_collect, run_batch_submit
from .paid_budget import PaidBudget, usage_cost
from .utils import digest, managed_run, write_json


def split_batches(rows, max_requests, max_input_tokens):
    if min(max_requests, max_input_tokens) <= 0:
        raise ValueError("Positive shard limits required")
    chunks, start, count, tokens = [], 0, 0, 0
    for index, row in enumerate(rows):
        amount = row["preflight_input_tokens"]
        if amount > max_input_tokens:
            raise ValueError("One request exceeds the entire shard limit")
        if count and (count == max_requests or tokens + amount > max_input_tokens):
            chunks.append({"offset": start, "count": count, "input_tokens": tokens})
            start, count, tokens = index, 0, 0
        count, tokens = count + 1, tokens + amount
    if count:
        chunks.append({"offset": start, "count": count, "input_tokens": tokens})
    return chunks


def persist_state(path, state):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(state, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def run_batch_schedule(config, config_path, root):
    settings = config["scheduler"]
    if settings["max_batch_input_tokens"] > settings["max_inflight_input_tokens"] or not 1 <= settings["poll_seconds"] <= 60:
        raise ValueError("Invalid queue or polling limits")
    with managed_run(config, config_path, root) as (run_dir, manifest):
        prepared = root / settings["prepared_run"]
        original = yaml.safe_load((prepared / "config.yaml").read_text())
        rows = [json.loads(line) for line in (prepared / "physical_calls.jsonl").read_text().splitlines()]
        fingerprint = digest(prepared / "physical_calls.jsonl")
        prepared_manifest = json.loads((prepared / "manifest.json").read_text())
        if prepared_manifest["status"] != "completed" or prepared_manifest["physical_calls_sha256"] != fingerprint:
            raise ValueError("Input bundle is incomplete or changed")
        pricing, budget_config = settings["pricing"], config["budget"]
        if pricing["model"] != original["llm"]["model"] or budget_config["total_paid_usd"] > 50:
            raise ValueError("Pricing or authorization mismatch")
        ledger = PaidBudget(root / budget_config["ledger_path"], run_dir.name, budget_config["total_paid_usd"],
                            budget_config["per_run_paid_usd"], budget_config["stop_at_usd"])
        upper = sum(usage_cost({"input_tokens": r["preflight_input_tokens"] + original["llm"]["input_reservation_margin_tokens"],
                               "output_tokens": original["llm"]["max_output_tokens"]}, pricing) for r in rows)
        if upper > budget_config["per_run_paid_usd"]:
            raise ValueError("Entire phase estimate exceeds its configured limit")
        state = {"input_sha256": fingerprint,
                 "chunks": [{**chunk, "state": "pending"} for chunk in split_batches(
                     rows, settings["max_requests_per_batch"], settings["max_batch_input_tokens"])],
                 "poll_calls": 0, "poll_errors": 0}
        if config.get("resume_from"):
            previous = root / config["resume_from"]
            old_config = yaml.safe_load((previous / "config.yaml").read_text())
            if any(config[k] != old_config[k] for k in ("scheduler", "budget")):
                raise ValueError("Resume must preserve phase input, queue settings and budget")
            state = json.loads((previous / "scheduler_state.json").read_text())
            if state["input_sha256"] != fingerprint or any(c["state"] == "submitting" for c in state["chunks"]):
                raise ValueError("Input changed or submission is ambiguous; inspect recorded intent/provider metadata before resuming")
        else:
            if ledger.snapshot()["campaign_accounted_usd"] + upper > budget_config["stop_at_usd"]:
                raise ValueError("Full phase estimate exceeds remaining campaign allowance")
        write_json(run_dir / "preflight_budget.json", {"whole_phase_upper_usd": upper,
            "physical_requests": len(rows), "shards": len(state["chunks"]), "accounting_before": ledger.snapshot()})
        state_path = run_dir / "scheduler_state.json"
        persist_state(state_path, state)
        print(f"Batch phase: {len(rows)} physical inputs, upper USD {upper:.6f}, {len(state['chunks'])} shards", flush=True)
        client = client_for(original["llm"], root)
        while any(chunk["state"] != "collected" for chunk in state["chunks"]):
            inflight = sum(c["input_tokens"] for c in state["chunks"] if c["state"] == "submitted")
            for index, chunk in enumerate(state["chunks"]):
                if chunk["state"] != "pending" or inflight + chunk["input_tokens"] > settings["max_inflight_input_tokens"]:
                    continue
                child = {"experiment_name": f"{config['experiment_name']}_s{index:03d}", "stage": "batch_submit",
                    "seed": config["seed"], "data": config["data"], "logging": config["logging"],
                    "runtime_source_run": str(run_dir.relative_to(root)),
                    "budget": budget_config,
                    "batch": {"source_run": settings["prepared_run"], "source_mode": "prepared_bundle",
                              "request_offset": chunk["offset"], "request_count": chunk["count"],
                              "max_enqueued_input_tokens": settings["max_batch_input_tokens"], "pricing": pricing}}
                child_path = run_dir / f"submit_{index:03d}.yaml"
                child_path.write_text(yaml.safe_dump(child, sort_keys=False), encoding="utf-8")
                chunk.update(state="submitting", intent_config=str(child_path.relative_to(root)))
                persist_state(state_path, state)
                submitted = run_batch_submit(child, child_path, root)
                submission = json.loads((submitted / "submission.json").read_text())
                chunk.update(state="submitted", submit_run=str(submitted.relative_to(root)), batch_id=submission["id"])
                persist_state(state_path, state)
                inflight += chunk["input_tokens"]
            for index, chunk in enumerate(state["chunks"]):
                if chunk["state"] != "submitted":
                    continue
                state["poll_calls"] += 1
                try:
                    batch = client.batches.retrieve(chunk["batch_id"])
                    chunk["poll_errors"] = 0
                except Exception as error:
                    state["poll_errors"] += 1
                    chunk["poll_errors"] = chunk.get("poll_errors", 0) + 1
                    state["last_poll_error"] = type(error).__name__
                    persist_state(state_path, state)
                    if chunk["poll_errors"] >= settings["max_consecutive_poll_errors"]:
                        raise RuntimeError("Polling unavailable; provider IDs and reservations retained for resume") from None
                    continue
                chunk["provider_status"] = batch.status
                chunk["provider_counts"] = batch.request_counts.model_dump()
                persist_state(state_path, state)
                if batch.status not in ("completed", "failed", "expired", "cancelled"):
                    continue
                child = {"experiment_name": f"{config['experiment_name']}_c{index:03d}", "stage": "batch_collect",
                    "runtime_source_run": str(run_dir.relative_to(root)),
                    "seed": config["seed"], "batch_run": chunk["submit_run"], "data": config["data"], "logging": config["logging"]}
                child_path = run_dir / f"collect_{index:03d}.yaml"
                child_path.write_text(yaml.safe_dump(child, sort_keys=False), encoding="utf-8")
                collected = run_batch_collect(child, child_path, root)
                chunk.update(state="collected", collection_run=str(collected.relative_to(root)))
                persist_state(state_path, state)
                if batch.status != "completed":
                    raise RuntimeError("Non-completed batch retained; inspect failures before dispatching remaining shards")
                print(f"Collected shard {index + 1}/{len(state['chunks'])}", flush=True)
            if any(c["state"] != "collected" for c in state["chunks"]):
                time.sleep(settings["poll_seconds"])
        write_json(run_dir / "collection_runs.json", [c["collection_run"] for c in state["chunks"]])
        write_json(run_dir / "resources.json", {"budget": ledger.snapshot(), "status_poll_calls": state["poll_calls"],
            "submitted_physical_requests": len(rows), "shards": len(state["chunks"]),
            "note": "Per-shard token usage and charges are settled in the shared ledger; no generation repeated on resume"})
        manifest.update(test_scored=False, prepared_run=settings["prepared_run"], stage_status="all_shards_collected")
        return run_dir
