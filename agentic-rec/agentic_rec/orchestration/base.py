from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable, Sequence
from typing import Any

from ..agents.base import Agent
from ..core.types import Action, ActionType, Message, Observation, RecList, User
from ..planning.builtin import ReActPlanner
from ..tools.base import Tool, ToolContext, ToolResult


class AgentTool(Tool):
    """Expose an agent as a tool so a manager can delegate to it."""

    input_schema = '{"query": str}'

    def __init__(self, agent: Agent, description: str = "") -> None:
        self.agent = agent
        self.name = agent.name
        self.description = description or agent.task or f"delegate to {agent.name}"

    def run(self, ctx: ToolContext, query: str = "", **_: Any) -> ToolResult:
        msgs = list(ctx.obs.messages)
        if query:
            msgs.append(Message("manager", query))
        obs = Observation(user=ctx.obs.user, messages=msgs, items=ctx.obs.items, extra=dict(ctx.obs.extra))
        action = self.agent.act(obs)
        if action.type is ActionType.RECOMMEND and action.items:
            ctx.candidates = action.items
            cat = ctx.scratch.get("catalog")
            text = "\n".join(cat.get(i).describe() if cat and cat.has(i) else f"[{i}]" for i in action.items)
        else:
            text = str(action.payload)
        return ToolResult(text=f"{self.agent.name} says:\n{text}", items=action.items)


class Orchestrator(ABC):
    k: int = 10

    @abstractmethod
    def act(self, obs: Observation) -> Action: ...

    def recommend(self, user: User, messages: list[Message] | None = None) -> RecList:
        action = self.act(Observation(user=user, messages=messages or []))
        return RecList(user.id, action.items[: self.k], explanation=action.rationale)

    def describe(self) -> str:
        return f"{type(self).__name__}[" + "; ".join(a.describe() for a in self.agents()) + "]"

    def feedback(self, text: str) -> None:
        for a in self.agents():
            a.feedback(text)

    @abstractmethod
    def agents(self) -> Sequence[Agent]: ...

    def reset(self) -> None:
        for a in self.agents():
            a.reset()


class ManagerOrchestrator(Orchestrator):
    """MACRec-style: a manager agent plans over worker agents exposed as tools."""

    def __init__(self, manager: Agent, workers: Sequence[Agent]) -> None:
        self.manager = manager
        self.workers = list(workers)
        for w in self.workers:
            self.manager.tools.add(AgentTool(w))
        if not isinstance(self.manager.planner, ReActPlanner) and self.manager.llm is not None:
            self.manager.planner = ReActPlanner(self.manager.llm, top_k=self.manager.planner.top_k)

    def act(self, obs: Observation) -> Action:
        return self.manager.act(obs)

    def agents(self) -> Sequence[Agent]:
        return [self.manager, *self.workers]


class PipelineOrchestrator(Orchestrator):
    """Sequential hand-off: each agent sees the previous agent's output as a message."""

    def __init__(self, stages: Sequence[Agent]) -> None:
        self.stages = list(stages)

    def act(self, obs: Observation) -> Action:
        msgs = list(obs.messages)
        action = Action(ActionType.RESPOND, payload="")
        for agent in self.stages:
            action = agent.act(Observation(user=obs.user, messages=msgs, items=obs.items, extra=obs.extra))
            msgs.append(Message(agent.name, Agent._describe(action)))
            if action.type is ActionType.RECOMMEND and action.items:
                obs.extra["candidates"] = action.items
        return action

    def agents(self) -> Sequence[Agent]:
        return self.stages


class VoteOrchestrator(Orchestrator):
    """MACRS-style: several agents propose, a selector picks (or merges) one.

    ``selector`` receives the list of proposals and returns the winning index;
    the default merges proposals by Borda count, which favours items that
    several agents rank highly.
    """

    def __init__(self, proposers: Sequence[Agent], selector: Callable[[list[Action]], int] | None = None, top_k: int = 10) -> None:
        self.proposers = list(proposers)
        self.selector = selector
        self.top_k = top_k

    def act(self, obs: Observation) -> Action:
        proposals = [a.act(Observation(user=obs.user, messages=list(obs.messages), items=obs.items, extra=dict(obs.extra))) for a in self.proposers]
        if self.selector is not None:
            return proposals[self.selector(proposals)]
        scores: dict[str, float] = {}
        for p in proposals:
            for rank, iid in enumerate(p.items):
                scores[iid] = scores.get(iid, 0.0) + 1.0 / (rank + 1)
        if not scores:
            return proposals[0]
        merged = sorted(scores, key=lambda i: -scores[i])[: self.top_k]
        return Action(ActionType.RECOMMEND, payload=merged, rationale="borda merge of " + ", ".join(a.name for a in self.proposers))

    def agents(self) -> Sequence[Agent]:
        return self.proposers
