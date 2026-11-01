"""The Parameters dock — FragM's `VariableEditor`: a preset chooser and the widgets of every `#group`.

Widgets are created from the document's parameters after every build; one whose `unique_name` (group, name and
range) is unchanged is kept, so values and lock states survive an edit-and-build cycle. A parameter the compiler
optimised away is hidden (unless locked — FragM's rule), and a group that ends up empty hides too. The preset combo
applies a preset when chosen (and *Apply* re-applies it). The groups are arranged by a `parameter_groups` view —
collapsible sections on one page (default) or FragM's tabs — chosen with the ⊞ button; extra pages such as the
grading controls join the same arrangement. Parameters pinned from their row menu gather in a *★ Favourites* group
at the top (the list travels in the `.fafrag`). The panel routes every edit to the document and refreshes from its
signals; it never touches the renderer.
"""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QFileDialog, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton, QToolButton, QVBoxLayout, QWidget

from ...fragments.files import IMAGE_SUFFIXES, FileManager
from ...fragments.parameters import LockType
from ...fragments.state import CAMERA_2D, CAMERA_3D, ParameterState
from ...widgets.silent import blocked
from .document import FragDocument
from .parameter_groups import MODES, make_groups
from .parameter_widgets import SamplerWidget, VariableWidget, make_widget

