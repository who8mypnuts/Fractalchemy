"""The Transform Editor's side panel: the tabs of Apophysis's editor, bound to an `EditorContext`.

* **Variations** — every loaded formula (built-ins, bundled plugins, user formulas) with the selected
  transform's weight for it; used ones in bold; search box, *Hide unused*, *Clear*. The third column tags
  `pre` / `post` formulas, 3D ones (they set the depth), direct-colour ones and random ones.
* **Variables** — the parameters of the transform's active variations (z / 3D parameters included), with
  *Show all variables* listing every parameter of every formula. Double-click a name to reset its default.
* **Xaos** — the transform's outgoing (*to*) or incoming (*from*) xaos weights.
* **Triangle** — corner coordinates of the triangle being edited, rotate / move / scale buttons with their
  amounts, and the pivot.
* **Transform** — the X, Y, O vectors of all three affines (pre / normal / post), rectangular or polar,
  with reset buttons, and *Auto-calculate pre_zscale* for 3D work.
* **Colors** — transform colour (on the palette), colour speed, opacity, direct colour, *solo*.

Every tab edits the document through the context (undoable) and refreshes from `refresh()`.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QSignalBlocker, Qt, Signal
from PySide6.QtGui import QColor, QMouseEvent, QPainter, QPaintEvent, QPen
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QPushButton, QRadioButton, QSizePolicy, QToolButton,
                               QVBoxLayout, QWidget)

from ..fractal import triangles as T
from ..fractal import variations as V
from ..fractal.scene import XForm
from ..fractal.triangles import CORNER_NAMES, CORNER_O, CORNER_X, CORNER_Y
from ..widgets.silent import set_value_silently
from ..widgets.triangle_view import PIVOT_LOCAL, PIVOT_WORLD, TriangleView
from ..widgets.value_table import ValueRow, ValueTable
from .editor_context import MODE_LABELS, MODE_NORMAL, MODE_POST, MODE_PRE, EditorContext
from .info_panel import palette_pixmap

SPIN_WIDTH = 82
ROTATE_STEPS = ("5", "10", "15", "30", "45", "60", "90", "180")
MOVE_STEPS = ("0.01", "0.05", "0.1", "0.25", "0.5", "1")
SCALE_STEPS = ("105", "110", "125", "150", "200")
KIND_TAGS = {V.PRE: "pre", V.POST: "post"}


def _spin(parent: QWidget, lo: float = -1e6, hi: float = 1e6, decimals: int = 4, step: float = 0.05,
          suffix: str = "") -> QDoubleSpinBox:
    box = QDoubleSpinBox(parent)
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setSuffix(suffix)
    box.setKeyboardTracking(False)
    box.setFixedWidth(SPIN_WIDTH)
    box.setAlignment(Qt.AlignmentFlag.AlignRight)
    return box


def variation_tags(var: V.Variation | None) -> str:
    """Short tags for the Variations list: `pre`, `post`, `3D`, `DC`, `random`, or `missing`."""
    if var is None:
        return "missing"
    tags = []
    if var.kind in KIND_TAGS:
        tags.append(KIND_TAGS[var.kind])
    if var.z == V.Z_FORMULA:
        tags.append("3D")
    if var.dc:
        tags.append("DC")
    if var.random:
        tags.append("random")
    return " ".join(tags)


def param_rows(xform: XForm, show_all: bool) -> list[ValueRow]:
    """The Variables tab's rows: parameters of the transform's variations (or of every formula)."""
    rows: list[ValueRow] = []
    seen: set[str] = set()
    names = list(xform.variations) if not show_all else sorted(V.REGISTRY, key=str.lower)
    if show_all:
        names = list(xform.variations) + [n for n in names if n not in xform.variations]
    for name in names:
        var = V.REGISTRY.get(name)
        used = name in xform.variations
        if var is None:
            for key, value in xform.params.items():   # a missing formula: show what the file had
                if key.startswith(name + "_") and key not in seen:
                    seen.add(key)
                    rows.append(ValueRow(key, value, name, f"{key}: parameter of {name} (formula not available)", bold=used,
                                         color=QColor(200, 60, 60)))
            continue
        for key, default in var.params.items():
            if key in seen:
                continue
            seen.add(key)
            info = var.param_info.get(key)
            value = xform.params.get(key, default)
            tip = f"{key} — parameter of {name}; default {default:g}"
            if info is not None:
                if info.min is not None or info.max is not None:
                    tip += f"; range {'' if info.min is None else f'{info.min:g}'} … {'' if info.max is None else f'{info.max:g}'}"
                if info.nonzero:
                    tip += "; must not be 0"
                if info.cyclic:
                    tip += "; cyclic"
            rows.append(ValueRow(key, value, name, tip, bold=used, integer=info is not None and info.type == "int"))
    for key, value in xform.params.items():   # parameters no formula declares (kept for round-tripping)
        if key not in seen:
            seen.add(key)
            rows.append(ValueRow(key, value, "", f"{key}: not declared by any loaded formula", color=QColor(150, 150, 150)))
    return rows


class PaletteSlider(QWidget):
    """The palette as a strip with a marker at the transform colour; click or drag to choose.

    Signals:
        value_changed(float): The colour position (0..1) while dragging / on click.
    """
    value_changed = Signal(float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._palette: list = []
        self._value = 0.0
        self._pixmap = None
        self.setMinimumHeight(26)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def set_palette(self, palette) -> None:
        self._palette = list(palette)
        self._pixmap = None
        self.update()

    def value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(1.0, float(value)))
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        w, h = self.width(), self.height()
        if self._palette:
            if self._pixmap is None or self._pixmap.width() != w - 2:
                self._pixmap = palette_pixmap(self._palette, max(1, w - 2), h - 8)
            painter.drawPixmap(1, 1, self._pixmap)
        painter.setPen(QPen(QColor(90, 90, 90), 1))
        painter.drawRect(0, 0, w - 1, h - 7)
        x = 1 + self._value * (w - 3)
        painter.setPen(QPen(QColor(20, 20, 20), 1))
        painter.setBrush(QColor(240, 240, 240))
        painter.drawPolygon([QPointF(x, h - 8), QPointF(x - 5, h - 1), QPointF(x + 5, h - 1)])
        painter.end()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton:
            self._pick(event.position().x())

    def _pick(self, x: float) -> None:
        value = max(0.0, min(1.0, (x - 1) / max(1, self.width() - 3)))
        if value != self._value:
            self.set_value(value)
            self.value_changed.emit(self._value)


class _Tab(QWidget):
    """Base: holds the context and a re-entrancy guard for model → control updates."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.context = context
        self._updating = False

    @property
    def document(self):
        return self.context.document

    def refresh(self) -> None:
        """Show the selected transform (no-op in the base)."""


