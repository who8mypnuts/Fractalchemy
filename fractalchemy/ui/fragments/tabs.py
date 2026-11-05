"""The source tabs: one `GlslCodeEditor` and one `FragDocument` per open fragment.

FragM keeps a `TabInfo` per tab (file name, editor, unsaved flags) and the parameter state travels with the tab; so
does this. The manager owns the `QTabBar` + `QStackedWidget`, creates tabs for texts / files, mirrors editor text
into the document, shows the unsaved mark in the tab title, asks before closing an unsaved tab, and tells the window
which document is current.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QEvent, QObject, Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QGuiApplication
from PySide6.QtWidgets import QMenu, QMessageBox, QStackedWidget, QTabBar, QVBoxLayout, QWidget

from ...fragments.document_format import FragmentFormatError, FragmentMetadata, read_fragment
from ...fragments.library_format import is_bundled_path
from .code_editor import GlslCodeEditor
from .document import FragDocument


class Tab:
    """One open fragment: its editor and document."""

    def __init__(self, document: FragDocument, editor: GlslCodeEditor):
        self.document = document
        self.editor = editor
        self.read_only = False


class TabManager(QObject):
    """Owns the tab bar and the stack of editors (see the module docstring).

    Signals:
        current_changed(object): The current `FragDocument` (None when no tab is open).
        document_opened(object): A new tab's document (for connecting its signals).
        document_closed(object): A closed tab's document.
    """
    current_changed = Signal(object)
    document_opened = Signal(object)
    document_closed = Signal(object)

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.font_size = 0                      # the editors' font size in points (0 = system)
        self.theme = "Default"                  # the editors' colour theme
        self.bar = QTabBar(parent)
        self.bar.setTabsClosable(True)
        self.bar.setMovable(True)
        self.bar.setExpanding(False)
        self.bar.setDocumentMode(True)
        self.stack = QStackedWidget(parent)
        self.widget = QWidget(parent)
        layout = QVBoxLayout(self.widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.bar)
        layout.addWidget(self.stack, 1)
        self._tabs: list[Tab] = []
        self.bar.currentChanged.connect(self._on_current)
        self.bar.tabCloseRequested.connect(self.close_tab)
        self.bar.tabMoved.connect(self._on_moved)
        self.bar.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.bar.customContextMenuRequested.connect(self._tab_menu)
        self.bar.installEventFilter(self)

    def eventFilter(self, obj, event) -> bool:  # noqa: N802 - Qt override
        """Middle-click closes a tab."""
        if obj is self.bar and event.type() == QEvent.Type.MouseButtonRelease and event.button() == Qt.MouseButton.MiddleButton:
            index = self.bar.tabAt(event.position().toPoint())
            if index >= 0:
                self.close_tab(index)
                return True
        return super().eventFilter(obj, event)

    def _tab_menu(self, pos) -> None:
        """Close / close others / close all, copy the path, show the file in its folder."""
        index = self.bar.tabAt(pos)
        if index < 0:
            return
        tab = self._tabs[index]
        menu = QMenu(self.widget)
        close = menu.addAction("Close")
        others = menu.addAction("Close others")
        every = menu.addAction("Close all")
        menu.addSeparator()
        copy_path = menu.addAction("Copy path")
        reveal = menu.addAction("Show in folder")
        for action in (copy_path, reveal):
            action.setEnabled(tab.document.path is not None)
        choice = menu.exec(self.bar.mapToGlobal(pos))
        if choice is close:
            self.close_tab(index)
        elif choice is others:
            self.close_others(index)
        elif choice is every:
            self.close_all()
        elif choice is copy_path:
            QGuiApplication.clipboard().setText(str(tab.document.path))
        elif choice is reveal:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(tab.document.path.parent)))

    def close_others(self, keep: int) -> None:
        """Close every tab but `keep` (stops at the first refused close)."""
        for index in range(len(self._tabs) - 1, -1, -1):
            if index != keep and not self.close_tab(index):
                return

    def close_all(self) -> None:
        for index in range(len(self._tabs) - 1, -1, -1):
            if not self.close_tab(index):
                return

    # --- queries --------------------------------------------------------------------------------------------------------
    @property
    def tabs(self) -> list[Tab]:
        return list(self._tabs)

    @property
    def current(self) -> Tab | None:
        index = self.bar.currentIndex()
        return self._tabs[index] if 0 <= index < len(self._tabs) else None

    @property
    def document(self) -> FragDocument | None:
        tab = self.current
        return tab.document if tab else None

    @property
    def editor(self) -> GlslCodeEditor | None:
        tab = self.current
        return tab.editor if tab else None

    def tab_for(self, document: FragDocument) -> Tab | None:
        return next((t for t in self._tabs if t.document is document), None)

    def tab_for_path(self, path: Path) -> Tab | None:
        return next((t for t in self._tabs if t.document.path is not None and t.document.path.resolve() == Path(path).resolve()), None)

    # --- opening ---------------------------------------------------------------------------------------------------------
    def open_text(self, text: str, path: Path | None = None, read_only: bool = False, metadata: FragmentMetadata | None = None) -> FragDocument:
        """A new tab with `text` (from `path` when given); becomes current."""
        document = FragDocument(text, path, self, metadata)
        editor = GlslCodeEditor(self.stack)
        editor.set_font_size(self.font_size)
        if self.theme != "Default":
            editor.set_theme(self.theme)
        editor.set_text(text)
        editor.setReadOnly(read_only)
        tab = Tab(document, editor)
        tab.read_only = read_only
        self._tabs.append(tab)
        self.stack.addWidget(editor)
        index = self.bar.addTab(self._title(tab))
        editor.textChanged.connect(lambda d=document, e=editor: d.set_text(e.toPlainText()))
        document.modified_changed.connect(lambda _m, t=tab: self._refresh_title(t))
        document.path_changed.connect(lambda _p, t=tab: self._refresh_title(t))
        document.text_changed.connect(lambda d=document, e=editor: self._mirror_to_editor(d, e))
        self.document_opened.emit(document)
        self.bar.setCurrentIndex(index)
        if self.bar.count() == 1:
            self._on_current(index)
        return document

    def open_file(self, path: Path, read_only: bool = False) -> FragDocument:
        """Open (or switch to) the tab showing `path`."""
        existing = self.tab_for_path(path)
        if existing is not None:
            self.bar.setCurrentIndex(self._tabs.index(existing))
            return existing.document
        try:
            text, metadata = read_fragment(Path(path))
        except FragmentFormatError:
            text, metadata = Path(path).read_text(encoding="utf-8", errors="replace"), None     # a broken block: keep the text
        return self.open_text(text, Path(path), read_only, metadata)

    def _mirror_to_editor(self, document: FragDocument, editor: GlslCodeEditor) -> None:
        """The document's text changed programmatically (a preset inserted): the editor follows."""
        if editor.toPlainText() != document.text:
            position = editor.position
            editor.set_text(document.text)
            cursor = editor.textCursor()
            cursor.setPosition(min(position, len(document.text)))
            editor.setTextCursor(cursor)

    # --- titles ----------------------------------------------------------------------------------------------------------
    def _title(self, tab: Tab) -> str:
        name = tab.document.path.name if tab.document.path else "Unnamed"
        kind = " (read-only)" if tab.read_only else " (example)" if tab.document.path and is_bundled_path(tab.document.path) else ""
        return name + (" *" if tab.document.modified else "") + kind

    def _refresh_title(self, tab: Tab) -> None:
        if tab in self._tabs:
            index = self._tabs.index(tab)
            self.bar.setTabText(index, self._title(tab))
            self.bar.setTabToolTip(index, str(tab.document.path) if tab.document.path else "Not saved yet")

    # --- switching and closing ----------------------------------------------------------------------------------------------
    def _on_current(self, index: int) -> None:
        if 0 <= index < len(self._tabs):
            self.stack.setCurrentWidget(self._tabs[index].editor)
            self.current_changed.emit(self._tabs[index].document)
        else:
            self.current_changed.emit(None)

    def _on_moved(self, from_index: int, to_index: int) -> None:
        tab = self._tabs.pop(from_index)
        self._tabs.insert(to_index, tab)

    def set_current(self, document: FragDocument) -> None:
        tab = self.tab_for(document)
        if tab is not None:
            self.bar.setCurrentIndex(self._tabs.index(tab))

    def close_tab(self, index: int, ask: bool = True) -> bool:
        """Close tab `index`; asks about unsaved changes when `ask`. False when the user cancelled."""
        if not 0 <= index < len(self._tabs):
            return True
        tab = self._tabs[index]
        if ask and tab.document.modified and not tab.read_only:
            answer = QMessageBox.question(self.widget, "Fragments", f"'{self._title(tab).rstrip(' *')}' has unsaved changes. Close it anyway?",
                                          QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
            if answer != QMessageBox.StandardButton.Discard:
                return False
        self._tabs.pop(index)
        self.bar.removeTab(index)
        self.stack.removeWidget(tab.editor)
        tab.editor.deleteLater()
        self.document_closed.emit(tab.document)
        if not self._tabs:
            self.current_changed.emit(None)
        return True

    def close_current(self) -> bool:
        return self.close_tab(self.bar.currentIndex())

    def unsaved_documents(self) -> list[FragDocument]:
        return [t.document for t in self._tabs if t.document.modified and not t.read_only]


__all__ = ["TabManager", "Tab"]
