"""The main window's viewport: frames the flame as an *image* of a chosen resolution and lets the
user look at it (view pan/zoom) or re-compose it (camera pan/zoom).

Two layers of geometry:

* **image** — `document.image_size` pixels, framed by `flame.camera.at_size(...)`. This is what a
  final render would produce; its aspect ratio is what the resolution dropdown chooses.
* **view** — how that image sits in the widget: `zoom` screen pixels per image pixel and an offset.
  "Fit" shows the whole image letterboxed; up to 300 % magnifies it.

Only the *visible* part of the image is rendered, at screen density, so a 6000×4800 print size costs
no more than the widget's pixels, and zooming in genuinely reveals more detail.

Mouse: left-drag pans the view, wheel zooms the view about the cursor. With **Ctrl** the same
gestures move/zoom the flame's camera instead (changing the composition). Double-click re-centres
the composition. Interaction renders at `INTERACTIVE_SCALE`; full resolution follows once it settles.

Transform edits (the Transform Editor) are debounced: the running render is cancelled at once, and a
fresh full render starts `EDIT_RENDER_DELAY_MS` after the last change, so a drag in the editor does not
keep the engine churning — the editor's own small preview follows the drag instead.
"""

from __future__ import annotations


import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import config
from ..fractal.scene import Camera
from ..render.service import PRIORITY_VIEWPORT, RenderService
from ..render.settings import RenderSettings, RenderStats
from .fractal_document import FractalDocument

