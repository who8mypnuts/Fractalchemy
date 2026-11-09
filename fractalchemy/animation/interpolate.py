"""Interpolating flames between keyframes. Pure Python + numpy, no Qt.

Every frame is a *weighted blend* of the keyframes around it (two for linear, four for the
Catmull-Rom spline, one for hold): `blend_plan` says which keyframes and with what weights, and
`fractal.blend` does the rest — **align** the keyframe flames to one structure (missing transforms
fade in or out at weight 0, missing variations at 0, parameters from the nearest keyframe), then
**blend** every number. The blending lives in `fractal.blend` because mutation and breeding use it
too; `align_flames` / `blend_flames` are re-exported here for the animation code that imports them.

`flame_at(animation, frame)` does both for one frame.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..fractal.blend import align_flames, blend_flames
from ..fractal.scene import Flame

if TYPE_CHECKING:
    from .model import Animation, Keyframe


# --- weights ---------------------------------------------------------------------------------------------------
def ease(t: float, easing: str) -> float:
    """Warp the local time 0..1 of a segment."""
    t = min(1.0, max(0.0, t))
    if easing == "ease-in":
        return t * t
    if easing == "ease-out":
        return 1.0 - (1.0 - t) ** 2
    if easing == "ease-in-out":
        return t * t * (3.0 - 2.0 * t)
    return t


def catmull_rom_weights(t: float) -> tuple[float, float, float, float]:
    """Weights of p0..p3 for the uniform Catmull-Rom spline at local time `t` between p1 and p2 (they sum to 1)."""
    t2, t3 = t * t, t * t * t
    return (0.5 * (-t + 2 * t2 - t3), 0.5 * (2 - 5 * t2 + 3 * t3), 0.5 * (t + 4 * t2 - 3 * t3), 0.5 * (-t2 + t3))


def blend_plan(animation: "Animation", frame: int) -> list[tuple["Keyframe", float]]:
    """Which keyframes make up `frame`, with their weights (summing to 1). Empty without keyframes."""
    keys = animation.keyframes
    if not keys:
        return []
    frame = int(frame)
    before, after = animation.segment(frame)
    if before is None:                       # before the first keyframe: hold it
        return [(keys[0], 1.0)]
    if after is None:
        if not animation.loop or len(keys) == 1 or frame >= animation.total_frames:
            return [(before, 1.0)]           # after the last keyframe: hold it
        after, after_frame = keys[0], animation.total_frames    # looping: on to the first keyframe at the end
    else:
        after_frame = after.frame
    if before.frame == frame or animation.interpolation == "hold":
        return [(before, 1.0)]
    t = ease((frame - before.frame) / max(1, after_frame - before.frame), animation.easing)
    if animation.interpolation != "smooth" or len(keys) < 3:
        return [(before, 1.0 - t), (after, t)]
    i1 = keys.index(before)
    i2 = keys.index(after)
    if animation.loop:
        p0, p3 = keys[(i1 - 1) % len(keys)], keys[(i2 + 1) % len(keys)]
    else:
        p0, p3 = keys[max(0, i1 - 1)], keys[min(len(keys) - 1, i2 + 1)]
    w0, w1, w2, w3 = catmull_rom_weights(t)
    return _merge([(p0, w0), (before, w1), (after, w2), (p3, w3)])


def _merge(plan: list[tuple["Keyframe", float]]) -> list[tuple["Keyframe", float]]:
    """Combine repeated keyframes (the clamped ends) into one entry each."""
    out: list[tuple["Keyframe", float]] = []
    for key, weight in plan:
        for i, (k, w) in enumerate(out):
            if k is key:
                out[i] = (k, w + weight)
                break
        else:
            out.append((key, weight))
    return out


# --- the frame -------------------------------------------------------------------------------------------------
def flame_at(animation: "Animation", frame: int) -> Flame | None:
    """The flame the animation shows at `frame` (None without keyframes)."""
    plan = blend_plan(animation, frame)
    if not plan:
        return None
    if len(plan) == 1:
        return plan[0][0].flame.copy()
    aligned = align_flames([k.flame for k, _w in plan])
    flame = blend_flames(aligned, [w for _k, w in plan])
    flame.name = f"{animation.name} — frame {frame}"
    return flame


def blend_fraction(animation: "Animation", frame: int) -> float:
    """How far `frame` is between its keyframes (0 at a keyframe; for the status bar)."""
    plan = blend_plan(animation, frame)
    if len(plan) < 2:
        return 0.0
    weights = {id(k): w for k, w in plan}
    before, _after = animation.segment(frame)
    return 1.0 - weights.get(id(before), 1.0) if before is not None else 0.0


__all__ = ["flame_at", "blend_plan", "align_flames", "blend_flames", "catmull_rom_weights", "ease", "blend_fraction"]

