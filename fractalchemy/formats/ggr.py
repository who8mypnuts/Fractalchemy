"""GIMP gradients (`.ggr`): segments with a midpoint, a blend shape and a colour-space each.

    GIMP Gradient
    Name: Sunrise
    2
    0.000 0.250 0.500 1 0 0 1 1 1 0 1 0 0
    0.500 0.750 1.000 1 1 0 1 0 0 1 1 2 1

Every segment line is `left middle right  lr lg lb la  rr rg rb ra  blend colour` (GIMP 2.10 appends two
colour-source ints that are ignored). The blend shapes and colour spaces follow GIMP's own `gimpgradient.c`
rather than Fragmentarium's ggr2glsl, whose sine and sphere shapes run backwards and whose curved shape
misses the midpoint; the maths live in `evaluate_segments` so the Fragments window's GLSL emitter, the
gradient preview and the tests share one reference implementation.

Reading produces a host `Gradient`: linear RGB segments become two stops, curved ones are sampled (the
registry simplifies redundant stops). Writing maps each pair of host stops to a linear RGB segment.
"""

from __future__ import annotations

import colorsys
import math
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path

from .. import config
from ..model import Gradient
from ..model.stop import ColorStop
from .base import FormatError, GradientFormat
from .textfile import atomic_write_bytes

RGBF = tuple[float, float, float]
_EPSILON = 1e-10
_CURVED_SAMPLES = 24  # points per non-linear segment when converting to host stops


class BlendType(IntEnum):
    """GIMP segment blend shapes (file values)."""
    LINEAR = 0
    CURVED = 1
    SINE = 2
    SPHERE_INCREASING = 3
    SPHERE_DECREASING = 4
    STEP = 5


class ColorType(IntEnum):
    """GIMP segment colour spaces (file values)."""
    RGB = 0
    HSV_CCW = 1
    HSV_CW = 2


@dataclass(frozen=True)
class Segment:
    """One GIMP gradient segment: `left..right` with the blend midpoint at `middle` (absolute positions)."""
    left: float
    middle: float
    right: float
    left_color: RGBF
    right_color: RGBF
    blend: BlendType = BlendType.LINEAR
    color: ColorType = ColorType.RGB

    def blend_factor(self, t: float) -> float:
        """GIMP's blend factor (0 at `left`, 1 at `right`) for an absolute position `t` inside the segment."""
        length = self.right - self.left
        if length < _EPSILON:
            middle, pos = 0.5, 0.5
        else:
            middle = (self.middle - self.left) / length
            pos = (t - self.left) / length
        return _shape(self.blend, middle, pos)

    def color_at(self, t: float) -> RGBF:
        """The colour at absolute position `t` (clamped to the segment)."""
        factor = self.blend_factor(min(max(t, self.left), self.right))
        if self.color == ColorType.RGB:
            return tuple(a + (b - a) * factor for a, b in zip(self.left_color, self.right_color))
        return _blend_hsv(self.left_color, self.right_color, factor, self.color == ColorType.HSV_CW)


def _linear_factor(middle: float, pos: float) -> float:
    """GIMP's `gimp_gradient_calc_linear_factor`: piecewise linear through (middle, 0.5)."""
    if pos <= middle:
        return 0.0 if middle < _EPSILON else 0.5 * pos / middle
    pos -= middle
    middle = 1.0 - middle
    return 1.0 if middle < _EPSILON else 0.5 + 0.5 * pos / middle


def _shape(blend: BlendType, middle: float, pos: float) -> float:
    if blend == BlendType.CURVED:
        if middle < _EPSILON:
            return 1.0
        if 1.0 - middle < _EPSILON:
            return 0.0
        return math.pow(pos, math.log(0.5) / math.log(middle)) if pos > 0 else 0.0
    if blend == BlendType.STEP:
        return 1.0 if pos >= middle else 0.0
    linear = _linear_factor(middle, pos)
    if blend == BlendType.SINE:
        return (math.sin(-math.pi / 2 + math.pi * linear) + 1.0) / 2.0
    if blend == BlendType.SPHERE_INCREASING:
        p = linear - 1.0
        return math.sqrt(max(0.0, 1.0 - p * p))
    if blend == BlendType.SPHERE_DECREASING:
        return 1.0 - math.sqrt(max(0.0, 1.0 - linear * linear))
    return linear


