from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Any, Protocol

from ..agents.user import UserAgent
from ..core.types import Action, ActionType, Message, Observation, Trajectory
from ..data.catalog import Catalog


class Recommender(Protocol):
    def act(self, obs: Observation) -> Action: ...
    def feedback(self, text: str) -> Any: ...
    def reset(self) -> None: ...


@dataclass
class EpisodeConfig:
    max_turns: int = 5
    k: int = 10
    reset_between_users: bool = True
    verbose: bool = False


class Environment:
    """Repeated recommender/user exchanges (RecoWorld, Agent4Rec, SUBER style).

    Each turn: the recommender observes the user record and dialogue, emits an
    action; if it recommends, the user agent reacts; the reaction is turned into
    natural-language feedback for the recommender (closing the reflection loop)
    and into a numeric reward (for RL-style optimisation).  Episodes end on
    EXIT or after ``max_turns``.
    """

    def __init__(self, catalog: Catalog, config: EpisodeConfig | None = None) -> None:
        self.catalog = catalog
        self.config = config or EpisodeConfig()

    def run_episode(self, recommender: Recommender, user: UserAgent) -> Trajectory:
        cfg = self.config
        if cfg.reset_between_users:
            recommender.reset()
        traj = Trajectory(user_id=user.id)
        messages: list[Message] = []
        for turn in range(cfg.max_turns):
            obs = Observation(user=user.user, messages=list(messages))
            rec_action = recommender.act(obs)
            if rec_action.type is ActionType.ASK or (rec_action.type is ActionType.RESPOND and not rec_action.items):
                messages.append(Message("assistant", str(rec_action.payload)))
                user_action = user.react([], messages)
                messages.append(Message("user", user_action.rationale or user_action.type.value))
                reward = 0.0
            else:
                ids = rec_action.items[: cfg.k]
                items = [self.catalog.get(i) for i in ids if self.catalog.has(i)]
                messages.append(Message("assistant", "Recommended: " + ", ".join(i.title for i in items)))
                user_action = user.react(items, messages)
                messages.append(Message("user", user.describe_feedback(user_action)))
                reward = self.reward(user_action, len(items))
            recommender.feedback(user.describe_feedback(user_action))
            traj.add(
                turn=turn,
                recommended=rec_action.items[: cfg.k],
                rec_type=rec_action.type.value,
                user_action=user_action.type.value,
                clicked=user_action.items,
                reward=reward,
                strategy=rec_action.meta.get("strategy"),
            )
            if cfg.verbose:
                print(f"[{user.id} t={turn}] rec={rec_action.items[: cfg.k]} -> {user_action.type.value} {user_action.items}")
            if user_action.type is ActionType.EXIT:
                break
        return traj

    def run(self, recommender: Recommender, users: Iterable[UserAgent]) -> list[Trajectory]:
        return [self.run_episode(recommender, u) for u in users]

    @staticmethod
    def reward(action: Action, n_shown: int) -> float:
        if action.type in (ActionType.CLICK, ActionType.RATE):
            return len(action.items) / max(1, n_shown) + 0.5
        if action.type is ActionType.EXIT:
            return -1.0
        return -0.1