MAX_ZOOM = 3.0                  # 300 %
VIEW_ZOOM_STEP = 1.25           # per wheel notch
CAMERA_ZOOM_PER_NOTCH = 0.25    # Apophysis zoom units (powers of two)
EMPTY_BACKGROUND = QColor(24, 24, 24)
FRAME_COLOR = QColor(70, 70, 70)


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
        self._document: FractalDocument | None = None
        self._service: RenderService | None = None
        self._image: QImage | None = None
        self._image_region = QRectF()           # part of the image (image pixels) the rendered picture covers
        self._regions: dict[object, QRectF] = {}   # request key -> region it will cover
        self._image_rect = QRect()              # screen rect of the visible part of the image
        self._generation = 0
        self._current_key: object = None
        self._stats: RenderStats | None = None
        self._zoom: float | None = None         # None = fit
        self._offset = QPointF(0, 0)            # screen position of image pixel (0, 0)
        self._drag: _Drag | None = None
        self._settle = QTimer(self, singleShot=True, interval=config.INTERACTION_SETTLE_MS)
        self._settle.timeout.connect(self._render_full)
        self._resize_timer = QTimer(self, singleShot=True, interval=150)
        self._resize_timer.timeout.connect(self._on_resized)
        self._edit_timer = QTimer(self, singleShot=True, interval=config.EDIT_RENDER_DELAY_MS)
        self._edit_timer.timeout.connect(self._render_full)
        self.settings = RenderSettings()
        self.render_scale = 1.0   # preview detail: fraction of the screen resolution the render uses

    # --- wiring -------------------------------------------------------------
    def bind(self, document: FractalDocument, service: RenderService) -> None:
        """Attach the document to show and the service that renders it."""
        self._document = document
        self._service = service
        document.flame_replaced.connect(self._on_flame_replaced)
        document.camera_changed.connect(self._render_interactive)
        document.palette_changed.connect(self._render_interactive)
        document.coloring_changed.connect(self._render_interactive)
        document.image_size_changed.connect(self._on_image_size_changed)
        document.xform_changed.connect(self._render_after_edit)
        document.transforms_changed.connect(self._render_after_edit)
        document.flame_restored.connect(self._on_flame_restored)
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)

    def set_render_scale(self, fraction: float) -> None:
        """Render the preview at `fraction` of the screen resolution (scaled up on screen) and re-render."""
        fraction = max(0.05, min(1.0, float(fraction)))
        if fraction != self.render_scale:
            self.render_scale = fraction
            self._render_full()

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
        return self._stats

    @property
    def generation(self) -> int:
        """Increments with every render request (tests use it to await results)."""
        return self._generation

    @property
    def image_size(self) -> tuple[int, int]:
        return self._document.image_size if self._document is not None else (800, 600)

    @property
    def image_rect(self) -> QRect:
        """Screen rectangle of the visible part of the image."""
        return QRect(self._image_rect)

    def fit_zoom(self) -> float:
        """Screen pixels per image pixel at which the whole image fits the widget."""
        iw, ih = self.image_size
        return max(1e-6, min(self.width() / iw, self.height() / ih))

    def min_zoom(self) -> float:
        """Zooming out stops where the whole image is visible (or at 300 % for tiny images)."""
        return min(self.fit_zoom(), MAX_ZOOM)

    def zoom(self) -> float:
        return self.fit_zoom() if self._zoom is None else self._zoom

    @property
    def is_fit(self) -> bool:
        return self._zoom is None

    def image_camera(self) -> Camera | None:
        """Camera framing the full image at its resolution."""
        if self._document is None or self._document.flame is None:
            return None
        return self._document.flame.camera.at_size(*self.image_size)

    # --- view control (does not modify the flame) ------------------------------
    def set_zoom(self, zoom: float | None, anchor: QPointF | None = None) -> None:
        """Set the view zoom (None = fit). `anchor` is the screen point that stays put."""
        if zoom is None:
            self._zoom = None
            self._layout()
            self._after_view_change()
            return
        zoom = max(self.min_zoom(), min(MAX_ZOOM, float(zoom)))
        anchor = anchor if anchor is not None else QPointF(self.width() / 2, self.height() / 2)
        old = self.zoom()
        image_point = (anchor - self._offset) / old
        self._zoom = zoom
        self._offset = anchor - image_point * zoom
        self._layout()
        self._after_view_change()

    def zoom_to_fit(self) -> None:
        self.set_zoom(None)

    def pan_view(self, delta: QPoint | QPointF) -> None:
        """Scroll the view by `delta` screen pixels (clamped so the image stays in view)."""
        if self._zoom is None:
            self._zoom = self.fit_zoom()  # panning leaves fit mode (fit has nothing to pan anyway)
        self._offset = self._offset + QPointF(delta)
        self._layout()
        self._after_view_change()

    def _after_view_change(self) -> None:
        self.view_changed.emit(self.zoom(), self.fit_zoom())
        self._render_interactive()

    # --- geometry -------------------------------------------------------------
    def _layout(self) -> None:
        """Clamp the offset (image centred when smaller than the widget) and compute the visible rect."""
        iw, ih = self.image_size
        z = self.zoom()
        shown_w, shown_h = iw * z, ih * z
        w, h = self.width(), self.height()
        if self._zoom is None or shown_w <= w:
            x = (w - shown_w) / 2
        else:
            x = min(0.0, max(w - shown_w, self._offset.x()))
        if self._zoom is None or shown_h <= h:
            y = (h - shown_h) / 2
        else:
            y = min(0.0, max(h - shown_h, self._offset.y()))
        self._offset = QPointF(x, y)
        visible = QRectF(x, y, shown_w, shown_h).intersected(QRectF(0, 0, w, h))
        self._image_rect = visible.toAlignedRect()

    def screen_to_image(self, pos: QPointF) -> QPointF:
        """Image pixel coordinates under a screen point."""
        z = self.zoom()
        return QPointF((pos.x() - self._offset.x()) / z, (pos.y() - self._offset.y()) / z)

    def fractal_point_at(self, pos: QPointF, camera: Camera | None = None) -> tuple[float, float] | None:
        """Fractal-space point under a screen point (None without a flame)."""
        camera = camera or self.image_camera()
        if camera is None:
            return None
        p = self.screen_to_image(pos)
        return camera.unproject(p.x(), p.y(), camera.width, camera.height)

    def render_camera(self) -> tuple[Camera, int, int] | None:
        """Camera and size that render exactly the visible part of the image at screen density."""
        camera = self.image_camera()
        if camera is None or self._image_rect.isEmpty():
            return None
        z = self.zoom()
        rect = self._image_rect
        centre = self.screen_to_image(QPointF(rect.x() + rect.width() / 2, rect.y() + rect.height() / 2))
        cx, cy = camera.unproject(centre.x(), centre.y(), camera.width, camera.height)
        ppu = camera.pixels_per_unit(camera.width, camera.height) * z
        return (Camera((cx, cy), ppu, 0.0, camera.rotate, rect.width(), rect.height(),
                       camera.pitch, camera.yaw, camera.perspective, camera.zpos, camera.dof), rect.width(), rect.height())

    # --- rendering ----------------------------------------------------------
    def _on_flame_replaced(self) -> None:
        self._edit_timer.stop()
        self._clear_image()
        self._zoom = None
        self._layout()
        self.view_changed.emit(self.zoom(), self.fit_zoom())
        self.update()
        self._render_full()

    def _on_flame_restored(self) -> None:
        """Undo / redo / paste: anything may have changed, so re-render (keeping the view zoom)."""
        self._layout()
        self.view_changed.emit(self.zoom(), self.fit_zoom())
        self.update()
        self._render_full()

    def _on_image_size_changed(self) -> None:
        self._clear_image()   # a new framing: the old picture would mislead
        self._zoom = None
        self._layout()
        self.view_changed.emit(self.zoom(), self.fit_zoom())
        self.update()
        self._render_interactive()

    def _clear_image(self) -> None:
        self._image = None
        self._stats = None
        self._image_region = QRectF()
        self.image_changed.emit(None)

    def _render_full(self) -> None:
        self._settle.stop()
        self._edit_timer.stop()
        self._submit(1.0)

    def _render_interactive(self) -> None:
        self._submit(config.INTERACTIVE_SCALE)
        self._settle.start()

    def _render_after_edit(self, *_args) -> None:
        """A transform was edited: stop rendering the old flame and re-render once the edits pause."""
        self._settle.stop()
        if self._service is not None and self._current_key is not None:
            self._service.cancel(self._current_key)
        self._edit_timer.start()

    @property
    def edit_render_pending(self) -> bool:
        """True while a render is being held back after a transform edit (tests)."""
        return self._edit_timer.isActive()

    def _submit(self, scale: float) -> None:
        if self._document is None or self._service is None or self._document.flame is None:
            return
        self._layout()
        target = self.render_camera()
        if target is None:
            return
        camera, width, height = target
        if self._current_key is not None:
            self._service.cancel(self._current_key)
        self._generation += 1
        self._current_key = ("viewport", self._generation)
        rect, z = self._image_rect, self.zoom()
        self._regions = {self._current_key: QRectF((rect.x() - self._offset.x()) / z, (rect.y() - self._offset.y()) / z,
                                                   rect.width() / z, rect.height() / z)}
        flame = self._document.flame.copy()
        flame.camera = camera
        settings = (self.settings.with_size(width, height).scaled(scale * self.render_scale)
                    .for_zoom(self._document.flame.camera.zoom).within_bucket_limit())
        if scale < 1.0:
            settings = settings.with_refine(0.0)   # the transient low-resolution render: the full one follows
        self._service.submit(self._current_key, flame, settings, PRIORITY_VIEWPORT)

    def _on_pass(self, key: object, image: np.ndarray, stats: RenderStats) -> None:
        if key != self._current_key:
            return  # a superseded request finishing a pass we no longer want
        self._image = _to_qimage(image)
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
        if self._image is not None and not self._image_region.isEmpty():
            # draw the picture where its part of the image sits under the *current* view, so panning and
            # zooming feel immediate; the re-render replaces it when it lands
            z, region = self.zoom(), self._image_region
            target = QRectF(self._offset.x() + region.x() * z, self._offset.y() + region.y() * z,
                            region.width() * z, region.height() * z)
            painter.setClipRect(self._image_rect)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, abs(target.width() - self._image.width()) > 0.5)
            painter.drawImage(target, self._image)
            painter.setClipping(False)
        if self._document is not None and self._document.flame is not None:
            painter.setPen(QPen(FRAME_COLOR, 1))
            painter.drawRect(self._image_rect.adjusted(0, 0, -1, -1))
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self._layout()
        self.view_changed.emit(self.zoom(), self.fit_zoom())
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
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.zoom_camera_at(event.position(), steps * CAMERA_ZOOM_PER_NOTCH)
        else:
            self.set_zoom(self.zoom() * (VIEW_ZOOM_STEP ** steps), event.position())
        event.accept()

    def zoom_camera_at(self, pos: QPointF, delta_zoom: float) -> None:
        """Change the flame's zoom by `delta_zoom` (powers of two) keeping the fractal point under `pos` fixed."""
        anchor = self.fractal_point_at(pos)
        if anchor is None:
            return
        camera = self._document.flame.camera
        camera.zoom += delta_zoom
        moved = self.fractal_point_at(pos)
        cx, cy = camera.center
        self._document.set_view(center=(cx + anchor[0] - moved[0], cy + anchor[1] - moved[1]))

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton or self._document is None or self._document.flame is None:
            return
        compose = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        self._drag = _Drag(event.position(), self._offset, self._document.flame.camera.center, compose, self.image_camera())
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
            self._offset = drag.offset
            self.pan_view(event.position() - drag.origin)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        """Double-click re-centres the composition on the clicked point."""
        point = self.fractal_point_at(event.position())
        if point is not None:
            self._document.set_view(center=point)


class _Drag:
    __slots__ = ("origin", "offset", "center", "compose", "camera")

    def __init__(self, origin: QPointF, offset: QPointF, center, compose: bool, camera: Camera | None):
        self.origin, self.offset, self.center, self.compose, self.camera = origin, QPointF(offset), center, compose, camera


def _to_qimage(rgba: np.ndarray) -> QImage:
    h, w = rgba.shape[:2]
    data = np.ascontiguousarray(rgba)
    return QImage(data.data, w, h, w * 4, QImage.Format.Format_RGBA8888).copy()


__all__ = ["FractalViewport", "MAX_ZOOM"]
