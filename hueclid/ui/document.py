"""The gradient currently being edited, plus where it came from.

Widgets and file actions both talk to this object; it is the only thing that
mutates the Gradient, and it announces every change via signals.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from typing import Callable

from ..formats import GradientFormat, format_for
from ..model import RGB, ColorStop, Gradient
from ..model.adjust import Adjustments, apply_adjustments


class GradientDocument(QObject):
    gradient_replaced = Signal()          # a whole new gradient was loaded
    gradient_changed = Signal()           # every stop may have changed (adjustment / operation)
    stop_changed = Signal(int)            # a single stop moved / recoloured (its current index)
    selection_changed = Signal(int)       # -1 when nothing is selected
    adjustments_reset = Signal()          # pending slider adjustments were baked in; sliders go to 0

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._gradient = Gradient()
        self._source_path: Path | None = None
        self._source_index = 0
        self._selected = -1
        self._base: Gradient | None = None        # gradient before the pending adjustments
        self._adjustments = Adjustments()
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

    @property
    def adjustments(self) -> Adjustments:
        return self._adjustments

    # --- commands -----------------------------------------------------------
    def replace(self, gradient: Gradient, source_path: Path | None = None, source_index: int = 0) -> None:
        self._gradient = gradient
        self._source_path = source_path
        self._source_index = source_index
        self.modified = False
        self._reset_adjustments()
        self.select(-1)
        self.gradient_replaced.emit()

    def mark_saved(self, path: Path, index: int = 0) -> None:
        self._source_path = path
        self._source_index = index
        self.modified = False

    def is_showing(self, path: Path, index: int) -> bool:
        return self._source_path == path and self._source_index == index

    # --- whole-gradient edits ----------------------------------------------
    def set_adjustments(self, adjustments: Adjustments) -> None:
        """Re-derive the gradient from the base snapshot with new slider values (lossless)."""
        if self._base is None:
            self._base = self._gradient.copy()
        self._adjustments = adjustments
        self._gradient = apply_adjustments(self._base, adjustments)
        self.modified = True
        self.select(-1)
        self.gradient_changed.emit()

    def apply_operation(self, operation: Callable[[Gradient], list[ColorStop]]) -> None:
        """Replace all stops with `operation(gradient)`; bakes in any pending adjustments first."""
        self._commit_adjustments()
        self._gradient = Gradient(self._gradient.name, operation(self._gradient))
        self.modified = True
        self.select(-1)
        self.gradient_changed.emit()

    # --- single-stop edits --------------------------------------------------
    def move_stop(self, index: int, position: float) -> int:
        """Move a stop; selection follows it. Returns its new index."""
        self._commit_adjustments()
        new_index = self._gradient.move_stop(index, position)
        if self._selected == index:
            self.select(new_index)
        self._touch(new_index)
        return new_index

    def set_color(self, index: int, color: RGB) -> None:
        self._commit_adjustments()
        self._gradient.set_color(index, color)
        self._touch(index)

    def select(self, index: int) -> None:
        if index != self._selected:
            self._selected = index
            self.selection_changed.emit(index)

    # --- internals ----------------------------------------------------------
    def _commit_adjustments(self) -> None:
        """The adjusted gradient becomes the new base; sliders return to zero."""
        if self._base is not None:
            self._reset_adjustments()

    def _reset_adjustments(self) -> None:
        had_pending = self._base is not None or not self._adjustments.is_identity
        self._base = None
        self._adjustments = Adjustments()
        if had_pending:
            self.adjustments_reset.emit()

    def _touch(self, index: int) -> None:
        self.modified = True
        self.stop_changed.emit(index)
