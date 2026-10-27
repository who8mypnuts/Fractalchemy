"""The flame currently shown in the main window, plus where it came from."""

from __future__ import annotations

import time
from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..fractal.scene import Flame
from ..model import Gradient

UNDO_COALESCE_SECONDS = 1.0   # edits of the same kind within this window (slider drags) are one undo step
UNDO_LIMIT = 200


class FractalDocument(QObject):
    """Holds the current Flame; every change is announced so the viewport and status bar follow.

    Signals:
        flame_replaced(): A different flame was loaded.
        camera_changed(): The view (center / zoom / rotation / 3D camera) of the current flame changed.
        palette_changed(): The flame's colours changed (e.g. edited in the Gradient Library).
        coloring_changed(): Brightness / gamma / threshold / vibrancy / background changed.
        image_size_changed(): The output resolution chosen for the viewer changed.
        modified_changed(bool): Whether the flame differs from what was loaded / last saved.
        flame_restored(): Undo / redo / paste put a different state in place (anything may have changed).
        undo_changed(bool, bool): (can undo, can redo).
    """
    flame_replaced = Signal()
    camera_changed = Signal()
    palette_changed = Signal()
    coloring_changed = Signal()
    image_size_changed = Signal()
    modified_changed = Signal(bool)
    flame_restored = Signal()
    undo_changed = Signal(bool, bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._flame: Flame | None = None
        self._original: Flame | None = None   # as loaded, so adjustments can be reverted
        self._source_path: Path | None = None
        self._source_index = 0
        self._image_size: tuple[int, int] | None = None   # None = the flame's own size
        self._modified = False
        self._undo: list[tuple[str, Flame]] = []
        self._redo: list[Flame] = []
        self._last_edit: tuple[str, float] = ("", 0.0)

    @property
    def flame(self) -> Flame | None:
        return self._flame

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def source_index(self) -> int:
        return self._source_index

    @property
    def image_size(self) -> tuple[int, int]:
        """Output resolution the viewer frames: the chosen one, else the flame's own size."""
        if self._image_size is not None:
            return self._image_size
        if self._flame is not None:
            return (self._flame.camera.width, self._flame.camera.height)
        return (800, 600)

    @property
    def custom_image_size(self) -> tuple[int, int] | None:
        """The explicitly chosen resolution, or None when following the flame."""
        return self._image_size

    def set_image_size(self, size: tuple[int, int] | None) -> None:
        """Choose the output resolution (None = the flame's own size)."""
        size = None if size is None else (max(1, int(size[0])), max(1, int(size[1])))
        if size != self._image_size:
            self._image_size = size
            self.image_size_changed.emit()

    def is_showing(self, path: Path, index: int) -> bool:
        return self._source_path == path and self._source_index == index

    @property
    def modified(self) -> bool:
        """True once the camera / colouring / palette has been edited since loading or saving."""
        return self._modified

    def mark_saved(self) -> None:
        """The current state is now what the file holds."""
        if self._flame is not None:
            self._original = self._flame.copy()
        self._set_modified(False)

    def _set_modified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    # --- undo / redo ------------------------------------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def _record(self, kind: str) -> None:
        """Remember the state before an edit of `kind` (same-kind edits in quick succession share one step)."""
        if self._flame is None:
            return
        now = time.monotonic()
        last_kind, last_time = self._last_edit
        self._last_edit = (kind, now)
        if self._undo and last_kind == kind and now - last_time < UNDO_COALESCE_SECONDS:
            return
        self._undo.append((kind, self._flame.copy()))
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self.undo_changed.emit(True, False)

    def undo(self) -> bool:
        """Restore the state before the last edit; False if there is nothing to undo."""
        if not self._undo or self._flame is None:
            return False
        _kind, flame = self._undo.pop()
        self._redo.append(self._flame)
        self._restore(flame)
        return True

    def redo(self) -> bool:
        if not self._redo or self._flame is None:
            return False
        flame = self._redo.pop()
        self._undo.append(("redo", self._flame))
        self._restore(flame)
        return True

    def _restore(self, flame: Flame) -> None:
        self._flame = flame
        self._last_edit = ("", 0.0)
        self._set_modified(True)
        self.undo_changed.emit(self.can_undo, self.can_redo)
        self.flame_restored.emit()

    def paste(self, flame: Flame) -> None:
        """Replace the flame's parameters (transforms, camera, coloring, palette) keeping the file link; undoable."""
        if self._flame is None:
            self.replace(flame)
            return
        self._record("paste")
        self._last_edit = ("", 0.0)
        self._flame = flame.copy()
        self._set_modified(True)
        self.flame_restored.emit()

    def set_source(self, path: Path | None, index: int) -> None:
        """Where the flame now lives (after a save into a file / entry)."""
        self._source_path = path
        self._source_index = index

    @property
    def original(self) -> Flame | None:
        """The flame as it was loaded (before any camera / colouring adjustments)."""
        return self._original

    def replace(self, flame: Flame, source_path: Path | None = None, source_index: int = 0) -> None:
        """Show `flame` (the document keeps its own copy)."""
        self._flame = flame.copy()
        self._original = flame.copy()
        self._source_path = source_path
        self._source_index = source_index
        self._undo.clear()
        self._redo.clear()
        self._last_edit = ("", 0.0)
        self._set_modified(False)
        self.undo_changed.emit(False, False)
        self.flame_replaced.emit()

    def set_view(self, center: tuple[float, float] | None = None, zoom: float | None = None, rotate: float | None = None) -> None:
        """Change the camera of the current flame (no-op without a flame)."""
        if self._flame is None:
            return
        self._record("view")
        camera = self._flame.camera
        if center is not None:
            camera.center = (float(center[0]), float(center[1]))
        if zoom is not None:
            camera.zoom = float(zoom)
        if rotate is not None:
            camera.rotate = float(rotate)
        self._set_modified(True)
        self.camera_changed.emit()

    def pan(self, dx: float, dy: float) -> None:
        """Move the view by a fraction of the image (`dx = 0.1` shows what lies 10% of the width to the right).

        Screen directions: y down, the camera's rotation respected.
        """
        if self._flame is None:
            return
        camera = self._flame.camera
        w, h = camera.width, camera.height
        x0, y0 = camera.unproject(w / 2, h / 2, w, h)
        x1, y1 = camera.unproject(w / 2 + dx * w, h / 2 + dy * h, w, h)
        self.set_view(center=(camera.center[0] + x1 - x0, camera.center[1] + y1 - y0))

    def pan_units(self, dx: float, dy: float) -> None:
        """Move the view by `dx` / `dy` fractal units along the screen axes (y down; rotation respected)."""
        if self._flame is None:
            return
        camera = self._flame.camera
        w, h = camera.width, camera.height
        ppu = camera.pixels_per_unit(w, h)
        x0, y0 = camera.unproject(w / 2, h / 2, w, h)
        x1, y1 = camera.unproject(w / 2 + dx * ppu, h / 2 + dy * ppu, w, h)
        self.set_view(center=(camera.center[0] + x1 - x0, camera.center[1] + y1 - y0))

    def set_camera_3d(self, pitch: float | None = None, yaw: float | None = None, perspective: float | None = None,
                      zpos: float | None = None, dof: float | None = None, pitch_y: float | None = None) -> None:
        """Change the 3D camera (angles in radians; None leaves a value alone). No-op without a flame."""
        if self._flame is None:
            return
        self._record("camera3d")
        camera = self._flame.camera
        for name, value in (("pitch", pitch), ("yaw", yaw), ("perspective", perspective), ("zpos", zpos), ("dof", dof),
                            ("pitch_y", pitch_y)):
            if value is not None:
                setattr(camera, name, float(value))
        self._set_modified(True)
        self.camera_changed.emit()

    def set_coloring(self, brightness: float | None = None, gamma: float | None = None, gamma_threshold: float | None = None,
                     vibrancy: float | None = None, contrast: float | None = None, background=None, curves=None) -> None:
        """Change the tone mapping (None leaves a value alone). No-op without a flame."""
        if self._flame is None:
            return
        given = [n for n, v in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                                ("vibrancy", vibrancy), ("contrast", contrast), ("background", background), ("curves", curves)) if v is not None]
        self._record("coloring:" + ",".join(given))
        coloring = self._flame.coloring
        for name, value in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                            ("vibrancy", vibrancy), ("contrast", contrast)):
            if value is not None:
                setattr(coloring, name, float(value))
        if background is not None:
            coloring.background = tuple(int(c) for c in background)
        if curves is not None:
            coloring.curves = curves.copy()
        self._set_modified(True)
        self.coloring_changed.emit()

    def set_curve(self, channel: str, points) -> None:
        """Replace one tone curve's control points. No-op without a flame."""
        if self._flame is None:
            return
        self._record("curve:" + channel)
        self._flame.coloring.curves.set_points(channel, points)
        self._set_modified(True)
        self.coloring_changed.emit()

    def reset_curves(self, channel: str | None = None) -> None:
        """Put one tone curve (or all of them) back to the identity."""
        if self._flame is None:
            return
        self._record("curves-reset")
        self._flame.coloring.curves.reset(channel)
        self._set_modified(True)
        self.coloring_changed.emit()

    def revert_view(self) -> None:
        """Put the centre / zoom / rotation back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.camera
        self.set_view(center=o.center, zoom=o.zoom, rotate=o.rotate)

    def revert_camera_3d(self) -> None:
        """Put the 3D camera back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.camera
        self.set_camera_3d(o.pitch, o.yaw, o.perspective, o.zpos, o.dof, o.pitch_y)

    def revert_coloring(self) -> None:
        """Put the tone mapping back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.coloring
        self.set_coloring(o.brightness, o.gamma, o.gamma_threshold, o.vibrancy, o.contrast, o.background, o.curves)

    def set_gradient(self, gradient: Gradient) -> None:
        """Recolour the current flame from a Gradient (no-op without a flame, or if nothing changes)."""
        if self._flame is None:
            return
        palette = list(gradient.sample(len(self._flame.palette) or 256))
        if palette == self._flame.palette:
            return
        self._record("palette")
        self._flame.palette = palette
        self._set_modified(True)
        self.palette_changed.emit()
