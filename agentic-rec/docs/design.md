# Framework Design Notes

The framework is the survey's Section 4 turned into interfaces. This page records the decisions, so that they can be revisited.

## 1. One agent skeleton for every role

```
Observation ──► profile.render ─┐
                memory.render ──┼─► PlanContext ─► planner.plan(tools) ─► Action
                task ───────────┘                        │
                                                          ▼
                    feedback ─► reflector.reflect ─► memory.add(insight)
```

`Agent` in `agentic_rec/agents/base.py` is the only place where components meet. `RecommenderAgent` fixes a default task and adds `recommend(user)`; `UserAgent` keeps the same three parts (profile, memory, decision procedure) but its decision procedure is a `UserPolicy` because the user side needs a transparent rule-based option for tests and reward shaping; `ItemAgent` is a description that rewrites itself.

The alternative, a class hierarchy with `RecommenderAgent`, `ConversationalAgent`, `PlanningAgent`, ..., was rejected because the survey shows papers differ by *which components they attach*, not by *what kind of agent they are*.

## 2. Every component is optional

Each component family has a `Null*` implementation and a registry key `"none"`. Absent keys in a config mean "no such component", and the agent constructor accepts `None` for each part. The planner default is a deterministic tool chain so that an agent with no LLM still works. That default is what makes classic baselines (ItemKNN, popularity) live in the same space as agentic systems: they are agents with no profile, no memory, no reflection and a `chain` planner.

A subtle consequence: components must be compared with `is None`, never by truthiness, because an empty memory has length zero. That bug was found and fixed while writing the tests, and `test_buffer_memory_len_is_not_truthiness_trap` guards it.

## 3. Composition through a small context object, not through inheritance

`PlanContext` carries the rendered persona, memory text, task, tool set and a `ToolContext`. `ToolContext` holds the observation, a `candidates` list (InteRecAgent's candidate bus) and a `scratch` dict. Tools read and write `candidates`; planners read it as a fallback when the LLM's final answer contains no ids. No component holds a reference to another component; the only shared state is these two dataclasses, created fresh on every step.

## 4. Agents as tools

`AgentTool` wraps any agent as a tool. `ManagerOrchestrator` is then an ordinary ReAct agent whose tools are its workers. `PipelineOrchestrator` and `VoteOrchestrator` cover the other two topologies in the survey. Because the manager is a normal agent, it can itself have a profile, a memory and a reflector, which is what MACRec's design calls for.

## 5. Registry plus plain dict configs

Components register under `(kind, name)`. A config is a nested dict; TOML is the default because it is in the standard library, JSON is accepted, YAML if PyYAML is installed. `registry.create` inspects constructor signatures and injects shared objects (`llm`, `catalog`, `k`) only where they are accepted, so a component never has to declare parameters it does not use.

Extension is: subclass, decorate with `@registry.register("tool", "my_tool")`, refer to `"my_tool"` in a config. `examples/04_custom_component.py` shows this for a tool and a memory.

## 6. LLM backends without SDKs

`LLM.complete(prompt)` and `LLM.chat(messages)` are the whole interface. `OpenAICompatibleLLM` and `AnthropicLLM` use `urllib` so that the package has zero runtime dependencies. `MockLLM` is a deterministic policy over the framework's own prompt conventions; it lets the entire pipeline, the orchestration and the evaluation run offline, which is what the tests and CI use. It is not a model of user behaviour and the README says so.

## 7. Environment returns both text and reward

`Environment.run_episode` converts each user reaction into (a) natural-language feedback delivered to the recommender through `feedback()`, closing the Reflexion loop, and (b) a scalar reward stored in the trajectory, which is what an RL trainer would consume. Both views exist because the survey's 2023 to 2024 systems adapt through text and its 2025 to 2026 systems adapt through rewards; the environment should not force the choice.

## 8. What is deliberately not here

- No training loops. RL and supervised tuning depend on the model runtime; the framework exposes trajectories and rewards and stops there.
- No vector database. `VectorMemory` accepts an `embed` callable; the default is bag-of-words cosine so that retrieval semantics can be tested without a model.
- No dataset downloads. `make_synthetic` provides a catalog with known latent preferences; a MovieLens or Amazon loader is a `Catalog` plus a list of `User` and belongs in user code or a follow-up.

## 9. Reading the structural reproductions

`configs/*.toml` map papers to component choices. They are structural, not numerical, reproductions: the tools are item-kNN and popularity over a synthetic catalog, and the mock LLM follows a fixed policy. Their purpose is to show that eleven published architectures are eleven points in one configuration space and to be a starting point when a real reproduction is needed.
