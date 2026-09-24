"""Apply saved development-selected policies using observable features only."""

import json
import time

import joblib

from .routing_model import UtilityRouter
from .routing_trainer import random_actions, rule_actions
from .utils import digest


def decide_frozen_policies(root, selection_run, request_ids, features, expected_hashes, cpu_threads):
    from threadpoolctl import threadpool_limits

    directory = root / selection_run
    for name, checksum in expected_hashes.items():
        if digest(directory / name) != checksum:
            raise ValueError("Frozen routing artifact changed")
    selected = json.loads((directory / "selection_frozen.json").read_text())
    plans = tuple(selected["plans"])
    if len(request_ids) != len(features) or len(set(request_ids)) != len(request_ids):
        raise ValueError("One feature row per unique request required")
    models, decisions, timing = {}, {}, {}
    for identity, row in selected["chosen"].items():
        start = time.perf_counter()
        spec = row["policy"]
        if spec["kind"] == "learned":
            model_id = spec["estimator_id"]
            filename = f"estimator_{model_id}.joblib"
            if filename not in expected_hashes:
                raise ValueError("Selected estimator is absent from the frozen artifact list")
            if model_id not in models:
                models[model_id] = joblib.load(directory / filename)
            policy = UtilityRouter(models[model_id], plans, tuple(selected["feature_names"]),
                                   tuple(selected["training_mean_costs"]), spec["cost_weight"])
            with threadpool_limits(limits=cpu_threads):
                actions = policy.decide(features)
            control = row["random_control"]
            random_id = identity.replace("learned_", "random_", 1)
            decisions[random_id] = random_actions(request_ids, control["probabilities"], plans, control["seed"])
        elif spec["kind"] == "rule":
            actions = rule_actions(features, spec["rule"])
        elif spec["kind"] == "fixed":
            actions = [spec["plan"]] * len(features)
        else:
            raise ValueError("Unknown frozen policy kind")
        timing[identity] = (time.perf_counter() - start) * 1000
        decisions[identity] = actions
    for plan in plans:
        decisions[f"fixed_{plan}"] = [plan] * len(features)
    if any(len(actions) != len(request_ids) or set(actions) - set(plans) for actions in decisions.values()):
        raise ValueError("Invalid action output")
    return {"request_ids": request_ids, "actions": decisions, "label_access": False,
            "policy_batch_wall_ms_including_first_load": timing,
            "timing_scope": "offline decision preparation; not per-request serving latency"}
