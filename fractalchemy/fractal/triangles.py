"""Triangles: the editor's picture of an affine transform. Pure Python, no Qt.

Apophysis shows each affine as the image of a reference triangle with corners **X** = (1, 0),
**O** = (0, 0) and **Y** = (0, 1). The editor works in *editor space*, which is fractal space
with the y axis pointing **up** (fractal-space y points down on screen, as in flam3), so a
triangle's corners are where the affine sends the unit vectors, as seen on screen. The
conversions below take care of the flip, and every operation (move, rotate, scale, flip) acts
on the triangle; `triangle_to_affine` turns the result back into the `(a, b, c, d, e, f)` the
renderers use.

A `Triangle` is the tuple `(X, O, Y)` of `(x, y)` points — the corner order of Apophysis
(`MainTriangles[n].x[0..2]`), so corner 1 is the origin O.
"""

from __future__ import annotations

import math

from .scene import Affine, identity_affine

Point = tuple[float, float]
Triangle = tuple[Point, Point, Point]

CORNER_X, CORNER_O, CORNER_Y = 0, 1, 2
CORNER_NAMES = ("X", "O", "Y")
REFERENCE: Triangle = ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0))


# --- affine <-> triangle -----------------------------------------------------------------------------------
def affine_to_triangle(coefs: Affine) -> Triangle:
    """Corners X, O, Y of the affine's triangle in editor space (y up)."""
    a, b, c, d, e, f = coefs
    return ((a + e, -(b + f)), (e, -f), (e - c, d - f))


def triangle_to_affine(triangle: Triangle) -> Affine:
    """The affine whose triangle is `triangle` (inverse of `affine_to_triangle`)."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    return tuple(v + 0.0 for v in (xx - ox, -(xy - oy), -(yx - ox), yy - oy, ox, -oy))   # + 0.0: no negative zeros


def to_editor(point: Point) -> Point:
    """Fractal-space point → editor space (y flipped)."""
    return (point[0], -point[1])


def to_fractal(point: Point) -> Point:
    """Editor-space point → fractal space (y flipped)."""
    return (point[0], -point[1])


def editor_affine(coefs: Affine) -> Affine:
    """The affine as Apophysis's Transform tab shows it: vectors X, Y and O in editor space (b, c, f negated)."""
    a, b, c, d, e, f = coefs
    return (a, -b, -c, d, e, -f)


def from_editor_affine(coefs: Affine) -> Affine:
    """Inverse of `editor_affine` (the flip is its own inverse)."""
    return editor_affine(coefs)


def is_reference(triangle: Triangle, tolerance: float = 1e-12) -> bool:
    """True if the triangle is the reference triangle (the identity affine)."""
    return all(abs(p[0] - q[0]) <= tolerance and abs(p[1] - q[1]) <= tolerance for p, q in zip(triangle, REFERENCE))


# --- geometry --------------------------------------------------------------------------------------------
def centroid(triangle: Triangle) -> Point:
    """The triangle's centre of mass."""
    return (sum(p[0] for p in triangle) / 3.0, sum(p[1] for p in triangle) / 3.0)


def area(triangle: Triangle) -> float:
    """Unsigned area (Apophysis's auto weights use it)."""
    (x0, y0), (x1, y1), (x2, y2) = triangle
    return abs((x1 - x0) * (y2 - y0) - (x2 - x0) * (y1 - y0)) / 2.0


def local_point(triangle: Triangle, u: float, v: float) -> Point:
    """The point at local coordinates (u, v): O + u·(X − O) + v·(Y − O) — Apophysis's local pivot."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    return (ox + (xx - ox) * u + (yx - oy) * v, oy + (xy - oy) * u + (yy - oy) * v)


def local_coords(triangle: Triangle, point: Point) -> Point | None:
    """Local (u, v) of a world point, or None for a degenerate triangle (inverse of `local_point`)."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    ax, ay, bx, by = xx - ox, xy - oy, yx - ox, yy - oy
    det = ax * by - bx * ay
    if abs(det) < 1e-15:
        return None
    px, py = point[0] - ox, point[1] - oy
    return ((px * by - py * bx) / det, (-px * ay + py * ax) / det)


def translate(triangle: Triangle, dx: float, dy: float) -> Triangle:
    """The triangle moved by (dx, dy)."""
    return tuple((x + dx, y + dy) for x, y in triangle)   # type: ignore[return-value]


