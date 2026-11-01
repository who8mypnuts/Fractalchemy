"""How the Parameters dock arranges its `#group`s: stacked collapsible sections (the default) or FragM's tabs.

Both views offer the same small interface to the panel — a layout per group, the current group, per-group visibility,
extra pages such as *Grading* — so the panel builds its widgets once and the user can switch with a click.
Sections show every group at once on one scrolling page (the modern, nothing-hidden arrangement; a group's fold
state is remembered by name); tabs keep one group in view at a time and flip to the side when the dock is tall,
as FragM does. A right-click on a section header or a tab asks for the group menu.
"""

from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QScrollArea, QTabWidget, QToolButton, QVBoxLayout, QWidget

from ...widgets.collapsible_section import CollapsibleSection

MODES = ("sections", "tabs")


class _PageLayout(QVBoxLayout):
    """The layout holding one group's parameter rows."""

    def __init__(self, parent: QWidget):
        super().__init__(parent)
        self.setContentsMargins(4, 2, 4, 2)
        self.setSpacing(2)


class TabbedGroups(QWidget):
    """One tab per group (FragM's arrangement).

    Signals:
        menu_requested(str, QPoint): The group under a right-click, global position.
    """
    menu_requested = Signal(str, QPoint)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(lambda pos: self.menu_requested.emit(self.current_group(), self.tabs.mapToGlobal(pos)))
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tabs)
        self._layouts: dict[str, QVBoxLayout] = {}
        self._pages: dict[str, QWidget] = {}

    def clear(self) -> None:
        while self.tabs.count():
            self.tabs.removeTab(0)
        for page in self._pages.values():
            page.deleteLater()
        self._pages.clear()
        self._layouts.clear()

    def layout_for(self, group: str) -> QVBoxLayout:
        if group not in self._layouts:
            page = QWidget()
            layout = _PageLayout(page)
            scroll = QScrollArea(self.tabs)
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            self.tabs.addTab(scroll, group)
            self._pages[group] = scroll
            self._layouts[group] = layout
        return self._layouts[group]

    def add_page(self, title: str, widget: QWidget) -> None:
        """A page that is not a parameter group (the grading controls)."""
        self.tabs.addTab(widget, title)
        self._pages[title] = widget

    def groups(self) -> list[str]:
        return [self.tabs.tabText(i) for i in range(self.tabs.count())]

    def current_group(self) -> str:
        return self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.count() else ""

    def set_current(self, group: str) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == group:
                self.tabs.setCurrentIndex(i)
                return

    def set_group_visible(self, group: str, visible: bool) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == group:
                self.tabs.setTabVisible(i, visible)

    def finish(self) -> None:
        for layout in self._layouts.values():
            layout.addStretch(1)

    def resizeEvent(self, event) -> None:  # noqa: N802 - Qt override: FragM flips the tabs East when the dock is tall
        super().resizeEvent(event)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.width() > self.height() else QTabWidget.TabPosition.East)


class SectionGroups(QWidget):
    """Every group as a collapsible section on one scrolling page, with a jump combo and expand / collapse all.

    Signals:
        menu_requested(str, QPoint): The group whose header was right-clicked, global position.
    """
    menu_requested = Signal(str, QPoint)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.fold_state: dict[str, bool] = {}
        self._sections: dict[str, CollapsibleSection] = {}
        self._layouts: dict[str, QVBoxLayout] = {}
        self._current = ""
        bar = QHBoxLayout()
        bar.setContentsMargins(0, 0, 0, 0)
        self.jump = QComboBox(self)
        self.jump.setToolTip("Scroll to a group")
        self.jump.activated.connect(lambda i: self.set_current(self.jump.itemText(i)))
        self.expand_all = QToolButton(self)
        self.expand_all.setText("▾ all")
        self.expand_all.setAutoRaise(True)
        self.expand_all.setToolTip("Expand every group")
        self.expand_all.clicked.connect(lambda: self._fold_all(True))
        self.collapse_all = QToolButton(self)
        self.collapse_all.setText("▸ all")
        self.collapse_all.setAutoRaise(True)
        self.collapse_all.setToolTip("Collapse every group")
        self.collapse_all.clicked.connect(lambda: self._fold_all(False))
        bar.addWidget(self.jump, 1)
        bar.addWidget(self.expand_all)
        bar.addWidget(self.collapse_all)
        self.page = QWidget()
        self.page_layout = QVBoxLayout(self.page)
        self.page_layout.setContentsMargins(0, 0, 0, 0)
        self.page_layout.setSpacing(4)
        self.scroll = QScrollArea(self)
        self.scroll.setWidgetResizable(True)
        self.scroll.setWidget(self.page)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addLayout(bar)
        layout.addWidget(self.scroll, 1)

    def clear(self) -> None:
        for section in self._sections.values():
            self.page_layout.removeWidget(section)
            section.deleteLater()
        while self.page_layout.count():
            item = self.page_layout.takeAt(0)
            if item.widget() is not None:
                item.widget().deleteLater()
        self._sections.clear()
        self._layouts.clear()
        self.jump.clear()

    def layout_for(self, group: str) -> QVBoxLayout:
        if group not in self._layouts:
            content = QWidget()
            layout = _PageLayout(content)
            self._layouts[group] = layout
            self._add_section(group, content)
        return self._layouts[group]

    def add_page(self, title: str, widget: QWidget) -> None:
        self._add_section(title, widget)

    def _add_section(self, title: str, content: QWidget) -> None:
        section = CollapsibleSection(title, content, self.page, expanded=self.fold_state.get(title, True))
        section.header.setStyleSheet("QToolButton { text-align: left; padding: 3px; font-weight: bold; background: palette(alternate-base); border-radius: 3px; }")
        section.header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        section.header.customContextMenuRequested.connect(lambda pos, g=title: self.menu_requested.emit(g, section.header.mapToGlobal(pos)))
        section.header.clicked.connect(lambda _on, g=title: self._activate(g))
        section.toggled.connect(lambda expanded, g=title: self.fold_state.__setitem__(g, expanded))
        self._sections[title] = section
        self.page_layout.addWidget(section)
        self.jump.addItem(title)

    def finish(self) -> None:
        self.page_layout.addStretch(1)
        if self._sections and self._current not in self._sections:
            self._current = next(iter(self._sections))
        self.jump.setCurrentText(self._current)

    def _activate(self, group: str) -> None:
        self._current = group
        self.jump.setCurrentText(group)

    def groups(self) -> list[str]:
        return list(self._sections)

    def current_group(self) -> str:
        return self._current if self._current in self._sections else (next(iter(self._sections)) if self._sections else "")

    def set_current(self, group: str) -> None:
        section = self._sections.get(group)
        if section is None:
            return
        self._activate(group)
        section.set_expanded(True)
        self.scroll.verticalScrollBar().setValue(section.pos().y())

    def set_group_visible(self, group: str, visible: bool) -> None:
        section = self._sections.get(group)
        if section is not None:
            section.setVisible(visible)

    def _fold_all(self, expanded: bool) -> None:
        for section in self._sections.values():
            section.set_expanded(expanded)


def make_groups(mode: str, parent: QWidget | None = None):
    """A group view for `mode` (`sections` or `tabs`)."""
    return SectionGroups(parent) if mode != "tabs" else TabbedGroups(parent)


__all__ = ["TabbedGroups", "SectionGroups", "make_groups", "MODES"]
