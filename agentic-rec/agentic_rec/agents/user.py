"""User-side agents.

``UserAgent`` follows the same skeleton as the recommender agent: a profile
(persona), a memory, and a decision procedure.  The decision procedure is a
``UserPolicy`` so that an LLM persona (Agent4Rec, RecAgent, SimUSER) and a
transparent rule-based oracle (useful for tests and for RL-style reward
shaping) are interchangeable.
"""

from __future__ import annotations

import json
import random
import re
from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Any

from ..core.prompting import render_items, section
from ..core.registry import registry
from ..core.types import Action, ActionType, Interaction, Item, Message, Observation, User
from ..llm.base import LLM
from ..memory.base import Memory, MemoryEntry, NullMemory
from ..profile.base import NullProfile, Profile

_JSON_RE = re.compile(r"\{.*\}", re.S)


class UserPolicy(ABC):
    @abstractmethod
    def decide(self, obs: Observation, persona: str, memory: str) -> Action: ...


@registry.register("user_policy", "llm")
class LLMUserPolicy(UserPolicy):
    """Persona-conditioned LLM decision returning a JSON action."""

    def __init__(self, llm: LLM | None = None, max_clicks: int = 3) -> None:
        self.llm = llm
        self.max_clicks = max_clicks

    def decide(self, obs: Observation, persona: str, memory: str) -> Action:
        assert self.llm is not None, "LLMUserPolicy needs an LLM"
        prompt = (
            section("Persona", persona)
            + section("Memory", memory)
            + section("Recommended items", render_items(obs.items))
            + "Act as this user. Respond with a JSON object: "
            '{"action": "click"|"rate"|"skip"|"exit", "items": [ids], "rating": 1-5 (optional), "comment": str}\n'
            f"Choose at most {self.max_clicks} items. Exit only if you have grown tired of the platform.\n"
        )
        out = self.llm.complete(prompt)
        return self._parse(out, obs)

    @staticmethod
    def _parse(text: str, obs: Observation) -> Action:
        m = _JSON_RE.search(text)
        valid = {it.id for it in obs.items}
        try:
            data: dict[str, Any] = json.loads(m.group(0)) if m else {}
        except json.JSONDecodeError:
            data = {}
        kind = str(data.get("action", "skip")).lower()
        items = [str(i) for i in data.get("items", []) if str(i) in valid]
        atype = {"click": ActionType.CLICK, "rate": ActionType.RATE, "exit": ActionType.EXIT}.get(kind, ActionType.SKIP)
        if atype in (ActionType.CLICK, ActionType.RATE) and not items:
            atype = ActionType.SKIP
        return Action(atype, payload=items, rationale=str(data.get("comment", "")), meta={"rating": data.get("rating")})


@registry.register("user_policy", "preference")
class PreferenceUserPolicy(UserPolicy):
    """Transparent oracle: click probability from latent attribute preferences.

    ``truth`` maps user id -> {attribute value -> weight}.  ``attr`` names the
    item attribute (e.g. ``genre``).  Conformity mixes in popularity; a
    boredom counter drives EXIT when nothing was clicked ``patience`` turns
    in a row.  Deterministic given ``seed``.
    """

    def __init__(
        self,
        truth: dict[str, dict[str, float]] | None = None,
        catalog=None,
        attr: str = "genre",
        threshold: float = 0.15,
        max_clicks: int = 3,
        patience: int = 2,
        seed: int = 0,
    ) -> None:
        self.truth = truth or {}
        self.catalog = catalog
        self.attr = attr
        self.threshold = threshold
        self.max_clicks = max_clicks
        self.patience = patience
        self.rng = random.Random(seed)
        self._misses: dict[str, int] = {}

    def _affinity(self, user_id: str, item: Item) -> float:
        prefs = self.truth.get(user_id, {})
        vals = item.get(self.attr, [])
        vals = vals if isinstance(vals, (list, tuple, set)) else [vals]
        return max((prefs.get(str(v), 0.0) for v in vals), default=0.0)

    def decide(self, obs: Observation, persona: str, memory: str) -> Action:
        uid = obs.user.id if obs.user else ""
        seen = set(obs.user.item_ids()) if obs.user else set()
        scored = []
        for it in obs.items:
            if it.id in seen:
                continue
            a = self._affinity(uid, it)
            if a >= self.threshold and self.rng.random() < min(1.0, a + 0.3):
                scored.append((a, it.id))
        scored.sort(reverse=True)
        picks = [i for _, i in scored[: self.max_clicks]]
        if picks:
            self._misses[uid] = 0
            return Action(ActionType.CLICK, payload=picks, rationale="matches my taste")
        self._misses[uid] = self._misses.get(uid, 0) + 1
        if self._misses[uid] >= self.patience:
            return Action(ActionType.EXIT, payload=[], rationale="nothing here for me; leaving")
        return Action(ActionType.SKIP, payload=[], rationale="not interested in these")


