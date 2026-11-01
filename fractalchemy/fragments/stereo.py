"""Stereo pairs, 360° panoramas and render regions — the projection and compositing arithmetic of the final renderer.

FragM renders one eye from one camera; a stereo image is two renders with the eye shifted along the camera's right
vector by half the separation each way, composited afterwards: **anaglyph** (red from the left eye, green and blue
from the right — for red / cyan glasses) or **side by side** (left | right, for VR viewers and 3D displays). A
**360° panorama** uses `3D.frag`'s `EquiRectangular` mode (a 2:1 image whose pixels map to longitude / latitude) and
needs no compositing. A **region** is a crop of the frame rendered at full resolution: FragM's tile matrix (which
already maps one tile's part of the frame onto the whole buffer) is composed with the region's own scale /
translate, so nothing else in the pipeline needs to know.
"""

from __future__ import annotations

import numpy as np

from .gl.uniforms import IDENTITY

STEREO_MODES = ("none", "anaglyph", "sbs")
STEREO_LABELS = {"none": "Mono", "anaglyph": "Anaglyph (red / cyan)", "sbs": "Side by side (left | right)"}
CAMERA_KEYS = ("Eye", "Target", "Up")


def stereo_values(values: dict, separation: float) -> tuple[dict, dict]:
    """`(left, right)` copies of `values` with `Eye` (and `Target`) shifted ∓ / ± half the separation along the camera's right.

    `separation` is a fraction of the eye–target distance (0.03 ≈ a human pair of eyes looking at something two metres
    away); the target shifts with the eye, so both eyes converge at the same depth as before.
    """
    eye, target, up = (np.array(values.get(k, d), dtype=float) for k, d in zip(CAMERA_KEYS, ((0, 0, -10), (0, 0, 0), (0, 1, 0))))
    forward = target - eye
    distance = float(np.linalg.norm(forward))
    if distance < 1e-12:
        return dict(values), dict(values)
    right = np.cross(forward / distance, up)
    norm = float(np.linalg.norm(right))
    right = right / norm if norm > 1e-12 else np.array([1.0, 0.0, 0.0])
    shift = right * (separation * distance * 0.5)
    left, right_values = dict(values), dict(values)
    left["Eye"], left["Target"] = tuple(float(v) for v in eye - shift), tuple(float(v) for v in target - shift)
    right_values["Eye"], right_values["Target"] = tuple(float(v) for v in eye + shift), tuple(float(v) for v in target + shift)
    return left, right_values


def compose_anaglyph(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """Red from the left eye, green and blue from the right (`(H, W, 4)` float arrays in, the same out)."""
    out = right.copy()
    out[..., 0] = left[..., 0]
    out[..., 3] = np.maximum(left[..., 3], right[..., 3])
    return out


def compose_side_by_side(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    """`left | right` in one image twice as wide."""
    return np.concatenate([left, right], axis=1)


def compose(mode: str, left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if mode == "anaglyph":
        return compose_anaglyph(left, right)
    if mode == "sbs":
        return compose_side_by_side(left, right)
    raise ValueError(f"unknown stereo mode {mode!r}")


# --- regions -------------------------------------------------------------------------------------------------------------
def region_projection(region: tuple[float, float, float, float] | None) -> tuple[float, ...]:
    """The column-major matrix mapping the frame's region `(x, y, w, h)` (fractions, y down) onto the whole buffer."""
    if region is None:
        return IDENTITY
    x, y, w, h = (float(v) for v in region)
    w, h = max(1e-6, w), max(1e-6, h)
    cx, cy = 2.0 * (x + w / 2.0) - 1.0, 1.0 - 2.0 * (y + h / 2.0)
    return (w, 0.0, 0.0, 0.0, 0.0, h, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0, cx, cy, 0.0, 1.0)


def compose_projection(outer: tuple[float, ...], inner: tuple[float, ...]) -> tuple[float, ...]:
    """`outer · inner` for FragM's scale-and-translate tile matrices (column-major 4×4 tuples)."""
    a = np.array(outer, dtype=float).reshape(4, 4).T
    b = np.array(inner, dtype=float).reshape(4, 4).T
    return tuple(float(v) for v in (a @ b).T.flatten())


def region_size(region: tuple[float, float, float, float] | None, frame_width: int, frame_height: int) -> tuple[int, int]:
    """The pixel size of `region` cut from a `frame_width × frame_height` frame (the whole frame without a region)."""
    if region is None:
        return frame_width, frame_height
    return max(1, int(round(region[2] * frame_width))), max(1, int(round(region[3] * frame_height)))


__all__ = ["STEREO_MODES", "STEREO_LABELS", "stereo_values", "compose_anaglyph", "compose_side_by_side", "compose", "region_projection",
           "compose_projection", "region_size"]
