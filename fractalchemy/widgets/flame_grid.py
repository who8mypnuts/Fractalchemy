"""A 3 × 3 grid of small flame previews: the Mutate & Breed window's view.

Each cell shows an image (letterboxed), a caption and its number (1–9, in reading order). The centre cell can be marked
as the *parent*: it is drawn with an accent frame and does not count as a choice. Clicking a cell, or pressing its number,
emits `chosen`; right-clicking emits `menu_requested`; **Space** asks for new offspring (`regenerate_requested`). The grid only displays; what the cells hold is the window's
business. Colours come from the theme: the ground is a canvas (dark on every theme), frames and captions use the
canvas roles.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QPoint, QRect, QSize, Qt, Signal
from PySide6.QtGui import QColor, QImage, QKeyEvent, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import QSizePolicy, QWidget

from .fractal_preview import fitted_rect
from .theming import theme_color

ROWS = COLUMNS = 3
CENTRE = 4
CELLS = ROWS * COLUMNS
GAP = 6
CAPTION_HEIGHT = 18
MIN_CELL = QSize(120, 90)


@dataclass
class Cell:
    """What one cell shows."""
    caption: str = ""
    tooltip: str = ""
    image: QImage | None = None
    busy: bool = False


class FlameGrid(QWidget):
    """The grid (see the module docstring).

    Signals:
        chosen(int): A cell (not the parent) was clicked or its number pressed.
        menu_requested(int, QPoint): Right-click on a cell (global position).
        regenerate_requested(): Space.
    """
    chosen = Signal(int)
    menu_requested = Signal(int, QPoint)
    regenerate_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.cells = [Cell() for _ in range(CELLS)]
        self.parent_cell: int | None = CENTRE
        self.message = ""
        self._hover = -1
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMinimumSize(COLUMNS * MIN_CELL.width() + (COLUMNS + 1) * GAP, ROWS * (MIN_CELL.height() + CAPTION_HEIGHT) + (ROWS + 1) * GAP)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    # --- contents ---------------------------------------------------------------------------------------------------
    def set_cell(self, index: int, caption: str, tooltip: str = "", busy: bool = True) -> None:
        """Caption and tooltip of cell `index`; its image is cleared (and it shows as busy) until `set_image`."""
        self.cells[index] = Cell(caption, tooltip, None, busy)
        self.update()

    def set_image(self, index: int, image: QImage) -> None:
        """The rendered picture of cell `index`."""
        self.cells[index].image = image
        self.cells[index].busy = False
        self.update()

    def clear(self, message: str = "") -> None:
        """Empty every cell; `message` is shown across the grid (e.g. why there is nothing)."""
        self.cells = [Cell() for _ in range(CELLS)]
        self.message = message
        self.update()

    def set_message(self, message: str) -> None:
        """A line across the grid ("" hides it)."""
        self.message = message
        self.update()

    # --- geometry ---------------------------------------------------------------------------------------------------
    def cell_rect(self, index: int) -> QRect:
        """The rectangle of cell `index` (image and caption)."""
        width = (self.width() - (COLUMNS + 1) * GAP) // COLUMNS
        height = (self.height() - (ROWS + 1) * GAP) // ROWS
        row, column = divmod(index, COLUMNS)
        return QRect(GAP + column * (width + GAP), GAP + row * (height + GAP), width, height)

    def cell_at(self, pos: QPoint) -> int:
        """The cell under `pos`, -1 between cells."""
        return next((i for i in range(CELLS) if self.cell_rect(i).contains(pos)), -1)

    def sizeHint(self) -> QSize:
        return QSize(3 * 220 + 4 * GAP, 3 * (150 + CAPTION_HEIGHT) + 4 * GAP)

    # --- painting ---------------------------------------------------------------------------------------------------
    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.fillRect(self.rect(), theme_color("canvas_bg"))
        text, grid, accent = theme_color("canvas_text"), theme_color("canvas_grid"), theme_color("canvas_accent")
        for index, cell in enumerate(self.cells):
            rect = self.cell_rect(index)
            picture = rect.adjusted(0, 0, 0, -CAPTION_HEIGHT)
            painter.fillRect(picture, QColor(0, 0, 0))
            if cell.image is not None:
                painter.drawImage(fitted_rect(cell.image.size(), picture), cell.image)
            elif cell.busy:
                painter.setPen(text)
                painter.drawText(picture, Qt.AlignmentFlag.AlignCenter, "rendering…")
            frame = accent if index == self.parent_cell else (text if index == self._hover and cell.caption else grid)
            painter.setPen(QPen(frame, 2 if index in (self.parent_cell, self._hover) else 1))
            painter.drawRect(picture.adjusted(0, 0, -1, -1))
            painter.setPen(text)
            caption = rect.adjusted(4, rect.height() - CAPTION_HEIGHT, -4, 0)
            label = f"{index + 1}  {cell.caption}" if cell.caption else ""
            painter.drawText(caption, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                             painter.fontMetrics().elidedText(label, Qt.TextElideMode.ElideRight, caption.width()))
        if self.message:
            painter.setPen(text)
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.message)
        painter.end()

    # --- interaction ------------------------------------------------------------------------------------------------
    def _choosable(self, index: int) -> bool:
        return 0 <= index < CELLS and index != self.parent_cell and bool(self.cells[index].caption)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        index = self.cell_at(event.position().toPoint())
        if index != self._hover:
            self._hover = index
            self.setToolTip(self.cells[index].tooltip if index >= 0 else "")
            self.update()

    def leaveEvent(self, event) -> None:
        self._hover = -1
        self.update()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        index = self.cell_at(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and self._choosable(index):
            self.chosen.emit(index)

    def contextMenuEvent(self, event) -> None:
        index = self.cell_at(event.pos())
        if 0 <= index < CELLS and self.cells[index].caption:
            self.menu_requested.emit(index, event.globalPos())

    def keyPressEvent(self, event: QKeyEvent) -> None:
        key = event.key()
        if Qt.Key.Key_1 <= key <= Qt.Key.Key_9 and self._choosable(key - Qt.Key.Key_1):
            self.chosen.emit(key - Qt.Key.Key_1)
        elif key == Qt.Key.Key_Space:
            self.regenerate_requested.emit()
        else:
            super().keyPressEvent(event)


__all__ = ["FlameGrid", "Cell", "CENTRE", "CELLS"]
