"""The main window's viewport: frames the flame as an *image* of a chosen resolution and lets the
user look at it (view pan/zoom) or re-compose it (camera pan/zoom).

Two layers of geometry:

* **image** — `document.image_size` pixels, framed by `flame.camera.at_size(...)`. This is what a
  final render would produce; its aspect ratio is what the resolution dropdown chooses.
* **view** — how that image sits in the widget (`ViewGeometry`): zoom and offset, fit by default.

Only the *visible* part of the image is rendered, at screen density, so a 6000×4800 print size costs
no more than the widget's pixels, and zooming in genuinely reveals more detail.

Mouse: left-drag pans the view, wheel zooms the view about the cursor. With **Ctrl** the same
gestures move/zoom the flame's camera instead (changing the composition). Double-click re-centres
the composition. Interaction renders at `INTERACTIVE_SCALE`; full resolution follows once it settles.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import config
from ..fractal.scene import Camera
from ..render.service import PRIORITY_VIEWPORT, RenderService
from ..render.settings import RenderSettings, RenderStats
from ..widgets.images import rgba_to_qimage
from .fractal_document import FractalDocument
from .view_geometry import MAX_ZOOM, ViewGeometry

VIEW_ZOOM_STEP = 1.25           # per wheel notch
CAMERA_ZOOM_PER_NOTCH = 0.25    # Apophysis zoom units (powers of two)
EMPTY_BACKGROUND = QColor(24, 24, 24)
FRAME_COLOR = QColor(70, 70, 70)
RESIZE_SETTLE_MS = 150


@dataclass
class _Drag:
    """State captured at mouse press for a pan (view) or a camera move (compose)."""
    origin: QPointF
    offset: QPointF
    center: tuple[float, float]
    compose: bool
    camera: Camera | None


class FractalViewport(QWidget):
    """Paints the latest render of the document's flame and re-renders on any change of what is visible.

    Signals:
        render_progress(RenderStats): After every delivered pass (of the request being shown).
        render_failed(str): The render could not be set up (e.g. no usable transform).
        image_changed(QImage | None): The picture on screen changed (other previews mirror it).
        view_changed(float, float): (zoom, fit zoom) after any view change — for the zoom box.
    """
    render_progress = Signal(object)
    render_failed = Signal(str)
    image_changed = Signal(object)
    view_changed = Signal(float, float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(160, 120)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.view = ViewGeometry(widget_size=(self.width(), self.height()))
        self.settings = RenderSettings()
        self._document: FractalDocument | None = None
        self._service: RenderService | None = None
        self._image: QImage | None = None
        self._image_region = QRectF()              # part of the image (image pixels) the picture covers
        self._regions: dict[object, QRectF] = {}   # request key -> region it will cover
        self._generation = 0
        self._current_key: object = None
        self._stats: RenderStats | None = None
        self._drag: _Drag | None = None
        self._settle = QTimer(self, singleShot=True, interval=config.INTERACTION_SETTLE_MS)
        self._settle.timeout.connect(self._render_full)
        self._resize_timer = QTimer(self, singleShot=True, interval=RESIZE_SETTLE_MS)
        self._resize_timer.timeout.connect(self._render_interactive)

    # --- wiring -------------------------------------------------------------
    def bind(self, document: FractalDocument, service: RenderService) -> None:
        """Attach the document to show and the service that renders it."""
        self._document = document
        self._service = service
        document.flame_replaced.connect(self._on_flame_replaced)
        document.camera_changed.connect(self._render_interactive)
        document.palette_changed.connect(self._render_interactive)
        document.image_size_changed.connect(self._on_image_size_changed)
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)

    def set_render_settings(self, settings: RenderSettings) -> None:
        """Change passes / quality etc.; re-renders the current view."""
        self.settings = settings
        self._render_full()

    # --- state --------------------------------------------------------------
    @property
    def image(self) -> QImage | None:
        """The last image delivered for the current flame (None before the first pass)."""
        return self._image

    @property
    def stats(self) -> RenderStats | None:
        """Progress of the render being shown, or None."""
        return self._stats

    @property
    def generation(self) -> int:
        """Increments with every render request (tests use it to await results)."""
        return self._generation

    @property
    def image_size(self) -> tuple[int, int]:
        """Output resolution being framed."""
        return self.view.image_size

    @property
    def image_rect(self) -> QRect:
        """Screen rectangle of the visible part of the image."""
        return self.view.image_rect

    @property
    def is_fit(self) -> bool:
        """True while the whole image is shown (no explicit zoom)."""
        return self.view.is_fit

    def zoom(self) -> float:
        """View zoom: screen pixels per image pixel."""
        return self.view.zoom()

    def fit_zoom(self) -> float:
        """The zoom at which the whole image fits the widget."""
        return self.view.fit_zoom()

    def image_camera(self) -> Camera | None:
        """Camera framing the full image at its resolution."""
        if self._document is None or self._document.flame is None:
            return None
        return self._document.flame.camera.at_size(*self.view.image_size)

    # --- view control (does not modify the flame) ------------------------------
    def set_zoom(self, zoom: float | None, anchor: QPointF | None = None) -> None:
        """Set the view zoom (None = fit). `anchor` is the screen point that stays put."""
        self.view.set_zoom(zoom, anchor)
        self._after_view_change()

    def zoom_to_fit(self) -> None:
        """Show the whole image."""
        self.set_zoom(None)

    def pan_view(self, delta: QPointF) -> None:
        """Scroll the view by `delta` screen pixels (clamped so the image stays in view)."""
        self.view.pan(QPointF(delta))
        self._after_view_change()

    def screen_to_image(self, pos: QPointF) -> QPointF:
        """Image pixel coordinates under a screen point."""
        return self.view.screen_to_image(pos)

    def fractal_point_at(self, pos: QPointF, camera: Camera | None = None) -> tuple[float, float] | None:
        """Fractal-space point under a screen point (None without a flame)."""
        camera = camera or self.image_camera()
        if camera is None:
            return None
        p = self.view.screen_to_image(pos)
        return camera.unproject(p.x(), p.y(), camera.width, camera.height)

    def render_camera(self) -> tuple[Camera, int, int] | None:
        """Camera and size that render exactly the visible part of the image at screen density."""
        camera = self.image_camera()
        rect = self.view.image_rect
        if camera is None or rect.isEmpty():
            return None
        centre = self.view.screen_to_image(QPointF(rect.x() + rect.width() / 2, rect.y() + rect.height() / 2))
        cx, cy = camera.unproject(centre.x(), centre.y(), camera.width, camera.height)
        ppu = camera.pixels_per_unit(camera.width, camera.height) * self.view.zoom()
        return Camera((cx, cy), ppu, 0.0, camera.rotate, rect.width(), rect.height()), rect.width(), rect.height()

    # --- composition (modifies the flame, undoably) ---------------------------------
    def zoom_camera_at(self, pos: QPointF, delta_zoom: float) -> None:
        """Change the flame's zoom by `delta_zoom` (powers of two) keeping the fractal point under `pos` fixed."""
        anchor = self.fractal_point_at(pos)
        if anchor is None:
            return
        zoomed = self._document.flame.camera.copy()   # work on a copy: the document records the edit as one step
        zoomed.zoom += delta_zoom
        moved = self.fractal_point_at(pos, zoomed.at_size(*self.view.image_size))
        cx, cy = zoomed.center
        self._document.set_view(center=(cx + anchor[0] - moved[0], cy + anchor[1] - moved[1]), zoom=zoomed.zoom)

    # --- rendering ----------------------------------------------------------
    def _after_view_change(self) -> None:
        self.view_changed.emit(self.view.zoom(), self.view.fit_zoom())
        self._render_interactive()

    def _on_flame_replaced(self) -> None:
        self._clear_image()
        self.view.set_image_size(self._document.image_size)
        self.view_changed.emit(self.view.zoom(), self.view.fit_zoom())
        self.update()
        self._render_full()

    def _on_image_size_changed(self) -> None:
        self._clear_image()   # a new framing: the old picture would mislead
        self.view.set_image_size(self._document.image_size)
        self.view_changed.emit(self.view.zoom(), self.view.fit_zoom())
        self.update()
        self._render_interactive()

    def _clear_image(self) -> None:
        self._image = None
        self._stats = None
        self._image_region = QRectF()
        self.image_changed.emit(None)

    def _render_full(self) -> None:
        self._settle.stop()
        self._submit(1.0)

    def _render_interactive(self) -> None:
        self._submit(config.INTERACTIVE_SCALE)
        self._settle.start()

    def _submit(self, scale: float) -> None:
        """Ask the service for the visible region at `scale` of screen density, superseding the previous request."""
        if self._document is None or self._service is None or self._document.flame is None:
            return
        target = self.render_camera()
        if target is None:
            return
        camera, width, height = target
        if self._current_key is not None:
            self._service.cancel(self._current_key)
        self._generation += 1
        self._current_key = ("viewport", self._generation)
        self._regions = {self._current_key: self.view.visible_region()}
        flame = self._document.flame.copy()
        flame.camera = camera
        self._service.submit(self._current_key, flame, self.settings.with_size(width, height).scaled(scale), PRIORITY_VIEWPORT)

    def _on_pass(self, key: object, image: np.ndarray, stats: RenderStats) -> None:
        if key != self._current_key:
            return  # a superseded request finishing a pass we no longer want
        self._image = rgba_to_qimage(image)
        self._image_region = self._regions.get(key, self._image_region)
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
        image_rect = self.view.image_rect
        if self._image is not None and not self._image_region.isEmpty():
            # the picture goes where its part of the image sits under the *current* view, so panning and
            # zooming feel immediate; the re-render replaces it when it lands
            target = self.view.image_to_screen(self._image_region)
            painter.setClipRect(image_rect)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, abs(target.width() - self._image.width()) > 0.5)
            painter.drawImage(target, self._image)
            painter.setClipping(False)
        if self._document is not None and self._document.flame is not None:
            painter.setPen(QPen(FRAME_COLOR, 1))
            painter.drawRect(image_rect.adjusted(0, 0, -1, -1))
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.view.set_widget_size(self.width(), self.height())
        self.view_changed.emit(self.view.zoom(), self.view.fit_zoom())
        if self._document is not None and self._document.flame is not None:
            self._resize_timer.start()

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self._document is None or self._document.flame is None:
            return
        steps = event.angleDelta().y() / 120.0
        if steps == 0:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_camera_at(event.position(), steps * CAMERA_ZOOM_PER_NOTCH)
        else:
            self.set_zoom(self.view.zoom() * (VIEW_ZOOM_STEP ** steps), event.position())
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._document is None or self._document.flame is None:
            return
        compose = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._drag = _Drag(event.position(), self.view.offset, self._document.flame.camera.center, compose, self.image_camera())
        self.setCursor(Qt.CursorShape.SizeAllCursor if compose else Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None or self._document is None or self._document.flame is None:
            return
        drag = self._drag
        if drag.compose:
            start = self.fractal_point_at(drag.origin, drag.camera)
            now = self.fractal_point_at(event.position(), drag.camera)
            cx, cy = drag.center
            self._document.set_view(center=(cx - (now[0] - start[0]), cy - (now[1] - start[1])))
        else:
            self.view.set_offset(drag.offset + (event.position() - drag.origin))
            self._after_view_change()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click re-centres the composition on the clicked point."""
        point = self.fractal_point_at(event.position())
        if point is not None:
            self._document.set_view(center=point)


__all__ = ["FractalViewport", "MAX_ZOOM"]
