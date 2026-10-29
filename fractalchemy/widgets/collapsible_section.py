"""A titled section that folds away behind a caret — for options a panel should offer without showing all the time.

    section = CollapsibleSection("Variation preview", options_widget)
    section.set_expanded(False)                     # collapsed: just the caret and the title
    section.toggled.connect(save_state)
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QSizePolicy, QToolButton, QVBoxLayout, QWidget


class CollapsibleSection(QWidget):
    """A caret + title button over a content widget that shows only while expanded.

    Signals:
        toggled(bool): Expanded (True) or collapsed.
    """
    toggled = Signal(bool)

    def __init__(self, title: str, content: QWidget, parent: QWidget | None = None, expanded: bool = False):
        super().__init__(parent)
        self.header = QToolButton(self)
        self.header.setText(title)
        self.header.setCheckable(True)
        self.header.setAutoRaise(True)
        self.header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        self.header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.header.setStyleSheet("QToolButton { text-align: left; padding: 2px; }")
        self.content = content
        content.setParent(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.header)
        layout.addWidget(content)
        self.header.toggled.connect(self._on_toggled)
        self.header.setChecked(expanded)
        self._on_toggled(expanded)

    @property
    def expanded(self) -> bool:
        """True while the content shows."""
        return self.header.isChecked()

    def set_expanded(self, expanded: bool) -> None:
        """Show or fold the content."""
        self.header.setChecked(expanded)

    def _on_toggled(self, expanded: bool) -> None:
        self.header.setArrowType(Qt.ArrowType.DownArrow if expanded else Qt.ArrowType.RightArrow)
        self.content.setVisible(expanded)
        self.toggled.emit(expanded)


__all__ = ["CollapsibleSection"]
