"""Explicit state machines (Qt-free): the primitive (`core`) and every machine of the application (`specs`).

See `docs/state-machines.md` for each machine's states and transitions, and for the inventory of lifecycles that stay
implicit on purpose.
"""

from .core import IllegalTransition, Machine, MachineSpec, Transition, is_strict, set_strict
from .specs import (ALL, BUILD, JOB, OFFSPRING, PLAYBACK, RENDER_QUEUE, SCRIPT_RUN, BuildState, JobState, OffspringState,
                    PlaybackState, QueueState, ScriptState)

__all__ = ["IllegalTransition", "Machine", "MachineSpec", "Transition", "is_strict", "set_strict", "ALL", "BUILD", "JOB",
           "OFFSPRING", "PLAYBACK", "RENDER_QUEUE", "SCRIPT_RUN", "BuildState", "JobState", "OffspringState", "PlaybackState",
           "QueueState", "ScriptState"]
