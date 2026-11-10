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

Composition guides (`set_guides`): rule-of-thirds, golden-ratio and centre lines drawn over the whole
image (not just the visible part), as Apophysis's guidelines do.

Transform edits (the Transform Editor) are debounced: the running render is cancelled at once, and a
fresh full render starts `EDIT_RENDER_DELAY_MS` after the last change, so a drag in the editor does not
keep the engine churning — the editor's own small preview follows the drag instead.

Colouring edits (brightness, gamma, threshold, vibrancy, contrast, background, curves — and undoing one) do not
render again at all: the render's histogram is kept (`RenderService.submit(retain=True)`) and only tone-mapped again
(`RenderService.retone`), so the picture changes at once at the quality it had already reached, and refining carries
on. That applies while everything else that shapes the picture is what the current render was made of (compared
through `_render_signature`); otherwise — and when the service has no job left to re-colour — a normal render starts.
"""

from __future__ import annotations


import numpy as np
from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QPen, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from .. import config
from ..fractal.scene import Camera
from ..render.service import PRIORITY_EDITOR, PRIORITY_VIEWPORT, RenderService
from ..render.settings import RenderSettings, RenderStats
from .fractal_document import FractalDocument
from ..widgets.theming import theme_color

MAX_ZOOM = 3.0                  # 300 %
VIEW_ZOOM_STEP = 1.25           # per wheel notch
CAMERA_ZOOM_PER_NOTCH = 0.25    # Apophysis zoom units (powers of two)
FRAME_COLOR = QColor(70, 70, 70)
GOLDEN = (3 - 5 ** 0.5) / 2     # 0.381966…: the golden section of a length (1 − 1/φ)
GUIDE_FRACTIONS: dict[str, tuple[float, ...]] = {
    "thirds": (1 / 3, 2 / 3),
    "golden": (GOLDEN, 1 - GOLDEN),
    "center": (0.5,),
}
GUIDE_COLORS: dict[str, QColor] = {
    "thirds": QColor(255, 255, 255, 150),
    "golden": QColor(255, 208, 64, 170),
    "center": QColor(96, 200, 255, 150),
}
GUIDE_SHADOW = QColor(0, 0, 0, 110)


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
        self._submitted_signature = None       # what the current render was made of, bar the colouring (re-colouring)
        self._compare: tuple[str, object] | None = None    # (label, signature) while the before / after view is on
        self._compare_image: QImage | None = None
        self._compare_signature = None
        self._compare_key: object = None
        self._compare_generation = 0
        self.compare_renders = 0               # comparison renders asked for (tests)
        self.submits = 0                        # renders asked for (tests)
        self.retones = 0                        # re-colourings asked for instead (tests)
        self._guides_shown = False
        self._guide_kinds: tuple[str, ...] = ("thirds",)

    # --- wiring -------------------------------------------------------------
    def bind(self, document: FractalDocument, service: RenderService) -> None:
        """Attach the document to show and the service that renders it."""
        self._document = document
        self._service = service
        document.flame_replaced.connect(self._on_flame_replaced)
        document.camera_changed.connect(self._render_interactive)
        document.palette_changed.connect(self._render_interactive)
        document.coloring_changed.connect(self._on_coloring_changed)
        document.image_size_changed.connect(self._on_image_size_changed)
        document.xform_changed.connect(self._render_after_edit)
        document.transforms_changed.connect(self._render_after_edit)
        document.flame_restored.connect(self._on_flame_restored)
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)
        service.retone_missed.connect(self._on_retone_missed)

    def set_guides(self, shown: bool, kinds=None) -> None:
        """Show / hide the composition guides and choose which (`thirds`, `golden`, `center`); repaints only."""
        self._guides_shown = bool(shown)
        if kinds is not None:
            self._guide_kinds = tuple(k for k in GUIDE_FRACTIONS if k in set(kinds))
        self.update()

    @property
    def guides_shown(self) -> bool:
        return self._guides_shown

    @property
    def guide_kinds(self) -> tuple[str, ...]:
        return self._guide_kinds

    def guide_lines(self) -> list[tuple[str, float, float, float, float]]:
        """The guide lines as (kind, x1, y1, x2, y2) in screen coordinates, clipped to the widget (empty when hidden)."""
        if not self._guides_shown or self._document is None or self._document.flame is None:
            return []
        iw, ih = self.image_size
        z = self.zoom()
        left, top = self._offset.x(), self._offset.y()
        right, bottom = left + iw * z, top + ih * z
        x0, y0 = max(0.0, left), max(0.0, top)
        x1, y1 = min(float(self.width()), right), min(float(self.height()), bottom)
        lines = []
        for kind in self._guide_kinds:
            for f in GUIDE_FRACTIONS[kind]:
                x = left + iw * z * f
                y = top + ih * z * f
                if x0 <= x <= x1:
                    lines.append((kind, x, y0, x, y1))
                if y0 <= y <= y1:
                    lines.append((kind, x0, y, x1, y))
        return lines

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

    def render_camera(self, flame=None) -> tuple[Camera, int, int] | None:
        """Camera and size that render exactly the visible part of the image at screen density (of `flame`'s camera when
        given — the before / after comparison — else the document's)."""
        camera = self.image_camera() if flame is None else flame.camera.at_size(*self.image_size)
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
        """Undo / redo / paste / a script: anything may have changed, the framing included; the old picture stays until the new one lands.
        A live parameter tick (`document.live_edit`) renders at interactive resolution, the full one following once they pause;
        a change of the colouring alone (undoing a gamma drag) only re-colours the current render."""
        self._layout()
        self.view_changed.emit(self.zoom(), self.fit_zoom())
        self.update()
        if self._try_retone():
            return
        if self._document is not None and self._document.live_edit:
            self._render_interactive()
        else:
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

    # --- before / after -------------------------------------------------------------------------------------------
    def set_compare(self, flame, label: str = "Before") -> None:
        """Show `flame` in place of the fractal (rendered once with the same view, then kept while nothing changes), with
        `label` in the corner; None shows the fractal again. A comparison, not an edit: the document is untouched."""
        if flame is None:
            self._compare = None
            self.update()
            return
        signature = (repr(flame.to_dict()), self._image_rect.getRect(), round(self.zoom(), 9), (self._offset.x(), self._offset.y()))
        self._compare = (label, signature)
        if self._compare_image is not None and self._compare_signature == signature:
            self.update()
            return
        target = self.render_camera(flame)
        if target is None or self._service is None:
            return
        camera, width, height = target
        self._compare_image, self._compare_signature = None, signature
        self._compare_generation += 1
        self._compare_key = ("compare", self._compare_generation)
        render = flame.copy()
        render.camera = camera
        settings = self.settings.with_size(width, height).for_zoom(flame.camera.zoom).within_bucket_limit().with_refine(0.0)
        self.compare_renders += 1
        self._service.submit(self._compare_key, render, settings, PRIORITY_EDITOR)     # a quick look goes before the viewport
        self.update()

    @property
    def comparing(self) -> bool:
        return self._compare is not None

    def _paint_compare_label(self, painter: QPainter) -> None:
        label = self._compare[0] + ("" if self._compare_image is not None else " — rendering…")
        font = painter.font()
        font.setBold(True)
        painter.setFont(font)
        box = painter.fontMetrics().boundingRect(label).adjusted(-8, -4, 8, 4)
        box.moveTopLeft(self._image_rect.topLeft() + QPoint(8, 8))
        background = theme_color("window")
        background.setAlpha(200)
        painter.fillRect(box, background)
        painter.setPen(theme_color("window_text"))
        painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label)

    # --- re-colouring ---------------------------------------------------------------------------------------------
    def _render_signature(self):
        """Everything about the flame and the view that shapes the render except its colouring."""
        flame = self._document.flame if self._document is not None else None
        if flame is None:
            return None
        data = flame.to_dict()
        data.pop("coloring", None)
        data.pop("name", None)
        return (repr(data), self._image_rect.getRect(), round(self.zoom(), 9), (self._offset.x(), self._offset.y()))

    def _try_retone(self) -> bool:
        """Re-colour the current render if only the colouring changed since it was asked for; True if so."""
        if (self._service is None or self._current_key is None or self._document is None or self._document.flame is None
                or self._submitted_signature is None or self._render_signature() != self._submitted_signature):
            return False
        self._service.retone(self._current_key, self._document.flame.coloring)
        self.retones += 1
        return True

    def _on_coloring_changed(self) -> None:
        if not self._try_retone():
            self._render_interactive()

    def _on_retone_missed(self, key: object) -> None:
        if key == self._current_key:
            self._render_full()

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
        settings = (self.settings.with_size(width, height).scaled(scale)
                    .for_zoom(self._document.flame.camera.zoom).within_bucket_limit())
        if scale < 1.0:
            settings = settings.with_refine(0.0)   # the transient low-resolution render: the full one follows
        self._submitted_signature = self._render_signature()
        self.submits += 1
        self._service.submit(self._current_key, flame, settings, PRIORITY_VIEWPORT, retain=True)

    def _on_pass(self, key: object, image: np.ndarray, stats: RenderStats) -> None:
        if key == self._compare_key:
            self._compare_image = _to_qimage(image)
            self.update()
            return
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
        painter.fillRect(self.rect(), theme_color("canvas_bg"))
        comparing = self._compare is not None and self._compare_image is not None
        if comparing:
            painter.setClipRect(self._image_rect)
            painter.drawImage(QRectF(self._image_rect), self._compare_image)
            painter.setClipping(False)
        elif self._image is not None and not self._image_region.isEmpty():
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
        self._paint_guides(painter)
        if self._compare is not None:
            self._paint_compare_label(painter)
        painter.end()

    def _paint_guides(self, painter: QPainter) -> None:
        lines = self.guide_lines()
        if not lines:
            return
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        for kind, x1, y1, x2, y2 in lines:
            painter.setPen(QPen(GUIDE_SHADOW, 3))               # a dark halo keeps the line visible on bright areas
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))
            painter.setPen(QPen(GUIDE_COLORS[kind], 1))
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

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
        camera = self._document.flame.camera.copy()          # worked out on a copy: the document makes the edit (one undo step)
        camera.zoom += delta_zoom
        moved = self.fractal_point_at(pos, camera.at_size(*self.image_size))
        cx, cy = camera.center
        self._document.set_view(center=(cx + anchor[0] - moved[0], cy + anchor[1] - moved[1]), zoom=camera.zoom)

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