def rotate_about(triangle: Triangle, pivot: Point, radians: float) -> Triangle:
    """Rotate counter-clockwise (in editor space) about `pivot`."""
    cos_a, sin_a = math.cos(radians), math.sin(radians)
    px, py = pivot
    return tuple((px + (x - px) * cos_a - (y - py) * sin_a, py + (x - px) * sin_a + (y - py) * cos_a)
                 for x, y in triangle)   # type: ignore[return-value]


def scale_about(triangle: Triangle, pivot: Point, factor: float) -> Triangle:
    """Scale about `pivot` (a zero factor is nudged so the triangle never collapses to a point)."""
    if factor == 0:
        factor = 1e-12
    px, py = pivot
    return tuple((px + (x - px) * factor, py + (y - py) * factor) for x, y in triangle)   # type: ignore[return-value]


def flip_horizontal(triangle: Triangle, pivot: Point | None = None) -> Triangle:
    """Mirror left-right about the vertical line through `pivot` (the world y axis by default)."""
    px = 0.0 if pivot is None else pivot[0]
    return tuple((2 * px - x, y) for x, y in triangle)   # type: ignore[return-value]


def flip_vertical(triangle: Triangle, pivot: Point | None = None) -> Triangle:
    """Mirror top-bottom about the horizontal line through `pivot` (the world x axis by default)."""
    py = 0.0 if pivot is None else pivot[1]
    return tuple((x, 2 * py - y) for x, y in triangle)   # type: ignore[return-value]


def move_corner(triangle: Triangle, corner: int, point: Point, lock_axes: bool = False) -> Triangle:
    """Put `corner` at `point`; with `lock_axes` the other corners follow (moving O drags the whole triangle)."""
    corners = list(triangle)
    if lock_axes:
        dx, dy = point[0] - corners[corner][0], point[1] - corners[corner][1]
        return translate(triangle, dx, dy)
    corners[corner] = (float(point[0]), float(point[1]))
    return tuple(corners)   # type: ignore[return-value]


def reset_corner(triangle: Triangle, corner: int) -> Triangle:
    """Apophysis's X / Y / O buttons: X back to O + (1, 0), Y to O + (0, 1), O to the origin (moving the others)."""
    corners = list(triangle)
    ox, oy = corners[CORNER_O]
    if corner == CORNER_X:
        corners[CORNER_X] = (ox + 1.0, oy)
    elif corner == CORNER_Y:
        corners[CORNER_Y] = (ox, oy + 1.0)
    else:
        return translate(triangle, -ox, -oy)
    return tuple(corners)   # type: ignore[return-value]


def reset_rotation(triangle: Triangle) -> Triangle:
    """Keep O and the axis lengths, point X along +x and Y along +y."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    return ((ox + math.hypot(xx - ox, xy - oy), oy), (ox, oy), (ox, oy + math.hypot(yx - ox, yy - oy)))


def snap_rotation(triangle: Triangle) -> Triangle:
    """Apophysis's *reset rotation*: turn each axis to the nearest multiple of 90°, keeping O and the lengths
    (and keeping the axes distinct, so a triangle never collapses onto one line)."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    ax_, ay_ = xx - ox, xy - oy
    bx_, by_ = yx - ox, yy - oy
    qa = round(math.atan2(ay_, ax_) / (math.pi / 2))
    qb = round(math.atan2(by_, bx_) / (math.pi / 2))
    da = 1 if ax_ * by_ - bx_ * ay_ >= 0 else -1
    if qa == qb:
        qb += da
    elif abs(qa - qb) == 2:
        qb -= da
    la, lb = math.hypot(ax_, ay_), math.hypot(bx_, by_)
    return ((ox + la * math.cos(qa * math.pi / 2), oy + la * math.sin(qa * math.pi / 2)), (ox, oy),
            (ox + lb * math.cos(qb * math.pi / 2), oy + lb * math.sin(qb * math.pi / 2)))


def snap_corner_rotation(triangle: Triangle, corner: int) -> Triangle:
    """Turn one axis (O→corner) to the nearest multiple of 90°; for O, snap its position about the origin."""
    corners = list(triangle)
    if corner == CORNER_O:
        ox, oy = corners[CORNER_O]
        d = math.hypot(ox, oy)
        if d == 0:
            return triangle
        q = round(math.atan2(oy, ox) / (math.pi / 2))
        return translate(triangle, d * math.cos(q * math.pi / 2) - ox, d * math.sin(q * math.pi / 2) - oy)
    ox, oy = corners[CORNER_O]
    x, y = corners[corner]
    d = math.hypot(x - ox, y - oy)
    q = round(math.atan2(y - oy, x - ox) / (math.pi / 2))
    corners[corner] = (ox + d * math.cos(q * math.pi / 2), oy + d * math.sin(q * math.pi / 2))
    return tuple(corners)   # type: ignore[return-value]


