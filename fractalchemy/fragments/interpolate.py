"""Interpolated presets — the *All parameters* interpolation mode (an extension; FragM animates only the camera).

The `KeyFrame.nnnn` presets are spaced evenly over the animation, as the camera path spaces them, and every numeric
parameter both neighbouring keyframes mention is blended between them (linearly, or with a smoothstep when
`smooth`); integers, booleans, menus and texture files hold the value of the last keyframe passed. The camera
vectors are left to the spline and eased components to their curves — `animation.frame_values` applies those on
top. Parameters a keyframe does not mention keep their current value.
"""

from __future__ import annotations

from typing import Any

from .parameters import ColorParameter, FloatColorParameter, FloatParameter, VectorParameter, parse_settings
from .presets import is_keyframe, keyframe_index

CAMERA_NAMES = ("Eye", "Target", "Up")
MODES = ("camera", "all")


def keyframe_values(presets: dict[str, str], params: dict[str, Any]) -> list[dict[str, Any]]:
    """The parsed values of every `KeyFrame.nnnn` preset, in numeric order (only names the fragment declares)."""
    found = sorted(((keyframe_index(name), body) for name, body in presets.items() if is_keyframe(name)), key=lambda item: item[0])
    result = []
    for _index, body in found:
        values: dict[str, Any] = {}
        for line in parse_settings(body).lines:
            param = params.get(line.name)
            if param is None or line.name in CAMERA_NAMES:
                continue
            try:
                values[line.name] = param.parse(line.value_text)
            except (ValueError, TypeError):
                continue
        result.append(values)
    return result


def _blendable(param: Any) -> bool:
    return isinstance(param, (FloatParameter, VectorParameter, ColorParameter, FloatColorParameter))


def _mix(a: Any, b: Any, t: float) -> Any:
    if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
        return tuple(float(x) + (float(y) - float(x)) * t for x, y in zip(a, b))
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) and not isinstance(a, bool):
        return float(a) + (float(b) - float(a)) * t
    return a


class KeyframeBlend:
    """Parameter values between keyframes at a frame (see the module docstring).

    Args:
        presets: The fragment's presets (name → body).
        params: The fragment's parameters (name → `GuiParameter`).
        frames: The animation length in frames.
        smooth: Smoothstep between keyframes instead of a straight line.
    """

    def __init__(self, presets: dict[str, str], params: dict[str, Any], frames: int, smooth: bool = True):
        self.keyframes = keyframe_values(presets, params)
        self.params = params
        self.frames = max(1, int(frames))
        self.smooth = smooth

    @property
    def valid(self) -> bool:
        return len(self.keyframes) >= 2

    def position(self, frame: int) -> tuple[int, float]:
        """`(left keyframe index, blend factor)` for `frame`, the keyframes spaced evenly over the animation."""
        n = len(self.keyframes)
        if n < 2:
            return 0, 0.0
        span = max(1, self.frames - 1) / (n - 1)
        x = min(max(frame, 0), self.frames - 1) / span
        left = min(int(x), n - 2)
        t = min(max(x - left, 0.0), 1.0)
        if self.smooth:
            t = t * t * (3.0 - 2.0 * t)
        return left, t

    def at(self, frame: int) -> dict[str, Any]:
        """The blended values at `frame` (empty without two keyframes)."""
        if not self.valid:
            return {}
        left, t = self.position(frame)
        a, b = self.keyframes[left], self.keyframes[left + 1]
        values: dict[str, Any] = {}
        for name, value in a.items():
            param = self.params.get(name)
            if name in b and _blendable(param):
                values[name] = _mix(value, b[name], t)
            else:
                values[name] = value if t < 1.0 else b.get(name, value)      # hold the last keyframe passed
        return values


__all__ = ["KeyframeBlend", "keyframe_values", "MODES", "CAMERA_NAMES"]
