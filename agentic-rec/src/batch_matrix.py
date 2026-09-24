"""Prepare target-free batch inputs and evaluate only a complete collected matrix."""

import hashlib
import json
import random
import time
from dataclasses import asdict

import numpy as np

from .batch_experiment import client_for
from .data import load_amazon_metadata, load_amazon_reviews
from .evidence import build_prompt
from .execution import RatePacer
from .feature import routing_features
from .frozen_protocol import verify_final_config
from .llm_experiment import choose_views, validate_llm_config
from .metrics import aggregate_requests, single_target_metrics
from .model_artifacts import load_frozen_retriever
from .policy_inference import decide_frozen_policies
from .protocol import CandidateSnapshot, replay_requests, validate_ranking
from .replay import make_candidates
from .utils import digest, managed_run, write_json


def canonicalize_plans(planned, share_within_request):
    """Common random draw only for identical inputs at the same prediction request."""
    canonical, logical, physical = {}, [], []
    for row in planned:
        identity = f"{row['request_id']}_{row['plan']}"
        key = (row["request_id"], row["evidence"]["candidate_hash"], row["prompt_sha256"])
        shared_id = canonical.setdefault(key, identity) if share_within_request else identity
        item = {**row, "canonical_id": shared_id}
        logical.append(item)
        if shared_id == identity:
            physical.append(item)
    return logical, physical


def run_matrix_prepare(config, config_path, root):
    import tiktoken

    frozen = verify_final_config(config, root) if config["stage"] == "frozen_matrix_prepare" else None
    validate_llm_config(config, verified_final_test=frozen is not None)
    with managed_run(config, config_path, root) as (run_dir, manifest):
        for path, checksum in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / config["data"][path]) != config["data"][checksum]:
                raise ValueError("Input checksum changed")
        events, _ = load_amazon_reviews(root / config["data"]["raw_path"])
        views, audit, _ = choose_views(events, config)
        write_json(run_dir / "sampling.json", audit)
        metadata = load_amazon_metadata(root / config["data"]["metadata_path"], ["title", "categories"])
        model = load_frozen_retriever(root, config["retriever"])
        snapshots, retrieval = {}, {}
        for view in views:
            start = time.perf_counter()
            snapshots[view.request_id] = make_candidates(view, model, config["retriever"]["candidate_count"],
                config["protocol"]["positive_rating"], config["retriever"]["model_hash"])
            retrieval[view.request_id] = (time.perf_counter() - start) * 1000
        write_json(run_dir / "candidates.json", {q: asdict(s) for q, s in snapshots.items()})
        write_json(run_dir / "retrieval_latency_ms.json", retrieval)
        write_json(run_dir / "request_views.json", [{"request_id": v.request_id, "user_id": v.user_id,
            "history_count": len(v.history), "prediction_time": v.prediction_time,
            "history_event_ids": [e.event_id for e in v.history]} for v in views])
        if frozen is not None:
            additional = {}
            for name, model_config in config["evaluation"].get("additional_baselines", {}).items():
                alternative = load_frozen_retriever(root, model_config)
                alternative_snapshots, elapsed = {}, {}
                for view in views:
                    started = time.perf_counter()
                    snapshot = make_candidates(view, alternative, model_config["candidate_count"],
                        config["protocol"]["positive_rating"], model_config["model_hash"])
                    alternative_snapshots[view.request_id] = asdict(snapshot)
                    elapsed[view.request_id] = (time.perf_counter() - started) * 1000
                additional[name] = {"model_config": model_config, "catalog": alternative.catalog,
                                    "candidates": alternative_snapshots, "retrieval_latency_ms": elapsed}
            write_json(run_dir / "additional_baselines.json", additional)
            manifest["additional_baselines_sha256"] = digest(run_dir / "additional_baselines.json")
            # Decisions are materialized before any generation or target lookup.
            catalog = set(model.catalog)
            features = [routing_features(v, snapshots[v.request_id], catalog, config["protocol"]["positive_rating"])
                        for v in views]
            decisions = decide_frozen_policies(root, frozen["routing_run"], [v.request_id for v in views], features,
                frozen["selection_artifact_hashes"], frozen["routing_cpu_threads"])
            write_json(run_dir / "routing_decisions.json", decisions)
            manifest.update(final_test_freeze=config["final_test_freeze"],
                            routing_decisions_sha256=digest(run_dir / "routing_decisions.json"))
        tokenizer = tiktoken.get_encoding(config["evidence"]["tokenizer"])

        def truncate(text, limit):
            tokens = tokenizer.encode(text, disallowed_special=())
            return tokenizer.decode(tokens[:limit]), len(tokens) > limit

        client = client_for(config["llm"], root)
        pacer = RatePacer(tokens_per_minute=config["preparation"]["count_token_pacing"],
                          requests_per_minute=config["preparation"]["count_requests_per_minute"])
        instructions = (root / config["evidence"]["prompt_path"]).read_text(encoding="utf-8")
        jobs = [(view, plan) for view in views for plan in config["evidence"]["plans"]]
        random.Random(config["seed"]).shuffle(jobs)
        counts, planned = {}, []
        with (run_dir / "planned_calls.jsonl").open("w", encoding="utf-8") as stream:
            for view, plan in jobs:
                messages, schema, _, evidence = build_prompt(view, snapshots[view.request_id], metadata, plan,
                    config["evidence"], truncate, instructions)
                common = {"model": config["llm"]["model"], "input": messages,
                    "text": {"format": {"type": "json_schema", "name": "ranking", "strict": True, "schema": schema}}}
                fingerprint = hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest()
                if fingerprint not in counts:
                    pacer.wait(0, 0)
                    try:
                        counts[fingerprint] = client.responses.input_tokens.count(**common).input_tokens
                    except Exception as error:
                        raise RuntimeError(f"Token preflight failed: {type(error).__name__}; no generation submitted") from None
                if counts[fingerprint] > config["llm"]["max_input_tokens"]:
                    raise ValueError("Prepared input exceeds cap; adjust evidence on development before any generation")
                row = {"request_id": view.request_id, "plan": plan, "prompt_sha256": fingerprint,
                       "preflight_input_tokens": counts[fingerprint], "evidence": evidence,
                       "record_type": "planned_not_executed", "call_id": None}
                planned.append(row)
                stream.write(json.dumps(row) + "\n")
                stream.flush()
        planned, physical = canonicalize_plans(planned, config["preparation"].get("share_identical_inputs_within_request", False))
        for name, records in (("planned_calls.jsonl", planned), ("physical_calls.jsonl", physical)):
            (run_dir / name).write_text("".join(json.dumps(r) + "\n" for r in records), encoding="utf-8")
        write_json(run_dir / "resources.json", {"generation_calls": 0, "count_endpoint_calls": len(counts),
            "planned_physical_calls": len(physical), "logical_action_outcomes": len(planned),
            "exact_payload_count_reuse": len(planned) - len(counts), "prepared_input_tokens": sum(r["preflight_input_tokens"] for r in planned),
            "paid_generation_usd": 0, "retrieval_ms": float(np.sum(list(retrieval.values())))})
        manifest.update(stage_status="prepared_not_executed", test_scored=False,
                        planned_calls_sha256=digest(run_dir / "planned_calls.jsonl"),
                        physical_calls_sha256=digest(run_dir / "physical_calls.jsonl"),
                        candidates_sha256=digest(run_dir / "candidates.json"))
        print(f"Prepared {len(planned)} generation inputs using {len(counts)} count requests; no generations", flush=True)


