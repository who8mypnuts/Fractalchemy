"""The Transform Editor's canvas: the triangles of every transform, editable with the mouse, as in Apophysis.

The view knows nothing about flames. The window hands it a list of `TriangleEntry` (one per transform:
key, the triangle being edited, an optional *ghost* triangle shown dotted, colour, label, hint) and the
view reports what the user does:

* `selected(key)` — a triangle was clicked;
* `triangle_dragged(key, triangle)` — live, on every mouse move of a drag; `drag_finished(key, changed)` after;
* `triangle_command(key, name)` — a double-click reset (`reset-corner-x` …) or a key (`move-left`, `rotate-ccw`,
  `scale-up`, `duplicate`, `delete`, `toggle-pivot`);
* `context_menu(pos, hit)` — right-click without dragging (`hit` is a `Hit` or None for empty space);
* `status(text)` and `view_changed()`.

`set_variation_preview(points, colour)` shows Apophysis's *variation preview*: editor-space points (a grid sent
through the selected transform, see `render/xform_preview.py`) drawn as dots behind the triangles.

Coordinates are *editor space* (y up; see `fractal.triangles`). Mouse gestures follow Apophysis:

* drag a corner: moves it (**move** mode; dragging **O** drags the whole triangle when the axes are locked),
  turns it about the pivot (**rotate**), or slides it along the pivot ray (**scale**); **Shift** snaps;
* drag inside a triangle: move / rotate / scale the whole triangle about the pivot;
* drag an edge: the hypotenuse scales, the two axes rotate (Apophysis's *extended edit*);
* **Alt** while dragging rotates, **Ctrl** scales, whatever the mode;
* right-drag pans, the wheel zooms about the cursor, double-click on empty space fits everything;
* double-click a corner resets it (X / Y: unit axis; O: back to the origin), inside a triangle: rotation
  (rotate mode) or scale (scale mode) — or moves the triangle back to the origin in move mode;
* arrows nudge (Shift ×10, Ctrl ÷10), Alt+←/→ rotate, Alt+↑/↓ scale, PgUp/PgDn rotate, Home/End scale,
  Insert duplicates, Delete deletes, +/− zoom, Space / W toggle the pivot, A toggles select mode, M / R / S pick
  the move / rotate / scale mode, T steps through the pre / normal / post affines, Esc cancels a drag.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
from PySide6.QtCore import QPoint, QPointF, Qt, Signal
from PySide6.QtGui import (QBrush, QColor, QFont, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen, QPolygonF,
                           QResizeEvent, QWheelEvent)
from PySide6.QtWidgets import QSizePolicy, QWidget

from ..fractal import triangles as T
from ..fractal.triangle_drag import (MODE_MOVE, MODE_ROTATE, MODE_SCALE, DragState, DragSteps, begin_corner_drag,
                                     begin_triangle_drag, drag, edge_drag_mode)
from ..fractal.triangles import CORNER_O, CORNER_X, CORNER_Y, Point, Triangle

PIVOT_LOCAL, PIVOT_WORLD = "local", "world"
CORNER_RADIUS_PX = 5.0
CORNER_HIT_PX = 7.0
EDGE_HIT_PX = 4.0
ZOOM_STEP = 1.25
MIN_PIXELS_PER_UNIT = 0.5
MAX_PIXELS_PER_UNIT = 50000.0
DEFAULT_PIXELS_PER_UNIT = 50.0 * 2.0     # Apophysis: 50 · GraphZoom, GraphZoom 2 at start
FIT_MARGIN = 1.25

BACKGROUND = QColor(12, 12, 12)
GRID_MINOR = QColor(38, 38, 38)
GRID_AXIS = QColor(96, 96, 96)
REFERENCE_COLOR = QColor(127, 127, 127)
HELPER_COLOR = QColor(128, 128, 128)
PIVOT_COLOR = QColor(230, 230, 230)
TEXT_COLOR = QColor(160, 160, 160)
CORNER_HOVER = {CORNER_X: QColor(220, 60, 60), CORNER_O: QColor(200, 200, 200), CORNER_Y: QColor(70, 110, 240)}
# Apophysis's TrgColors (BGR in the source; converted to RGB here)
TRANSFORM_COLORS = [QColor(*rgb) for rgb in (
    (255, 0, 0), (204, 204, 0), (0, 204, 0), (0, 204, 204), (64, 64, 255), (204, 0, 204), (204, 128, 0),
    (128, 0, 79), (128, 128, 34), (96, 128, 96), (80, 128, 128), (79, 79, 128), (128, 80, 128), (128, 96, 34))]
FINAL_COLOR = QColor(255, 255, 255)


def transform_color(index: int | None) -> QColor:
    """Apophysis's triangle colour for transform `index` (white for the final transform)."""
    return FINAL_COLOR if index is None else TRANSFORM_COLORS[index % len(TRANSFORM_COLORS)]


