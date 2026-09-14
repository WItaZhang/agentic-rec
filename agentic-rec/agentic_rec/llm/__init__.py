"""LLM backends.

Every backend implements :class:`LLM`.  The framework only ever calls
``complete`` (single prompt) or ``chat`` (message list); backends that support
one can derive the other.  ``MockLLM`` keeps the whole framework runnable and
testable with no network access.
"""

from .base import LLM, ChatLLM
from .http import AnthropicLLM, OpenAICompatibleLLM
from .mock import MockLLM, ScriptedLLM

__all__ = [
    "LLM",
    "ChatLLM",
    "MockLLM",
    "ScriptedLLM",
    "OpenAICompatibleLLM",
    "AnthropicLLM",
]
