"""The 3D Editor's viewport: the scene rendered as a solid, with an orbit rig on the flame's 3D camera.

Renders go through the shared `RenderService` (the GPU solid renderer when there is one, the numpy one
otherwise) under this widget's own key, progressively: the first pass lands quickly, later ones fill the
surface in. While the mouse drags, renders are made at `INTERACTIVE_SCALE` with a single pass so the view
keeps up; the full render follows once the drag settles.

When the display mode is *mesh* and a mesh has been generated, the picture is the mesh instead: points sampled
on its faces through the same shader (`solid.mesh_preview`), rendered by a `MeshPreviewJob` thread rather than
the render service — the camera, lights and materials are the same, so the mesh lands over the solid render.

Mouse: **left-drag** orbits (yaw with horizontal motion, pitch with vertical), **right-** or **middle-drag**
pans (moves the camera centre in the view plane), the **wheel** zooms (the flame's `zoom`, powers of two),
**Ctrl+wheel** changes the perspective strength, and **double-click** resets the view to the flame's own
camera as it was pulled in. Every change is written to the flame's camera through the document, so it is
undoable and travels with the flame when it is sent back to the main window.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QMouseEvent, QPainter, QPaintEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from ... import config
from ...fractal.scene import Camera
from ...render.service import PRIORITY_VIEWPORT, RenderService
from ...render.settings import RenderSettings, RenderStats
from ...widgets.fractal_preview import fitted_rect
from ...widgets.images import rgba_to_qimage
from .document import Scene3DDocument
from .jobs import MeshPreviewJob

MESH_SAMPLES_PER_PIXEL = 3       # the mesh preview splats about this many surface points per G-buffer pixel
MESH_SAMPLES_MIN, MESH_SAMPLES_MAX = 200_000, 2_000_000

BACKGROUND = QColor(24, 24, 24)
TEXT = QColor(110, 110, 110)
ORBIT_RADIANS_PER_PIXEL = 0.008
ZOOM_PER_NOTCH = 0.25            # powers of two per wheel notch
PERSPECTIVE_PER_NOTCH = 0.05
MAX_PITCH = math.pi               # Apophysis lets the pitch go all the way round
SETTLE_MS = 350
RESIZE_MS = 200
EDIT_MS = 150                     # a material / light slider drag re-renders this long after its last tick
MIN_SIZE = 32


class PreviewQuality:
    """A viewport quality preset: how many samples go into the G-buffer and how fine it is."""
    __slots__ = ("name", "quality", "passes", "oversample", "points")

    def __init__(self, name: str, quality: float, passes: int, oversample: int, points: int):
        self.name, self.quality, self.passes, self.oversample, self.points = name, quality, passes, oversample, points


QUALITIES = (
    PreviewQuality("Draft", 6.0, 2, 1, 1 << 16),
    PreviewQuality("Normal", 16.0, 4, 2, 1 << 17),
    PreviewQuality("Fine", 48.0, 6, 2, 1 << 17),
)
DEFAULT_QUALITY = QUALITIES[1]


def quality_named(name: str) -> PreviewQuality:
    """The preset called `name` (the default when unknown)."""
    for level in QUALITIES:
        if level.name.lower() == str(name).strip().lower():
            return level
    return DEFAULT_QUALITY


class Viewport3D(QWidget):
    """Paints the latest solid render of the document's scene and re-renders on every change (see the module docstring).

    Signals:
        render_progress(RenderStats): After every delivered pass.
        render_failed(str): The render could not be set up.
        camera_dragged(): The user orbited / panned / zoomed (the panels refresh their camera fields).
    """
    render_progress = Signal(object)
    render_failed = Signal(str)
    camera_dragged = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._document: Scene3DDocument | None = None
        self._service: RenderService | None = None
        self._image: QImage | None = None
        self._stats: RenderStats | None = None
        self._generation = 0
        self._current_key: object = None
        self._stats_key: object = None
        self._drag: _Drag | None = None
        self._own_move = False           # a camera change made by the rig (renders interactively, not fully)
        self._home: Camera | None = None
        self._mesh_job: MeshPreviewJob | None = None
        self._mesh_pending: tuple | None = None
        self.mesh_form = "clean"         # which generated mesh the *mesh* display shows: "clean" or "full"
        self.quality = DEFAULT_QUALITY
        self.placeholder = "No fractal — use the main window's, or open a scene"
        self._settle = QTimer(self, singleShot=True, interval=SETTLE_MS)
        self._settle.timeout.connect(self.render_full)
        self._resize_timer = QTimer(self, singleShot=True, interval=RESIZE_MS)
        self._resize_timer.timeout.connect(self.render_full)
        self._edit_timer = QTimer(self, singleShot=True, interval=EDIT_MS)
        self._edit_timer.timeout.connect(self.render_full)
        self.setMinimumSize(MIN_SIZE, MIN_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip("Left-drag: orbit · right-drag: pan · wheel: zoom · Ctrl+wheel: perspective · double-click: reset view")

    def bind(self, document: Scene3DDocument, service: RenderService) -> None:
        """Attach the scene to show and the service that renders it."""
        self._document = document
        self._service = service
        service.pass_done.connect(self._on_pass)
        service.job_failed.connect(self._on_failed)
        document.scene_replaced.connect(self._on_scene_replaced)
        document.fractal_changed.connect(self._on_scene_replaced)
        document.scene_restored.connect(self._on_scene_restored)
        document.camera_changed.connect(self._on_camera_changed)
        for signal in (document.materials_changed, document.lights_changed, document.environment_changed, document.solid_changed):
            signal.connect(self._render_after_edit)
        document.mesh_changed.connect(self._on_mesh_changed)

    # --- state ------------------------------------------------------------------------------------------------
    @property
    def image(self) -> QImage | None:
        """The latest render (None before the first pass lands)."""
        return self._image

    @property
    def stats(self) -> RenderStats | None:
        return self._stats

    @property
    def generation(self) -> int:
        """Increments with every render submitted (tests wait on it)."""
        return self._generation

    @property
    def up_to_date(self) -> bool:
        """True when the picture shown is the finished render of the latest request."""
        return (self._stats is not None and self._stats.finished and self._stats_key == self._current_key
                and self._current_key is not None and not self._edit_timer.isActive() and not self._settle.isActive()
                and not self._resize_timer.isActive() and self._mesh_job is None and self._mesh_pending is None)

    @property
    def showing_mesh(self) -> bool:
        """True when the picture is the generated mesh rather than the fractal."""
        return (self._document is not None and self._document.scene.solid.display == "mesh"
                and self._document.mesh_result is not None)

    def set_mesh_form(self, form: str) -> None:
        """Show the `clean` or the `full` mesh in the mesh display."""
        if form != self.mesh_form:
            self.mesh_form = form
            if self.showing_mesh:
                self.render_full()

    def set_quality(self, level: PreviewQuality | str) -> None:
        level = level if isinstance(level, PreviewQuality) else quality_named(level)
        if level is not self.quality:
            self.quality = level
            self.render_full()

    def home_camera(self) -> Camera | None:
        """The camera the fractal arrived with (what double-click goes back to)."""
        return self._home

    # --- rendering ----------------------------------------------------------------------------------------------
    def _on_scene_replaced(self) -> None:
        flame = self._document.flame if self._document else None
        self._home = flame.camera.copy() if flame is not None else None
        self._image = None
        self._stats = None
        self.update()
        self.render_full()

    def _on_scene_restored(self) -> None:
        """Undo / redo: re-render; the home camera stays (the flame may even have gone)."""
        if self._document.flame is None:
            self._home = None
        self.render_full()

    def render_full(self) -> None:
        """Render at the widget's full resolution with the chosen quality."""
        self._settle.stop()
        self._submit(1.0)

    def _render_after_edit(self) -> None:
        """A material / light / environment edit: stop rendering the old scene, re-render once the edits pause."""
        if self._service is not None and self._current_key is not None:
            self._service.cancel(self._current_key)
        self._edit_timer.start()

    def _on_camera_changed(self) -> None:
        """A camera edit from a panel (or undo) renders fully; the rig's own moves render interactively."""
        if not self._own_move:
            self.render_full()

    def _render_interactive(self) -> None:
        self._submit(config.INTERACTIVE_SCALE)
        self._settle.start()

    def _submit(self, scale: float) -> None:
        if self._document is None or self._service is None or not self.isVisible():
            return
        if self._current_key is not None:
            self._service.cancel(self._current_key)
            self._current_key = None
        flame = self._document.flame
        if flame is None or not flame.renderable() or self.width() < MIN_SIZE or self.height() < MIN_SIZE:
            self._image = None
            self._stats = None
            self.update()
            return
        width, height = max(1, int(self.width() * scale)), max(1, int(self.height() * scale))
        flame = flame.copy()
        flame.camera = flame.camera.at_size(width, height)
        level = self.quality
        scene = self._document.scene.copy()
        self._generation += 1
        if scene.solid.display == "mesh":
            if self._document.mesh_result is not None:
                self._current_key = ("3d-mesh", id(self), self._generation)
                mesh = self._document.mesh_result.mesh(self.mesh_form)
                oversample = 2 if (scale == 1.0 and level.name == "Fine") else 1
                samples = int(min(MESH_SAMPLES_MAX, max(MESH_SAMPLES_MIN, MESH_SAMPLES_PER_PIXEL * width * height * oversample ** 2)))
                self._start_mesh_job((mesh, flame.camera, scene, width, height, oversample, samples, self._current_key))
                return
            scene.solid.display = "solid"                  # no mesh yet: show the fractal
        passes = 1 if scale < 1.0 else level.passes
        settings = RenderSettings(width, height, passes=passes, quality=level.quality if scale == 1.0 else level.quality / 2,
                                  points=level.points, fuse=config.PREVIEW_FUSE, oversample=level.oversample if scale == 1.0 else 1,
                                  filter_radius=0.0, refine_to=0.0).with_solid(scene)
        self._current_key = ("3d-viewport", id(self), self._generation)
        self._service.submit(self._current_key, flame, settings, PRIORITY_VIEWPORT)

    # --- the mesh display --------------------------------------------------------------------------------------------
    def _on_mesh_changed(self) -> None:
        if self._document is not None and self._document.scene.solid.display == "mesh":
            self.render_full()

    def _start_mesh_job(self, request: tuple) -> None:
        """Run one mesh preview at a time; a request arriving while one runs replaces any waiting one."""
        if self._mesh_job is not None:
            self._mesh_pending = request
            return
        mesh, camera, scene, width, height, oversample, samples, key = request
        job = MeshPreviewJob(mesh, camera, scene, width, height, oversample, samples, key, self)
        job.finished_with.connect(self._on_mesh_image)
        job.failed.connect(self._on_mesh_failed)
        job.finished.connect(self._on_mesh_job_done)
        self._mesh_job = job
        job.start()

    def _on_mesh_job_done(self) -> None:
        job = self._mesh_job
        self._mesh_job = None
        if job is not None:
            job.deleteLater()
        if self._mesh_pending is not None:
            request, self._mesh_pending = self._mesh_pending, None
            self._start_mesh_job(request)

    def _on_mesh_image(self, image: np.ndarray, key: object) -> None:
        if key != self._current_key:
            return
        mesh_result = self._document.mesh_result if self._document is not None else None
        faces = mesh_result.mesh(self.mesh_form).face_count if mesh_result is not None else 0
        samples = int(min(MESH_SAMPLES_MAX, max(MESH_SAMPLES_MIN, MESH_SAMPLES_PER_PIXEL * image.shape[0] * image.shape[1])))
        stats = RenderStats(engine="mesh preview (CPU)", passes_done=1, passes_total=1, samples=samples, hits=samples,
                            width=image.shape[1], height=image.shape[0], notes=[f"{faces:,} faces"])
        self._on_pass(key, image, stats)

    def _on_mesh_failed(self, message: str) -> None:
        self.render_failed.emit(message)

    def _on_pass(self, key: object, image: np.ndarray, stats: RenderStats) -> None:
        if key != self._current_key:
            return
        self._image = rgba_to_qimage(image)
        self._stats = stats
        self._stats_key = key
        self.render_progress.emit(stats)
        self.update()

    def _on_failed(self, key: object, message: str) -> None:
        if key == self._current_key:
            self.render_failed.emit(message)

    # --- painting / geometry ---------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        if self._image is not None and not self._image.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._image.size() != self.size())
            painter.drawImage(fitted_rect(self._image.size(), self.rect()), self._image)
        elif self._document is None or self._document.flame is None:
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self.placeholder)
        else:
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Rendering…")
        painter.end()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._document is not None and self._document.flame is not None:
            self._resize_timer.start()

    def showEvent(self, event) -> None:
        super().showEvent(event)
        if self._image is None:
            QTimer.singleShot(0, self.render_full)

    # --- the orbit rig ------------------------------------------------------------------------------------------
    def _camera(self) -> Camera | None:
        flame = self._document.flame if self._document is not None else None
        return flame.camera if flame is not None else None

    def orbit(self, d_yaw: float, d_pitch: float, interactive: bool = True) -> None:
        """Turn the camera by `d_yaw` / `d_pitch` radians (the pitch is kept within ±π)."""
        camera = self._camera()
        if camera is None:
            return
        pitch = max(-MAX_PITCH, min(MAX_PITCH, camera.pitch + d_pitch))
        yaw = (camera.yaw + d_yaw + math.pi) % (2 * math.pi) - math.pi
        self._apply(interactive, "orbit", pitch=pitch, yaw=yaw)

    def pan(self, dx_pixels: float, dy_pixels: float, interactive: bool = True) -> None:
        """Move the camera centre so the picture shifts by the given screen pixels."""
        camera = self._camera()
        if camera is None:
            return
        w, h = self.width(), self.height()
        x0, y0 = camera.unproject(0.0, 0.0, w, h)
        x1, y1 = camera.unproject(dx_pixels, dy_pixels, w, h)
        cx, cy = camera.center
        self._apply(interactive, "pan", center=(cx - (x1 - x0), cy - (y1 - y0)))

    def zoom_by(self, notches: float) -> None:
        camera = self._camera()
        if camera is None:
            return
        self._apply(True, "zoom", zoom=max(-10.0, min(10.0, camera.zoom + notches * ZOOM_PER_NOTCH)))

    def change_perspective(self, notches: float) -> None:
        camera = self._camera()
        if camera is None:
            return
        self._apply(True, "perspective", perspective=max(0.0, min(2.0, camera.perspective + notches * PERSPECTIVE_PER_NOTCH)))

    def reset_view(self) -> None:
        """Back to the camera the fractal arrived with."""
        camera = self._camera()
        if camera is None or self._home is None:
            return
        home = self._home
        self._document.set_camera(None, pitch=home.pitch, yaw=home.yaw, pitch_y=home.pitch_y, perspective=home.perspective,
                                  zpos=home.zpos, zoom=home.zoom, center=home.center)
        self.camera_dragged.emit()

    def _apply(self, interactive: bool, merge_key: str, **fields) -> None:
        """Write camera fields through the document; interactive moves render at half size and coalesce in the history
        (one undo step per gesture, by `merge_key`)."""
        self._own_move = True
        try:
            self._document.set_camera(merge_key if interactive else None, **fields)
        finally:
            self._own_move = False
        if interactive:
            self._render_interactive()
        else:
            self.render_full()
        self.camera_dragged.emit()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if self._camera() is None:
            return
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = _Drag(event.position(), "orbit")
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        elif event.button() in (Qt.MouseButton.RightButton, Qt.MouseButton.MiddleButton):
            self._drag = _Drag(event.position(), "pan")
            self.setCursor(Qt.CursorShape.SizeAllCursor)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            return
        delta = event.position() - self._drag.last
        self._drag.last = QPointF(event.position())
        if self._drag.mode == "orbit":
            self.orbit(delta.x() * ORBIT_RADIANS_PER_PIXEL, delta.y() * ORBIT_RADIANS_PER_PIXEL)
        else:
            self.pan(delta.x(), delta.y())

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag is not None:
            self._drag = None
            self.setCursor(Qt.CursorShape.OpenHandCursor)
            if self._document is not None:
                self._document.end_merge()
            self._settle.start()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag = None
            self.reset_view()

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps == 0 or self._camera() is None:
            return
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            self.change_perspective(steps)
        else:
            self.zoom_by(steps)
        event.accept()


class _Drag:
    __slots__ = ("last", "mode")

    def __init__(self, origin: QPointF, mode: str):
        self.last, self.mode = QPointF(origin), mode


__all__ = ["Viewport3D", "PreviewQuality", "QUALITIES", "DEFAULT_QUALITY", "quality_named"]