def reset_corner_scale(triangle: Triangle, corner: int) -> Triangle:
    """Make one axis (O→corner) unit length, keeping its direction; for O, nothing changes."""
    if corner == CORNER_O:
        return triangle
    corners = list(triangle)
    ox, oy = corners[CORNER_O]
    x, y = corners[corner]
    d = math.hypot(x - ox, y - oy)
    if d == 0:
        return triangle
    corners[corner] = (ox + (x - ox) / d, oy + (y - oy) / d)
    return tuple(corners)   # type: ignore[return-value]


def reset_scale(triangle: Triangle) -> Triangle:
    """Keep O and the axis directions, make both axes unit length."""
    (xx, xy), (ox, oy), (yx, yy) = triangle
    out = [(xx, xy), (ox, oy), (yx, yy)]
    for i, (x, y) in ((CORNER_X, (xx, xy)), (CORNER_Y, (yx, yy))):
        length = math.hypot(x - ox, y - oy)
        if length > 0:
            out[i] = (ox + (x - ox) / length, oy + (y - oy) / length)
    return tuple(out)   # type: ignore[return-value]


def axis_angle(triangle: Triangle, corner: int) -> float:
    """Direction of the O→corner axis in degrees (editor space, counter-clockwise from +x)."""
    ox, oy = triangle[CORNER_O]
    x, y = triangle[corner]
    return math.degrees(math.atan2(y - oy, x - ox))


def axis_length(triangle: Triangle, corner: int) -> float:
    """Length of the O→corner axis."""
    ox, oy = triangle[CORNER_O]
    x, y = triangle[corner]
    return math.hypot(x - ox, y - oy)


def with_axis_polar(triangle: Triangle, corner: int, length: float, degrees: float) -> Triangle:
    """Set the O→corner axis by length and angle (editor space)."""
    corners = list(triangle)
    ox, oy = corners[CORNER_O]
    rad = math.radians(degrees)
    corners[corner] = (ox + length * math.cos(rad), oy + length * math.sin(rad))
    return tuple(corners)   # type: ignore[return-value]


# --- hit testing -------------------------------------------------------------------------------------------
def contains(triangle: Triangle, point: Point) -> bool:
    """Even-odd point-in-polygon test (Apophysis `InsideTriangle`)."""
    x, y = point
    inside = False
    j = 2
    for i in range(3):
        xi, yi = triangle[i]
        xj, yj = triangle[j]
        if ((yi <= y < yj) or (yj <= y < yi)) and x < (xj - xi) * (y - yi) / (yj - yi) + xi:
            inside = not inside
        j = i
    return inside


def segment_distance(point: Point, a: Point, b: Point) -> float:
    """Distance from `point` to the segment a–b."""
    px, py = point
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    if length2 == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def nearest_corner(triangle: Triangle, point: Point, radius: float) -> int | None:
    """Index of the corner within `radius` of `point` (the closest one), else None."""
    best, best_d = None, radius
    for i, (x, y) in enumerate(triangle):
        d = math.hypot(point[0] - x, point[1] - y)
        if d <= best_d:
            best, best_d = i, d
    return best


def nearest_edge(triangle: Triangle, point: Point, radius: float) -> int | None:
    """Index `i` of the edge corner i → corner (i+1) mod 3 within `radius` of `point`, else None."""
    best, best_d = None, radius
    for i in range(3):
        d = segment_distance(point, triangle[i], triangle[(i + 1) % 3])
        if d <= best_d:
            best, best_d = i, d
    return best


def bounds(triangles) -> tuple[float, float, float, float]:
    """(min x, min y, max x, max y) over every corner of `triangles` (the origin is always included)."""
    xs, ys = [0.0], [0.0]
    for triangle in triangles:
        for x, y in triangle:
            xs.append(x)
            ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def identity_triangle() -> Triangle:
    """The identity affine's triangle (the reference triangle)."""
    return affine_to_triangle(identity_affine())


__all__ = [name for name in dir() if not name.startswith("_")]
