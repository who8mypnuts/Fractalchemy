"""A name / value table with Apophysis's editing gestures, for the Transform Editor's lists.

* Type a number in the value column (Enter / focus out commits it).
* Press on a *name* and drag left / right to change its value continuously: 0.001 per pixel,
  **Shift** 0.01, **Ctrl** 0.0001, **Alt** 0.00001 (Apophysis's "drag the variation name").
* Double-click a name: `name_double_clicked` (the owner toggles 0 ↔ 1 or resets a default).

Rows are `ValueRow`s; the table only reports edits (`value_edited(name, value)`), it never changes
a model itself. `set_rows` keeps the scroll position and the current row when the names are the same.
"""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QFont, QMouseEvent
from PySide6.QtWidgets import QAbstractItemView, QHeaderView, QTableWidget, QTableWidgetItem, QWidget

DRAG_STEPS = {"plain": 0.001, "shift": 0.01, "ctrl": 0.0001, "alt": 0.00001}
DRAG_DEAD_ZONE_PX = 2


@dataclass
class ValueRow:
    """One row: `name` (the key reported back), its `value`, an optional third-column `info` and a tooltip."""
    name: str
    value: float
    info: str = ""
    tooltip: str = ""
    bold: bool = False
    decimals: int = 6
    integer: bool = False
    color: QColor | None = None


def format_value(value: float, decimals: int = 6, integer: bool = False) -> str:
    if integer:
        return str(int(round(value)))
    text = f"{value:.{decimals}f}".rstrip("0").rstrip(".")
    return text if text not in ("", "-", "-0") else "0"


