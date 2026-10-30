"""Capturing the chaos game's points: the orbit as arrays, for meshing.

The solid renderer splats points as it goes and keeps only the nearest per pixel; meshing needs the points
themselves — world positions after the final transform, the palette colour, the transform that produced each.
`capture_points()` runs the same numpy iteration as the CPU engine (`PointPopulation`) on a few threads and
returns a `PointCloud` of about the requested size. A million points of a simple flame takes a second or two; a
formula-heavy one (cellular noise, many small numpy calls) is bound by the interpreter, which is why the default is
one thread — more threads contend for the GIL and come out slower on such flames.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Callable

import numpy as np

from ..fractal.scene import Flame
from ..render.compiled import CompiledFlame
from ..render.cpu_engine import PointPopulation, apply_xform

DEFAULT_POPULATION = 1 << 15
DEFAULT_FUSE = 20
DEFAULT_THREADS = 1


@dataclass
class PointCloud:
    """Captured orbit points.

    Attributes:
        xyz: `(N, 3)` float32 world positions (after the final transform).
        color: `(N,)` uint8 palette index.
        xform: `(N,)` int16 index of the transform that produced the point.
        palette: `(256, 3)` float32 palette in 0..1 (the flame's).
    """
    xyz: np.ndarray
    color: np.ndarray
    xform: np.ndarray
    palette: np.ndarray

    def __len__(self) -> int:
        return int(self.xyz.shape[0])

    @property
    def rgb(self) -> np.ndarray:
        """`(N, 3)` float32 colours."""
        return self.palette[self.color]

    def subset(self, mask: np.ndarray) -> "PointCloud":
        return PointCloud(self.xyz[mask], self.color[mask], self.xform[mask], self.palette)


def capture_points(flame: Flame, count: int, seed: int = 1, threads: int = DEFAULT_THREADS, fuse: int = DEFAULT_FUSE,
                   population: int = DEFAULT_POPULATION, cancelled: Callable[[], bool] | None = None,
                   progress: Callable[[float], None] | None = None) -> PointCloud | None:
    """Run the chaos game and keep about `count` points (None when cancelled).

    Args:
        flame: The fractal (its camera is irrelevant here; world coordinates are kept).
        count: Points wanted (the result has at least this many unless cancelled).
        seed: Random seed (repeatable captures).
        threads: Worker threads, each with its own population.
        fuse: Warm-up iterations before points are kept.
        population: Points per thread iterated in parallel.
        cancelled: Polled between iterations.
        progress: Called with the fraction done.

    Raises:
        ValueError: For a flame with no usable transform.
    """
    compiled = CompiledFlame.build(flame)
    threads = max(1, min(threads, max(1, count // 4096)))
    per_thread = max(1, -(-count // threads))
    cancelled = cancelled or (lambda: False)
    done = [0] * threads

    def work(index: int) -> tuple[list, list, list] | None:
        pop = PointPopulation(compiled, min(population, per_thread), seed * 7919 + index * 104729 + 1, (1, 0, 0, 1, 0, 0), 1, 1)
        pop.fuse(fuse)
        opacities = pop.opacities
        xyz_parts, color_parts, xform_parts = [], [], []
        kept = 0
        while kept < per_thread:
            if cancelled():
                return None
            xi = pop._step()
            x, y, z, c = pop.x, pop.y, pop.z, pop.c
            if compiled.final is not None:
                x, y, z, c = apply_xform(compiled.final, x, y, z, c, pop.rng)
            keep = (opacities[xi] > 0) & np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
            if keep.any():
                xyz_parts.append(np.stack([x[keep], y[keep], z[keep]], axis=1).astype(np.float32))
                color_parts.append(np.clip(c[keep] * 255.0 + 0.5, 0, 255).astype(np.uint8))
                xform_parts.append(xi[keep].astype(np.int16))
                kept += int(keep.sum())
            done[index] = min(kept, per_thread)
            if progress is not None and index == 0:
                progress(min(1.0, sum(done) / max(1, count)))
        return xyz_parts, color_parts, xform_parts

    with ThreadPoolExecutor(max_workers=threads, thread_name_prefix="capture") as pool:
        results = list(pool.map(work, range(threads)))
    if any(r is None for r in results):
        return None
    xyz = np.concatenate([p for r in results for p in r[0]]) if results else np.zeros((0, 3), np.float32)
    color = np.concatenate([p for r in results for p in r[1]]) if results else np.zeros(0, np.uint8)
    xform = np.concatenate([p for r in results for p in r[2]]) if results else np.zeros(0, np.int16)
    if progress is not None:
        progress(1.0)
    return PointCloud(xyz, color, xform, compiled.palette.astype(np.float32))


__all__ = ["PointCloud", "capture_points", "DEFAULT_POPULATION", "DEFAULT_FUSE", "DEFAULT_THREADS"]
