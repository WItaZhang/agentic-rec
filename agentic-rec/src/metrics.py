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
