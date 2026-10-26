"""The editable gradient: colour strip on top, draggable nodes beneath."""

from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .. import config
from ..ui.document import GradientDocument
from .gradient_strip import GradientStrip
from .node_bar import NodeBar


class GradientEditor(QWidget):
    """Built empty (so it can be promoted in Qt Designer); call `bind()` once."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._document: GradientDocument | None = None
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)

    @property
    def document(self) -> GradientDocument | None:
        return self._document

    def bind(self, document: GradientDocument) -> None:
        if self._document is not None:
            raise RuntimeError("GradientEditor is already bound to a document")
        self._document = document
        self.strip = GradientStrip(document, config.EDITOR_MARGIN, self)
        self.nodes = NodeBar(document, config.EDITOR_MARGIN, self)
        self._layout.addWidget(self.strip, 1)
        self._layout.addWidget(self.nodes, 0)
