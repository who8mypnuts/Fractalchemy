"""The main window's viewport: shows the current flame and drives the preview renders.

Interaction policy (see the design notes in README):

* any camera change or resize renders at `INTERACTIVE_SCALE` of the viewport size;
* `INTERACTION_SETTLE_MS` after the last change, a full-resolution render starts;
* every request gets a new generation number, so a pass from an older request that
  arrives late is ignored, and the render service is told to drop the older job.

Wheel zooms about the cursor; left-drag pans. The widget only paints the latest image.
"""

from __future__ import annotations

import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import config
from ..render.service import PRIORITY_VIEWPORT, RenderService
from ..render.settings import RenderSettings, RenderStats
from .fractal_document import FractalDocument

ZOOM_PER_WHEEL_STEP = 0.25   # in Apophysis zoom units (powers of two) per 15° wheel notch
EMPTY_BACKGROUND = QColor(24, 24, 24)


class FractalViewport(QWidget):
    """Paints the latest render of the document's flame and re-renders on camera changes.

    Signals:
        render_progress(RenderStats): After every delivered pass (of the request being shown).
        render_failed(str): The render could not be set up (e.g. no usable transform).
        image_changed(QImage | None): The picture on screen changed (other previews mirror it).
    """
    render_progress = Signal(object)
    render_failed = Signal(str)
    image_changed = Signal(object)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)
        self.setMouseTracking(False)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self._document: FractalDocument | None = None
        self._service: RenderService | None = None
        self._image: QImage | None = None
        self._image_is_preview = False
        self._generation = 0
        self._current_key: object = None
        self._stats: RenderStats | None = None
        self._drag_origin: QPoint | None = None
        self._drag_center: tuple[float, float] | None = None
        self._settle = QTimer(self, singleShot=True, interval=config.INTERACTION_SETTLE_MS)
        self._settle.timeout.connect(self._render_full)
        self._resize_timer = QTimer(self, singleShot=True, interval=150)
        self._resize_timer.timeout.connect(self._on_resized)
        self.settings = RenderSettings()

    # --- wiring -------------------------------------------------------------
    def bind(self, document: FractalDocument, service: RenderService) -> None:
        """Attach the document to show and the service that renders it."""
        self._document = document
        self._service = service
        document.flame_replaced.connect(self._on_flame_replaced)
        document.camera_changed.connect(self._render_interactive)
        document.palette_changed.connect(self._render_interactive)
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)

    @property
    def image(self) -> QImage | None:
        """The last image delivered for the current flame (None before the first pass)."""
        return self._image

    @property
    def stats(self) -> RenderStats | None:
        return self._stats

    @property
    def generation(self) -> int:
        """Increments with every render request (tests use it to await results)."""
        return self._generation

    # --- rendering ----------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        self._image = None
        self._stats = None
        self.image_changed.emit(None)
        self.update()
        self._render_full()

    def _render_full(self) -> None:
        self._settle.stop()
        self._submit(1.0)

    def _render_interactive(self) -> None:
        self._submit(config.INTERACTIVE_SCALE)
        self._settle.start()

    def _submit(self, scale: float) -> None:
        if self._document is None or self._service is None or self._document.flame is None:
            return
        if self._current_key is not None:
            self._service.cancel(self._current_key)
        self._generation += 1
        self._current_key = ("viewport", self._generation)
        settings = self.settings.with_size(self.width(), self.height()).scaled(scale)
        self._service.submit(self._current_key, self._document.flame, settings, PRIORITY_VIEWPORT)

    def _on_pass(self, key: object, image: np.ndarray, stats: RenderStats) -> None:
        if key != self._current_key:
            return  # a superseded request finishing a pass we no longer want
        self._image = _to_qimage(image)
        self._image_is_preview = image.shape[1] < self.width()
        self._stats = stats
        self.render_progress.emit(stats)
        self.image_changed.emit(self._image)
        self.update()

    def _on_failed(self, key: object, message: str) -> None:
        if key == self._current_key:
            self.render_failed.emit(message)

    # --- Qt events ----------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), EMPTY_BACKGROUND)
        if self._image is not None:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._image_is_preview)
            painter.drawImage(QRect(0, 0, self.width(), self.height()), self._image)
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._document is not None and self._document.flame is not None:
            self._resize_timer.start()

    def _on_resized(self) -> None:
        self._render_interactive()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._document is None or self._document.flame is None:
            return
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            return
        self.zoom_at(event.position(), steps * ZOOM_PER_WHEEL_STEP)
        event.accept()

    def zoom_at(self, pos: QPointF, delta_zoom: float) -> None:
        """Zoom by `delta_zoom` (powers of two) keeping the fractal point under `pos` fixed."""
        camera = self._document.flame.camera
        w, h = self.width(), self.height()
        anchor = camera.unproject(pos.x(), pos.y(), w, h)
        camera.zoom += delta_zoom
        moved = camera.unproject(pos.x(), pos.y(), w, h)
        cx, cy = camera.center
        self._document.set_view(center=(cx + anchor[0] - moved[0], cy + anchor[1] - moved[1]))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._document is not None and self._document.flame is not None:
            self._drag_origin = event.position().toPoint()
            self._drag_center = self._document.flame.camera.center
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag_origin is None or self._document is None or self._document.flame is None:
            return
        camera = self._document.flame.camera
        w, h = self.width(), self.height()
        camera.center = self._drag_center
        start = camera.unproject(self._drag_origin.x(), self._drag_origin.y(), w, h)
        now = camera.unproject(event.position().x(), event.position().y(), w, h)
        cx, cy = self._drag_center
        self._document.set_view(center=(cx - (now[0] - start[0]), cy - (now[1] - start[1])))

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_origin = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click re-centres on the clicked point."""
        if self._document is not None and self._document.flame is not None:
            point = self._document.flame.camera.unproject(event.position().x(), event.position().y(), self.width(), self.height())
            self._document.set_view(center=point)


def _to_qimage(rgba: np.ndarray) -> QImage:
    h, w = rgba.shape[:2]
    data = np.ascontiguousarray(rgba)
    return QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()
