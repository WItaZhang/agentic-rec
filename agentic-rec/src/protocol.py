"""Immutable inference views, evaluator-only labels, and timestamp-batch replay."""

import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from itertools import groupby

from .data import ReviewEvent


@dataclass(frozen=True)
class RequestView:
    request_id: str
    user_id: str
    prediction_time: int
    history: tuple[ReviewEvent, ...]
    partition: str

    def __post_init__(self):
        if any(event.timestamp >= self.prediction_time for event in self.history):
            raise ValueError("Evidence must strictly precede prediction time")
        if any(event.user != self.user_id for event in self.history):
            raise ValueError("User history contains another user's events")


@dataclass(frozen=True)
class EvaluationTarget:
    request_id: str
    item_id: str


@dataclass(frozen=True)
class CandidateSnapshot:
    request_id: str
    item_ids: tuple[str, ...]
    scores: tuple[float, ...]
    model_hash: str
    prediction_time: int

    def __post_init__(self):
        if len(self.item_ids) != len(set(self.item_ids)) or len(self.item_ids) != len(self.scores):
            raise ValueError("Candidates must be unique and aligned with scores")

    @property
    def content_hash(self):
        payload = {"request_id": self.request_id, "item_ids": self.item_ids, "scores": self.scores,
                   "model_hash": self.model_hash, "prediction_time": self.prediction_time}
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def replay_requests(events, boundaries, positive_rating):
    """Yield views and separate labels; reveal a timestamp's events only after all predictions."""
    if not boundaries or any(left[1] >= right[1] for left, right in zip(boundaries, boundaries[1:])):
        raise ValueError("Strictly increasing global partition ends required")
    histories = defaultdict(list)
    seen = defaultdict(set)
    for timestamp, batch in groupby(sorted(events, key=lambda row: (row.timestamp, row.event_id)),
                                   key=lambda row: row.timestamp):
        batch = list(batch)
        partition = next((name for name, end in boundaries if timestamp < end), None)
        if partition is None:
            break
        for event in batch:
            if event.rating >= positive_rating and event.item not in seen[event.user]:
                request_id = "q_" + event.event_id
                yield (RequestView(request_id, event.user, timestamp,
                                   tuple(histories[event.user]), partition),
                       EvaluationTarget(request_id, event.item))
        for event in batch:
            histories[event.user].append(event)
            seen[event.user].add(event.item)


def hash_sample(requests, max_users, seed):
    """One label-blind hash-selected request per user, then a uniform user hash sample."""
    def key(value):
        return hashlib.sha256(f"{seed}:{value}".encode()).hexdigest()

    by_user = defaultdict(list)
    for request in requests:
        by_user[request.user_id].append(request)
    users = sorted(by_user, key=lambda user: key("user:" + user))
    chosen = [min(by_user[user], key=lambda request: key("request:" + request.request_id))
              for user in users[:max_users]]
    audit = {"eligible_users": len(users), "eligible_requests": len(requests),
             "selected_users": len(chosen), "per_user_cap": 1,
             "user_inclusion_probability": min(1, max_users / len(users)) if users else 0,
             "within_user_request_probability": "1 / eligible requests for that user",
             "selection_uses_labels": False, "seed": seed}
    return sorted(chosen, key=lambda request: (request.prediction_time, request.request_id)), audit


def validate_ranking(ranking, candidates, k):
    """Target-free deterministic repair; preserve valid IDs, then fill in base order."""
    members = set(candidates.item_ids)
    result, errors = [], []
    for item in ranking:
        if item not in members:
            errors.append("outside_candidate")
        elif item in result:
            errors.append("duplicate")
        else:
            result.append(item)
    if len(result) < min(k, len(members)):
        errors.append("short_output")
    result.extend(item for item in candidates.item_ids if item not in result)
    return tuple(result[:k]), sorted(set(errors))