# --- Variations ---------------------------------------------------------------------------------------------
class VariationsTab(_Tab):
    """Weights of every variation for the selected transform."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search variations…")
        self.search.setClearButtonEnabled(True)
        self.hide_unused = QCheckBox("Hide unused", self)
        self.clear_button = QPushButton("Clear", self)
        self.clear_button.setToolTip("Set every variation of this transform to zero")
        self.table = ValueTable(self, ("Variation", "Weight", "Kind"))
        self.table.setToolTip("Type a weight, or press on a name and drag sideways (Shift: coarse, Ctrl / Alt: fine).\n"
                              "Double-click a name to switch it between 0 and 1.")
        self.count_label = QLabel(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        bottom.addWidget(self.hide_unused)
        bottom.addWidget(self.count_label, 1)
        bottom.addWidget(self.clear_button)
        layout.addLayout(bottom)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        self.hide_unused.toggled.connect(lambda _c: self._apply_filter())
        self.clear_button.clicked.connect(self._clear)
        self.table.value_edited.connect(self._edited)
        self.table.name_double_clicked.connect(self._toggle)
        self._names: list[str] = []
        self.populate()

    def populate(self) -> None:
        """(Re)build the list from the registry — call after formulas were (re)loaded."""
        self._names = sorted(V.REGISTRY, key=str.lower)
        self.refresh()

    def refresh(self) -> None:
        xform = self.context.xform()
        weights = dict(xform.variations) if xform is not None else {}
        names = list(self._names)
        for name in weights:           # variations the file has that no formula provides still show (in red)
            if name not in V.REGISTRY and name not in names:
                names.append(name)
        rows = []
        for name in names:
            var = V.REGISTRY.get(name)
            tip = f"{name}" + (f" — {var.summary()}" if var is not None else " — not available: no loaded formula has this name")
            rows.append(ValueRow(name, weights.get(name, 0.0), variation_tags(var), tip, bold=name in weights,
                                 color=QColor(200, 60, 60) if var is None else None))
        self._updating = True
        try:
            self.table.set_rows(rows)
        finally:
            self._updating = False
        self.setEnabled(xform is not None)
        self._apply_filter()

    def _apply_filter(self) -> None:
        hide_unused = self.hide_unused.isChecked()
        shown = self.table.filter(self.search.text(), (lambda row: row.value == 0) if hide_unused else None)
        self.count_label.setText(f"{shown} of {len(self.table.names())}")

    def _edited(self, name: str, value: float) -> None:
        if not self._updating:
            self.document.set_variation(self.context.selected, name, value)

    def _toggle(self, name: str) -> None:
        current = self.table.value_of(name) or 0.0
        self.document.set_variation(self.context.selected, name, 1.0 if current == 0 else 0.0)

    def _clear(self) -> None:
        self.document.clear_variations(self.context.selected)


# --- Variables ----------------------------------------------------------------------------------------------
class VariablesTab(_Tab):
    """Parameters of the active variations (or all of them)."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search variables…")
        self.search.setClearButtonEnabled(True)
        self.show_all = QCheckBox("Show all variables", self)
        self.show_all.setToolTip("List every parameter of every loaded formula, not only those of the active variations")
        self.table = ValueTable(self, ("Variable", "Value", "Variation"))
        self.table.setToolTip("Type a value, or press on a name and drag sideways. Double-click a name to reset its default.")
        self.count_label = QLabel(self)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.search)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        bottom.addWidget(self.show_all)
        bottom.addWidget(self.count_label, 1)
        layout.addLayout(bottom)
        self.search.textChanged.connect(lambda _t: self._apply_filter())
        self.show_all.toggled.connect(lambda _c: self.refresh())
        self.table.value_edited.connect(self._edited)
        self.table.name_double_clicked.connect(self._reset)

    def refresh(self) -> None:
        xform = self.context.xform()
        rows = param_rows(xform, self.show_all.isChecked()) if xform is not None else []
        self._updating = True
        try:
            self.table.set_rows(rows)
        finally:
            self._updating = False
        self.setEnabled(xform is not None)
        self._apply_filter()

    def _apply_filter(self) -> None:
        shown = self.table.filter(self.search.text())
        self.count_label.setText(f"{shown} of {len(self.table.names())}")

    def _edited(self, key: str, value: float) -> None:
        if not self._updating:
            self.document.set_param(self.context.selected, key, value)

    def _reset(self, key: str) -> None:
        owner = V.parameter_owner(key)
        var = V.REGISTRY.get(owner) if owner else None
        if var is not None and key in var.params:
            self.document.set_param(self.context.selected, key, var.params[key])


