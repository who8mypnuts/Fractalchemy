"""Horizontal strip of every gradient in the current file; click one to edit it."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QAbstractItemView, QListView, QListWidget, QListWidgetItem, QWidget

from ..model import Gradient
from .thumbnail import THUMBNAIL_SIZE, render_thumbnail


class GradientBrowser(QListWidget):
    """Horizontal strip of thumbnails, one per gradient in the open file.

    Signals:
        entry_chosen(int): The user clicked the thumbnail at this index.
    """
    entry_chosen = Signal(int)

    def __init__(self, parent: QWidget | None = None):
        """Configure a single-row, horizontally scrolling icon view."""
        super().__init__(parent)
        self._path: Path | None = None
        self._configure()
        self.itemClicked.connect(lambda item: self.entry_chosen.emit(self.row(item)))

    def _configure(self) -> None:
        self.setViewMode(QListView.ViewMode.IconMode)
        self.setFlow(QListView.Flow.LeftToRight)
        self.setWrapping(False)
        self.setMovement(QListView.Movement.Static)
        self.setIconSize(THUMBNAIL_SIZE)
        self.setSpacing(6)
        self.setUniformItemSizes(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setFixedHeight(THUMBNAIL_SIZE.height() + 48)
        self.setToolTip("Gradients in this file — click one to edit it")

    # --- API ----------------------------------------------------------------
    @property
    def path(self) -> Path | None:
        """File whose entries are shown, or None."""
        return self._path

    def set_entries(self, path: Path | None, gradients: list[Gradient]) -> None:
        """Show thumbnails for `gradients` from `path`."""
        self._path = path
        self.clear()
        for gradient in gradients:
            self.addItem(self._make_item(gradient))

    def update_entry(self, index: int, gradient: Gradient) -> None:
        """Re-render the thumbnail and name at `index`."""
        item = self.item(index)
        if item is not None:
            item.setIcon(QIcon(render_thumbnail(gradient)))
            item.setText(gradient.name)
            item.setToolTip(_tooltip(gradient, index))

    def set_current(self, index: int) -> None:
        """Highlight and scroll to `index` without emitting entry_chosen."""
        if 0 <= index < self.count():
            self.setCurrentRow(index)
            self.scrollToItem(self.item(index))
        else:
            self.clearSelection()

    # --- internals ----------------------------------------------------------
    def _make_item(self, gradient: Gradient) -> QListWidgetItem:
        item = QListWidgetItem(QIcon(render_thumbnail(gradient)), gradient.name)
        item.setToolTip(_tooltip(gradient, self.count()))
        item.setSizeHint(QSize(THUMBNAIL_SIZE.width() + 12, THUMBNAIL_SIZE.height() + 28))
        item.setTextAlignment(Qt.AlignmentFlag.AlignHCenter)
        return item


def _tooltip(gradient: Gradient, index: int) -> str:
    return f"#{index + 1}  {gradient.name}  ({len(gradient)} nodes)"
