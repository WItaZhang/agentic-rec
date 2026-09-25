"""Post-evaluation error attribution and deterministic, text-redacted case selection."""

import hashlib
import json

from .data import load_amazon_metadata, load_amazon_reviews
from .evidence_analysis import validate_table
from .frozen_protocol import verify_final_config
from .protocol import replay_requests
from .utils import digest, managed_run, verified_run_config, write_json


def error_tags(base, outcome, call):
    """Observable error classes; these evaluator labels are never routing features."""
    tags = []
    if outcome.get("cold_item"):
        tags.append("cold_target")
    if not outcome["candidate_recall"]:
        tags.append("retrieval_miss")
    if base["hr"] and not outcome["hr"]:
        tags.append("baseline_hit_lost")
    if not base["hr"] and outcome["hr"]:
        tags.append("baseline_miss_rescued")
    if outcome["ndcg"] < base["ndcg"]:
        tags.append("rank_quality_loss")
    if outcome["history_count"] == 0 and not outcome["hr"]:
        tags.append("no_history_miss")
    if call and call["status"] != "completed":
        tags.append("api_failure")
    if outcome.get("repair_errors"):
        tags.append("ranking_repair")
    return tags


def choose_case_ids(tagged, limit, seed):
    if limit < 1:
        raise ValueError("A positive case limit is required")
    names = sorted({tag for tags in tagged.values() for tag in tags})
    return {tag: sorted((q for q, tags in tagged.items() if tag in tags),
                       key=lambda q: hashlib.sha256(f"{seed}:{tag}:{q}".encode()).hexdigest())[:limit]
            for tag in names}


def development_fixed_decisions(original, status, request_ids, policies):
    if (status["status"] != "completed" or status.get("test_scored")
            or original["evaluation"]["partition"] != "validation"
            or original["sampling"]["mode"] != "uniform_users"):
        raise ValueError("Development failure diagnostics require complete population validation")
    plans = ["R0", *original["evidence"]["plans"]]
    if any(name not in [f"fixed_{p}" for p in plans] for name in policies):
        raise ValueError("Development case analysis supports fixed evidence actions only")
    return {"request_ids": sorted(request_ids), "label_access": False,
            "actions": {name: [name.removeprefix("fixed_")] * len(request_ids) for name in policies}}


def run_failure_analysis(config, config_path, root):
    from .llm_experiment import choose_views

    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config["failure_analysis"]
        matrix = root / settings["matrix_run"]
        status = json.loads((matrix / "manifest.json").read_text())
        is_final = config["stage"] == "final_failure_analysis"
        if config["stage"] not in ("final_failure_analysis", "development_failure_analysis"):
            raise ValueError("Unknown failure-analysis scope")
        if status["status"] != "completed" or bool(status.get("test_scored")) != is_final:
            raise ValueError("Failure-analysis scope must match the complete evaluated partition")
        prepared = root / status["prepared_run"]
        preparation = json.loads((prepared / "manifest.json").read_text())
        if digest(prepared / "candidates.json") != preparation["candidates_sha256"]:
            raise ValueError("Candidates changed after preparation")
        original = verified_run_config(prepared)
        rows = json.loads((matrix / "outcomes.json").read_text())
        calls = [json.loads(line) for line in (matrix / "calls.jsonl").read_text().splitlines()]
        table, attempts = validate_table(rows, calls, ["R0", *original["evidence"]["plans"]])
        if is_final:
            verify_final_config(original, root)
            if digest(prepared / "routing_decisions.json") != status["routing_decisions_sha256"]:
                raise ValueError("Saved decisions changed after evaluation")
            decisions = json.loads((prepared / "routing_decisions.json").read_text())
        else:
            decisions = development_fixed_decisions(original, status, table, settings["policies"])
        write_json(run_dir / "analyzed_decisions.json", decisions)
        if set(decisions["request_ids"]) != set(table):
            raise ValueError("Failure analysis must retain the complete evaluated sample")
        for path, checksum in (("raw_path", "sha256"), ("metadata_path", "metadata_sha256")):
            if digest(root / original["data"][path]) != original["data"][checksum]:
                raise ValueError("Evaluation source changed")
        events, _ = load_amazon_reviews(root / original["data"]["raw_path"])
        views, _, ends = choose_views(events, original)
        views = {v.request_id: v for v in views}
        targets = {target.request_id: target.item_id for _, target in
                   replay_requests(events, ends, original["protocol"]["positive_rating"])}
        metadata = load_amazon_metadata(root / original["data"]["metadata_path"], ["title", "categories"])
        candidates = json.loads((prepared / "candidates.json").read_text())

        def item(identity):
            # No user identifier, current target review, or historical review text is exported.
            return {"item_id": identity, "title": metadata.get(identity, {}).get("title", identity),
                    "categories": metadata.get(identity, {}).get("categories") or []}

        analyses = {}
        for policy in settings["policies"]:
            actions = dict(zip(decisions["request_ids"], decisions["actions"][policy], strict=True))
            tagged = {q: error_tags(table[q]["R0"], table[q][action], attempts.get((q, action)))
                      for q, action in actions.items()}
            selected = choose_case_ids(tagged, settings["cases_per_class"], config["seed"])
            cases = {}
            for q in sorted({q for ids in selected.values() for q in ids}):
                target, outcome = targets[q], table[q][actions[q]]
                call = attempts.get((q, actions[q]))
                pool = candidates[q]["item_ids"]
                cases[q] = {"request_id": q, "tags": tagged[q], "action": actions[q],
                    "history_count": len(views[q].history), "target": item(target),
                    "target_base_candidate_rank": pool.index(target) + 1 if target in pool else None,
                    "target_output_rank": list(outcome["ranking"]).index(target) + 1 if target in outcome["ranking"] else None,
                    "base_ndcg": table[q]["R0"]["ndcg"], "policy_ndcg": outcome["ndcg"],
                    "status": call["status"] if call else "no_model_call",
                    "api_usd": (call["actual_known_usd"] if call["actual_known_usd"] is not None else call["reserved_usd"]) if call else 0,
                    "output": [item(i) for i in outcome["ranking"]],
                    "recent_history": [{**item(e.item), "rating": e.rating,
                        "age_days": (views[q].prediction_time - e.timestamp) // 86400000}
                        for e in views[q].history[-settings["history_items_per_case"]:]]}
            analyses[policy] = {"requests": len(actions),
                "class_counts": {tag: sum(tag in tags for tags in tagged.values()) for tag in selected},
                "api_usd_on_retrieval_misses": sum(
                    (attempts[q, action]["actual_known_usd"] if attempts[q, action]["actual_known_usd"] is not None
                     else attempts[q, action]["reserved_usd"])
                    for q, action in actions.items() if action != "R0" and not table[q][action]["candidate_recall"]),
                "case_ids_by_class": selected, "cases": cases}
        write_json(run_dir / "failure_cases.json", {"policies": analyses,
            "partition": original["evaluation"]["partition"],
            "scope": "Post-evaluation diagnostics; overlapping classes, deterministic illustrative cases, not causal explanations of model reasoning",
            "privacy": "No user identifiers or review text; public product metadata only",
            "llm_calls": 0, "paid_api_usd": 0})
        manifest.update(test_scored=is_final,
                        matrix_outcome_sha256=digest(matrix / "outcomes.json"),
                        stage_status="failure_analysis_complete", paid_api_usd=0, llm_calls=0)
        if is_final:
            manifest["final_test_freeze"] = original["final_test_freeze"]
