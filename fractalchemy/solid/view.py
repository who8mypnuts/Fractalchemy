"""The solid renderer's camera: the flame's 3D camera as a view transform, a pixel mapping and a depth range.

View space: the flame's points after the camera rotation (`Camera.matrix()`, the Apophysis pitch / yaw matrix)
and the depth offset (`zpos`). x points right, y down (fractal y is down on screen), z **towards the camera** —
a larger `z` is nearer, which is how Apophysis's perspective (`1 − perspective · z`) reads it. The renderer keeps
view-space positions per pixel (normals and lighting are computed in this space, and the lights are placed in
it), and a *depth* `−z` for the z-buffer (smaller = nearer).

`View.project()` then applies the perspective divide and the flat camera's pixel transform, exactly as
`render/projection.py` + `Camera.pixel_transform()` do for the 2D engines, so a solid render frames the
fractal like the main viewport does.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..fractal.scene import Camera
from ..render.filtering import bucket_transform
from ..render.projection import DOF_SCALE

DEPTH_MARGIN = 0.5        # the depth range is widened by this fraction on each side


@dataclass(frozen=True)
class View:
    """The camera for a `width × height` target (supersampled `oversample` times).

    Attributes:
        camera: The flame's camera (rotation, perspective, zpos, dof, centre, zoom).
        width, height: Output size in pixels.
        oversample: Buckets per pixel along each axis (the G-buffer is this much larger).
    """
    camera: Camera
    width: int
    height: int
    oversample: int = 1

    @property
    def size(self) -> tuple[int, int]:
        """The G-buffer's size (the output size times the oversampling)."""
        return self.width * self.oversample, self.height * self.oversample

    @property
    def pixel_transform(self) -> tuple[float, ...]:
        """Affine from the flat camera plane to G-buffer pixels (no gutter: the solid renderer has no spatial filter)."""
        return bucket_transform(self.camera.pixel_transform(self.width, self.height), self.oversample, 0)

    @property
    def matrix(self) -> np.ndarray:
        """The 3×3 camera rotation as `Camera.matrix()` gives it (row = source axis)."""
        return np.array(self.camera.matrix(), dtype=np.float64)

    @property
    def eye(self) -> np.ndarray:
        """Where the camera sits in view space: on the z axis, `1 / perspective` in front (far away when orthographic)."""
        p = self.camera.perspective
        return np.array([0.0, 0.0, 1.0 / p if p > 1e-9 else 1e9])

    def to_view(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """World points → view-space positions (rotated, depth offset applied)."""
        m = self.matrix
        zz = z - self.camera.zpos
        vx = m[0, 0] * x + m[1, 0] * y + m[2, 0] * zz
        vy = m[0, 1] * x + m[1, 1] * y + m[2, 1] * zz
        vz = m[0, 2] * x + m[1, 2] * y + m[2, 2] * zz
        return vx, vy, vz

    def project(self, vx: np.ndarray, vy: np.ndarray, vz: np.ndarray, rng: np.random.Generator | None = None
                ) -> tuple[np.ndarray, np.ndarray]:
        """View-space positions → G-buffer pixel coordinates (floats; depth of field jitters them when `rng` is given)."""
        zr = 1.0 - self.camera.perspective * vz
        px, py = vx, vy
        if self.camera.dof and rng is not None:
            t = rng.random(vx.shape[0]) * 2.0 * np.pi
            dr = rng.random(vx.shape[0]) * DOF_SCALE * self.camera.dof * vz
            px = px + dr * np.cos(t)
            py = py + dr * np.sin(t)
        with np.errstate(divide="ignore", invalid="ignore"):
            fx, fy = px / zr, py / zr
        a, b, c, d, e, f = self.pixel_transform
        return a * fx + c * fy + e, b * fx + d * fy + f

    def view_direction(self, pos: np.ndarray) -> np.ndarray:
        """Unit vectors from view-space positions `(…, 3)` towards the camera."""
        v = self.eye - pos
        norm = np.linalg.norm(v, axis=-1, keepdims=True)
        return v / np.maximum(norm, 1e-12)

    def depth_range(self, vz: np.ndarray) -> tuple[float, float]:
        """A (near, far) pair of depths (`−z`) that encloses these points with a margin — the z-buffer's normalisation
        on the GPU, the scale of fog and of the shadow maps everywhere."""
        finite = vz[np.isfinite(vz)]
        if finite.size == 0:
            return -1.0, 1.0
        depth = -finite
        lo, hi = float(np.percentile(depth, 0.5)), float(np.percentile(depth, 99.5))
        span = max(hi - lo, 1e-3)
        return lo - span * DEPTH_MARGIN, hi + span * DEPTH_MARGIN

    def bounds(self, vx: np.ndarray, vy: np.ndarray, vz: np.ndarray) -> np.ndarray:
        """The view-space bounding box `[[min x, y, z], [max x, y, z]]` of these points (percentile-trimmed)."""
        cols = []
        for v in (vx, vy, vz):
            finite = v[np.isfinite(v)]
            if finite.size == 0:
                cols.append((-1.0, 1.0))
                continue
            lo, hi = float(np.percentile(finite, 0.5)), float(np.percentile(finite, 99.5))
            span = max(hi - lo, 1e-3)
            cols.append((lo - 0.1 * span, hi + 0.1 * span))
        return np.array([[c[0] for c in cols], [c[1] for c in cols]])


def light_direction(altitude: float, azimuth: float) -> np.ndarray:
    """A distant light's unit direction *towards the light* in view space: altitude above the view plane (90° =
    from the camera), azimuth around the view axis (0° = from the right, 90° = from above)."""
    alt, az = np.radians(altitude), np.radians(azimuth)
    return np.array([np.cos(alt) * np.cos(az), -np.cos(alt) * np.sin(az), np.sin(alt)])


__all__ = ["View", "light_direction", "DEPTH_MARGIN"]
