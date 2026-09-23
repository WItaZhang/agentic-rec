# agentic-rec

**A survey of agentic recommender systems, and the composable framework it implies.**

[中文说明](README.zh-CN.md) · [中文学习路线](docs/zh/00-学习路线.md) · [Survey](docs/survey.md) · [Paper × component matrix](docs/component-matrix.md) · [Design notes](docs/design.md)

**Next research project:** [Adaptive Evidence Acquisition for Agentic Recommendation](docs/adaptive-evidence/README.md) — a detailed plan for temporal real-data evaluation, evidence-routing policies, quality–cost experiments, implementation milestones, and resume claims supported by measured results. The design is in Chinese; its methods and results are explicitly marked as planned. It also explains how the existing [MovieLens experiment PR](https://github.com/WItaZhang/agentic-rec/pull/1) fits into the roadmap.

Between 2023 and 2026, several dozen papers put an LLM *agent* at the centre of a recommender: as the recommender itself (RecMind, InteRecAgent, MACRec, BiLLP), as a simulated user (RecAgent, Agent4Rec, SimUSER, RecoWorld), as an item (AgentCF), or as an assistant on the user's side (RAH, iAgent). Read side by side, they share nine components and differ mainly in which ones they attach and how they are optimised.

This repository contains:

- **`docs/`** – a survey of the field, a paper-by-component matrix over 21 systems, and the design rationale. `docs/zh/` is a Chinese learning path that builds the same material up from recommender-system basics for readers new to the area.
- **`agentic_rec/`** – a zero-dependency Python package where every component (profile, memory, planner, tools, reflector, coordination, environment) is an optional, registry-addressable module.
- **`configs/`** – eleven published architectures written as configurations over those modules.
- **`examples/`, `tests/`** – runnable examples and a test suite that exercise everything offline with a deterministic mock LLM.

## The component model

```
Observation ──► profile.render ─┐
                memory.render ──┼─► PlanContext ─► planner.plan(tools) ─► Action
                task ───────────┘                        │
                                                          ▼
                    feedback ─► reflector.reflect ─► memory.add(insight)
```

| Component | Registry kind | Shipped variants | Papers it comes from |
|---|---|---|---|
| Profile | `profile` | `none` `static` `history` `traits` | InteRecAgent, Agent4Rec, SimUSER |
| Memory | `memory` | `none` `buffer` `window` `vector` `hierarchical` | RecMind, RecAgent, Generative Agents |
| Planner | `planner` | `chain` `direct` `react` `plan_execute` `hierarchical` | Chat-REC, ReAct, RecMind, BiLLP |
| Tools | `tool` | `history` `item_info` `search` `filter` `retrieve` `rank` `popular` | InteRecAgent, ToolRec, AgenticRec |
| Reflector | `reflector` | `none` `self_critique` `feedback` | Reflexion, MACRS, BiLLP |
| User policy | `user_policy` | `llm` `preference` | Agent4Rec, SUBER |
| Coordination | – | `ManagerOrchestrator` `PipelineOrchestrator` `VoteOrchestrator` | MACRec, iAgent, MACRS |
| Environment | – | multi-turn simulation with text feedback and scalar reward | RecoWorld, Agent4Rec |

A multi-agent system is a single agent whose tools are other agents (`AgentTool`). A classic ItemKNN baseline is an agent with no LLM, no memory and a `chain` planner. Both live in the same configuration space.

## Quick start

```bash
pip install -e ".[dev]"          # no runtime dependencies; dev adds pytest + ruff
agentic-rec list                 # registered components
agentic-rec run configs/interecagent.toml
agentic-rec compare configs/*.toml --users 30
pytest
```

Build an agent by hand:

```python
from agentic_rec import MockLLM, RecommenderAgent, make_synthetic
from agentic_rec.memory import WindowMemory
from agentic_rec.planning import ReActPlanner
from agentic_rec.profile import HistoryProfile
from agentic_rec.reflection import SelfCritiqueReflector
from agentic_rec.tools import HistoryTool, RankTool, RetrieveTool

data = make_synthetic()
llm = MockLLM()  # or OpenAICompatibleLLM(model="gpt-4o-mini"), AnthropicLLM()

agent = RecommenderAgent(
    llm=llm,
    profile=HistoryProfile(data.catalog),
    memory=WindowMemory(size=20),
    planner=ReActPlanner(llm, max_steps=6),
    tools=[HistoryTool(data.catalog), RetrieveTool(data.catalog), RankTool(data.catalog)],
    reflector=SelfCritiqueReflector(llm),
    catalog=data.catalog,
)
rec = agent.recommend(data.users[0])
agent.feedback("skip: none of these fit")   # reflection -> memory
```

Or from a config, which is how the paper reproductions are expressed:

```toml
# configs/interecagent.toml
[recommender]
profile   = "history"
memory    = { type = "window", size = 20 }
planner   = { type = "react", max_steps = 6 }
tools     = ["history", "filter", "retrieve", "rank"]
reflector = "self_critique"

[user]
profile = "traits"
policy  = "preference"

[environment]
max_turns = 5
k = 10
```

```python
from agentic_rec import MockLLM, build_system, load_config, make_synthetic, simulation_metrics

system = build_system(load_config("configs/interecagent.toml"), MockLLM(), make_synthetic())
trajectories = system.env.run(system.recommender, system.users)
print(simulation_metrics(trajectories))
```

Delete a line from the config and that component is gone; `examples/03_ablation.py` turns this into a component ablation loop.

## Paper reproductions (structural)

| Config | Paper | What it exercises |
|---|---|---|
| `chatrec.toml` | Chat-REC (2023) | direct prompting over prefetched candidates |
| `recmind.toml` | RecMind (2023) | plan-then-execute, vector memory, search tool |
| `interecagent.toml` | InteRecAgent (2023) | ReAct over filter / retrieve / rank tools, candidate bus, reflection |
| `recagent.toml` | RecAgent (2023) | LLM user personas with hierarchical memory |
| `agent4rec.toml` | Agent4Rec (2024) | taste / activity / conformity personas, exit actions |
| `macrec.toml` | MACRec (2024) | manager delegating to analyst agents exposed as tools |
| `macrs.toml` | MACRS (2024) | several proposers, vote, feedback-aware reflection |
| `billp.toml` | BiLLP (2024) | macro strategy + micro ReAct, long-horizon episodes |
| `iagent.toml` | iAgent (2025) | platform recommender -> user-side re-ranking agent |
| `recoworld.toml` | RecoWorld (2025) | retention-driven users, instructional feedback |
| `baseline_itemknn.toml` | – | the same tools with no LLM anywhere |

These are *structural* reproductions: the tools are item-kNN and popularity over a synthetic catalog with known latent preferences, and `MockLLM` is a deterministic policy over the framework's prompt format. They show that the architectures are points in one configuration space and give a starting point for a numerical reproduction with a real model and dataset.

## Extending

Subclass, register, reference by name:

```python
from agentic_rec import registry
from agentic_rec.tools import Tool, ToolContext, ToolResult

@registry.register("tool", "recent_year")
class RecentYearTool(Tool):
    name, description = "recent_year", "Keep only candidates released after a year."
    def __init__(self, catalog, k=20, year=2015): ...
    def run(self, ctx: ToolContext, year=None, **_) -> ToolResult: ...
```

```toml
tools = ["retrieve", { type = "recent_year", year = 2010 }, "rank"]
```

Shared objects (`llm`, `catalog`, `k`) are injected into any constructor that declares them. See `examples/04_custom_component.py`.

## Layout

```
agentic-rec/
├── docs/               survey.md · component-matrix.md · design.md · references.bib · zh/ (中文学习路线)
├── agentic_rec/
│   ├── core/           types, registry, config loader, prompt helpers
│   ├── llm/            LLM interface; mock, OpenAI-compatible and Anthropic backends (stdlib only)
│   ├── profile/ memory/ planning/ tools/ reflection/
│   ├── agents/         Agent skeleton, RecommenderAgent, UserAgent (+ policies), ItemAgent
│   ├── orchestration/  agents-as-tools, manager / pipeline / vote
│   ├── environment/    multi-turn simulation, rewards
│   ├── evaluation/     ranking + simulation metrics
│   ├── data/           Catalog, synthetic dataset
│   ├── recipes/        config -> System builder
│   └── cli.py
├── configs/            eleven architectures as TOML
├── examples/           quickstart, config-driven run, ablation, custom component
└── tests/
```

## Status and limitations

- Reference implementation, not a benchmark result. Numbers printed by `compare` come from a synthetic dataset and a mock LLM and should not be read as paper comparisons.
- No training loops. The environment exposes trajectories and rewards; RL or supervised tuning belongs to the model runtime.
- Retrieval tools are item-kNN and keyword search; drop in a real retriever by subclassing `Tool`.

## License

MIT.
