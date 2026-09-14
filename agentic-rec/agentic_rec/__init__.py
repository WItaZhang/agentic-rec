"""agentic-rec: a composable reference framework for agentic recommender systems.

Quick start::

    from agentic_rec import make_synthetic, MockLLM, load_config, build_system

    data = make_synthetic()
    system = build_system(load_config("configs/interecagent.toml"), MockLLM(), data)
    trajectories = system.env.run(system.recommender, system.users)
"""

from .agents import ItemAgent, RecommenderAgent, UserAgent
from .core import (
    Action,
    ActionType,
    Interaction,
    Item,
    Message,
    Observation,
    RecList,
    Trajectory,
    User,
)
from .core.config import build, load_config
from .core.registry import registry
from .data import Catalog, make_synthetic
from .environment import Environment, EpisodeConfig
from .evaluation import evaluate_offline, ranking_metrics, simulation_metrics
from .llm import AnthropicLLM, MockLLM, OpenAICompatibleLLM, ScriptedLLM
from .recipes import System, build_recommender, build_system, build_user_agents

__version__ = "0.1.0"

__all__ = [
    "Action",
    "ActionType",
    "Interaction",
    "Item",
    "Message",
    "Observation",
    "RecList",
    "Trajectory",
    "User",
    "Catalog",
    "make_synthetic",
    "Environment",
    "EpisodeConfig",
    "RecommenderAgent",
    "UserAgent",
    "ItemAgent",
    "MockLLM",
    "ScriptedLLM",
    "OpenAICompatibleLLM",
    "AnthropicLLM",
    "registry",
    "build",
    "load_config",
    "System",
    "build_system",
    "build_recommender",
    "build_user_agents",
    "evaluate_offline",
    "ranking_metrics",
    "simulation_metrics",
]
