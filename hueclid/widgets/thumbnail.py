"""Small pixmap previews of gradients for the browser strip."""

from __future__ import annotations

from PySide6.QtCore import QRectF, QSize
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap

from ..model import Gradient
from .qt_colors import to_qgradient

THUMBNAIL_SIZE = QSize(110, 36)


def render_thumbnail(gradient: Gradient, size: QSize = THUMBNAIL_SIZE) -> QPixmap:
    """Paint `gradient` into a bordered pixmap of `size`."""
    pixmap = QPixmap(size)
    pixmap.fill(QColor(40, 40, 40))
    painter = QPainter(pixmap)
    rect = QRectF(0, 0, size.width(), size.height())
    if gradient.stops:
        painter.fillRect(rect, to_qgradient(gradient, rect.left(), rect.right()))
    painter.setPen(QPen(QColor(70, 70, 70)))
    painter.drawRect(rect.adjusted(0, 0, -1, -1))
    painter.end()
    return pixmap
