"""Tools: everything an agent can *call* instead of *know*.

The pattern is InteRecAgent's: the LLM is the brain, conventional
recommender components (hard filters, retrievers, rankers, lookups) are
tools, and a shared ``ToolContext`` plays the role of the *candidate bus*
that lets tools pass item sets to each other without stuffing them into the
prompt.
"""

from .base import Tool, ToolContext, ToolResult, ToolSet
from .builtin import (
    FilterTool,
    HistoryTool,
    ItemInfoTool,
    PopularityTool,
    RankTool,
    RetrieveTool,
    SearchTool,
)

__all__ = [
    "Tool",
    "ToolContext",
    "ToolResult",
    "ToolSet",
    "HistoryTool",
    "ItemInfoTool",
    "SearchTool",
    "FilterTool",
    "RetrieveTool",
    "RankTool",
    "PopularityTool",
]