class UserAgent:
    """A simulated user: persona + memory + policy, with a dynamic history."""

    def __init__(
        self,
        user: User,
        policy: UserPolicy,
        profile: Profile | None = None,
        memory: Memory | None = None,
        memory_k: int = 5,
    ) -> None:
        self.user = user
        self.policy = policy
        self.profile = profile if profile is not None else NullProfile()
        self.memory = memory if memory is not None else NullMemory()
        self.memory_k = memory_k
        self._clock = len(user.history)

    @property
    def id(self) -> str:
        return self.user.id

    def react(self, items: Iterable[Item], messages: list[Message] | None = None) -> Action:
        items = list(items)
        obs = Observation(user=self.user, messages=messages or [], items=items)
        persona = self.profile.render(obs)
        mem = self.memory.render(query=" ".join(it.title for it in items), k=self.memory_k)
        action = self.policy.decide(obs, persona, mem)
        self._record(action, items)
        return action

    def _record(self, action: Action, items: list[Item]) -> None:
        titles = {it.id: it.title for it in items}
        if action.type in (ActionType.CLICK, ActionType.RATE):
            for iid in action.items:
                self._clock += 1
                self.user.history.append(Interaction(self.user.id, iid, action.type.value, 1.0, self._clock))
                self.memory.add(MemoryEntry(f"I engaged with {titles.get(iid, iid)}", importance=0.7))
        else:
            self.memory.add(MemoryEntry(f"I {action.type.value}ped a list: {', '.join(titles.values())[:120]}", importance=0.3))

    def describe_feedback(self, action: Action) -> str:
        if action.type in (ActionType.CLICK, ActionType.RATE):
            return f"{action.type.value} on {', '.join(action.items)}: {action.rationale}"
        return f"{action.type.value}: {action.rationale}"


class ItemAgent:
    """An item that maintains its own textual memory of who liked it (AgentCF).

    Kept minimal on purpose: the point is the interface, i.e. that items can
    be first-class agents that update a description from interactions and
    contribute it to prompts.
    """

    def __init__(self, item: Item, llm: LLM | None = None) -> None:
        self.item = item
        self.llm = llm
        self.memory = "" if not item.attrs.get("text") else str(item.attrs["text"])

    def observe(self, user_persona: str, liked: bool) -> None:
        note = f"{'Liked' if liked else 'Rejected'} by a user described as: {user_persona[:120]}"
        if self.llm is None:
            self.memory = (self.memory + " " + note).strip()[-600:]
            return
        prompt = (
            section("Current item description", self.memory or self.item.describe())
            + section("New evidence", note)
            + "Rewrite the item description in two sentences to better reflect who enjoys it.\nDescription:"
        )
        self.memory = self.llm.complete(prompt).strip()

    def describe(self) -> str:
        return f"{self.item.describe()} :: {self.memory}" if self.memory else self.item.describe()
