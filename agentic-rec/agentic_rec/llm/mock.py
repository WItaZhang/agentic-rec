"""Offline stand-ins for a language model.

``ScriptedLLM`` replays a fixed list of responses (useful in tests).

``MockLLM`` is a deterministic *policy* that understands the framework's own
prompt conventions well enough to drive every planner end to end:

* When the prompt lists tools and ends with an action request, it calls the
  tools in the listed order, then finishes with the ids found in the most
  recent observation.
* When asked for a plan, it returns one numbered step per tool.
* When asked to reflect, judge, or summarise, it returns a short canned text.

It is not a model of anything; it exists so that the pipeline, the
orchestration, and the evaluation code can be exercised without a key.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence

from .base import LLM

_ID_RE = re.compile(r"\[([A-Za-z0-9_\-:.]+)\]")


class ScriptedLLM(LLM):
    def __init__(self, responses: Sequence[str], loop: bool = False, record: bool = False):
        super().__init__(record=record)
        self._responses = list(responses)
        self._i = 0
        self._loop = loop

    def _complete(self, prompt: str, **kw: object) -> str:
        if self._i >= len(self._responses):
            if not self._loop:
                raise RuntimeError("ScriptedLLM ran out of responses")
            self._i = 0
        out = self._responses[self._i]
        self._i += 1
        return out


class MockLLM(LLM):
    def __init__(self, policy: Callable[[str], str] | None = None, top_k: int = 10, record: bool = False):
        super().__init__(record=record)
        self._policy = policy
        self.top_k = top_k

    # ------------------------------------------------------------------ helpers
    @staticmethod
    def _tools(prompt: str) -> list[str]:
        m = re.search(r"## Available tools\n(.*?)\n##", prompt, re.S)
        block = m.group(1) if m else ""
        return re.findall(r"^- (\w+)", block, re.M)

    @staticmethod
    def _used(prompt: str) -> list[str]:
        return re.findall(r"^Action: (\w+)", prompt, re.M)

    @staticmethod
    def _last_ids(prompt: str) -> list[str]:
        obs = prompt.rsplit("Observation:", 1)
        text = obs[1] if len(obs) == 2 else prompt
        seen: list[str] = []
        for x in _ID_RE.findall(text):
            if x not in seen:
                seen.append(x)
        return seen

    # ------------------------------------------------------------------ policy
    def _complete(self, prompt: str, **kw: object) -> str:
        if self._policy is not None:
            return self._policy(prompt)
        low = prompt.lower()

        if "respond with a json object" in low and "\"action\"" in low:
            return self._user_decision(prompt)
        if prompt.rstrip().endswith("Strategy:"):
            m = re.search(r"## Strategies\n(.*?)\n##|## Strategies\n(.*?)\nChoose", prompt, re.S)
            block = (m.group(1) or m.group(2)) if m else ""
            options = re.findall(r"^- (.+)$", block, re.M)
            self._strategy_calls = getattr(self, "_strategy_calls", 0) + 1
            return options[(self._strategy_calls - 1) % len(options)] if options else "exploit"
        if "write a numbered plan" in low:
            tools = self._tools(prompt) or ["retrieve", "rank"]
            return "\n".join(f"{i + 1}. use {t}" for i, t in enumerate(tools)) + f"\n{len(tools) + 1}. finish"
        if "## available tools" in low and "action:" in low:
            tools, used = self._tools(prompt), self._used(prompt)
            remaining = [t for t in tools if t not in used]
            if remaining:
                return f"Thought: I should consult {remaining[0]}.\nAction: {remaining[0]}\nAction Input: {{}}"
            ids = self._last_ids(prompt)[: self.top_k]
            return "Thought: I have enough evidence.\nFinal Answer: " + ", ".join(ids)
        if "reflect" in low or "critique" in low:
            return "Insight: prefer items matching the user's dominant attribute; avoid repeats."
        if "score" in low and "0 to 1" in low:
            return "0.5"
        if "rate" in low and "1 to 5" in low:
            return "4"
        ids = self._last_ids(prompt)[: self.top_k]
        if ids:
            return ", ".join(ids)
        return "OK."

    def _user_decision(self, prompt: str) -> str:
        ids = self._last_ids(prompt)
        liked = re.search(r"likes?: ([^\n]+)", prompt, re.I)
        pick = ids[:1]
        if liked and ids:
            keys = [k.strip().lower() for k in liked.group(1).split(",")]
            for iid in ids:
                m = re.search(rf"\[{re.escape(iid)}\][^\n]*", prompt)
                if m and any(k in m.group(0).lower() for k in keys):
                    pick = [iid]
                    break
        if not pick:
            return '{"action": "skip", "items": [], "comment": "nothing appealing"}'
        return '{"action": "click", "items": ["' + pick[0] + '"], "comment": "looks interesting"}'
