"""Running a parameterised script many times: variations for the explorer grid, sweeps for animation (Qt-free).

* `vary(specs, values, seed, rng, options)` — values near (or anywhere within the ranges of) the current ones, for the
  Mutate & Breed window's *Explore script* tab. Bounded numbers move by a Gaussian step (sigma = spread × range / 4),
  unbounded ones relatively, integers always move when the spread is above zero, check boxes flip and dropdowns change
  with a probability of spread / 2 and spread; text never changes. Locked parameters keep their value; `vary_seed`
  gives each variation new random numbers too.
* `explore(...)` — runs the script once per variation, restricted (no side effects), and returns the flames with
  their values, seed and a note of what changed; blow-ups are flagged.
* `sweep(spec, start, end, count, easing)` — the values of an animated parameter (*Animate…* in the Parameters tab);
  integer and dropdown parameters step through each distinct value.
"""

from __future__ import annotations

import math
import random
import threading
from dataclasses import dataclass, field
from typing import Any, Callable

from ..fractal.scene import Flame
from .parameters import ParamSpec, coerce
from .runner import run_script

EXPLORE_RESTRICTION = "in the explorer grid"
MODES = ("around", "anywhere", "seeds")


@dataclass(frozen=True)
class ExploreOptions:
    """How far the explorer strays.

    Attributes:
        spread: 0 (barely) .. 1 (wildly).
        mode: `around` the current values, `anywhere` within the ranges, or `seeds` (new random numbers only).
        locked: Parameters that keep their value.
        vary_seed: Give every variation new random numbers as well.
    """
    spread: float = 0.35
    mode: str = "around"
    locked: frozenset = frozenset()
    vary_seed: bool = False


@dataclass
class Variant:
    """One set of values (and a seed) to run, with a note of what differs from the current ones."""
    values: dict[str, Any]
    seed: int
    notes: list[str] = field(default_factory=list)


@dataclass
class ExploreResult:
    """A variant and what the script made of it."""
    variant: Variant
    flame: Flame | None
    error: str = ""
    unstable: bool = False


def _vary_one(spec: ParamSpec, value: Any, rng: random.Random, options: ExploreOptions) -> Any:
    spread = max(0.0, min(1.0, float(options.spread)))
    if spec.kind == "bool":
        return (not value) if rng.random() < spread / 2 or options.mode == "anywhere" and rng.random() < 0.5 else value
    if spec.kind == "choice":
        if options.mode == "anywhere" or rng.random() < spread:
            others = [c for c in spec.choices if c != value] or list(spec.choices)
            return rng.choice(others)
        return value
    if spec.kind == "text":
        return value
    if options.mode == "anywhere" and spec.bounded:
        new = rng.uniform(spec.minimum, spec.maximum)
    elif spec.bounded:
        new = value + rng.gauss(0.0, spread * (spec.maximum - spec.minimum) / 4.0)
    else:
        new = value + rng.gauss(0.0, spread * (abs(value) + 1.0))
    if spec.kind == "int" and spread > 0 and int(round(new)) == value:
        new = value + rng.choice((-1, 1)) * max(1, int(spec.step or 1))
    return coerce(spec, new)


def vary(specs: list[ParamSpec], values: dict[str, Any], seed: int, count: int, rng: random.Random,
         options: ExploreOptions = ExploreOptions()) -> list[Variant]:
    """`count` variations of `values` (see the module docstring)."""
    variants = []
    for _ in range(count):
        new_values, notes = dict(values), []
        if options.mode != "seeds":
            for spec in specs:
                if spec.name in options.locked:
                    continue
                current = values.get(spec.name, spec.default)
                changed = _vary_one(spec, current, rng, options)
                new_values[spec.name] = changed
                if changed != current:
                    notes.append(f"{spec.name} {_short(changed)}")
        new_seed = seed
        if options.mode == "seeds" or options.vary_seed:
            new_seed = rng.getrandbits(32)
            notes.append("new seed")
        variants.append(Variant(new_values, new_seed, notes))
    return variants


def explore(code: str, snapshot: Flame, specs: list[ParamSpec], values: dict[str, Any], seed: int, count: int, rng_seed: int,
            options: ExploreOptions = ExploreOptions(), stop: threading.Event | None = None,
            check: Callable[[Flame], bool] | None = None) -> list[ExploreResult]:
    """Run `code` on `snapshot` once per variation (restricted: no prompts, messages, updates or files)."""
    rng = random.Random(rng_seed)
    results = []
    for variant in vary(specs, values, seed, count, rng, options):
        if stop is not None and stop.is_set():
            break
        result = run_script(code, snapshot, None, stop, seed=variant.seed, parameters=variant.values, restricted=EXPLORE_RESTRICTION)
        if not result.ok or result.refused:
            error = str(result.error) if result.error is not None else result.refused
            results.append(ExploreResult(variant, None, error))
            continue
        unstable = check is not None and result.flame is not None and not check(result.flame)
        results.append(ExploreResult(variant, result.flame, "", unstable))
    return results


def sweep(spec: ParamSpec, start: Any, end: Any, count: int, easing: str = "linear") -> list[Any]:
    """The values of `spec` at `count` evenly spaced (or eased) keyframes from `start` to `end`; integers and dropdowns
    visit each distinct value between the two ends once."""
    if spec.kind == "choice":
        i, j = spec.choices.index(start), spec.choices.index(end)
        step = 1 if j >= i else -1
        return [spec.choices[k] for k in range(i, j + step, step)]
    if spec.kind == "bool":
        return [bool(start), bool(end)]
    if spec.kind == "int":
        a, b = int(start), int(end)
        step = 1 if b >= a else -1
        return list(range(a, b + step, step))
    count = max(2, int(count))
    values = []
    for k in range(count):
        t = k / (count - 1)
        t = _ease(t, easing)
        values.append(coerce(spec, float(start) + (float(end) - float(start)) * t))
    return values


def _ease(t: float, easing: str) -> float:
    if easing == "in":
        return t * t
    if easing == "out":
        return 1 - (1 - t) * (1 - t)
    if easing == "in-out":
        return 0.5 - 0.5 * math.cos(math.pi * t)
    return t


def _short(value) -> str:
    return f"{value:.3g}" if isinstance(value, float) else str(value)


__all__ = ["ExploreOptions", "Variant", "ExploreResult", "vary", "explore", "sweep", "MODES", "EXPLORE_RESTRICTION"]
