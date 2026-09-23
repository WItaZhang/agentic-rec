"""Configured real-API development experiments; label lookup occurs after inference."""

import hashlib
import json
import random
import time
from collections import Counter
from dataclasses import asdict

import numpy as np
from scipy import sparse

from .data import load_amazon_metadata, load_amazon_reviews
from .evidence import build_prompt
from .execution import execute_bounded
from .metrics import aggregate_requests, single_target_metrics
from .model import ItemKNNModel
from .openai_adapter import OpenAIBackend
from .paid_budget import PaidBudget, usage_cost
from .protocol import hash_sample, replay_requests, validate_ranking
from .replay import make_candidates, model_fingerprint
from .utils import digest, managed_run, utc_seconds, write_json


def validate_llm_config(config):
    if config["evaluation"]["partition"] not in ("policy_train", "validation"):
        raise ValueError("Development API stage cannot score or call on test")
    if not 1 <= config["runtime"]["concurrency"] <= 4 or config["runtime"]["cache"] != "disabled":
        raise ValueError("Protocol supports concurrency 1–4 with application caching disabled")
    if config["llm"]["temperature"] != 0 or config["llm"]["model"] != config["llm"]["pricing"]["model"]:
        raise ValueError("Frozen greedy decoding and model-specific prices required")
    if config["budget"]["total_paid_usd"] > 50 or config["budget"]["cloud_rental_allowed"]:
        raise ValueError("Configuration exceeds current authorization")
    if not 0 < config["evidence"]["recent_events"] <= config["evidence"]["max_history_events"]:
        raise ValueError("Invalid history limits")


def load_frozen_knn(root, config):
    directory = root / config["artifact_path"]
    model = json.loads((directory / "model.json").read_text())
    result = ItemKNNModel(tuple(model["catalog"]), sparse.load_npz(directory / "itemknn.npz"),
                          tuple(model["popularity"]))
    if model_fingerprint(result) != config["model_hash"]:
        raise ValueError("Frozen model fingerprint mismatch")
    return result


def choose_views(events, config):
    ends = [(name, utc_seconds(config["data"][key]) * 1000) for name, key in (
        ("base_train", "base_train_end"), ("policy_train", "policy_train_end"),
        ("validation", "validation_end"), ("test", "test_end"))]
    partition = config["evaluation"]["partition"]
    views = [view for view, _ in replay_requests(events, ends, config["protocol"]["positive_rating"])
             if view.partition == partition]
    sampling = config["sampling"]
    if sampling["mode"] == "smoke_history_strata":
        # Label-blind convenience sample for protocol checks only; not population estimates.
        chosen, audit = [], {}
        for name, present in (("zero", False), ("nonzero", True)):
            part, part_audit = hash_sample([v for v in views if bool(v.history) == present],
                                          sampling["users_by_history"][name], config["seed"])
            chosen.extend(part)
            audit[name] = part_audit
        return chosen, audit, ends
    if sampling["mode"] != "uniform_users":
        raise ValueError("Unknown sampling mode")
    chosen, audit = hash_sample(views, sampling["max_users"], config["seed"])
    return chosen, audit, ends


