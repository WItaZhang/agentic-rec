from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass, field

from ..core.types import Message


@dataclass
class LLMStats:
    calls: int = 0
    prompt_chars: int = 0
    completion_chars: int = 0
    history: list[tuple[str, str]] = field(default_factory=list)


class LLM(ABC):
    """Abstract text-completion backend."""

    def __init__(self, record: bool = False) -> None:
        self.stats = LLMStats()
        self._record = record

    @abstractmethod
    def _complete(self, prompt: str, **kw: object) -> str: ...

    def complete(self, prompt: str, **kw: object) -> str:
        out = self._complete(prompt, **kw)
        self.stats.calls += 1
        self.stats.prompt_chars += len(prompt)
        self.stats.completion_chars += len(out)
        if self._record:
            self.stats.history.append((prompt, out))
        return out

    def chat(self, messages: Sequence[Message], **kw: object) -> str:
        prompt = "\n".join(f"{m.role}: {m.content}" for m in messages) + "\nassistant:"
        return self.complete(prompt, **kw)


class ChatLLM(LLM):
    """Base for backends whose native interface is a message list."""

    @abstractmethod
    def _chat(self, messages: Sequence[Message], **kw: object) -> str: ...

    def _complete(self, prompt: str, **kw: object) -> str:
        return self._chat([Message("user", prompt)], **kw)

    def chat(self, messages: Sequence[Message], **kw: object) -> str:
        out = self._chat(messages, **kw)
        self.stats.calls += 1
        self.stats.prompt_chars += sum(len(m.content) for m in messages)
        self.stats.completion_chars += len(out)
        if self._record:
            self.stats.history.append(("\n".join(map(str, messages)), out))
        return out
