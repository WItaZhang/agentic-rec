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
from .llm_experiment import choose_views, load_frozen_knn, validate_llm_config
from .metrics import aggregate_requests, single_target_metrics
from .protocol import CandidateSnapshot, replay_requests, validate_ranking
from .replay import make_candidates
from .utils import digest, managed_run, write_json


def run_matrix_prepare(config, config_path, root):
    import tiktoken

    validate_llm_config(config)  # This stage cannot prepare final test inputs.
    with managed_run(config, config_path, root) as (run_dir, manifest):
        for path, checksum in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / config["data"][path]) != config["data"][checksum]:
                raise ValueError("Input checksum changed")
        events, _ = load_amazon_reviews(root / config["data"]["raw_path"])
        views, audit, _ = choose_views(events, config)
        write_json(run_dir / "sampling.json", audit)
        metadata = load_amazon_metadata(root / config["data"]["metadata_path"], ["title", "categories"])
        model = load_frozen_knn(root, config["retriever"])
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
        write_json(run_dir / "resources.json", {"generation_calls": 0, "count_endpoint_calls": len(counts),
            "exact_payload_count_reuse": len(planned) - len(counts), "prepared_input_tokens": sum(r["preflight_input_tokens"] for r in planned),
            "paid_generation_usd": 0, "retrieval_ms": float(np.sum(list(retrieval.values())))})
        manifest.update(stage_status="prepared_not_executed", test_scored=False,
                        planned_calls_sha256=digest(run_dir / "planned_calls.jsonl"),
                        candidates_sha256=digest(run_dir / "candidates.json"))
        print(f"Prepared {len(planned)} generation inputs using {len(counts)} count requests; no generations", flush=True)


def run_matrix_evaluate(config, config_path, root):
    import yaml

    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["prepared_run"]
        original = yaml.safe_load((source / "config.yaml").read_text())
        validate_llm_config(original)
        planned = [json.loads(line) for line in (source / "planned_calls.jsonl").read_text().splitlines()]
        plan_table = {f"{r['request_id']}_{r['plan']}": r for r in planned}
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
        if set(results) != set(plan_table):
            raise ValueError("Incomplete matrix: keep waiting; never drop missing requests")
        views = {row["request_id"]: row for row in json.loads((source / "request_views.json").read_text())}
        snapshots = {q: CandidateSnapshot(item_ids=tuple(row.pop("item_ids")), scores=tuple(row.pop("scores")), **row)
                     for q, row in json.loads((source / "candidates.json").read_text()).items()}
        model = load_frozen_knn(root, original["retriever"])
        predictions, calls = [], []
        for custom_id, result in results.items():
            plan = plan_table[custom_id]
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
            calls.append({**plan, **result, "generation_attempts": 1, "count_endpoint_calls": 0,
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
        write_json(run_dir / "outcomes.json", outcomes)
        (run_dir / "calls.jsonl").write_text("".join(json.dumps(r) + "\n" for r in calls), encoding="utf-8")
        write_json(run_dir / "metrics.json", {plan: aggregate_requests([r for r in outcomes if r["plan"] == plan])
                                              for plan in ["R0", *original["evidence"]["plans"]]})
        manifest.update(test_scored=False, prepared_run=config["prepared_run"],
                        source_plan_sha256=digest(source / "planned_calls.jsonl"), stage_status="evaluated")
