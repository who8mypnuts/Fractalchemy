"""Running one script on many fractals (Qt-free): the core of the *Run Script on Many Fractals* window.

`apply_to_flames(spec, flames, stop, on_each)` runs the script once per flame, restricted (no prompts, messages,
`update()` or files — a batch must run unattended and must not write anything but its own output), and reports each
outcome through `on_each(BatchItem)`. The caller writes the results; the originals are never touched.

Seeds: `same` gives every flame the same random numbers (a deterministic filter), `per flame` a fresh seed each
(derived from the batch seed, so a batch repeats exactly). Names: `{name}` is the source flame's name, `{script}` the
script's, `{n}` the 1-based position.
"""

from __future__ import annotations

import random
import threading
from dataclasses import dataclass, field
from typing import Callable, Iterable

from ..fractal.scene import Flame
from .runner import run_script

BATCH_RESTRICTION = "when running on many fractals"
SEED_SAME, SEED_PER_FLAME = "same", "per flame"
NAME_PATTERNS = ("{name}", "{name} · {script}", "{script} {n}")


@dataclass(frozen=True)
class BatchSpec:
    """What to run and how.

    Attributes:
        code: The script.
        script_name: Its name (for `{script}` in names and for the report).
        parameters: Values for its `param()` declarations.
        seed: The batch seed.
        seed_policy: `same` or `per flame`.
        name_pattern: How results are named (`{name}`, `{script}`, `{n}`).
        stop_on_error: Stop at the first failing flame (else skip it and go on).
    """
    code: str
    script_name: str = "script"
    parameters: dict = field(default_factory=dict)
    seed: int = 0
    seed_policy: str = SEED_PER_FLAME
    name_pattern: str = "{name}"
    stop_on_error: bool = False


@dataclass
class BatchItem:
    """The outcome for one source flame."""
    index: int
    source_name: str
    flame: Flame | None
    error: str = ""
    unstable: bool = False

    @property
    def ok(self) -> bool:
        return self.flame is not None and not self.error


@dataclass
class BatchReport:
    items: list[BatchItem] = field(default_factory=list)
    stopped: bool = False

    @property
    def succeeded(self) -> int:
        return sum(1 for item in self.items if item.ok)

    @property
    def failed(self) -> int:
        return sum(1 for item in self.items if not item.ok)


def result_name(pattern: str, source: str, script: str, n: int) -> str:
    try:
        return pattern.format(name=source, script=script, n=n) or source
    except (KeyError, IndexError, ValueError):
        return source


def apply_to_flames(spec: BatchSpec, flames: Iterable[Flame], stop: threading.Event | None = None,
                    on_each: Callable[[BatchItem], None] | None = None, check: Callable[[Flame], bool] | None = None) -> BatchReport:
    """Run the script on every flame (see the module docstring); `check(flame)` flags unstable results."""
    stop = stop or threading.Event()
    seeds = random.Random(spec.seed)
    report = BatchReport()
    for index, source in enumerate(flames):
        if stop.is_set():
            report.stopped = True
            break
        seed = spec.seed if spec.seed_policy == SEED_SAME else seeds.getrandbits(32)
        result = run_script(spec.code, source, None, stop, seed=seed, parameters=spec.parameters, restricted=BATCH_RESTRICTION)
        if stop.is_set() and result.user_stopped:
            report.stopped = True
            break
        if not result.ok or result.refused or result.flame is None:
            error = result.refused or (str(result.error) if result.error is not None else "no result")
            item = BatchItem(index, source.name, None, error)
        else:
            flame = result.flame
            flame.name = result_name(spec.name_pattern, source.name, spec.script_name, index + 1)
            item = BatchItem(index, source.name, flame, "", check is not None and not check(flame))
        report.items.append(item)
        if on_each is not None:
            on_each(item)
        if not item.ok and spec.stop_on_error:
            report.stopped = True
            break
    return report


__all__ = ["BatchSpec", "BatchItem", "BatchReport", "apply_to_flames", "result_name", "BATCH_RESTRICTION", "SEED_SAME",
           "SEED_PER_FLAME", "NAME_PATTERNS"]
