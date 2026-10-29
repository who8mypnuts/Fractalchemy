"""The completion popup shared by the code editors: a candidate list that never takes the focus, with a documentation box.

Candidates are `scripting.completion.Item`s whatever the language (the Script Editor's Python completer and the
Formula Editor's dialect completer both produce them), so one widget serves both.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, QRect, QSize, Qt
from PySide6.QtGui import QColor, QPainter, QPixmap
from PySide6.QtWidgets import QFrame, QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget

from ..scripting import completion as C

POPUP_ROWS = 9
POPUP_MIN_WIDTH = 300
DOC_WIDTH = 360
KIND_BADGES = {"function": ("f", "#3b5f9e"), "method": ("f", "#3b5f9e"), "property": ("p", "#9a6a1d"), "object": ("o", "#2f7a42"),
               "variable": ("v", "#9a6a1d"), "keyword": ("k", "#6a4a7a"), "constant": ("c", "#7a3a3a"), "option": ("\"", "#2a7a7a"),
               "argument": ("=", "#5a5a9a"), "module": ("m", "#2f7a42"), "class": ("C", "#2f7a42")}


def badge_pixmap(kind: str, size: int = 16) -> QPixmap:
    letter, color = KIND_BADGES.get(kind, ("?", "#666666"))
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color))
    painter.setPen(Qt.PenStyle.NoPen)
    painter.drawRoundedRect(1, 1, size - 2, size - 2, 3, 3)
    painter.setPen(QColor("#ffffff"))
    font = painter.font()
    font.setBold(True)
    font.setPixelSize(size - 5)
    painter.setFont(font)
    painter.drawText(QRect(0, 0, size, size), Qt.AlignmentFlag.AlignCenter, letter)
    painter.end()
    return pixmap


def item_doc_html(item: C.Item) -> str:
    """The inline documentation shown beside the completion list."""
    from html import escape
    sig = item.sig or (f"{item.name}()" if item.kind in ("function", "method") else item.name + (f" : {item.type}" if item.type else ""))
    html = f"<div style='font-family: monospace; color: #0d47a1; font-weight: bold'>{escape(sig)}</div>"
    if item.desc:
        html += f"<div style='margin-top: 3px'>{escape(item.desc)}</div>"
    if item.detail:
        html += f"<div style='color: #777; margin-top: 3px'>parameters: {escape(item.detail)}</div>"
    if item.entry is not None and item.entry.example:
        html += f"<pre style='background: #f4f4f4; margin-top: 4px; padding: 3px'>{escape(item.entry.example)}</pre>"
    return html


class CompletionPopup(QFrame):
    """The list of candidates (a tool-tip style window that never takes the focus) plus the documentation box."""

    def __init__(self, editor: QWidget):
        super().__init__(editor, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._editor = editor
        self.list = QTreeWidget(self)
        self.list.setColumnCount(2)
        self.list.setHeaderHidden(True)
        self.list.setRootIsDecorated(False)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.list.setUniformRowHeights(True)
        self.list.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.list.setIconSize(QSize(16, 16))
        self.list.itemClicked.connect(lambda *_: editor.accept_completion())
        self.list.currentItemChanged.connect(lambda *_: self._show_doc())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(1, 1, 1, 1)
        layout.addWidget(self.list)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.doc = QLabel(editor, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.doc.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self.doc.setWordWrap(True)
        self.doc.setTextFormat(Qt.TextFormat.RichText)
        self.doc.setFrameShape(QFrame.Shape.StyledPanel)
        self.doc.setMargin(6)
        self.doc.setFixedWidth(DOC_WIDTH)
        self.doc.setStyleSheet("QLabel { background: #fffdf5; }")
        self.items: list[C.Item] = []

    def show_items(self, items: list[C.Item], at: QPoint) -> None:
        self.items = items
        self.list.clear()
        for item in items:
            row = QTreeWidgetItem([item.name, item.type or ""])
            row.setIcon(0, badge_pixmap(item.kind))
            row.setForeground(1, QColor("#777777"))
            font = row.font(0)
            font.setFamily(self._editor.font().family())
            row.setFont(0, font)
            self.list.addTopLevelItem(row)
        self.list.resizeColumnToContents(0)
        self.list.setCurrentItem(self.list.topLevelItem(0))
        rows = min(POPUP_ROWS, len(items))
        row_height = self.list.sizeHintForRow(0) if items else 20
        width = max(POPUP_MIN_WIDTH, self.list.columnWidth(0) + 120)
        self.resize(width, rows * row_height + 8)
        self.move(at)
        self.show()
        self._show_doc()

    def current(self) -> C.Item | None:
        index = self.list.indexOfTopLevelItem(self.list.currentItem())
        return self.items[index] if 0 <= index < len(self.items) else None

    def move_selection(self, delta: int) -> None:
        count = self.list.topLevelItemCount()
        if not count:
            return
        index = max(0, min(count - 1, self.list.indexOfTopLevelItem(self.list.currentItem()) + delta))
        self.list.setCurrentItem(self.list.topLevelItem(index))
        self.list.scrollToItem(self.list.topLevelItem(index))

    def _show_doc(self) -> None:
        item = self.current()
        if item is None or not self.isVisible():
            self.doc.hide()
            return
        self.doc.setText(item_doc_html(item))
        self.doc.adjustSize()
        x = self.x() + self.width() + 2
        screen = self.screen().availableGeometry() if self.screen() else QRect(0, 0, 100000, 100000)
        if x + DOC_WIDTH > screen.right():
            x = self.x() - DOC_WIDTH - 2
        self.doc.move(x, self.y())
        self.doc.show()

    def hideEvent(self, event) -> None:
        self.doc.hide()
        super().hideEvent(event)


__all__ = ["CompletionPopup", "badge_pixmap", "item_doc_html", "KIND_BADGES", "POPUP_ROWS", "POPUP_MIN_WIDTH", "DOC_WIDTH"]
