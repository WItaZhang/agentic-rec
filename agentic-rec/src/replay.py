"""Offline model selection, fixed candidate materialization and development evaluation."""

import hashlib
import json
import time
from dataclasses import asdict
from itertools import product

from scipy import sparse

from .baselines import fit_itemknn
from .data import load_amazon_reviews
from .feature import popularity_features
from .metrics import aggregate_requests, single_target_metrics
from .model import ItemKNNModel, PopularityModel
from .protocol import CandidateSnapshot, hash_sample, replay_requests
from .utils import digest, managed_run, utc_seconds, write_json


def model_fingerprint(model):
    if hasattr(model, "checkpoint_hash"):
        return model.checkpoint_hash
    value = hashlib.sha256()
    if isinstance(model, ItemKNNModel):
        value.update(json.dumps([model.catalog, model.popularity]).encode())
        for array in (model.similarity.data, model.similarity.indices, model.similarity.indptr):
            value.update(array.tobytes())
    else:
        value.update(json.dumps(model.ranked_items).encode())
    return value.hexdigest()


def make_candidates(request, model, candidate_count, positive_rating, model_hash):
    """Inference only: no evaluation target parameter or global label lookup."""
    seen = {event.item for event in request.history}
    positive = {event.item for event in request.history if event.rating >= positive_rating}
    if isinstance(model, ItemKNNModel) or hasattr(model, "score_history"):
        values = (model.score_items(positive) if isinstance(model, ItemKNNModel)
                  else model.score_history(request.history, positive_rating))
        indices = sorted(range(len(model.catalog)),
                         key=lambda i: (-values[i], -model.popularity[i], model.catalog[i]))
        indices = [i for i in indices if model.catalog[i] not in seen][:candidate_count]
        items = tuple(model.catalog[i] for i in indices)
        scores = tuple(float(values[i]) for i in indices)
    else:
        items = tuple(model.recommend(seen, candidate_count))
        # Rank-derived scores are explicitly identified, not claimed as probabilities.
        index = {item: i for i, item in enumerate(model.ranked_items)}
        scores = tuple(float(len(index) - index[item]) for item in items)
    return CandidateSnapshot(request.request_id, items, scores, model_hash, request.prediction_time)


def evaluate_views(requests, target_table, model, count, threshold, k):
    model_hash = model_fingerprint(model)
    catalog = set(model.ranked_items)
    outcomes = []
    for request in requests:
        snapshot = make_candidates(request, model, count, threshold, model_hash)
        target = target_table[request.request_id]
        outcomes.append({"request_id": request.request_id, "user_id": request.user_id,
                         "history_count": len(request.history), "cold_item": target not in catalog,
                         **single_target_metrics(list(snapshot.item_ids[:k]), target,
                                                 snapshot.item_ids, k)})
    return outcomes


