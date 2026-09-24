"""Analyze decisions saved before labels; report counterfactual costs without simulated latency."""

import json

import numpy as np
import yaml

from .evidence_analysis import validate_table
from .frozen_protocol import verify_final_config
from .metrics import paired_bootstrap
from .utils import digest, managed_run, write_json


def evaluate_decisions(outcomes, calls, decisions, plans, analysis):
    table, attempts = validate_table(outcomes, calls, plans)
    ids = decisions["request_ids"]
    if len(ids) != len(set(ids)) or set(ids) != set(table):
        raise ValueError("Decisions must cover the complete frozen request population")
    if len({table[q]["R0"]["user_id"] for q in ids}) != len(ids) or decisions["label_access"] is not False:
        raise ValueError("Current policy inference requires one independent request per user and no labels")
    draws = analysis["bootstrap_repetitions"]
    confidence, seed = analysis["confidence"], analysis["seed"]
    per_policy, methods = {}, {}
    for name, actions in decisions["actions"].items():
        if len(actions) != len(ids) or set(actions) - set(plans):
            raise ValueError("Missing or unsupported actions")
        observations = []
        for request, action in zip(ids, actions, strict=True):
            outcome = table[request][action]
            call = attempts.get((request, action))
            usage = (call.get("usage") or {}) if call else {}
            cost = (call["actual_known_usd"] if call["actual_known_usd"] is not None else call["reserved_usd"]) if call else 0
            observations.append({**{key: outcome[key] for key in ("user_id", "ndcg", "hr", "candidate_recall", "history_count")},
                "request_id": request, "action": action, "accounted_usd": cost,
                "input_tokens_known": usage.get("input_tokens", 0), "output_tokens_known": usage.get("output_tokens", 0),
                "cached_tokens_known": (usage.get("input_tokens_details") or {}).get("cached_tokens", 0),
                "unknown_usage": bool(call and call.get("usage") is None),
                "llm_calls": int(action != "R0"), "repair": bool(outcome.get("repair_errors")),
                "failed": bool(call and call["status"] != "completed"), "cold_item": outcome.get("cold_item", False)})
        per_policy[name] = observations
        ndcg = [row["ndcg"] for row in observations]
        methods[name] = {"users": len(ids), "requests": len(ids),
            "ndcg_interval": paired_bootstrap(ndcg, np.zeros(len(ids)), draws, seed, confidence),
            **{f"mean_{key}": float(np.mean([row[key] for row in observations])) for key in (
                "ndcg", "hr", "candidate_recall", "accounted_usd", "input_tokens_known", "output_tokens_known", "cached_tokens_known",
                "llm_calls", "failed", "repair")},
            "unknown_usage_requests": sum(row["unknown_usage"] for row in observations),
            "action_counts": {plan: actions.count(plan) for plan in plans},
            "mean_service_ms": None, "p95_service_ms": None}

    def compare(left, right, indices):
        if not indices:
            return {"users": 0}
        a, b = per_policy[left], per_policy[right]
        result = {"users": len(indices)}
        for metric in ("ndcg", "hr", "accounted_usd"):
            x = np.array([a[i][metric] for i in indices])
            y = np.array([b[i][metric] for i in indices])
            interval = paired_bootstrap(x, y, draws, seed, confidence)
            interval["bootstrap_degenerate"] = bool(np.all(x - y == (x - y)[0]))
            if len(indices) < analysis["minimum_group_users_for_interval"]:
                interval.update(ci_low=None, ci_high=None, interval_status="descriptive_small_group")
            result[metric] = interval
        # A separate one-sided 95% lower bound is a central 90% interval's lower endpoint.
        epsilon = analysis["noninferiority_tolerance"]
        lower = paired_bootstrap([a[i]["ndcg"] for i in indices], [b[i]["ndcg"] for i in indices],
                                 draws, seed, 2 * confidence - 1)["ci_low"]
        adequate = len(indices) >= analysis["minimum_group_users_for_interval"]
        nondegenerate = not result["ndcg"]["bootstrap_degenerate"]
        result["noninferiority"] = {"epsilon": epsilon, "one_sided_confidence": confidence,
            "lower_bound": lower if adequate else None,
            "supported": bool(adequate and nondegenerate and lower > -epsilon),
            "warning": "Specific to the frozen margin and sampling/model-output realization"}
        return result

    indices = list(range(len(ids)))
    comparisons = {f"{a}_minus_{b}": compare(a, b, indices) for a, b in analysis["comparisons"]}
    groups = {}
    for name, low, high in analysis["group_boundaries"]:
        chosen = [i for i, q in enumerate(ids) if low <= table[q]["R0"]["history_count"] < high]
        groups[name] = {"users": len(chosen), "descriptive": True,
            "means": {method: {f"mean_{metric}": float(np.mean([rows[i][metric] for i in chosen])) if chosen else None
                      for metric in ("ndcg", "hr", "accounted_usd")} for method, rows in per_policy.items()},
            "comparisons": {f"{a}_minus_{b}": compare(a, b, chosen) for a, b in analysis["comparisons"]}}
    return {"methods": methods, "comparisons": comparisons, "history_groups": groups,
        "primary_comparison": analysis["primary_comparison"], "primary_metric": "ndcg",
        "inference": "One prespecified primary comparison; secondary/group intervals are exploratory",
        "cost_scope": "counterfactual single-action spend measured in the batch label matrix; controller/local CPU separate",
        "latency_scope": "batch service latency is unknown; no cached replay latency is substituted"}, per_policy