# --- Xaos ---------------------------------------------------------------------------------------------------
class XaosTab(_Tab):
    """Outgoing (`to`) or incoming (`from`) xaos weights of the selected transform."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.to_button = QRadioButton("View links as \"to\"", self)
        self.from_button = QRadioButton("View links as \"from\"", self)
        self.to_button.setChecked(True)
        self.to_button.setToolTip("Each row: the relative weight of choosing that transform after this one")
        self.from_button.setToolTip("Each row: the relative weight of choosing this transform after that one")
        self.table = ValueTable(self, ("Transform", "Weight"))
        self.table.setToolTip("Relative weight of the link (1 = default, 0 = never). Double-click a name to switch 0 ↔ 1.")
        self.clear_all = QPushButton("Clear all", self)
        self.set_all = QPushButton("Set all", self)
        self.clear_all.setToolTip("Set every outgoing link of this transform to 0")
        self.set_all.setToolTip("Set every outgoing link of this transform to 1 (the default: no xaos)")
        self.note = QLabel(self)
        self.note.setWordWrap(True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.addWidget(self.table, 1)
        layout.addWidget(self.to_button)
        layout.addWidget(self.from_button)
        buttons = QHBoxLayout()
        buttons.addWidget(self.clear_all)
        buttons.addWidget(self.set_all)
        buttons.addStretch(1)
        layout.addLayout(buttons)
        layout.addWidget(self.note)
        self.to_button.toggled.connect(lambda _c: self.refresh())
        self.table.value_edited.connect(self._edited)
        self.table.name_double_clicked.connect(self._toggle)
        self.clear_all.clicked.connect(lambda: self._set_all(0.0))
        self.set_all.clicked.connect(lambda: self._set_all(1.0))

    def _row_name(self, index: int) -> str:
        xform = self.context.xform(index)
        label = f"{index + 1}"
        return label + (f" - {xform.name}" if xform is not None and xform.name else "")

    def refresh(self) -> None:
        flame = self.context.flame
        selected = self.context.selected
        rows: list[ValueRow] = []
        enabled = flame is not None and selected is not None
        if enabled:
            from ..fractal.xform_ops import chaos_row
            n = len(flame.xforms)
            for j in range(n):
                if self.to_button.isChecked():
                    value = chaos_row(flame.xforms[selected], n)[j]
                    tip = f"Weight of transform {j + 1} being chosen after transform {selected + 1}"
                else:
                    value = chaos_row(flame.xforms[j], n)[selected]
                    tip = f"Weight of transform {selected + 1} being chosen after transform {j + 1}"
                rows.append(ValueRow(self._row_name(j), value, "", tip, bold=value != 1.0, decimals=4))
        self._updating = True
        try:
            self.table.set_rows(rows)
        finally:
            self._updating = False
        self.setEnabled(enabled)
        self.note.setText("The final transform has no xaos links." if flame is not None and selected is None else "")

    def _indices(self, name: str) -> tuple[int, int] | None:
        names = self.table.names()
        if name not in names or self.context.selected is None:
            return None
        j, selected = names.index(name), self.context.selected
        return (selected, j) if self.to_button.isChecked() else (j, selected)

    def _edited(self, name: str, value: float) -> None:
        pair = self._indices(name)
        if pair is not None and not self._updating:
            self.document.set_chaos(pair[0], pair[1], value)

    def _toggle(self, name: str) -> None:
        pair = self._indices(name)
        if pair is not None:
            current = self.table.value_of(name) or 0.0
            self.document.set_chaos(pair[0], pair[1], 0.0 if current == 1.0 else 1.0)

    def _set_all(self, value: float) -> None:
        if self.context.selected is not None:
            self.document.set_all_chaos(self.context.selected, value)


# --- Triangle -----------------------------------------------------------------------------------------------
class TriangleTab(_Tab):
    """Corner coordinates, rotate / move / scale buttons and the pivot, acting on the triangle view's selection."""

    def __init__(self, context: EditorContext, view: TriangleView, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.view = view
        self.corner_boxes: dict[int, tuple[QDoubleSpinBox, QDoubleSpinBox]] = {}
        self.rotate_step = QComboBox(self)
        self.move_step = QComboBox(self)
        self.scale_step = QComboBox(self)
        self.pivot_mode = QPushButton(self)
        self.pivot_x = _spin(self, decimals=4, step=0.1)
        self.pivot_y = _spin(self, decimals=4, step=0.1)
        self.reset_pivot = QPushButton("Reset pivot", self)
        self.reset_triangle = QPushButton("Reset triangle", self)
        self.axis_lock = QCheckBox("Lock axes when moving O", self)
        self.extended_edit = QCheckBox("Edges rotate / scale (extended edit)", self)
        self.auto_weights = QCheckBox("Auto weights from triangle area", self)
        self.mode_label = QLabel(self)
        self._build()
        self._connect()
        self._steps_changed()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        self.mode_label.setWordWrap(True)
        layout.addWidget(self.mode_label)
        corners = QGroupBox("Corners", self)
        grid = QGridLayout(corners)
        grid.addWidget(QLabel("x", corners), 0, 1)
        grid.addWidget(QLabel("y", corners), 0, 2)
        for row, corner in enumerate((CORNER_X, CORNER_O, CORNER_Y), start=1):
            grid.addWidget(QLabel(CORNER_NAMES[corner], corners), row, 0)
            bx, by = _spin(corners), _spin(corners)
            bx.setToolTip(f"Corner {CORNER_NAMES[corner]} of the triangle (editor space, y up)")
            by.setToolTip(bx.toolTip())
            grid.addWidget(bx, row, 1)
            grid.addWidget(by, row, 2)
            self.corner_boxes[corner] = (bx, by)
        grid.setColumnStretch(3, 1)
        layout.addWidget(corners)
        ops = QGroupBox("Rotate · move · scale", self)
        ops_grid = QGridLayout(ops)
        # rotate row
        self.rotate_left90 = self._tool("↶ 90°", "Rotate the triangle 90° counter-clockwise about the pivot")
        self.rotate_left = self._tool("↶", "Rotate counter-clockwise by the angle (Ctrl: ÷6, Shift: ×6)")
        self.rotate_right = self._tool("↷", "Rotate clockwise by the angle (Ctrl: ÷6, Shift: ×6)")
        self.rotate_right90 = self._tool("↷ 90°", "Rotate the triangle 90° clockwise about the pivot")
        self.rotate_step.setEditable(True)
        self.rotate_step.addItems(ROTATE_STEPS)
        self.rotate_step.setCurrentText("15")
        self.rotate_step.setToolTip("Rotation step in degrees (also the snap angle when dragging with Shift)")
        ops_grid.addWidget(self.rotate_left90, 0, 0)
        ops_grid.addWidget(self.rotate_left, 0, 1)
        ops_grid.addWidget(self.rotate_step, 0, 2)
        ops_grid.addWidget(self.rotate_right, 0, 3)
        ops_grid.addWidget(self.rotate_right90, 0, 4)
        # move rows
        self.move_up = self._tool("▲", "Move up by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_down = self._tool("▼", "Move down by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_left = self._tool("◀", "Move left by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_right = self._tool("▶", "Move right by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_step.setEditable(True)
        self.move_step.addItems(MOVE_STEPS)
        self.move_step.setCurrentText("0.1")
        self.move_step.setToolTip("Move step in fractal units (also the snap when scaling a corner with Shift)")
        ops_grid.addWidget(self.move_up, 1, 2)
        ops_grid.addWidget(self.move_left, 2, 1)
        ops_grid.addWidget(self.move_step, 2, 2)
        ops_grid.addWidget(self.move_right, 2, 3)
        ops_grid.addWidget(self.move_down, 3, 2)
        # scale row
        self.scale_down = self._tool("−", "Shrink about the pivot by the percentage (Ctrl: √, Shift: squared)")
        self.scale_up = self._tool("+", "Grow about the pivot by the percentage (Ctrl: √, Shift: squared)")
        self.scale_step.setEditable(True)
        self.scale_step.addItems(SCALE_STEPS)
        self.scale_step.setCurrentText("125")
        self.scale_step.setToolTip("Scale step in percent (also the snap when scaling with Shift)")
        ops_grid.addWidget(self.scale_down, 4, 1)
        ops_grid.addWidget(self.scale_step, 4, 2)
        ops_grid.addWidget(self.scale_up, 4, 3)
        ops_grid.addWidget(self.reset_triangle, 4, 4)
        self.reset_triangle.setToolTip("Back to the reference triangle (the identity affine)")
        layout.addWidget(ops)
        pivot = QGroupBox("Pivot", self)
        pivot_layout = QGridLayout(pivot)
        self.pivot_mode.setCheckable(True)
        self.pivot_mode.setToolTip("Rotate and scale about the triangle's own point O (local) or about the world origin (world)")
        self.pivot_x.setToolTip("Pivot x: local (u, v) coordinates in the triangle, or world coordinates")
        self.pivot_y.setToolTip(self.pivot_x.toolTip())
        self.reset_pivot.setToolTip("Pivot back to O (local) or to the origin (world)")
        pivot_layout.addWidget(self.pivot_mode, 0, 0)
        pivot_layout.addWidget(QLabel("x", pivot), 0, 1)
        pivot_layout.addWidget(self.pivot_x, 0, 2)
        pivot_layout.addWidget(QLabel("y", pivot), 0, 3)
        pivot_layout.addWidget(self.pivot_y, 0, 4)
        pivot_layout.addWidget(self.reset_pivot, 0, 5)
        layout.addWidget(pivot)
        options = QGroupBox("Options", self)
        opt = QVBoxLayout(options)
        self.axis_lock.setChecked(True)
        self.axis_lock.setToolTip("Dragging corner O moves the whole triangle (off: O alone moves, shearing the triangle)")
        self.extended_edit.setChecked(True)
        self.extended_edit.setToolTip("Drag an axis edge to rotate, the hypotenuse to scale")
        self.auto_weights.setToolTip("Keep every transform's weight proportional to its triangle's area while editing")
        opt.addWidget(self.axis_lock)
        opt.addWidget(self.extended_edit)
        opt.addWidget(self.auto_weights)
        layout.addWidget(options)
        layout.addStretch(1)

    def _tool(self, text: str, tip: str) -> QToolButton:
        button = QToolButton(self)
        button.setText(text)
        button.setToolTip(tip)
        button.setAutoRepeat(True)
        button.setMinimumWidth(40)
        return button

    def _connect(self) -> None:
        for corner, (bx, by) in self.corner_boxes.items():
            bx.valueChanged.connect(lambda _v, c=corner: self._corner_edited(c))
            by.valueChanged.connect(lambda _v, c=corner: self._corner_edited(c))
        self.rotate_step.currentTextChanged.connect(self._steps_changed)
        self.move_step.currentTextChanged.connect(self._steps_changed)
        self.scale_step.currentTextChanged.connect(self._steps_changed)
        self.pivot_mode.toggled.connect(self._pivot_mode_toggled)
        self.pivot_x.valueChanged.connect(self._pivot_edited)
        self.pivot_y.valueChanged.connect(self._pivot_edited)
        self.reset_pivot.clicked.connect(self._reset_pivot)
        self.axis_lock.toggled.connect(lambda on: setattr(self.view, "axis_lock", on))
        self.extended_edit.toggled.connect(lambda on: setattr(self.view, "extended_edit", on))

    # --- steps (read by the window for buttons and keys) ---------------------------------------------------
    def rotate_degrees(self) -> float:
        return _parse(self.rotate_step.currentText(), 15.0)

    def move_amount(self) -> float:
        return _parse(self.move_step.currentText(), 0.1)

    def scale_factor(self) -> float:
        return max(1e-6, _parse(self.scale_step.currentText(), 125.0) / 100.0)

    def _steps_changed(self, *_args) -> None:
        self.view.rotate_step_degrees = self.rotate_degrees()
        self.view.move_step = self.move_amount()
        self.view.scale_step = self.scale_factor()

    # --- model → controls -----------------------------------------------------------------------------------
    def refresh(self) -> None:
        triangle = self.context.triangle()
        self.setEnabled(triangle is not None)
        self.mode_label.setText(f"Editing the <b>{MODE_LABELS[self.context.mode]}</b> triangle" if triangle is not None else "")
        self._updating = True
        try:
            if triangle is not None:
                for corner, (bx, by) in self.corner_boxes.items():
                    set_value_silently(bx, triangle[corner][0])
                    set_value_silently(by, triangle[corner][1])
            self.refresh_pivot()
        finally:
            self._updating = False

    def refresh_pivot(self) -> None:
        with QSignalBlocker(self.pivot_mode):
            self.pivot_mode.setChecked(self.view.pivot_mode == PIVOT_WORLD)
        self.pivot_mode.setText("World pivot" if self.view.pivot_mode == PIVOT_WORLD else "Local pivot")
        point = self.view.world_pivot if self.view.pivot_mode == PIVOT_WORLD else self.view.local_pivot
        set_value_silently(self.pivot_x, point[0])
        set_value_silently(self.pivot_y, point[1])

    # --- controls → model -----------------------------------------------------------------------------------
    def _corner_edited(self, corner: int) -> None:
        if self._updating:
            return
        triangle = self.context.triangle()
        if triangle is None:
            return
        bx, by = self.corner_boxes[corner]
        self.context.set_triangle(self.context.selected, T.move_corner(triangle, corner, (bx.value(), by.value())),
                                  kind=f"corner:{corner}:{self.context.selected}")

    def _pivot_mode_toggled(self, world: bool) -> None:
        self.view.set_pivot_mode(PIVOT_WORLD if world else PIVOT_LOCAL)
        self.refresh_pivot()

    def _pivot_edited(self, *_args) -> None:
        if self._updating:
            return
        if self.view.pivot_mode == PIVOT_WORLD:
            self.view.set_world_pivot(self.pivot_x.value(), self.pivot_y.value())
        else:
            self.view.set_local_pivot(self.pivot_x.value(), self.pivot_y.value())

    def _reset_pivot(self) -> None:
        if self.view.pivot_mode == PIVOT_WORLD:
            self.view.set_world_pivot(0.0, 0.0)
        else:
            self.view.set_local_pivot(0.0, 0.0)
        self.refresh_pivot()


# --- Transform ----------------------------------------------------------------------------------------------
class AffineGroup(QGroupBox):
    """X / Y / O vectors of one affine (editor space), rectangular or polar, with reset buttons.

    Signals:
        vector_changed(str, int, float, float): (mode, corner, first, second) — x / y, or length / angle in polar.
        reset_requested(str, int): (mode, corner) — corner -1 resets the whole affine.
    """
    vector_changed = Signal(str, int, float, float)
    reset_requested = Signal(str, int)

    def __init__(self, mode: str, title: str, parent: QWidget | None = None):
        super().__init__(title, parent)
        self.mode = mode
        self.polar = False
        self._updating = False
        self.boxes: dict[int, tuple[QDoubleSpinBox, QDoubleSpinBox]] = {}
        self.buttons: dict[int, QPushButton] = {}
        self.reset_all = QPushButton("Reset", self)
        grid = QGridLayout(self)
        for row, corner in enumerate((CORNER_X, CORNER_Y, CORNER_O)):
            button = QPushButton(CORNER_NAMES[corner], self)
            button.setFixedWidth(28)
            button.setToolTip(f"Reset the {CORNER_NAMES[corner]} vector" + (" (the offset)" if corner == CORNER_O else ""))
            button.clicked.connect(lambda _c=False, c=corner: self.reset_requested.emit(self.mode, c))
            first, second = _spin(self), _spin(self)
            first.valueChanged.connect(lambda _v, c=corner: self._edited(c))
            second.valueChanged.connect(lambda _v, c=corner: self._edited(c))
            grid.addWidget(button, row, 0)
            grid.addWidget(first, row, 1)
            grid.addWidget(second, row, 2)
            self.boxes[corner] = (first, second)
            self.buttons[corner] = button
        self.reset_all.setToolTip("Back to the identity")
        self.reset_all.clicked.connect(lambda: self.reset_requested.emit(self.mode, -1))
        grid.addWidget(self.reset_all, 0, 3, 3, 1)
        grid.setColumnStretch(4, 1)

    def show_affine(self, coefs, polar: bool) -> None:
        """Show the affine's vectors (`coefs` in flame-file convention; None disables the group)."""
        self.polar = polar
        self.setEnabled(coefs is not None)
        if coefs is None:
            return
        triangle = T.affine_to_triangle(coefs)
        ox, oy = triangle[CORNER_O]
        self._updating = True
        try:
            for corner, (first, second) in self.boxes.items():
                x, y = triangle[corner]
                if corner != CORNER_O:
                    x, y = x - ox, y - oy
                if polar:
                    first.setSuffix("")
                    second.setSuffix("°")
                    set_value_silently(first, math.hypot(x, y))
                    set_value_silently(second, math.degrees(math.atan2(y, x)))
                else:
                    first.setSuffix("")
                    second.setSuffix("")
                    set_value_silently(first, x)
                    set_value_silently(second, y)
        finally:
            self._updating = False

    def _edited(self, corner: int) -> None:
        if not self._updating:
            first, second = self.boxes[corner]
            self.vector_changed.emit(self.mode, corner, first.value(), second.value())


class TransformTab(_Tab):
    """The three affines as vectors, plus the 3D helper."""
    auto_zscale_toggled = Signal(bool)

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.rect_button = QRadioButton("Rectangular", self)
        self.polar_button = QRadioButton("Polar", self)
        self.rect_button.setChecked(True)
        self.groups = {MODE_PRE: AffineGroup(MODE_PRE, "Pre affine (applied first)", self),
                       MODE_NORMAL: AffineGroup(MODE_NORMAL, "Normal (the triangle)", self),
                       MODE_POST: AffineGroup(MODE_POST, "Post affine (applied last)", self)}
        self.auto_zscale = QCheckBox("Auto-calculate pre_zscale", self)
        self.auto_zscale.setToolTip("Keep pre_zscale = √|det| of the normal affine, so depth scales with the triangle (3D flames)")
        self.note = QLabel("Vectors are in editor space (y up): X and Y relative to O. Pre → Normal → variations → Post.", self)
        self.note.setWordWrap(True)
        self.note.setEnabled(False)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        row = QHBoxLayout()
        row.addWidget(self.rect_button)
        row.addWidget(self.polar_button)
        row.addStretch(1)
        layout.addLayout(row)
        for mode in (MODE_PRE, MODE_NORMAL, MODE_POST):
            layout.addWidget(self.groups[mode])
            self.groups[mode].vector_changed.connect(self._vector_changed)
            self.groups[mode].reset_requested.connect(self._reset)
        layout.addWidget(self.auto_zscale)
        layout.addWidget(self.note)
        layout.addStretch(1)
        self.rect_button.toggled.connect(lambda _c: self.refresh())
        self.auto_zscale.toggled.connect(self.auto_zscale_toggled)

    def refresh(self) -> None:
        xform = self.context.xform()
        polar = self.polar_button.isChecked()
        for mode, group in self.groups.items():
            group.show_affine(None if xform is None else getattr(xform, mode), polar)
            group.setTitle(group.title().rstrip(" ◀") + (" ◀" if mode == self.context.mode else ""))
        self.auto_zscale.setEnabled(xform is not None)

    def _vector_changed(self, mode: str, corner: int, first: float, second: float) -> None:
        affine = self.context.affine(mode=mode)
        if affine is None:
            return
        triangle = T.affine_to_triangle(affine)
        ox, oy = triangle[CORNER_O]
        if self.polar_button.isChecked():
            x, y = first * math.cos(math.radians(second)), first * math.sin(math.radians(second))
        else:
            x, y = first, second
        if corner == CORNER_O:
            new = T.translate(triangle, x - ox, y - oy)
        else:
            new = T.move_corner(triangle, corner, (ox + x, oy + y))
        self.context.set_triangle(self.context.selected, new, kind=f"vector:{mode}:{corner}:{self.context.selected}", mode=mode)

    def _reset(self, mode: str, corner: int) -> None:
        affine = self.context.affine(mode=mode)
        if affine is None:
            return
        if corner < 0:
            new = T.REFERENCE
        else:
            new = T.reset_corner(T.affine_to_triangle(affine), corner)
        self.context.set_triangle(self.context.selected, new, kind=f"reset:{mode}:{corner}:{self.context.selected}", mode=mode)


# --- Colors -------------------------------------------------------------------------------------------------
class ColorsTab(_Tab):
    """Transform colour, colour speed, opacity, direct colour and solo."""
    solo_toggled = Signal(bool)

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.palette = PaletteSlider(self)
        self.color_box = _spin(self, 0.0, 1.0, 3, 0.01)
        self.speed_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.symmetry_label = QLabel(self)
        self.opacity_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.var_color_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.solo = QCheckBox("Solo: show only this transform in the editor preview", self)
        self._build()
        self._connect()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        group = QGroupBox("Transform color", self)
        form = QFormLayout(group)
        self.palette.setToolTip("Where on the palette this transform colours its points (click or drag)")
        self.color_box.setToolTip("Colour position 0..1 on the palette")
        form.addRow(self.palette)
        form.addRow("Color", self.color_box)
        self.speed_box.setToolTip("How strongly the transform pulls the point colour to its own (flam3 colour speed, 0..1).\n"
                                  "Apophysis's 'symmetry' is 1 − 2·speed: 0.5 here is Apophysis 0.")
        speed_row = QHBoxLayout()
        speed_row.addWidget(self.speed_box)
        speed_row.addWidget(self.symmetry_label, 1)
        form.addRow("Color speed", speed_row)
        self.opacity_box.setToolTip("Visibility of the points this transform produces (0 = invisible)")
        form.addRow("Opacity", self.opacity_box)
        self.var_color_box.setToolTip("How much direct-colour variations (dc_…) recolour the point (Apophysis var_color)")
        form.addRow("Direct color", self.var_color_box)
        layout.addWidget(group)
        self.solo.setToolTip("Preview only the selected transform (the others' opacity is zero in the editor's preview; nothing is saved)")
        layout.addWidget(self.solo)
        layout.addStretch(1)

    def _connect(self) -> None:
        self.palette.value_changed.connect(lambda v: self._set("color", v))
        self.color_box.valueChanged.connect(lambda v: self._set("color", v))
        self.speed_box.valueChanged.connect(lambda v: self._set("color_speed", v))
        self.opacity_box.valueChanged.connect(lambda v: self._set("opacity", v))
        self.var_color_box.valueChanged.connect(lambda v: self._set("var_color", v))
        self.solo.toggled.connect(self.solo_toggled)

    def refresh(self) -> None:
        xform = self.context.xform()
        flame = self.context.flame
        self.setEnabled(xform is not None)
        if xform is None:
            return
        self._updating = True
        try:
            if flame is not None:
                self.palette.set_palette(flame.palette)
            self.palette.set_value(xform.color)
            set_value_silently(self.color_box, xform.color)
            set_value_silently(self.speed_box, xform.color_speed)
            self.symmetry_label.setText(f"(Apophysis symmetry {xform.symmetry:+.3g})")
            set_value_silently(self.opacity_box, xform.opacity)
            set_value_silently(self.var_color_box, xform.var_color)
            self.opacity_box.setEnabled(not self.context.is_final)
            self.solo.setEnabled(not self.context.is_final)
        finally:
            self._updating = False

    def _set(self, field: str, value: float) -> None:
        if not self._updating:
            self.document.set_xform_fields(self.context.selected, **{field: value})


def _parse(text: str, default: float) -> float:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return default


__all__ = ["VariationsTab", "VariablesTab", "XaosTab", "TriangleTab", "TransformTab", "ColorsTab", "PaletteSlider",
           "AffineGroup", "param_rows", "variation_tags"]
