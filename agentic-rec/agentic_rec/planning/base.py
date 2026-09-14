from __future__ import annotations

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from ..core.prompting import section
from ..core.types import Action, ActionType, Observation
from ..llm.base import LLM
from ..tools.base import ToolContext, ToolSet

_FINAL_RE = re.compile(r"Final Answer:\s*(.*)", re.S)
_ACTION_RE = re.compile(r"Action:\s*([\w\-]+)\s*(?:\nAction Input:\s*(.*?))?(?:\n|$)", re.S)
_ID_RE = re.compile(r"[A-Za-z0-9_\-:.]+")


@dataclass
class PlanContext:
    """Everything a planner may read while deciding."""

    obs: Observation
    persona: str = ""
    memory: str = ""
    task: str = "Recommend the best items for the user."
    tools: ToolSet = field(default_factory=ToolSet)
    tool_ctx: ToolContext | None = None
    trace: list[str] = field(default_factory=list)  # thought/action/observation log
    demos: str = ""  # dynamic demonstrations (InteRecAgent)

    def __post_init__(self) -> None:
        if self.tool_ctx is None:
            self.tool_ctx = ToolContext(obs=self.obs)

    def prompt_head(self) -> str:
        parts = []
        if self.persona:
            parts.append(section("Persona / target user", self.persona))
        if self.memory:
            parts.append(section("Memory", self.memory))
        if self.demos:
            parts.append(section("Demonstrations", self.demos))
        parts.append(section("Task", self.task))
        return "\n".join(parts)


class Planner(ABC):
    def __init__(self, llm: LLM | None = None, top_k: int = 10) -> None:
        self.llm = llm
        self.top_k = top_k

    @abstractmethod
    def plan(self, ctx: PlanContext) -> Action: ...

    # ------------------------------------------------------------- helpers
    def parse_final(self, text: str, ctx: PlanContext) -> Action:
        """Turn a free-form final answer into a RECOMMEND action."""
        m = _FINAL_RE.search(text)
        body = m.group(1) if m else text
        ids = [t for t in _ID_RE.findall(body) if ctx.tool_ctx and self._known(t, ctx)]
        seen = list(dict.fromkeys(ids))
        if not seen and ctx.tool_ctx and ctx.tool_ctx.candidates:
            seen = list(ctx.tool_ctx.candidates)
        if not seen:
            return Action(ActionType.RESPOND, payload=body.strip(), rationale=text)
        return Action(ActionType.RECOMMEND, payload=seen[: self.top_k], rationale=text)

    @staticmethod
    def _known(token: str, ctx: PlanContext) -> bool:
        tc = ctx.tool_ctx
        if tc is None:
            return False
        if token in tc.candidates:
            return True
        cat = tc.scratch.get("catalog")
        return bool(cat is not None and cat.has(token))

    @staticmethod
    def parse_action(text: str) -> tuple[str, str] | None:
        m = _ACTION_RE.search(text)
        if not m:
            return None
        return m.group(1).strip(), (m.group(2) or "").strip()
