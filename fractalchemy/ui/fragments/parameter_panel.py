"""The Parameters dock — FragM's `VariableEditor`: a preset chooser and one tab of widgets per `#group`.

Widgets are created from the document's parameters after every build; one whose `unique_name` (group, name and
range) is unchanged is kept, so values and lock states survive an edit-and-build cycle. A parameter the compiler
optimised away is hidden (unless locked — FragM's rule), and a tab that ends up empty hides too. The preset combo
applies a preset when chosen (and *Apply* re-applies it). The group tabs sit at the top when the dock is wide and
on the right when it is tall, as FragM's do. The panel routes every edit to the document and refreshes from its
signals; it never touches the renderer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (QComboBox, QFileDialog, QHBoxLayout, QLabel, QMenu, QPushButton, QScrollArea, QTabWidget, QVBoxLayout,
                               QWidget)

from ...fragments.files import IMAGE_SUFFIXES, FileManager
from ...fragments.parameters import LockType
from ...fragments.state import ParameterState
from ...widgets.silent import blocked
from .document import FragDocument
from .parameter_widgets import SamplerWidget, VariableWidget, make_widget

DEFAULT_GROUP = "Default"


class ParameterPanel(QWidget):
    """The parameter editor for one document (see the module docstring).

    Signals:
        select_source_requested(str): *Select source* on a slider: the editor should show the parameter's line.
        bounds_edit_requested(str, int, int, float): A slider bound was typed (name, component, 1 lower / 2 upper, value).
        group_preset_requested(str): *Group → preset* on a tab: the window asks for a name and inserts the block.
        status(str): A message for the status bar.
    """
    select_source_requested = Signal(str)
    bounds_edit_requested = Signal(str, int, int, float)
    group_preset_requested = Signal(str)
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.document: FragDocument | None = None
        self.hide_unused = True
        self.last_edited_slider = ""            # `Power1`, `JuliaC2`: what F7 edits by default
        self.widgets: dict[str, VariableWidget] = {}
        self._tabs: dict[str, QWidget] = {}
        self._layouts: dict[str, QVBoxLayout] = {}
        self.preset_combo = QComboBox(self)
        self.preset_combo.setToolTip("The fragment's presets (#preset blocks); choosing one applies it")
        self.apply_button = QPushButton("Apply", self)
        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.empty = QLabel("No parameters — build a fragment with annotated uniforms", self)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        top = QHBoxLayout()
        top.addWidget(QLabel("Preset:", self))
        top.addWidget(self.preset_combo, 1)
        top.addWidget(self.apply_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addLayout(top)
        layout.addWidget(self.tabs, 1)
        layout.addWidget(self.empty, 1)
        self.tabs.hide()
        self.preset_combo.currentTextChanged.connect(self._on_preset_chosen)
        self.apply_button.clicked.connect(self.apply_current_preset)
        self.tabs.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._tab_menu)

    # --- the document -------------------------------------------------------------------------------------------------
    def set_document(self, document: FragDocument | None) -> None:
        """Show another document's parameters."""
        if self.document is not None:
            for signal, slot in self._connections(self.document):
                signal.disconnect(slot)
        self.document = document
        if document is not None:
            for signal, slot in self._connections(document):
                signal.connect(slot)
        self.rebuild()

    def _connections(self, document: FragDocument) -> list[tuple]:
        return [(document.built, self._on_built), (document.parameters_changed, self._on_parameters_changed),
                (document.parameters_replaced, self.refresh_values), (document.facts_changed, self._on_facts)]

    def _on_built(self, _source) -> None:
        self.rebuild()

    # --- building the widgets ------------------------------------------------------------------------------------------
    def rebuild(self) -> None:
        """Recreate the tabs from the document's parameters, keeping widgets whose identity did not change."""
        document = self.document
        old = self.widgets
        self.widgets = {}
        params = document.state.params if document is not None and document.source is not None else {}
        current_tab = self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.count() else ""
        self._clear_tabs()
        files = FileManager(original=document.path).image_files() if document is not None else []
        for name, param in params.items():
            widget = old.pop(name, None)
            if widget is None or widget.param.unique_name != param.unique_name:
                widget = make_widget(param, files)
                self._connect_widget(widget)
            widget.param = param
            self.widgets[name] = widget
            self._layout_for(param.group or DEFAULT_GROUP).addWidget(widget)
        for widget in old.values():
            widget.setParent(None)
            widget.deleteLater()
        for layout in self._layouts.values():
            layout.addStretch(1)
        self.refresh_values()
        self._refresh_presets()
        self.tabs.setVisible(bool(self.widgets))
        self.empty.setVisible(not self.widgets)
        self._select_tab(current_tab)
        self._apply_unused()

    def _clear_tabs(self) -> None:
        while self.tabs.count():
            self.tabs.removeTab(0)
        for tab in self._tabs.values():
            tab.deleteLater()
        self._tabs.clear()
        self._layouts.clear()

    def _layout_for(self, group: str) -> QVBoxLayout:
        if group not in self._tabs:
            page = QWidget()
            layout = QVBoxLayout(page)
            layout.setContentsMargins(4, 4, 4, 4)
            layout.setSpacing(2)
            scroll = QScrollArea(self.tabs)
            scroll.setWidgetResizable(True)
            scroll.setWidget(page)
            scroll.setFrameShape(QScrollArea.Shape.NoFrame)
            self.tabs.addTab(scroll, group)
            self._tabs[group] = scroll
            self._layouts[group] = layout
        return self._layouts[group]

    def _select_tab(self, name: str) -> None:
        for i in range(self.tabs.count()):
            if self.tabs.tabText(i) == name:
                self.tabs.setCurrentIndex(i)
                return

    def _connect_widget(self, widget: VariableWidget) -> None:
        widget.value_edited.connect(self._on_value_edited)
        widget.lock_toggled.connect(self._on_lock_toggled)
        widget.select_source.connect(self.select_source_requested)
        widget.bounds_edited.connect(self.bounds_edit_requested)
        if isinstance(widget, SamplerWidget):
            widget.browse_requested.connect(self._browse_texture)

    # --- showing values ----------------------------------------------------------------------------------------------------
    def refresh_values(self) -> None:
        """Every widget shows the document's current values, locks and slider types."""
        if self.document is None:
            return
        state: ParameterState = self.document.state
        for name, widget in self.widgets.items():
            if name in state:
                widget.set_value(state.values[name])
                widget.set_lock(state.locks[name])
                widget.set_slider_type(state.sliders[name])
        self._apply_unused()

    def _on_parameters_changed(self, names: list, _recompile: bool, _buffer_only: bool) -> None:
        if self.document is None:
            return
        for name in names:
            widget = self.widgets.get(name)
            if widget is not None and name in self.document.state:
                widget.set_value(self.document.state.values[name])
                widget.set_lock(self.document.state.locks[name])

    def _on_facts(self, _facts) -> None:
        self._apply_unused()

    def _apply_unused(self) -> None:
        """FragM's `hideUnusedVariableWidgets`: hide what the compiler optimised away, unless locked; hide empty tabs."""
        unused = set(self.document.facts.unused) if self.document is not None and self.document.facts is not None else set()
        shown_by_group: dict[str, int] = {}
        for name, widget in self.widgets.items():
            hidden = self.hide_unused and name in unused and not widget.param.lock.locked and not (
                self.document is not None and self.document.state.is_locked(name))
            widget.setVisible(not hidden)
            group = widget.param.group or DEFAULT_GROUP
            shown_by_group[group] = shown_by_group.get(group, 0) + (0 if hidden else 1)
        for i in range(self.tabs.count()):
            self.tabs.setTabVisible(i, shown_by_group.get(self.tabs.tabText(i), 0) > 0)

    def set_hide_unused(self, hide: bool) -> None:
        self.hide_unused = hide
        self._apply_unused()

    # --- edits ----------------------------------------------------------------------------------------------------------------
    def _on_value_edited(self, name: str, value, merge_key) -> None:
        widget = self.widgets.get(name)
        component = getattr(widget, "last_component", 1) if widget is not None else 1
        self.last_edited_slider = f"{name}{component}"
        if self.document is not None:
            self.document.set_value(name, value, merge_key)
            if merge_key is None:
                self.document.end_merge()

    def _on_lock_toggled(self, name: str, lock: LockType) -> None:
        if self.document is not None:
            self.document.set_lock(name, lock)

    def _browse_texture(self, name: str) -> None:
        if self.document is None:
            return
        widget = self.widgets.get(name)
        start = str(self.document.path.parent) if self.document and self.document.path else ""
        patterns = " ".join(f"*{s}" for s in IMAGE_SUFFIXES)
        chosen, _filter = QFileDialog.getOpenFileName(self, f"Texture for {name}", start, f"Images ({patterns});;All files (*)")
        if chosen and widget is not None:
            widget.set_value(chosen)
            self.document.set_value(name, widget.value())

    # --- presets -----------------------------------------------------------------------------------------------------------------
    def _refresh_presets(self) -> None:
        names = self.document.source.presets.keys() if self.document is not None and self.document.source is not None else []
        with blocked(self.preset_combo):
            self.preset_combo.clear()
            self.preset_combo.addItems(list(names))
            if self.document is not None and self.document.current_preset in names:
                self.preset_combo.setCurrentText(self.document.current_preset)
        self.preset_combo.setEnabled(self.preset_combo.count() > 0)
        self.apply_button.setEnabled(self.preset_combo.count() > 0)

    def _on_preset_chosen(self, name: str) -> None:
        if name:
            self.apply_preset(name)

    def apply_current_preset(self) -> None:
        self.apply_preset(self.preset_combo.currentText())

    def apply_preset(self, name: str) -> None:
        """Apply a preset by name (FragM's `setPreset`); a preset with locks marks the document for a rebuild."""
        if self.document is not None and self.document.apply_preset(name):
            with blocked(self.preset_combo):
                self.preset_combo.setCurrentText(name)
            self.status.emit(f"Applied preset '{name}'" + (" — build needed (locked values)" if self.document.needs_build else ""))

    def current_group(self) -> str:
        """The visible tab's group name."""
        return self.tabs.tabText(self.tabs.currentIndex()) if self.tabs.count() else DEFAULT_GROUP

    def group_names(self, group: str) -> list[str]:
        return [n for n, w in self.widgets.items() if (w.param.group or DEFAULT_GROUP) == group]

    # --- group actions (FragM's tab context menu) -----------------------------------------------------------------------------
    def _tab_menu(self, pos) -> None:
        if self.document is None or not self.tabs.count():
            return
        group = self.current_group()
        menu = QMenu(self)
        actions = {menu.addAction(f"Reset group '{group}'"): "reset", menu.addAction("Lock group"): "lock", menu.addAction("Unlock group"): "unlock",
                   menu.addAction("Copy group settings"): "copy", menu.addAction("Group → preset…"): "preset"}
        menu.addSeparator()
        hide = menu.addAction("Hide unused parameters")
        hide.setCheckable(True)
        hide.setChecked(self.hide_unused)
        choice = menu.exec(self.tabs.mapToGlobal(pos))
        if choice is hide:
            self.set_hide_unused(hide.isChecked())
        elif choice in actions:
            self.group_action(actions[choice], group)

    def group_action(self, kind: str, group: str | None = None) -> None:
        """`reset`, `lock`, `unlock`, `copy` or `preset` on a group (the current tab's by default)."""
        if self.document is None:
            return
        group = group or self.current_group()
        names = self.group_names(group)
        if kind == "reset":
            self.document.reset(names)
        elif kind in ("lock", "unlock"):
            self.document.set_group_lock(group, LockType.LOCKED if kind == "lock" else LockType.NOT_LOCKED)
        elif kind == "copy":
            from PySide6.QtGui import QGuiApplication
            QGuiApplication.clipboard().setText(self.document.state.to_text(names=names))
            self.status.emit(f"Copied the settings of group '{group}'")
        elif kind == "preset":
            self.group_preset_requested.emit(group)

    def group_settings_text(self, group: str | None = None) -> str:
        """The settings text of one group (for *Group → preset*)."""
        if self.document is None:
            return ""
        return self.document.state.to_text(names=self.group_names(group or self.current_group()))

    def resizeEvent(self, event) -> None:  # noqa: D102 - Qt override: FragM flips the tabs East when the dock is tall
        super().resizeEvent(event)
        self.tabs.setTabPosition(QTabWidget.TabPosition.North if self.width() > self.height() else QTabWidget.TabPosition.East)


__all__ = ["ParameterPanel", "DEFAULT_GROUP"]
