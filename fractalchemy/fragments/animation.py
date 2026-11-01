"""What a fragment's animation is made of, and the parameter values it produces at a frame.

FragM animates two things: the 3D camera follows a Catmull-Rom path through the `KeyFrame.nnnn` presets
(`spline.py`), and individual slider components follow easing curves (`easing.py`). `AnimationSettings` holds the
clock (frames per second, length in seconds, looping) and `frame_values()` turns a frame number into the parameter
values to apply — `Eye` / `Target` / `Up` from the path (plus `FocalPlane` when *AutoFocus* is on) and one component
of every eased parameter — so the viewport, the final renderer and the tests share one definition of "frame n".
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from .easing import EasingSetting
from .interpolate import MODES, KeyframeBlend
from .spline import CameraPath, keyframes_from_presets
from .state import ParameterState


@dataclass(frozen=True)
class AnimationSettings:
    """The clock.

    Attributes:
        fps: Frames per second (FragM's *Animation frame rate* preference, 25 by default).
        length: Animation length in seconds (the toolbar's spin box).
        loop_play: Start again at the end (*Loop play*).
        loop_path: The camera path wraps back to the first keyframe (*Loop camera path*).
        interpolation: `camera` (FragM: the camera path and the easing curves) or `all` (every numeric parameter
            blended between the keyframe presets as well — `interpolate.py`).
    """
    fps: int = 25
    length: int = 10
    loop_play: bool = True
    loop_path: bool = False
    interpolation: str = "camera"

    @property
    def frames(self) -> int:
        """Total frames (`length · fps`, at least 1)."""
        return max(1, int(self.fps) * int(self.length))

    def time_of(self, frame: int) -> float:
        """Seconds for a frame (the `time` uniform)."""
        return frame / max(1, self.fps)

    def frame_of(self, seconds: float) -> int:
        return int(seconds * self.fps)

    def with_(self, **fields) -> "AnimationSettings":
        return replace(self, **fields)

    def to_dict(self) -> dict:
        return {"fps": self.fps, "length": self.length, "loop_play": self.loop_play, "loop_path": self.loop_path,
                "interpolation": self.interpolation}

    @classmethod
    def from_dict(cls, data: dict | None) -> "AnimationSettings":
        data = data or {}
        mode = data.get("interpolation", "camera")
        return cls(int(data.get("fps", 25)), int(data.get("length", 10)), bool(data.get("loop_play", True)), bool(data.get("loop_path", False)),
                   mode if mode in MODES else "camera")


def keyframe_blend(presets: dict[str, str], state: ParameterState, settings: AnimationSettings) -> KeyframeBlend | None:
    """The parameter blend for the *all* interpolation mode (None in camera mode)."""
    if settings.interpolation != "all":
        return None
    return KeyframeBlend(presets, state.params, settings.frames)


def camera_path(presets: dict[str, str], settings: AnimationSettings) -> CameraPath:
    """The camera path through the keyframe presets at the settings' frame count."""
    return CameraPath(keyframes_from_presets(presets), settings.frames, settings.loop_path)


def frame_values(frame: int, state: ParameterState, path: CameraPath | None, curves: list[EasingSetting],
                 auto_focus: bool = False, blend: KeyframeBlend | None = None) -> dict[str, Any]:
    """The parameter values frame `frame` sets: the blended presets (when `blend`), the camera from the path, the
    eased components from the curves — each layer on top of the previous."""
    values: dict[str, Any] = {}
    if blend is not None and blend.valid:
        values.update({name: value for name, value in blend.at(frame).items() if name in state})
    if path is not None and path.valid and "Eye" in state and "Target" in state and "Up" in state:
        eye, target, up = path.at(frame)
        values["Eye"], values["Target"], values["Up"] = tuple(map(float, eye)), tuple(map(float, target)), tuple(map(float, up))
        if auto_focus and state.get("AutoFocus") and "FocalPlane" in state:
            values["FocalPlane"] = float(sum((a - b) ** 2 for a, b in zip(eye, target)) ** 0.5)
    for curve in curves:
        name = curve.parameter
        if name not in state:
            continue
        current = values.get(name, state.get(name))
        new = curve.value_at(frame)
        if isinstance(current, (tuple, list)):
            components = list(current)
            if 1 <= curve.component <= len(components):
                components[curve.component - 1] = new
            values[name] = tuple(components)
        else:
            values[name] = new
    return values


def curves_past_the_end(curves: list[EasingSetting], settings: AnimationSettings) -> list[EasingSetting]:
    """Curves whose last animated frame lies beyond the animation (FragM stops playback and asks to fix them)."""
    return [c for c in curves if c.end_frame > settings.frames]


__all__ = ["AnimationSettings", "camera_path", "frame_values", "curves_past_the_end", "keyframe_blend", "MODES"]
