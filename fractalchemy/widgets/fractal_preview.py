"""A small mirror of the main window's fractal viewport, for other windows.

It never renders anything itself: `set_image()` receives whatever the viewport
just displayed, so the Gradient Library can show the effect of a gradient edit
even when it covers the main window.
"""

from __future__ import annotations

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPaintEvent
from PySide6.QtWidgets import QSizePolicy, QWidget

BACKGROUND = QColor(24, 24, 24)
TEXT = QColor(110, 110, 110)


class FractalPreview(QWidget):
    """Paints the latest viewport image, letterboxed to keep its aspect ratio."""

    def __init__(self, parent: QWidget | None = None, size: QSize = QSize(256, 144)):
        super().__init__(parent)
        self._image: QImage | None = None
        self._placeholder = "No fractal loaded"
        self.setFixedSize(size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.setToolTip("The fractal shown in the main window, with the current gradient")

    @property
    def image(self) -> QImage | None:
        return self._image

    def set_image(self, image: QImage | None) -> None:
        """Show `image` (None clears the preview)."""
        self._image = image
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), BACKGROUND)
        if self._image is None or self._image.isNull():
            painter.setPen(TEXT)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, self._placeholder)
        else:
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            painter.drawImage(fitted_rect(self._image.size(), self.rect()), self._image)
        painter.end()


def fitted_rect(image: QSize, box: QRect) -> QRect:
    """The largest rectangle of `image`'s aspect ratio centred inside `box`."""
    scaled = image.scaled(box.size(), Qt.AspectRatioMode.KeepAspectRatio)
    return QRect(box.x() + (box.width() - scaled.width()) // 2, box.y() + (box.height() - scaled.height()) // 2,
                 scaled.width(), scaled.height())
