"""Engine-side chores run on the render thread through the service's job protocol.

The OpenGL context lives on the render service's thread, so anything that touches the engine — *Test GLSL
versions* (compile the fragment at every version the driver offers), *Clear texture cache* — is submitted like a
render: a `FragTask` payload whose `run(engine)` the `FragTaskJob` executes in its single pass. The result travels
back in `RenderStats.facts` of the `job_finished` signal; an exception becomes `job_failed`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import numpy as np

from ...render.settings import RenderStats

TASK_PRIORITY = -2  # ahead of everything: the chores are quick and the user asked for them


@dataclass(frozen=True)
class FragTask:
    """Work for the engine.

    Attributes:
        name: For the log.
        run: `run(engine) -> result`; the result ends up in the finished stats' `facts`.
    """
    name: str
    run: Callable[[object], object]

    def copy(self) -> "FragTask":
        """The service copies payloads; a task is immutable."""
        return self


class FragTaskJob:
    """The service's job protocol around one `FragTask`: one pass, a blank 1×1 image, the result in `stats.facts`."""

    def __init__(self, engine, task: FragTask, settings=None):
        self.engine = engine
        self.task = task
        self.stats = RenderStats(engine.name, 0, 1, 0, 0, 0.0, 1, 1)

    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        self.stats.facts = self.task.run(self.engine)
        self.stats.passes_done = 1
        return np.zeros((1, 1, 4), dtype=np.uint8)

    def close(self) -> None:
        return None


def check_versions(source, mode: str, versions: list[int], has_fp64: bool) -> Callable[[object], list[tuple[int, list]]]:
    """A task body compiling `source` at each of `versions`: `[(version, diagnostics)]` (empty diagnostics = compiled)."""
    from ..glsl_compat import CompatError, CompatOptions, modernise

    def run(engine) -> list[tuple[int, list]]:
        results = []
        for version in versions:
            try:
                modern = modernise(source, CompatOptions(mode, engine.capabilities.glsl_version, has_fp64, force_version=version))
            except (CompatError, ValueError) as exc:
                results.append((version, [str(exc)]))
                continue
            results.append((version, engine.check(modern)))
        return results

    return run


def clear_textures(engine) -> str:
    """A task body: drop every cached texture (they reload on the next subframe)."""
    engine.textures.clear()
    return "texture cache cleared"


__all__ = ["FragTask", "FragTaskJob", "TASK_PRIORITY", "check_versions", "clear_textures"]
