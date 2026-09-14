"""Build one recommender agent by hand and inspect its reasoning trace."""

from agentic_rec import MockLLM, RecommenderAgent, make_synthetic
from agentic_rec.memory import WindowMemory
from agentic_rec.planning import ReActPlanner
from agentic_rec.profile import HistoryProfile
from agentic_rec.reflection import SelfCritiqueReflector
from agentic_rec.tools import HistoryTool, RankTool, RetrieveTool

data = make_synthetic(n_items=100, n_users=5, seed=0)
llm = MockLLM()  # swap for OpenAICompatibleLLM(model="gpt-4o-mini") or AnthropicLLM()

agent = RecommenderAgent(
    llm=llm,
    profile=HistoryProfile(data.catalog),
    memory=WindowMemory(size=20),
    planner=ReActPlanner(llm, max_steps=6),
    tools=[HistoryTool(data.catalog), RetrieveTool(data.catalog), RankTool(data.catalog)],
    reflector=SelfCritiqueReflector(llm),
    catalog=data.catalog,
    k=5,
)

user = data.users[0]
rec = agent.recommend(user)
print("user likes:", user.attrs["likes"])
print("recommended:", [data.catalog.get(i).describe() for i in rec.item_ids])
print("\n--- trace ---")
print("\n".join(agent.last_trace)[:1500])
print("\n--- reflection ---")
print(agent.feedback("skip: none of these match my mood"))
print("\nmemory now holds:", len(agent.memory), "entries")
