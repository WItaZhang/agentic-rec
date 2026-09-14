from __future__ import annotations

from ..core.prompting import section
from ..core.registry import registry
from ..core.types import Action, Observation
from ..llm.base import LLM
from .base import Reflector


@registry.register("reflector", "self_critique")
class SelfCritiqueReflector(Reflector):
    """Reflexion-style verbal self-critique of the last trajectory."""

    def __init__(self, llm: LLM | None = None, max_trace_chars: int = 3000) -> None:
        self.llm = llm
        self.max_trace_chars = max_trace_chars

    def reflect(self, obs: Observation, action: Action, feedback: str = "", trace: list[str] | None = None) -> str | None:
        if self.llm is None:
            return None
        trace_txt = "\n".join(trace or [])[-self.max_trace_chars :]
        prompt = (
            section("Trajectory", trace_txt)
            + section("Action taken", f"{action.type.value}: {action.payload}")
            + (section("Feedback", feedback) if feedback else "")
            + "Critique this trajectory. Reflect on what to do differently and write one concise, "
            "reusable insight for future recommendations to this user.\nInsight:"
        )
        return self.llm.complete(prompt).strip()


@registry.register("reflector", "feedback")
class FeedbackReflector(Reflector):
    """Feedback-aware reflection (MACRS): only reflects when feedback is negative."""

    def __init__(self, llm: LLM | None = None, negative_markers: tuple[str, ...] = ("skip", "exit", "dislike", "no")) -> None:
        self.llm = llm
        self.markers = negative_markers

    def reflect(self, obs: Observation, action: Action, feedback: str = "", trace: list[str] | None = None) -> str | None:
        low = feedback.lower()
        if not feedback or not any(m in low for m in self.markers):
            return None
        if self.llm is None:
            return f"User reacted negatively ({feedback}); avoid similar suggestions."
        prompt = (
            section("Recommendation", str(action.payload))
            + section("User feedback", feedback)
            + "The user was not satisfied. Reflect on the likely cause and state one adjustment for the next turn.\nInsight:"
        )
        return self.llm.complete(prompt).strip()
