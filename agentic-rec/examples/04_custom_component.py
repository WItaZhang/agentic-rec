"""Register a custom tool and a custom memory, then use them from a config.

This is the extension path: subclass, register under a string key, refer to
the key in TOML.  Nothing else in the framework needs to change.
"""

import copy

from agentic_rec import MockLLM, build_system, make_synthetic, registry, simulation_metrics
from agentic_rec.memory import BufferMemory
from agentic_rec.tools import Tool, ToolContext, ToolResult


@registry.register("tool", "recent_year")
class RecentYearTool(Tool):
    name = "recent_year"
    description = "Keep only candidates released after a given year."
    input_schema = '{"year": int}'

    def __init__(self, catalog, k: int = 20, year: int = 2015):
        self.catalog, self.k, self.year = catalog, k, year

    def run(self, ctx: ToolContext, year: int | None = None, **_) -> ToolResult:
        y = year or self.year
        ids = [i for i in ctx.candidates if self.catalog.get(i).get("year", 0) >= y][: self.k]
        ctx.candidates = ids
        return ToolResult(text=self.render(self.catalog.get(i) for i in ids), items=ids)


@registry.register("memory", "insight_only")
class InsightOnlyMemory(BufferMemory):
    """Keeps reflections, drops raw events."""

    def add(self, entry, **kw):
        e = self._coerce(entry, **kw)
        if e.kind == "insight":
            super().add(e)


cfg = {
    "recommender": {
        "profile": "history",
        "memory": "insight_only",
        "planner": {"type": "react", "max_steps": 6},
        "tools": ["retrieve", {"type": "recent_year", "year": 2010}, "rank"],
        "reflector": "self_critique",
    },
    "user": {"policy": "preference"},
    "environment": {"max_turns": 4, "k": 8},
}

data = make_synthetic(seed=1)
system = build_system(cfg, MockLLM(), copy.deepcopy(data))
print(system.recommender.describe())
print(simulation_metrics(system.env.run(system.recommender, system.users[:10])))
