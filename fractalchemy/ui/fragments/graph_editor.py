"""The animation graph: parameter values against frames, with draggable easing-curve handles.

The timeline's lanes show *when* a curve acts; the graph shows *what* it does: every easing curve as a line of its
value per frame, its two handles (start frame / value, end frame / value) draggable — drop one and the curve is
rewritten (`curve_changed`). Keyframe tracks — the value a numeric parameter takes in each `KeyFrame` preset, which
the *All parameters* interpolation blends between — are drawn as dots joined by lines, read-only (edit the presets
to move them). A vertical marker follows the playhead. The vertical range fits the visible tracks.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from ...fragments.easing import EasingSetting

MARGIN_LEFT, MARGIN_RIGHT, MARGIN_TOP, MARGIN_BOTTOM = 54, 12, 10, 22
HANDLE_RADIUS = 6.0
PALETTE = [QColor("#1e88e5"), QColor("#e53935"), QColor("#43a047"), QColor("#fb8c00"), QColor("#8e24aa"), QColor("#00acc1"), QColor("#f4511e")]
TRACK_COLOR = QColor(200, 200, 200)
GRID = QColor(60, 60, 60)
TEXT = QColor(190, 190, 190)


class GraphCanvas(QWidget):
    """The drawing / dragging surface.

    Signals:
        curve_changed(object): An `EasingSetting` with a handle moved (on release).
        frame_clicked(int): A click on empty space: move the playhead there.
    """
    curve_changed = Signal(object)
    frame_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.curves: list[EasingSetting] = []
        self.tracks: dict[str, list[tuple[int, float]]] = {}       # parameter → (frame, value) per keyframe
        self.frames = 250
        self.frame = 0
        self.selected: str = ""                                       # the slider whose curve is highlighted
        self._drag: tuple[int, str] | None = None                      # (curve index, "start" / "end")
        self._preview: EasingSetting | None = None
        self.setMinimumHeight(180)
        self.setMouseTracking(True)

    # --- data ----------------------------------------------------------------------------------------------------------
    def set_data(self, curves: list[EasingSetting], tracks: dict[str, list[tuple[int, float]]], frames: int, frame: int) -> None:
        self.curves = list(curves)
        self.tracks = dict(tracks)
        self.frames = max(2, int(frames))
        self.frame = frame
        self._drag = None
        self._preview = None
        self.update()

    def set_frame(self, frame: int) -> None:
        self.frame = frame
        self.update()

    def value_range(self) -> tuple[float, float]:
        """The vertical range that fits every visible curve and track (a little padding, never empty)."""
        values: list[float] = []
        for curve in self._shown_curves():
            values += [curve.start, curve.end]
        for points in self.tracks.values():
            values += [v for _f, v in points]
        if not values:
            return -1.0, 1.0
        lo, hi = min(values), max(values)
        pad = (hi - lo) * 0.1 or max(abs(lo), 1.0) * 0.1
        return lo - pad, hi + pad

    def _shown_curves(self) -> list[EasingSetting]:
        return [self._preview if self._preview is not None and self._drag is not None and c is self.curves[self._drag[0]] else c
                for c in self.curves]

    # --- geometry --------------------------------------------------------------------------------------------------------
    def plot_rect(self) -> QRectF:
        return QRectF(MARGIN_LEFT, MARGIN_TOP, max(1.0, self.width() - MARGIN_LEFT - MARGIN_RIGHT), max(1.0, self.height() - MARGIN_TOP - MARGIN_BOTTOM))

    def to_screen(self, frame: float, value: float, lo: float, hi: float) -> QPointF:
        rect = self.plot_rect()
        x = rect.left() + frame / max(1, self.frames - 1) * rect.width()
        y = rect.bottom() - (value - lo) / max(1e-12, hi - lo) * rect.height()
        return QPointF(x, y)

    def from_screen(self, pos: QPointF, lo: float, hi: float) -> tuple[int, float]:
        rect = self.plot_rect()
        frame = int(round((pos.x() - rect.left()) / max(1.0, rect.width()) * (self.frames - 1)))
        value = lo + (rect.bottom() - pos.y()) / max(1.0, rect.height()) * (hi - lo)
        return max(0, min(self.frames - 1, frame)), value

    def handles(self) -> list[tuple[int, str, QPointF]]:
        """`(curve index, which, screen point)` for every curve's start and end handle."""
        lo, hi = self.value_range()
        out = []
        for index, curve in enumerate(self._shown_curves()):
            out.append((index, "start", self.to_screen(curve.first_frame, curve.start, lo, hi)))
            out.append((index, "end", self.to_screen(curve.last_frame, curve.end, lo, hi)))
        return out

    def _hit(self, pos: QPointF) -> tuple[int, str] | None:
        for index, which, point in self.handles():
            if (point - pos).manhattanLength() <= HANDLE_RADIUS * 1.5:
                return index, which
        return None

    # --- painting ----------------------------------------------------------------------------------------------------------
    def paintEvent(self, event) -> None:  # noqa: N802 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(34, 34, 34))
        rect = self.plot_rect()
        lo, hi = self.value_range()
        self._paint_grid(painter, rect, lo, hi)
        for name, points in self.tracks.items():
            self._paint_track(painter, name, points, lo, hi)
        for index, curve in enumerate(self._shown_curves()):
            self._paint_curve(painter, curve, PALETTE[index % len(PALETTE)], curve.slider == self.selected, lo, hi)
        x = self.to_screen(self.frame, lo, lo, hi).x()
        painter.setPen(QPen(QColor(255, 255, 255, 160), 1))
        painter.drawLine(QPointF(x, rect.top()), QPointF(x, rect.bottom()))
        painter.end()

    def _paint_grid(self, painter: QPainter, rect: QRectF, lo: float, hi: float) -> None:
        painter.setPen(QPen(GRID, 1))
        painter.drawRect(rect)
        painter.setPen(TEXT)
        for i in range(5):
            value = lo + (hi - lo) * i / 4
            y = self.to_screen(0, value, lo, hi).y()
            painter.setPen(QPen(GRID, 1, Qt.PenStyle.DotLine))
            painter.drawLine(QPointF(rect.left(), y), QPointF(rect.right(), y))
            painter.setPen(TEXT)
            painter.drawText(QRectF(0, y - 8, MARGIN_LEFT - 4, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f"{value:.3g}")
        for i in range(5):
            frame = int(round((self.frames - 1) * i / 4))
            x = self.to_screen(frame, lo, lo, hi).x()
            painter.drawText(QRectF(x - 30, rect.bottom() + 2, 60, 18), Qt.AlignmentFlag.AlignHCenter, str(frame))

    def _paint_track(self, painter: QPainter, name: str, points: list[tuple[int, float]], lo: float, hi: float) -> None:
        painter.setPen(QPen(TRACK_COLOR, 1, Qt.PenStyle.DashLine))
        mapped = [self.to_screen(f, v, lo, hi) for f, v in points]
        for a, b in zip(mapped, mapped[1:]):
            painter.drawLine(a, b)
        painter.setPen(QPen(TRACK_COLOR, 1))
        painter.setBrush(TRACK_COLOR)
        for point in mapped:
            painter.drawEllipse(point, 3.0, 3.0)
        if mapped:
            painter.drawText(mapped[-1] + QPointF(6, 4), name)

    def _paint_curve(self, painter: QPainter, curve: EasingSetting, colour: QColor, selected: bool, lo: float, hi: float) -> None:
        path = QPainterPath()
        first = True
        for frame in range(0, self.frames):
            point = self.to_screen(frame, curve.value_at(frame), lo, hi)
            if first:
                path.moveTo(point)
                first = False
            else:
                path.lineTo(point)
        painter.setPen(QPen(colour, 2.5 if selected else 1.5))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPath(path)
        painter.setBrush(colour)
        for frame, value in ((curve.first_frame, curve.start), (curve.last_frame, curve.end)):
            painter.drawEllipse(self.to_screen(frame, value, lo, hi), HANDLE_RADIUS, HANDLE_RADIUS)
        painter.setPen(colour)
        painter.drawText(self.to_screen(curve.last_frame, curve.end, lo, hi) + QPointF(8, -6), curve.slider)

    # --- mouse ---------------------------------------------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        hit = self._hit(event.position())
        if hit is not None and event.button() == Qt.MouseButton.LeftButton:
            self._drag = hit
            self._preview = self.curves[hit[0]]
            self.selected = self._preview.slider
            self.update()
            return
        if event.button() == Qt.MouseButton.LeftButton:
            lo, hi = self.value_range()
            self.frame_clicked.emit(self.from_screen(event.position(), lo, hi)[0])

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            self.setCursor(Qt.CursorShape.OpenHandCursor if self._hit(event.position()) else Qt.CursorShape.ArrowCursor)
            return
        lo, hi = self.value_range()
        frame, value = self.from_screen(event.position(), lo, hi)
        index, which = self._drag
        curve = self.curves[index]
        if which == "start":
            self._preview = replace(curve, first_frame=min(frame, curve.last_frame - 1), start=value)
        else:
            self._preview = replace(curve, last_frame=max(frame, curve.first_frame + 1), end=value)
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            return
        changed, self._drag, self._preview = self._preview, None, None
        if changed is not None and changed != self.curves[[c.slider for c in self.curves].index(changed.slider)]:
            self.curve_changed.emit(changed)
        self.update()


class GraphEditor(QWidget):
    """The canvas with a track chooser above it (see the module docstring).

    Signals:
        curve_changed(object): Relayed from the canvas.
        frame_clicked(int): Relayed from the canvas.
    """
    curve_changed = Signal(object)
    frame_clicked = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.canvas = GraphCanvas(self)
        self.track_combo = QComboBox(self)
        self.track_combo.setToolTip("A parameter whose keyframe values to show (the All-parameters interpolation blends between them)")
        self.hint = QLabel("Drag a curve's end handles to change its frames and values; click elsewhere to move the playhead", self)
        top = QHBoxLayout()
        top.addWidget(QLabel("Keyframe track:", self))
        top.addWidget(self.track_combo, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(top)
        layout.addWidget(self.canvas, 1)
        layout.addWidget(self.hint)
        self._tracks: dict[str, list[tuple[int, float]]] = {}
        self.canvas.curve_changed.connect(self.curve_changed)
        self.canvas.frame_clicked.connect(self.frame_clicked)
        self.track_combo.currentTextChanged.connect(lambda _t: self._apply_track())

    def show_data(self, curves: list[EasingSetting], tracks: dict[str, list[tuple[int, float]]], frames: int, frame: int) -> None:
        """`tracks`: parameter → `(frame, value)` per keyframe (scalar values; vector components as `Name.1`)."""
        self._tracks = tracks
        current = self.track_combo.currentText()
        self.track_combo.blockSignals(True)
        self.track_combo.clear()
        self.track_combo.addItem("(none)")
        self.track_combo.addItems(sorted(tracks))
        if current in tracks:
            self.track_combo.setCurrentText(current)
        self.track_combo.blockSignals(False)
        self._curves, self._frames, self._frame = list(curves), frames, frame
        self._apply_track()

    def _apply_track(self) -> None:
        name = self.track_combo.currentText()
        shown = {name: self._tracks[name]} if name in self._tracks else {}
        self.canvas.set_data(getattr(self, "_curves", []), shown, getattr(self, "_frames", 250), getattr(self, "_frame", 0))

    def set_frame(self, frame: int) -> None:
        self.canvas.set_frame(frame)


def keyframe_tracks(presets: dict[str, str], params: dict, frames: int) -> dict[str, list[tuple[int, float]]]:
    """Parameter → `(frame, value)` per keyframe preset, the keyframes spaced evenly over `frames` (vector components as `Name.n`)."""
    from ...fragments.interpolate import keyframe_values
    values = keyframe_values(presets, params)
    if not values:
        return {}
    count = len(values)
    tracks: dict[str, list[tuple[int, float]]] = {}
    for index, entry in enumerate(values):
        frame = int(round(index * (frames - 1) / max(1, count - 1))) if count > 1 else 0
        for name, value in entry.items():
            if isinstance(value, bool):
                continue
            if isinstance(value, (int, float)):
                tracks.setdefault(name, []).append((frame, float(value)))
            elif isinstance(value, (tuple, list)):
                for c, component in enumerate(value, start=1):
                    if isinstance(component, (int, float)):
                        tracks.setdefault(f"{name}.{c}", []).append((frame, float(component)))
    return tracks


__all__ = ["GraphEditor", "GraphCanvas", "keyframe_tracks"]
