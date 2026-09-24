"""Real synchronous resource audit of frozen policies; never reads evaluation labels."""

import hashlib
import json
import random
import time

import joblib
import numpy as np
import yaml

from .data import load_amazon_metadata, load_amazon_reviews
from .evidence import build_prompt
from .execution import execute_bounded
from .feature import routing_features
from .frozen_protocol import INFERENCE_KEYS, verify_final_config
from .llm_experiment import choose_views
from .model_artifacts import load_frozen_retriever
from .openai_adapter import OpenAIBackend
from .paid_budget import PaidBudget, usage_cost
from .protocol import validate_ranking
from .replay import make_candidates
from .routing_model import UtilityRouter, random_actions, rule_actions
from .utils import digest, managed_run, write_json


def run_serving_audit(config, config_path, root):
    import tiktoken
    from threadpoolctl import threadpool_limits

    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config["audit"]
        if settings["concurrency"] != 1:
            raise ValueError("The prespecified serving audit uses concurrency one")
        frozen = json.loads((root / settings["freeze_path"]).read_text())
        verify_final_config(frozen["test_config"], root)
        source = root / settings["validation_prepared_run"]
        original = yaml.safe_load((source / "config.yaml").read_text(encoding="utf-8"))
        for key in INFERENCE_KEYS:
            if original[key] != frozen["test_config"][key]:
                raise ValueError("Serving audit must use the frozen inference specification")
        if original["evaluation"]["partition"] != "validation":
            raise ValueError("Resource audit samples validation, never final-test labels")
        source_manifest = json.loads((source / "manifest.json").read_text())
        for file, key in (("candidates.json", "candidates_sha256"), ("planned_calls.jsonl", "planned_calls_sha256")):
            if source_manifest["status"] != "completed" or digest(source / file) != source_manifest[key]:
                raise ValueError("Audit input source changed")
        for path, checksum in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / original["data"][path]) != original["data"][checksum]:
                raise ValueError("Audit dataset changed")
        events, _ = load_amazon_reviews(root / original["data"]["raw_path"])
        views, _, _ = choose_views(events, original)
        views = sorted(views, key=lambda v: hashlib.sha256(f"{config['seed']}:{v.request_id}".encode()).hexdigest())[:settings["users"]]
        metadata = load_amazon_metadata(root / original["data"]["metadata_path"], ["title", "categories"])
        recommender = load_frozen_retriever(root, original["retriever"])
        additional_specs = frozen["test_config"]["evaluation"].get("additional_baselines", {})
        additional_models = {name: load_frozen_retriever(root, spec) for name, spec in additional_specs.items()}
        catalog = set(recommender.catalog)
        directory = root / frozen["routing_run"]
        selected = json.loads((directory / "selection_frozen.json").read_text())
        budget_point = str(frozen["analysis"]["primary_budget_usd_per_1000"])
        learned = selected["chosen"][f"learned_{budget_point}"]
        rule = selected["chosen"][f"rule_{budget_point}"]["policy"]["rule"]
        specification = learned["policy"]
        estimator = joblib.load(directory / f"estimator_{specification['estimator_id']}.joblib")
        plans = tuple(selected["plans"])
        router = UtilityRouter(estimator, plans, tuple(selected["feature_names"]),
                               tuple(selected["training_mean_costs"]), specification["cost_weight"])
        control = learned["random_control"]
        tokenizer = tiktoken.get_encoding(original["evidence"]["tokenizer"])

        def truncate(text, maximum):
            tokens = tokenizer.encode(text, disallowed_special=())
            return tokenizer.decode(tokens[:maximum]), len(tokens) > maximum

        instructions = (root / original["evidence"]["prompt_path"]).read_text(encoding="utf-8")
        counterfactual = {(row["request_id"], row["plan"]): row for row in
                          (json.loads(line) for line in (source / "planned_calls.jsonl").read_text().splitlines())}
        saved_candidates = json.loads((source / "candidates.json").read_text())
        methods = settings["methods"]
        ordinary_methods = {"base", "recent", "full", "rule", "random", "learned"}
        if set(additional_specs) & ordinary_methods or set(methods) - ordinary_methods - set(additional_specs):
            raise ValueError("Unsupported serving audit method")

        def route(method, view, snapshot):
            if method in additional_models:
                return "R0"
            if method in ("base", "recent", "full"):
                return {"base": "R0", "recent": "R1", "full": "R4"}[method]
            if method == "random":
                return random_actions([view.request_id], control["probabilities"], plans, control["seed"])[0]
            features = [routing_features(view, snapshot, catalog, original["protocol"]["positive_rating"])]
            return rule_actions(features, rule)[0] if method == "rule" else router.decide(features)[0]

        llm_config = {**original["llm"], "rate_limits": settings["rate_limits"]}
        budget_config = config["budget"]
        budget = PaidBudget(root / budget_config["ledger_path"], run_dir.name, budget_config["total_paid_usd"],
                            budget_config["per_run_paid_usd"], budget_config["stop_at_usd"])
        if budget_config["total_paid_usd"] > 50 or budget_config["cloud_rental_allowed"]:
            raise ValueError("Serving audit exceeds resource authorization")
        backend = OpenAIBackend(llm_config, root, budget)
        jobs, upper = [], 0.0
        with threadpool_limits(limits=settings["cpu_threads"]):
            for view in views:
                snapshot = make_candidates(view, recommender, original["retriever"]["candidate_count"],
                    original["protocol"]["positive_rating"], original["retriever"]["model_hash"])
                if list(snapshot.item_ids) != saved_candidates[view.request_id]["item_ids"]:
                    raise ValueError("Serving candidate order differs from its frozen matrix")
                for method in methods:
                    action = route(method, view, snapshot)
                    jobs.append((view, method, action))
                    if action != "R0":
                        count = counterfactual[view.request_id, action]["preflight_input_tokens"]
                        upper += usage_cost({"input_tokens": count + llm_config["input_reservation_margin_tokens"],
                                             "output_tokens": llm_config["max_output_tokens"]}, llm_config["pricing"])
        if upper > budget_config["per_run_paid_usd"] or upper + budget.snapshot()["campaign_accounted_usd"] > budget_config["stop_at_usd"]:
            raise ValueError("Complete resource audit exceeds remaining allowance")
        write_json(run_dir / "preflight_budget.json", {"upper_usd": upper, "users": len(views), "requests": len(jobs),
                   "planned_generation_attempts": sum(action != "R0" for _, _, action in jobs), "budget": budget.snapshot()})
        print(f"Synchronous serving audit: {len(jobs)} requests, upper USD {upper:.6f}", flush=True)
        random.Random(config["seed"]).shuffle(jobs)

        def work(job):
            view, method, expected_action = job
            started = time.perf_counter()
            model = additional_models.get(method, recommender)
            model_config = additional_specs.get(method, original["retriever"])
            snapshot = make_candidates(view, model, model_config["candidate_count"],
                original["protocol"]["positive_rating"], model_config["model_hash"])
            retrieved = time.perf_counter()
            action = route(method, view, snapshot)
            decided = time.perf_counter()
            if action != expected_action:
                raise ValueError("Frozen policy action changed within the resource audit")
            record = {"request_id": view.request_id, "method": method, "action": action,
                      "retriever": model_config["name"],
                      "history_count": len(view.history), "retrieval_ms": (retrieved - started) * 1000,
                      "feature_and_policy_ms": (decided - retrieved) * 1000}
            if action == "R0":
                record.update(status="completed", actual_known_usd=0, generation_attempts=0, count_endpoint_calls=0,
                              usage=None, repair_errors=[], evidence_ms=0)
            else:
                messages, schema, aliases, evidence = build_prompt(view, snapshot, metadata, action,
                    original["evidence"], truncate, instructions)
                record["evidence_ms"] = (time.perf_counter() - decided) * 1000
                common = {"model": llm_config["model"], "input": messages,
                          "text": {"format": {"type": "json_schema", "name": "ranking", "strict": True, "schema": schema}}}
                fingerprint = hashlib.sha256(json.dumps(common, sort_keys=True).encode()).hexdigest()
                if fingerprint != counterfactual[view.request_id, action]["prompt_sha256"]:
                    raise ValueError("Serving model inputs differ from the frozen action matrix")
                response = backend.complete(messages, schema, {"request_id": view.request_id, "method": method, "plan": action})
                record.update(response, evidence=evidence)
                ranked = []
                if response["status"] == "completed":
                    try:
                        ranked = [aliases.get(item, "OUTSIDE") for item in json.loads(response["text"])["item_ids"]]
                    except (ValueError, KeyError, TypeError):
                        pass
                ranking, errors = validate_ranking(ranked, snapshot, original["evidence"]["k"])
                record.update(ranking=ranking, repair_errors=errors)
            record["service_ms"] = (time.perf_counter() - started) * 1000
            return record

        records = []
        with threadpool_limits(limits=settings["cpu_threads"]), (run_dir / "calls.jsonl").open("w", encoding="utf-8") as stream:
            for _, record in execute_bounded(jobs, work, settings["concurrency"]):
                records.append(record)
                stream.write(json.dumps(record) + "\n")
                stream.flush()
                if record["status"] != "completed" or (record["generation_attempts"] and record.get("usage") is None):
                    raise RuntimeError("Serving audit stopped on a failed attempt; partial records retained, no quality claim")
        summary = {}
        for method in methods:
            rows = [r for r in records if r["method"] == method]
            if len(rows) != len(views):
                raise ValueError("Incomplete serving comparison")
            cost = [r["actual_known_usd"] if r["actual_known_usd"] is not None else r["reserved_usd"] for r in rows]
            summary[method] = {"requests": len(rows), "mean_service_ms": float(np.mean([r["service_ms"] for r in rows])),
                "p95_service_ms": float(np.percentile([r["service_ms"] for r in rows], 95)),
                "mean_api_usd": float(np.mean(cost)), "generation_attempts": sum(r["generation_attempts"] for r in rows),
                "count_endpoint_calls": sum(r["count_endpoint_calls"] for r in rows),
                "input_tokens": sum((r.get("usage") or {}).get("input_tokens", 0) for r in rows),
                "output_tokens": sum((r.get("usage") or {}).get("output_tokens", 0) for r in rows),
                "cached_tokens": sum(((r.get("usage") or {}).get("input_tokens_details") or {}).get("cached_tokens", 0) for r in rows),
                "repairs": sum(bool(r["repair_errors"]) for r in rows),
                **{f"mean_{key}": float(np.mean([r.get(key, 0) for r in rows]))
                   for key in ("retrieval_ms", "feature_and_policy_ms", "evidence_ms", "rate_queue_ms", "generation_latency_ms")}}
        write_json(run_dir / "resources.json", {"methods": summary, "budget": budget.snapshot(),
            "application_output_cache": "disabled, independent call for each method/request",
            "provider_prefix_cache": "automatic, actual cached tokens recorded",
            "additional_conventional_methods": list(additional_models),
            "quality_scored": False, "latency_scope": "warm resident models; includes retrieval, routing, prompt construction, token preflight, queue, network and validation"})
        manifest.update(test_scored=False, quality_scored=False, stage_status="resource_audit_complete",
                        final_protocol_sha256=digest(root / settings["freeze_path"]))
