"""Post-evaluation sensitivity: calibrate random spending using costs, never quality."""

import gzip
import json

import numpy as np

from .evidence_analysis import validate_table
from .metrics import paired_bootstrap
from .routing_model import random_actions
from .routing_trainer import random_probabilities
from .utils import digest, managed_run, write_json


def verified_archive(source, checksum):
    path = source / "archive_manifest.json"
    if digest(path) != checksum:
        raise ValueError("Pinned archive manifest changed")
    record = json.loads(path.read_text(encoding="utf-8"))
    if record["status"] != "completed" or record["kind"] != "policy":
        raise ValueError("A complete policy archive is required")
    for name, expected in record["files"].items():
        if "/" in name or "\\" in name or digest(source / name) != expected:
            raise ValueError("Archive file changed or filename is unsafe")
    return record


def calibrate(ids, actions, calls, plans, tolerance):
    """No outcomes/features/labels are accepted at this boundary."""
    if not ids or len(set(ids)) != len(ids) or len(actions) != len(ids) or set(actions) - set(plans):
        raise ValueError("Complete unique requests and valid saved actions required")
    if not plans or plans[0] != "R0" or len(plans) != len(set(plans)) or not 0 <= tolerance <= 1e-12:
        raise ValueError("Zero-cost R0 first, unique plans and roundoff-only tolerance required")
    table = {(row["request_id"], row["plan"]): row for row in calls}
    expected_keys = {(q, plan) for q in ids for plan in plans[1:]}
    if len(table) != len(calls) or set(table) != expected_keys:
        raise ValueError("Complete cost accounting required; no missing, duplicate or extra requests")
    costs = np.zeros((len(ids), len(plans)))
    for i, q in enumerate(ids):
        for j, plan in enumerate(plans[1:], 1):
            row = table[q, plan]
            cost = row["actual_known_usd"]
            if cost is None or not np.isfinite(cost) or cost < 0 or row.get("usage") is None:
                raise ValueError("Sensitivity requires known observed costs for every attempted action")
            costs[i, j] = cost
    matched = random_probabilities(actions, costs, plans)
    if abs(matched["target_validation_usd"] - matched["expected_validation_usd"]) > tolerance:
        raise ValueError("Requested cost match is infeasible with this conditional action mixture")
    receipt = {
        "scope": "post_evaluation_exploratory_cost_diagnostic",
        "calibration_inputs": "saved actions and observed costs only; no quality, targets or features",
        "requests": len(ids), "plans": list(plans),
        "learner_action_counts": {plan: actions.count(plan) for plan in plans},
        "probabilities": matched["probabilities"],
        "mean_plan_costs_usd": costs.mean(axis=0).tolist(),
        "learner_mean_usd": matched["target_validation_usd"],
        "random_expected_mean_usd": matched["expected_validation_usd"],
        "absolute_cost_tolerance": tolerance,
        "definition": "Preserve the learner's conditional non-R0 action mix; rescale its total call probability to match observed mean cost",
        "deployment_eligible": False,
    }
    return receipt, costs


def evaluate(rows, calls, ids, actions, plans, receipt, costs, settings, seeds):
    table, _ = validate_table(rows, calls, plans)
    if set(table) != set(ids) or len({table[q]["R0"]["user_id"] for q in ids}) != len(ids):
        raise ValueError("All calibrated requests must be paired independent users")
    p = np.array(receipt["probabilities"])
    indices = np.array([plans.index(action) for action in actions])
    result = {"users": len(ids), "scope": receipt["scope"], "quality": {},
        "interval_scope": "Nominal paired user bootstrap conditional on the cost calibration and saved model outputs; not confirmatory or uncertainty over a newly fitted future calibration",
        "cost_match_scope": "Exact full-population expectation; sampled allocations can have different realized costs",
        "paid_api_usd": 0, "deployment_reselected": False}
    matrices = {}
    for metric in ("ndcg", "hr"):
        matrix = np.array([[table[q][plan][metric] for plan in plans] for q in ids])
        matrices[metric] = matrix
        learner = matrix[np.arange(len(ids)), indices]
        expected = matrix @ p
        result["quality"][metric] = {"learner_mean": float(learner.mean()),
            "random_expected_mean": float(expected.mean()),
            "learner_minus_expected_random": paired_bootstrap(learner, expected,
                settings["bootstrap_repetitions"], settings["seed"], settings["confidence"])}
    samples = []
    for seed in seeds:
        allocation = random_actions(ids, p, plans, seed)
        columns = [plans.index(action) for action in allocation]
        samples.append({"seed": seed, "action_counts": {plan: allocation.count(plan) for plan in plans},
            "mean_accounted_usd": float(costs[np.arange(len(ids)), columns].mean()),
            **{f"mean_{metric}": float(matrix[np.arange(len(ids)), columns].mean()) for metric, matrix in matrices.items()}})
    result["allocation_seed_sensitivity"] = samples
    return result


def run_cost_alignment(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        source = root / config["archive_path"]
        record = verified_archive(source, config["archive_sha256"])
        calls = [json.loads(line) for line in gzip.decompress((source / "calls.jsonl.gz").read_bytes()).decode().splitlines()]
        decisions = json.loads((source / "routing_decisions.json").read_text(encoding="utf-8"))
        if decisions["label_access"] is not False:
            raise ValueError("Original routing decisions must exclude labels")
        plans, policy = config["plans"], config["policy"]
        ids, actions = decisions["request_ids"], decisions["actions"][policy]
        receipt, costs = calibrate(ids, actions, calls, plans, config["absolute_cost_tolerance"])
        receipt.update(archive_sha256=config["archive_sha256"], policy=policy,
            calls_sha256=record["files"]["calls.jsonl.gz"], decisions_sha256=record["files"]["routing_decisions.json"])
        # Persist the cost-only allocation before decoding any outcome quality.
        write_json(run_dir / "cost_calibration.json", receipt)
        rows = json.loads(gzip.decompress((source / "outcomes.json.gz").read_bytes()))
        settings = json.loads((source / "analysis_settings.json").read_text(encoding="utf-8"))
        seeds = [decisions["random_parameters"][policy.replace("learned_", "random_", 1)]["seed"],
                 *settings["random_sensitivity_seeds"]]
        result = evaluate(rows, calls, ids, actions, plans, receipt, costs, settings, seeds)
        write_json(run_dir / "analysis.json", result)
        manifest.update(archive_sha256=config["archive_sha256"], paid_api_usd=0,
            cost_calibration_sha256=digest(run_dir / "cost_calibration.json"),
            scope=receipt["scope"], test_reselected=False)
        print(json.dumps({"cost_calibration": receipt, "quality": result["quality"]}), flush=True)
