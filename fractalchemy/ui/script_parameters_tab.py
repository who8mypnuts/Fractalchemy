"""The Script Editor drawer's *Parameters* tab: one control per `param()` declaration of the last run.

A pure view — `LiveParameters` (`script_live.py`) decides what moving a control does. Rows:

* a number with `min` and `max`: a slider and a spin box (`FloatRow`; integers use 0 decimals), otherwise a spin box;
* True / False: a check box; `choices`: a dropdown; text: a line edit that commits on Enter or when it loses focus.

A row's label is dimmed while the value is the declared default and shown normally, with a trailing "•", once you
change it; its tooltip is the declaration's `help`. Right-click a row: *Reset to default*, *Copy value*, *Animate…*,
*Go to declaration*. Above the rows: a status chip (*Live*, *Updating…*, *Not live: …*, *Detached: …*) and a banner when
the script has been edited since it ran; below them the seed (*New seed*, *Keep seed on Run*) and *Reset all*,
*Set as defaults in script*, *Explore…*. With nothing declared the tab explains `param()` and can insert an example.
"""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QHBoxLayout, QLabel, QLineEdit, QMenu, QPushButton,
                               QScrollArea, QSpinBox, QToolButton, QVBoxLayout, QWidget)

from ..machines import LiveState
from ..scripting.parameters import ParamSpec
from ..widgets.float_row import FloatRow
from ..widgets.silent import blocked
from ..widgets.theming import colored_html, on_theme_changed, set_themed_style

EXAMPLE = "angle = param('Angle', 30, min=-180, max=180)\n"
EMPTY_TEXT = ("<p>This script has no parameters.</p><p>Declare the inputs a script should expose and run it — a control "
              "appears here for each, and moving it updates the fractal live:</p>"
              "<pre>angle = param('Angle', 30, min=-180, max=180)\ncopies = param('Copies', 3, min=1, max=12)\n"
              "keep = param('Keep colours', True)\npalette = param('Palette', 'Fire', choices=list_gradient_presets())</pre>")
UNBOUNDED = 1e9
STATUS_TEXT = {LiveState.OFF: ("", "dim_text"), LiveState.READY: ("● Live", "success"), LiveState.PENDING: ("● Live", "success"),
               LiveState.RERUNNING: ("● Live", "success"), LiveState.QUEUED: ("● Live", "success"),
               LiveState.INERT: ("Not live", "warning"), LiveState.DETACHED: ("Detached", "warning")}
BUSY_TEXT = ("Updating…", "dim_text")


class ParamRow(QWidget):
    """One parameter's control (see the module docstring).

    Signals:
        value_changed(str, object, bool): (name, value, final — False while a slider is being dragged).
        menu_requested(str, object): (name, global position) for the row's context menu.
    """
    value_changed = Signal(str, object, bool)
    menu_requested = Signal(str, object)

    def __init__(self, spec: ParamSpec, value: Any, parent: QWidget | None = None):
        super().__init__(parent)
        self.spec = spec
        self._touched = False
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.float_row: FloatRow | None = None
        self.editor: QWidget
        if spec.kind in ("float", "int") and spec.bounded:
            decimals = 0 if spec.kind == "int" else spec.decimals
            self.float_row = FloatRow(spec.name, spec.minimum, spec.maximum, decimals, spec.step, parent=self)
            self.label = self.float_row.label                      # the row's own label
            self.label.setMinimumWidth(90)
            self.editor = self.float_row
            self.float_row.value_changed.connect(lambda v: self._emit(self._number(v), not self.float_row.slider.isSliderDown()))
            self.float_row.slider.sliderReleased.connect(lambda: self._emit(self.value(), True))
            layout.addWidget(self.float_row)
        else:
            self.label = QLabel(spec.name, self)
            self.label.setMinimumWidth(90)
            layout.addWidget(self.label)
            self.editor = self._make_editor(spec)
            layout.addWidget(self.editor, 1)
        for widget in (self.label, self.editor):
            widget.setToolTip(spec.help or spec.name)
        self.set_value(value)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(lambda pos: self.menu_requested.emit(spec.name, self.mapToGlobal(pos)))

    def _make_editor(self, spec: ParamSpec) -> QWidget:
        if spec.kind == "bool":
            box = QCheckBox(self)
            box.toggled.connect(lambda checked: self._emit(bool(checked), True))
            return box
        if spec.kind == "choice":
            combo = QComboBox(self)
            combo.addItems([str(c) for c in spec.choices])
            combo.currentIndexChanged.connect(lambda i: self._emit(spec.choices[i], True))
            return combo
        if spec.kind == "text":
            line = QLineEdit(self)
            line.editingFinished.connect(lambda: self._emit(line.text(), True))
            return line
        spin: QSpinBox | QDoubleSpinBox
        if spec.kind == "int":
            spin = QSpinBox(self)
            spin.setRange(int(spec.minimum if spec.minimum is not None else -UNBOUNDED),
                          int(spec.maximum if spec.maximum is not None else UNBOUNDED))
            spin.setSingleStep(int(spec.step or 1))
        else:
            spin = QDoubleSpinBox(self)
            spin.setDecimals(spec.decimals)
            spin.setRange(spec.minimum if spec.minimum is not None else -UNBOUNDED, spec.maximum if spec.maximum is not None else UNBOUNDED)
            spin.setSingleStep(spec.step or 10 ** -spec.decimals * 10)
        spin.setKeyboardTracking(False)
        spin.valueChanged.connect(lambda v: self._emit(self._number(v), True))
        return spin

    def _number(self, value: float):
        return int(round(value)) if self.spec.kind == "int" else float(value)

    def _emit(self, value: Any, final: bool) -> None:
        self.value_changed.emit(self.spec.name, value, bool(final))

    # --- value -------------------------------------------------------------------------------------------------------------
    def value(self) -> Any:
        if self.float_row is not None:
            return self._number(self.float_row.value())
        editor = self.editor
        if isinstance(editor, QCheckBox):
            return editor.isChecked()
        if isinstance(editor, QComboBox):
            return self.spec.choices[editor.currentIndex()]
        if isinstance(editor, QLineEdit):
            return editor.text()
        return self._number(editor.value())

    def set_value(self, value: Any) -> None:
        """Show `value` without announcing it."""
        if self.float_row is not None:
            self.float_row.set_value(float(value))
            return
        editor = self.editor
        with blocked(editor):
            if isinstance(editor, QCheckBox):
                editor.setChecked(bool(value))
            elif isinstance(editor, QComboBox):
                editor.setCurrentIndex(self.spec.choices.index(value) if value in self.spec.choices else 0)
            elif isinstance(editor, QLineEdit):
                editor.setText(str(value))
            else:
                editor.setValue(value)

    def set_touched(self, touched: bool) -> None:
        """Mark the value as changed from the default (a normal label with "•") or not (dimmed)."""
        self._touched = touched
        self.label.setText(self.spec.name + (" •" if touched else ""))
        set_themed_style(self.label, "" if touched else "QLabel {{ color: {dim_text}; }}")


