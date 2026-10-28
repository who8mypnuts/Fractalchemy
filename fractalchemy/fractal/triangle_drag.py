"""The maths of dragging a triangle (or one of its corners) with the mouse, as Apophysis's editor does it.

Pure Python: a `DragState` remembers where the drag began — the triangle, the pivot, the grabbed
corner and its vector from the pivot — and `drag_corner` / `drag_triangle` turn the current mouse
point into the new triangle and a line of status text. The canvas widget only supplies the points.

Modes (`MODE_MOVE`, `MODE_ROTATE`, `MODE_SCALE`):

* a corner *moves* to the mouse (Shift snaps to the pivot's axes), *rotates* about the pivot at its
  original distance (Shift snaps the angle to `DragSteps.rotate_degrees`), or *scales* along its pivot
  ray (Shift snaps the length to multiples of `DragSteps.move`);
* a whole triangle moves by the mouse's displacement, rotates by the angle swept about the pivot, or
  scales by the projection of the mouse onto the starting ray (Shift snaps to the scale step).

Dragging corner **O** with `lock_axes` (or in rotate / scale mode) carries X and Y along; Apophysis
rotates / scales O about the world origin in that case, because the local pivot *is* O.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import triangles as T
from .triangles import CORNER_O, Point, Triangle

MODE_MOVE, MODE_ROTATE, MODE_SCALE = "move", "rotate", "scale"
HYPOTENUSE_EDGE = 2          # the edge Y→X: dragging it scales, the two axis edges rotate


@dataclass(frozen=True)
class DragSteps:
    """The snapping steps (the Triangle tab's amounts): degrees, fractal units, scale factor."""
    rotate_degrees: float = 15.0
    move: float = 0.1
    scale: float = 1.25


@dataclass
class DragState:
    """Where a drag began.

    Attributes:
        mode: What the drag does (`MODE_*`).
        start: The mouse point at the press.
        pivot: The point rotations and scalings turn about.
        original: The triangle at the press.
        corner: The grabbed corner (None = the whole triangle).
        old: Vector from the pivot to the anchor (the corner, or the press point).
        olddist: Its length.
        lock_o: Corner O drags the whole triangle along.
        changed: Whether any move produced a new triangle.
    """
    mode: str
    start: Point
    pivot: Point
    original: Triangle
    corner: int | None = None
    old: Point = (0.0, 0.0)
    olddist: float = 0.0
    lock_o: bool = False
    changed: bool = False


def begin_corner_drag(mode: str, start: Point, pivot: Point, triangle: Triangle, corner: int, local_pivot: bool) -> DragState:
    """A drag of one corner. For O with a local pivot the world origin is the pivot (O cannot turn about itself)."""
    if corner == CORNER_O and local_pivot:
        pivot = (0.0, 0.0)
    anchor = triangle[corner]
    old = (anchor[0] - pivot[0], anchor[1] - pivot[1])
    return DragState(mode, start, pivot, triangle, corner, old, math.hypot(*old), lock_o=corner == CORNER_O)


def begin_triangle_drag(mode: str, start: Point, pivot: Point, triangle: Triangle) -> DragState:
    """A drag of the whole triangle from `start`."""
    old = (start[0] - pivot[0], start[1] - pivot[1])
    return DragState(mode, start, pivot, triangle, None, old, math.hypot(*old))


def edge_drag_mode(edge: int) -> str:
    """What dragging an edge does: the hypotenuse scales, the axes rotate."""
    return MODE_SCALE if edge == HYPOTENUSE_EDGE else MODE_ROTATE


def drag_corner(state: DragState, point: Point, shift: bool, steps: DragSteps, axis_lock: bool) -> tuple[Triangle | None, str]:
    """The triangle with the grabbed corner taken to `point`, and a status line (None, "" when nothing moves)."""
    px, py = state.pivot
    if state.mode == MODE_ROTATE:
        d = math.hypot(point[0] - px, point[1] - py)
        if d == 0:
            return None, ""
        if shift and steps.rotate_degrees:
            step = math.radians(steps.rotate_degrees)
            a = round(math.atan2(point[1] - py, point[0] - px) / step) * step
            vx, vy = state.olddist * math.cos(a), state.olddist * math.sin(a)
        else:
            vx, vy = (point[0] - px) * state.olddist / d, (point[1] - py) * state.olddist / d
        angle = math.degrees(math.atan2(vy, vx) - math.atan2(state.old[1], state.old[0]))
        target, text = (px + vx, py + vy), f"rotated {wrap_degrees(angle):.2f}°"
    elif state.mode == MODE_SCALE:
        if state.olddist == 0:
            return None, ""
        d = (state.old[0] * (point[0] - px) + state.old[1] * (point[1] - py)) / state.olddist
        if shift and steps.move:
            d = math.trunc(d / steps.move) * steps.move
        vx, vy = state.old[0] * d / state.olddist, state.old[1] * d / state.olddist
        target, text = (px + vx, py + vy), f"axis length {math.hypot(vx, vy):.4f}  ({d * 100 / state.olddist:.1f} %)"
    else:
        if shift:
            target = (point[0], py) if abs(point[0] - px) > abs(point[1] - py) else (px, point[1])
        else:
            target = point
        anchor = state.original[state.corner]
        text = f"moved {target[0] - anchor[0]:+.4f}, {target[1] - anchor[1]:+.4f}"
    lock = state.lock_o and (axis_lock or state.mode != MODE_MOVE)
    return T.move_corner(state.original, state.corner, target, lock_axes=lock), text


def drag_triangle(state: DragState, point: Point, shift: bool, steps: DragSteps) -> tuple[Triangle | None, str]:
    """The whole triangle moved / rotated / scaled for the mouse at `point`, and a status line."""
    px, py = state.pivot
    if state.mode == MODE_ROTATE:
        angle = math.atan2(point[1] - py, point[0] - px) - math.atan2(state.old[1], state.old[0])
        if shift and steps.rotate_degrees:
            step = math.radians(steps.rotate_degrees)
            angle = round(angle / step) * step
        return T.rotate_about(state.original, state.pivot, angle), f"rotated {wrap_degrees(math.degrees(angle)):.2f}°"
    if state.mode == MODE_SCALE:
        if state.olddist == 0:
            return None, ""
        factor = (state.old[0] * (point[0] - px) + state.old[1] * (point[1] - py)) / (state.olddist ** 2)
        if shift and steps.scale != 1.0:
            step = abs(steps.scale - 1.0)
            factor = math.trunc(factor / step) * step
        if factor == 0:
            return None, ""
        return T.scale_about(state.original, state.pivot, factor), f"scaled {factor * 100:.1f} %"
    dx, dy = point[0] - state.start[0], point[1] - state.start[1]
    if shift:
        if abs(dx) > abs(dy):
            dy = 0.0
        else:
            dx = 0.0
    return T.translate(state.original, dx, dy), f"moved {dx:+.4f}, {dy:+.4f}"


def drag(state: DragState, point: Point, shift: bool, steps: DragSteps, axis_lock: bool) -> tuple[Triangle | None, str]:
    """`drag_corner` or `drag_triangle`, whichever the state is."""
    if state.corner is not None:
        return drag_corner(state, point, shift, steps, axis_lock)
    return drag_triangle(state, point, shift, steps)


def wrap_degrees(angle: float) -> float:
    """An angle folded into −180 … 180."""
    return (angle + 180.0) % 360.0 - 180.0


__all__ = ["DragState", "DragSteps", "begin_corner_drag", "begin_triangle_drag", "edge_drag_mode", "drag", "drag_corner",
           "drag_triangle", "wrap_degrees", "MODE_MOVE", "MODE_ROTATE", "MODE_SCALE", "HYPOTENUSE_EDGE"]
