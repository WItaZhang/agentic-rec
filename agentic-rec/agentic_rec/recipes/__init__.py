"""Build agents and simulations from declarative configs.

The config schema mirrors the component taxonomy of the survey, so a paper's
architecture is a point in this configuration space (see ``configs/``).
"""

from .build import System, build_recommender, build_system, build_user_agents

__all__ = ["System", "build_recommender", "build_system", "build_user_agents"]
