from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from ..core.types import Action, ActionType, Observation
from ..llm.base import LLM
from ..memory.base import Memory, MemoryEntry, NullMemory
from ..planning.base import PlanContext, Planner
from ..planning.builtin import ChainPlanner
from ..profile.base import NullProfile, Profile
from ..reflection.base import NullReflector, Reflector
from ..tools.base import Tool, ToolContext, ToolSet


class Agent:
    """Composable agent.  Every component is optional.

    Parameters
    ----------
    name:       role label used in traces and multi-agent messages
    llm:        shared language model (may be None for fully rule-based agents)
    profile:    persona renderer (default: none)
    memory:     memory store (default: none)
    planner:    decision procedure (default: a deterministic tool chain)
    tools:      callable tools (default: none)
    reflector:  post-hoc reflection (default: none)
    task:       task description injected into every prompt
    catalog:    optional catalog exposed to planners/tools via ``scratch``
    memory_k:   how many memory entries to render per step
    """

    def __init__(
        self,
        name: str = "agent",
        llm: LLM | None = None,
        profile: Profile | None = None,
        memory: Memory | None = None,
        planner: Planner | None = None,
        tools: Iterable[Tool] | ToolSet | None = None,
        reflector: Reflector | None = None,
        task: str = "",
        catalog: Any = None,
        memory_k: int = 5,
    ) -> None:
        self.name = name
        self.llm = llm
        self.profile = profile if profile is not None else NullProfile()
        self.memory = memory if memory is not None else NullMemory()
        self.planner = planner if planner is not None else ChainPlanner()
        self.tools = tools if isinstance(tools, ToolSet) else ToolSet(tools or ())
        self.reflector = reflector if reflector is not None else NullReflector()
        self.task = task
        self.catalog = catalog
        self.memory_k = memory_k
        self.last_trace: list[str] = []
        self._last: tuple[Observation, Action] | None = None

    # ---------------------------------------------------------------- loop
    def act(self, obs: Observation) -> Action:
        persona = self.profile.render(obs)
        query = obs.last_message.content if obs.last_message else (obs.user.id if obs.user else "")
        memory_txt = self.memory.render(query=query, k=self.memory_k) if self.memory_k else ""
        tool_ctx = ToolContext(obs=obs, scratch={"catalog": self.catalog})
        ctx = PlanContext(
            obs=obs,
            persona=persona,
            memory=memory_txt,
            task=self.task,
            tools=self.tools,
            tool_ctx=tool_ctx,
        )
        action = self.planner.plan(ctx)
        self.last_trace = ctx.trace
        self._last = (obs, action)
        self.memory.add(MemoryEntry(content=self._describe(action), kind="event", importance=0.5))
        return action

    def feedback(self, text: str, importance: float = 0.8) -> str | None:
        """Deliver feedback for the last action; runs reflection and stores insights."""
        if self._last is None:
            return None
        obs, action = self._last
        self.memory.add(MemoryEntry(content=f"feedback on {action.type.value}: {text}", kind="event", importance=0.6))
        insight = self.reflector.reflect(obs, action, feedback=text, trace=self.last_trace)
        if insight:
            self.memory.add(MemoryEntry(content=insight, kind="insight", importance=importance))
        return insight

    def reset(self) -> None:
        self.memory.clear()
        self.last_trace = []
        self._last = None

    # ------------------------------------------------------------- helpers
    @staticmethod
    def _describe(action: Action) -> str:
        if action.type is ActionType.RECOMMEND:
            return "recommended " + ", ".join(action.items[:10])
        return f"{action.type.value}: {str(action.payload)[:200]}"

    def describe(self) -> str:
        return (
            f"{self.name}: profile={type(self.profile).__name__}, memory={type(self.memory).__name__}, "
            f"planner={type(self.planner).__name__}, tools=[{', '.join(self.tools.names())}], "
            f"reflector={type(self.reflector).__name__}"
        )
