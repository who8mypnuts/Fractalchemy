"""Easing curves on single slider components — FragM's twelve-field setting and its frame-by-frame evaluation.

    Power1:InOutQuad:5:2:8:0:100:0.3:1:1.7:1:0
    name  :type    :n:start:end:first:last:period:amplitude:overshoot:loops:pingpong

The name is a slider component (`Power1`, `JuliaC2`); the curve is one of Qt's `QEasingCurve` types by number;
between `first` and `last` frame the value runs from `start` to `end` (FragM's end value is nudged so the last frame
lands exactly on `end`), repeated `loops` times, reversed on every other loop when `pingpong`; before the range the
start value holds, after it the final value. `Range…` presets store these lines; *save easing in presets* puts them in
ordinary presets too. (FragM sets period / amplitude / overshoot on a copy of the curve by mistake; here they apply.)
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QEasingCurve

ELASTIC = (QEasingCurve.Type.InElastic, QEasingCurve.Type.OutElastic, QEasingCurve.Type.InOutElastic, QEasingCurve.Type.OutInElastic)
BOUNCE = (QEasingCurve.Type.InBounce, QEasingCurve.Type.OutBounce, QEasingCurve.Type.InOutBounce, QEasingCurve.Type.OutInBounce)
BACK = (QEasingCurve.Type.InBack, QEasingCurve.Type.OutBack, QEasingCurve.Type.InOutBack, QEasingCurve.Type.OutInBack)
CURVE_NAMES = [name for name in dir(QEasingCurve.Type) if name[0].isupper() and name not in ("Custom", "NCurveTypes", "BezierSpline", "TCBSpline")]


def curve_type(number: int) -> QEasingCurve.Type:
    try:
        return QEasingCurve.Type(int(number))
    except ValueError:
        return QEasingCurve.Type.Linear


def curve_name(number: int) -> str:
    return curve_type(number).name


def curve_number(name: str) -> int:
    return getattr(QEasingCurve.Type, name, QEasingCurve.Type.Linear).value


@dataclass(frozen=True)
class EasingSetting:
    """One easing curve (see the module docstring)."""
    slider: str
    type_number: int
    start: float
    end: float
    first_frame: int
    last_frame: int
    period: float = 0.3
    amplitude: float = 1.0
    overshoot: float = 1.70158
    loops: int = 1
    pingpong: bool = False

    @classmethod
    def parse(cls, text: str) -> "EasingSetting | None":
        parts = text.strip().split(":")
        if len(parts) != 12:
            return None
        try:
            return cls(parts[0], int(parts[2]), float(parts[3]), float(parts[4]), int(parts[5]), int(parts[6]), float(parts[7]),
                       float(parts[8]), float(parts[9]), int(parts[10]), parts[11].strip() not in ("0", "false", ""))
        except ValueError:
            return None

    def format(self) -> str:
        return ":".join([self.slider, curve_name(self.type_number), str(self.type_number), f"{self.start:g}", f"{self.end:g}",
                         str(self.first_frame), str(self.last_frame), f"{self.period:g}", f"{self.amplitude:g}", f"{self.overshoot:g}",
                         str(self.loops), "1" if self.pingpong else "0"])

    @property
    def parameter(self) -> str:
        """The parameter name (the slider name without its component digit)."""
        return self.slider[:-1] if self.slider[-1:].isdigit() else self.slider

    @property
    def component(self) -> int:
        """1-based component the curve drives."""
        return int(self.slider[-1]) if self.slider[-1:].isdigit() else 1

    @property
    def duration(self) -> int:
        """Frames per loop (FragM's `getLoopDuration`: last − first + 1)."""
        return max(1, self.last_frame - self.first_frame + 1)

    @property
    def end_frame(self) -> int:
        """The last animated frame over every loop."""
        return self.first_frame + self.duration * max(1, self.loops) - 1

    def curve(self) -> QEasingCurve:
        curve = QEasingCurve(curve_type(self.type_number))
        if curve.type() in ELASTIC:
            curve.setPeriod(self.period)
            curve.setAmplitude(self.amplitude)
        elif curve.type() in BOUNCE:
            curve.setAmplitude(self.amplitude)
        elif curve.type() in BACK:
            curve.setOvershoot(self.overshoot)
        return curve

    def _local_time(self, frame: int) -> int:
        """FragM's `updateEasingCurves`: the time inside the loop for `frame`, holding the ends."""
        duration, loops = self.duration, max(1, self.loops)
        if frame <= self.first_frame:
            return 0
        animframe = frame - self.first_frame
        if frame <= self.end_frame:
            if self.pingpong:
                even = (animframe // duration) % 2 == 0
                return animframe % duration if even else duration - (animframe % duration) - 1
            return animframe % duration
        if self.pingpong:
            return 0 if loops % 2 == 0 else duration - 1
        return duration - 1

    def value_at(self, frame: int) -> float:
        """The animated value at `frame`."""
        duration = self.duration
        span = self.last_frame - self.first_frame
        end = self.end + (self.end - self.start) / span if span > 0 else self.end      # FragM's nudge: the last frame reaches `end`
        progress = self._local_time(frame) / duration
        return self.start + (end - self.start) * self.curve().valueForProgress(progress)


def parse_all(lines: list[str]) -> list[EasingSetting]:
    return [s for s in (EasingSetting.parse(line) for line in lines) if s is not None]


def with_setting(settings: list[EasingSetting], new: EasingSetting) -> list[EasingSetting]:
    """`settings` with `new` replacing the curve of the same slider, or appended."""
    out = [s for s in settings if s.slider != new.slider]
    out.append(new)
    return out


def without_slider(settings: list[EasingSetting], slider: str) -> list[EasingSetting]:
    return [s for s in settings if s.slider != slider]


__all__ = ["EasingSetting", "parse_all", "with_setting", "without_slider", "curve_type", "curve_name", "curve_number", "CURVE_NAMES"]
