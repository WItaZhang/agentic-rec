from __future__ import annotations

from ..core.prompting import section
from ..core.registry import registry
from ..core.types import Action, ActionType
from .base import PlanContext, Planner

_REACT_RULES = (
    "Decide step by step. Use exactly this format on each turn:\n"
    "Thought: <reasoning>\nAction: <tool name>\nAction Input: <json>\n"
    "When you are done, answer with:\nThought: <reasoning>\nFinal Answer: <comma-separated item ids>\n"
)


@registry.register("planner", "direct")
class DirectPlanner(Planner):
    """Single-shot prompting: persona + memory + candidates -> ranked answer.

    With ``prefetch`` (default) every attached tool is run once, in order,
    before the LLM call, so conventional models generate candidates and the
    LLM only re-ranks them (Chat-REC).  Without tools it is pure prompting.
    """

    def __init__(self, llm=None, top_k: int = 10, prefetch: bool = True) -> None:
        super().__init__(llm, top_k)
        self.prefetch = prefetch

    def plan(self, ctx: PlanContext) -> Action:
        assert self.llm is not None, "DirectPlanner needs an LLM"
        if self.prefetch:
            for name in ctx.tools.names():
                result = ctx.tools.call(name, ctx.tool_ctx, "{}")
                ctx.trace.append(f"Action: {name}\nObservation: {result.text}")
        cands = ctx.tool_ctx.candidates if ctx.tool_ctx else []
        cat = ctx.tool_ctx.scratch.get("catalog") if ctx.tool_ctx else None
        rows = [cat.get(i).describe() if cat and cat.has(i) else f"[{i}]" for i in cands]
        prompt = ctx.prompt_head() + section("Candidates", "\n".join(rows) or "(none: propose items yourself)")
        prompt += "Observation: " + ("; ".join(rows) if rows else "(no candidates)")
        prompt += "\nAnswer with a comma-separated list of item ids, best first.\nFinal Answer:"
        out = self.llm.complete(prompt)
        ctx.trace.append(out)
        return self.parse_final(out, ctx)


@registry.register("planner", "react")
class ReActPlanner(Planner):
    """Thought -> Action -> Observation loop with tool calls (ReAct)."""

    def __init__(self, llm=None, top_k: int = 10, max_steps: int = 6) -> None:
        super().__init__(llm, top_k)
        self.max_steps = max_steps

    def plan(self, ctx: PlanContext) -> Action:
        assert self.llm is not None, "ReActPlanner needs an LLM"
        head = ctx.prompt_head() + section("Available tools", ctx.tools.render()) + section("Rules", _REACT_RULES)
        scratch = ""
        for _ in range(self.max_steps):
            out = self.llm.complete(head + scratch + "\n")
            ctx.trace.append(out)
            if "Final Answer:" in out:
                return self.parse_final(out, ctx)
            parsed = self.parse_action(out)
            if parsed is None:
                return self.parse_final(out, ctx)
            name, raw = parsed
            result = ctx.tools.call(name, ctx.tool_ctx, raw)
            obs_text = f"Observation: {result.text}\n"
            ctx.trace.append(obs_text)
            scratch += "\n" + out.strip() + "\n" + obs_text
        return self.parse_final("Final Answer: " + ", ".join(ctx.tool_ctx.candidates[: self.top_k]), ctx)


@registry.register("planner", "plan_execute")
class PlanAndExecutePlanner(Planner):
    """Write a numbered plan first, then execute it step by step (RecMind).

    Each step that names a tool is executed; the final step yields the
    answer.  ``replan`` re-asks for a plan after the first failure.
    """

    def __init__(self, llm=None, top_k: int = 10, replan: bool = True) -> None:
        super().__init__(llm, top_k)
        self.replan = replan

    def plan(self, ctx: PlanContext) -> Action:
        assert self.llm is not None
        head = ctx.prompt_head() + section("Available tools", ctx.tools.render())
        plan_txt = self.llm.complete(head + "## Instruction\nWrite a numbered plan, one tool per step, ending with 'finish'.\nPlan:\n")
        ctx.trace.append("Plan:\n" + plan_txt)
        steps = [ln.strip() for ln in plan_txt.splitlines() if ln.strip()]
        last_obs = ""
        for step in steps:
            name = next((n for n in ctx.tools.names() if n in step), None)
            if name is None:
                continue
            result = ctx.tools.call(name, ctx.tool_ctx, "{}")
            if not result.ok and self.replan:
                return ReActPlanner(self.llm, self.top_k).plan(ctx)
            last_obs = result.text
            ctx.trace.append(f"Action: {name}\nObservation: {result.text}")
        prompt = head + f"Observation: {last_obs}\nGive the final ranked item ids.\nFinal Answer:"
        out = self.llm.complete(prompt)
        ctx.trace.append(out)
        return self.parse_final(out, ctx)


@registry.register("planner", "hierarchical")
class HierarchicalPlanner(Planner):
    """Macro planner sets a goal; micro planner executes with tools (BiLLP).

    The macro step is one LLM call that produces a short strategy
    (e.g. "explore a new genre" vs "exploit dominant taste"); the strategy is
    injected into the micro planner's task description.
    """

    def __init__(self, llm=None, top_k: int = 10, max_steps: int = 6, strategies: list[str] | None = None) -> None:
        super().__init__(llm, top_k)
        self.micro = ReActPlanner(llm, top_k, max_steps)
        self.strategies = strategies or ["exploit the user's dominant preference", "explore an adjacent interest"]

    def plan(self, ctx: PlanContext) -> Action:
        assert self.llm is not None
        macro_prompt = (
            ctx.prompt_head()
            + section("Strategies", "\n".join(f"- {s}" for s in self.strategies))
            + "Choose one strategy for this turn and state it in one line.\nStrategy:"
        )
        strategy = self.llm.complete(macro_prompt).strip().splitlines()[0] if self.strategies else ""
        if not any(s in strategy for s in self.strategies):
            strategy = self.strategies[0]
        ctx.trace.append(f"Macro strategy: {strategy}")
        ctx.task = f"{ctx.task} Long-term strategy for this turn: {strategy}."
        action = self.micro.plan(ctx)
        action.meta["strategy"] = strategy
        return action


@registry.register("planner", "chain")
class ChainPlanner(Planner):
    """Deterministic tool pipeline; no LLM.  Useful as a baseline and in tests."""

    def __init__(self, llm=None, top_k: int = 10, steps: list[str] | None = None) -> None:
        super().__init__(llm, top_k)
        self.steps = steps or ["retrieve", "rank"]

    def plan(self, ctx: PlanContext) -> Action:
        for name in self.steps:
            result = ctx.tools.call(name, ctx.tool_ctx, "{}")
            ctx.trace.append(f"Action: {name}\nObservation: {result.text}")
        ids = list(ctx.tool_ctx.candidates[: self.top_k])
        return Action(type=ActionType.RECOMMEND, payload=ids, rationale="\n".join(ctx.trace))
