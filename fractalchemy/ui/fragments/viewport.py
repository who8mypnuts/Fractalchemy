"""The Fragments viewport: paints the latest rendered image and turns mouse / keys into camera edits.

The image arrives from the render driver (RGBA8, the buffer size) and is drawn letterboxed when the buffer is not
locked to the window. Input follows FragM's `CameraControl` exactly (§1.7 of the plan): for a 3D fragment left-drag
orients, Shift orbits the origin, Shift+Alt orbits the target, right-drag pans, both buttons dolly, the wheel dollies,
`W A S D R F` fly, `T G Y H` turn, `Q E` roll, `1 3 2 5` change the step; for a 2D fragment left-drag pans, right-drag
zooms about the press point, the wheel zooms, `A D W S Q E` pan and zoom. A click without a drag reports the 3D point
under the cursor (the depth probe), middle-click puts `Target` (Ctrl: `LightPos`) there. While a button is held the
driver renders small and one subframe at a time. Esc toggles fullscreen; Shift+right-click opens the context menu.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...fragments.camera import STEP_2D_DEFAULT, STEP_3D_DEFAULT, Camera2D, Camera3D, clamp_step, step_after_key
from ...widgets.fractal_preview import fitted_rect
from ...widgets.images import rgba_to_qimage
from .document import FragDocument
from .render_driver import RenderDriver

BACKGROUND = QColor(30, 30, 30)
TEXT = QColor(150, 150, 150)
MIN_SIZE = 32
RESIZE_MS = 200
CAMERA_KEYS_3D = {Qt.Key.Key_W: "w", Qt.Key.Key_A: "a", Qt.Key.Key_S: "s", Qt.Key.Key_D: "d", Qt.Key.Key_R: "r", Qt.Key.Key_F: "f",
                  Qt.Key.Key_T: "t", Qt.Key.Key_G: "g", Qt.Key.Key_Y: "y", Qt.Key.Key_H: "h", Qt.Key.Key_Q: "q", Qt.Key.Key_E: "e",
                  Qt.Key.Key_AsciiTilde: "~"}
CAMERA_KEYS_2D = {Qt.Key.Key_W: "w", Qt.Key.Key_A: "a", Qt.Key.Key_S: "s", Qt.Key.Key_D: "d", Qt.Key.Key_Q: "q", Qt.Key.Key_E: "e"}
STEP_KEYS = {Qt.Key.Key_1: "1", Qt.Key.Key_2: "2", Qt.Key.Key_3: "3", Qt.Key.Key_5: "5", Qt.Key.Key_X: "x"}


class FragViewport(QWidget):
    """Shows the render and drives the camera (see the module docstring).

    Signals:
        status(str): A message for the status bar (the step size, the picked point).
        fullscreen_requested(): Esc was pressed.
        context_menu_requested(QPoint): Shift + right-click (global position).
        play_toggle_requested(): Space was pressed (FragM toggles play / stop).
    """
    status = Signal(str)
    fullscreen_requested = Signal()
    context_menu_requested = Signal(QPoint)
    play_toggle_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.document: FragDocument | None = None
        self.driver: RenderDriver | None = None
        self._image: QImage | None = None
        self._building = False
        self._message = ""
        self._drag: _Drag | None = None
        self.traveling_wheel = False           # the 2D wheel preference (*traveling* vs *fixed*)
        self.path = None                        # the keyframe camera path to draw over the image (None: nothing)
        self.draw_paths = True
        self.hud_enabled = False
        self._resize_timer = QTimer(self, singleShot=True, interval=RESIZE_MS)
        self._resize_timer.timeout.connect(self._after_resize)
        self.setMinimumSize(MIN_SIZE, MIN_SIZE)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setFocusPolicy(Qt.FocusPolicy.WheelFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

    def bind(self, driver: RenderDriver) -> None:
        self.driver = driver
        driver.image_ready.connect(self.show_image)
        driver.building.connect(self._on_building)
        driver.failed.connect(self._on_failed)
        driver.set_window_size(self.width(), self.height())

    def set_document(self, document: FragDocument | None) -> None:
        """Show another document (its render arrives through the driver)."""
        self.document = document
        self._image = None
        self._message = ""
        self.update()

    # --- display ------------------------------------------------------------------------------------------------------
    @property
    def image(self) -> QImage | None:
        """The latest rendered image."""
        return self._image

    def show_image(self, rgba) -> None:
        self._image = rgba_to_qimage(rgba)
        self._message = ""
        self.update()

    def image_rect(self) -> QRect:
        """Where the image is drawn (letterboxed to the buffer's aspect)."""
        if self._image is None:
            return self.rect()
        return fitted_rect(self._image.size(), self.rect())

    def _on_building(self, building: bool) -> None:
        self._building = building
        self.update()

    def _on_failed(self, message: str) -> None:
        self._message = f"Cannot render: {message}"
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        if self._image is not None and not self._image.isNull():
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, self._image.size() != self.size())
            painter.drawImage(self.image_rect(), self._image)
        if self.path is not None and self.draw_paths and self._image is not None:
            self._paint_path(painter)
        if self.hud_enabled and self._image is not None:
            self._paint_hud(painter)
        painter.setPen(TEXT)
        if self._message:
            painter.drawText(self.rect().adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                             self._message)
        elif self.document is None:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No fragment — open one from the library or create a new one")
        elif self._image is None:
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "Building…" if self._building else "Press Build (F5) to render")
        elif self._building and self.driver is not None and self.driver.stats is None:
            painter.drawText(self.rect().adjusted(8, 8, -8, -8), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, "Building…")
        painter.end()

    # --- performance HUD ---------------------------------------------------------------------------------------------------
    def set_hud(self, enabled: bool) -> None:
        self.hud_enabled = enabled
        self.update()

    def hud_lines(self) -> list[str]:
        """What the HUD shows: images / s, ms per subframe with the watchdog margin, subframes, tiling, size, GPU load."""
        driver = self.driver
        if driver is None or driver.stats is None:
            return ["no render yet"]
        stats, facts = driver.stats, driver.stats.facts
        lines = [f"{driver.fps:.1f} images/s" if driver.fps > 0 else "idle", f"{stats.passes_done} subframes  ·  {stats.width}×{stats.height}"
                 + ("  ·  interactive" if driver.interactive else "")]
        if facts is not None:
            budget = driver.subframe_budget_ms
            margin = f"  ({facts.subframe_ms / budget * 100:.0f}% of the {budget:.0f} ms watchdog budget)" if budget > 0 and facts.subframe_ms > 0 else ""
            lines.append(f"{facts.subframe_ms:.1f} ms / subframe{margin}")
            if facts.tiled > 1:
                lines.append(f"tiled {facts.tiled}×{facts.tiled}")
            lines.append(f"GLSL {facts.version}  ·  compile {facts.compile_ms:.0f} ms  ·  {len(facts.active)} uniforms")
        if driver.gpu_load < 1.0:
            lines.append(f"GPU load limit {driver.gpu_load * 100:.0f}%")
        return lines

    def _paint_hud(self, painter: QPainter) -> None:
        lines = self.hud_lines()
        metrics = painter.fontMetrics()
        width = max(metrics.horizontalAdvance(line) for line in lines) + 16
        height = metrics.height() * len(lines) + 12
        rect = QRect(self.width() - width - 8, 8, width, height)
        painter.fillRect(rect, QColor(0, 0, 0, 150))
        painter.setPen(QColor(230, 230, 230))
        y = rect.top() + 6 + metrics.ascent()
        for line in lines:
            painter.drawText(rect.left() + 8, y, line)
            y += metrics.height()

    def set_path(self, path) -> None:
        """The camera path (`CameraPath`) to draw, or None."""
        self.path = path if path is not None and path.valid else None
        self.update()

    def _project(self, points, matrix, rect: QRect) -> list[QPointF | None]:
        """World points → widget positions through the camera's projection · view matrix (None behind the camera)."""
        import numpy as np
        out = []
        for point in points:
            clip = matrix @ np.array([point[0], point[1], point[2], 1.0])
            if clip[3] <= 1e-9:
                out.append(None)
                continue
            x, y = clip[0] / clip[3], clip[1] / clip[3]
            out.append(QPointF(rect.x() + (x * 0.5 + 0.5) * rect.width(), rect.y() + (0.5 - y * 0.5) * rect.height()))
        return out

    def _paint_path(self, painter: QPainter) -> None:
        """FragM's spline overlay: the eye path (red), the target path (blue), the control points (green)."""
        from PySide6.QtGui import QPen
        if self.document is None or self._kind() != "3D":
            return
        rect = self.image_rect()
        matrix = self.document.camera3d().projection_view(rect.width() / max(1, rect.height()))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for points, colour in ((self.path.sample(min(self.path.frames, 400)), QColor(220, 60, 60)),
                               (self.path.target_sample(min(self.path.frames, 400)), QColor(60, 120, 230))):
            painter.setPen(QPen(colour, 1.5))
            projected = self._project(points, matrix, rect)
            for a, b in zip(projected, projected[1:]):
                if a is not None and b is not None:
                    painter.drawLine(a, b)
        painter.setPen(QPen(QColor(60, 200, 60), 1))
        painter.setBrush(QColor(60, 200, 60))
        for keyframe in self.path.keyframes:
            for point in self._project([keyframe.eye, keyframe.target], matrix, rect):
                if point is not None:
                    painter.drawEllipse(point, 3.5, 3.5)

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self.driver is not None:
            self.driver.set_window_size(self.width(), self.height())
            self._resize_timer.start()        # a splitter drag resizes many times a second: re-render when it settles

    def _after_resize(self) -> None:
        if self.driver is not None and self.driver.buffer_size.locked_to_window and self.document is not None \
                and self.document.request() is not None:
            self.driver.render(clear=True)

    # --- cameras ----------------------------------------------------------------------------------------------------
    def _kind(self) -> str:
        return self.document.camera_kind if self.document is not None else "2D"

    def step(self) -> float:
        if self.document is None:
            return STEP_2D_DEFAULT
        if self.document.step_size is None:
            self.document.step_size = STEP_3D_DEFAULT if self._kind() == "3D" else STEP_2D_DEFAULT
        return self.document.step_size

    def _set_step(self, step: float) -> None:
        if self.document is not None:
            self.document.step_size = clamp_step(step)
            self.status.emit(f"Step size: {self.document.step_size:g}")

    def _buffer_point(self, pos: QPointF) -> tuple[float, float, int, int]:
        """The mouse position in buffer pixels (y down) and the buffer size."""
        rect = self.image_rect()
        width, height = (self._image.width(), self._image.height()) if self._image is not None else (self.width(), self.height())
        x = (pos.x() - rect.x()) / max(1, rect.width()) * width
        y = (pos.y() - rect.y()) / max(1, rect.height()) * height
        return x, y, width, height

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.fullscreen_requested.emit()
            return
        if event.key() == Qt.Key.Key_Space and not event.isAutoRepeat():
            self.play_toggle_requested.emit()
            return
        if self.document is None or not self.document.has_camera():
            return super().keyPressEvent(event)
        key = event.key()
        if key in STEP_KEYS and not event.isAutoRepeat():
            default = STEP_3D_DEFAULT if self._kind() == "3D" else STEP_2D_DEFAULT
            self._set_step(step_after_key(self.step(), STEP_KEYS[key], default))
            return
        text = (CAMERA_KEYS_3D if self._kind() == "3D" else CAMERA_KEYS_2D).get(key)
        if text is None:
            return super().keyPressEvent(event)
        if self._kind() == "3D":
            camera = self.document.camera3d().key(text, self.step())
            if camera is not None:
                self.document.set_camera3d(camera, merge_key=("key", text), interactive=False)
        else:
            camera = self.document.camera2d().key(text, self.step())
            if camera is not None:
                self.document.set_camera2d(camera, merge_key=("key", text), interactive=False)
        event.accept()

    def keyReleaseEvent(self, event: QKeyEvent) -> None:
        if not event.isAutoRepeat() and self.document is not None:
            self.document.end_merge()
        super().keyReleaseEvent(event)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.document is None or not self.document.has_camera():
            return
        notches = event.angleDelta().y() / 120.0
        if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            self._set_step(self.step() * (2.0 if notches > 0 else 0.5))
        elif self._kind() == "3D":
            self.document.set_camera3d(self.document.camera3d().wheel(notches, self.step()), merge_key="wheel")
        else:
            x, y, w, h = self._buffer_point(event.position())
            self.document.set_camera2d(self.document.camera2d().wheel(notches, (x, y), w, h, self.traveling_wheel), merge_key="wheel")
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        if event.button() == Qt.MouseButton.RightButton and event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
            self.context_menu_requested.emit(event.globalPosition().toPoint())
            return
        if self.document is None or not self.document.has_camera():
            return
        x, y, w, h = self._buffer_point(event.position())
        camera = self.document.camera3d().orthogonalized() if self._kind() == "3D" else self.document.camera2d()
        self._drag = _Drag(event.position(), (x, y, w, h), camera, event.modifiers())
        if self.driver is not None:
            self.driver.depth_probe = (int(x), int(h - 1 - y))
            self.driver.set_interactive(True)
        event.accept()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None or self.document is None or event.buttons() == Qt.MouseButton.NoButton:
            return
        self._drag.moved = True
        if self._kind() == "3D":
            self._drag_3d(event)
        else:
            self._drag_2d(event)
        event.accept()

    def _drag_3d(self, event: QMouseEvent) -> None:
        drag = self._drag
        dp = ((drag.origin.x() - event.position().x()) / max(1, self.width()), (drag.origin.y() - event.position().y()) / max(1, self.height()))
        buttons, mods = event.buttons(), event.modifiers()
        if buttons == (Qt.MouseButton.LeftButton | Qt.MouseButton.RightButton):
            kind = "dolly"
        elif buttons == Qt.MouseButton.RightButton:
            if mods != Qt.KeyboardModifier.NoModifier:
                return
            kind = "pan"
        elif buttons == Qt.MouseButton.LeftButton:
            if mods == Qt.KeyboardModifier.ShiftModifier:
                kind = "orbit_origin"
            elif mods == (Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.AltModifier):
                kind = "orbit_target"
            elif mods == Qt.KeyboardModifier.NoModifier:
                kind = "orient"
            else:
                return
        else:
            return
        camera = self.document.camera3d().drag(kind, drag.camera, dp, self.step())
        self.document.set_camera3d(camera, merge_key=("drag", id(drag)), interactive=True)

    def _drag_2d(self, event: QMouseEvent) -> None:
        drag = self._drag
        x, y, w, h = self._buffer_point(event.position())
        kind = "pan" if event.buttons() == Qt.MouseButton.LeftButton else "zoom" if event.buttons() == Qt.MouseButton.RightButton else None
        if kind is None:
            return
        camera = self.document.camera2d().drag(kind, drag.camera, drag.buffer_pos[:2], (x, y), w, h)
        self.document.set_camera2d(camera, merge_key=("drag", id(drag)), interactive=True)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        drag, self._drag = self._drag, None
        if self.driver is not None:
            self.driver.set_interactive(False)
        if self.document is None or drag is None:
            return
        self.document.end_merge()
        if not drag.moved and self._kind() == "3D":
            self._report_click(drag, event)
        event.accept()

    def _report_click(self, drag: "_Drag", event: QMouseEvent) -> None:
        """A click without a drag: the 3D point under the cursor (FragM's `screenTo3D`), `Target` / `LightPos` on middle-click."""
        depth = self.driver.probe_depth if self.driver is not None else None
        if not depth:
            return
        x, y, w, h = drag.buffer_pos
        point = self.document.camera3d().screen_to_3d(x, y, w, h, depth)
        self.status.emit(f"X:{point[0]:.6g} Y:{point[1]:.6g} Z:{point[2]:.6g}")
        if event.button() == Qt.MouseButton.MiddleButton:
            name = "LightPos" if event.modifiers() & Qt.KeyboardModifier.ControlModifier else "Target"
            if name in self.document.state:
                values = {name: tuple(float(v) for v in point)}
                self.document.set_values(values)
                if name == "Target" and self.document.source.auto_focus and self.document.state.get("AutoFocus"):
                    eye = self.document.camera3d().eye
                    self.document.set_values({"FocalPlane": float(sum((a - b) ** 2 for a, b in zip(eye, point)) ** 0.5)}, merge_key="focus")

    def contextMenuEvent(self, event) -> None:
        event.ignore()        # Shift + right-click is handled in mousePressEvent (FragM: only in fullscreen)


class _Drag:
    """What the mouse looked like when the button went down."""

    def __init__(self, origin: QPointF, buffer_pos: tuple, camera: Camera3D | Camera2D, modifiers):
        self.origin = origin
        self.buffer_pos = buffer_pos
        self.camera = camera
        self.modifiers = modifiers
        self.moved = False


__all__ = ["FragViewport"]
