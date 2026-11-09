"""What mutation and breeding produce, and the check every result passes. Pure Python + numpy, no Qt.

An `Offspring` is a flame plus notes saying how it came about ("affine: transform 2 turned 14°", "alternate: 1, 3
from A · 2 from B") — the grid shows them as tool tips. `roll(make, …)` asks `make()` for candidates until one is
*stable* (its attractor neither blows up nor collapses: `random_flame.attractor_bounds`, with a small sample so the
check stays cheap even for slow compiled formulas) and falls back to a gentler candidate when none is.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from .. import config
from .random_flame import attractor_bounds
from .scene import Flame


@dataclass
class Offspring:
    """A mutant or a bred child.

    Attributes:
        flame: The new flame.
        notes: How it differs from its parent(s), one short phrase per change.
    """
    flame: Flame
    notes: list[str] = field(default_factory=list)

    @property
    def description(self) -> str:
        """The notes as one line."""
        return "; ".join(self.notes) or "unchanged"


def is_stable(flame: Flame) -> bool:
    """Whether `flame` renders: some transform has weight, and the attractor neither blows up nor collapses."""
    return flame.renderable() and attractor_bounds(flame, config.MUTATION_CHECK_POINTS, config.MUTATION_CHECK_STEPS) is not None


def roll(make: Callable[[], Offspring], gentle: Callable[[], Offspring], parent: Flame, check: bool = True,
         attempts: int = config.MUTATION_ATTEMPTS) -> Offspring:
    """The first stable candidate of up to `attempts` from `make()`; failing that a stable `gentle()` one; failing
    that a copy of `parent` — each fallback noted. With `check` off the first candidate is taken (tests that do not
    iterate flames)."""
    for _ in range(max(1, attempts)):
        candidate = make()
        if not check or is_stable(candidate.flame):
            return candidate
    candidate = gentle()
    if is_stable(candidate.flame):
        candidate.notes.append("(a gentler variation: the bolder ones blew up)")
        return candidate
    return Offspring(parent.copy(), ["unchanged: every variation tried blew up"])


def normalise_weights(flame: Flame) -> None:
    """Scale the transform weights to sum to 1 (keeps their ratios; nothing to do without positive weights)."""
    total = sum(max(0.0, x.weight) for x in flame.xforms)
    if total > 0:
        for x in flame.xforms:
            x.weight = max(0.0, x.weight) / total


__all__ = ["Offspring", "is_stable", "roll", "normalise_weights"]
