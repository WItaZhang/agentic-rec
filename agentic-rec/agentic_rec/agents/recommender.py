from __future__ import annotations

from ..core.types import Action, ActionType, Message, Observation, RecList, User
from .base import Agent

DEFAULT_TASK = (
    "You are a recommender agent. Select items the target user is most likely to enjoy next, "
    "avoiding items they have already interacted with. Return a ranked list of item ids."
)


class RecommenderAgent(Agent):
    def __init__(self, name: str = "recommender", task: str = DEFAULT_TASK, k: int = 10, **kw) -> None:
        super().__init__(name=name, task=task, **kw)
        self.k = k

    def recommend(self, user: User, messages: list[Message] | None = None) -> RecList:
        obs = Observation(user=user, messages=messages or [])
        action = self.act(obs)
        ids = action.items[: self.k]
        if action.type is not ActionType.RECOMMEND and not ids:
            # planner produced a question or free text; surface it as an empty list
            return RecList(user.id, [], explanation=str(action.payload))
        return RecList(user.id, ids, explanation=action.rationale)

    def respond(self, user: User, messages: list[Message]) -> Action:
        """Dialogue entry point: may recommend, ask or respond."""
        return self.act(Observation(user=user, messages=messages))
