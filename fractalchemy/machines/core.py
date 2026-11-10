"""Explicit state machines: named states, a declared transition table, observable changes. Pure Python, no Qt.

A lifecycle that lives in scattered flags (`self.job is None`, `self._busy`, a button's enabled state …) is an *implicit*
state machine: nothing says which combinations are legal, so illegal ones happen (a render paused after Stop waited
forever). A `MachineSpec` declares the states and every allowed `(state, event) → state` step once; a `Machine` is one
running instance of it:

    JOB = MachineSpec("Render job", JobState, JobState.IDLE, {
        (JobState.IDLE, "start"): JobState.RUNNING,
        (JobState.RUNNING, "pause"): JobState.PAUSED, …})
    machine = JOB.new("Render Image window")
    machine.can("pause")          # what the UI enables
    machine.fire("start")         # True; machine.state is JobState.RUNNING
    machine.on_change(refresh)    # refresh(transition) after every step

States are `StrEnum`s, so `machine.state == "running"` works too (handy in tests and for agents reading logs).

**Illegal events** (an event the current state has no step for) are refused: `fire` logs a warning and returns False, so
the application never crashes over one. Under `set_strict(True)` — the test-suite turns it on in `conftest.py` — they
raise `IllegalTransition` instead, so a wrong sequence fails the tests loudly rather than being papered over. Owners
that *expect* an event may not apply use `fire_if` (fire only when allowed; no warning).

Every machine keeps a short `history` of its steps (time, from, event, to, note) for debugging, and every spec can
describe itself (`table()`, `mermaid()`) — `tools/state_machines.py` writes `docs/state-machines.md` from them.
"""

from __future__ import annotations

import logging
import time
from collections import deque
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Callable, Mapping

log = logging.getLogger(__name__)
HISTORY = 32                    # steps kept per machine
_strict = False


def set_strict(strict: bool) -> None:
    """Raise `IllegalTransition` on illegal events (tests) instead of logging and refusing them (the application)."""
    global _strict
    _strict = bool(strict)


def is_strict() -> bool:
    """Whether illegal events raise."""
    return _strict


class IllegalTransition(RuntimeError):
    """An event the machine's current state has no step for (raised in strict mode only)."""


@dataclass(frozen=True)
class Transition:
    """One step a machine took."""
    at: float
    before: StrEnum
    event: str
    after: StrEnum
    note: str = ""


@dataclass(frozen=True)
class MachineSpec:
    """A state machine's definition: its states, where it starts, and every allowed step.

    Attributes:
        name: Shown in the docs and in log messages (`Render job`).
        states: The `StrEnum` of states; each member's docstring-like meaning comes from `meanings`.
        initial: The state a new machine starts in.
        transitions: `(state, event) → next state`. Anything not listed is illegal.
        meanings: state → one line saying what the state means (the docs and `describe()` show it).
        owner: Where the machine lives (module / class), for the docs.
        doc: A paragraph on what the machine models.
    """
    name: str
    states: type[StrEnum]
    initial: StrEnum
    transitions: Mapping[tuple[StrEnum, str], StrEnum]
    meanings: Mapping[StrEnum, str] = field(default_factory=dict)
    owner: str = ""
    doc: str = ""

    def __post_init__(self) -> None:
        mentioned = [state for (source, _event), target in self.transitions.items() for state in (source, target)]
        problems = [f"{state!r} is not a {self.states.__name__}" for state in mentioned if not isinstance(state, self.states)]
        if not isinstance(self.initial, self.states):
            problems.append(f"initial {self.initial!r} is not a {self.states.__name__}")
        unreachable = set(self.states) - self.reachable()
        if unreachable:
            problems.append(f"unreachable states: {sorted(unreachable)}")
        if problems:
            raise ValueError(f"state machine {self.name!r}: " + "; ".join(problems))

    def new(self, label: str = "") -> "Machine":
        """A machine of this spec in its initial state (`label` names it in log messages)."""
        return Machine(self, label)

    def events(self) -> list[str]:
        """Every event name, in declaration order."""
        seen: dict[str, None] = {}
        for (_state, event) in self.transitions:
            seen.setdefault(event, None)
        return list(seen)

    def reachable(self) -> set[StrEnum]:
        """The states reachable from the initial one."""
        found, frontier = {self.initial}, [self.initial]
        while frontier:
            state = frontier.pop()
            for (source, _event), target in self.transitions.items():
                if source == state and target not in found:
                    found.add(target)
                    frontier.append(target)
        return found

    def table(self) -> list[tuple[str, str, str]]:
        """(state, event, next state) rows in declaration order."""
        return [(str(s), e, str(t)) for (s, e), t in self.transitions.items()]

    def mermaid(self) -> str:
        """The machine as a Mermaid state diagram (for the docs)."""
        lines = ["stateDiagram-v2", f"    [*] --> {self.initial}"]
        lines += [f"    {s} --> {t}: {e}" for (s, e), t in self.transitions.items()]
        return "\n".join(lines)


class Machine:
    """One running instance of a `MachineSpec` (see the module docstring)."""

    def __init__(self, spec: MachineSpec, label: str = ""):
        self.spec = spec
        self.label = label or spec.name
        self._state = spec.initial
        self._listeners: list[Callable[[Transition], None]] = []
        self.history: deque[Transition] = deque(maxlen=HISTORY)

    @property
    def state(self) -> StrEnum:
        """The current state."""
        return self._state

    def is_in(self, *states: StrEnum) -> bool:
        """Whether the current state is one of `states`."""
        return self._state in states

    def can(self, event: str) -> bool:
        """Whether `event` is allowed in the current state."""
        return (self._state, event) in self.spec.transitions

    def allowed(self) -> list[str]:
        """The events the current state accepts."""
        return [e for (s, e) in self.spec.transitions if s == self._state]

    def on_change(self, listener: Callable[[Transition], None]) -> None:
        """Call `listener(transition)` after every step (self-loops included)."""
        self._listeners.append(listener)

    def fire(self, event: str, note: str = "") -> bool:
        """Take the step `event` leads to from the current state; False (and a warning) when it is illegal — or
        `IllegalTransition` in strict mode."""
        target = self.spec.transitions.get((self._state, event))
        if target is None:
            message = (f"{self.label}: '{event}' is not allowed in state '{self._state}' "
                       f"(allowed: {', '.join(self.allowed()) or 'nothing'})")
            if _strict:
                raise IllegalTransition(message)
            log.warning(message)
            return False
        step = Transition(time.monotonic(), self._state, event, target, note)
        self._state = target
        self.history.append(step)
        for listener in list(self._listeners):
            listener(step)
        return True

    def fire_if(self, event: str, note: str = "") -> bool:
        """Fire `event` only when the current state allows it (no warning otherwise): for events that are legitimately
        irrelevant in some states."""
        return self.can(event) and self.fire(event, note)

    def describe(self) -> str:
        """One line for logs and debugging: label, state, what the state means, what it accepts."""
        meaning = self.spec.meanings.get(self._state, "")
        return f"{self.label}: {self._state}" + (f" — {meaning}" if meaning else "") + f" [accepts: {', '.join(self.allowed()) or 'nothing'}]"

    def __repr__(self) -> str:
        return f"<Machine {self.label!r} state={self._state!s}>"


__all__ = ["MachineSpec", "Machine", "Transition", "IllegalTransition", "set_strict", "is_strict", "HISTORY"]