class ValueTable(QTableWidget):
    """Name / value (/ info) table; see the module docstring.

    Signals:
        value_edited(str, float): The user typed or dragged a new value for `name` (live while dragging).
        drag_finished(str): A value drag ended (the owner may close an undo step).
        name_double_clicked(str): A name cell was double-clicked.
        current_changed(str): The current row changed (empty string for none).
    """
    value_edited = Signal(str, float)
    drag_finished = Signal(str)
    name_double_clicked = Signal(str)
    current_changed = Signal(str)

    def __init__(self, parent: QWidget | None = None, headers: tuple[str, ...] = ("Name", "Value")):
        super().__init__(0, len(headers), parent)
        self._rows: dict[str, ValueRow] = {}
        self._order: list[str] = []
        self._drag: tuple[str, float, float, bool] | None = None   # (name, start x, start value, moved)
        self._updating = False
        self.setHorizontalHeaderLabels(list(headers))
        self.verticalHeader().setVisible(False)
        header = self.horizontalHeader()
        header.setStretchLastSection(False)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Fixed)
        self.setColumnWidth(1, 78)
        if len(headers) > 2:
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            self.setColumnWidth(2, 84)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked
                             | QAbstractItemView.EditTrigger.EditKeyPressed | QAbstractItemView.EditTrigger.AnyKeyPressed)
        self.setAlternatingRowColors(True)
        self.setMouseTracking(True)
        self.itemChanged.connect(self._on_item_changed)
        self.itemDoubleClicked.connect(self._on_double_clicked)
        self.currentCellChanged.connect(lambda row, *_: self.current_changed.emit(self.name_at(row) or ""))

    # --- rows -----------------------------------------------------------------------------------------------
    def set_rows(self, rows: list[ValueRow]) -> None:
        """Show `rows`; when the names are unchanged only the texts are refreshed (no flicker, scroll kept)."""
        names = [r.name for r in rows]
        rebuilt = names != self._order
        self._updating = True
        try:
            if rebuilt:
                current = self.current_name()
                self.setRowCount(0)
                self.setRowCount(len(rows))
                for i, row in enumerate(rows):
                    name_item = QTableWidgetItem(row.name)
                    name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    value_item = QTableWidgetItem()
                    value_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                    self.setItem(i, 0, name_item)
                    self.setItem(i, 1, value_item)
                    if self.columnCount() > 2:
                        info_item = QTableWidgetItem()
                        info_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                        self.setItem(i, 2, info_item)
                self._order = names
                if current in names:
                    self.setCurrentCell(names.index(current), 0)
            previous = {} if rebuilt else self._rows
            self._rows = {r.name: r for r in rows}
            for i, row in enumerate(rows):
                self._refresh_row(i, row, previous.get(row.name))
        finally:
            self._updating = False

    def _refresh_row(self, i: int, row: ValueRow, previous: ValueRow | None) -> None:
        """Update the cells of row `i`; only what differs from `previous` is touched (cheap on every drag step)."""
        name_item, value_item = self.item(i, 0), self.item(i, 1)
        if previous is None or previous.bold != row.bold:
            font = QFont(name_item.font())
            font.setBold(row.bold)
            name_item.setFont(font)
        if previous is None or previous.tooltip != row.tooltip:
            name_item.setToolTip(row.tooltip or row.name)
            value_item.setToolTip(row.tooltip or row.name)
        if row.color is not None and (previous is None or previous.color != row.color):
            name_item.setForeground(row.color)
        if previous is None or previous.value != row.value or previous.decimals != row.decimals:
            value_item.setText(format_value(row.value, row.decimals, row.integer))
        if self.columnCount() > 2 and (previous is None or previous.info != row.info):
            self.item(i, 2).setText(row.info)
            self.item(i, 2).setToolTip(row.tooltip or row.info)

    def update_value(self, name: str, value: float) -> None:
        """Refresh one value (from the model) without emitting."""
        row = self._rows.get(name)
        if row is None:
            return
        row.value = value
        if name in self._order:
            self._updating = True
            try:
                self.item(self._order.index(name), 1).setText(format_value(value, row.decimals, row.integer))
            finally:
                self._updating = False

    def value_of(self, name: str) -> float | None:
        row = self._rows.get(name)
        return None if row is None else row.value

    def names(self) -> list[str]:
        return list(self._order)

    def name_at(self, row: int) -> str | None:
        return self._order[row] if 0 <= row < len(self._order) else None

    def current_name(self) -> str | None:
        return self.name_at(self.currentRow())

    def select_name(self, name: str) -> None:
        if name in self._order:
            self.setCurrentCell(self._order.index(name), 0)

    def filter(self, needle: str, hide_if=None) -> int:
        """Hide rows whose name does not contain `needle` (or for which `hide_if(row)` is true); returns the visible count."""
        needle = needle.strip().lower()
        shown = 0
        for i, name in enumerate(self._order):
            row = self._rows[name]
            hidden = (needle and needle not in name.lower() and needle not in row.info.lower()) or (hide_if is not None and hide_if(row))
            self.setRowHidden(i, bool(hidden))
            shown += not hidden
        return shown

    # --- editing --------------------------------------------------------------------------------------------
    def _on_item_changed(self, item: QTableWidgetItem) -> None:
        if self._updating or item.column() != 1:
            return
        name = self.name_at(item.row())
        row = self._rows.get(name) if name else None
        if row is None:
            return
        try:
            value = float(item.text().replace(",", "."))
        except ValueError:
            self.update_value(name, row.value)
            return
        if row.integer:
            value = float(int(round(value)))
        if value != row.value:
            row.value = value
            self.value_edited.emit(name, value)
        self.update_value(name, value)

    def _on_double_clicked(self, item: QTableWidgetItem) -> None:
        if item.column() == 0:
            name = self.name_at(item.row())
            if name:
                self.name_double_clicked.emit(name)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        item = self.itemAt(event.position().toPoint())
        if event.button() == Qt.MouseButton.LeftButton and item is not None and item.column() == 0:
            name = self.name_at(item.row())
            if name is not None:
                self.setCurrentCell(item.row(), 0)
                self._drag = (name, event.position().x(), self._rows[name].value, False)
                self.setCursor(Qt.CursorShape.SizeHorCursor)
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._drag is None:
            item = self.itemAt(event.position().toPoint())
            self.setCursor(Qt.CursorShape.SizeHorCursor if item is not None and item.column() == 0 else Qt.CursorShape.ArrowCursor)
            super().mouseMoveEvent(event)
            return
        name, x0, start, moved = self._drag
        dx = event.position().x() - x0
        if not moved and abs(dx) < DRAG_DEAD_ZONE_PX:
            return
        mods = event.modifiers()
        if mods & Qt.KeyboardModifier.AltModifier:
            step = DRAG_STEPS["alt"]
        elif mods & Qt.KeyboardModifier.ControlModifier:
            step = DRAG_STEPS["ctrl"]
        elif mods & Qt.KeyboardModifier.ShiftModifier:
            step = DRAG_STEPS["shift"]
        else:
            step = DRAG_STEPS["plain"]
        row = self._rows[name]
        value = round(start + dx * step, 6)
        if row.integer:
            value = float(int(round(start + dx * step * 100)))   # a pixel is 0.1 for integers: 10 px per step
        self._drag = (name, x0, start, True)
        if value != row.value:
            row.value = value
            self.update_value(name, value)
            self.value_edited.emit(name, value)
        event.accept()

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if self._drag is not None and event.button() == Qt.MouseButton.LeftButton:
            name, _x0, _start, moved = self._drag
            self._drag = None
            self.setCursor(Qt.CursorShape.ArrowCursor)
            if moved:
                self.drag_finished.emit(name)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent) -> None:
        self._drag = None
        super().mouseDoubleClickEvent(event)


def blocked_table(table: ValueTable):
    """Context manager blocking the table's signals (for programmatic selection changes)."""
    return QSignalBlocker(table)


__all__ = ["ValueTable", "ValueRow", "format_value", "blocked_table"]
