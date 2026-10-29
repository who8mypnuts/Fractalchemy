"""A small captioned gradient swatch that acts as a button — the Formula Editor's gradient chooser.

    bar = GradientBar("Gradient")
    bar.set_palette(flame.palette)          # RGB triples, 0..255
    bar.clicked.connect(open_gradient_library)
"""

from __future__ import annotations

from PySide6.QtCore import QRect, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QLabel, QSizePolicy, QVBoxLayout, QWidget

from .images import palette_pixmap

BAR_HEIGHT = 18
BORDER = QColor(70, 70, 70)
HOVER_BORDER = QColor(200, 200, 200)


class _Swatch(QWidget):
    """The painted band; repaints from the palette it was last given."""
    clicked = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._palette: list = []
        self._hover = False
        self.setFixedHeight(BAR_HEIGHT)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)

    @property
    def palette_colors(self) -> list:
        """The colours shown (RGB triples)."""
        return list(self._palette)

    def set_palette(self, palette) -> None:
        """Show `palette` (RGB triples, 0..255)."""
        self._palette = list(palette)
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        rect = self.rect().adjusted(0, 0, -1, -1)
        if self._palette:
            painter.drawPixmap(QRect(0, 0, self.width(), self.height()), palette_pixmap(self._palette, self.width(), self.height()))
        else:
            painter.fillRect(rect, QColor(40, 40, 40))
        painter.setPen(QPen(HOVER_BORDER if self._hover else BORDER))
        painter.drawRect(rect)
        painter.end()

    def enterEvent(self, event) -> None:
        self._hover = True
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:
        self._hover = False
        self.update()
        super().leaveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self.rect().contains(event.position().toPoint()):
            self.clicked.emit()
        super().mouseReleaseEvent(event)


class GradientBar(QWidget):
    """A caption over a clickable gradient band.

    Signals:
        clicked(): The band was clicked.
    """
    clicked = Signal()

    def __init__(self, caption: str = "Gradient", parent: QWidget | None = None):
        super().__init__(parent)
        self.label = QLabel(caption, self)
        self.swatch = _Swatch(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.label)
        layout.addWidget(self.swatch)
        self.swatch.clicked.connect(self.clicked)

    @property
    def palette_colors(self) -> list:
        """The colours shown (RGB triples)."""
        return self.swatch.palette_colors

    def set_palette(self, palette) -> None:
        """Show `palette` (RGB triples, 0..255)."""
        self.swatch.set_palette(palette)


__all__ = ["GradientBar"]