def _blend_hsv(left: RGBF, right: RGBF, factor: float, clockwise: bool) -> RGBF:
    lh, ls, lv = colorsys.rgb_to_hsv(*left)
    rh, rs, rv = colorsys.rgb_to_hsv(*right)
    s = ls + (rs - ls) * factor
    v = lv + (rv - lv) * factor
    if clockwise:
        h = lh - ((lh - rh) if rh <= lh else (1.0 - (rh - lh))) * factor
        h += 1.0 if h < 0.0 else 0.0
    else:
        h = lh + ((rh - lh) if lh <= rh else (1.0 - (lh - rh))) * factor
        h -= 1.0 if h > 1.0 else 0.0
    return colorsys.hsv_to_rgb(h, s, v)


# --- evaluation -------------------------------------------------------------
def segment_index(segments: list[Segment], t: float) -> int:
    """The segment containing `t` (binary search on the right edges, as GIMP and the GLSL emitter do)."""
    first, last = 0, len(segments) - 1
    while first != last:
        mid = (first + last) // 2
        if t <= segments[mid].right:
            last = mid
        else:
            first = mid + 1
    return first


def evaluate_segments(segments: list[Segment], t: float) -> RGBF:
    """The gradient's colour (floats 0..1) at `t` in 0..1 — the reference the GLSL output must match."""
    if not segments:
        return (0.0, 0.0, 0.0)
    t = min(max(t, 0.0), 1.0)
    return segments[segment_index(segments, t)].color_at(t)


def sample_segments(segments: list[Segment], count: int) -> list[RGBF]:
    """`count` evenly spaced evaluations across 0..1."""
    if count <= 1:
        return [evaluate_segments(segments, 0.0)] * max(count, 0)
    return [evaluate_segments(segments, i / (count - 1)) for i in range(count)]


# --- conversions ------------------------------------------------------------
def segments_from_gradient(gradient: Gradient) -> list[Segment]:
    """Linear RGB segments reproducing a host gradient exactly, including its cyclic wrap-around ends."""
    stops = gradient.stops
    if not stops:
        return []
    points = [(s.position, _unit(s.color)) for s in stops]
    if points[0][0] > 0.0:
        points.insert(0, (0.0, _unit(gradient.color_at(0.0))))
    if points[-1][0] < 1.0:
        points.append((1.0, _unit(gradient.color_at(1.0))))
    if len(points) == 1:
        points.append((1.0, points[0][1]))
    return [Segment(left, (left + right) / 2, right, lc, rc)
            for (left, lc), (right, rc) in zip(points, points[1:]) if right > left]


def gradient_from_segments(name: str, segments: list[Segment]) -> Gradient:
    """A host gradient: two stops per linear RGB segment, sampled stops for the other shapes."""
    stops: list[ColorStop] = []
    for segment in segments:
        for position in _stop_positions(segment):
            stops.append(ColorStop(position, _eight_bit(segment.color_at(position))))
    return Gradient(name, _drop_duplicates(stops))


def _stop_positions(segment: Segment) -> list[float]:
    simple = segment.blend == BlendType.LINEAR and segment.color == ColorType.RGB
    if simple and abs(segment.blend_factor(segment.middle) - 0.5) < 1e-9 and abs(segment.middle - (segment.left + segment.right) / 2) < 1e-6:
        return [segment.left, segment.right]
    span = segment.right - segment.left
    return [segment.left + span * i / _CURVED_SAMPLES for i in range(_CURVED_SAMPLES + 1)]


