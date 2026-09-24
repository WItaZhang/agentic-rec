"""Paired analysis of complete, real counterfactual outcome tables (never partial runs)."""

import json
import math
from collections import defaultdict

import numpy as np

from .metrics import aggregate_requests, paired_bootstrap
from .utils import digest, managed_run, write_json


def validate_table(outcomes, calls, plans):
    rows = defaultdict(dict)
    for outcome in outcomes:
        request = outcome["request_id"]
        if outcome["plan"] in rows[request]:
            raise ValueError("Duplicate outcome")
        rows[request][outcome["plan"]] = outcome
    call_table = {(row["request_id"], row["plan"]): row for row in calls}
    if len(call_table) != len(calls):
        raise ValueError("Duplicate calls in the outcome table")
    for request, methods in rows.items():
        if set(methods) != set(plans):
            raise ValueError("Incomplete method matrix; do not drop failed or missing requests")
        fingerprints = {methods[plan]["candidate_hash"] for plan in plans if plan != "R0"}
        if methods["R0"].get("candidate_hash"):
            fingerprints.add(methods["R0"]["candidate_hash"])
        if len(fingerprints) != 1 or len({r["user_id"] for r in methods.values()}) != 1:
            raise ValueError("Unpaired candidates or users")
        for plan in plans:
            if plan != "R0" and (request, plan) not in call_table:
                raise ValueError("Missing attempt accounting")
    return dict(rows), call_table


def analyze_matrix(outcomes, calls, config):
    plans = config["plans"]
    rows, call_table = validate_table(outcomes, calls, plans)
    user_ids = sorted({r["R0"]["user_id"] for r in rows.values()})

    def average_available(values, percentile=None):
        observed = [v for v in values if v is not None]
        if not observed:
            return None
        return float(np.percentile(observed, percentile) if percentile else np.mean(observed))

    def values(plan, metric, selected=None):
        by_user = defaultdict(list)
        for request, methods in rows.items():
            if selected is None or request in selected:
                by_user[methods[plan]["user_id"]].append(methods[plan][metric])
        return {user: float(np.mean(items)) for user, items in by_user.items()}

    def comparison(left, right, selected=None):
        result = {}
        for metric in ("ndcg", "hr"):
            a, b = values(left, metric, selected), values(right, metric, selected)
            users = sorted(a)
            if not users:
                result[metric] = {"users": 0}
                continue
            result[metric] = paired_bootstrap([a[u] for u in users], [b[u] for u in users],
                config["bootstrap_repetitions"], config["seed"], config["confidence"])
            differences = np.array([a[u] - b[u] for u in users])
            sd = float(differences.std(ddof=1)) if len(users) > 1 else None
            result[metric]["paired_sd"] = sd
            result[metric]["bootstrap_degenerate"] = sd is None or sd == 0
            if selected is not None and len(users) < config.get("minimum_group_users_for_interval", 30):
                result[metric].update(ci_low=None, ci_high=None, interval_status="descriptive_small_group")
            result[metric]["approx_users_for_target_power"] = (
                math.ceil((config["normal_z_alpha"] + config["normal_z_power"]) ** 2 * sd ** 2
                          / config["minimum_detectable_difference"] ** 2) if sd is not None and sd > 0 else None)
        return result

    methods = {}
    for plan in plans:
        selected = [method[plan] for method in rows.values()]
        attempts = [r for r in calls if r["plan"] == plan]
        dollars = [r.get("actual_known_usd") if r.get("actual_known_usd") is not None
                   else r["reserved_usd"] for r in attempts]
        service = [r["service_latency_ms"] for r in selected]
        methods[plan] = {**aggregate_requests(selected), "total_accounted_usd": sum(dollars),
            "mean_accounted_usd": sum(dollars) / len(selected),
            "unknown_usage_attempts": sum(r.get("usage") is None and r["generation_attempts"] > 0 for r in attempts),
            "calls": sum(r["generation_attempts"] for r in attempts),
            "counterfactual_single_action_calls": sum(r.get("counterfactual_generation_attempts", r["generation_attempts"]) for r in attempts),
            "input_tokens_known": sum((r["usage"] or {}).get("input_tokens", 0) for r in attempts),
            "output_tokens_known": sum((r["usage"] or {}).get("output_tokens", 0) for r in attempts),
            "cached_tokens_known": sum(((r["usage"] or {}).get("input_tokens_details") or {}).get("cached_tokens", 0)
                                       for r in attempts),
            "fallback_or_repair_requests": sum(bool(r.get("repair_errors")) for r in selected),
            "mean_service_ms": average_available(service), "p95_service_ms": average_available(service, 95),
            "service_latency_observations": sum(v is not None for v in service),
            "mean_rate_queue_ms": average_available([r.get("rate_queue_ms") for r in attempts]),
            "mean_network_generation_ms": average_available([r.get("generation_latency_ms") for r in attempts])}
        user_quality = values(plan, "ndcg")
        methods[plan]["ndcg_interval"] = paired_bootstrap(list(user_quality.values()),
            [0] * len(user_quality), config["bootstrap_repetitions"], config["seed"], config["confidence"])
    comparisons = {f"{a}_minus_{b}": comparison(a, b) for a, b in config["comparisons"]}
    groups = {}
    for name, lower, upper in config["history_groups"]:
        ids = {q for q, v in rows.items() if lower <= v["R0"]["history_count"] < upper}
        groups[name] = {"requests": len(ids), "users": len({rows[q]["R0"]["user_id"] for q in ids}),
                       "means": {plan: aggregate_requests([rows[q][plan] for q in sorted(ids)]) for plan in plans},
                       "comparisons": {f"{a}_minus_{b}": comparison(a, b, ids) for a, b in config["comparisons"]},
                       "interpretation": "descriptive_exploration"}
    oracle = defaultdict(list)
    for methods_by_request in rows.values():
        oracle[methods_by_request["R0"]["user_id"]].append(max(r["ndcg"] for r in methods_by_request.values()))
    identical = defaultdict(dict)
    for call in calls:
        if call.get("status") == "completed" and call.get("call_id"):
            identical[call["request_id"], call.get("prompt_sha256")][call["call_id"]] = call["plan"]
    noise = []
    for (request, fingerprint), repetitions in identical.items():
        if fingerprint is None or len(repetitions) < 2:
            continue
        repeated = [rows[request][plan] for plan in repetitions.values()]
        quality = [r["ndcg"] for r in repeated]
        noise.append({"distinct_rankings": len({tuple(r["ranking"]) for r in repeated}),
                      "ndcg_range": max(quality) - min(quality),
                      "label_aware_choice_gain": max(quality) - float(np.mean(quality))})
    return {"methods": methods, "comparisons": comparisons, "history_groups": groups,
            "identical_input_noise": {"independent_repetition_groups": len(noise),
                "groups_with_changed_ranking": sum(row["distinct_rankings"] > 1 for row in noise),
                "groups_with_changed_ndcg": sum(row["ndcg_range"] > 0 for row in noise),
                "mean_label_aware_choice_gain": float(np.mean([r["label_aware_choice_gain"] for r in noise])) if noise else None,
                "interpretation": "descriptive noise diagnostic, not exploitable evidence or a serving policy"},
            "users": len(user_ids), "requests": len(rows),
            "oracle_user_macro_ndcg": float(np.mean([np.mean(v) for v in oracle.values()])),
            "oracle_warning": "Label-aware upper bound includes output noise; cannot be deployed or claimed as learnable gain",
            "inference": "Development exploration; nominal intervals, not multiple-comparison-confirmatory claims",
            "sample_size_warning": "Normal approximation for planning, not a guarantee; includes cold/missed/failed requests"}


