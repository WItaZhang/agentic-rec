"""Fit full-information utility estimates; select all routing parameters on validation."""

import itertools
import json
import time

import joblib
import numpy as np

from .routing_data import load_routing_data
from .routing_model import UtilityRouter, build_quality_estimator, random_actions, rule_actions
from .utils import digest, managed_run, write_json


def replay_actions(data, actions, plans):
    indices = np.array([plans.index(action) for action in actions])
    rows = np.arange(len(indices))
    return {"ndcg": float(data["quality"][rows, indices].mean()),
            "mean_accounted_usd": float(data["costs"][rows, indices].mean()),
            "action_counts": {plan: actions.count(plan) for plan in plans}, "requests": len(actions)}


def random_probabilities(actions, validation_costs, plans):
    """Match observed validation spending in expectation, independent of request features."""
    target_indices = np.array([plans.index(action) for action in actions])
    target = validation_costs[np.arange(len(actions)), target_indices].mean()
    frequencies = np.array([actions.count(plan) / len(actions) for plan in plans])
    expected = float(np.dot(frequencies, validation_costs.mean(axis=0)))
    scale = target / expected if expected else 0
    probabilities = frequencies * scale
    probabilities[0] = 0
    if probabilities.sum() > 1:
        probabilities /= probabilities.sum()
    probabilities[0] = 1 - probabilities.sum()
    return {"probabilities": probabilities.tolist(), "target_validation_usd": float(target),
            "expected_validation_usd": float(np.dot(probabilities, validation_costs.mean(axis=0))),
            "definition": "frozen marginal allocation; actual test cost can differ"}


def run_routing(config, config_path, root):
    from threadpoolctl import threadpool_limits

    with managed_run(config, config_path, root) as (run_dir, manifest):
        settings = config["routing"]
        plans = tuple(settings["plans"])
        train = load_routing_data(root, settings["policy_run"], "policy_train", plans)
        validation = load_routing_data(root, settings["validation_run"], "validation", plans)
        for key in ("protocol", "data", "retriever", "evidence", "llm"):
            if train["source_config"][key] != validation["source_config"][key]:
                raise ValueError(f"Training/validation inference settings differ: {key}")
        names = tuple(settings["features"])
        x = np.array([[row[name] for name in names] for row in train["features"]])
        y = train["quality"][:, 1:] - train["quality"][:, [0]]
        costs = tuple(np.average(train["costs"], axis=0, weights=train["fit_weights"]))
        candidates, policies, fit_records = [], {}, []
        for estimator_id, parameters in enumerate(settings["estimators"]):
            start, cpu_start = time.perf_counter(), time.process_time()
            estimator = build_quality_estimator(parameters, config["seed"])
            with threadpool_limits(limits=config["runtime"]["cpu_threads"]):
                if parameters["kind"] == "ridge":
                    estimator.fit(x, y, standardscaler__sample_weight=train["fit_weights"],
                                  ridge__sample_weight=train["fit_weights"])
                else:
                    estimator.fit(x, y, sample_weight=train["fit_weights"])
            path = run_dir / f"estimator_{estimator_id}.joblib"
            joblib.dump(estimator, path)
            fit_records.append({"id": estimator_id, "parameters": parameters, "sha256": digest(path),
                                "wall_seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu_start})
            for weight in settings["cost_weights"]:
                policy_id = f"learned_{estimator_id}_weight_{weight}"
                policy = UtilityRouter(estimator, plans, names, costs, weight)
                started = time.perf_counter()
                with threadpool_limits(limits=config["runtime"]["cpu_threads"]):
                    actions = policy.decide(validation["features"])
                policies[policy_id] = {"kind": "learned", "estimator_id": estimator_id, "cost_weight": weight,
                    "actions": actions, "inference_total_ms": (time.perf_counter() - started) * 1000}
                candidates.append({"id": policy_id, "kind": "learned", **replay_actions(validation, actions, plans)})
        for name in settings["rules"]:
            actions = rule_actions(validation["features"], name)
            policies[name] = {"kind": "rule", "rule": name, "actions": actions}
            candidates.append({"id": name, "kind": "rule", **replay_actions(validation, actions, plans)})
        for plan in plans:
            actions = [plan] * len(validation["ids"])
            policies[f"fixed_{plan}"] = {"kind": "fixed", "plan": plan, "actions": actions}
            candidates.append({"id": f"fixed_{plan}", "kind": "fixed", **replay_actions(validation, actions, plans)})
        chosen = {}
        for budget, kind in itertools.product(settings["budget_usd_per_1000"], ("learned", "rule", "fixed")):
            eligible = [c for c in candidates if c["kind"] == kind and c["mean_accounted_usd"] * 1000 <= budget]
            if not eligible:
                continue
            best = max(row["ndcg"] for row in eligible)
            near = [row for row in eligible if row["ndcg"] >= best - settings["validation_quality_tolerance"]]
            selected = min(near, key=lambda row: (row["mean_accounted_usd"], -row["ndcg"], row["id"]))
            policy = policies[selected["id"]]
            entry = {**selected, "policy": {k: v for k, v in policy.items() if k != "actions"}}
            if kind == "learned":
                random = random_probabilities(policy["actions"], validation["costs"], plans)
                actions = random_actions(validation["ids"], random["probabilities"], plans, settings["random_seed"])
                entry["random_control"] = {**random, "seed": settings["random_seed"],
                                           "observed_validation": replay_actions(validation, actions, plans)}
            chosen[f"{kind}_{budget}"] = entry
        primary_budget = config["analysis"]["primary_budget_usd_per_1000"]
        finalists = [(kind, chosen[f"{kind}_{primary_budget}"]) for kind in ("fixed", "rule", "learned")
                     if f"{kind}_{primary_budget}" in chosen]
        highest = max(row["ndcg"] for _, row in finalists)
        near = [(kind, row) for kind, row in finalists
                if row["ndcg"] >= highest - settings["validation_quality_tolerance"]]
        deploy_kind, deploy_row = min(near, key=lambda pair: (
            pair[1]["mean_accounted_usd"], {"fixed": 0, "rule": 1, "learned": 2}[pair[0]], pair[1]["id"]))
        deployment = {"kind": deploy_kind, "validation_budget_usd_per_1000": primary_budget,
                      "selected_policy": deploy_row, "selection_scope": "validation_only"}
        write_json(run_dir / "validation_grid.json", candidates)
        write_json(run_dir / "fit_resources.json", {"fits": fit_records, "paid_api_usd": 0,
            "sampling_correction": "inverse user-state inclusion weights, normalized to mean one",
            "policy_label_cost_already_accounted_usd": train["label_physical_cost"],
            "feature_computation_ms": {"policy_train": sum(train["feature_ms"].values()),
                                       "validation": sum(validation["feature_ms"].values())}})
        write_json(run_dir / "selection_frozen.json", {"selection_scope": "validation_only", "chosen": chosen,
            "plans": plans, "feature_names": names, "training_mean_costs": costs,
            "quality_tolerance": settings["validation_quality_tolerance"],
            "deployment_candidate": deployment,
            "cost_interpretation": "actual observed counterfactual matrix cost; cache/backend distribution can differ at deployment",
            "test_scored": False})
        manifest.update(test_scored=False, policy_outcome_sha256=train["outcome_sha256"],
                        validation_outcome_sha256=validation["outcome_sha256"])
        print(json.dumps({key: {"ndcg": value["ndcg"], "mean_usd": value["mean_accounted_usd"]}
                          for key, value in chosen.items()}), flush=True)
