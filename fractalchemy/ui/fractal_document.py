"""The flame currently shown in the main window, plus where it came from."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..fractal.scene import Flame


class FractalDocument(QObject):
    """Holds the current Flame; every change is announced so the viewport and status bar follow.

    Signals:
        flame_replaced(): A different flame was loaded.
        camera_changed(): The view (center / zoom / rotation) of the current flame changed.
    """
    flame_replaced = Signal()
    camera_changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._flame: Flame | None = None
        self._source_path: Path | None = None
        self._source_index = 0

    @property
    def flame(self) -> Flame | None:
        return self._flame

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def source_index(self) -> int:
        return self._source_index

    def is_showing(self, path: Path, index: int) -> bool:
        return self._source_path == path and self._source_index == index

    def replace(self, flame: Flame, source_path: Path | None = None, source_index: int = 0) -> None:
        """Show `flame` (the document keeps its own copy)."""
        self._flame = flame.copy()
        self._source_path = source_path
        self._source_index = source_index
        self.flame_replaced.emit()

    def set_view(self, center: tuple[float, float] | None = None, zoom: float | None = None, rotate: float | None = None) -> None:
        """Change the camera of the current flame (no-op without a flame)."""
        if self._flame is None:
            return
        camera = self._flame.camera
        if center is not None:
            camera.center = (float(center[0]), float(center[1]))
        if zoom is not None:
            camera.zoom = float(zoom)
        if rotate is not None:
            camera.rotate = float(rotate)
        self.camera_changed.emit()
