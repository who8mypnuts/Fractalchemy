"""Tone curves (Chaotica / Apophysis 7X "curves"): overall, red, green, blue and alpha.

Each channel is a list of `(x, y)` control points in 0..1, interpolated with a monotone cubic
(Fritsch–Carlson, so the curve never overshoots the points). The renderer turns every channel into a
256-entry lookup table and applies *overall* first, then the colour channel: `r' = red(overall(r))`;
the alpha curve remaps the coverage (how much background shows through) before compositing.

Pure Python, no numpy: the scene model stays light. `from_apophysis()` reads Apophysis 7X's
48-number `curves` attribute (four rational cubic Béziers, evaluated by parameter as Apophysis does).
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

CHANNELS = ("overall", "red", "green", "blue", "alpha")
Point = tuple[float, float]
DEFAULT_POINTS: list[Point] = [(0.0, 0.0), (1.0, 1.0)]
LUT_SIZE = 256


def _clamp(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else float(v)


def normalise_points(points) -> list[Point]:
    """Sorted, clamped control points with the ends pinned to x = 0 and x = 1 (at least two points)."""
    pts = sorted((_clamp(x), _clamp(y)) for x, y in points)
    if not pts:
        return list(DEFAULT_POINTS)
    if len(pts) == 1:
        pts = [(0.0, pts[0][1]), (1.0, pts[0][1])]
    pts[0] = (0.0, pts[0][1])
    pts[-1] = (1.0, pts[-1][1])
    out: list[Point] = []
    for p in pts:   # equal x: the later point wins (the one just dragged there)
        if out and abs(out[-1][0] - p[0]) < 1e-9:
            out[-1] = p
        else:
            out.append(p)
    if len(out) == 1:
        out = [(0.0, out[0][1]), (1.0, out[0][1])]
    return out


def monotone_cubic(points: list[Point], xs) -> list[float]:
    """Fritsch–Carlson monotone cubic Hermite interpolation of `points` at `xs` (clamped to the end values)."""
    pts = normalise_points(points)
    n = len(pts)
    x = [p[0] for p in pts]
    y = [p[1] for p in pts]
    d = [(y[i + 1] - y[i]) / (x[i + 1] - x[i]) for i in range(n - 1)]
    m = [0.0] * n
    m[0], m[-1] = d[0], d[-1]
    for i in range(1, n - 1):
        m[i] = 0.0 if d[i - 1] * d[i] <= 0 else (d[i - 1] + d[i]) / 2.0
    for i in range(n - 1):
        if d[i] == 0.0:
            m[i] = m[i + 1] = 0.0
            continue
        a, b = m[i] / d[i], m[i + 1] / d[i]
        s = a * a + b * b
        if s > 9.0:
            t = 3.0 / math.sqrt(s)
            m[i], m[i + 1] = t * a * d[i], t * b * d[i]
    out = []
    k = 0
    for xv in xs:
        if xv <= x[0]:
            out.append(_clamp(y[0]))
            continue
        if xv >= x[-1]:
            out.append(_clamp(y[-1]))
            continue
        while xv > x[k + 1]:
            k += 1
        h = x[k + 1] - x[k]
        t = (xv - x[k]) / h
        t2, t3 = t * t, t * t * t
        h00, h10, h01, h11 = 2 * t3 - 3 * t2 + 1, t3 - 2 * t2 + t, -2 * t3 + 3 * t2, t3 - t2
        out.append(_clamp(h00 * y[k] + h10 * h * m[k] + h01 * y[k + 1] + h11 * h * m[k + 1]))
    return out


@dataclass
class Curves:
    """The five tone curves; `points[channel]` is a control-point list (see module doc)."""
    points: dict[str, list[Point]] = field(default_factory=lambda: {c: list(DEFAULT_POINTS) for c in CHANNELS})

    def __post_init__(self) -> None:
        self.points = {c: normalise_points(self.points.get(c, DEFAULT_POINTS)) for c in CHANNELS}

    def copy(self) -> "Curves":
        return Curves({c: list(p) for c, p in self.points.items()})

    def is_default(self, channel: str | None = None) -> bool:
        """True if `channel` (or every channel) is the identity."""
        channels = CHANNELS if channel is None else (channel,)
        return all(self.points[c] == DEFAULT_POINTS for c in channels)

    def set_points(self, channel: str, points) -> None:
        self.points[channel] = normalise_points(points)

    def reset(self, channel: str | None = None) -> None:
        for c in (CHANNELS if channel is None else (channel,)):
            self.points[c] = list(DEFAULT_POINTS)

    def lut(self, channel: str, size: int = LUT_SIZE) -> list[float]:
        """`size` samples of the channel's curve over 0..1."""
        return monotone_cubic(self.points[channel], [i / (size - 1) for i in range(size)])

    def evaluate(self, channel: str, x: float) -> float:
        return monotone_cubic(self.points[channel], [x])[0]

    # --- serialisation ----------------------------------------------------------------------------------
    def to_text(self) -> str:
        """`overall:0,0;0.5,0.6;1,1|red:…` — only the channels that differ from the identity."""
        parts = []
        for c in CHANNELS:
            if self.points[c] != DEFAULT_POINTS:
                parts.append(c + ":" + ";".join(f"{x:.8g},{y:.8g}" for x, y in self.points[c]))
        return "|".join(parts)

    @classmethod
    def from_text(cls, text: str) -> "Curves":
        curves = cls()
        for part in (text or "").split("|"):
            if ":" not in part:
                continue
            name, body = part.split(":", 1)
            if name not in CHANNELS:
                continue
            try:
                pts = [tuple(float(v) for v in pair.split(",")) for pair in body.split(";") if pair]
                curves.set_points(name, [(p[0], p[1]) for p in pts])
            except (ValueError, IndexError):
                continue
        return curves

    def to_dict(self) -> dict:
        return {c: [list(p) for p in self.points[c]] for c in CHANNELS if self.points[c] != DEFAULT_POINTS}

    @classmethod
    def from_dict(cls, data: dict | None) -> "Curves":
        curves = cls()
        for c, pts in (data or {}).items():
            if c in CHANNELS:
                curves.set_points(c, [(float(p[0]), float(p[1])) for p in pts])
        return curves

    @classmethod
    def from_apophysis(cls, text: str, samples: int = 9) -> "Curves":
        """Apophysis 7X `curves="x y w x y w … "` (4 channels × 4 control points × (x, y, weight)).

        Apophysis evaluates each rational cubic Bézier *by parameter* (`csa[ch][i] = Bezier(i/256).y`),
        so the curve is `y(t)` with `t` the input value; we sample it at `samples` points.
        """
        try:
            values = [float(v) for v in text.split()]
        except ValueError:
            return cls()
        curves = cls()
        if len(values) < 48:
            return curves
        for ch, name in enumerate(("overall", "red", "green", "blue")):
            base = ch * 12
            px = [values[base + 3 * k] for k in range(4)]
            py = [values[base + 3 * k + 1] for k in range(4)]
            w = [values[base + 3 * k + 2] for k in range(4)]
            if px == [0, 0, 1, 1] and py == [0, 0, 1, 1]:
                continue   # Apophysis's untouched curve (it only applies curves once they were edited)
            pts = []
            for i in range(samples):
                t = i / (samples - 1)
                s = 1.0 - t
                basis = [w[0] * s ** 3, w[1] * 3 * s * s * t, w[2] * 3 * s * t * t, w[3] * t ** 3]
                denom = sum(basis)
                yv = sum(b * p for b, p in zip(basis, py)) / denom if denom else t
                pts.append((t, yv))
            if all(abs(yv - t) < 1e-6 for t, yv in pts):
                continue   # identity: keep the simple default
            curves.set_points(name, pts)
        return curves
