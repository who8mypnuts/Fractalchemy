"""The Fragments viewport: paints the latest rendered image and turns mouse / keys into camera edits.

The image arrives from the render driver (RGBA8, the buffer size) and is drawn letterboxed when the buffer is not
locked to the window. Input follows FragM's `CameraControl` exactly (§1.7 of the plan): for a 3D fragment left-drag
orients, Shift orbits the origin, Shift+Alt orbits the target, right-drag pans, both buttons dolly, the wheel dollies,
`W A S D R F` fly, `T G Y H` turn, `Q E` roll, `1 3 2 5` change the step; for a 2D fragment left-drag pans, right-drag
zooms about the press point, the wheel zooms, `A D W S Q E` pan and zoom. A click without a drag reports the 3D point
under the cursor (the depth probe), middle-click puts `Target` (Ctrl: `LightPos`) there. While a button is held the
driver renders small and one subframe at a time. Esc toggles fullscreen; Shift+right-click opens the context menu.
The overlays (`viewport_overlays.py`) add Ctrl+drag for a render region, a draggable divider in A/B compare mode,
draggable keyframe handles on the camera path, and the mini-map in the corner.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QPointF, QRect, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QResizeEvent, QWheelEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

from ...fragments.camera import STEP_2D_DEFAULT, STEP_3D_DEFAULT, Camera2D, Camera3D, clamp_step, depth_to_distance, step_after_key
from ...widgets.fractal_preview import fitted_rect
from ...widgets.images import rgba_to_qimage
from .document import FragDocument
from .render_driver import RenderDriver
from .viewport_overlays import CompareWipe, KeyframeHandles, MiniMap, RegionSelect

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
        context_menu_requested(QPoint): Shift + right-click (global position): the menu bar as a popup (fullscreen).
        viewport_menu_requested(QPoint): A right-click without a drag (global position): the viewport's own menu.
        play_toggle_requested(): Space was pressed (FragM toggles play / stop).
        region_selected(tuple): Ctrl+drag ended: `(x, y, w, h)` as fractions of the image (y down).
        keyframe_moved(str, tuple): A keyframe handle was dropped: the preset name and the new `Eye`.
    """
    status = Signal(str)
    fullscreen_requested = Signal()
    context_menu_requested = Signal(QPoint)
    viewport_menu_requested = Signal(QPoint)
    play_toggle_requested = Signal()
    region_selected = Signal(tuple)
    keyframe_moved = Signal(str, tuple)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.document: FragDocument | None = None
        self.driver: RenderDriver | None = None
        self._image: QImage | None = None
        self._building = False
        self._message = ""
        self._drag: _Drag | None = None
        self.traveling_wheel = False           # the 2D wheel preference (*traveling* vs *fixed*)
        self.navigation = "orbit"               # "orbit" (DCC style: orbit / pan / dolly about the target) or "fragm" (FragM's fly)
        self._turntable = QTimer(self, interval=40)
        self._turntable.timeout.connect(self._turntable_tick)
        self.path = None                        # the keyframe camera path to draw over the image (None: nothing)
        self.draw_paths = True
        self.occlude_paths = True               # hide (dash) the parts of the path behind the rendered surface
        self.hud_enabled = False
        self.minimap = MiniMap()
        self.compare = CompareWipe()
        self.region = RegionSelect()
        self.handles = KeyframeHandles()
        self._overlay_drag = ""                 # "region" / "divider" / "handle" while one of the overlays owns the mouse
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
            self.compare.paint(painter, self.image_rect())
        if self.path is not None and self.draw_paths and self._image is not None:
            self._paint_path(painter)
        if self.minimap.enabled and self.document is not None and self.document.has_camera():
            self.minimap.paint(painter, self.rect(), self.document.camera3d() if self._kind() == "3D" else self.document.camera2d(), self.path, self._kind())
        self.region.paint(painter, self.image_rect())
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
        self.handles = KeyframeHandles()          # the handle positions belong to this path; the next paint places them
        self._update_depth_wish()
        self.update()

    def set_occlusion(self, on: bool) -> None:
        """Whether the path is hidden where the surface is in front of it (needs the depth buffer after every pass)."""
        self.occlude_paths = on
        self._update_depth_wish()
        self.update()

    def update_depth_wish(self) -> None:
        """Tell the driver whether the depth buffer is needed after each pass (paths drawn, occlusion on, a 3D camera)."""
        self._update_depth_wish()

    def _update_depth_wish(self) -> None:
        if self.driver is not None:
            self.driver.want_depth = bool(self.path is not None and self.draw_paths and self.occlude_paths and self._kind() == "3D")

    def _surface_distance(self, screen: QPointF, rect: QRect):
        """The distance to the rendered surface under a widget position (None: background, no depth buffer, or outside)."""
        depth = self.driver.depth_buffer if self.driver is not None else None
        if depth is None or self.document is None:
            return None
        h, w = depth.shape
        x = int((screen.x() - rect.x()) / max(1, rect.width()) * w)
        y = int((screen.y() - rect.y()) / max(1, rect.height()) * h)
        if not (0 <= x < w and 0 <= y < h):
            return None
        return depth_to_distance(depth[y, x], bool(self.document.state.get("DepthToAlpha")))

    def _hidden(self, point, screen: QPointF, rect: QRect, eye) -> bool:
        """True when the surface lies between the eye and `point` (FragM's spline occlusion by the depth buffer)."""
        if not self.occlude_paths or screen is None:
            return False
        surface = self._surface_distance(screen, rect)
        if surface is None:
            return False
        import numpy as np
        distance = float(np.linalg.norm(np.asarray(point, dtype=float) - np.asarray(eye, dtype=float)))
        return surface < distance * 0.995

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
        camera = self.document.camera3d()
        matrix = camera.projection_view(rect.width() / max(1, rect.height()))
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        for points, colour in ((self.path.sample(min(self.path.frames, 400)), QColor(220, 60, 60)),
                               (self.path.target_sample(min(self.path.frames, 400)), QColor(60, 120, 230))):
            projected = self._project(points, matrix, rect)
            hidden = [self._hidden(point, screen, rect, camera.eye) for point, screen in zip(points, projected)]
            for (a, b), behind in zip(zip(projected, projected[1:]), zip(hidden, hidden[1:])):
                if a is not None and b is not None:
                    painter.setPen(QPen(QColor(colour.red(), colour.green(), colour.blue(), 70), 1.0, Qt.PenStyle.DashLine) if any(behind)
                                   else QPen(colour, 1.5))
                    painter.drawLine(a, b)
        painter.setPen(QPen(QColor(60, 200, 60), 1))
        for keyframe in self.path.keyframes:
            for point, screen in zip((keyframe.eye, keyframe.target), self._project([keyframe.eye, keyframe.target], matrix, rect)):
                if screen is not None:
                    painter.setBrush(QColor(60, 200, 60, 60) if self._hidden(point, screen, rect, camera.eye) else QColor(60, 200, 60))
                    painter.drawEllipse(screen, 3.5, 3.5)
        self.handles.update(self.path, matrix, rect, self._project)
        self.handles.paint(painter, self._project)

    # --- overlays: compare, region, handles, mini-map -----------------------------------------------------------------------
    def set_minimap(self, enabled: bool) -> None:
        self.minimap.enabled = enabled
        self.update()

    def freeze_reference(self) -> bool:
        """*Compare ▸ Freeze reference*: the current image becomes A; the live render shows right of the divider."""
        ok = self.compare.freeze(self._image)
        self.update()
        return ok

    def set_compare(self, enabled: bool) -> None:
        if enabled and self.compare.reference is None:
            self.freeze_reference()
        self.compare.enabled = enabled and self.compare.reference is not None
        self.update()

    def _overlay_press(self, event: QMouseEvent) -> bool:
        """Give the press to an overlay when it wants it (region drag, the divider, a keyframe handle)."""
        pos = event.position()
        if event.button() != Qt.MouseButton.LeftButton:
            return False
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and self._image is not None:
            self.region.begin(pos)
            self._overlay_drag = "region"
        elif self.compare.hits_divider(pos, self.image_rect()):
            self.compare.dragging = True
            self._overlay_drag = "divider"
        elif event.modifiers() == Qt.KeyboardModifier.NoModifier and self.draw_paths and self.path is not None and self._kind() == "3D":
            name = self.handles.hit(pos)
            keyframe = next((k for k in self.path.keyframes if k.name == name), None) if name is not None else None
            if keyframe is None:
                return False
            self.handles.begin(name, keyframe.eye)
            self._overlay_drag = "handle"
            self.status.emit(f"Dragging {name} (release to rewrite the preset)")
        else:
            return False
        event.accept()
        return True

    def _overlay_move(self, event: QMouseEvent) -> bool:
        if not self._overlay_drag:
            if self.compare.hits_divider(event.position(), self.image_rect()):
                self.setCursor(Qt.CursorShape.SplitHCursor)
            elif self.draw_paths and self.path is not None and self._kind() == "3D" and self.handles.hit(event.position()):
                self.setCursor(Qt.CursorShape.OpenHandCursor)
            else:
                self.setCursor(Qt.CursorShape.CrossCursor)
            return False
        if self._overlay_drag == "region":
            self.region.move(event.position())
        elif self._overlay_drag == "divider":
            self.compare.drag_to(event.position(), self.image_rect())
        elif self._overlay_drag == "handle":
            self.handles.drag_to(event.position())
        self.update()
        event.accept()
        return True

    def _overlay_release(self, event: QMouseEvent) -> bool:
        kind, self._overlay_drag = self._overlay_drag, ""
        if not kind:
            return False
        if kind == "region":
            region = self.region.finish(self.image_rect())
            if region is not None:
                self.region_selected.emit(region)
        elif kind == "divider":
            self.compare.dragging = False
        elif kind == "handle":
            moved = self.handles.finish()
            if moved is not None:
                self.keyframe_moved.emit(*moved)
        self.update()
        event.accept()
        return True

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
        if self._numpad_key(event):
            return
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
        elif self._kind() == "3D" and self.navigation == "orbit":
            factor = 0.9 ** notches if not event.modifiers() & Qt.KeyboardModifier.ControlModifier else 0.98 ** notches
            self.document.set_camera3d(self.document.camera3d().dolly_target(factor), merge_key="wheel")
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
        if self._overlay_press(event):
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
        if self._overlay_move(event):
            return
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
        if self.navigation == "orbit":
            self._drag_orbit(drag, dp, buttons, mods)
            return
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

    def _drag_orbit(self, drag, dp, buttons, mods) -> None:
        """DCC-style navigation: left orbits the target, middle (or Shift+right) pans, right (or Ctrl+middle) dollies;
        Shift+left looks around (FragM's orient), Alt+left orbits the origin."""
        camera = self.document.camera3d()
        shift, ctrl, alt = (bool(mods & m) for m in (Qt.KeyboardModifier.ShiftModifier, Qt.KeyboardModifier.ControlModifier,
                                                       Qt.KeyboardModifier.AltModifier))
        if buttons == Qt.MouseButton.LeftButton:
            if shift:
                new = camera.drag("orient", drag.camera, dp, self.step())
            elif alt:
                new = camera.drag("orbit_origin", drag.camera, dp, self.step())
            else:
                new = camera.orbit(drag.camera, (-dp[0], -dp[1]))
        elif buttons == Qt.MouseButton.MiddleButton:
            new = camera.orbit(drag.camera, (-dp[0], -dp[1])) if alt else drag.camera.dolly_target(2.0 ** (dp[1] * 4.0)) if ctrl \
                else camera.pan_screen(drag.camera, (dp[0], dp[1]))
        elif buttons == Qt.MouseButton.RightButton:
            new = camera.pan_screen(drag.camera, (dp[0], dp[1])) if shift else drag.camera.dolly_target(2.0 ** (dp[1] * 4.0))
        else:
            return
        self.document.set_camera3d(new, merge_key=("drag", id(drag)), interactive=True)

    # --- views (the numpad and the View menu) --------------------------------------------------------------------------
    def view_from(self, side: str) -> None:
        """`front` / `back` / `left` / `right` / `top` / `bottom` at the current distance from the target."""
        if self.document is not None and self._kind() == "3D" and self.document.has_camera():
            self.document.set_camera3d(self.document.camera3d().view_from(side), merge_key=None, interactive=False)
            self.status.emit(f"View: {side}")

    def orbit_by(self, degrees: float, axis: str) -> None:
        if self.document is not None and self._kind() == "3D" and self.document.has_camera():
            self.document.set_camera3d(self.document.camera3d().turned_about_target(degrees, axis), merge_key=("orbit", axis), interactive=False)

    def flip_view(self) -> None:
        """Numpad 9: the opposite side of the target."""
        if self.document is not None and self._kind() == "3D" and self.document.has_camera():
            camera = self.document.camera3d()
            eye = tuple(2 * t - e for e, t in zip(camera.eye, camera.target))
            self.document.set_camera3d(camera.__class__(eye, camera.target, camera.up, camera.fov).orthogonalized(), merge_key=None, interactive=False)

    def frame_origin(self) -> None:
        """Numpad `.`: put the target on the origin, keeping the distance and direction."""
        if self.document is not None and self._kind() == "3D" and self.document.has_camera():
            camera = self.document.camera3d()
            offset = tuple(e - t for e, t in zip(camera.eye, camera.target))
            self.document.set_camera3d(camera.__class__(offset, (0.0, 0.0, 0.0), camera.up, camera.fov), merge_key=None, interactive=False)

    def set_turntable(self, on: bool) -> None:
        """Auto-rotate around the target (a slow turntable) while on."""
        if on:
            self._turntable.start()
        else:
            self._turntable.stop()

    def _turntable_tick(self) -> None:
        if self.document is None or self._kind() != "3D" or not self.document.has_camera():
            return
        self.document.set_camera3d(self.document.camera3d().turned_about_target(0.6, "up"), merge_key="turntable", interactive=False)

    def _numpad_key(self, event: QKeyEvent) -> bool:
        """Blender's numpad views: 1 / 3 / 7 front / right / top (Ctrl: the opposite), 9 flips, 4 6 8 2 orbit 15°, `.` frames the origin."""
        if not event.modifiers() & Qt.KeyboardModifier.KeypadModifier or self._kind() != "3D":
            return False
        ctrl = bool(event.modifiers() & Qt.KeyboardModifier.ControlModifier)
        key = event.key()
        views = {Qt.Key.Key_1: ("front", "back"), Qt.Key.Key_3: ("right", "left"), Qt.Key.Key_7: ("top", "bottom")}
        if key in views:
            self.view_from(views[key][1 if ctrl else 0])
        elif key == Qt.Key.Key_9:
            self.flip_view()
        elif key in (Qt.Key.Key_4, Qt.Key.Key_6):
            self.orbit_by(15.0 if key == Qt.Key.Key_4 else -15.0, "up")
        elif key in (Qt.Key.Key_8, Qt.Key.Key_2):
            self.orbit_by(15.0 if key == Qt.Key.Key_8 else -15.0, "right")
        elif key == Qt.Key.Key_Period:
            self.frame_origin()
        else:
            return False
        return True

    def _drag_2d(self, event: QMouseEvent) -> None:
        drag = self._drag
        x, y, w, h = self._buffer_point(event.position())
        kind = "pan" if event.buttons() == Qt.MouseButton.LeftButton else "zoom" if event.buttons() == Qt.MouseButton.RightButton else None
        if kind is None:
            return
        camera = self.document.camera2d().drag(kind, drag.camera, drag.buffer_pos[:2], (x, y), w, h)
        self.document.set_camera2d(camera, merge_key=("drag", id(drag)), interactive=True)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._overlay_release(event):
            return
        drag, self._drag = self._drag, None
        if self.driver is not None:
            self.driver.set_interactive(False)
        if drag is None:
            if event.button() == Qt.MouseButton.RightButton and event.modifiers() != Qt.KeyboardModifier.ShiftModifier:
                self.viewport_menu_requested.emit(event.globalPosition().toPoint())
            return
        if self.document is None:
            return
        self.document.end_merge()
        if not drag.moved and event.button() == Qt.MouseButton.RightButton:
            self.viewport_menu_requested.emit(event.globalPosition().toPoint())
        elif not drag.moved and self._kind() == "3D":
            self._report_click(drag, event)
        event.accept()

    def _report_click(self, drag: "_Drag", event: QMouseEvent) -> None:
        """A click without a drag: the 3D point under the cursor (FragM's `screenTo3D`), `Target` / `LightPos` on middle-click."""
        depth = self.driver.probe_depth if self.driver is not None else None
        distance = depth_to_distance(depth, bool(self.document.state.get("DepthToAlpha"))) if depth else None
        if not distance:
            return
        x, y, w, h = drag.buffer_pos
        point = self.document.camera3d().screen_to_3d(x, y, w, h, 1.0 / distance)
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
