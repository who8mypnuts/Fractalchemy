"""What the viewport draws over the image and what the mouse may grab there, as small self-contained helpers.

* `MiniMap` — a schematic plan of the 3D scene in a corner: the origin, the target, the eye with its view wedge and
  the keyframe path, seen from above along the camera's up vector (the 2D camera shows its centre and zoom instead);
* `CompareWipe` — *A/B compare*: a frozen reference image on the left of a draggable divider, the live render on the
  right, so a slider change can be judged against the look before it;
* `RegionSelect` — Ctrl+drag a rectangle: the *region of interest* for the render window (a crop rendered at full
  resolution);
* `KeyframeHandles` — the keyframe eye points of the camera path are handles: drag one in the screen plane and the
  `KeyFrame` preset is rewritten on release.

Each knows how to paint itself and how to answer a hit test; the viewport decides when to ask.
"""

from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRect, QRectF, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen

MAP_SIZE = 150
MAP_MARGIN = 10
HANDLE_RADIUS = 7.0
DIVIDER_GRAB = 8


class MiniMap:
    """The schematic plan (see the module docstring)."""

    def __init__(self):
        self.enabled = False

    def rect(self, widget_rect: QRect) -> QRect:
        return QRect(widget_rect.left() + MAP_MARGIN, widget_rect.bottom() - MAP_SIZE - MAP_MARGIN, MAP_SIZE, MAP_SIZE)

    def paint(self, painter: QPainter, widget_rect: QRect, camera, path, kind: str) -> None:
        rect = self.rect(widget_rect)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(rect, QColor(0, 0, 0, 160))
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.drawRect(rect)
        if kind == "3D":
            self._paint_3d(painter, rect, camera, path)
        else:
            self._paint_2d(painter, rect, camera)

    def _paint_2d(self, painter: QPainter, rect: QRect, camera) -> None:
        centre, zoom = camera.center, max(camera.zoom, 1e-300)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(rect.adjusted(6, 4, -4, -4), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft | Qt.TextFlag.TextWordWrap,
                         f"centre {centre[0]:.6g}, {centre[1]:.6g}\nzoom {zoom:.4g}")
        size = rect.width() * 0.4
        painter.setPen(QPen(QColor(120, 120, 120), 1))
        painter.drawRect(QRectF(rect.center().x() - size / 2, rect.center().y() - size / 2 + 14, size, size))
        span = max(2.0, abs(centre[0]) + 1.0 / zoom, abs(centre[1]) + 1.0 / zoom)   # the frame of ±2 world units at least
        scale = size / (2 * span)
        view = size / (zoom * span)                                               # the visible area is 2/zoom across
        x, y = rect.center().x() + centre[0] * scale, rect.center().y() + 14 - centre[1] * scale
        painter.setPen(QPen(QColor(220, 60, 60), 1.5))
        painter.drawRect(QRectF(x - max(2.0, view / 2), y - max(2.0, view / 2), max(4.0, view), max(4.0, view)))

    def _paint_3d(self, painter: QPainter, rect: QRect, camera, path) -> None:
        up = np.array(camera.up, dtype=float)
        up /= max(np.linalg.norm(up), 1e-12)
        forward = np.array(camera.direction, dtype=float)
        forward -= up * float(forward @ up)
        if np.linalg.norm(forward) < 1e-9:
            forward = np.array(camera.right, dtype=float)
        forward /= max(np.linalg.norm(forward), 1e-12)
        right = np.cross(forward, up)
        eye, target = np.array(camera.eye, dtype=float), np.array(camera.target, dtype=float)
        points = [eye, target, np.zeros(3)]
        samples = path.sample(min(path.frames, 200)) if path is not None and getattr(path, "valid", False) else None
        if samples is not None:
            points += [np.asarray(p, dtype=float) for p in samples]
        plane = [(float((p - target) @ right), float((p - target) @ forward)) for p in points]
        extent = max(1e-9, max(max(abs(x), abs(y)) for x, y in plane))
        scale = (MAP_SIZE / 2 - 14) / extent

        def at(xy) -> QPointF:
            return QPointF(rect.center().x() + xy[0] * scale, rect.center().y() - xy[1] * scale)

        if samples is not None:
            painter.setPen(QPen(QColor(220, 60, 60, 180), 1))
            mapped = [at(p) for p in plane[3:]]
            for a, b in zip(mapped, mapped[1:]):
                painter.drawLine(a, b)
        painter.setPen(QPen(QColor(160, 160, 160), 1))
        origin = at(plane[2])
        painter.drawLine(origin + QPointF(-4, 0), origin + QPointF(4, 0))
        painter.drawLine(origin + QPointF(0, -4), origin + QPointF(0, 4))
        eye_pt, target_pt = at(plane[0]), at(plane[1])
        half = math.atan(max(0.01, float(camera.fov)))          # FragM's FOV is the tangent of the half angle
        direction = math.atan2(-(target_pt.y() - eye_pt.y()), target_pt.x() - eye_pt.x())
        length = max(12.0, math.hypot(target_pt.x() - eye_pt.x(), target_pt.y() - eye_pt.y()))
        painter.setPen(QPen(QColor(255, 200, 80, 160), 1))
        for angle in (direction - half, direction + half):
            painter.drawLine(eye_pt, eye_pt + QPointF(math.cos(angle) * length, -math.sin(angle) * length))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor(60, 120, 230))
        painter.drawEllipse(target_pt, 3.5, 3.5)
        painter.setBrush(QColor(220, 60, 60))
        painter.drawEllipse(eye_pt, 3.5, 3.5)
        painter.setPen(QColor(200, 200, 200))
        painter.drawText(rect.adjusted(4, 2, -4, -2), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, f"plan · {extent:.3g} units")