@dataclass
class TriangleEntry:
    """One transform as the view shows it.

    Attributes:
        key: Identifies the transform (an index, or None for the final transform).
        triangle: The triangle being edited (the active mode's affine).
        ghost: Another of the transform's triangles shown dotted for reference (the normal one while a
            pre / post affine is edited), or None.
        ghosts: Further reference triangles with a caption — the transform's pre / post affines that are not
            the identity, shown faintly while the normal triangle is edited.
        color: Outline colour.
        label: Short caption drawn near O (`1`, `Final`, a transform's name).
        hint: Lines shown in the corner of the view while the mouse is over the triangle (its variations).
    """
    key: object
    triangle: Triangle
    ghost: Triangle | None = None
    color: QColor = field(default_factory=lambda: QColor(255, 255, 255))
    label: str = ""
    hint: tuple[str, ...] = ()
    ghosts: tuple[tuple[str, Triangle], ...] = ()


@dataclass(frozen=True)
class Hit:
    """What is under the mouse: a transform (`key` may be None: the final transform), and its corner or edge if any."""
    key: object
    corner: int | None = None
    edge: int | None = None


class TriangleView(QWidget):
    """The editable triangle canvas (see the module docstring for the gestures)."""
    selected = Signal(object)
    triangle_dragged = Signal(object, object)
    drag_finished = Signal(object, bool)
    triangle_command = Signal(object, str)
    context_menu = Signal(QPoint, object)
    status = Signal(str)
    view_changed = Signal()
    hover_changed = Signal(object)      # a Hit, or None

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMinimumSize(200, 160)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self._entries: list[TriangleEntry] = []
        self._selected_key: object = 0
        self._center: Point = (0.0, 0.0)
        self._ppu = DEFAULT_PIXELS_PER_UNIT
        self.edit_mode = MODE_MOVE
        self.select_mode = True
        self.axis_lock = True
        self.extended_edit = True
        self.show_helpers = True
        self.show_ghosts = True
        self.pivot_mode = PIVOT_LOCAL
        self.local_pivot: Point = (0.0, 0.0)     # in the triangle's own (u, v) coordinates
        self.world_pivot: Point = (0.0, 0.0)
        self.drag_steps = DragSteps()       # the snapping steps (the Triangle tab keeps them in step)
        self.mode_caption = ""
        self._drag: DragState | None = None
        self._drag_key: object = None
        self._pan: tuple[QPointF, Point] | None = None
        self._pan_moved = False
        self._hover: Hit | None = None
        self._mouse: Point | None = None
        self._has_focus_frame = False
        self._preview_points: np.ndarray | None = None     # (N, 2) editor-space points
        self._input_points: np.ndarray | None = None       # the grid they came from, drawn faintly (optional)
        self._preview_color = QColor(255, 255, 255)

    # --- data ---------------------------------------------------------------------------------------------
    def set_entries(self, entries: list[TriangleEntry], selected_key: object = 0) -> None:
        """Show these triangles (replacing all), with `selected_key` selected; keeps the view and a drag in progress."""
        self._entries = list(entries)
        keys = [e.key for e in entries]
        self._selected_key = selected_key if selected_key in keys else (keys[0] if keys else None)
        if self._hover is not None and self._hover.key not in keys:
            self._hover = None
        self.update()

    def entries(self) -> list[TriangleEntry]:
        """The triangles shown (copies of the list; the entries themselves are shared)."""
        return list(self._entries)

    def entry(self, key: object) -> TriangleEntry | None:
        """The entry for a transform key, if shown."""
        for e in self._entries:
            if e.key == key:
                return e
        return None

    @property
    def selected_key(self) -> object:
        """The key of the selected triangle."""
        return self._selected_key

    def select(self, key: object) -> None:
        """Select a triangle programmatically (no signal)."""
        if self.entry(key) is not None and key != self._selected_key:
            self._selected_key = key
            self.update()

    def triangle(self, key: object) -> Triangle | None:
        """The triangle of a transform key, if shown."""
        e = self.entry(key)
        return e.triangle if e else None

    def is_dragging(self) -> bool:
        """True while a mouse drag is in progress."""
        return self._drag is not None

    def set_variation_preview(self, points: np.ndarray | None, color: QColor | None = None, inputs: np.ndarray | None = None) -> None:
        """Show `points` (editor space, shape (N, 2)) as dots in `color`; None hides the preview. `inputs` — the grid the
        points came from — is drawn faintly beneath them when given."""
        self._preview_points = None if points is None or len(points) == 0 else np.asarray(points, dtype=np.float64)
        self._input_points = None if inputs is None or len(inputs) == 0 else np.asarray(inputs, dtype=np.float64)
        if color is not None:
            self._preview_color = QColor(color)
        self.update()

    @property
    def variation_preview_count(self) -> int:
        """How many preview dots are shown (tests)."""
        return 0 if self._preview_points is None else int(len(self._preview_points))

    # --- view ---------------------------------------------------------------------------------------------
    @property
    def pixels_per_unit(self) -> float:
        """The zoom: screen pixels per fractal unit."""
        return self._ppu

    @property
    def center(self) -> Point:
        """The editor-space point at the widget's centre."""
        return self._center

    def set_view(self, center: Point, pixels_per_unit: float) -> None:
        """Set the view's centre and zoom (the zoom is clamped)."""
        self._center = (float(center[0]), float(center[1]))
        self._ppu = max(MIN_PIXELS_PER_UNIT, min(MAX_PIXELS_PER_UNIT, float(pixels_per_unit)))
        self.view_changed.emit()
        self.update()

    def fit(self) -> None:
        """Zoom and centre so every triangle (and the origin) is in view — Apophysis's *auto zoom*."""
        triangles = [e.triangle for e in self._entries] + [e.ghost for e in self._entries if e.ghost is not None]
        triangles += [t for e in self._entries for _label, t in e.ghosts]
        x0, y0, x1, y1 = T.bounds(triangles)
        span_x, span_y = max(x1 - x0, 1e-6), max(y1 - y0, 1e-6)
        ppu = min(self.width() / (span_x * FIT_MARGIN), self.height() / (span_y * FIT_MARGIN))
        self.set_view(((x0 + x1) / 2, (y0 + y1) / 2), ppu)

    def zoom_by(self, factor: float, anchor: QPointF | None = None) -> None:
        """Zoom about a screen point (the widget centre by default)."""
        anchor = anchor if anchor is not None else QPointF(self.width() / 2, self.height() / 2)
        before = self.to_editor(anchor)
        self._ppu = max(MIN_PIXELS_PER_UNIT, min(MAX_PIXELS_PER_UNIT, self._ppu * factor))
        after = self.to_editor(anchor)
        self._center = (self._center[0] + before[0] - after[0], self._center[1] + before[1] - after[1])
        self.view_changed.emit()
        self.update()

    def to_screen(self, point: Point) -> QPointF:
        """Editor-space point → widget coordinates."""
        return QPointF(self.width() / 2 + (point[0] - self._center[0]) * self._ppu,
                       self.height() / 2 - (point[1] - self._center[1]) * self._ppu)

    def to_editor(self, pos: QPointF) -> Point:
        """Widget coordinates → editor-space point."""
        return ((pos.x() - self.width() / 2) / self._ppu + self._center[0],
                -(pos.y() - self.height() / 2) / self._ppu + self._center[1])

    # --- pivot --------------------------------------------------------------------------------------------
    def pivot_of(self, key: object) -> Point:
        """The pivot point for transform `key`: its local pivot, or the world pivot."""
        if self.pivot_mode == PIVOT_WORLD:
            return self.world_pivot
        triangle = self.triangle(key)
        if triangle is None:
            return (0.0, 0.0)
        return T.local_point(triangle, *self.local_pivot)

    def pivot(self) -> Point:
        """The pivot point of the selected transform."""
        return self.pivot_of(self._selected_key)

    def set_pivot_mode(self, mode: str) -> None:
        """`PIVOT_LOCAL` (the triangle's own coordinates) or `PIVOT_WORLD` (a fixed point)."""
        self.pivot_mode = PIVOT_WORLD if mode == PIVOT_WORLD else PIVOT_LOCAL
        self.update()

    def set_local_pivot(self, u: float, v: float) -> None:
        """The local pivot in triangle coordinates: (0, 0) is O, (1, 0) is X, (0, 1) is Y."""
        self.local_pivot = (float(u), float(v))
        self.update()

    def set_world_pivot(self, x: float, y: float) -> None:
        """The world pivot in editor space."""
        self.world_pivot = (float(x), float(y))
        self.update()

    def set_pivot_point(self, point: Point) -> None:
        """Put the pivot at an editor-space point (kept as local (u, v) in local mode)."""
        if self.pivot_mode == PIVOT_WORLD:
            self.set_world_pivot(*point)
            return
        triangle = self.triangle(self._selected_key)
        local = T.local_coords(triangle, point) if triangle is not None else None
        if local is not None:
            self.set_local_pivot(*local)

    # --- hit testing --------------------------------------------------------------------------------------
    def _candidates(self, prefer_selected: bool) -> list[TriangleEntry]:
        """Triangles the mouse may grab: all of them, topmost (last) first, in select mode — with the selected one
        ahead when `prefer_selected`, so its corners win where triangles coincide; otherwise only the selected one."""
        selected = self.entry(self._selected_key)
        first = [selected] if selected is not None else []
        if not self.select_mode:
            return first
        if prefer_selected:
            return first + [e for e in reversed(self._entries) if e is not selected]
        return list(reversed(self._entries))

    def _hit(self, point: Point) -> Hit | None:
        """What is under `point`: corners first, then edges (extended edit), then the interior; None for nothing."""
        corner_radius, edge_radius = CORNER_HIT_PX / self._ppu, EDGE_HIT_PX / self._ppu
        candidates = self._candidates(prefer_selected=True)
        for e in candidates:
            corner = T.nearest_corner(e.triangle, point, corner_radius)
            if corner is not None:
                return Hit(e.key, corner, None)
        if self.extended_edit:
            for e in candidates:
                edge = T.nearest_edge(e.triangle, point, edge_radius)
                if edge is not None:
                    return Hit(e.key, None, edge)
        for e in self._candidates(prefer_selected=False):
            if T.contains(e.triangle, point):
                return Hit(e.key)
        return None

    def hit_at(self, point: Point) -> Hit | None:
        """Public hit test (tests and callers): see `_hit`."""
        return self._hit(point)

    # --- Qt events ----------------------------------------------------------------------------------------
    def mousePressEvent(self, event: QMouseEvent) -> None:
        self.setFocus()
        point = self.to_editor(event.position())
        if event.button() == Qt.MouseButton.RightButton:
            if self._drag is None:
                self._pan = (event.position(), self._center)
                self._pan_moved = False
                self.setCursor(Qt.CursorShape.ClosedHandCursor)
            return
        if event.button() != Qt.MouseButton.LeftButton or not self._entries:
            return
        hit = self._hit(point)
        if hit is None and self.select_mode:
            return                                  # clicked empty space
        if hit is None:
            hit = Hit(self._selected_key)           # not selecting: any click grabs the selected triangle
        key, corner, edge = hit.key, hit.corner, hit.edge
        if key != self._selected_key:
            self._selected_key = key
            self.selected.emit(key)
        triangle = self.triangle(key)
        if triangle is None:
            return
        pivot = self.pivot_of(key)
        if corner is not None:
            state = begin_corner_drag(self._effective_mode(event.modifiers()), point, pivot, triangle, corner,
                                      self.pivot_mode == PIVOT_LOCAL)
        elif edge is not None:
            state = begin_triangle_drag(edge_drag_mode(edge), point, pivot, triangle)
        else:
            state = begin_triangle_drag(self._effective_mode(event.modifiers()), point, pivot, triangle)
        self._drag = state
        self._drag_key = key
        if hit != self._hover:
            self._hover = hit
            self.hover_changed.emit(hit)
        self._update_cursor(state.mode)
        self.update()

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        pos = event.position()
        point = self.to_editor(pos)
        self._mouse = point
        if self._pan is not None:
            origin, center = self._pan
            delta = pos - origin
            if abs(delta.x()) + abs(delta.y()) > 2:
                self._pan_moved = True
            self._center = (center[0] - delta.x() / self._ppu, center[1] + delta.y() / self._ppu)
            self.view_changed.emit()
            self.update()
            return
        if self._drag is not None:
            self._drag_to(point, event.modifiers())
            return
        hit = self._hit(point)
        changed = hit != self._hover
        self._hover = hit
        if hit is not None and hit.corner is not None:
            self.setCursor(Qt.CursorShape.CrossCursor)
        elif hit is not None and hit.edge is not None:
            self.setCursor(Qt.CursorShape.SizeAllCursor if hit.edge == 2 else Qt.CursorShape.PointingHandCursor)
        elif hit is not None or not self.select_mode:
            self._update_cursor(self._effective_mode(event.modifiers()))
        else:
            self.setCursor(Qt.CursorShape.ArrowCursor)
        if changed:
            self.hover_changed.emit(hit)
        self.status.emit(f"X: {point[0]:.4f}   Y: {point[1]:.4f}" + (f"   {self._caption(hit.key)}" if hit is not None else ""))
        if changed:
            self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.RightButton and self._pan is not None:
            self._pan = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if not self._pan_moved:
                hit = self._hover
                if hit is not None and hit.key != self._selected_key:
                    self._selected_key = hit.key
                    self.selected.emit(hit.key)
                    self.update()
                self.context_menu.emit(event.position().toPoint(), hit)
            return
        if event.button() == Qt.MouseButton.LeftButton and self._drag is not None:
            state = self._drag
            self._drag = None
            self._hover = None          # re-evaluated on the next move (the triangle moved under the mouse)
            self.drag_finished.emit(self._drag_key, state.changed)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return
        point = self.to_editor(event.position())
        hit = self._hit(point)
        if hit is None:
            self.fit()
            return
        key, corner, edge = hit.key, hit.corner, hit.edge
        if key != self._selected_key:
            self._selected_key = key
            self.selected.emit(key)
        mode = self._effective_mode(event.modifiers())
        if corner is not None:
            name = {CORNER_X: "x", CORNER_O: "o", CORNER_Y: "y"}[corner]
            if mode == MODE_ROTATE:
                self.triangle_command.emit(key, f"snap-corner-{name}")
            elif mode == MODE_SCALE:
                self.triangle_command.emit(key, f"unit-corner-{name}")
            else:
                self.triangle_command.emit(key, f"reset-corner-{name}")
        elif edge is not None:
            self.triangle_command.emit(key, "reset-scale" if edge == 2 or mode == MODE_SCALE else "reset-rotation")
        else:
            self.triangle_command.emit(key, {MODE_ROTATE: "reset-rotation", MODE_SCALE: "reset-scale"}.get(mode, "reset-position"))

    def wheelEvent(self, event: QWheelEvent) -> None:
        steps = event.angleDelta().y() / 120.0
        if steps:
            self.zoom_by(ZOOM_STEP ** steps, event.position())
        event.accept()

    def leaveEvent(self, event) -> None:
        if self._drag is None:
            self._hover = None
            self._mouse = None
            self.hover_changed.emit(None)
            self.update()
        super().leaveEvent(event)

    def focusInEvent(self, event) -> None:
        self._has_focus_frame = True
        self.update()
        super().focusInEvent(event)

    def focusOutEvent(self, event) -> None:
        self._has_focus_frame = False
        self.update()
        super().focusOutEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key, mods = event.key(), event.modifiers()
        alt = bool(mods & Qt.KeyboardModifier.AltModifier)
        commands = {
            Qt.Key.Key_Left: "rotate-ccw" if alt else "move-left",
            Qt.Key.Key_Right: "rotate-cw" if alt else "move-right",
            Qt.Key.Key_Up: "scale-up" if alt else "move-up",
            Qt.Key.Key_Down: "scale-down" if alt else "move-down",
            Qt.Key.Key_PageUp: "rotate-ccw", Qt.Key.Key_PageDown: "rotate-cw",
            Qt.Key.Key_Home: "scale-up", Qt.Key.Key_End: "scale-down",
            Qt.Key.Key_Insert: "duplicate", Qt.Key.Key_Delete: "delete",
            Qt.Key.Key_Space: "toggle-pivot", Qt.Key.Key_W: "toggle-pivot",
            Qt.Key.Key_A: "toggle-select", Qt.Key.Key_M: "mode-move", Qt.Key.Key_R: "mode-rotate", Qt.Key.Key_S: "mode-scale",
            Qt.Key.Key_T: "next-affine", Qt.Key.Key_V: "toggle-var-preview",
        }
        if key in (Qt.Key.Key_Plus, Qt.Key.Key_Equal):
            self.zoom_by(ZOOM_STEP)
        elif key in (Qt.Key.Key_Minus, Qt.Key.Key_Underscore):
            self.zoom_by(1.0 / ZOOM_STEP)
        elif key == Qt.Key.Key_Escape:
            self.cancel_drag()
        elif key in commands:
            self.triangle_command.emit(self._selected_key, commands[key])
        else:
            super().keyPressEvent(event)
            return
        event.accept()

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        self.view_changed.emit()

    # --- dragging -----------------------------------------------------------------------------------------
    def cancel_drag(self) -> None:
        """Esc: put the triangle back where the drag started."""
        state = self._drag
        if state is None:
            return
        self._drag = None
        if state.changed:
            self.triangle_dragged.emit(self._drag_key, state.original)
        self.drag_finished.emit(self._drag_key, False)
        self.setCursor(Qt.CursorShape.ArrowCursor)
        self.update()

    def _effective_mode(self, modifiers) -> str:
        if modifiers & Qt.KeyboardModifier.AltModifier:
            return MODE_ROTATE
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            return MODE_SCALE
        return self.edit_mode

    def _update_cursor(self, mode: str) -> None:
        self.setCursor({MODE_ROTATE: Qt.CursorShape.PointingHandCursor, MODE_SCALE: Qt.CursorShape.SizeFDiagCursor}.get(
            mode, Qt.CursorShape.SizeAllCursor))

    def _drag_to(self, point: Point, modifiers) -> None:
        """Apply the drag in progress to the mouse point: update the entry, tell the owner, show what happened."""
        state = self._drag
        shift = bool(modifiers & Qt.KeyboardModifier.ShiftModifier)
        triangle, text = drag(state, point, shift, self.drag_steps, self.axis_lock)
        if triangle is None:
            return
        state.changed = True
        entry = self.entry(self._drag_key)
        if entry is not None:
            entry.triangle = triangle
        self.status.emit(f"X: {point[0]:.4f}   Y: {point[1]:.4f}   {text}")
        self.triangle_dragged.emit(self._drag_key, triangle)
        self.update()

    # --- painting -----------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), BACKGROUND)
        self._paint_grid(painter)
        self._paint_variation_preview(painter)
        self._paint_reference(painter)
        if self.show_ghosts:
            for e in self._entries:
                if e.ghost is not None:
                    self._paint_ghost(painter, e.color, e.ghost, "")
                for label, triangle in e.ghosts:
                    self._paint_ghost(painter, e.color, triangle, label)
        for e in self._entries:
            if e.key != self._selected_key:
                self._paint_entry(painter, e, selected=False)
        sel = self.entry(self._selected_key)
        if sel is not None:
            self._paint_entry(painter, sel, selected=True)
        self._paint_hover(painter)
        self._paint_helpers(painter)
        self._paint_pivot(painter)
        self._paint_captions(painter)
        painter.end()

    def _paint_grid(self, painter: QPainter) -> None:
        w, h = self.width(), self.height()
        span = max(w, h) / self._ppu
        if span <= 0:
            return
        exponent = round(math.log10(span)) - 1
        step = 10.0 ** exponent
        if step * self._ppu < 6:
            step *= 10
        x0, y0 = self.to_editor(QPointF(0, h))
        x1, y1 = self.to_editor(QPointF(w, 0))
        painter.setPen(QPen(GRID_MINOR, 1))
        gx = math.floor(x0 / step) * step
        while gx <= x1:
            sx = self.to_screen((gx, 0)).x()
            painter.drawLine(QPointF(sx, 0), QPointF(sx, h))
            gx += step
        gy = math.floor(y0 / step) * step
        while gy <= y1:
            sy = self.to_screen((0, gy)).y()
            painter.drawLine(QPointF(0, sy), QPointF(w, sy))
            gy += step
        painter.setPen(QPen(GRID_AXIS, 1))
        origin = self.to_screen((0.0, 0.0))
        painter.drawLine(QPointF(origin.x(), 0), QPointF(origin.x(), h))
        painter.drawLine(QPointF(0, origin.y()), QPointF(w, origin.y()))

    def _paint_variation_preview(self, painter: QPainter) -> None:
        """The preview dots (and the faint input grid), plotted through numpy into an image (tens of thousands of
        points stay cheap)."""
        w, h = self.width(), self.height()
        if w <= 0 or h <= 0 or (self._preview_points is None and self._input_points is None):
            return
        image = np.zeros((h, w, 4), dtype=np.uint8)
        c = self._preview_color
        for pts, rgba in ((self._input_points, (150, 150, 150, 70)), (self._preview_points, (c.red(), c.green(), c.blue(), 210))):
            if pts is None:
                continue
            px = np.floor(w / 2 + (pts[:, 0] - self._center[0]) * self._ppu).astype(np.int64)
            py = np.floor(h / 2 - (pts[:, 1] - self._center[1]) * self._ppu).astype(np.int64)
            inside = (px >= 0) & (px < w) & (py >= 0) & (py < h)
            image[py[inside], px[inside]] = rgba
        painter.drawImage(0, 0, QImage(image.data, w, h, w * 4, QImage.Format.Format_RGBA8888))

    def _points(self, triangle: Triangle) -> list[QPointF]:
        return [self.to_screen(p) for p in triangle]

    def _paint_reference(self, painter: QPainter) -> None:
        a, b, c = self._points(T.REFERENCE)
        pen = QPen(REFERENCE_COLOR, 1, Qt.PenStyle.DotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(QPolygonF([a, b, c]))
        painter.setPen(REFERENCE_COLOR)
        painter.drawText(QPointF(c.x() - 10, c.y() - 4), "Y")
        painter.drawText(QPointF(a.x() + 4, a.y() + 12), "X")
        painter.drawText(QPointF(b.x() - 10, b.y() + 12), "O")

    def _paint_ghost(self, painter: QPainter, base: QColor, triangle: Triangle, label: str) -> None:
        color = QColor(base)
        color.setAlpha(110 if not label else 80)
        pen = QPen(color, 1, Qt.PenStyle.DotLine if not label else Qt.PenStyle.DashDotLine)
        painter.setPen(pen)
        painter.setBrush(Qt.BrushStyle.NoBrush)
        points = self._points(triangle)
        painter.drawPolygon(QPolygonF(points))
        if label:
            o = points[CORNER_O]
            painter.drawText(QPointF(o.x() + 5, o.y() - 4), label)

    def _paint_entry(self, painter: QPainter, e: TriangleEntry, selected: bool) -> None:
        a, b, c = self._points(e.triangle)
        color = QColor(e.color)
        if selected:
            painter.setPen(QPen(color, 1.5))
            painter.drawLine(a, b)
            painter.drawLine(b, c)
            painter.setPen(QPen(color.darker(150), 1, Qt.PenStyle.DotLine))
            painter.drawLine(c, a)
            fill = QColor(color)
            fill.setAlpha(28)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(fill)
            painter.drawPolygon(QPolygonF([a, b, c]))
        else:
            painter.setPen(QPen(color, 1, Qt.PenStyle.DotLine))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawPolygon(QPolygonF([a, b, c]))
        painter.setPen(QPen(color, 1))
        painter.setBrush(QBrush(BACKGROUND))
        r = CORNER_RADIUS_PX if selected else CORNER_RADIUS_PX - 1
        for p in (a, b, c):
            painter.drawEllipse(p, r, r)
        painter.setPen(color)
        painter.drawText(QPointF(a.x() + 5, a.y() + 12), "X")
        painter.drawText(QPointF(c.x() + 5, c.y() - 4), "Y")
        painter.drawText(QPointF(b.x() + 5, b.y() + 12), "O")
        if e.label:
            painter.drawText(QPointF(b.x() - 6 - painter.fontMetrics().horizontalAdvance(e.label), b.y() + 12), e.label)

    def _paint_hover(self, painter: QPainter) -> None:
        hit = self._hover
        e = self.entry(hit.key) if hit is not None else None
        if e is None:
            return
        a, b, c = self._points(e.triangle)
        glow = QColor(e.color)
        glow.setAlpha(70)
        painter.setPen(QPen(glow, 4))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawPolygon(QPolygonF([a, b, c]))
        if hit.edge is not None:
            i = hit.edge
            painter.setPen(QPen(e.color, 5))
            painter.drawLine(self._points(e.triangle)[i], self._points(e.triangle)[(i + 1) % 3])
        if hit.corner is not None:
            p = self._points(e.triangle)[hit.corner]
            painter.setPen(QPen(QColor(255, 255, 255), 1))
            painter.setBrush(CORNER_HOVER[hit.corner])
            painter.drawEllipse(p, CORNER_RADIUS_PX + 1, CORNER_RADIUS_PX + 1)
        if self._drag is None and e.hint:
            painter.setPen(e.color)
            metrics = painter.fontMetrics()
            y = self.height() - 8
            for line in reversed(e.hint):
                painter.drawText(QPointF(self.width() - 8 - metrics.horizontalAdvance(line), y), line)
                y -= metrics.height()

    def _paint_helpers(self, painter: QPainter) -> None:
        state = self._drag
        if state is None or not self.show_helpers:
            return
        painter.setPen(QPen(HELPER_COLOR, 1, Qt.PenStyle.DotLine))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        pv = self.to_screen(state.pivot)
        painter.drawLine(QPointF(pv.x(), 0), QPointF(pv.x(), self.height()))
        painter.drawLine(QPointF(0, pv.y()), QPointF(self.width(), pv.y()))
        triangle = self.triangle(self._drag_key)
        if triangle is None:
            return
        if state.mode == MODE_ROTATE:
            r = state.olddist * self._ppu
            if r > 4:
                painter.drawEllipse(pv, r, r)
        elif state.mode == MODE_SCALE:
            corners = [triangle[state.corner]] if state.corner is not None else list(triangle)
            for corner in corners:
                dx, dy = corner[0] - state.pivot[0], corner[1] - state.pivot[1]
                if dx or dy:
                    far = 1e4 / max(self._ppu, 1e-9)
                    n = math.hypot(dx, dy)
                    p0 = self.to_screen((state.pivot[0] - dx / n * far, state.pivot[1] - dy / n * far))
                    p1 = self.to_screen((state.pivot[0] + dx / n * far, state.pivot[1] + dy / n * far))
                    painter.drawLine(p0, p1)

    def _paint_pivot(self, painter: QPainter) -> None:
        if self.entry(self._selected_key) is None:
            return
        p = self.to_screen(self.pivot())
        painter.setPen(QPen(PIVOT_COLOR, 1))
        painter.setBrush(QBrush(QColor(192, 192, 192)))
        r = 2.5 if self.pivot_mode == PIVOT_LOCAL else 3.5
        painter.drawEllipse(p, r, r)

    def _paint_captions(self, painter: QPainter) -> None:
        painter.setPen(TEXT_COLOR)
        font = QFont(painter.font())
        font.setBold(True)
        painter.setFont(font)
        if self.mode_caption:
            painter.drawText(QPointF(8, 18), self.mode_caption)
        if self._has_focus_frame:
            painter.setPen(QPen(HELPER_COLOR, 1))
            s, o = 24, 3
            w, h = self.width() - 1, self.height() - 1
            for (x, y, dx, dy) in ((o, o, 1, 1), (w - o, o, -1, 1), (o, h - o, 1, -1), (w - o, h - o, -1, -1)):
                painter.drawLine(QPointF(x, y), QPointF(x + dx * s, y))
                painter.drawLine(QPointF(x, y), QPointF(x, y + dy * s))

    def _caption(self, key: object) -> str:
        e = self.entry(key)
        return f"Transform {e.label}" if e is not None and e.label else ""


__all__ = ["TriangleView", "TriangleEntry", "Hit", "transform_color", "MODE_MOVE", "MODE_ROTATE", "MODE_SCALE", "PIVOT_LOCAL",
           "PIVOT_WORLD", "TRANSFORM_COLORS", "FINAL_COLOR"]