def _drop_duplicates(stops: list[ColorStop]) -> list[ColorStop]:
    kept: list[ColorStop] = []
    for stop in stops:
        if kept and abs(kept[-1].position - stop.position) < 1e-9 and kept[-1].color == stop.color:
            continue
        kept.append(stop)
    return kept


def _unit(color) -> RGBF:
    return tuple(c / 255.0 for c in color)


def _eight_bit(color: RGBF) -> tuple[int, int, int]:
    return tuple(min(255, max(0, int(round(c * 255.0)))) for c in color)


# --- file format ------------------------------------------------------------
def parse_ggr(text: str, fallback_name: str = "untitled") -> tuple[str, list[Segment]]:
    """The gradient name and segments of a `.ggr` text.

    Raises:
        FormatError: Missing header, or a segment line that is not `3 positions, 2 RGBA colours, 2 types`.
    """
    lines = [line.strip() for line in text.splitlines()]
    if not lines or "GIMP Gradient" not in lines[0]:
        raise FormatError("not a GIMP gradient (missing 'GIMP Gradient' header)")
    name = fallback_name
    body = lines[1:]
    if body and body[0].startswith("Name:"):
        name = body[0][5:].strip() or fallback_name
        body = body[1:]
    if body and body[0].isdigit():
        body = body[1:]  # the segment count: the lines are the truth
    segments = [_parse_segment(line) for line in body if line]
    if not segments:
        raise FormatError("GIMP gradient has no segments")
    return name, segments


def _parse_segment(line: str) -> Segment:
    fields = line.split()
    if len(fields) < 13:
        raise FormatError(f"bad GIMP gradient segment: {line!r}")
    try:
        values = [float(f) for f in fields[:11]]
        blend, color = int(fields[11]), int(fields[12])
    except ValueError as exc:
        raise FormatError(f"bad GIMP gradient segment: {line!r}") from exc
    left, middle, right = values[:3]
    return Segment(left, middle, right, tuple(values[3:6]), tuple(values[7:10]),
                   BlendType(blend) if blend in BlendType._value2member_map_ else BlendType.LINEAR,
                   ColorType(color) if color in ColorType._value2member_map_ else ColorType.RGB)


def format_ggr(name: str, segments: list[Segment]) -> str:
    """The `.ggr` text for `segments`."""
    rows = [f"{s.left:.6f} {s.middle:.6f} {s.right:.6f} "
            f"{_rgba(s.left_color)} {_rgba(s.right_color)} {int(s.blend)} {int(s.color)}" for s in segments]
    return "\n".join(["GIMP Gradient", f"Name: {name}", str(len(segments)), *rows]) + "\n"


def _rgba(color: RGBF) -> str:
    return " ".join(f"{c:.6f}" for c in color) + " 1.000000"


def read_ggr(path: Path) -> tuple[str, list[Segment]]:
    """Name and segments of a `.ggr` file (the file name when it carries no name)."""
    return parse_ggr(path.read_text(encoding="utf-8", errors="replace"), path.stem)


class GgrFormat(GradientFormat):
    """Reader/writer for GIMP `.ggr` gradients (one gradient per file)."""
    name = "GIMP gradient"
    extensions = (".ggr",)
    can_save = True
    can_create = True

    def load(self, path: Path) -> list[Gradient]:
        """The file's gradient with GIMP's blend shapes baked into sampled stops.

        Raises:
            FormatError: If the file is not a GIMP gradient.
        """
        name, segments = read_ggr(path)
        return [gradient_from_segments(name, segments)]

    def save(self, gradient: Gradient, path: Path, index: int = 0) -> None:
        """Write the gradient as linear RGB segments (the index is ignored: one gradient per file)."""
        name = gradient.name or config.APP_NAME
        atomic_write_bytes(path, format_ggr(name, segments_from_gradient(gradient)).encode("utf-8"))
