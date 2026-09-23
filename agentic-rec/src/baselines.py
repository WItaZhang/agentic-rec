"""Conventional baseline training, validation selection and isolated test evaluation."""

import json
import time
from collections import Counter, defaultdict
from itertools import product

import numpy as np
from scipy import sparse

from .feature import popularity_features, relevant_items
from .metrics import multipositive_metrics, paired_bootstrap
from .model import ItemKNNModel, PopularityModel
from .utils import digest, write_json


def fit_itemknn(rows, positive_rating, neighbors, shrinkage):
    """Fit only the explicitly supplied training rows; negatives are seen, not likes."""
    if neighbors < 1 or shrinkage < 0:
        raise ValueError("Invalid neighbor count or shrinkage")
    popularity, seen = popularity_features(rows, positive_rating)
    catalog = tuple(sorted(popularity))
    item_index = {item: i for i, item in enumerate(catalog)}
    user_index = {user: i for i, user in enumerate(sorted(seen))}
    positives = relevant_items(rows, positive_rating)
    coordinates = [(user_index[user], item_index[item])
                   for user, items in positives.items() for item in items]
    x = sparse.csr_matrix((np.ones(len(coordinates)),
                           ([p[0] for p in coordinates], [p[1] for p in coordinates])),
                          shape=(len(user_index), len(catalog)))
    counts = np.asarray(x.sum(axis=0)).ravel()
    cooccurrence = (x.T @ x).tocsr()
    indptr, indices, values = [0], [], []
    for i in range(len(catalog)):
        start, end = cooccurrence.indptr[i:i + 2]
        targets, common = cooccurrence.indices[start:end], cooccurrence.data[start:end]
        mask = targets != i
        targets, common = targets[mask], common[mask]
        similarities = common / (np.sqrt(counts[i] * counts[targets]) + shrinkage)
        order = np.lexsort((targets, -similarities))[:neighbors]
        indices.extend(targets[order].tolist())
        values.extend(similarities[order].tolist())
        indptr.append(len(indices))
    graph = sparse.csr_matrix((values, indices, indptr), shape=(len(catalog), len(catalog)))
    model = ItemKNNModel(catalog, graph, tuple(popularity[item] for item in catalog))
    return model, seen, positives


def evaluate_users(model, seen, positives, rows, threshold, k, history_boundary):
    relevant = relevant_items(rows, threshold)
    catalog = set(model.ranked_items)
    outcomes = []
    for user, targets in sorted(relevant.items()):
        history = seen.get(user, set())
        targets = targets - history
        if not targets:
            continue
        start = time.perf_counter()
        if isinstance(model, ItemKNNModel):
            ranking = model.recommend(history, k, positives.get(user, set()))
        else:
            ranking = model.recommend(history, k)
        latency = (time.perf_counter() - start) * 1000
        if set(ranking) - catalog or set(ranking) & history:
            raise AssertionError("Candidate/seen constraint violated")
        group = "cold" if not history else (
            "short_history" if len(history) <= history_boundary else "long_history")
        outcomes.append({"user": user, "group": group, "history_count": len(history),
                         "positive_targets": len(targets), "cold_targets": len(targets - catalog),
                         "latency_ms": latency, "ranking": ranking,
                         **multipositive_metrics(ranking, targets, k)})
    return outcomes


def aggregate(outcomes):
    if not outcomes:
        return {"users": 0}
    return {"users": len(outcomes),
            "ndcg_at_k": float(np.mean([x["ndcg_at_k"] for x in outcomes])),
            "recall_at_k": float(np.mean([x["recall_at_k"] for x in outcomes])),
            "positive_targets": sum(x["positive_targets"] for x in outcomes),
            "cold_item_positives_counted_as_misses": sum(x["cold_targets"] for x in outcomes),
            "cold_users_included": sum(x["history_count"] == 0 for x in outcomes),
            "latency_mean_ms": float(np.mean([x["latency_ms"] for x in outcomes])),
            "latency_p95_ms": float(np.percentile([x["latency_ms"] for x in outcomes], 95))}