def run_replay(config, config_path, root):
    with managed_run(config, config_path, root) as (run_dir, manifest):
        raw = root / config["data"]["raw_path"]
        if digest(raw) != config["data"]["sha256"]:
            raise ValueError("Raw review checksum mismatch")
        events, audit = load_amazon_reviews(raw)
        threshold = config["protocol"]["positive_rating"]
        ends = [(name, utc_seconds(config["data"][key]) * 1000) for name, key in (
            ("base_train", "base_train_end"), ("policy_train", "policy_train_end"),
            ("validation", "validation_end"), ("test", "test_end"))]
        train_end = ends[0][1]
        inner_end = utc_seconds(config["data"]["inner_train_end"]) * 1000
        if inner_end >= train_end:
            raise ValueError("Inner model selection must precede policy training")
        if config["evaluation"]["partitions"] != ["policy_train", "validation"]:
            raise ValueError("Development replay cannot score final test labels")
        train = [event for event in events if event.timestamp < train_end]
        inner_train = [event for event in train if event.timestamp < inner_end]
        inner_pairs = list(replay_requests(train, [("inner_train", inner_end), ("inner_validation", train_end)], threshold))
        inner_views = [view for view, _ in inner_pairs if view.partition == "inner_validation"]
        inner_sample, inner_audit = hash_sample(inner_views, config["train"]["selection_max_users"], config["seed"])
        inner_targets = {label.request_id: label.item_id for _, label in inner_pairs}
        grid, selected, best_key = [], None, None
        count, k = config["model"]["candidate_count"], config["evaluation"]["k"]
        for neighbors, shrinkage in product(config["model"]["neighbors_grid"], config["model"]["shrinkage_grid"]):
            started = time.perf_counter()
            model, _, _ = fit_itemknn(inner_train, threshold, neighbors, shrinkage)
            quality = aggregate_requests(evaluate_views(inner_sample, inner_targets, model, count, threshold, k))
            grid.append({"neighbors": neighbors, "shrinkage": shrinkage, "quality": quality,
                         "wall_seconds": time.perf_counter() - started})
            score = (quality["user_macro"]["ndcg"], -neighbors, -shrinkage)
            if best_key is None or score > best_key:
                best_key, selected = score, {"neighbors": neighbors, "shrinkage": shrinkage}
        write_json(run_dir / "inner_validation_grid.json", grid)
        write_json(run_dir / "selection_frozen.json", {
            "scope": "base_train_internal_temporal_validation_only", "selected": selected,
            "inner_sample": inner_audit, "test_scored": False})
        itemknn, _, _ = fit_itemknn(train, threshold, **selected)
        popularity, _ = popularity_features(train, threshold)
        pop = PopularityModel(tuple(sorted(popularity, key=lambda item: (-popularity[item], item))))
        models = {"popularity": pop, "itemknn": itemknn}
        sparse.save_npz(run_dir / "itemknn.npz", itemknn.similarity)
        write_json(run_dir / "model.json", {"catalog": itemknn.catalog, "popularity": itemknn.popularity,
                                           "selected": selected, "base_train_end": train_end})
        pairs = list(replay_requests(events, ends, threshold))
        target_table = {label.request_id: label.item_id for _, label in pairs}
        by_partition = {name: [view for view, _ in pairs if view.partition == name]
                        for name, _ in ends}
        sample_audit, samples = {}, {}
        for partition, maximum in config["sampling"]["max_users"].items():
            samples[partition], sample_audit[partition] = hash_sample(
                by_partition[partition], maximum, config["seed"])
        metrics, resources = {}, {"model_grid_runs": len(grid), "llm_calls": 0, "paid_api_usd": 0}
        for partition in config["evaluation"]["partitions"]:
            metrics[partition] = {}
            for name, model in models.items():
                started = time.perf_counter()
                outcomes = evaluate_views(by_partition[partition], target_table, model, count, threshold, k)
                metrics[partition][name] = aggregate_requests(outcomes)
                resources[f"{partition}_{name}_wall_seconds"] = time.perf_counter() - started
                print(f"{partition}/{name}: {metrics[partition][name]}")
        processed = root / config["data"]["processed_path"] / run_dir.name
        processed.mkdir()
        # Inference files contain no targets, ranks of targets or target reviews.
        with (processed / "requests.jsonl").open("w", encoding="utf-8") as views_file, \
                (processed / "candidates.jsonl").open("w", encoding="utf-8") as candidates_file, \
                (processed / "evaluator_targets.jsonl").open("w", encoding="utf-8") as targets_file:
            for partition, requests in samples.items():
                for request in requests:
                    views_file.write(json.dumps({"request_id": request.request_id, "user_id": request.user_id,
                                                 "prediction_time": request.prediction_time, "partition": partition,
                                                 "history_event_ids": [event.event_id for event in request.history]}) + "\n")
                    targets_file.write(json.dumps({"request_id": request.request_id,
                                                   "item_id": target_table[request.request_id]}) + "\n")
                    for name, model in models.items():
                        snapshot = make_candidates(request, model, count, threshold, model_fingerprint(model))
                        candidates_file.write(json.dumps({"retriever": name, "content_hash": snapshot.content_hash,
                                                          **asdict(snapshot)}) + "\n")
        manifest.update(raw_sha256=digest(raw), input_audit=audit, protocol_id=config["protocol"]["id"],
                        model_hashes={name: model_fingerprint(model) for name, model in models.items()},
                        processed_path=str(processed.relative_to(root)).replace("\\", "/"),
                        artifact_hashes={path.name: digest(path) for path in processed.iterdir()},
                        test_scored=False)
        if manifest["raw_sha256"] != config["data"]["sha256"]:
            raise RuntimeError("Raw data changed during run")
        write_json(run_dir / "sampling.json", sample_audit)
        write_json(run_dir / "metrics.json", metrics)
        write_json(run_dir / "resources.json", resources)
        write_json(run_dir / "split_summary.json", {
            name: {"eligible_requests": len(by_partition[name]), "end_exclusive": end,
                   "zero_history_requests": sum(not view.history for view in by_partition[name])}
            for name, end in ends})
