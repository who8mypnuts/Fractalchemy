"""Sampling a fragment's distance estimator on a voxel grid with the GPU — the first half of *Export mesh…*.

The **probe program** is the translated fragment shader with its `main` renamed away and a generated `main`
appended: every pixel of an `res × (res · k)` RGBA32F target is one voxel of `k` consecutive z-slices, and the
shader writes `DE(p)` into red (after `init()` when the fragment `#define providesInit`) and, when it
`#define providesColor`, `baseColor(p, n)` into green / blue / alpha with `n` from a central-difference gradient of
the DE. The user's uniform values and textures are uploaded exactly as for a render, so the probe sees the same
fractal as the viewport. `k` slices per draw keeps the number of read-backs small; a coarse pass (`fit_bounds`)
can shrink the sampling box to where the fractal actually is.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Callable

import numpy as np

from ..glsl_compat import ModernSource
from .uniforms import upload_values

RE_MAIN = re.compile(r"\bvoid\s+main\s*\(")
RE_DE = re.compile(r"\bfloat\s+DE\s*\(\s*(?:in\s+)?vec3\b")
RE_PROVIDES_COLOR = re.compile(r"^\s*#\s*define\s+providesColor\b", re.MULTILINE)
MAX_TARGET_SIDE = 4096
Progress = Callable[[float, str], None]
Cancelled = Callable[[], bool]

PROBE_MAIN = """
uniform vec3 probeOrigin;
uniform vec3 probeU;
uniform vec3 probeV;
uniform vec3 probeW;
uniform float probeStep;
uniform int probeRes;
uniform int probeFirstSlice;
uniform int probeWantColor;
float probeDE(vec3 p) {
#ifdef providesInit
    init();
#endif
    return DE(p);
}
void main() {
    ivec2 pix = ivec2(gl_FragCoord.xy);
    int row = pix.y / probeRes;
    vec3 p = probeOrigin + float(pix.x) * probeU + float(pix.y - row * probeRes) * probeV + float(probeFirstSlice + row) * probeW;
    float d = probeDE(p);
    vec3 c = vec3(0.0);
#ifdef providesColor
    if (probeWantColor != 0) {
        vec3 e = vec3(probeStep * 0.5, 0.0, 0.0);
        vec3 n = normalize(vec3(probeDE(p + e.xyy) - probeDE(p - e.xyy), probeDE(p + e.yxy) - probeDE(p - e.yxy),
                                probeDE(p + e.yyx) - probeDE(p - e.yyx)) + 1e-20);
        c = baseColor(p, n);
    }
#endif
    gl_FragColor = vec4(d, c);
}
"""


def has_distance_estimator(modern: ModernSource) -> bool:
    """True when the translated fragment defines `float DE(vec3)`."""
    return RE_DE.search(modern.fragment) is not None


def provides_color(modern: ModernSource) -> bool:
    """True when the fragment `#define providesColor` (so `baseColor` exists)."""
    return RE_PROVIDES_COLOR.search(modern.fragment) is not None


def probe_source(modern: ModernSource) -> ModernSource:
    """The probe program: `main` renamed, the probe `main` appended (the line map keeps the original lines)."""
    renamed, count = RE_MAIN.subn("void fractalchemy_original_main(", modern.fragment)
    fragment = renamed + PROBE_MAIN
    line_map = modern.fragment_map.copy()
    line_map.origins.extend([None] * PROBE_MAIN.count("\n"))
    return replace(modern, fragment=fragment, fragment_map=line_map, notes=[*modern.notes, f"probe: {count} main() renamed"])


@dataclass(frozen=True)
class Bounds:
    """An axis-aligned sampling box.

    Attributes:
        center: Its middle.
        size: Its side (a cube).
    """
    center: tuple[float, float, float] = (0.0, 0.0, 0.0)
    size: float = 2.5

    @property
    def origin(self) -> tuple[float, float, float]:
        """The corner of voxel (0, 0, 0)."""
        return tuple(c - self.size / 2.0 for c in self.center)

    def spacing(self, resolution: int) -> float:
        return self.size / max(1, resolution)


@dataclass
class ProbeResult:
    """What a probe produced.

    Attributes:
        distance: `(nx, ny, nz)` float32 DE values at the voxel centres.
        color: `(nx, ny, nz, 3)` float32 colours, or None.
        bounds: The box sampled.
        spacing: Voxel side in world units.
    """
    distance: np.ndarray
    color: np.ndarray | None
    bounds: Bounds
    spacing: float

    @property
    def origin(self) -> np.ndarray:
        return np.asarray(self.bounds.origin, dtype=np.float64)


class DistanceProbe:
    """Samples a fragment's DE on the GPU (see the module docstring).

    Args:
        engine: A `FragEngine` owned by the calling thread.
        request: The fragment program and its values (a `FragRequest`).

    Raises:
        ValueError: When the fragment has no `float DE(vec3)`.
        FragBuildError: When the probe program fails to compile.
    """

    def __init__(self, engine, request):
        if not has_distance_estimator(request.modern):
            raise ValueError("the fragment has no `float DE(vec3 p)` — only DE-based fragments can be meshed")
        self.engine = engine
        self.request = request
        self.colors_available = provides_color(request.modern)
        self.program, _cached = engine.build(probe_source(request.modern))
        self._fbo = None
        self._shape: tuple[int, int] | None = None

    def sample(self, bounds: Bounds, resolution: int, colors: bool = False, progress: Progress | None = None,
               cancelled: Cancelled | None = None) -> ProbeResult | None:
        """Every voxel centre of `bounds` at `resolution`³ (None when cancelled)."""
        res = max(2, int(resolution))
        want_color = colors and self.colors_available
        per_draw = max(1, min(res, MAX_TARGET_SIDE // res))
        distance = np.empty((res, res, res), dtype=np.float32)
        color = np.empty((res, res, res, 3), dtype=np.float32) if want_color else None
        spacing = bounds.spacing(res)
        origin = tuple(o + spacing / 2.0 for o in bounds.origin)    # voxel centres
        for first in range(0, res, per_draw):
            if cancelled is not None and cancelled():
                return None
            count = min(per_draw, res - first)
            axes = ((spacing, 0.0, 0.0), (0.0, spacing, 0.0), (0.0, 0.0, spacing))
            block = self._draw(origin, axes, spacing, res, first, count, want_color)
            # block rows: slice-major then y; pixel x is the voxel's x → arrays indexed [x, y, z]
            block = block.reshape(count, res, res, 4)               # (slice, y, x, channel)
            distance[:, :, first:first + count] = np.transpose(block[..., 0], (2, 1, 0))
            if color is not None:
                color[:, :, first:first + count, :] = np.transpose(block[..., 1:4], (2, 1, 0, 3))
            if progress is not None:
                progress((first + count) / res, f"Sampling the distance estimator ({first + count}/{res} slices)")
        return ProbeResult(distance, color, bounds, spacing)

    def sample_plane(self, centre, u, v, size: float, resolution: int) -> np.ndarray:
        """`(resolution, resolution)` DE values on the plane through `centre` spanned by unit vectors `u`, `v` (`size` wide);
        row 0 is the −v edge, column 0 the −u edge."""
        res = max(2, int(resolution))
        step = size / res
        centre, u, v = (np.asarray(x, dtype=np.float64) for x in (centre, u, v))
        origin = centre - (u + v) * (size / 2.0 - step / 2.0)
        axes = (tuple(u * step), tuple(v * step), (0.0, 0.0, 0.0))
        block = self._draw(tuple(origin), axes, step, res, 0, 1, False)
        return block.reshape(res, res, 4)[..., 0].copy()

    def fit_bounds(self, bounds: Bounds, threshold: float, coarse: int = 48, margin: float = 0.08) -> Bounds:
        """Shrink `bounds` to the box where the DE is below `threshold` (+ a margin); unchanged when nothing is found."""
        result = self.sample(bounds, coarse)
        if result is None:
            return bounds
        hits = np.argwhere(result.distance <= threshold)
        if hits.shape[0] == 0:
            return bounds
        lo = result.origin + (hits.min(axis=0)) * result.spacing
        hi = result.origin + (hits.max(axis=0) + 1.0) * result.spacing
        size = float((hi - lo).max()) * (1.0 + 2.0 * margin)
        center = tuple(float(v) for v in (lo + hi) / 2.0)
        return Bounds(center, max(size, result.spacing * 2.0))

    def close(self) -> None:
        if self._fbo is not None:
            self._fbo.release()
            self._fbo = None

    # --- internals -------------------------------------------------------------------------------------------------------
    def _target(self, width: int, height: int):
        if self._shape != (width, height):
            self.close()
            self._fbo = self.engine.ctx.simple_framebuffer((width, height), components=4, dtype="f4")
            self._shape = (width, height)
        return self._fbo

    def _draw(self, origin, axes, spacing: float, res: int, first: int, count: int, want_color: bool) -> np.ndarray:
        ctx = self.engine.ctx
        fbo = self._target(res, res * count)
        fbo.use()
        ctx.viewport = (0, 0, res, res * count)
        ctx.disable(ctx.DEPTH_TEST)
        self.engine.bind_textures(self.program, self.request)
        upload_values(self.program, self.request.values)
        self.program.set("probeOrigin", tuple(float(v) for v in origin))
        for name, axis in zip(("probeU", "probeV", "probeW"), axes):
            self.program.set(name, tuple(float(v) for v in axis))
        self.program.set("probeStep", float(spacing))
        self.program.set("probeRes", int(res))
        self.program.set("probeFirstSlice", int(first))
        self.program.set("probeWantColor", 1 if want_color else 0)
        self.program.render()
        data = np.frombuffer(fbo.read(components=4, dtype="f4"), dtype=np.float32)
        return np.nan_to_num(data, nan=1e9, posinf=1e9, neginf=-1e9)


__all__ = ["Bounds", "DistanceProbe", "ProbeResult", "has_distance_estimator", "provides_color", "probe_source"]
