"""Load complete development matrices and reconstruct label-free routing inputs."""

import json
import time

import numpy as np

from .data import load_amazon_reviews
from .evidence_analysis import validate_table
from .feature import routing_features
from .llm_experiment import choose_views
from .model_artifacts import load_frozen_retriever
from .protocol import CandidateSnapshot
from .utils import digest, verified_run_config


def load_routing_data(root, run_path, expected_partition, plans):
    directory = root / run_path
    manifest = json.loads((directory / "manifest.json").read_text())
    if manifest["status"] != "completed" or manifest.get("test_scored"):
        raise ValueError("Routing development requires completed, non-test outcomes")
    inference = root / manifest["prepared_run"] if "prepared_run" in manifest else directory
    source_config = verified_run_config(inference)
    if source_config["evaluation"]["partition"] != expected_partition:
        raise ValueError("Policy fitting/selection partition mismatch")
    if expected_partition == "validation" and source_config["sampling"]["mode"] != "uniform_users":
        raise ValueError("Routing selection requires population validation, not diagnostic strata")
    if digest(root / source_config["data"]["raw_path"]) != source_config["data"]["sha256"]:
        raise ValueError("Input source changed")
    outcomes = json.loads((directory / "outcomes.json").read_text())
    calls = [json.loads(line) for line in (directory / "calls.jsonl").read_text().splitlines()]
    table, call_table = validate_table(outcomes, calls, plans)
    events, _ = load_amazon_reviews(root / source_config["data"]["raw_path"])
    views, _, _ = choose_views(events, source_config)
    views = {view.request_id: view for view in views}
    if set(views) != set(table):
        raise ValueError("Outcome matrix differs from the frozen user sample")
    model = load_frozen_retriever(root, source_config["retriever"])
    catalog = set(model.catalog)
    candidates = json.loads((inference / "candidates.json").read_text())
    features, feature_ms = {}, {}
    for request_id, record in candidates.items():
        arguments = {key: record[key] for key in ("request_id", "item_ids", "scores", "model_hash", "prediction_time")}
        arguments["item_ids"], arguments["scores"] = tuple(arguments["item_ids"]), tuple(arguments["scores"])
        snapshot = CandidateSnapshot(**arguments)
        if snapshot.content_hash != table[request_id][plans[1]]["candidate_hash"]:
            raise ValueError("Policy features and outcome candidates differ")
        start = time.perf_counter()
        features[request_id] = routing_features(views[request_id], snapshot, catalog,
                                               source_config["protocol"]["positive_rating"])
        feature_ms[request_id] = (time.perf_counter() - start) * 1000
    ids = sorted(table)
    if len({table[q]["R0"]["user_id"] for q in ids}) != len(ids):
        raise ValueError("Current router fitting requires one sampled request per user")
    costs = np.zeros((len(ids), len(plans)))
    sample_audit = json.loads((inference / "sampling.json").read_text())
    inclusion = sample_audit.get("user_inclusion_probability_by_request", {})
    weights = np.array([1 / inclusion.get(q, 1) for q in ids], dtype=float)
    weights /= weights.mean()
    quality = np.array([[table[q][plan]["ndcg"] for plan in plans] for q in ids])
    for i, request in enumerate(ids):
        for j, plan in enumerate(plans[1:], 1):
            call = call_table[request, plan]
            costs[i, j] = call["actual_known_usd"] if call["actual_known_usd"] is not None else call["reserved_usd"]
    physical_costs = {r["call_id"]: r["actual_known_usd"] if r["actual_known_usd"] is not None else r["reserved_usd"] for r in calls}
    return {"ids": ids, "features": [features[q] for q in ids], "quality": quality, "costs": costs, "fit_weights": weights,
            "label_physical_cost": sum(physical_costs.values()),
            "feature_ms": feature_ms, "source_config": source_config, "table": table,
            "outcome_sha256": digest(directory / "outcomes.json"), "calls_sha256": digest(directory / "calls.jsonl")}
