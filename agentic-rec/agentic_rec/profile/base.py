from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.registry import registry
from ..core.types import Observation


class Profile(ABC):
    @abstractmethod
    def render(self, obs: Observation) -> str: ...

    def update(self, obs: Observation, feedback: str) -> None:  # optional hook
        return None


@registry.register("profile", "none")
class NullProfile(Profile):
    def render(self, obs: Observation) -> str:
        return ""
