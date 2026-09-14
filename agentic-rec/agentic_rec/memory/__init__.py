"""Memory modules.

Interface: ``add(entry)``, ``retrieve(query, k)``, ``render(query, k)``,
``clear()``.  Implementations range from a plain buffer to the three-tier
sensory / short-term / long-term structure used by RecAgent and
Generative-Agents-style simulators, with importance scoring and reflection
into higher tiers.
"""

from .base import Memory, MemoryEntry, NullMemory
from .builtin import BufferMemory, HierarchicalMemory, VectorMemory, WindowMemory

__all__ = [
    "Memory",
    "MemoryEntry",
    "NullMemory",
    "BufferMemory",
    "WindowMemory",
    "VectorMemory",
    "HierarchicalMemory",
]