def run_matrix_evaluate(config, config_path, root):
    import yaml

    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["prepared_run"]
        prepared_manifest = json.loads((source / "manifest.json").read_text())
        for name, key in (("planned_calls.jsonl", "planned_calls_sha256"), ("candidates.json", "candidates_sha256")):
            if prepared_manifest["status"] != "completed" or digest(source / name) != prepared_manifest[key]:
                raise ValueError("Prepared matrix artifacts changed or preparation was incomplete")
        original = yaml.safe_load((source / "config.yaml").read_text())
        frozen = verify_final_config(original, root) if original["stage"] == "frozen_matrix_prepare" else None
        validate_llm_config(original, verified_final_test=frozen is not None)
        if frozen is not None:
            decision_hash = digest(source / "routing_decisions.json")
            if decision_hash != prepared_manifest["routing_decisions_sha256"]:
                raise ValueError("Test routing decisions changed after preparation")
            manifest.update(final_test_freeze=original["final_test_freeze"], routing_decisions_sha256=decision_hash)
        planned = [json.loads(line) for line in (source / "planned_calls.jsonl").read_text().splitlines()]
        plan_table = {f"{r['request_id']}_{r['plan']}": r for r in planned}
        expected_ids = {r.get("canonical_id", identity) for identity, r in plan_table.items()}
        results = {}
        for location in config["collection_runs"]:
            collected = root / location
            state = json.loads((collected / "manifest.json").read_text())
            if state["stage_status"] != "collected":
                raise ValueError("Batch has not been fully collected")
            for row in json.loads((collected / "results.json").read_text()):
                if row["custom_id"] in results or row["custom_id"] not in plan_table:
                    raise ValueError("Duplicate or unexpected collected request")
                if row["prompt_sha256"] != plan_table[row["custom_id"]]["prompt_sha256"]:
                    raise ValueError("Collected request has different model or evidence inputs")
                results[row["custom_id"]] = row
        if set(results) != expected_ids:
            raise ValueError("Incomplete matrix: keep waiting; never drop missing requests")
        views = {row["request_id"]: row for row in json.loads((source / "request_views.json").read_text())}
        snapshots = {q: CandidateSnapshot(item_ids=tuple(row.pop("item_ids")), scores=tuple(row.pop("scores")), **row)
                     for q, row in json.loads((source / "candidates.json").read_text()).items()}
        model = load_frozen_retriever(root, original["retriever"])
        predictions, calls = [], []
        for custom_id, plan in plan_table.items():
            canonical_id = plan.get("canonical_id", custom_id)
            result = results[canonical_id]
            if plan["request_id"] != plan_table[canonical_id]["request_id"] or result["prompt_sha256"] != plan["prompt_sha256"]:
                raise ValueError("A reused output crossed request visibility or changed model inputs")
            request_id = plan["request_id"]
            aliases = {f"C{i:03d}": item for i, item in enumerate(snapshots[request_id].item_ids, 1)}
            ranked = []
            if result["status"] == "completed":
                try:
                    ranked = [aliases.get(alias, "OUTSIDE") for alias in json.loads(result["text"])["item_ids"]]
                except (ValueError, KeyError, TypeError):
                    pass
            ranking, errors = validate_ranking(ranked, snapshots[request_id], original["evidence"]["k"])
            predictions.append({"request_id": request_id, "user_id": views[request_id]["user_id"],
                "plan": plan["plan"], "ranking": ranking, "repair_errors": errors,
                "status": result["status"], "candidate_hash": snapshots[request_id].content_hash,
                "service_latency_ms": None, "latency_mode": "offline_batch"})
            calls.append({**plan, **result, "generation_attempts": int(canonical_id == custom_id),
                          "counterfactual_generation_attempts": 1, "reused_generation": canonical_id != custom_id,
                          "canonical_id": canonical_id, "logical_id": custom_id, "count_endpoint_calls": 0,
                          "total_latency_ms": None, "rate_queue_ms": None, "generation_latency_ms": None})
        for q, view in views.items():
            predictions.append({"request_id": q, "user_id": view["user_id"], "plan": "R0",
                                "ranking": snapshots[q].item_ids[:original["evidence"]["k"]],
                                "candidate_hash": snapshots[q].content_hash, "service_latency_ms": None})
        # No targets read until every prediction is finalized.
        if digest(root / original["data"]["raw_path"]) != original["data"]["sha256"]:
            raise ValueError("Raw data changed since preparation")
        events, _ = load_amazon_reviews(root / original["data"]["raw_path"])
        _, _, ends = choose_views(events, original)
        targets = {target.request_id: target.item_id for _, target in replay_requests(
            events, ends, original["protocol"]["positive_rating"])}
        outcomes = [{**prediction, "history_count": views[prediction["request_id"]]["history_count"],
            "cold_item": targets[prediction["request_id"]] not in model.catalog,
            **single_target_metrics(prediction["ranking"], targets[prediction["request_id"]],
                                    snapshots[prediction["request_id"]].item_ids, original["evidence"]["k"])}
            for prediction in predictions]
        if frozen is not None:
            if digest(source / "additional_baselines.json") != prepared_manifest["additional_baselines_sha256"]:
                raise ValueError("Additional conventional candidates changed after freezing")
            extra_outcomes = []
            for name, record in json.loads((source / "additional_baselines.json").read_text()).items():
                if set(record["candidates"]) != set(views):
                    raise ValueError("Additional conventional baseline has a different request sample")
                catalog = set(record["catalog"])
                for q, snapshot in record["candidates"].items():
                    ranking = snapshot["item_ids"][:original["evidence"]["k"]]
                    extra_outcomes.append({"request_id": q, "user_id": views[q]["user_id"], "plan": name,
                        "ranking": ranking, "history_count": views[q]["history_count"], "cold_item": targets[q] not in catalog,
                        **single_target_metrics(ranking, targets[q], snapshot["item_ids"], original["evidence"]["k"]),
                        "retrieval_ms": record["retrieval_latency_ms"][q], "actual_api_usd": 0})
            write_json(run_dir / "additional_baseline_outcomes.json", extra_outcomes)
            manifest["additional_baselines_sha256"] = prepared_manifest["additional_baselines_sha256"]
        write_json(run_dir / "outcomes.json", outcomes)
        (run_dir / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in calls), encoding="utf-8")
        write_json(run_dir / "metrics.json", {plan: aggregate_requests([r for r in outcomes if r["plan"] == plan])
                                              for plan in ["R0", *original["evidence"]["plans"]]})
        physical = list(results.values())
        write_json(run_dir / "resources.json", {
            "submitted_physical_requests": len(physical), "logical_action_outcomes": len(planned),
            "same_request_exact_input_reuses": len(planned) - len(physical),
            "input_tokens_known": sum((r["usage"] or {}).get("input_tokens", 0) for r in physical),
            "output_tokens_known": sum((r["usage"] or {}).get("output_tokens", 0) for r in physical),
            "cached_tokens_known": sum(((r["usage"] or {}).get("input_tokens_details") or {}).get("cached_tokens", 0) for r in physical),
            "actual_known_usd": sum(r["actual_known_usd"] or 0 for r in physical),
            "accounted_usd": sum(r["actual_known_usd"] if r["actual_known_usd"] is not None else r["reserved_usd"] for r in physical),
            "unknown_usage_requests": sum(r["usage"] is None for r in physical),
            "service_latency_ms": None,
            "cost_scope": "offline label construction; each physical call counted once, including shared outcomes"})
        manifest.update(test_scored=frozen is not None, prepared_run=config["prepared_run"],
                        source_plan_sha256=digest(source / "planned_calls.jsonl"), stage_status="evaluated",
                        physical_generations=len(results), logical_outcomes=len(plan_table))
