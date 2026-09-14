"""Profile modules: how an agent describes *who it is acting for / as*.

A profile is a function ``(observation) -> str`` producing the persona block
of a prompt.  Recommender agents use it to describe the target user; user
agents use it to describe themselves (Agent4Rec's taste / rationality /
activity traits, RecAgent's personas, SimUSER's self-consistent personas).
"""

from .base import NullProfile, Profile
from .builtin import HistoryProfile, StaticProfile, TraitProfile

__all__ = ["Profile", "NullProfile", "StaticProfile", "HistoryProfile", "TraitProfile"]