class ParametersTab(QWidget):
    """The tab (see the module docstring).

    Signals:
        value_changed(str, object, bool): A control moved (name, value, final).
        reset_requested(object): Reset one parameter (its name) or all (None).
        bake_requested(): *Set as defaults in script*.
        reseed_requested(): *New seed*.
        keep_seed_toggled(bool): *Keep seed on Run*.
        goto_line(int): *Go to declaration*.
        insert_example(): The empty state's *Insert example*.
        explore_requested(): *Explore…* (the Mutate & Breed grid's script tab).
        animate_requested(str): *Animate…* on a row.
    """
    value_changed = Signal(str, object, bool)
    reset_requested = Signal(object)
    bake_requested = Signal()
    reseed_requested = Signal()
    keep_seed_toggled = Signal(bool)
    goto_line = Signal(int)
    insert_example = Signal()
    explore_requested = Signal()
    animate_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.rows: dict[str, ParamRow] = {}
        self._specs: list[ParamSpec] = []
        self._state = LiveState.OFF
        self._reason = ""
        self._busy = False
        self.status = QLabel(self)
        self.status.setTextFormat(Qt.TextFormat.RichText)
        self.status.setWordWrap(True)
        self.banner = QLabel(self)
        self.banner.setWordWrap(True)
        self.banner.setTextFormat(Qt.TextFormat.RichText)
        self.error = QLabel(self)
        self.error.setWordWrap(True)
        self.error.setTextFormat(Qt.TextFormat.RichText)
        self.empty = QLabel(EMPTY_TEXT, self)
        self.empty.setWordWrap(True)
        self.empty.setTextFormat(Qt.TextFormat.RichText)
        self.example_button = QPushButton("Insert example", self)
        self.rows_widget = QWidget(self)
        self.rows_layout = QVBoxLayout(self.rows_widget)
        self.rows_layout.setContentsMargins(0, 0, 0, 0)
        self.rows_layout.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidget(self.rows_widget)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        self.seed_label = QLabel(self)
        self.reseed_button = QToolButton(self)
        self.reseed_button.setText("🎲 New seed")
        self.reseed_button.setToolTip("Run again with new random numbers")
        self.keep_seed = QCheckBox("Keep seed on Run", self)
        self.keep_seed.setToolTip("Run uses this seed too, so random scripts repeat exactly")
        self.reset_button = QPushButton("Reset all", self)
        self.bake_button = QPushButton("Set as defaults in script", self)
        self.bake_button.setToolTip("Write the current values into the param() calls as their new defaults")
        self.explore_button = QPushButton("Explore…", self)
        self.explore_button.setToolTip("Eight variations of these values in the Mutate & Breed grid")
        self._build(scroll)
        self.example_button.clicked.connect(self.insert_example.emit)
        self.reseed_button.clicked.connect(self.reseed_requested.emit)
        self.keep_seed.toggled.connect(self.keep_seed_toggled.emit)
        self.reset_button.clicked.connect(lambda: self.reset_requested.emit(None))
        self.bake_button.clicked.connect(self.bake_requested.emit)
        self.explore_button.clicked.connect(self.explore_requested.emit)
        self._busy_timer = QTimer(self, singleShot=True)
        on_theme_changed(self, lambda _theme: self._show_status())
        self.set_specs([], {})

    def _build(self, scroll: QScrollArea) -> None:
        seed_row = QHBoxLayout()
        seed_row.addWidget(self.seed_label)
        seed_row.addWidget(self.reseed_button)
        seed_row.addStretch(1)
        seed_row.addWidget(self.keep_seed)
        buttons = QHBoxLayout()
        buttons.addWidget(self.reset_button)
        buttons.addWidget(self.bake_button)
        buttons.addStretch(1)
        buttons.addWidget(self.explore_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.addWidget(self.status)
        layout.addWidget(self.banner)
        layout.addWidget(self.error)
        layout.addWidget(self.empty)
        layout.addWidget(self.example_button, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(scroll, 1)
        layout.addLayout(seed_row)
        layout.addLayout(buttons)
        self.seed_controls = (self.seed_label, self.reseed_button, self.keep_seed, self.reset_button, self.bake_button, self.explore_button)

    # --- rows ----------------------------------------------------------------------------------------------------------------
    def set_specs(self, specs: list[ParamSpec], values: dict[str, Any], touched: set[str] = frozenset()) -> None:
        """Show one row per spec (a row whose spec is unchanged keeps its widget, so a drag in progress survives)."""
        if [s for s in specs] != self._specs:
            keep = {name: row for name, row in self.rows.items() if any(s.name == name and s.same_control(row.spec) for s in specs)}
            for name, row in list(self.rows.items()):
                if name not in keep:
                    row.deleteLater()
            self.rows = {}
            while self.rows_layout.count() > 1:
                self.rows_layout.takeAt(0)
            for spec in specs:
                row = keep.get(spec.name) or self._new_row(spec, values.get(spec.name, spec.default))
                row.spec = spec
                self.rows[spec.name] = row
                self.rows_layout.insertWidget(self.rows_layout.count() - 1, row)
            self._specs = list(specs)
        for name, row in self.rows.items():
            if name in values and row.value() != values[name]:
                row.set_value(values[name])
            row.set_touched(name in touched)
        has = bool(specs)
        self.empty.setVisible(not has)
        self.example_button.setVisible(not has)
        for widget in self.seed_controls:
            widget.setVisible(has)

    def _new_row(self, spec: ParamSpec, value: Any) -> ParamRow:
        row = ParamRow(spec, value, self.rows_widget)
        row.value_changed.connect(self.value_changed.emit)
        row.menu_requested.connect(self._row_menu)
        return row

    def row_menu(self, name: str) -> QMenu:
        """The context menu of a row."""
        row = self.rows[name]
        menu = QMenu(self)
        menu.addAction("Reset to default", lambda: self.reset_requested.emit(name))
        menu.addAction("Copy value", lambda: QGuiApplication.clipboard().setText(repr(row.value())))
        animate = menu.addAction("Animate…", lambda: self.animate_requested.emit(name))
        animate.setEnabled(row.spec.kind in ("float", "int", "choice", "bool"))
        goto = menu.addAction("Go to declaration", lambda: self.goto_line.emit(row.spec.line or 1))
        goto.setEnabled(row.spec.line is not None)
        return menu

    def _row_menu(self, name: str, pos) -> None:
        self.row_menu(name).exec(pos)

    # --- status ---------------------------------------------------------------------------------------------------------------
    def set_state(self, state: LiveState, reason: str = "") -> None:
        """Show the live session's state (`reason` says why it is not live)."""
        self._state, self._reason = state, reason
        self._show_status()

    def set_busy(self, busy: bool) -> None:
        """A re-run has been running for a while ("Updating…")."""
        self._busy = busy
        self._show_status()

    def _show_status(self) -> None:
        text, role = BUSY_TEXT if self._busy else STATUS_TEXT.get(self._state, ("", "dim_text"))
        reason = f" — {self._reason}" if self._reason and self._state in (LiveState.INERT, LiveState.DETACHED, LiveState.OFF) else ""
        self.status.setText(colored_html(text, role) + reason if text or reason else "")
        self.status.setVisible(bool(text or reason))

    def set_code_changed(self, changed: bool) -> None:
        """The banner: the editor's text differs from the code that ran."""
        self.banner.setText(colored_html("The script has changed since it ran: the controls drive the version that ran. "
                                         "Run it to pick up your changes.", "warning") if changed else "")
        self.banner.setVisible(changed)

    def set_error(self, text: str) -> None:
        """The last re-run's error (empty clears it)."""
        self.error.setText(colored_html(text, "error") if text else "")
        self.error.setVisible(bool(text))

    def set_seed(self, seed: int | None, keep: bool) -> None:
        self.seed_label.setText(f"Seed {seed}" if seed is not None else "Seed —")
        with blocked(self.keep_seed):
            self.keep_seed.setChecked(keep)

    @property
    def state(self) -> LiveState:
        return self._state

    def status_text(self) -> str:
        """The status line as plain text (tests)."""
        from html import unescape
        import re
        return unescape(re.sub(r"<[^>]+>", "", self.status.text()))


__all__ = ["ParametersTab", "ParamRow", "EXAMPLE"]
