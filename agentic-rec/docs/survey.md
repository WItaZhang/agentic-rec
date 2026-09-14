# Agentic Recommender Systems: A Survey and a Component Model

*Last revised September 2026.*

This document surveys the line of work that puts a large language model (LLM) *agent*, rather than a scoring model, at the centre of a recommender system. It has three goals:

1. Organise the field with a taxonomy that is stable across the 2023 to 2026 literature.
2. Identify the components that influential systems share, and show that most systems are configurations of the same small set of parts.
3. Motivate the accompanying reference framework, in which each of those parts is an optional, replaceable module ([design.md](design.md)).

The paper-by-component matrix is kept separately in [component-matrix.md](component-matrix.md); citation keys refer to [references.bib](references.bib).

---

## 1. Scope and definitions

**LLM-for-recommendation** uses a language model as a feature extractor, a generator of item text, a re-ranker, or a fine-tuned scorer. The model is called once per query and has no control flow of its own.

**Agentic recommendation** gives the model a loop. The agent perceives a state (user record, dialogue, candidate items), plans, invokes tools or other agents, acts, observes the result, and updates an internal state before the next step. The distinguishing features, inherited from the general agent literature (ReAct [yao2023react], Reflexion [shinn2023reflexion], Generative Agents [park2023generative]), are:

- **autonomy over control flow**: the agent decides how many steps to take and which capabilities to invoke;
- **statefulness across steps and sessions**: memory that outlives a single prompt;
- **interaction with an environment**: tools, users, and other agents, whose outputs feed back into the loop.

This survey covers work from Chat-REC in March 2023 to the mid-2026 benchmark and reinforcement learning papers. It excludes pure prompt-based re-ranking and LLM fine-tuning for recommendation unless the resulting model is used inside an agent loop.

Two recent surveys cover overlapping ground and are recommended as complementary reading: Peng et al. [peng2025survey] categorise systems as recommender-, interaction- and simulation-oriented; Lin et al. [lin2026roadmap] organise the field by level of autonomy and by the paradigms agent-assisted, agent-as-recommender and agent-as-user-simulator. Huang et al. [huang2025multimodal] focus on the multimodal case. The taxonomy below is compatible with all three but is organised around *what role the agent plays* and *what the agent is made of*, because that is what determines the engineering.

---

## 2. Taxonomy

### 2.1 By role of the agent

| Role | The agent acts as... | Representative work |
|---|---|---|
| **Agent-as-recommender** | the system that selects items, holds a dialogue, and calls conventional models as tools | Chat-REC, RecMind, InteRecAgent, ToolRec, MACRec, BiLLP, MACRS, LLMCRS, AgenticRec |
| **Agent-as-user** | a simulated person who browses, clicks, rates, converses and leaves | RecAgent, Agent4Rec, iEvaLM, SUBER, KuaiSim, SimUSER, RecoWorld's user side |
| **Agent-as-item** | an item with a self-updating description that "negotiates" with user agents | AgentCF, Rec4Agentverse |
| **User-side assistant** | a personal agent between the user and the platform, re-ranking or filtering on the user's behalf | RAH, iAgent |
| **Co-evolving pair** | recommender and user agents trained jointly from shared trajectories | CoARS, RecoWorld |

The first two roles account for the majority of papers; the multi-agent systems combine several roles in one system.

### 2.2 By topology

- **Single agent** with tools (RecMind, InteRecAgent, ToolRec, BiLLP, iAgent, AgenticRec).
- **Manager and workers**: one agent delegates sub-tasks to specialised agents (MACRec's manager, user analyst, item analyst, reflector, searcher; AgentRec's coordinator).
- **Proposal and selection**: several agents propose, one selects (MACRS's act-specific responders and selector; MACS's hybrid LLM plus search engine).
- **Population**: many user agents interacting with one recommender (Agent4Rec's 1,000 agents; RecAgent; AgentRecBench's simulated worlds).

### 2.3 By how the agent is optimised

