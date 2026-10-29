"""The find / replace strip shown above a code editor (Ctrl+F / Ctrl+H in the Script and Formula Editors)."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QWidget

from .base_code_editor import BaseCodeEditor


class FindBar(QWidget):
    """Find / replace strip above the editor (Ctrl+F / Ctrl+H): next / previous, replace one / all, match case."""

    def __init__(self, editor: BaseCodeEditor, parent: QWidget | None = None):
        super().__init__(parent)
        self._editor = editor
        self.find_box = QLineEdit(self, placeholderText="Find")
        self.replace_box = QLineEdit(self, placeholderText="Replace with")
        self.case_box = QCheckBox("Match case", self)
        self.count_label = QLabel(self)
        self.next_button = QPushButton("Next", self)
        self.previous_button = QPushButton("Previous", self)
        self.replace_button = QPushButton("Replace", self)
        self.replace_all_button = QPushButton("Replace all", self)
        self.close_button = QPushButton("✕", self)
        self.close_button.setFixedWidth(28)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        for w in (self.find_box, self.previous_button, self.next_button, self.count_label, self.replace_box, self.replace_button,
                  self.replace_all_button, self.case_box):
            layout.addWidget(w)
        layout.addStretch(1)
        layout.addWidget(self.close_button)
        self.find_box.textChanged.connect(self._changed)
        self.find_box.returnPressed.connect(self.find_next)
        self.replace_box.returnPressed.connect(self.replace_one)
        self.next_button.clicked.connect(self.find_next)
        self.previous_button.clicked.connect(self.find_previous)
        self.replace_button.clicked.connect(self.replace_one)
        self.replace_all_button.clicked.connect(self.replace_all)
        self.close_button.clicked.connect(self.dismiss)
        self.case_box.toggled.connect(self._changed)
        self.hide()

    def open(self, replace: bool) -> None:
        selected = self._editor.selected_text()
        if selected and "\n" not in selected:
            self.find_box.setText(selected)
        self.show()
        (self.replace_box if replace else self.find_box).setFocus()
        self.find_box.selectAll()
        self._changed()

    def dismiss(self) -> None:
        self.hide()
        self._editor.setFocus()

    def _changed(self, *_args) -> None:
        count = self._editor.count_matches(self.find_box.text(), self.case_box.isChecked())
        self.count_label.setText(f"{count} match{'es' if count != 1 else ''}" if self.find_box.text() else "")
        if self.find_box.text() and self.sender() is self.find_box:
            self._editor.find_text(self.find_box.text(), False, self.case_box.isChecked())

    def find_next(self) -> None:
        self._editor.find_text(self.find_box.text(), False, self.case_box.isChecked())

    def find_previous(self) -> None:
        self._editor.find_text(self.find_box.text(), True, self.case_box.isChecked())

    def replace_one(self) -> None:
        self._editor.replace_current(self.find_box.text(), self.replace_box.text(), self.case_box.isChecked())
        self._changed()

    def replace_all(self) -> int:
        n = self._editor.replace_all(self.find_box.text(), self.replace_box.text(), self.case_box.isChecked())
        self._changed()
        return n

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.dismiss()
            return
        super().keyPressEvent(event)


__all__ = ["FindBar"]
