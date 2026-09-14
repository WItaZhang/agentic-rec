from __future__ import annotations

import math
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, dataclass, field

from ..core.types import RecList, Trajectory


@dataclass
class RankingReport:
    k: int
    n_users: int
    hit_rate: float
    recall: float
    precision: float
    ndcg: float
    mrr: float
    coverage: float

    def as_dict(self) -> dict[str, float]:
        return asdict(self)

    def __str__(self) -> str:
        return (
            f"@{self.k} over {self.n_users} users | HR={self.hit_rate:.3f} R={self.recall:.3f} "
            f"P={self.precision:.3f} NDCG={self.ndcg:.3f} MRR={self.mrr:.3f} Cov={self.coverage:.3f}"
        )


@dataclass
class SimulationReport:
    n_episodes: int
    avg_turns: float
    click_rate: float  # fraction of turns with at least one click
    ctr: float  # clicked / shown
    exit_rate: float
    avg_reward: float
    coverage: float
    extra: dict[str, float] = field(default_factory=dict)

    def as_dict(self) -> dict[str, float]:
        d = asdict(self)
        d.update(d.pop("extra"))
        return d

    def __str__(self) -> str:
        return (
            f"{self.n_episodes} episodes | turns={self.avg_turns:.2f} click_rate={self.click_rate:.3f} "
            f"CTR={self.ctr:.3f} exit={self.exit_rate:.3f} reward={self.avg_reward:.3f} Cov={self.coverage:.3f}"
        )


def ranking_metrics(recs: Iterable[RecList], truth: Mapping[str, Sequence[str]], k: int = 10, n_items: int | None = None) -> RankingReport:
    hr = rec = prec = ndcg = mrr = 0.0
    n = 0
    shown: set[str] = set()
    for r in recs:
        pos = set(truth.get(r.user_id, ()))
        if not pos:
            continue
        n += 1
        top = r.top(k)
        shown.update(top)
        hits = [i for i in top if i in pos]
        hr += 1.0 if hits else 0.0
        rec += len(hits) / len(pos)
        prec += len(hits) / k
        dcg = sum(1.0 / math.log2(rank + 2) for rank, i in enumerate(top) if i in pos)
        idcg = sum(1.0 / math.log2(rank + 2) for rank in range(min(len(pos), k)))
        ndcg += dcg / idcg if idcg else 0.0
        for rank, i in enumerate(top):
            if i in pos:
                mrr += 1.0 / (rank + 1)
                break
    n = max(n, 1)
    cov = len(shown) / n_items if n_items else float(len(shown))
    return RankingReport(k, n, hr / n, rec / n, prec / n, ndcg / n, mrr / n, cov)


def simulation_metrics(trajs: Sequence[Trajectory], n_items: int | None = None) -> SimulationReport:
    n = len(trajs) or 1
    turns = clicks_turns = shown = clicked = exits = 0
    reward = 0.0
    seen: set[str] = set()
    strategies: dict[str, int] = {}
    for t in trajs:
        turns += t.n_turns
        for s in t.steps:
            shown += len(s.get("recommended", []))
            seen.update(s.get("recommended", []))
            c = len(s.get("clicked", []))
            clicked += c
            clicks_turns += 1 if c else 0
            reward += s.get("reward", 0.0)
            if s.get("strategy"):
                strategies[s["strategy"]] = strategies.get(s["strategy"], 0) + 1
            if s.get("user_action") == "exit":
                exits += 1
    total_turns = max(turns, 1)
    extra = {f"strategy:{k}": v / total_turns for k, v in strategies.items()}
    return SimulationReport(
        n_episodes=len(trajs),
        avg_turns=turns / n,
        click_rate=clicks_turns / total_turns,
        ctr=clicked / max(shown, 1),
        exit_rate=exits / n,
        avg_reward=reward / total_turns,
        coverage=len(seen) / n_items if n_items else float(len(seen)),
        extra=extra,
    )


def evaluate_offline(recommender, users, truth: Mapping[str, Sequence[str]], k: int = 10, n_items: int | None = None) -> RankingReport:
    """Leave-out evaluation: recommend once per user, compare against held-out positives."""
    recs = []
    for u in users:
        recommender.reset()
        recs.append(recommender.recommend(u))
    return ranking_metrics(recs, truth, k=k, n_items=n_items)