def run_llm(config, config_path, root):
    import tiktoken

    validate_llm_config(config)
    with managed_run(config, config_path, root) as (run_dir, manifest):
        for path_key, hash_key in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / config["data"][path_key]) != config["data"][hash_key]:
                raise ValueError("Dataset checksum mismatch")
        events, audit = load_amazon_reviews(root / config["data"]["raw_path"])
        metadata = load_amazon_metadata(root / config["data"]["metadata_path"], ["title", "categories"])
        views, sampling, ends = choose_views(events, config)
        write_json(run_dir / "sampling.json", sampling)
        model = load_frozen_knn(root, config["retriever"])
        snapshots, retrieval_ms = {}, {}
        for view in views:
            start = time.perf_counter()
            snapshots[view.request_id] = make_candidates(view, model, config["retriever"]["candidate_count"],
                config["protocol"]["positive_rating"], config["retriever"]["model_hash"])
            retrieval_ms[view.request_id] = (time.perf_counter() - start) * 1000
        write_json(run_dir / "retrieval_latency_ms.json", retrieval_ms)
        write_json(run_dir / "candidates.json", {key: {**asdict(value), "content_hash": value.content_hash}
                                                for key, value in snapshots.items()})
        tokenizer = tiktoken.get_encoding(config["evidence"]["tokenizer"])

        def truncate(text, limit):
            tokens = tokenizer.encode(text, disallowed_special=())
            return tokenizer.decode(tokens[:limit]), len(tokens) > limit

        budget_config = config["budget"]
        budget = PaidBudget(root / budget_config["ledger_path"], run_dir.name,
            budget_config["total_paid_usd"], budget_config["per_run_paid_usd"], budget_config["stop_at_usd"])
        backend = OpenAIBackend(config["llm"], root, budget)
        instructions = (root / config["evidence"]["prompt_path"]).read_text(encoding="utf-8")
        jobs = [(v, plan) for v in views for plan in config["evidence"]["plans"]]
        random.Random(config["seed"]).shuffle(jobs)
        predictions, records = [], []
        if config.get("resume_from"):
            import yaml

            previous = root / config["resume_from"]
            old_config = yaml.safe_load((previous / "config.yaml").read_text())
            for key in ("protocol", "data", "retriever", "sampling", "evaluation", "evidence", "llm", "runtime", "seed"):
                if config[key] != old_config[key]:
                    raise ValueError("Resuming must preserve every inference and sampling setting")
            records = [json.loads(line) for line in (previous / "calls.jsonl").read_text().splitlines()]
            predictions = [json.loads(line) for line in (previous / "predictions.jsonl").read_text().splitlines()]
            done = {(p["request_id"], p["plan"]) for p in predictions}
            if len(done) != len(predictions) or done != {(r["request_id"], r["plan"]) for r in records}:
                raise ValueError("Resume call/prediction journals are incomplete or duplicate")
            if any(p["candidate_hash"] != snapshots[p["request_id"]].content_hash for p in predictions):
                raise ValueError("Resume candidates changed")
            jobs = [(v, p) for v, p in jobs if (v.request_id, p) not in done]
            manifest["resume_from"] = config["resume_from"]
            manifest["reused_attempts"] = len(records)
        upper = len(jobs) * usage_cost({"input_tokens": config["llm"]["max_input_tokens"]
                                       + config["llm"]["input_reservation_margin_tokens"],
                                       "output_tokens": config["llm"]["max_output_tokens"]}, config["llm"]["pricing"])
        estimate = {"maximum_generation_calls": len(jobs), "upper_bound_usd": upper,
                    "accounting_before": budget.snapshot(), "price_source": config["llm"]["pricing"]["source"]}
        write_json(run_dir / "preflight_budget.json", estimate)
        print(f"Preflight: {len(views)} requests, {len(jobs)} calls, conservative upper ${upper:.6f}", flush=True)
        if upper > budget_config["per_run_paid_usd"] or upper + budget.snapshot()["campaign_accounted_usd"] > budget_config["stop_at_usd"]:
            raise ValueError("Full round estimate exceeds configured budget; revise round before calling")
        def work(job):
            view, plan = job
            start = time.perf_counter()
            messages, schema, _, evidence = build_prompt(view, snapshots[view.request_id], metadata, plan,
                config["evidence"], truncate, instructions)
            evidence_ms = (time.perf_counter() - start) * 1000
            result = backend.complete(messages, schema, {"request_id": view.request_id, "plan": plan})
            result.update(evidence=evidence, evidence_latency_ms=evidence_ms)
            return result

        with (run_dir / "calls.jsonl").open("w", encoding="utf-8") as calls_file, \
                (run_dir / "predictions.jsonl").open("w", encoding="utf-8") as predictions_file:
            for record in records:
                calls_file.write(json.dumps(record) + "\n")
            for prediction in predictions:
                predictions_file.write(json.dumps(prediction) + "\n")
            for index, ((view, plan), record) in enumerate(execute_bounded(jobs, work, config["runtime"]["concurrency"]), 1):
                snapshot = snapshots[view.request_id]
                aliases = {f"C{i:03d}": item for i, item in enumerate(snapshot.item_ids, 1)}
                records.append(record)
                calls_file.write(json.dumps(record) + "\n")
                calls_file.flush()
                ranked, parse_error = [], None
                if record["status"] == "completed":
                    try:
                        ranked = [aliases.get(alias, "OUTSIDE") for alias in json.loads(record["text"])["item_ids"]]
                    except (ValueError, KeyError, TypeError):
                        parse_error = "malformed_ranking"
                ranking, errors = validate_ranking(ranked, snapshot, config["evidence"]["k"])
                prediction = {"request_id": view.request_id, "user_id": view.user_id, "plan": plan,
                              "ranking": ranking, "repair_errors": errors, "parse_error": parse_error,
                              "status": record["status"], "candidate_hash": snapshot.content_hash,
                              "retrieval_latency_ms": retrieval_ms[view.request_id],
                              "service_latency_ms": (retrieval_ms[view.request_id]
                                  + record["evidence_latency_ms"] + record["total_latency_ms"])}
                predictions.append(prediction)
                predictions_file.write(json.dumps(prediction) + "\n")
                predictions_file.flush()
                write_json(run_dir / "budget_checkpoint.json", budget.snapshot())
                if index % config["runtime"].get("progress_every", 1) == 0 or record["status"] != "completed":
                    print(f"Call {index}/{len(jobs)} {plan}: {record['status']}; accounted ${budget.snapshot()['round_accounted_usd']:.6f}", flush=True)
        if len(records) != len(views) * len(config["evidence"]["plans"]):
            raise RuntimeError("Partial API round: in-flight calls drained; resume from journals without retrying completed attempts")
        # Evaluation is downstream of all inference; never passed into evidence or backend.
        targets = {target.request_id: target.item_id for _, target in replay_requests(
            events, ends, config["protocol"]["positive_rating"])}
        outcomes = []
        for view in views:
            predictions.append({"request_id": view.request_id, "user_id": view.user_id, "plan": "R0",
                                "service_latency_ms": retrieval_ms[view.request_id],
                                "ranking": snapshots[view.request_id].item_ids[:config["evidence"]["k"]]})
        by_id = {v.request_id: v for v in views}
        for prediction in predictions:
            request_id = prediction["request_id"]
            outcomes.append({**prediction, "history_count": len(by_id[request_id].history),
                "cold_item": targets[request_id] not in model.catalog,
                **single_target_metrics(prediction["ranking"], targets[request_id], snapshots[request_id].item_ids,
                                        config["evidence"]["k"])})
        write_json(run_dir / "outcomes.json", outcomes)
        metrics = {plan: aggregate_requests([r for r in outcomes if r["plan"] == plan])
                   for plan in ["R0", *config["evidence"]["plans"]]}
        write_json(run_dir / "metrics.json", metrics)
        resources = {"budget": budget.snapshot(), "calls": len(records),
                     "input_tokens": sum((r["usage"] or {}).get("input_tokens", 0) for r in records),
                     "output_tokens": sum((r["usage"] or {}).get("output_tokens", 0) for r in records),
                     "cached_input_tokens": sum(((r["usage"] or {}).get("input_tokens_details") or {}).get("cached_tokens", 0)
                                                for r in records),
                     "provider_caching": "automatic; actual cached tokens recorded; application cache disabled",
                     "usage_priced_usd": sum(r.get("actual_known_usd") or 0 for r in records),
                     "retrieval_total_cpu_wall_ms": sum(retrieval_ms.values()),
                     "statuses": dict(Counter(r["status"] for r in records)),
                     "count_endpoint_calls": sum(r["count_endpoint_calls"] for r in records),
                     "other_model_calls": {"planning": 0, "summary": 0, "reflection": 0, "embedding": 0},
                     "mean_service_latency_ms": float(np.mean([r["total_latency_ms"] + r["evidence_latency_ms"] for r in records])),
                     "p95_service_latency_ms": float(np.percentile([r["total_latency_ms"] + r["evidence_latency_ms"] for r in records], 95))}
        write_json(run_dir / "resources.json", resources)
        manifest.update(test_scored=False, input_audit=audit, raw_sha256=digest(root / config["data"]["raw_path"]),
                        prompt_sha256=hashlib.sha256(instructions.encode()).hexdigest(),
                        candidates_sha256=digest(run_dir / "candidates.json"), tokenizer=config["evidence"]["tokenizer"])