def plot_policies(result, output):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(9, 5.5))
    styles = {"learned": ("tab:blue", "o"), "rule": ("tab:green", "s"), "random": ("tab:orange", "^")}
    for kind, (color, marker) in styles.items():
        rows = sorted((r for name, r in result["methods"].items() if name.startswith(kind + "_")),
                      key=lambda r: r["mean_accounted_usd"])
        x = [r["mean_accounted_usd"] * 1000 for r in rows]
        y = [r["mean_ndcg"] for r in rows]
        errors = [[max(0, r["mean_ndcg"] - r["ndcg_interval"]["ci_low"]) for r in rows],
                  [max(0, r["ndcg_interval"]["ci_high"] - r["mean_ndcg"]) for r in rows]]
        ax.errorbar(x, y, yerr=errors, color=color, marker=marker, capsize=3, label=kind, alpha=.85)
    for name, row in result["methods"].items():
        if not name.startswith("fixed_R"):
            continue
        x, y = row["mean_accounted_usd"] * 1000, row["mean_ndcg"]
        ax.scatter(x, y, marker="x", color="black")
        ax.annotate(name.removeprefix("fixed_"), (x, y), xytext=(6, 5), textcoords="offset points")
    ax.set(xlabel="Observed batch API USD per 1,000 requests", ylabel="User-macro NDCG@10",
           title="Frozen policies: quality and counterfactual API cost")
    ax.grid(alpha=.25)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "policy_quality_cost.png", dpi=180)
    fig.savefig(output / "policy_quality_cost.svg")
    plt.close(fig)


def run_final_analysis(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        matrix = root / config["analysis"]["matrix_run"]
        evaluated = json.loads((matrix / "manifest.json").read_text())
        if evaluated["status"] != "completed" or not evaluated.get("test_scored"):
            raise ValueError("Final analysis requires a complete frozen test matrix")
        source = root / evaluated["prepared_run"]
        original = yaml.safe_load((source / "config.yaml").read_text(encoding="utf-8"))
        frozen = verify_final_config(original, root)
        if digest(source / "routing_decisions.json") != evaluated["routing_decisions_sha256"]:
            raise ValueError("Saved test decisions were altered")
        decisions = json.loads((source / "routing_decisions.json").read_text())
        outcomes = json.loads((matrix / "outcomes.json").read_text())
        calls = [json.loads(line) for line in (matrix / "calls.jsonl").read_text().splitlines()]
        settings = {**frozen["analysis"], "seed": original["seed"]}
        budget = str(settings["primary_budget_usd_per_1000"])

        def resolve(name):
            return name if name.startswith("fixed_") else f"{name}_{budget}"

        settings["primary_comparison"] = [resolve(x) for x in settings["primary_comparison"]]
        settings["comparisons"] = [settings["primary_comparison"],
                                   *[[resolve(x) for x in pair] for pair in settings["secondary_comparisons"]]]
        write_json(run_dir / "analysis_settings.json", settings)
        result, rows = evaluate_decisions(outcomes, calls, decisions, ["R0", *original["evidence"]["plans"]], settings)
        write_json(run_dir / "analysis.json", result)
        write_json(run_dir / "policy_outcomes.json", rows)
        plot_policies(result, run_dir)
        manifest.update(test_scored=True, final_test_freeze=original["final_test_freeze"],
            matrix_outcome_sha256=digest(matrix / "outcomes.json"), routing_decisions_sha256=evaluated["routing_decisions_sha256"])
        print(json.dumps(result["comparisons"]), flush=True)
