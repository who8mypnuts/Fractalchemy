"""`.cube` colour look-up tables (Adobe / Resolve / IWLTBAP …) as a 3D array the grading stage uploads as a 3D texture.

A `.cube` is a text file: `TITLE`, `LUT_3D_SIZE n` (or `LUT_1D_SIZE n`), optional `DOMAIN_MIN` / `DOMAIN_MAX`, then
`n³` (or `n`) RGB triples with red varying fastest. A 1D LUT is expanded to a small 3D one so the shader has a
single code path. Values are kept as float32 in `[0, 1]` of the domain.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

MAX_SIZE = 65


class LutError(ValueError):
    """The file is not a LUT this reader understands."""


@dataclass(frozen=True)
class Lut:
    """A 3D LUT: `table[b, g, r]` is the RGB output for input `(r, g, b)` (texture layout: blue is the slowest axis).

    Attributes:
        size: Samples per axis.
        table: `(size, size, size, 3)` float32.
        title: The file's `TITLE`, if any.
        domain_min, domain_max: The input range the table covers.
    """
    size: int
    table: np.ndarray
    title: str = ""
    domain_min: tuple[float, float, float] = (0.0, 0.0, 0.0)
    domain_max: tuple[float, float, float] = (1.0, 1.0, 1.0)

    @property
    def bytes(self) -> bytes:
        """The table as the 3D texture's data (float32 RGB, red fastest, then green, then blue)."""
        return np.ascontiguousarray(self.table, dtype=np.float32).tobytes()


def parse_cube(text: str, title: str = "") -> Lut:
    """A `Lut` from `.cube` text.

    Raises:
        LutError: Missing size, wrong number of entries, or unreadable numbers.
    """
    size_3d = size_1d = 0
    domain_min, domain_max = (0.0, 0.0, 0.0), (1.0, 1.0, 1.0)
    rows: list[tuple[float, float, float]] = []
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        upper = line.upper()
        if upper.startswith("TITLE"):
            title = line[5:].strip().strip('"')
        elif upper.startswith("LUT_3D_SIZE"):
            size_3d = int(line.split()[1])
        elif upper.startswith("LUT_1D_SIZE"):
            size_1d = int(line.split()[1])
        elif upper.startswith("DOMAIN_MIN"):
            domain_min = tuple(float(v) for v in line.split()[1:4])
        elif upper.startswith("DOMAIN_MAX"):
            domain_max = tuple(float(v) for v in line.split()[1:4])
        elif upper.startswith(("LUT_3D_INPUT_RANGE", "LUT_1D_INPUT_RANGE")):
            lo, hi = (float(v) for v in line.split()[1:3])
            domain_min, domain_max = (lo, lo, lo), (hi, hi, hi)
        else:
            parts = line.split()
            if len(parts) < 3:
                continue
            try:
                rows.append((float(parts[0]), float(parts[1]), float(parts[2])))
            except ValueError as exc:
                raise LutError(f"unreadable LUT entry: {line!r}") from exc
    if size_3d:
        if size_3d > MAX_SIZE or len(rows) != size_3d ** 3:
            raise LutError(f"a LUT_3D_SIZE {size_3d} table needs {size_3d ** 3} entries (found {len(rows)}; at most {MAX_SIZE} a side)")
        table = np.asarray(rows, dtype=np.float32).reshape(size_3d, size_3d, size_3d, 3)     # red fastest → [b, g, r]
        return Lut(size_3d, table, title, domain_min, domain_max)
    if size_1d:
        if len(rows) != size_1d:
            raise LutError(f"a LUT_1D_SIZE {size_1d} table needs {size_1d} entries (found {len(rows)})")
        return Lut(*_expand_1d(np.asarray(rows, dtype=np.float32)), title, domain_min, domain_max)
    raise LutError("no LUT_3D_SIZE or LUT_1D_SIZE line")


def _expand_1d(curve: np.ndarray) -> tuple[int, np.ndarray]:
    """A per-channel curve as an equivalent 3D table (at most 33 a side, resampled linearly)."""
    size = min(33, len(curve))
    x = np.linspace(0.0, 1.0, size)
    positions = np.linspace(0.0, 1.0, len(curve))
    channels = [np.interp(x, positions, curve[:, c]) for c in range(3)]
    b, g, r = np.meshgrid(channels[2], channels[1], channels[0], indexing="ij")
    return size, np.stack([r, g, b], axis=-1).astype(np.float32)


def read_cube(path: Path) -> Lut:
    """Read a `.cube` file (`LutError` for a malformed one, `OSError` for an unreadable one)."""
    path = Path(path)
    return parse_cube(path.read_text(encoding="utf-8", errors="replace"), path.stem)


def identity_lut(size: int = 2) -> Lut:
    """The table that changes nothing (for tests and as a placeholder)."""
    x = np.linspace(0.0, 1.0, size, dtype=np.float32)
    b, g, r = np.meshgrid(x, x, x, indexing="ij")
    return Lut(size, np.stack([r, g, b], axis=-1).astype(np.float32), "identity")


__all__ = ["Lut", "LutError", "parse_cube", "read_cube", "identity_lut", "MAX_SIZE"]