CAMERA_NAMES = set(CAMERA_3D) | set(CAMERA_2D)
DEFAULT_GROUP = "Default"
FAVOURITES_GROUP = "★ Favourites"
FAVOURITES_KEY = "favourites"


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
    mode_changed = Signal(str)
    status = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.document: FragDocument | None = None
        self.hide_unused = True
        self.last_edited_slider = ""            # `Power1`, `JuliaC2`: what F7 edits by default
        self.widgets: dict[str, VariableWidget] = {}
        self.filter = QLineEdit(self)
        self.filter.setPlaceholderText("Filter parameters…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(lambda _t: self._apply_unused())
        self.preset_combo = QComboBox(self)
        self.preset_combo.setToolTip("The fragment's presets (#preset blocks); choosing one applies it")
        self.apply_button = QPushButton("Apply", self)
        self.mode = "sections"
        self.extra_pages: list[tuple[str, QWidget]] = []
        self.groups = make_groups(self.mode, self)
        self.groups.menu_requested.connect(self._group_menu)
        self.mode_button = QToolButton(self)
        self.mode_button.setText("⊞")
        self.mode_button.setAutoRaise(True)
        self.mode_button.setToolTip("Arrange the groups as sections on one page or as tabs")
        self.mode_button.clicked.connect(lambda: self.set_mode("tabs" if self.mode == "sections" else "sections"))
        self.empty = QLabel("No parameters — build a fragment with annotated uniforms", self)
        self.empty.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty.setWordWrap(True)
        top = QHBoxLayout()
        top.addWidget(QLabel("Preset:", self))
        top.addWidget(self.preset_combo, 1)
        top.addWidget(self.apply_button)
        top.addWidget(self.mode_button)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(4, 4, 4, 4)
        self._layout.addLayout(top)
        self._layout.addWidget(self.filter)
        self._layout.addWidget(self.groups, 1)
        self._layout.addWidget(self.empty, 1)
        self.preset_combo.currentTextChanged.connect(self._on_preset_chosen)
        self.apply_button.clicked.connect(self.apply_current_preset)

    # --- arrangement --------------------------------------------------------------------------------------------------
    def set_mode(self, mode: str) -> None:
        """`sections` or `tabs` (the widgets are rebuilt into the new view)."""
        if mode not in MODES or mode == self.mode:
            return
        fold_state = getattr(self.groups, "fold_state", {})
        self.mode = mode
        for widget in self.widgets.values():
            widget.setParent(None)
        for _title, page in self.extra_pages:
            page.setParent(None)
        self.groups.clear()
        self._layout.removeWidget(self.groups)
        self.groups.deleteLater()
        self.groups = make_groups(mode, self)
        if hasattr(self.groups, "fold_state"):
            self.groups.fold_state = dict(fold_state)
        self.groups.menu_requested.connect(self._group_menu)
        self._layout.insertWidget(2, self.groups, 1)
        self.rebuild()
        self.mode_changed.emit(mode)

    def add_page(self, title: str, widget: QWidget) -> None:
        """A page that is not a group (the grading controls); shown after the groups in either arrangement."""
        self.extra_pages.append((title, widget))
        self.rebuild()

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
        current = self.groups.current_group()
        for widget in old.values():
            widget.setParent(None)
        for _title, page in self.extra_pages:
            page.setParent(None)
        self.groups.clear()
        files = FileManager(original=document.path).image_files() if document is not None else []
        favourites = self.favourites()
        if favourites:
            self.groups.layout_for(FAVOURITES_GROUP)           # first, so it sits on top
        for name, param in params.items():
            widget = old.pop(name, None)
            if widget is None or widget.param.unique_name != param.unique_name:
                widget = make_widget(param, files)
                self._connect_widget(widget)
            widget.param = param
            self.widgets[name] = widget
            self.groups.layout_for(self._group_of(widget)).addWidget(widget)
        for widget in old.values():
            widget.deleteLater()
        self.groups.finish()
        for title, page in self.extra_pages:
            self.groups.add_page(title, page)
        self.refresh_values()
        self._refresh_presets()
        self.groups.setVisible(bool(self.widgets) or bool(self.extra_pages))
        self.empty.setVisible(not self.widgets)
        if current:
            self.groups.set_current(current)
        self._apply_unused()

    def _connect_widget(self, widget: VariableWidget) -> None:
        widget.is_pinned = lambda name=widget.name: name in self.favourites()
        widget.value_edited.connect(self._on_value_edited)
        widget.row_action.connect(self.row_action)
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
        """FragM's `hideUnusedVariableWidgets`: hide what the compiler optimised away, unless locked; apply the filter box; hide empty tabs."""
        unused = set(self.document.facts.unused) if self.document is not None and self.document.facts is not None else set()
        needle = self.filter.text().strip().lower()
        by_name = any(needle in name.lower() for name in self.widgets) if needle else False      # names first, tooltips only as a fallback
        shown_by_group: dict[str, int] = {}
        for name, widget in self.widgets.items():
            hidden = self.hide_unused and name in unused and not widget.param.lock.locked and not (
                self.document is not None and self.document.state.is_locked(name))
            if needle and (needle not in name.lower() if by_name else needle not in (widget.param.tooltip or "").lower()):
                hidden = True
            widget.setVisible(not hidden)
            group = self._group_of(widget)
            shown_by_group[group] = shown_by_group.get(group, 0) + (0 if hidden else 1)
        extra = {title for title, _page in self.extra_pages}
        for group in self.groups.groups():
            self.groups.set_group_visible(group, group in extra and not needle or shown_by_group.get(group, 0) > 0)
        if needle and shown_by_group.get(self.current_group(), 0) == 0:       # jump to the first group with a match
            for group in self.groups.groups():
                if shown_by_group.get(group, 0) > 0:
                    self.groups.set_current(group)
                    break

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
        """The group in front / last touched (group actions default to it)."""
        return self.groups.current_group() or DEFAULT_GROUP

    def group_names(self, group: str) -> list[str]:
        return [n for n, w in self.widgets.items() if self._group_of(w) == group]

    # --- favourites ---------------------------------------------------------------------------------------------------------
    def favourites(self) -> list[str]:
        """The pinned parameter names (kept in the document's metadata)."""
        if self.document is None:
            return []
        names = self.document.metadata.tabs.get(FAVOURITES_KEY) or []
        return [str(n) for n in names] if isinstance(names, list) else []

    def set_favourite(self, name: str, pinned: bool) -> None:
        """Pin / unpin one parameter (its row moves into / out of the Favourites group)."""
        if self.document is None:
            return
        names = [n for n in self.favourites() if n != name]
        if pinned:
            names.append(name)
        self.document.set_tab_metadata(FAVOURITES_KEY, names)
        self.rebuild()
        self.status.emit(f"{'Pinned' if pinned else 'Unpinned'} {name}")

    def _group_of(self, widget: VariableWidget) -> str:
        if widget.name in self.favourites():
            return FAVOURITES_GROUP
        return widget.param.group or DEFAULT_GROUP

    # --- group actions (FragM's tab context menu) -----------------------------------------------------------------------------
    def _group_menu(self, group: str, pos) -> None:
        if self.document is None or group not in self.group_names_all():
            return
        menu = QMenu(self)
        actions = {menu.addAction(f"Reset group '{group}'"): "reset", menu.addAction("Randomize group"): "randomize",
                   menu.addAction("Lock group"): "lock", menu.addAction("Unlock group"): "unlock",
                   menu.addAction("Copy group settings"): "copy", menu.addAction("Group → preset…"): "preset"}
        menu.addSeparator()
        hide = menu.addAction("Hide unused parameters")
        hide.setCheckable(True)
        hide.setChecked(self.hide_unused)
        choice = menu.exec(pos)
        if choice is hide:
            self.set_hide_unused(hide.isChecked())
        elif choice in actions:
            self.group_action(actions[choice], group)

    # --- one parameter's row menu -----------------------------------------------------------------------------------------
    def row_action(self, name: str, action: str) -> None:
        """`reset`, `randomize`, `copy` or `paste` on one parameter (the row's context menu)."""
        from PySide6.QtGui import QGuiApplication
        document = self.document
        if document is None or name not in document.state:
            return
        if action == "reset":
            document.reset([name])
        elif action in ("pin", "unpin"):
            self.set_favourite(name, action == "pin")
        elif action == "randomize":
            self.randomize([name])
        elif action == "copy":
            QGuiApplication.clipboard().setText(document.state.to_text(names=[name]).strip().splitlines()[-1])
            self.status.emit(f"Copied {name}")
        elif action == "paste":
            text = QGuiApplication.clipboard().text().strip()
            line = text if "=" in text else f"{name} = {text}"
            if not line.split("=")[0].strip() == name:
                line = f"{name} = {line.split('=', 1)[1].strip()}"
            warnings = document.apply_settings(line, label=f"paste {name}")
            if warnings:
                self.status.emit(warnings[0])

    def randomize(self, names: list[str] | None = None, group: str | None = None) -> int:
        """Random values within the sliders' ranges for `names` (or the unlocked parameters of `group`, the camera excluded); one undo step."""
        import numpy as np
        document = self.document
        if document is None:
            return 0
        if names is None:
            group = group or self.current_group()
            names = [n for n in self.group_names(group) if n not in CAMERA_NAMES]
        rng = np.random.default_rng()
        values = {}
        for name in names:
            param = document.state.params.get(name)
            if param is None or document.state.is_locked(name):
                continue
            value = param.random_value(rng)
            if value is not None:
                values[name] = value
        if values:
            document.set_values(values)
            document.end_merge()
            self.status.emit(f"Randomized {len(values)} parameters")
        return len(values)

    def mutate(self, strength: float, group: str | None = None, names: list[str] | None = None) -> int:
        """Nudge the unlocked parameters by up to `strength` of their ranges; one undo step.

        By default the fragment's own parameters (declared in the tab, not in the includes — the raytracer's `Detail`,
        `BoundingSphere` and lights stay put); `group` restricts to one group, `names` to a list. The camera never moves.
        """
        import numpy as np
        document = self.document
        if document is None:
            return 0
        if names is None:
            own = document.source.own_param_names() if document.source is not None else []
            names = self.group_names(group) if group else (own or list(self.widgets))
            names = [n for n in names if n not in CAMERA_NAMES and n in self.widgets]
        rng = np.random.default_rng()
        values = {}
        for name in names:
            param = document.state.params.get(name)
            if param is None or document.state.is_locked(name):
                continue
            value = param.mutated_value(document.state.values[name], strength, rng)
            if value is not None and value != document.state.values[name]:
                values[name] = value
        if values:
            document.set_values(values)
            document.end_merge()
            self.status.emit(f"Mutated {len(values)} parameters by {strength * 100:.0f}%")
        return len(values)

    def group_action(self, kind: str, group: str | None = None) -> None:
        """`reset`, `lock`, `unlock`, `copy` or `preset` on a group (the current tab's by default)."""
        if self.document is None:
            return
        group = group or self.current_group()
        names = self.group_names(group)
        if kind == "reset":
            self.document.reset(names)
        elif kind == "randomize":
            self.randomize(group=group)
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

    def group_names_all(self) -> set[str]:
        return {self._group_of(w) for w in self.widgets.values()}


__all__ = ["ParameterPanel", "DEFAULT_GROUP", "FAVOURITES_GROUP"]
