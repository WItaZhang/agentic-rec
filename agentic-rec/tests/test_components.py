import json

from agentic_rec import MockLLM, ScriptedLLM, make_synthetic
from agentic_rec.agents import LLMUserPolicy, PreferenceUserPolicy, RecommenderAgent, UserAgent
from agentic_rec.core.types import Message, Observation
from agentic_rec.planning import (
    ChainPlanner,
    DirectPlanner,
    HierarchicalPlanner,
    PlanAndExecutePlanner,
    ReActPlanner,
)
from agentic_rec.planning.base import PlanContext, Planner
from agentic_rec.profile import HistoryProfile, TraitProfile
from agentic_rec.reflection import FeedbackReflector, SelfCritiqueReflector
from agentic_rec.tools import (
    FilterTool,
    HistoryTool,
    RankTool,
    RetrieveTool,
    SearchTool,
    ToolContext,
    ToolSet,
)


def _data():
    return make_synthetic(n_items=60, n_users=5, seed=1)


def test_catalog_filter_search_similar():
    d = _data()
    cat = d.catalog
    comedies = cat.filter(genre="comedy")
    assert all("comedy" in cat.get(i).attrs["genre"] for i in comedies)
    assert cat.search("Golden")  # title keyword
    hist = d.users[0].item_ids()
    sim = cat.similar(hist, k=5, exclude=set(hist))
    assert len(sim) == 5 and not set(sim) & set(hist)


def test_tools_share_candidate_bus():
    d = _data()
    ctx = ToolContext(obs=Observation(user=d.users[0]))
    tools = ToolSet([HistoryTool(d.catalog), RetrieveTool(d.catalog, k=8), RankTool(d.catalog, k=5)])
    assert tools.call("history", ctx, "{}").ok
    tools.call("retrieve", ctx, "{}")
    assert len(ctx.candidates) == 8
    tools.call("rank", ctx, json.dumps({"k": 3}))
    assert len(ctx.candidates) == 3
    assert not tools.call("nope", ctx).ok


def test_filter_and_search_tools_parse_inputs():
    d = _data()
    ctx = ToolContext(obs=Observation(user=d.users[0]))
    r = FilterTool(d.catalog).run(ctx, genre="drama")
    assert r.ok and all("drama" in d.catalog.get(i).attrs["genre"] for i in r.items)
    r2 = SearchTool(d.catalog)(ctx, query="Empire")
    assert r2.ok


def test_react_planner_with_mock_llm_calls_all_tools_then_finishes():
    d = _data()
    tools = ToolSet([HistoryTool(d.catalog), RetrieveTool(d.catalog), RankTool(d.catalog)])
    ctx = PlanContext(obs=Observation(user=d.users[0]), tools=tools)
    ctx.tool_ctx.scratch["catalog"] = d.catalog
    action = ReActPlanner(MockLLM(), top_k=5, max_steps=6).plan(ctx)
    assert action.type.value == "recommend" and 0 < len(action.items) <= 5
    assert sum("Action: " in t for t in ctx.trace) >= 3


def test_parse_action_and_final():
    assert Planner.parse_action("Thought: x\nAction: retrieve\nAction Input: {\"k\": 3}\n") == ("retrieve", '{"k": 3}')
    assert Planner.parse_action("no action here") is None


def test_other_planners_run():
    d = _data()
    llm = MockLLM()
    for planner in (
        DirectPlanner(llm),
        PlanAndExecutePlanner(llm),
        HierarchicalPlanner(llm, max_steps=4),
        ChainPlanner(steps=["retrieve", "rank"]),
    ):
        tools = ToolSet([RetrieveTool(d.catalog), RankTool(d.catalog)])
        ctx = PlanContext(obs=Observation(user=d.users[1]), tools=tools)
        ctx.tool_ctx.scratch["catalog"] = d.catalog
        action = planner.plan(ctx)
        assert action.items, type(planner).__name__


def test_hierarchical_records_strategy():
    d = _data()
    p = HierarchicalPlanner(MockLLM(), strategies=["alpha strategy", "beta strategy"])
    ctx = PlanContext(obs=Observation(user=d.users[1]), tools=ToolSet([RetrieveTool(d.catalog)]))
    a = p.plan(ctx)
    assert a.meta["strategy"] in {"alpha strategy", "beta strategy"}


def test_profiles_render():
    d = _data()
    obs = Observation(user=d.users[0])
    txt = HistoryProfile(d.catalog).render(obs)
    assert "Dominant genres" in txt and d.users[0].id in txt
    assert "Likes:" in TraitProfile().render(obs)


def test_reflectors():
    d = _data()
    obs = Observation(user=d.users[0])
    from agentic_rec.core.types import Action, ActionType

    act = Action(ActionType.RECOMMEND, ["i1"])
    assert SelfCritiqueReflector(ScriptedLLM(["be better"])).reflect(obs, act, "skip", ["t"]) == "be better"
    fr = FeedbackReflector(None)
    assert fr.reflect(obs, act, "click on i1") is None
    assert "negative" in fr.reflect(obs, act, "skip: boring")


def test_recommender_agent_feedback_writes_insight_to_memory():
    d = _data()
    from agentic_rec.memory import BufferMemory

    agent = RecommenderAgent(
        llm=MockLLM(),
        profile=HistoryProfile(d.catalog),
        memory=BufferMemory(),
        planner=ReActPlanner(MockLLM(), max_steps=4),
        tools=[RetrieveTool(d.catalog), RankTool(d.catalog)],
        reflector=SelfCritiqueReflector(ScriptedLLM(["insight!"])),
        catalog=d.catalog,
    )
    rec = agent.recommend(d.users[0])
    assert rec.item_ids
    assert agent.feedback("skip") == "insight!"
    kinds = [e.kind for e in agent.memory.retrieve("", 10)]
    assert "insight" in kinds


def test_user_policies():
    d = _data()
    u = d.users[0]
    items = [d.catalog.get(i) for i in d.catalog.ids()[:10]]
    pref = PreferenceUserPolicy(truth=d.truth, catalog=d.catalog, threshold=0.0, patience=1)
    ua = UserAgent(u, pref, profile=TraitProfile())
    before = len(u.history)
    act = ua.react(items)
    assert act.type.value in {"click", "skip", "exit"}
    if act.type.value == "click":
        assert len(u.history) == before + len(act.items)

    llm_policy = LLMUserPolicy(ScriptedLLM(['{"action": "click", "items": ["' + items[0].id + '"], "comment": "ok"}']))
    ua2 = UserAgent(u, llm_policy, profile=TraitProfile())
    a2 = ua2.react(items, [Message("assistant", "hi")])
    assert a2.type.value == "click" and a2.items == [items[0].id]

    bad = LLMUserPolicy(ScriptedLLM(["not json"]))
    assert UserAgent(u, bad).react(items).type.value == "skip"
