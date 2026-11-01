"""The timeline editor — FragM's `TimeLineDialog`: keyframes and easing curves on one ruler.

The host's `Timeline` widget shows the animation's frames with a marker per `KeyFrame.nnnn` preset (FragM spaces the
keyframes evenly over the length) and the playhead; clicking a marker applies that keyframe's preset and moves the
playhead there, scrubbing moves the frame. Below it, one lane per easing curve: the name, the frame range as a bar
and the curve's shape; double-click edits the curve (`F7`), the context menu removes it. A second tab holds the
graph editor (`graph_editor.py`): values against frames with draggable curve handles and the keyframe tracks.
Opened from the time slider's context menu or *Animation ▸ Timeline editor*.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QDialog, QLabel, QMenu, QScrollArea, QTabWidget, QVBoxLayout, QWidget

from ...fragments.animation import AnimationSettings
from ...fragments.easing import EasingSetting
from ...fragments.spline import Keyframe
from ...widgets.timeline import Timeline
from .graph_editor import GraphEditor

LANE_HEIGHT = 44
LABEL_WIDTH = 130
LANE_BACKGROUND = QColor(34, 34, 34)
RANGE_COLOR = QColor(70, 110, 70)
CURVE_COLOR = QColor("#1e88e5")
TEXT_COLOR = QColor(190, 190, 190)


class KeyframeMarker:
    """What the `Timeline` widget needs of a keyframe: `.frame` and `.label`."""

    def __init__(self, keyframe: Keyframe, frame: int):
        self.keyframe = keyframe
        self.frame = frame
        self.label = keyframe.name


def keyframe_markers(keyframes: list[Keyframe], frames: int) -> list[KeyframeMarker]:
    """FragM spaces the keyframes evenly over the animation: keyframe *i* of *k* sits at `i · frames / (k − 1)`."""
    count = len(keyframes)
    if count == 0:
        return []
    if count == 1:
        return [KeyframeMarker(keyframes[0], 0)]
    return [KeyframeMarker(k, int(round(i * (frames - 1) / (count - 1)))) for i, k in enumerate(keyframes)]


class CurveLanes(QWidget):
    """One lane per easing curve, aligned with the timeline above.

    Signals:
        edit_requested(str): Double-click on a lane: the slider name to edit.
        remove_requested(str): The context menu's *Remove curve*.
    """
    edit_requested = Signal(str)
    remove_requested = Signal(str)

    def __init__(self, timeline: Timeline, parent: QWidget | None = None):
        super().__init__(parent)
        self.timeline = timeline
        self.curves: list[EasingSetting] = []
        self.frames = 1
        self.setMinimumHeight(LANE_HEIGHT)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._menu)
        timeline.view_changed.connect(self.update)

    def show_curves(self, curves: list[EasingSetting], frames: int) -> None:
        self.curves, self.frames = list(curves), max(1, frames)
        self.setMinimumHeight(max(LANE_HEIGHT, LANE_HEIGHT * len(curves)))
        self.setFixedHeight(max(LANE_HEIGHT, LANE_HEIGHT * len(curves)))
        self.update()

    def lane_at(self, y: float) -> EasingSetting | None:
        index = int(y // LANE_HEIGHT)
        return self.curves[index] if 0 <= index < len(self.curves) else None

    def paintEvent(self, event) -> None:  # noqa: D102 - Qt override
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), LANE_BACKGROUND)
        if not self.curves:
            painter.setPen(TEXT_COLOR)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No easing curves — select a slider and press F7")
            painter.end()
            return
        font = QFont(painter.font())
        font.setPointSizeF(max(7.0, font.pointSizeF() - 1))
        painter.setFont(font)
        for index, curve in enumerate(self.curves):
            top = index * LANE_HEIGHT
            painter.setPen(QPen(QColor(60, 60, 60), 1))
            painter.drawLine(0, top + LANE_HEIGHT - 1, self.width(), top + LANE_HEIGHT - 1)
            x0, x1 = self.timeline.x_of(curve.first_frame), self.timeline.x_of(min(curve.end_frame, self.frames))
            painter.fillRect(QRectF(x0, top + 6, max(2.0, x1 - x0), LANE_HEIGHT - 12), RANGE_COLOR)
            self._paint_curve(painter, curve, top)
            label = QRectF(4, top + 4, LABEL_WIDTH - 8, LANE_HEIGHT - 8)
            painter.fillRect(label, QColor(20, 20, 20, 170))
            painter.setPen(TEXT_COLOR)
            painter.drawText(label.adjusted(4, 0, 0, 0), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                             f"{curve.slider}\n{curve.start:g} → {curve.end:g}")
        painter.end()

    def _paint_curve(self, painter: QPainter, curve: EasingSetting, top: int) -> None:
        values = [curve.value_at(f) for f in range(0, self.frames + 1, max(1, self.frames // 200))]
        low, high = min(values), max(values)
        span = (high - low) or 1.0
        path = QPainterPath()
        step = max(1, self.frames // 200)
        for i, value in enumerate(values):
            x = self.timeline.x_of(i * step)
            y = top + LANE_HEIGHT - 8 - (value - low) / span * (LANE_HEIGHT - 16)
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        painter.setPen(QPen(CURVE_COLOR, 1.5))
        painter.drawPath(path)

    def mouseDoubleClickEvent(self, event) -> None:  # noqa: D102 - Qt override
        curve = self.lane_at(event.position().y())
        if curve is not None:
            self.edit_requested.emit(curve.slider)

    def _menu(self, pos) -> None:
        curve = self.lane_at(pos.y())
        if curve is None:
            return
        menu = QMenu(self)
        edit = menu.addAction(f"Edit curve of {curve.slider}…")
        remove = menu.addAction(f"Remove curve of {curve.slider}")
        choice = menu.exec(self.mapToGlobal(pos))
        if choice is edit:
            self.edit_requested.emit(curve.slider)
        elif choice is remove:
            self.remove_requested.emit(curve.slider)


class TimelineWindow(QDialog):
    """Keyframes and easing curves over the animation (see the module docstring).

    Signals:
        frame_scrubbed(int): The playhead was moved.
        keyframe_chosen(str): A keyframe marker was clicked (the preset name).
        edit_curve(str): Edit the curve of a slider component.
        remove_curve(str): Remove it.
        curve_changed(object): A curve's handle was dragged in the graph: the new `EasingSetting`.
    """
    frame_scrubbed = Signal(int)
    keyframe_chosen = Signal(str)
    edit_curve = Signal(str)
    remove_curve = Signal(str)
    curve_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle("Timeline")
        self.timeline = Timeline(self)
        self.lanes = CurveLanes(self.timeline, self)
        self.summary = QLabel(self)
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.lanes)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.graph = GraphEditor(self)
        self.tabs = QTabWidget(self)
        self.tabs.addTab(scroll, "Lanes")
        self.tabs.addTab(self.graph, "Graph")
        layout = QVBoxLayout(self)
        layout.addWidget(self.summary)
        layout.addWidget(self.timeline)
        layout.addWidget(self.tabs, 1)
        self.resize(900, 460)
        self._markers: list[KeyframeMarker] = []
        self.timeline.frame_scrubbed.connect(self.frame_scrubbed)
        self.timeline.keyframe_clicked.connect(lambda marker: self.keyframe_chosen.emit(marker.label))
        self.lanes.edit_requested.connect(self.edit_curve)
        self.lanes.remove_requested.connect(self.remove_curve)
        self.graph.curve_changed.connect(self.curve_changed)
        self.graph.frame_clicked.connect(self.frame_scrubbed)

    def show_animation(self, keyframes: list[Keyframe], curves: list[EasingSetting], settings: AnimationSettings, frame: int,
                       selected: str = "", tracks: dict | None = None) -> None:
        """Refresh everything from the document (`tracks`: the graph's keyframe tracks, `graph_editor.keyframe_tracks`)."""
        self._markers = keyframe_markers(keyframes, settings.frames)
        selected_marker = next((m for m in self._markers if m.label == selected), None)
        self.timeline.set_data(settings.frames, settings.fps, self._markers, selected_marker, frame, settings.loop_path)
        self.lanes.show_curves(curves, settings.frames)
        self.graph.show_data(curves, tracks or {}, settings.frames, frame)
        self.summary.setText(f"{len(keyframes)} keyframes · {len(curves)} easing curves · {settings.frames} frames at {settings.fps} fps "
                             f"({settings.length} s)" + (" · looping path" if settings.loop_path else ""))

    def set_frame(self, frame: int) -> None:
        self.timeline.set_current_frame(frame)
        self.graph.set_frame(frame)


__all__ = ["TimelineWindow", "CurveLanes", "KeyframeMarker", "keyframe_markers"]
