"""The main window's Fractal Library pane: the generic library panel plus list / thumbnail views."""

from __future__ import annotations

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QButtonGroup, QStyle, QToolButton, QWidget

from ..library.catalog import FRACTAL_CATALOG
from ..library.panel import LibraryPanel

LIST_ICON_SIZE = QSize(16, 16)


class FractalLibraryPanel(LibraryPanel):
    """Library tree of .flame / .chaos / .fa files with a list ↔ thumbnail view toggle.

    Signals:
        view_mode_changed(bool): True when the thumbnail view was selected.
    """
    view_mode_changed = Signal(bool)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent, FRACTAL_CATALOG)
        self.list_button = QToolButton(self)
        self.thumb_button = QToolButton(self)
        self._build_view_buttons()

    def _build_view_buttons(self) -> None:
        for button, icon, tip in ((self.list_button, _list_icon(self), "List view"),
                                  (self.thumb_button, _thumbnail_icon(self), "Thumbnail view")):
            button.setIcon(icon)
            button.setToolTip(tip)
            button.setCheckable(True)
            button.setAutoRaise(True)
        self.list_button.setChecked(True)
        group = QButtonGroup(self)
        group.setExclusive(True)
        group.addButton(self.list_button)
        group.addButton(self.thumb_button)
        # sit next to the search box, before the collapse button
        top = self.layout().itemAt(0).layout()
        top.insertWidget(1, self.list_button)
        top.insertWidget(2, self.thumb_button)
        self.thumb_button.toggled.connect(self._on_mode_toggled)

    @property
    def thumbnails_shown(self) -> bool:
        return self.thumb_button.isChecked()

    def set_thumbnail_view(self, on: bool) -> None:
        (self.thumb_button if on else self.list_button).setChecked(True)

    def _on_mode_toggled(self, thumbnails: bool) -> None:
        self.view_mode_changed.emit(thumbnails)

    def apply_icon_size(self, size: QSize) -> None:
        """Row icon size for the current mode (the provider's thumbnail size, or small icons)."""
        self.tree.setIconSize(size)
        self.tree.setUniformRowHeights(size == LIST_ICON_SIZE)  # thumbnail rows are tall, folder rows stay short


def _list_icon(widget: QWidget) -> QIcon:
    fallback = widget.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogListView)
    return QIcon.fromTheme("view-list-details", fallback)


def _thumbnail_icon(widget: QWidget) -> QIcon:
    icon = QIcon.fromTheme("view-preview")
    if not icon.isNull():
        return icon
    pixmap = QPixmap(16, 16)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setPen(widget.palette().text().color())
    for x in (1, 9):
        for y in (1, 9):
            painter.drawRect(x, y, 5, 5)
    painter.end()
    return QIcon(pixmap)
