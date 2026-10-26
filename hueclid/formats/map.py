"""Fractint / Ultra Fractal `.map` palettes: 256 lines of `R G B` (first line may carry a comment)."""

from __future__ import annotations

import re
from pathlib import Path

from .. import config
from ..model import Gradient
from .base import FormatError, GradientFormat
from .textfile import atomic_write_bytes

_TRIPLE = re.compile(r"^\s*(\d{1,3})\s+(\d{1,3})\s+(\d{1,3})")


class MapFormat(GradientFormat):
    name = "Fractint / UF palette map"
    extensions = (".map",)
    can_save = True
    can_create = True

    def load(self, path: Path) -> list[Gradient]:
        colors = []
        for line in path.read_text(encoding="latin-1").splitlines():
            match = _TRIPLE.match(line)
            if match:
                colors.append(tuple(min(255, int(v)) for v in match.groups()))
        if not colors:
            raise FormatError(f"{path.name} has no 'R G B' lines")
        return [Gradient.from_colors(path.stem, colors)]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        rows = [f"{r:3d} {g:3d} {b:3d}" for r, g, b in gradient.sample(config.FLAME_PALETTE_SIZE)]
        rows[0] += f"  {config.APP_NAME}"
        atomic_write_bytes(path, ("\r\n".join(rows) + "\r\n").encode("latin-1"))
