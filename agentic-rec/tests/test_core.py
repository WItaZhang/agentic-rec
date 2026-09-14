from agentic_rec.core.registry import Registry
from agentic_rec.core.types import Action, ActionType, Item, User
from agentic_rec.memory import BufferMemory, HierarchicalMemory, VectorMemory, WindowMemory


def test_registry_create_and_override_injection():
    reg = Registry()

    @reg.register("thing", "a")
    class A:
        def __init__(self, x=1, llm=None):
            self.x, self.llm = x, llm

    obj = reg.create("thing", {"type": "a", "x": 5}, llm="L", catalog="ignored")
    assert obj.x == 5 and obj.llm == "L"
    assert reg.create("thing", None) is None
    assert reg.names("thing") == ["a"]


def test_item_and_user_helpers():
    it = Item("i1", "Title", {"genre": ["a", "b"]})
    assert "[i1]" in it.describe() and it.get("genre") == ["a", "b"]
    u = User("u1")
    assert u.item_ids() == []
    a = Action(ActionType.RECOMMEND, ["i1", "i2"])
    assert a.items == ["i1", "i2"]


def test_window_memory_drops_oldest():
    m = WindowMemory(size=3)
    for i in range(5):
        m.add(f"e{i}")
    assert [e.content for e in m.retrieve("", 10)] == ["e2", "e3", "e4"]


def test_vector_memory_ranks_by_relevance():
    m = VectorMemory(beta=0.0, gamma=0.0)
    m.add("the user loves science fiction films")
    m.add("the user dislikes romance")
    m.add("weather is nice today")
    top = m.retrieve("science fiction", k=1)[0]
    assert "science" in top.content


def test_hierarchical_memory_promotes_insights():
    m = HierarchicalMemory(short_size=2, sensory_threshold=0.5, summarizer=lambda xs: "SUMMARY:" + ";".join(xs))
    m.add("noise", importance=0.1)  # stays in sensory
    m.add("clicked a", importance=0.9)
    m.add("clicked b", importance=0.9)
    m.add("clicked c", importance=0.9)  # overflow -> reflect
    longterm = m.long.retrieve("", 10)
    assert len(longterm) == 1 and longterm[0].content.startswith("SUMMARY:")
    assert len(m.short) == 1


def test_buffer_memory_len_is_not_truthiness_trap():
    m = BufferMemory()
    assert len(m) == 0
    from agentic_rec.agents.base import Agent

    a = Agent(memory=m)
    assert a.memory is m
