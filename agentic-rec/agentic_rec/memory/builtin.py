from __future__ import annotations

import math
import re
from collections import Counter
from typing import Any

from ..core.registry import registry
from .base import Memory, MemoryEntry

_TOKEN = re.compile(r"[a-z0-9]+")


def _tokens(text: str) -> Counter[str]:
    return Counter(_TOKEN.findall(text.lower()))


def _cosine(a: Counter[str], b: Counter[str]) -> float:
    if not a or not b:
        return 0.0
    dot = sum(a[t] * b[t] for t in a if t in b)
    na = math.sqrt(sum(v * v for v in a.values()))
    nb = math.sqrt(sum(v * v for v in b.values()))
    return dot / (na * nb) if na and nb else 0.0


@registry.register("memory", "buffer")
class BufferMemory(Memory):
    """Append-only list; ``retrieve`` returns the most recent ``k``."""

    def __init__(self) -> None:
        self._items: list[MemoryEntry] = []
        self._clock = 0

    def add(self, entry: MemoryEntry | str, **kw: Any) -> None:
        e = self._coerce(entry, **kw)
        self._clock += 1
        e.timestamp = e.timestamp or self._clock
        self._items.append(e)

    def retrieve(self, query: str = "", k: int = 5) -> list[MemoryEntry]:
        return self._items[-k:] if k else []

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        return len(self._items)


@registry.register("memory", "window")
class WindowMemory(BufferMemory):
    """Fixed-size sliding window (drops oldest entries)."""

    def __init__(self, size: int = 20) -> None:
        super().__init__()
        self.size = size

    def add(self, entry: MemoryEntry | str, **kw: Any) -> None:
        super().add(entry, **kw)
        if len(self._items) > self.size:
            del self._items[: len(self._items) - self.size]


@registry.register("memory", "vector")
class VectorMemory(BufferMemory):
    """Relevance-ranked retrieval using bag-of-words cosine similarity.

    Score = ``alpha * relevance + beta * recency + gamma * importance``, the
    retrieval rule popularised by Generative Agents and adopted by RecAgent
    and Agent4Rec.  A real embedding model can be dropped in via ``embed``.
    """

    def __init__(self, alpha: float = 1.0, beta: float = 0.5, gamma: float = 0.5, embed=None) -> None:
        super().__init__()
        self.alpha, self.beta, self.gamma = alpha, beta, gamma
        self._embed = embed

    def _vec(self, text: str) -> Any:
        return self._embed(text) if self._embed else _tokens(text)

    def _sim(self, a: Any, b: Any) -> float:
        if self._embed:
            dot = sum(x * y for x, y in zip(a, b, strict=True))
            na = math.sqrt(sum(x * x for x in a))
            nb = math.sqrt(sum(x * x for x in b))
            return dot / (na * nb) if na and nb else 0.0
        return _cosine(a, b)

    def retrieve(self, query: str = "", k: int = 5) -> list[MemoryEntry]:
        if not self._items or not k:
            return []
        if not query:
            return self._items[-k:]
        q = self._vec(query)
        now = self._clock or 1
        scored = []
        for e in self._items:
            rel = self._sim(q, self._vec(e.content))
            rec = e.timestamp / now
            scored.append((self.alpha * rel + self.beta * rec + self.gamma * e.importance, e))
        scored.sort(key=lambda t: t[0], reverse=True)
        return [e for _, e in scored[:k]]


@registry.register("memory", "hierarchical")
class HierarchicalMemory(Memory):
    """Sensory -> short-term -> long-term memory (RecAgent / Generative Agents).

    * Raw observations enter *sensory* memory; only those above
      ``sensory_threshold`` importance are promoted to *short-term*.
    * Short-term memory is a window.  When it overflows, or when
      ``reflect`` is called, its content is compressed into an *insight*
      that lands in *long-term* memory (a :class:`VectorMemory`).
    * ``retrieve`` merges long-term relevance hits with the short-term window.

    ``summarizer`` is an optional callable ``(list[str]) -> str``; typically
    an LLM call.  Without it, the promoted entries are joined verbatim.
    """

    def __init__(
        self,
        short_size: int = 10,
        sensory_threshold: float = 0.2,
        summarizer=None,
        alpha: float = 1.0,
        beta: float = 0.5,
        gamma: float = 0.5,
    ) -> None:
        self.sensory: list[MemoryEntry] = []
        self.short = WindowMemory(size=short_size)
        self.long = VectorMemory(alpha=alpha, beta=beta, gamma=gamma)
        self.short_size = short_size
        self.threshold = sensory_threshold
        self._summarizer = summarizer
        self._promotions = 0

    def add(self, entry: MemoryEntry | str, **kw: Any) -> None:
        e = self._coerce(entry, **kw)
        self.sensory.append(e)
        if e.importance >= self.threshold:
            if len(self.short) >= self.short_size:
                self.reflect()
            self.short.add(e)
        if len(self.sensory) > self.short_size * 4:
            del self.sensory[: -self.short_size * 2]

    def reflect(self) -> MemoryEntry | None:
        """Compress the current short-term window into one long-term insight."""
        entries = self.short.retrieve("", self.short_size)
        if not entries:
            return None
        texts = [e.content for e in entries]
        summary = self._summarizer(texts) if self._summarizer else " | ".join(texts)
        insight = MemoryEntry(
            content=summary,
            kind="insight",
            importance=max(e.importance for e in entries),
        )
        self.long.add(insight)
        self.short.clear()
        self._promotions += 1
        return insight

    def retrieve(self, query: str = "", k: int = 5) -> list[MemoryEntry]:
        half = max(1, k // 2)
        lt = self.long.retrieve(query, half)
        st = self.short.retrieve(query, k - len(lt))
        return lt + st

    def clear(self) -> None:
        self.sensory.clear()
        self.short.clear()
        self.long.clear()

    def __len__(self) -> int:
        return len(self.short) + len(self.long)
