"""The gradient currently being edited, plus where it came from.

Widgets and file actions both talk to this object; it is the only thing that
mutates the Gradient, and it announces every change via signals.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..formats import GradientFormat, format_for
from ..model import RGB, Gradient


class GradientDocument(QObject):
    gradient_replaced = Signal()          # a whole new gradient was loaded
    stop_changed = Signal(int)            # a single stop moved / recoloured (its current index)
    selection_changed = Signal(int)       # -1 when nothing is selected

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._gradient = Gradient()
        self._source_path: Path | None = None
        self._source_index = 0
        self._selected = -1
        self.modified = False

    # --- state --------------------------------------------------------------
    @property
    def gradient(self) -> Gradient:
        return self._gradient

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def source_index(self) -> int:
        """Which entry of a multi-gradient source file this is."""
        return self._source_index

    @property
    def source_format(self) -> GradientFormat | None:
        return format_for(self._source_path) if self._source_path else None

    @property
    def selected_index(self) -> int:
        return self._selected

    # --- commands -----------------------------------------------------------
    def replace(self, gradient: Gradient, source_path: Path | None = None, source_index: int = 0) -> None:
        self._gradient = gradient
        self._source_path = source_path
        self._source_index = source_index
        self.modified = False
        self.select(-1)
        self.gradient_replaced.emit()

    def mark_saved(self, path: Path, index: int = 0) -> None:
        self._source_path = path
        self._source_index = index
        self.modified = False

    def is_showing(self, path: Path, index: int) -> bool:
        return self._source_path == path and self._source_index == index

    def move_stop(self, index: int, position: float) -> int:
        """Move a stop; selection follows it. Returns its new index."""
        new_index = self._gradient.move_stop(index, position)
        if self._selected == index:
            self.select(new_index)
        self._touch(new_index)
        return new_index

    def set_color(self, index: int, color: RGB) -> None:
        self._gradient.set_color(index, color)
        self._touch(index)

    def select(self, index: int) -> None:
        if index != self._selected:
            self._selected = index
            self.selection_changed.emit(index)

    # --- internals ----------------------------------------------------------
    def _touch(self, index: int) -> None:
        self.modified = True
        self.stop_changed.emit(index)
