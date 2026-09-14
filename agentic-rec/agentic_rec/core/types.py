"""Plain data types used across the framework.

Everything here is a frozen or mutable dataclass with no behaviour beyond
convenience accessors, so that every other layer can depend on this module
without creating import cycles.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


@dataclass(frozen=True)
class Item:
    """A catalog entry.

    ``attrs`` holds arbitrary side information (genre, price, year, text ...).
    The framework never assumes a specific schema; tools that need a specific
    attribute declare it explicitly.
    """

    id: str
    title: str = ""
    attrs: dict[str, Any] = field(default_factory=dict)

    def get(self, key: str, default: Any = None) -> Any:
        return self.attrs.get(key, default)

    def describe(self) -> str:
        """Short natural-language description used in prompts."""
        extras = ", ".join(f"{k}={v}" for k, v in self.attrs.items() if k not in {"text"})
        return f"[{self.id}] {self.title}" + (f" ({extras})" if extras else "")


@dataclass
class Interaction:
    """One user-item event (click, rating, purchase, dislike ...)."""

    user_id: str
    item_id: str
    kind: str = "click"
    value: float = 1.0
    timestamp: int = 0
    context: dict[str, Any] = field(default_factory=dict)


@dataclass
class User:
    """A user record with an interaction history and free-form attributes."""

    id: str
    history: list[Interaction] = field(default_factory=list)
    attrs: dict[str, Any] = field(default_factory=dict)

    def item_ids(self, kinds: set[str] | None = None) -> list[str]:
        return [i.item_id for i in self.history if kinds is None or i.kind in kinds]


@dataclass
class Message:
    """A chat turn between roles (user / assistant / system / tool / agent name)."""

    role: str
    content: str
    meta: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:  # pragma: no cover - trivial
        return f"{self.role}: {self.content}"


class ActionType(str, Enum):
    """Action space shared by recommender agents and user agents.

    Recommender-side actions: RECOMMEND, ASK, RESPOND, TOOL.
    User-side actions:        CLICK, RATE, SKIP, EXIT, SAY.
    """

    RECOMMEND = "recommend"
    ASK = "ask"
    RESPOND = "respond"
    TOOL = "tool"
    CLICK = "click"
    RATE = "rate"
    SKIP = "skip"
    EXIT = "exit"
    SAY = "say"


@dataclass
class Action:
    """A decision emitted by an agent.

    ``payload`` depends on the type: a list of item ids for RECOMMEND/CLICK,
    a question string for ASK, a tool name + arguments for TOOL, etc.
    """

    type: ActionType
    payload: Any = None
    rationale: str = ""
    meta: dict[str, Any] = field(default_factory=dict)

    @property
    def items(self) -> list[str]:
        if isinstance(self.payload, list):
            return [str(x) for x in self.payload]
        return []


@dataclass
class Observation:
    """What an agent perceives before acting.

    ``user`` is the target user (may be None for user agents observing a
    recommendation list); ``messages`` is the dialogue so far; ``items`` are
    candidate or recommended items; ``extra`` carries anything else.
    """

    user: User | None = None
    messages: list[Message] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def last_message(self) -> Message | None:
        return self.messages[-1] if self.messages else None


@dataclass
class RecList:
    """A ranked list of item ids with optional scores and explanation."""

    user_id: str
    item_ids: list[str]
    scores: list[float] | None = None
    explanation: str = ""

    def top(self, k: int) -> list[str]:
        return self.item_ids[:k]


@dataclass
class Trajectory:
    """Log of one simulated episode (user x recommender)."""

    user_id: str
    steps: list[dict[str, Any]] = field(default_factory=list)

    def add(self, **kwargs: Any) -> None:
        self.steps.append(kwargs)

    @property
    def n_turns(self) -> int:
        return len(self.steps)
