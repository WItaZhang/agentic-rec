"""Reflection modules: turning outcomes into reusable insights.

A reflector is called *after* an action has been taken and (optionally)
feedback has arrived.  It returns a text insight which the agent writes into
memory so that later steps can retrieve it.  This is the Reflexion pattern
used by RecMind (self-inspiring), MACRec/MACRS (reflector agent), BiLLP
(reflector), iAgent (self-reflection) and most simulators.
"""

from .base import NullReflector, Reflector
from .builtin import FeedbackReflector, SelfCritiqueReflector

__all__ = ["Reflector", "NullReflector", "SelfCritiqueReflector", "FeedbackReflector"]