- **In-context only**: behaviour is shaped by prompt design, retrieved memory and verbal reflection; the LLM's weights are fixed. This describes almost every 2023 to 2024 system.
- **Supervised trajectory tuning**: the agent is fine-tuned on tool-use trajectories (ToolRec's surrogate-user tuning; AgenticRec's trajectory activation stage).
- **Reinforcement learning from interaction**: Rec-R1 closes the loop between a generative LLM and a fixed recommender's reward; RecoWorld and CoARS train against simulated users; ReRec applies reinforcement fine-tuning to a reasoning assistant; RecRM-Bench asks what the reward model should measure.

The shift from the first to the third category is the clearest trend of 2025 to 2026 and is discussed in Section 6.

---

## 3. Representative systems

The descriptions below are deliberately compressed to the *mechanism*. Years are those of the first public version.

### 3.1 2023: the founding designs

**Chat-REC** [gao2023chatrec]. A conventional recommender produces candidates; ChatGPT, prompted with the user's profile and history, re-ranks and explains them in a dialogue. There is no tool loop or memory beyond the dialogue, but the paper set the template of *LLM-as-interface over a retrieval model*.

**RecMind** [wang2023recmind]. The first fully agentic design: a planner that can use chain-of-thought, tree-of-thought or the paper's *self-inspiring* strategy (the agent keeps a record of previously explored plan branches to avoid repeating them), a memory split into personalised memory and world knowledge, and tools including a database query tool, a search tool and a text summariser. Evaluated on rating prediction, sequential recommendation, explanation and review summarisation.

**InteRecAgent** [huang2023interecagent]. "LLM as the brain, recommender models as tools." Three tool types (hard-condition query, soft-condition retrieval, ranking) share a **candidate bus** so that item sets flow between tools without passing through the prompt. Adds a **user-profile memory**, **dynamic demonstration** retrieval for in-context planning, and a **reflection** step that critiques the plan when the tool chain fails. The candidate bus is the single most reused engineering idea in the field.

**RAH** [shu2023rah]. RecSys-Assistant-Human: a personal assistant agent that perceives, learns, acts, critiques and reflects on the user's behalf, filtering and adjusting what the platform recommends.

**RecAgent** [wang2023recagent]. A user simulator whose agents have a **profile**, a **three-tier memory** (sensory, short-term, long-term, with importance scoring and reflection into the long-term store) and an **action** module covering browsing, clicking, chatting with other agents and posting to a social feed. Establishes the simulator-as-sandbox use case.

**Agent4Rec** [zhang2024agent4rec]. One thousand generative user agents initialised from MovieLens with persona traits (**taste**, **rationality/conformity**, **activity**), a factual and an emotional memory, and actions that include leaving the platform. Used to ask counterfactual questions such as whether a recommender causes filter bubbles.

**AgentCF** [zhang2024agentcf]. Both users and items are agents with textual memory. After each simulated interaction, a **collaborative reflection** step rewrites the user's and the item's self-descriptions so that they become more consistent with the observed preference, yielding a text-space analogue of collaborative filtering.

**iEvaLM** [wang2023ievalm] and **LLMCRS** [feng2023llmcrs]. Interactive evaluation of conversational recommenders with an LLM user simulator, and a conversational recommender that plans dialogue sub-tasks and calls expert models for each.

### 3.2 2024: multi-agent, long-horizon planning, tool learning

**MACRec** [wang2024macrec]. A manager decomposes the task and dispatches to a user analyst, an item analyst, a reflector and a searcher, each an LLM agent with its own prompt and tools. Shows that role decomposition lets a single system handle rating prediction, sequential recommendation and conversational recommendation.

**MACRS** [fang2024macrs]. A multi-agent conversational recommender in which act-specific agents (ask, recommend, chit-chat) each produce a candidate response, a planner selects among them, and a **user-feedback-aware reflection** mechanism revises dialogue-act planning after negative feedback.

**BiLLP** [shi2024billp]. Frames recommendation as a long-term engagement problem and uses **bi-level planning**: a macro planner sets a high-level strategy from long-term memory and a micro planner turns it into item-level actions; a reflector updates both memories from user feedback. It is the first agentic system explicitly targeting retention rather than one-shot accuracy.