def run_baselines(config, splits, run_dir):
    start, cpu_start = time.perf_counter(), time.process_time()
    threshold, k = config["model"]["positive_rating"], config["train"]["k"]
    popularity, seen = popularity_features(splits["train"], threshold)
    positives = relevant_items(splits["train"], threshold)
    base = PopularityModel(tuple(sorted(popularity, key=lambda item: (-popularity[item], item))))
    boundary = float(np.quantile([len(items) for items in seen.values()],
                                config["evaluation"]["history_quantile"]))
    grid = []
    best_key, selected, chosen = None, None, None
    for neighbors, shrinkage in product(config["model"]["neighbors_grid"],
                                       config["model"]["shrinkage_grid"]):
        tick = time.perf_counter()
        model, _, _ = fit_itemknn(splits["train"], threshold, neighbors, shrinkage)
        fit_seconds = time.perf_counter() - tick
        outcomes = evaluate_users(model, seen, positives, splits["validation"], threshold, k, boundary)
        metrics = aggregate(outcomes)
        grid.append({"neighbors": neighbors, "shrinkage": shrinkage,
                     "fit_seconds": fit_seconds, **metrics})
        key = (metrics["ndcg_at_k"], -neighbors, -shrinkage)
        if best_key is None or key > best_key:
            best_key, selected, chosen = key, model, {"neighbors": neighbors, "shrinkage": shrinkage}
    write_json(run_dir / "validation_grid.json", grid)
    # Write the complete selection before looking at held-out test rows.
    freeze = {"protocol_id": config["protocol_id"], "selection_partition": "validation",
              "selection_metric": "ndcg_at_k", "selected": chosen,
              "history_boundary": boundary, "history_boundary_source": "training_users",
              "primary_comparison": "itemknn_minus_popularity", "evaluation": config["evaluation"]}
    write_json(run_dir / "selection_frozen.json", freeze)
    sparse.save_npz(run_dir / "itemknn.npz", selected.similarity)
    write_json(run_dir / "model.json", {"catalog": selected.catalog, "popularity": selected.popularity,
                                        "hyperparameters": chosen})
    print(f"Validation selection frozen: {chosen}; test labels not used for selection.")
    metrics, records, statistics = {}, [], {}
    for partition in ("validation", "test"):
        by_method = {}
        metrics[partition] = {}
        for name, model in (("popularity", base), ("itemknn", selected)):
            outcomes = evaluate_users(model, seen, positives, splits[partition], threshold, k, boundary)
            by_method[name] = outcomes
            groups = defaultdict(list)
            for row in outcomes:
                groups[row["group"]].append(row)
            metrics[partition][name] = {"overall": aggregate(outcomes),
                                       "groups": {key: aggregate(value) for key, value in groups.items()}}
            records.extend({"partition": partition, "method": name, **row} for row in outcomes)
        left, right = by_method["itemknn"], by_method["popularity"]
        assert [row["user"] for row in left] == [row["user"] for row in right]
        statistics[partition] = {}
        for group in ("overall", "cold", "short_history", "long_history"):
            indices = [i for i, row in enumerate(left) if group == "overall" or row["group"] == group]
            if not indices:
                continue
            statistics[partition][group] = {metric: paired_bootstrap(
                [left[i][metric] for i in indices], [right[i][metric] for i in indices],
                config["evaluation"]["bootstrap_repetitions"], config["seed"],
                config["evaluation"]["confidence_level"])
                for metric in ("ndcg_at_k", "recall_at_k")}
    (run_dir / "predictions.jsonl").write_text(
        "".join(json.dumps(row, sort_keys=True) + "\n" for row in records), encoding="utf-8")
    write_json(run_dir / "metrics.json", metrics)
    write_json(run_dir / "statistics.json", statistics)
    write_json(run_dir / "resources.json", {
        "wall_seconds": time.perf_counter() - start, "cpu_seconds": time.process_time() - cpu_start,
        "paid_api_usd": 0, "llm_calls": 0, "input_tokens": 0, "output_tokens": 0,
        "training_grid_fits": len(grid), "fit_seconds_total": sum(x["fit_seconds"] for x in grid),
        "selection_sha256": digest(run_dir / "selection_frozen.json"),
        "cache": "none", "concurrency": 1, "device": "cpu"})
    write_json(run_dir / "dataset_profile.json", {
        "partitions": {name: {"ratings": len(rows), "users": len({r.user for r in rows}),
                               "items": len({r.item for r in rows}),
                               "rating_counts": dict(Counter(r.rating for r in rows))}
                       for name, rows in splits.items()},
        "training_history_quantiles": {str(q): float(np.quantile([len(x) for x in seen.values()], q))
                                       for q in (0, .25, .5, .75, 1)},
        "group_boundary_source": "training_only"})
    return metrics
