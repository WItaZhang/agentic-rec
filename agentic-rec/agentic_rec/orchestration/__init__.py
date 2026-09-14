"""Multi-agent coordination.

The key observation across MACRec, MACRS, AgentCF and the manager/worker
systems is that a *multi-agent* recommender is just an agent whose tools are
other agents.  ``AgentTool`` performs that adaptation; ``ManagerOrchestrator``
is then a normal ReAct agent.  ``PipelineOrchestrator`` and
``VoteOrchestrator`` cover the two other common topologies.
"""

from .base import (
    AgentTool,
    ManagerOrchestrator,
    Orchestrator,
    PipelineOrchestrator,
    VoteOrchestrator,
)

__all__ = ["AgentTool", "Orchestrator", "ManagerOrchestrator", "PipelineOrchestrator", "VoteOrchestrator"]