**ToolRec** [zhao2024toolrec]. LLM as **surrogate user** that explores the item space attribute by attribute, invoking attribute-oriented retrieval and ranking tools; the surrogate is tuned on synthesised trajectories.

**Rec4Agentverse** [zhang2024rec4agentverse]. Items become agents on an LLM agent platform; recommendation is then a matter of matching, and the paper sketches how user-agent, item-agent and platform-agent may collaborate.

**SUBER** [corecco2024suber] and **KuaiSim** [zhao2023kuaisim]. RL environments whose reward comes from LLM-simulated (SUBER) or model-based (KuaiSim) users; they connect the agentic simulator line to classical RL-for-recommendation.

**"How reliable is your simulator?"** [zhu2024reliable]. Evaluates LLM user simulators for conversational recommendation and finds data leakage, over-agreeableness and inconsistent personas. This is the most cited caution in the simulator literature.

### 3.3 2025: benchmarks, environments, user-side agents, RL

**iAgent** [bao2025iagent]. A *user-side* agent that re-ranks the platform's list according to the user's instruction and individual memory, using retrieved knowledge and self-reflection, so that the user's interests are shielded from platform incentives.

**Rec-R1** [lin2025recr1]. Closed-loop RL in which a generative LLM is optimised with rewards coming directly from a fixed downstream recommender, avoiding the need for labelled reasoning data.

**ARAG** [maragheh2025arag]. Agentic retrieval-augmented generation for personalisation: separate agents for user understanding, natural-language inference against the context, context summarisation and item ranking, replacing a single retrieval step.

**AgentRecBench** [zhang2025agentrecbench]. A benchmark that wraps multi-domain datasets (Yelp, Goodreads, Amazon) into simulated worlds with standard APIs an agent can query and act on, and evaluates agents on classic, evolving-interest and cold-start tasks.

**RecoWorld** [liu2025recoworld]. A simulated environment with a **dual view**: simulated users evaluate content, update preferences and emit *instructional* feedback when they are about to disengage; the agentic recommender integrates that feedback with its own reasoning and is improved by iterative RL. Retention is the objective.

**SimUSER** [bougie2025simuser]. User simulators built from self-consistent personas mined from histories, with persona, memory, perception and "brain" modules, validated against real human behaviour at micro and macro levels.

**AgentRec** [agentrec2025]. A multi-agent collaborative recommender with an adaptive coordinator, illustrating that manager/worker decomposition has become a default pattern.

### 3.4 2026: verifiable evaluation and learning from interaction

**AgenticRec** [li2026agenticrec]. Recommendation as tool-integrated reasoning over a recommendation-oriented tool suite, trained in two stages: trajectory activation from implicit feedback, then progressive preference refinement on self-generated hard item pairs.

**CoARS** [wang2026coars]. Argues that Reflexion-style textual memory is a bottleneck and instead internalises interaction experience into parameters: an interaction reward couples the recommender agent and the user agent through shared trajectories, and self-distilled credit assignment turns history into token-level supervision.

**τ-Rec** [narasimhan2026taurec]. Replaces LLM-as-judge with verifiable rewards over catalog predicates and a reveal-tagged elicitation protocol, reporting pass^k reliability; frontier models reach only about 57 percent at pass^1, which quantifies the gap between demo quality and deployable reliability.

**RecRM-Bench** [recrm2026]. Benchmarks reward models for agentic recommenders across several dimensions (instruction following, intent understanding, final outcome), arguing that single outcome-based rewards are insufficient for RL.

**Roadmap** [lin2026roadmap]. Organises the field by autonomy level, and reports that single-agent systems still dominate while multi-agent systems grow steadily. Also: MACS [macs2026] for reliable e-commerce conversational recommendation with hybrid LLM and search agents; entropy-guided diversification for preference elicitation [entropy2026]; ReRec [rerec2026] for reinforcement fine-tuning of reasoning assistants; AgenticRecTune [agenticrectune2026] for multi-agent system optimisation with a self-evolving skill hub.

---

## 4. The common components

