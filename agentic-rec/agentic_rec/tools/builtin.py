from __future__ import annotations

from typing import Any

from ..core.registry import registry
from ..data.catalog import Catalog
from .base import Tool, ToolContext, ToolResult


class _CatalogTool(Tool):
    def __init__(self, catalog: Catalog, k: int = 20) -> None:
        self.catalog = catalog
        self.k = k

    def _items(self, ids):
        return [self.catalog.get(i) for i in ids if self.catalog.has(i)]


@registry.register("tool", "history")
class HistoryTool(_CatalogTool):
    name = "history"
    description = "Show the target user's most recent interactions."
    input_schema = '{"n": int}'

    def run(self, ctx: ToolContext, n: int | None = None, **_: Any) -> ToolResult:
        ids = ctx.history[-(n or self.k) :]
        return ToolResult(text=self.render(self._items(ids)) if ids else "(no history)", items=ids)


@registry.register("tool", "item_info")
class ItemInfoTool(_CatalogTool):
    name = "item_info"
    description = "Look up details of specific items by id."
    input_schema = '{"ids": [str]}'

    def run(self, ctx: ToolContext, ids: list[str] | None = None, query: str = "", **_: Any) -> ToolResult:
        ids = ids or [x.strip() for x in query.split(",") if x.strip()]
        return ToolResult(text=self.render(self._items(ids)), items=[i for i in ids if self.catalog.has(i)])


@registry.register("tool", "search")
class SearchTool(_CatalogTool):
    name = "search"
    description = "Keyword search over the catalog; writes hits to the candidate bus."
    input_schema = '{"query": str}'

    def run(self, ctx: ToolContext, query: str = "", **_: Any) -> ToolResult:
        if not query:
            return ToolResult("search needs a query", ok=False)
        ids = [i for i in self.catalog.search(query, self.k * 2) if i not in ctx.history][: self.k]
        ctx.candidates = ids
        return ToolResult(text=self.render(self._items(ids)), items=ids)


@registry.register("tool", "filter")
class FilterTool(_CatalogTool):
    name = "filter"
    description = "Hard-filter the catalog by attribute conditions (e.g. genre=comedy)."
    input_schema = '{"<attr>": value, ...}'

    def run(self, ctx: ToolContext, **conditions: Any) -> ToolResult:
        conditions = {k: v for k, v in conditions.items() if k not in {"query"}}
        if not conditions:
            return ToolResult("filter needs at least one condition", ok=False)
        ids = [i for i in self.catalog.filter(**conditions) if i not in ctx.history]
        pool = set(ctx.candidates) if ctx.candidates else None
        if pool is not None:
            ids = [i for i in ids if i in pool] or ids
        ctx.candidates = ids[: self.k]
        return ToolResult(text=self.render(self._items(ctx.candidates)), items=ctx.candidates)


@registry.register("tool", "retrieve")
class RetrieveTool(_CatalogTool):
    name = "retrieve"
    description = "Soft retrieval: items similar to the user's history (item-kNN). Fills the candidate bus."
    input_schema = '{"k": int}'

    def run(self, ctx: ToolContext, k: int | None = None, **_: Any) -> ToolResult:
        seed = ctx.history[-self.k :] or ctx.candidates
        ids = self.catalog.similar(seed, k or self.k, exclude=set(ctx.history))
        ctx.candidates = ids
        return ToolResult(text=self.render(self._items(ids)), items=ids)


@registry.register("tool", "rank")
class RankTool(_CatalogTool):
    name = "rank"
    description = "Rank the current candidate bus for the target user with a scoring model."
    input_schema = '{"k": int}'

    def run(self, ctx: ToolContext, k: int | None = None, **_: Any) -> ToolResult:
        cands = ctx.candidates or self.catalog.most_popular(self.k, exclude=set(ctx.history))
        scores = self.catalog.score(cands, ctx.history)
        ranked = sorted(cands, key=lambda i: -scores.get(i, 0))[: k or self.k]
        ctx.candidates = ranked
        rows = [f"{self.catalog.get(i).describe()} score={scores.get(i, 0):.2f}" for i in ranked]
        return ToolResult(text="\n".join(rows) if rows else "(no candidates)", items=ranked)


@registry.register("tool", "popular")
class PopularityTool(_CatalogTool):
    name = "popular"
    description = "Most popular items not yet seen by the user (cold-start fallback)."
    input_schema = '{"k": int}'

    def run(self, ctx: ToolContext, k: int | None = None, **_: Any) -> ToolResult:
        ids = self.catalog.most_popular(k or self.k, exclude=set(ctx.history))
        if not ctx.candidates:
            ctx.candidates = ids
        return ToolResult(text=self.render(self._items(ids)), items=ids)
