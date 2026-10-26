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
from ..model.node_ops import without


class GradientDocument(QObject):
    """The gradient being edited, its origin, selection and pending adjustments.

    Every mutation goes through this object so widgets can stay in sync via
    signals. Whole-gradient adjustments are applied to a base snapshot and are
    baked in ("committed") by any other edit.

    Signals:
        gradient_replaced(): A different gradient was loaded.
        gradient_changed(): Any or all stops changed (adjustment / operation).
        stop_changed(int): One stop moved or was recoloured; its current index.
        selection_changed(int): The selected node index, -1 for none.
        adjustments_reset(): Pending slider values were committed; sliders show 0.
    """
    gradient_replaced = Signal()
    gradient_changed = Signal()
    stop_changed = Signal(int)
    selection_changed = Signal(int)
    adjustments_reset = Signal()

    def __init__(self, parent: QObject | None = None):
        """Start with an empty, unmodified gradient and no source file."""
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
        """The gradient as currently displayed (adjustments applied)."""
        return self._gradient

    @property
    def source_path(self) -> Path | None:
        """File the gradient came from, or None."""
        return self._source_path

    @property
    def source_index(self) -> int:
        """Which entry of a multi-gradient source file this is."""
        return self._source_index

    @property
    def source_format(self) -> GradientFormat | None:
        """Format of the source file, or None."""
        return format_for(self._source_path) if self._source_path else None

    @property
    def selected_index(self) -> int:
        """Index of the selected node, -1 for none."""
        return self._selected

    @property
    def adjustments(self) -> Adjustments:
        """Pending whole-gradient slider values."""
        return self._adjustments

    # --- commands -----------------------------------------------------------
    def replace(self, gradient: Gradient, source_path: Path | None = None, source_index: int = 0) -> None:
        """Show a new gradient, recording where it came from; clears edits and selection."""
        self._gradient = gradient
        self._source_path = source_path
        self._source_index = source_index
        self.modified = False
        self._reset_adjustments()
        self.select(-1)
        self.gradient_replaced.emit()

    def mark_saved(self, path: Path, index: int = 0) -> None:
        """Record that the gradient now lives at `path` / `index` and is unmodified."""
        self._source_path = path
        self._source_index = index
        self.modified = False

    def is_showing(self, path: Path, index: int) -> bool:
        """True if the document's source is exactly `path` / `index`."""
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
    def insert_stop(self, stops: list[ColorStop], new_index: int) -> None:
        """Replace the stop list (already containing the new node) and select the new node."""
        self._commit_adjustments()
        self._gradient = Gradient(self._gradient.name, stops)
        self.modified = True
        self.gradient_changed.emit()
        self.select(new_index)

    def remove_stop(self, index: int) -> None:
        """Delete a node and select its successor (or the new last node)."""
        self._commit_adjustments()
        self._gradient = Gradient(self._gradient.name, without(self._gradient, index))
        self.modified = True
        self.select(-1)
        self.gradient_changed.emit()
        self.select(min(index, len(self._gradient.stops) - 1))

    def move_stop(self, index: int, position: float) -> int:
        """Move a stop; selection follows it. Returns its new index."""
        self._commit_adjustments()
        new_index = self._gradient.move_stop(index, position)
        if self._selected == index:
            self.select(new_index)
        self._touch(new_index)
        return new_index

    def set_color(self, index: int, color: RGB) -> None:
        """Recolour node `index` (commits pending adjustments first)."""
        self._commit_adjustments()
        self._gradient.set_color(index, color)
        self._touch(index)

    def select(self, index: int) -> None:
        """Select node `index` (-1 clears); emits only on change."""
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
