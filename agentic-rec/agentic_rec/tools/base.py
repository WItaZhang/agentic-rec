from __future__ import annotations

import json
from abc import ABC, abstractmethod
from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Any

from ..core.types import Item, Observation


@dataclass
class ToolContext:
    """Mutable state shared by tools within one agent step (the *candidate bus*)."""

    obs: Observation
    candidates: list[str] = field(default_factory=list)
    scratch: dict[str, Any] = field(default_factory=dict)

    @property
    def user_id(self) -> str | None:
        return self.obs.user.id if self.obs.user else None

    @property
    def history(self) -> list[str]:
        return self.obs.user.item_ids() if self.obs.user else []


@dataclass
class ToolResult:
    text: str
    items: list[str] = field(default_factory=list)
    ok: bool = True

    def __str__(self) -> str:
        return self.text


class Tool(ABC):
    name: str = "tool"
    description: str = ""
    input_schema: str = "{}"

    @abstractmethod
    def run(self, ctx: ToolContext, **kwargs: Any) -> ToolResult: ...

    def __call__(self, ctx: ToolContext, **kwargs: Any) -> ToolResult:
        try:
            return self.run(ctx, **kwargs)
        except Exception as e:  # tools must never crash the agent loop
            return ToolResult(text=f"error in {self.name}: {e}", ok=False)

    def spec(self) -> str:
        return f"- {self.name}: {self.description} Input: {self.input_schema}"

    @staticmethod
    def render(items: Iterable[Item], limit: int = 20) -> str:
        rows = [it.describe() for it in items][:limit]
        return "\n".join(rows) if rows else "(no items)"


class ToolSet:
    """Ordered, name-addressable collection of tools."""

    def __init__(self, tools: Iterable[Tool] = ()) -> None:
        self._tools: dict[str, Tool] = {}
        for t in tools:
            self.add(t)

    def add(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self._tools.get(name)

    def names(self) -> list[str]:
        return list(self._tools)

    def __len__(self) -> int:
        return len(self._tools)

    def __iter__(self):
        return iter(self._tools.values())

    def render(self) -> str:
        return "\n".join(t.spec() for t in self._tools.values()) if self._tools else "(no tools)"

    def call(self, name: str, ctx: ToolContext, raw_input: str | dict[str, Any] | None = None) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(text=f"unknown tool '{name}'. available: {', '.join(self.names())}", ok=False)
        kwargs: dict[str, Any] = {}
        if isinstance(raw_input, dict):
            kwargs = raw_input
        elif raw_input:
            try:
                parsed = json.loads(raw_input)
                kwargs = parsed if isinstance(parsed, dict) else {"query": parsed}
            except json.JSONDecodeError:
                kwargs = {"query": raw_input.strip()}
        return tool(ctx, **kwargs)
