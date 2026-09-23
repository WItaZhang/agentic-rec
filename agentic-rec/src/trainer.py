"""Fit and evaluate a fixed-origin popularity baseline."""

import math

from .feature import popularity_features, relevant_items
from .model import PopularityModel
from .utils import write_json


def fit(rows, positive_rating):
    scores, seen = popularity_features(rows, positive_rating)
    model = PopularityModel(tuple(sorted(scores, key=lambda item: (-scores[item], item))))
    return model, seen


def evaluate(model, seen, rows, positive_rating, k):
    if k < 1:
        raise ValueError("k must be positive")
    catalog = set(model.ranked_items)
    relevant = relevant_items(rows, positive_rating)
    recalls, ndcgs = [], []
    cold_users = cold_items = excluded = positives = 0
    for user, targets in sorted(relevant.items()):
        history = seen.get(user, set())
        targets = targets - history
        if not targets:
            excluded += 1
            continue
        cold_users += int(user not in seen)
        cold_items += len(targets - catalog)
        positives += len(targets)
        recommendations = model.recommend(history, k)
        hits = [int(item in targets) for item in recommendations]
        recalls.append(sum(hits) / len(targets))
        dcg = sum(hit / math.log2(rank + 2) for rank, hit in enumerate(hits))
        ideal = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(targets))))
        ndcgs.append(dcg / ideal)
    count = len(recalls)
    return {
        "k": k,
        "recall_at_k": sum(recalls) / count if count else None,
        "ndcg_at_k": sum(ndcgs) / count if count else None,
        "evaluated_users": count,
        "cold_users_included": cold_users,
        "cold_item_positives_counted_as_misses": cold_items,
        "positive_targets": positives,
        "users_without_eligible_positives": len({r.user for r in rows} - relevant.keys()) + excluded,
    }


def run_experiment(config, splits, run_dir):
    if config["model"]["name"] == "baseline_suite":
        from .baselines import run_baselines

        return run_baselines(config, splits, run_dir)
    threshold = config["model"]["positive_rating"]
    model, seen = fit(splits["train"], threshold)
    write_json(run_dir / "model.json", {"ranked_items": model.ranked_items})
    metrics = {
        name: evaluate(model, seen, splits[name], threshold, config["train"]["k"])
        for name in ("validation", "test")
    }
    write_json(run_dir / "metrics.json", metrics)
    return metrics
