"""Camera paths through `KeyFrame.nnnn` presets — FragM's `QtSpline` (a Catmull-Rom spline) made Qt-free.

Each keyframe preset holds `Eye`, `Target` and `Up`; with two or more of them three splines run through the
control points and the camera follows them over the animation's frames. The basis is Catmull-Rom
(`½·[−1 2 −1 0; 3 −5 0 2; −3 4 1 0; 1 −1 0 0]`), the parameter step is FragM's "fudge" that lands the last frame
on the last control point (or, looping, wraps back to the first), and the end points are clamped (or wrapped).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .parameters import parse_numbers
from .presets import is_keyframe, keyframe_index

COEFS = np.array([[-1.0, 2.0, -1.0, 0.0], [3.0, -5.0, 0.0, 2.0], [-3.0, 4.0, 1.0, 0.0], [1.0, -1.0, 0.0, 0.0]])


@dataclass(frozen=True)
class Keyframe:
    """One `KeyFrame.nnnn` preset's camera.

    Attributes:
        name: The preset name.
        index: Its number (the order along the path).
        eye, target, up: The camera vectors.
        fov: The field of view when the preset carries one (None otherwise).
    """
    name: str
    index: int
    eye: tuple[float, float, float]
    target: tuple[float, float, float]
    up: tuple[float, float, float]
    fov: float | None = None


def parse_keyframe(name: str, body: str) -> Keyframe | None:
    """A keyframe from a preset body (None when `Eye` / `Target` / `Up` are missing — FragM skips those)."""
    values: dict[str, list[float]] = {}
    for line in body.splitlines():
        if "=" not in line or line.strip().startswith("//"):
            continue
        key, value = (part.strip() for part in line.split("=", 1))
        values[key] = parse_numbers(value, 3)
    if not all(k in values for k in ("Eye", "Target", "Up")):
        return None
    fov = values["FOV"][0] if "FOV" in values else None
    return Keyframe(name, keyframe_index(name), tuple(values["Eye"]), tuple(values["Target"]), tuple(values["Up"]), fov)


def keyframes_from_presets(presets: dict[str, str]) -> list[Keyframe]:
    """Every `KeyFrame.nnnn` preset with a camera, in numeric order."""
    found = [parse_keyframe(name, body) for name, body in presets.items() if is_keyframe(name)]
    return sorted((k for k in found if k is not None), key=lambda k: k.index)


def spline_point(points: np.ndarray, t: float, loop: bool) -> np.ndarray:
    """FragM's `VectSpline::spline`: the Catmull-Rom point at parameter `t` ∈ [0, 1] through `points` (n × 3)."""
    num = len(points)
    ki = 1.0 / num
    k = 0
    while ki * k < t:
        k += 1
    kj = ki * k
    kk = kj - ki
    h = (t - kk) / (kj - kk) if kj != kk else 0.0
    out = np.zeros(3)
    for i in range(4):
        kn = k + i - 2
        if kn < 0:
            kn = num - 1 if loop else 0
        elif kn > num - 1:
            kn = kn - num if loop else num - 1
        b = 0.5 * (((COEFS[i][0] * h + COEFS[i][1]) * h + COEFS[i][2]) * h + COEFS[i][3])
        out += b * points[kn]
    return out


class CameraPath:
    """The three splines of a keyframe set, sampled per frame.

    Args:
        keyframes: At least two keyframes (fewer: `valid` is False and `at()` returns None).
        frames: The animation length in frames (`length · fps`).
        loop: Wrap the path back to the first keyframe (FragM's *Loop camera path*).
    """

    def __init__(self, keyframes: list[Keyframe], frames: int, loop: bool = False):
        self.keyframes = list(keyframes)
        self.frames = max(1, int(frames))
        self.loop = loop
        self._eye = np.array([k.eye for k in keyframes], dtype=float) if keyframes else np.zeros((0, 3))
        self._target = np.array([k.target for k in keyframes], dtype=float) if keyframes else np.zeros((0, 3))
        self._up = np.array([k.up for k in keyframes], dtype=float) if keyframes else np.zeros((0, 3))

    @property
    def valid(self) -> bool:
        return len(self.keyframes) >= 2

    def step(self) -> float:
        """FragM's `enD`: the parameter advance per frame (the fudge that lands the end on the last control point)."""
        ns, nc = self.frames, len(self.keyframes)
        if self.loop:
            return 1.0 / max(ns - 1.0, 1.0)
        return 1.0 / ((ns - 1.0) + (ns - 1.0) * (1.0 / (nc - 1.0))) if ns > 1 and nc > 1 else 1.0

    def at(self, frame: int) -> tuple[np.ndarray, np.ndarray, np.ndarray] | None:
        """`(eye, target, up)` at `frame` (clamped to the path), or None without enough keyframes."""
        if not self.valid:
            return None
        t = min(max(self.step() * max(0, min(frame, self.frames)), 0.0), 1.0)
        return (spline_point(self._eye, t, self.loop), spline_point(self._target, t, self.loop), spline_point(self._up, t, self.loop))

    def sample(self, count: int | None = None) -> np.ndarray:
        """The eye path as `count` points (for drawing; the frame count by default)."""
        count = count or self.frames
        return np.array([self.at(int(round(i * self.frames / max(1, count - 1))))[0] for i in range(count)]) if self.valid else np.zeros((0, 3))

    def target_sample(self, count: int | None = None) -> np.ndarray:
        count = count or self.frames
        return np.array([self.at(int(round(i * self.frames / max(1, count - 1))))[1] for i in range(count)]) if self.valid else np.zeros((0, 3))


__all__ = ["Keyframe", "CameraPath", "parse_keyframe", "keyframes_from_presets", "spline_point"]