class CompareWipe:
    """*A/B compare* (see the module docstring)."""

    def __init__(self):
        self.reference: QImage | None = None
        self.position = 0.5
        self.enabled = False
        self.dragging = False

    def freeze(self, image: QImage | None) -> bool:
        """Keep `image` as the reference (A); False when there is nothing to keep."""
        if image is None or image.isNull():
            return False
        self.reference = image.copy()
        self.enabled = True
        return True

    def clear(self) -> None:
        self.reference = None
        self.enabled = False

    @property
    def active(self) -> bool:
        return self.enabled and self.reference is not None

    def divider_x(self, image_rect: QRect) -> float:
        return image_rect.left() + self.position * image_rect.width()

    def hits_divider(self, pos: QPointF, image_rect: QRect) -> bool:
        return self.active and abs(pos.x() - self.divider_x(image_rect)) <= DIVIDER_GRAB and image_rect.top() <= pos.y() <= image_rect.bottom()

    def drag_to(self, pos: QPointF, image_rect: QRect) -> None:
        self.position = min(1.0, max(0.0, (pos.x() - image_rect.left()) / max(1, image_rect.width())))

    def paint(self, painter: QPainter, image_rect: QRect) -> None:
        """The reference over the left part of `image_rect` (scaled like the live image), and the divider."""
        if not self.active:
            return
        split = self.divider_x(image_rect)
        left_width = max(0.0, split - image_rect.left())
        if left_width > 0:
            source_width = left_width / max(1, image_rect.width()) * self.reference.width()
            painter.drawImage(QRectF(image_rect.left(), image_rect.top(), left_width, image_rect.height()), self.reference,
                              QRectF(0, 0, source_width, self.reference.height()))
        painter.setPen(QPen(QColor(255, 255, 255, 200), 2))
        painter.drawLine(QPointF(split, image_rect.top()), QPointF(split, image_rect.bottom()))
        painter.setPen(QColor(255, 255, 255, 220))
        painter.drawText(QRectF(image_rect.left() + 6, image_rect.top() + 4, 60, 18), Qt.AlignmentFlag.AlignLeft, "A (frozen)")
        painter.drawText(QRectF(image_rect.right() - 66, image_rect.top() + 4, 60, 18), Qt.AlignmentFlag.AlignRight, "B (live)")


