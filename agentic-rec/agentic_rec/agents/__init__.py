"""Agents: a single composition skeleton for every role.

``Agent`` wires the optional components together::

    perceive -> profile.render -> memory.render -> planner.plan(tools) -> act
                                                  \\-> reflector.reflect -> memory.add

``RecommenderAgent`` and ``UserAgent`` are thin specialisations that fix the
task and the action space; ``ItemAgent`` gives items a voice (AgentCF).
"""

from .base import Agent
from .recommender import RecommenderAgent
from .user import ItemAgent, LLMUserPolicy, PreferenceUserPolicy, UserAgent, UserPolicy

__all__ = [
    "Agent",
    "RecommenderAgent",
    "UserAgent",
    "UserPolicy",
    "LLMUserPolicy",
    "PreferenceUserPolicy",
    "ItemAgent",
]
