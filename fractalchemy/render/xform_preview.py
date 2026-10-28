"""Apophysis's *variation preview*: a grid of points sent through one transform, for the editor canvas.

The editor draws the result as dots in the transform's colour, so the effect of the variations (with
their parameters, the affines and the xaos-independent part of the transform) can be seen directly on
the triangle canvas. Apophysis's `showVarPreview` code: a square grid spanning ±`range` with
`density · 5` points per unit, each mapped through the transform `depth` times.
"""

from __future__ import annotations

import numpy as np

from ..fractal.scene import XForm
from .compiled import CompiledXForm
from .cpu_engine import apply_xform

POINTS_PER_UNIT = 5          # Apophysis: density · 5 points per unit
MAX_POINTS = 300_000         # safety cap on the grid (range 5, density 5 is 251² = 63 001 points)
RESET_LIMIT = 1e6


def preview_grid(range_units: int, density: int) -> tuple[np.ndarray, np.ndarray]:
    """The input grid: x and y arrays of the points in [−range, range]² at `density · 5` per unit."""
    range_units, density = max(1, int(range_units)), max(1, int(density))
    per_unit = density * POINTS_PER_UNIT
    n = range_units * per_unit
    side = np.arange(-n, n + 1) / per_unit
    if side.size * side.size > MAX_POINTS:
        side = side[:: int(np.ceil(side.size / np.sqrt(MAX_POINTS)))]
    x, y = np.meshgrid(side, side)
    return x.ravel(), y.ravel()


def variation_preview(xform: XForm, range_units: int = 2, density: int = 2, depth: int = 1,
                      seed: int = 7) -> np.ndarray:
    """Fractal-space points `(N, 2)` of the grid after `depth` applications of `xform` (non-finite ones dropped).

    Random variations (`pre_blur`, blurs, …) use a fixed seed so the picture is stable while editing.
    """
    x, y = preview_grid(range_units, density)
    z, c = np.zeros_like(x), np.zeros_like(x)
    compiled = CompiledXForm.build(xform)
    rng = np.random.default_rng(seed)
    with np.errstate(all="ignore"):
        for _ in range(max(1, int(depth))):
            x, y, z, c = apply_xform(compiled, x, y, z, c, rng)
    keep = np.isfinite(x) & np.isfinite(y) & (np.abs(x) < RESET_LIMIT) & (np.abs(y) < RESET_LIMIT)
    return np.column_stack([x[keep], y[keep]])


__all__ = ["variation_preview", "preview_grid", "POINTS_PER_UNIT"]
