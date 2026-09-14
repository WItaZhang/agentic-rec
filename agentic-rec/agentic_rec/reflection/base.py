from __future__ import annotations

from abc import ABC, abstractmethod

from ..core.registry import registry
from ..core.types import Action, Observation


class Reflector(ABC):
    @abstractmethod
    def reflect(self, obs: Observation, action: Action, feedback: str = "", trace: list[str] | None = None) -> str | None: ...


@registry.register("reflector", "none")
class NullReflector(Reflector):
    def reflect(self, obs, action, feedback="", trace=None):
        return None