Reading the systems above side by side, the architectures reduce to nine components. Each one appears in most systems, is absent in some, and is implemented in only a handful of distinct ways.

### 4.1 Profile

*What the agent knows about who it acts for or as.*

- **Recommender side**: a rendered summary of the target user (id, demographics, recent history, dominant attributes). InteRecAgent keeps it as a memory; MACRec assigns a user analyst agent to produce it; ARAG has a user-understanding agent.
- **User side**: a persona. Agent4Rec's *taste, activity, conformity* triple is the most reused; RecAgent uses free-text profiles; SimUSER mines self-consistent personas.
- Variants: static (hand-written or generated once), history-derived (recomputed each step), trait-based (structured slots).

### 4.2 Memory

*State that outlives one prompt.*

- **Buffer / window**: dialogue history and recent actions (Chat-REC, InteRecAgent, most conversational systems).
- **Relevance-ranked store**: retrieval by a weighted sum of relevance, recency and importance; the Generative Agents rule adopted by RecAgent and Agent4Rec.
- **Hierarchical**: sensory to short-term to long-term with promotion and periodic reflection (RecAgent), factual versus emotional (Agent4Rec), personalised versus world knowledge (RecMind).
- **Item-side memory**: AgentCF's item descriptions.
- **Parametric memory**: CoARS moves experience into weights and treats textual memory as the baseline.

### 4.3 Planning

*How a step is chosen.*

