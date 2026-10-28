"""The Animation window's timeline: a ruler of frames and seconds, keyframe markers and a playhead.

    timeline.set_data(total_frames, fps, keyframes, selected, current_frame)

The widget never changes the animation; it reports what the user does:

* click or drag on the ruler / track → `frame_scrubbed(frame)` (the playhead follows the mouse);
* click a keyframe marker → `keyframe_clicked(keyframe)`; drag it → `keyframe_dragged(keyframe, frame)` while
  it moves and `keyframe_dropped(keyframe)` at the end; double-click → `keyframe_activated(keyframe)`;
* the wheel zooms about the cursor (Shift + wheel scrolls), double-click on empty space fits the whole
  animation; ←/→ step a frame (Shift: a second), Home / End jump, Delete → `delete_requested()`.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import config

RULER_HEIGHT = 22
TRACK_HEIGHT = 44
MARGIN = 10
MARKER_HALF = 7
MARKER_HIT = 9
MAX_PIXELS_PER_FRAME = 80.0
BACKGROUND = QColor(28, 28, 28)
RULER_BACKGROUND = QColor(40, 40, 40)
TRACK_BACKGROUND = QColor(34, 34, 34)
TICK_COLOR = QColor(110, 110, 110)
SECOND_COLOR = QColor(160, 160, 160)
TEXT_COLOR = QColor(190, 190, 190)
MARKER_COLOR = QColor(235, 235, 235)
MARKER_OUTLINE = QColor(20, 20, 20)
SEGMENT_COLOR = QColor(90, 90, 90)
LOOP_COLOR = QColor(70, 110, 70)
TICK_STEPS = (1, 2, 5, 10, 15, 25, 30, 50, 60, 100, 120, 150, 250, 300, 500, 600, 1000, 1200, 1500, 2500, 3000, 5000, 10000)
LABEL_SPACING_PX = 48


class Timeline(QWidget):
    """The timeline widget (see the module docstring)."""
    frame_scrubbed = Signal(int)
    keyframe_clicked = Signal(object)
    keyframe_dragged = Signal(object, int)
    keyframe_dropped = Signal(object)
    keyframe_activated = Signal(object)
    delete_requested = Signal()
    view_changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setMinimumHeight(RULER_HEIGHT + TRACK_HEIGHT + 8)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._total = 150
        self._fps = 30
        self._keyframes: list = []
        self._selected = None
        self._current = 0
        self._loop = False
        self._ppf: float | None = None          # pixels per frame; None = fit
        self._start = 0.0                        # frame at the left edge
        self._hover = None
        self._drag_key = None
        self._drag_moved = False
        self._scrubbing = False
        self._labels: dict[int, str] = {}

    # --- data ---------------------------------------------------------------------------------------------------
    def set_data(self, total_frames: int, fps: int, keyframes: list, selected=None, current_frame: int = 0,
                 loop: bool = False) -> None:
        """Show this state (keyframes are objects with `.frame` and `.label`)."""
        self._total = max(1, int(total_frames))
        self._fps = max(1, int(fps))
        self._keyframes = list(keyframes)
        self._selected = selected if selected in self._keyframes else None
        self._current = max(0, min(self._total - 1, int(current_frame)))
        self._loop = loop
        if self._drag_key is not None and self._drag_key not in self._keyframes:
            self._drag_key = None
        self._clamp_view()
        self.update()

    def set_current_frame(self, frame: int) -> None:
        """Move the playhead (clamped to the length)."""
        frame = max(0, min(self._total - 1, int(frame)))
        if frame != self._current:
            self._current = frame
            self.update()

    def set_selected(self, keyframe) -> None:
        """Highlight a keyframe (None, or one not shown, clears the highlight)."""
        self._selected = keyframe if keyframe in self._keyframes else None
        self.update()

    # --- view ---------------------------------------------------------------------------------------------------
    @property
    def pixels_per_frame(self) -> float:
        """The zoom: screen pixels per frame (the fit when not zoomed)."""
        width = max(1, self.width() - 2 * MARGIN)
        return self._ppf if self._ppf is not None else width / self._total

    def fit(self) -> None:
        """Show the whole animation."""
        self._ppf = None
        self._start = 0.0
        self.view_changed.emit()
        self.update()

    def zoom_by(self, factor: float, anchor_x: float | None = None) -> None:
        """Zoom about a widget x (the centre by default); zooming out stops where the whole animation fits."""
        anchor_x = self.width() / 2 if anchor_x is None else anchor_x
        frame_under = self.frame_at(anchor_x)
        fit = max(1, self.width() - 2 * MARGIN) / self._total
        wanted = min(MAX_PIXELS_PER_FRAME, self.pixels_per_frame * factor)
        if wanted <= fit:
            self.fit()
            return
        self._ppf = wanted
        self._start = frame_under - (anchor_x - MARGIN) / self._ppf
        self._clamp_view()
        self.view_changed.emit()
        self.update()

    def scroll_by(self, frames: float) -> None:
        """Scroll the view by `frames` (clamped to the animation)."""
        self._start += frames
        self._clamp_view()
        self.view_changed.emit()
        self.update()

    def _clamp_view(self) -> None:
        if self._ppf is None:
            self._start = 0.0
            return
        visible = max(1, self.width() - 2 * MARGIN) / self._ppf
        self._start = max(0.0, min(max(0.0, self._total - visible), self._start))

    def x_of(self, frame: float) -> float:
        """Widget x of a frame."""
        return MARGIN + (frame - self._start) * self.pixels_per_frame

    def frame_at(self, x: float) -> float:
        """The (fractional) frame under widget x."""
        return self._start + (x - MARGIN) / self.pixels_per_frame

    def frame_near(self, x: float) -> int:
        """The frame nearest widget x, within the animation."""
        return max(0, min(self._total - 1, int(round(self.frame_at(x)))))

    def keyframe_at(self, pos: QPointF):
        """The keyframe whose marker is under `pos`, or None."""
        if not (RULER_HEIGHT <= pos.y() <= RULER_HEIGHT + TRACK_HEIGHT):
            return None
        best, best_d = None, MARKER_HIT + 1
        for key in self._keyframes:
            d = abs(self.x_of(key.frame) - pos.x())
            if d < best_d:
                best, best_d = key, d
        return best

    # --- mouse --------------------------------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if event.button() != Qt.MouseButton.LeftButton:
            return
        key = self.keyframe_at(event.position())
        if key is not None:
            self._drag_key = key
            self._drag_moved = False
            self._selected = key
            self.keyframe_clicked.emit(key)
            self.update()
            return
        self._scrubbing = True
        self.frame_scrubbed.emit(self.frame_near(event.position().x()))

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        if self._drag_key is not None:
            frame = self.frame_near(pos.x())
            if frame != self._drag_key.frame:
                self._drag_moved = True
                self.keyframe_dragged.emit(self._drag_key, frame)
            return
        if self._scrubbing:
            self.frame_scrubbed.emit(self.frame_near(pos.x()))
            return
        hover = self.keyframe_at(pos)
        if hover is not self._hover:
            self._hover = hover
            self.setCursor(Qt.CursorShape.SizeHorCursor if hover is not None else Qt.CursorShape.ArrowCursor)
            self.update()
        frame = self.frame_near(pos.x())
        self.setToolTip(f"frame {frame}  ·  {frame / self._fps:.2f} s" + (f"  ·  {hover.label}" if hover is not None else ""))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._drag_key is not None:
            key, moved = self._drag_key, self._drag_moved
            self._drag_key = None
            if moved:
                self.keyframe_dropped.emit(key)
        self._scrubbing = False

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        key = self.keyframe_at(event.position())
        if key is not None:
            self.keyframe_activated.emit(key)
        elif event.position().y() > RULER_HEIGHT:
            self.fit()

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if not steps:
            steps = event.angleDelta().x() / 120.0
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            visible = max(1, self.width() - 2 * MARGIN) / self.pixels_per_frame
            self.scroll_by(-steps * visible / 10)          # a tenth of the view per notch
        else:
            self.zoom_by(1.25 ** steps, event.position().x())
        event.accept()

    def leaveEvent(self, event) -> None:
        self._hover = None
        self.update()
        super().leaveEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        shift = bool(event.modifiers() & Qt.KeyboardModifier.ShiftModifier)
        step = self._fps if shift else 1
        if key == Qt.Key.Key_Left:
            self.frame_scrubbed.emit(max(0, self._current - step))
        elif key == Qt.Key.Key_Right:
            self.frame_scrubbed.emit(min(self._total - 1, self._current + step))
        elif key == Qt.Key.Key_Home:
            self.frame_scrubbed.emit(0)
        elif key == Qt.Key.Key_End:
            self.frame_scrubbed.emit(self._total - 1)
        elif key == Qt.Key.Key_Delete:
            self.delete_requested.emit()
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._clamp_view()

    # --- painting -----------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        painter.fillRect(self.rect(), BACKGROUND)
        painter.fillRect(QRectF(0, 0, w, RULER_HEIGHT), RULER_BACKGROUND)
        painter.fillRect(QRectF(0, RULER_HEIGHT, w, TRACK_HEIGHT), TRACK_BACKGROUND)
        painter.setClipRect(QRectF(MARGIN - 1, 0, w - 2 * MARGIN + 2, h))
        self._paint_range(painter)
        self._paint_ruler(painter)
        self._paint_keyframes(painter)
        self._paint_playhead(painter)
        painter.setClipping(False)
        painter.end()

    def _paint_range(self, painter: QPainter) -> None:
        x0, x1 = self.x_of(0), self.x_of(self._total)
        painter.fillRect(QRectF(x0, RULER_HEIGHT, x1 - x0, TRACK_HEIGHT), QColor(46, 46, 46))
        if self._keyframes:
            first, last = self._keyframes[0].frame, self._keyframes[-1].frame
            y = RULER_HEIGHT + TRACK_HEIGHT / 2
            painter.setPen(QPen(SEGMENT_COLOR, 2))
            painter.drawLine(QPointF(self.x_of(first), y), QPointF(self.x_of(last), y))
            if self._loop and len(self._keyframes) > 1:
                painter.setPen(QPen(LOOP_COLOR, 2, Qt.PenStyle.DashLine))
                painter.drawLine(QPointF(self.x_of(last), y), QPointF(self.x_of(self._total), y))

    def _tick_step(self) -> int:
        """Frames between labelled ticks: the first nice number that leaves `LABEL_SPACING_PX` between labels."""
        need = LABEL_SPACING_PX / max(self.pixels_per_frame, 1e-9)
        return next((step for step in TICK_STEPS if step >= need), int(math.ceil(need / TICK_STEPS[-1]) * TICK_STEPS[-1]))

    def _paint_ruler(self, painter: QPainter) -> None:
        step = self._tick_step()
        font = QFont(painter.font())
        font.setPointSizeF(max(6.5, font.pointSizeF() - 1.5))
        painter.setFont(font)
        first = int(self.frame_at(MARGIN))
        last = int(self.frame_at(self.width() - MARGIN)) + 1
        minor = max(1, step // 5)
        for frame in range(max(0, first - first % minor), min(self._total, last) + 1, minor):
            x = self.x_of(frame)
            is_major = frame % step == 0
            is_second = frame % self._fps == 0
            painter.setPen(QPen(SECOND_COLOR if is_second else TICK_COLOR, 1))
            height = 10 if is_major else 5
            painter.drawLine(QPointF(x, RULER_HEIGHT - height), QPointF(x, RULER_HEIGHT))
            if is_major:
                painter.setPen(TEXT_COLOR)
                label = f"{frame}" if not is_second or frame == 0 else f"{frame} · {frame // self._fps}s"
                painter.drawText(QPointF(x + 3, RULER_HEIGHT - 11), label)
        painter.setPen(QPen(TICK_COLOR, 1))
        painter.drawLine(QPointF(MARGIN, RULER_HEIGHT), QPointF(self.width() - MARGIN, RULER_HEIGHT))

    def _marker(self, x: float, y: float, half: float) -> QPolygonF:
        return QPolygonF([QPointF(x, y - half), QPointF(x + half, y), QPointF(x, y + half), QPointF(x - half, y)])

    def _paint_keyframes(self, painter: QPainter) -> None:
        y = RULER_HEIGHT + TRACK_HEIGHT / 2
        highlight = QColor(config.HIGHLIGHT_COLOR)
        font = QFont(painter.font())
        font.setPointSizeF(max(6.5, font.pointSizeF() - 1.5))
        painter.setFont(font)
        for index, key in enumerate(self._keyframes):
            x = self.x_of(key.frame)
            selected = key is self._selected
            hovered = key is self._hover
            half = MARKER_HALF + (2 if selected else 0) + (1 if hovered else 0)
            painter.setPen(QPen(highlight.lighter(140) if selected else MARKER_OUTLINE, 1.5 if selected else 1))
            painter.setBrush(highlight if selected else (MARKER_COLOR.darker(115) if hovered else MARKER_COLOR))
            painter.drawPolygon(self._marker(x, y, half))
            painter.setPen(TEXT_COLOR)
            painter.drawText(QPointF(x - 3 - (4 if index >= 9 else 0), RULER_HEIGHT + TRACK_HEIGHT - 3), f"{index + 1}")

    def _paint_playhead(self, painter: QPainter) -> None:
        x = self.x_of(self._current)
        color = QColor(config.HIGHLIGHT_COLOR)
        painter.setPen(QPen(color, 1.5))
        painter.drawLine(QPointF(x, 4), QPointF(x, RULER_HEIGHT + TRACK_HEIGHT))
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawPolygon(QPolygonF([QPointF(x - 6, 2), QPointF(x + 6, 2), QPointF(x, 11)]))


__all__ = ["Timeline", "RULER_HEIGHT", "TRACK_HEIGHT"]
