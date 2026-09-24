# agentic-rec

**Agentic 推荐系统综述，以及由此归纳出的可组合框架。**

[English](README.md) · **[中文学习路线（从零开始）](docs/zh/00-学习路线.md)** · [英文综述](docs/survey.md) · [论文 × 组件矩阵](docs/component-matrix.md) · [设计说明](docs/design.md)

**进行中的研究：[自适应证据检索的 Agentic Recommendation](docs/adaptive-evidence/README.md)**。
MovieLens 基线已复现，Amazon 时间回放、ItemKNN 与因果序列模型已有真实结果；
同步和批量 LLM 调用已通过协议验证，正式证据对照仍在运行。
[进度记录](docs/adaptive-evidence/PROGRESS.md) 区分已实现、已验证与待完成能力，
[复现说明](docs/adaptive-evidence/REPRODUCE.md) 给出数据、配置、费用与恢复入口。
最终 Amazon 测试和学习路由的收益尚未报告。下面的 TOML 框架示例使用合成数据；
真实研究结果来自独立的 `src/`、YAML 配置和原始运行记录。

2023 到 2026 年间，几十篇工作把 LLM *agent* 放到推荐系统的中心：作为推荐器本身（RecMind、InteRecAgent、MACRec、BiLLP），作为模拟用户（RecAgent、Agent4Rec、SimUSER、RecoWorld），作为物品（AgentCF），或作为站在用户一侧的助理（RAH、iAgent）。把它们并排读，会发现共享九个组件，差异主要在于挂载了哪些组件、以及如何优化。

仓库包含：

- **`docs/zh/`** —— 面向没有推荐系统背景的读者的中文学习路线：推荐系统基础 → LLM 与 Agent 基础 → 什么是 Agentic 推荐 → 逐篇代表性工作 → 九个共享组件 → 论文组件矩阵 → 框架设计 → 代码导读 → 开放问题 → 术语表。

- **`docs/`** —— 领域综述、覆盖 21 个系统的论文 × 组件矩阵、框架设计说明。
- **`agentic_rec/`** —— 零依赖的 Python 包，每个组件（画像、记忆、规划器、工具、反思、协作、环境）都是可选的、可通过注册表按名字引用的模块。
- **`configs/`** —— 用这些模块写成的 11 个已发表架构。
- **`examples/`、`tests/`** —— 用确定性的 mock LLM 离线跑通全部流程的示例与测试。

## 组件模型

```
Observation ──► profile.render ─┐
                memory.render ──┼─► PlanContext ─► planner.plan(tools) ─► Action
                task ───────────┘                        │
                                                          ▼
                    feedback ─► reflector.reflect ─► memory.add(insight)
```

| 组件 | 注册类别 | 内置实现 | 来源论文 |
|---|---|---|---|
| 画像 Profile | `profile` | `none` `static` `history` `traits` | InteRecAgent、Agent4Rec、SimUSER |
| 记忆 Memory | `memory` | `none` `buffer` `window` `vector` `hierarchical` | RecMind、RecAgent、Generative Agents |
| 规划 Planner | `planner` | `chain` `direct` `react` `plan_execute` `hierarchical` | Chat-REC、ReAct、RecMind、BiLLP |
| 工具 Tools | `tool` | `history` `item_info` `search` `filter` `retrieve` `rank` `popular` | InteRecAgent、ToolRec、AgenticRec |
| 反思 Reflector | `reflector` | `none` `self_critique` `feedback` | Reflexion、MACRS、BiLLP |
| 用户策略 | `user_policy` | `llm` `preference` | Agent4Rec、SUBER |
| 协作 | – | `ManagerOrchestrator` `PipelineOrchestrator` `VoteOrchestrator` | MACRec、iAgent、MACRS |
| 环境 | – | 多轮模拟，同时产出文本反馈与标量奖励 | RecoWorld、Agent4Rec |

多智能体系统就是"工具是其他 agent"的单智能体（`AgentTool`）；经典 ItemKNN 基线就是"没有 LLM、没有记忆、规划器为 `chain`"的 agent。两者处在同一个配置空间里。

## 快速开始

```bash
uv sync --locked --extra yaml --extra experiments --extra api
uv run agentic-rec list
uv run agentic-rec run configs/interecagent.toml
uv run agentic-rec compare configs/*.toml --users 30
uv run --locked --extra yaml --extra experiments --extra api python -m pytest
```

配置驱动：

```toml
[recommender]
profile   = "history"
memory    = { type = "window", size = 20 }
planner   = { type = "react", max_steps = 6 }
tools     = ["history", "filter", "retrieve", "rank"]
reflector = "self_critique"

[user]
policy = "preference"

[environment]
max_turns = 5
k = 10
```

```python
from agentic_rec import MockLLM, build_system, load_config, make_synthetic, simulation_metrics

system = build_system(load_config("configs/interecagent.toml"), MockLLM(), make_synthetic())
print(simulation_metrics(system.env.run(system.recommender, system.users)))
```

从配置里删掉一行，对应组件就消失；`examples/03_ablation.py` 把这一点变成了组件消融循环。

## 论文复现（结构层面）

`configs/` 下有 Chat-REC、RecMind、InteRecAgent、RecAgent、Agent4Rec、MACRec、MACRS、BiLLP、iAgent、RecoWorld 和一个无 LLM 的 ItemKNN 基线。它们是**结构**复现而非数值复现：工具是合成目录上的 item-kNN 与流行度，`MockLLM` 是针对框架提示格式的确定性策略。目的在于证明这些架构是同一配置空间中的点，并为接入真实模型与数据集提供起点。

## 扩展

继承、注册、按名字引用：

```python
from agentic_rec import registry
from agentic_rec.tools import Tool

@registry.register("tool", "recent_year")
class RecentYearTool(Tool): ...
```

```toml
tools = ["retrieve", { type = "recent_year", year = 2010 }, "rank"]
```

共享对象（`llm`、`catalog`、`k`）会自动注入到声明了同名参数的构造函数。见 `examples/04_custom_component.py`。

## 现状与限制

- 参考实现，不是基准测试结果；`compare` 打印的数字来自合成数据和 mock LLM。
- 不包含训练循环；环境暴露轨迹与奖励，RL / 微调属于模型运行时。
- 检索工具为 item-kNN 与关键词检索，可通过继承 `Tool` 接入真实检索器。

## 许可

MIT。
