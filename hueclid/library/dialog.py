"""Modal 'Edit Library' window: one row per root with path, file count and a remove button."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QDialogButtonBox, QHeaderView, QPushButton, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from .controller import LibraryController


class EditLibraryDialog(QDialog):
    """Modal list of library folders with file counts and per-row remove buttons."""
    def __init__(self, controller: LibraryController, add_folder, parent: QWidget | None = None):
        """Args:
            controller: Source of roots and counts; also performs removal.
            add_folder: Callable that prompts for and adds a folder.
            parent: Qt parent.
        """
        super().__init__(parent)
        self._controller = controller
        self._add_folder = add_folder  # callable that prompts for and adds a directory
        self.setWindowTitle("Edit Library")
        self.resize(560, 320)
        self.table = QTreeWidget(self)
        self._build()
        self._refresh()
        controller.roots.added.connect(lambda _: self._refresh())
        controller.roots.removed.connect(lambda _: self._refresh())
        controller.root_scanned.connect(lambda _: self._refresh())

    def _build(self) -> None:
        self.table.setHeaderLabels(["Folder", "Files", ""])
        self.table.setRootIsDecorated(False)
        self.table.setTextElideMode(Qt.TextElideMode.ElideMiddle)
        header = self.table.header()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        add = QPushButton("Add folder…", self)
        add.clicked.connect(self._add_folder)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close, self)
        buttons.addButton(add, QDialogButtonBox.ButtonRole.ActionRole)
        buttons.rejected.connect(self.reject)
        layout = QVBoxLayout(self)
        layout.addWidget(self.table)
        layout.addWidget(buttons)

    def _refresh(self) -> None:
        counts = self._controller.model.file_counts()
        self.table.clear()
        for path in self._controller.roots.paths():
            row = QTreeWidgetItem([str(path), _count_text(counts.get(path)), ""])
            row.setToolTip(0, str(path))
            row.setTextAlignment(1, Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self.table.addTopLevelItem(row)
            self.table.setItemWidget(row, 2, self._remove_button(path))

    def _remove_button(self, path: Path) -> QToolButton:
        button = QToolButton(self)
        button.setText("✕")
        button.setToolTip(f"Remove {path.name} from the library")
        button.setStyleSheet("QToolButton { color: #d03030; font-weight: bold; border: none; }")
        button.clicked.connect(lambda: self._controller.remove_root(path))
        return button


def _count_text(count: int | None) -> str:
    return "…" if count is None else str(count)
