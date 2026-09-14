from __future__ import annotations

from collections import Counter

from ..core.registry import registry
from ..core.types import Observation
from .base import Profile


@registry.register("profile", "static")
class StaticProfile(Profile):
    """A fixed persona string (hand-written or produced offline)."""

    def __init__(self, text: str = "") -> None:
        self.text = text

    def render(self, obs: Observation) -> str:
        return self.text


@registry.register("profile", "history")
class HistoryProfile(Profile):
    """Summarise the user's recent history and dominant attributes.

    ``catalog`` (optional) lets the profile resolve item ids to titles and
    attributes; ``attr`` is the attribute whose distribution is reported.
    """

    def __init__(self, catalog=None, attr: str = "genre", recent: int = 10, top_attrs: int = 3) -> None:
        self.catalog = catalog
        self.attr = attr
        self.recent = recent
        self.top_attrs = top_attrs

    def render(self, obs: Observation) -> str:
        user = obs.user
        if user is None:
            return ""
        lines = [f"User id: {user.id}"]
        for k, v in user.attrs.items():
            lines.append(f"{k}: {v}")
        ids = user.item_ids()
        if ids:
            recent = ids[-self.recent :]
            if self.catalog is not None:
                recent_txt = "; ".join(self.catalog.get(i).describe() for i in recent if self.catalog.has(i))
                counts: Counter[str] = Counter()
                for i in ids:
                    if self.catalog.has(i):
                        val = self.catalog.get(i).get(self.attr)
                        for v in (val if isinstance(val, (list, tuple, set)) else [val]):
                            if v is not None:
                                counts[str(v)] += 1
                if counts:
                    top = ", ".join(f"{a} ({n})" for a, n in counts.most_common(self.top_attrs))
                    lines.append(f"Dominant {self.attr}s: {top}")
            else:
                recent_txt = ", ".join(recent)
            lines.append(f"Recent interactions: {recent_txt}")
        else:
            lines.append("Recent interactions: none (cold start)")
        return "\n".join(lines)


@registry.register("profile", "traits")
class TraitProfile(Profile):
    """Agent4Rec-style persona made of *taste*, *activity* and *conformity*.

    Values are read from ``obs.user.attrs`` when present and fall back to the
    constructor defaults, so one profile object can serve a whole user pool.
    """

    def __init__(
        self,
        taste: str = "",
        activity: str = "medium",
        conformity: str = "medium",
        diversity: str = "medium",
        extra: str = "",
    ) -> None:
        self.defaults = dict(taste=taste, activity=activity, conformity=conformity, diversity=diversity)
        self.extra = extra

    def render(self, obs: Observation) -> str:
        attrs = obs.user.attrs if obs.user else {}
        vals = {k: attrs.get(k, v) for k, v in self.defaults.items()}
        likes = attrs.get("likes")
        lines = [f"You are user {obs.user.id}." if obs.user else "You are a user."]
        if vals["taste"]:
            lines.append(f"Taste: {vals['taste']}")
        if likes:
            lines.append(f"Likes: {', '.join(map(str, likes)) if isinstance(likes, (list, tuple)) else likes}")
        lines.append(f"Activity level: {vals['activity']} (how many items you engage with per visit)")
        lines.append(f"Conformity: {vals['conformity']} (how much popularity sways you)")
        lines.append(f"Diversity seeking: {vals['diversity']}")
        if self.extra:
            lines.append(self.extra)
        return "\n".join(lines)