class RegionSelect:
    """Ctrl+drag a rectangle (see the module docstring)."""

    def __init__(self):
        self.start: QPointF | None = None
        self.end: QPointF | None = None
        self.region: tuple[float, float, float, float] | None = None    # the last chosen (x, y, w, h), image fractions

    @property
    def dragging(self) -> bool:
        return self.start is not None

    def begin(self, pos: QPointF) -> None:
        self.start = self.end = pos

    def move(self, pos: QPointF) -> None:
        self.end = pos

    def finish(self, image_rect: QRect) -> tuple[float, float, float, float] | None:
        """The dragged rectangle as image fractions (x, y, w, h; y down), None when it was a mere click."""
        start, end, self.start, self.end = self.start, self.end, None, None
        if start is None or end is None:
            return None
        rect = QRectF(start, end).normalized().intersected(QRectF(image_rect))
        if rect.width() < 4 or rect.height() < 4:
            return None
        w, h = max(1, image_rect.width()), max(1, image_rect.height())
        self.region = ((rect.left() - image_rect.left()) / w, (rect.top() - image_rect.top()) / h, rect.width() / w, rect.height() / h)
        return self.region

    def paint(self, painter: QPainter, image_rect: QRect) -> None:
        if self.start is None or self.end is None:
            return
        rect = QRectF(self.start, self.end).normalized()
        painter.setPen(QPen(QColor(255, 255, 255, 220), 1, Qt.PenStyle.DashLine))
        painter.setBrush(QColor(255, 255, 255, 30))
        painter.drawRect(rect)
        w, h = max(1, image_rect.width()), max(1, image_rect.height())
        painter.setPen(QColor(255, 255, 255, 220))
        painter.drawText(rect.topLeft() + QPointF(4, -4), f"region {rect.width() / w * 100:.0f}% × {rect.height() / h * 100:.0f}%")


class KeyframeHandles:
    """Draggable keyframe eye points (see the module docstring)."""

    def __init__(self):
        self.dragging: str | None = None
        self.point: np.ndarray | None = None     # the eye being dragged (world)
        self._projected: dict[str, tuple[QPointF, float]] = {}   # name → (screen point, clip w)
        self._matrix: np.ndarray | None = None
        self._rect: QRect | None = None

    def update(self, path, matrix: np.ndarray, rect: QRect, project) -> None:
        """Remember where the keyframes project to (`project(points, matrix, rect)` is the viewport's)."""
        self._projected = {}
        self._matrix, self._rect = matrix, rect
        if path is None:
            return
        points = [k.eye for k in path.keyframes]
        for keyframe, screen in zip(path.keyframes, project(points, matrix, rect)):
            if screen is not None:
                clip = matrix @ np.array([*keyframe.eye, 1.0])
                self._projected[keyframe.name] = (screen, float(clip[3]))

    def hit(self, pos: QPointF) -> str | None:
        for name, (screen, _w) in self._projected.items():
            if math.hypot(screen.x() - pos.x(), screen.y() - pos.y()) <= HANDLE_RADIUS:
                return name
        return None

    def begin(self, name: str, eye) -> None:
        self.dragging = name
        self.point = np.array(eye, dtype=float)

    def drag_to(self, pos: QPointF) -> np.ndarray | None:
        """The eye moved to the mouse position at its own depth (screen-plane drag)."""
        if self.dragging is None or self._matrix is None or self._rect is None:
            return None
        _screen, w = self._projected.get(self.dragging, (None, 1.0))
        rect = self._rect
        ndc_x = ((pos.x() - rect.x()) / max(1, rect.width()) - 0.5) * 2.0
        ndc_y = (0.5 - (pos.y() - rect.y()) / max(1, rect.height())) * 2.0
        clip = self._matrix @ np.array([*self.point, 1.0])
        new_clip = np.array([ndc_x * w, ndc_y * w, clip[2], w])
        try:
            world = np.linalg.inv(self._matrix) @ new_clip
        except np.linalg.LinAlgError:
            return None
        if abs(world[3]) < 1e-12:
            return None
        self.point = world[:3] / world[3]
        return self.point

    def finish(self) -> tuple[str, tuple[float, float, float]] | None:
        name, point, self.dragging, self.point = self.dragging, self.point, None, None
        if name is None or point is None:
            return None
        return name, tuple(float(v) for v in point)

    def paint(self, painter: QPainter, project) -> None:
        """Rings around the handles; the dragged one follows the mouse."""
        painter.setPen(QPen(QColor(255, 255, 255, 200), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        for name, (screen, _w) in self._projected.items():
            if name != self.dragging:
                painter.drawEllipse(screen, HANDLE_RADIUS, HANDLE_RADIUS)
        if self.dragging is not None and self.point is not None and self._matrix is not None:
            moved = project([self.point], self._matrix, self._rect)[0]
            if moved is not None:
                painter.setPen(QPen(QColor(255, 230, 80), 2))
                painter.drawEllipse(moved, HANDLE_RADIUS, HANDLE_RADIUS)


__all__ = ["MiniMap", "CompareWipe", "RegionSelect", "KeyframeHandles", "MAP_SIZE"]
