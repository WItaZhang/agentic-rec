"""HTTP backends implemented with the standard library only.

Both classes speak the plain JSON REST APIs, so no vendor SDK is needed.  Keys
are read from the environment when not given explicitly.
"""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Sequence

from ..core.types import Message
from .base import ChatLLM


def _post(url: str, headers: dict[str, str], body: dict, timeout: float) -> dict:
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


class OpenAICompatibleLLM(ChatLLM):
    """Any ``/v1/chat/completions`` endpoint (OpenAI, vLLM, Ollama, DeepSeek ...)."""

    def __init__(
        self,
        model: str,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        record: bool = False,
    ) -> None:
        super().__init__(record=record)
        self.model = model
        self.base_url = (base_url or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1").rstrip("/")
        self.api_key = api_key or os.getenv("OPENAI_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _chat(self, messages: Sequence[Message], **kw: object) -> str:
        body = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "temperature": kw.get("temperature", self.temperature),
            "max_tokens": kw.get("max_tokens", self.max_tokens),
        }
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}
        out = _post(f"{self.base_url}/chat/completions", headers, body, self.timeout)
        return out["choices"][0]["message"]["content"]


class AnthropicLLM(ChatLLM):
    """Anthropic Messages API."""

    def __init__(
        self,
        model: str = "claude-sonnet-5",
        api_key: str | None = None,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        timeout: float = 60.0,
        record: bool = False,
    ) -> None:
        super().__init__(record=record)
        self.model = model
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY", "")
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout

    def _chat(self, messages: Sequence[Message], **kw: object) -> str:
        system = "\n".join(m.content for m in messages if m.role == "system")
        convo = [{"role": m.role, "content": m.content} for m in messages if m.role != "system"]
        if not convo:
            convo = [{"role": "user", "content": system or "Hello"}]
            system = ""
        body = {
            "model": self.model,
            "max_tokens": kw.get("max_tokens", self.max_tokens),
            "temperature": kw.get("temperature", self.temperature),
            "messages": convo,
        }
        if system:
            body["system"] = system
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
        }
        out = _post("https://api.anthropic.com/v1/messages", headers, body, self.timeout)
        return "".join(block.get("text", "") for block in out.get("content", []))
