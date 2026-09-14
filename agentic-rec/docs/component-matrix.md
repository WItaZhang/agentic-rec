# Paper x Component Matrix

Legend: **●** central to the design · **○** present but secondary · **–** absent. "LLM-driven" marks systems whose user side is an LLM persona rather than a rule-based simulator. Optimisation: **P** prompting only, **S** supervised trajectory tuning, **R** reinforcement learning.

| System | Year | Role | Profile | Memory | Planning | Tools | Reflection | Coordination | Env / Opt | Config in repo |
|---|---|---|---|---|---|---|---|---|---|---|
| Chat-REC | 2023 | recommender | ● history | ○ dialogue | direct | ○ candidate model | – | single | P | `chatrec.toml` |
| RecMind | 2023 | recommender | ● | ● personal + world | plan-execute, ToT, self-inspiring | ● DB, search, summariser | ● self-inspiring | single | P | `recmind.toml` |
| InteRecAgent | 2023 | recommender | ● profile memory | ● candidate bus + dialogue | ReAct, plan-first, demos | ● filter / retrieve / rank | ● plan critique | single | P | `interecagent.toml` |
| RAH | 2023 | user-side assistant | ● | ● | perceive-learn-act | ○ | ● critic | pipeline | P | (`iagent.toml` is the closest) |
| RecAgent | 2023 | user simulator | ● persona | ● sensory / short / long | – | – | ● memory reflection | population | P | `recagent.toml` |
| Agent4Rec | 2024 | user simulator | ● taste / conformity / activity | ● factual + emotional | – | – | ○ | population | P | `agent4rec.toml` |
| AgentCF | 2024 | user + item agents | ● both sides | ● textual, both sides | – | – | ● collaborative reflection | pair | P | `ItemAgent` class |
| MACRec | 2024 | recommender | ● user analyst | ○ | manager delegation | ● agents as tools, search | ● reflector agent | manager / workers | P | `macrec.toml` |
| MACRS | 2024 | conversational recommender | ○ | ○ dialogue | act planning | – | ● feedback-aware | propose / select | P | `macrs.toml` |
| BiLLP | 2024 | recommender (long-term) | ○ | ● macro + micro memory | hierarchical | ○ | ● reflector | single | P | `billp.toml` |
| ToolRec | 2024 | recommender | ○ | ○ | attribute-wise exploration | ● attribute tools | – | single | S | `interecagent.toml` variant |
| SUBER / KuaiSim | 2024 | RL environment | ○ | – | – | – | – | env | R | `Environment.reward` |
| iAgent | 2025 | user-side agent | ● instruction | ● individual memory | ReAct | ● knowledge retrieval | ● self-reflection | pipeline | P | `iagent.toml` |
| Rec-R1 | 2025 | generator + fixed recommender | – | – | – | ○ recommender as reward | – | single | R | – |
| ARAG | 2025 | recommender | ● user-understanding agent | ○ | pipeline | ● NLI, summariser, ranker | – | pipeline | P | pipeline orchestrator |
| AgentRecBench | 2025 | benchmark | – | – | – | ● world APIs | – | – | env | `Catalog` tools |
| RecoWorld | 2025 | co-evolving pair | ● | ● | ● reasoning + feedback | ○ | ● instructional feedback | pair | R | `recoworld.toml` |
| SimUSER | 2025 | user simulator | ● mined persona | ● | – | – | ○ | population | P | `traits` profile |
| AgenticRec | 2026 | recommender | ○ | ○ | tool-integrated reasoning | ● rec tool suite | – | single | S + R | `interecagent.toml` variant |
| CoARS | 2026 | co-evolving pair | ○ | ● parametric | – | – | ○ (baseline) | pair | R | – |
| τ-Rec / RecRM-Bench | 2026 | evaluation | – | – | – | ● catalog predicates | – | – | verifiable reward | `ranking_metrics` |

## Counting

Over the 21 rows above:

| Component | Central (●) | Present (● or ○) | Absent |
|---|---|---|---|
| Profile | 12 | 17 | 4 |
| Memory | 11 | 17 | 4 |
| Planning | 9 | 12 | 9 |
| Tools | 9 | 14 | 7 |
| Reflection | 10 | 13 | 8 |
| Multi-agent coordination | 8 | 8 | 13 |

No component is universal. Profile and memory are the most common; multi-agent coordination the least. This distribution is the empirical basis for making every component optional in the framework.
