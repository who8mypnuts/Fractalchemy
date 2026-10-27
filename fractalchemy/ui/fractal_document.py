"""The flame currently shown in the main window, where it came from, and its undo history.

Every edit goes through `edit()`, which records a before/after snapshot on a QUndoStack
(flames are small, so whole-flame snapshots are the simplest reliable history). Rapid
edits of the same kind — a camera drag, a gradient slider — merge into one step.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QUndoCommand, QUndoStack

from ..fractal.scene import Flame
from ..model import Gradient

MERGE_WINDOW_SECONDS = 1.5


class FractalDocument(QObject):
    """Holds the current Flame; every change is announced so the viewport and status bar follow.

    Signals:
        flame_replaced(): A different flame was loaded (history cleared).
        flame_edited(str): Any edit, undo or redo; the text names the step. Emitted *after* the
            specific signal below, so listeners can react either way.
        camera_changed(): The view (center / zoom / rotation) of the current flame changed.
        palette_changed(): The flame's colours changed (e.g. edited in the Gradient Library).
        image_size_changed(): The output resolution chosen for the viewer changed.
        modified_changed(bool): Whether the flame differs from its saved state.
        source_changed(): The flame was saved to a (possibly new) file / entry.
        flame_renamed(): The flame took the name it was saved under.
    """
    source_changed = Signal()
    flame_renamed = Signal()
    flame_replaced = Signal()
    flame_edited = Signal(str)
    camera_changed = Signal()
    palette_changed = Signal()
    image_size_changed = Signal()
    modified_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._flame: Flame | None = None
        self._source_path: Path | None = None
        self._source_index = 0
        self._image_size: tuple[int, int] | None = None   # None = the flame's own size
        self.undo_stack = QUndoStack(self)
        self.undo_stack.cleanChanged.connect(lambda clean: self.modified_changed.emit(not clean))

    # --- state ---------------------------------------------------------------
    @property
    def flame(self) -> Flame | None:
        """The flame being shown, or None."""
        return self._flame

    @property
    def source_path(self) -> Path | None:
        """File the flame came from (or was saved to), or None."""
        return self._source_path

    @property
    def source_index(self) -> int:
        """Which entry of the source file this is."""
        return self._source_index

    @property
    def modified(self) -> bool:
        """True if the flame has edits since it was loaded or saved."""
        return self._flame is not None and not self.undo_stack.isClean()

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

    def is_showing(self, path: Path, index: int) -> bool:
        """True if the document's source is exactly `path` / `index`."""
        return self._source_path == path and self._source_index == index

    # --- loading / saving -----------------------------------------------------
    def replace(self, flame: Flame, source_path: Path | None = None, source_index: int = 0) -> None:
        """Show `flame` (the document keeps its own copy); clears the undo history."""
        self._flame = flame.copy()
        self._source_path = source_path
        self._source_index = source_index
        self.undo_stack.clear()
        self.flame_replaced.emit()

    def mark_saved(self, path: Path, index: int = 0) -> None:
        """Record that the flame now lives at `path` / `index` and is unmodified."""
        self._source_path = path
        self._source_index = index
        self.undo_stack.setClean()
        self.source_changed.emit()

    # --- edits -------------------------------------------------------------------
    def edit(self, text: str, apply: Callable[[Flame], None], merge_id: int = -1) -> bool:
        """Apply `apply(flame)` as an undoable step called `text`; returns False if nothing changed.

        `merge_id` ≥ 0 merges with the previous step of the same id made within MERGE_WINDOW_SECONDS.
        """
        if self._flame is None:
            return False
        before = self._flame.copy()
        apply(self._flame)
        after = self._flame.copy()
        if after.to_dict() == before.to_dict():
            return False
        self.undo_stack.push(_FlameEdit(self, text, before, after, merge_id))
        return True

    def set_view(self, center: tuple[float, float] | None = None, zoom: float | None = None, rotate: float | None = None) -> None:
        """Change the camera of the current flame (undoable; consecutive changes merge)."""
        def apply(flame: Flame) -> None:
            camera = flame.camera
            if center is not None:
                camera.center = (float(center[0]), float(center[1]))
            if zoom is not None:
                camera.zoom = float(zoom)
            if rotate is not None:
                camera.rotate = float(rotate)

        if self.edit("Move camera", apply, merge_id=1):
            self.camera_changed.emit()
            self.flame_edited.emit("Move camera")

    def set_gradient(self, gradient: Gradient) -> None:
        """Recolour the current flame from a Gradient (undoable; consecutive changes merge)."""
        def apply(flame: Flame) -> None:
            flame.palette = list(gradient.sample(len(flame.palette) or 256))

        if self.edit("Edit gradient", apply, merge_id=2):
            self.palette_changed.emit()
            self.flame_edited.emit("Edit gradient")

    def set_image_size(self, size: tuple[int, int] | None) -> None:
        """Choose the output resolution (None = the flame's own size). Not part of the undo history."""
        size = None if size is None else (max(1, int(size[0])), max(1, int(size[1])))
        if size != self._image_size:
            self._image_size = size
            self.image_size_changed.emit()

    # --- undo plumbing -----------------------------------------------------------
    def _restore(self, flame: Flame, text: str) -> None:
        """Called by undo/redo: swap in a snapshot and tell everyone."""
        old = self._flame
        self._flame = flame.copy()
        if old is None or old.camera != self._flame.camera:
            self.camera_changed.emit()
        if old is None or old.palette != self._flame.palette:
            self.palette_changed.emit()
        self.flame_edited.emit(text)


class _FlameEdit(QUndoCommand):
    """Before/after snapshot of the whole flame."""

    def __init__(self, document: FractalDocument, text: str, before: Flame, after: Flame, merge_id: int):
        super().__init__(text)
        self._document = document
        self._before, self._after = before, after
        self._merge_id = merge_id
        self._time = time.monotonic()
        self._applied_once = False

    def id(self) -> int:
        return self._merge_id

    def mergeWith(self, other: QUndoCommand) -> bool:
        if not isinstance(other, _FlameEdit) or other._merge_id != self._merge_id or self._merge_id < 0:
            return False
        if other._time - self._time > MERGE_WINDOW_SECONDS:
            return False
        self._after = other._after
        self._time = other._time
        return True

    def redo(self) -> None:
        if not self._applied_once:   # the edit was already applied when pushed
            self._applied_once = True
            return
        self._document._restore(self._after, self.text())

    def undo(self) -> None:
        self._document._restore(self._before, self.text())
