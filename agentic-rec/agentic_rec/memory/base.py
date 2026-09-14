from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from ..core.registry import registry


@dataclass
class MemoryEntry:
    content: str
    kind: str = "event"  # event | insight | dialogue | tool
    importance: float = 1.0
    timestamp: int = 0
    meta: dict[str, Any] = field(default_factory=dict)

    def __str__(self) -> str:
        return f"({self.kind}) {self.content}"


class Memory(ABC):
    @abstractmethod
    def add(self, entry: MemoryEntry | str, **kw: Any) -> None: ...

    @abstractmethod
    def retrieve(self, query: str = "", k: int = 5) -> list[MemoryEntry]: ...

    @abstractmethod
    def clear(self) -> None: ...

    def render(self, query: str = "", k: int = 5) -> str:
        entries = self.retrieve(query, k)
        return "\n".join(f"- {e}" for e in entries) if entries else "(empty)"

    def __len__(self) -> int:  # pragma: no cover - optional
        return len(self.retrieve("", 10**9))

    @staticmethod
    def _coerce(entry: MemoryEntry | str, **kw: Any) -> MemoryEntry:
        return entry if isinstance(entry, MemoryEntry) else MemoryEntry(content=entry, **kw)


@registry.register("memory", "none")
class NullMemory(Memory):
    def add(self, entry: MemoryEntry | str, **kw: Any) -> None:
        return None

    def retrieve(self, query: str = "", k: int = 5) -> list[MemoryEntry]:
        return []

    def clear(self) -> None:
        return None
