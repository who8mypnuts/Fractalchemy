"""Uploading the parameter values — by the *program's* uniform type, as FragM does, not by the annotation's.

An `int` annotation on a `float` uniform still works, a `bool` goes up as an int, a vector value is cut or padded to
the uniform's dimension, a double goes up as a double. Uniforms the compiler removed are skipped and reported as
unused so the panel can hide their widgets. The special uniforms (`pixelSize`, `subframe`, `time`, `backbuffer`,
`frontbuffer`, `projectionMatrix`) are set by the job every subframe; the tile transform is FragM's `renderTile`
matrix.
"""

from __future__ import annotations

import math
from typing import Any

import numpy as np

from .program import Program, UniformInfo

IDENTITY = tuple(float(v) for v in np.eye(4, dtype=np.float32).T.flatten())


def coerce(info: UniformInfo, value: Any) -> Any:
    """`value` in the shape moderngl expects for `info` (scalars for dimension 1, tuples otherwise)."""
    kind = info.scalar_kind
    items = list(value) if isinstance(value, (tuple, list, np.ndarray)) else [value]
    if info.dimension == 1 and info.array_length == 1:
        return _scalar(kind, items[0] if items else 0)
    wanted = info.dimension * info.array_length
    items = (items + [0] * wanted)[:wanted]
    return tuple(_scalar(kind, v) for v in items)


def _scalar(kind: str, v: Any):
    if kind in ("i", "I"):
        return int(v) if not isinstance(v, bool) else int(v)
    value = float(v)
    return value if math.isfinite(value) else 0.0


def upload_values(program: Program, values: dict[str, Any], skip: tuple[str, ...] = ()) -> list[str]:
    """Set every value uniform the program has; returns the names that were set."""
    done = []
    for name, value in values.items():
        info = program.uniforms.get(name)
        if info is None or info.sampler or name in skip:
            continue
        try:
            program.program[name].value = coerce(info, value)
            done.append(name)
        except (TypeError, ValueError, OverflowError):
            continue
    return done


def unused_names(program: Program, names: list[str]) -> list[str]:
    """Parameters the compiler optimised out of `program` (FragM hides their widgets unless locked)."""
    return [n for n in names if n not in program.uniforms]


def set_special(program: Program, width: int, height: int, subframe: int, time: float, projection: tuple[float, ...]) -> None:
    """The per-subframe built-ins (`backbuffer` / `frontbuffer` are bound to unit 0 by the job)."""
    program.set("pixelSize", (1.0 / max(width, 1), 1.0 / max(height, 1)))
    program.set("globalPixelSize", (1.0 / max(width, 1), 1.0 / max(height, 1)))
    program.set("subframe", int(subframe))
    program.set("time", float(time))
    program.set("projectionMatrix", projection)
    program.set("backbuffer", 0)
    program.set("frontbuffer", 0)


def tile_projection(index: int, tiles: int, padding: float) -> tuple[float, ...]:
    """FragM's tile matrix, column-major: `translate(x·2/n, y·2/n, 1) · scale((1+p)/n, (1+p)/n, 1)` for tile `index` of `n × n`."""
    if tiles <= 1:
        return IDENTITY
    x = (index // tiles) - (tiles - 1) / 2.0
    y = (index % tiles) - (tiles - 1) / 2.0
    s = (1.0 + padding) / tiles
    return (s, 0.0, 0.0, 0.0, 0.0, s, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, x * 2.0 / tiles, y * 2.0 / tiles, 1.0, 1.0)


__all__ = ["coerce", "upload_values", "unused_names", "set_special", "tile_projection", "IDENTITY"]
