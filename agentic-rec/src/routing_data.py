"""Load complete development matrices and reconstruct label-free routing inputs."""

import gzip
import json
import time

import numpy as np

from .data import load_amazon_reviews
from .evidence_analysis import validate_table
from .feature import routing_features
from .model_artifacts import load_frozen_retriever
from .protocol import CandidateSnapshot
from .utils import digest, verified_run_config


def load_routing_data(root, run_path, expected_partition, plans):
    from .llm_experiment import choose_views

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


def save_routing_matrix(path, data):
    """Public derived training data: no user IDs, review text, prompts or current targets."""
    keys = ("ids", "features", "source_config", "label_physical_cost", "feature_ms", "outcome_sha256", "calls_sha256")
    record = {key: data[key] for key in keys}
    record.update({key: data[key].tolist() for key in ("quality", "costs", "fit_weights")})
    path.write_bytes(gzip.compress(json.dumps(record, sort_keys=True).encode(), mtime=0))


def load_routing_matrix(root, settings, expected_partition, plans):
    path = root / settings["path"]
    if digest(path) != settings["sha256"]:
        raise ValueError("Published routing matrix changed")
    data = json.loads(gzip.decompress(path.read_bytes()))
    source = data["source_config"]
    if expected_partition not in ("policy_train", "validation") or source["evaluation"]["partition"] != expected_partition:
        raise ValueError("Published matrix has the wrong development partition")
    if expected_partition == "validation" and source["sampling"]["mode"] != "uniform_users":
        raise ValueError("Validation must represent the full request population")
    if ["R0", *source["evidence"]["plans"]] != list(plans):
        raise ValueError("Published matrix action order changed")
    for key in ("quality", "costs", "fit_weights"):
        data[key] = np.asarray(data[key], dtype=float)
        if not np.isfinite(data[key]).all():
            raise ValueError("Non-finite archived training values")
    n = len(data["ids"])
    if not n or len(set(data["ids"])) != n or len(data["features"]) != n:
        raise ValueError("Training rows are missing, duplicated or misaligned")
    if data["quality"].shape != (n, len(plans)) or data["costs"].shape != data["quality"].shape or data["fit_weights"].shape != (n,):
        raise ValueError("Published training matrix dimensions changed")
    if np.any(data["costs"] < 0) or np.any(data["fit_weights"] <= 0) or np.any((data["quality"] < 0) | (data["quality"] > 1)):
        raise ValueError("Invalid cost, quality or inclusion weight")
    return data
