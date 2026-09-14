from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# make sure every registered component is imported
from .. import memory, planning, profile, reflection, tools  # noqa: F401
from ..agents import user as _user  # noqa: F401
from ..agents.base import Agent
from ..agents.recommender import DEFAULT_TASK, RecommenderAgent
from ..agents.user import UserAgent
from ..core.config import build
from ..data.synthetic import SyntheticDataset
from ..environment.sim import Environment, EpisodeConfig
from ..llm.base import LLM
from ..orchestration.base import ManagerOrchestrator, PipelineOrchestrator, VoteOrchestrator


@dataclass
class System:
    name: str
    recommender: Any
    users: list[UserAgent]
    env: Environment
    config: dict[str, Any] = field(default_factory=dict)


def _agent(cfg: dict[str, Any], llm: LLM | None, catalog, name: str, k: int, cls=Agent, **extra: Any) -> Agent:
    shared = {"llm": llm, "catalog": catalog, "top_k": k, "k": k}
    tool_specs = cfg.get("tools", [])
    tool_objs = build("tool", tool_specs, catalog=catalog, k=max(k, 20)) if tool_specs else []
    kwargs = dict(
        name=name,
        llm=llm,
        profile=build("profile", cfg.get("profile"), catalog=catalog),
        memory=build("memory", cfg.get("memory")),
        planner=build("planner", cfg.get("planner"), **shared),
        tools=tool_objs,
        reflector=build("reflector", cfg.get("reflector"), llm=llm),
        catalog=catalog,
        memory_k=cfg.get("memory_k", 5),
        **extra,
    )
    if "task" in cfg:
        kwargs["task"] = cfg["task"]
    return cls(**kwargs)


def build_recommender(cfg: dict[str, Any], llm: LLM | None, catalog, k: int = 10):
    """Build a single recommender agent or a multi-agent orchestrator."""
    orch = cfg.get("orchestrator")
    if not orch:
        agent = _agent(cfg, llm, catalog, cfg.get("name", "recommender"), k, cls=RecommenderAgent)
        agent.k = k
        return agent

    roles = cfg.get("roles", {})
    workers = [_agent(rc, llm, catalog, rname, k, task=rc.get("task", "")) for rname, rc in roles.items()]
    if orch == "manager":
        mcfg = dict(cfg.get("manager", {}))
        mcfg.setdefault("planner", {"type": "react", "max_steps": len(workers) + 2})
        mcfg.setdefault("task", DEFAULT_TASK + " Consult your analysts before deciding.")
        manager = _agent(mcfg, llm, catalog, "manager", k)
        result = ManagerOrchestrator(manager, workers)
    elif orch == "pipeline":
        result = PipelineOrchestrator(workers)
    elif orch == "vote":
        result = VoteOrchestrator(workers, top_k=k)
    else:
        raise ValueError(f"unknown orchestrator '{orch}'")
    result.k = k
    return result


def build_user_agents(cfg: dict[str, Any], llm: LLM | None, dataset: SyntheticDataset, n_users: int | None = None, seed: int = 0) -> list[UserAgent]:
    users = dataset.users[:n_users] if n_users else dataset.users
    policy_spec = cfg.get("policy", "preference")
    policy = build(
        "user_policy",
        policy_spec,
        llm=llm,
        truth=dataset.truth,
        catalog=dataset.catalog,
        seed=seed,
    )
    profile_spec = cfg.get("profile", "traits")
    agents = []
    for u in users:
        agents.append(
            UserAgent(
                user=u,
                policy=policy,
                profile=build("profile", profile_spec, catalog=dataset.catalog),
                memory=build("memory", cfg.get("memory")),
            )
        )
    return agents


def build_system(config: dict[str, Any], llm: LLM | None, dataset: SyntheticDataset, n_users: int | None = None, seed: int = 0) -> System:
    env_cfg = config.get("environment", {})
    k = int(env_cfg.get("k", 10))
    recommender = build_recommender(config.get("recommender", {}), llm, dataset.catalog, k=k)
    users = build_user_agents(config.get("user", {}), llm, dataset, n_users=n_users, seed=seed)
    env = Environment(
        dataset.catalog,
        EpisodeConfig(max_turns=int(env_cfg.get("max_turns", 5)), k=k, verbose=bool(env_cfg.get("verbose", False))),
    )
    return System(name=config.get("name", "unnamed"), recommender=recommender, users=users, env=env, config=config)
