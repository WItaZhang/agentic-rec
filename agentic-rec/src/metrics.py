"""Pure ranking metrics and paired user bootstrap; no file or model access."""

import math

import numpy as np


def multipositive_metrics(ranking, targets, k):
    if not targets or k < 1:
        raise ValueError("Nonempty targets and positive k required")
    if len(ranking) != len(set(ranking)):
        raise ValueError("Repeated recommendations invalidate metrics")
    hits = [int(item in targets) for item in ranking[:k]]
    dcg = sum(hit / math.log2(rank + 2) for rank, hit in enumerate(hits))
    ideal = sum(1 / math.log2(rank + 2) for rank in range(min(k, len(targets))))
    return {"recall_at_k": sum(hits) / len(targets), "ndcg_at_k": dcg / ideal}


def paired_bootstrap(left, right, repetitions, seed, confidence):
    """Aligned independent user values. Never treat events as independent users."""
    difference = np.asarray(left, dtype=float) - np.asarray(right, dtype=float)
    if difference.ndim != 1 or not len(difference) or len(left) != len(right):
        raise ValueError("Aligned nonempty user arrays required")
    rng = np.random.default_rng(seed)
    means = np.empty(repetitions)
    for i in range(repetitions):
        means[i] = rng.choice(difference, size=len(difference), replace=True).mean()
    tail = (1 - confidence) / 2
    return {"difference": float(difference.mean()), "users": len(difference),
            "ci_low": float(np.quantile(means, tail)),
            "ci_high": float(np.quantile(means, 1 - tail)),
            "confidence": confidence, "repetitions": repetitions, "unit": "user"}


def single_target_metrics(ranking, target, candidates, k):
    if len(ranking) != len(set(ranking)) or set(ranking) - set(candidates):
        raise ValueError("Ranking must be unique and inside frozen candidates")
    rank = ranking.index(target) + 1 if target in ranking else None
    hit = rank is not None and rank <= k
    return {"ndcg": 1 / math.log2(rank + 1) if hit else 0.0,
            "hr": float(hit), "candidate_recall": float(target in candidates)}


def aggregate_requests(outcomes):
    from collections import defaultdict

    by_user = defaultdict(list)
    for row in outcomes:
        by_user[row["user_id"]].append(row)
    if not outcomes:
        return {"requests": 0, "users": 0}
    metrics = ("ndcg", "hr", "candidate_recall")
    user_values = {user: {key: float(np.mean([row[key] for row in rows])) for key in metrics}
                   for user, rows in by_user.items()}
    return {"requests": len(outcomes), "users": len(by_user),
            "user_macro": {key: float(np.mean([row[key] for row in user_values.values()]))
                           for key in metrics},
            "request_micro": {key: float(np.mean([row[key] for row in outcomes])) for key in metrics},
            "cold_item_misses": sum(row.get("cold_item", False) for row in outcomes),
            "zero_history_requests": sum(row.get("history_count", 0) == 0 for row in outcomes)}