def draw_cost_quality(result, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7.6, 4.8))
    for index, (plan, row) in enumerate(result["methods"].items()):
        mean, interval = row["user_macro"]["ndcg"], row["ndcg_interval"]
        ax.errorbar(row["mean_accounted_usd"] * 1000, mean,
                    yerr=[[max(0, mean - interval["ci_low"])], [max(0, interval["ci_high"] - mean)]],
                    fmt="o", capsize=3)
        ax.annotate(plan, (row["mean_accounted_usd"] * 1000, row["user_macro"]["ndcg"]),
                    xytext=(6, 8 if index % 2 else -14), textcoords="offset points")
    ax.set(xlabel="Incremental API USD / 1,000 requests (measured usage + unknown reservations)",
           ylabel="User-macro NDCG@10", title="Development evidence comparison — not final test")
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(output / "quality_cost.png", dpi=180)
    fig.savefig(output / "quality_cost.svg")
    plt.close(fig)


def run_analysis(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["analysis"]["source_run"]
        source_manifest = json.loads((source / "manifest.json").read_text())
        if source_manifest["status"] != "completed" or source_manifest.get("test_scored"):
            raise ValueError("Development analysis requires a complete development experiment")
        outcomes = json.loads((source / "outcomes.json").read_text())
        calls = [json.loads(line) for line in (source / "calls.jsonl").read_text().splitlines()]
        result = analyze_matrix(outcomes, calls, config["analysis"])
        write_json(run_dir / "analysis.json", result)
        draw_cost_quality(result, run_dir)
        manifest.update(source_run=config["analysis"]["source_run"],
                        outcome_sha256=digest(source / "outcomes.json"), call_sha256=digest(source / "calls.jsonl"),
                        test_scored=False, paid_api_usd=0)
        print(json.dumps({p: r["user_macro"] for p, r in result["methods"].items()}), flush=True)