- **Direct**: one call, no loop (Chat-REC).
- **ReAct**: interleaved thought, action, observation (InteRecAgent, iAgent, most tool-using agents).
- **Plan-then-execute**: write a plan, execute, replan on failure (RecMind; InteRecAgent's plan-first mode).
- **Hierarchical**: macro strategy then micro actions (BiLLP), or task decomposition into sub-tasks (LLMCRS, MACRec).
- **Search-based**: tree-of-thought and self-inspiring (RecMind).
- **Demonstration-augmented**: retrieve similar solved cases into the plan prompt (InteRecAgent).

### 4.4 Tool use

*Capabilities the agent calls rather than knows.*

- Conventional recommender models as tools: hard filter, soft retrieval, ranking (InteRecAgent, ToolRec, AgenticRec).
- Data access: SQL-like queries, item lookup, search (RecMind, MACRec's searcher, AgentRecBench's world APIs).
- Other agents as tools (MACRec, ARAG, AgentRec).
- Shared state between tools: the candidate bus.

### 4.5 Reflection

*Turning outcomes into reusable text.*

- Self-critique of a trajectory (Reflexion; RecMind's self-inspiring; InteRecAgent's plan reflection; iAgent).
- Feedback-conditioned reflection (MACRS; BiLLP's reflector; RecoWorld's instructional feedback).
- Collaborative reflection updating two parties (AgentCF).
- A dedicated reflector agent (MACRec).

### 4.6 Action interface

*What the agent can do to the world.*

- Recommender: recommend a list, ask a clarifying question, respond in natural language, call a tool.
- User: click, rate, skip, comment, exit; in richer simulators also chat and post.
- Item: rewrite own description.
- The action space, not the model, is what makes an agent a "recommender" or a "user"; the loop around it is the same.

### 4.7 Coordination

*How several agents combine.*

- Manager and workers (MACRec, AgentRec).
- Propose and select (MACRS, MACS).
- Pipeline (platform recommender then personal agent, as in RAH and iAgent).
- Population interaction (Agent4Rec, RecAgent).

### 4.8 Environment and optimisation

*Where the loop runs and what improves over time.*

- Static offline datasets with held-out positives (most 2023 to 2024 work).
- Simulated users with retention signals (Agent4Rec, RecoWorld, SUBER).
- Reward functions for RL (Rec-R1, CoARS, RecoWorld, RecRM-Bench).
- Trajectory datasets for supervised tuning (ToolRec, AgenticRec).

### 4.9 Evaluation

- Ranking metrics on held-out interactions (Hit rate, NDCG, Recall, MRR).
- Simulator metrics (clicks, turns to exit, retention, diversity, filter-bubble measures).
- LLM-as-judge for dialogue quality, with known reliability issues [zhu2024reliable].
- Verifiable rewards over catalog predicates and pass^k reliability (τ-Rec).
- Standardised agent benchmarks (AgentRecBench, RecRM-Bench).

---

## 5. What is actually shared, and what differs

Cross-referencing the component matrix gives four observations.

**Observation 1: the loop is universal; the components are optional.** Every system has *perceive, plan, act*; every system with more than one turn has some memory; every system with tools has a candidate-passing mechanism. No single component is present everywhere. Chat-REC has no memory or tools; Agent4Rec's recommender has no LLM; the ItemKNN baseline in this repository has no planner at all. This is exactly the shape of a framework with optional parameters rather than a fixed pipeline.

**Observation 2: differentiation is concentrated in three places.** Papers differ mainly in (a) how memory is structured and when reflection writes to it, (b) how planning is decomposed (flat, hierarchical, multi-agent), and (c) how the agent is optimised (prompting, tuning, RL). Tool suites, profiles and evaluation protocols are near-identical across papers.

**Observation 3: multi-agent is single-agent with agents as tools.** MACRec's manager is a ReAct agent whose tools happen to be other agents; MACRS's selector is a ranking step over proposals. Nothing in the loop needs to know whether a tool is a retrieval model or another LLM. Treating agents as tools removes an entire layer from the architecture.

**Observation 4: the field is moving from textual to parametric adaptation.** 2023 to 2024 systems adapt by writing text into memory; 2025 to 2026 systems (Rec-R1, AgenticRec, CoARS, RecoWorld) adapt by updating weights against simulated or real feedback, and the benchmark papers (τ-Rec, RecRM-Bench) are about making that feedback trustworthy. Textual reflection remains a strong baseline and is the cheaper option in practice.

---

## 6. Open problems

1. **Simulator fidelity.** LLM users are agreeable and leak knowledge [zhu2024reliable]; SimUSER and RecoWorld address consistency and disengagement but the sim-to-real gap remains unmeasured for most claims.
2. **Reliable evaluation.** τ-Rec's pass^k results show that single-run judge scores overstate reliability; verifiable rewards need structured catalogs that not all domains have.
3. **Cost.** A ReAct recommender spends 5 to 20 LLM calls per user per turn. Which components earn their cost is rarely ablated; the ablation example in this repository is meant to make that habit cheap.
4. **Long-horizon objectives.** BiLLP and RecoWorld target retention; most benchmarks still score one-shot accuracy.
5. **User-side agency and incentives.** iAgent and RAH place an agent on the user's side; how platform agents and user agents should negotiate is an open design question.
6. **Trust and safety.** Prompt injection through item text, unfair exposure, and explanation robustness (RobustExplain [robustexplain2026]) are only beginning to be studied.

---

## 7. From survey to framework

The accompanying package implements Section 4 as nine small module families with a shared registry, so that an architecture is a configuration:

| Component | Package module | Variants shipped |
|---|---|---|
| Profile | `agentic_rec.profile` | none, static, history, traits |
| Memory | `agentic_rec.memory` | none, buffer, window, vector, hierarchical |
| Planning | `agentic_rec.planning` | chain, direct, react, plan_execute, hierarchical |
| Tools | `agentic_rec.tools` | history, item_info, search, filter, retrieve, rank, popular |
| Reflection | `agentic_rec.reflection` | none, self_critique, feedback |
| Action interface | `agentic_rec.agents` | RecommenderAgent, UserAgent, ItemAgent |
| Coordination | `agentic_rec.orchestration` | manager, pipeline, vote, agents-as-tools |
| Environment | `agentic_rec.environment` | multi-turn simulation with rewards and retention |
| Evaluation | `agentic_rec.evaluation` | ranking and simulation reports |

The `configs/` directory expresses eleven of the systems above as configurations over these modules. They are structural reproductions, not numerical ones: the goal is to show that the architectures are points in one space, and to give a place to start when reproducing a specific paper. See [design.md](design.md) for the reasoning behind the interfaces.
