"""The Transform Editor's geometry and colour tabs, bound to an `EditorContext` (the list tabs are `editor_value_tabs`).

* **Triangle** — corner coordinates of the triangle being edited, rotate / move / scale buttons with their
  amounts, and the pivot.
* **Transform** — the X, Y, O vectors of all three affines (pre / normal / post), rectangular or polar,
  with reset buttons, and *Auto-calculate pre_zscale* for 3D work.
* **Colors** — transform colour (on the palette), colour speed, opacity, direct colour, *solo*, and the range /
  depth / density of the canvas's *variation preview* (Apophysis's sliders; the toolbar button turns it on).

Every tab edits the document through the context (undoable) and refreshes from `refresh()`.
"""

from __future__ import annotations

import math

from PySide6.QtCore import QSignalBlocker, Qt, Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QPushButton, QRadioButton, QSlider, QToolButton, QVBoxLayout, QWidget)

from ..fractal import triangles as T
from ..fractal.triangle_drag import DragSteps
from ..fractal.triangles import CORNER_NAMES, CORNER_O, CORNER_X, CORNER_Y
from ..widgets.palette_slider import PaletteSlider
from ..widgets.silent import set_value_silently, updating
from ..widgets.triangle_view import PIVOT_LOCAL, PIVOT_WORLD, TriangleView
from .editor_context import MODE_LABELS, MODE_NORMAL, MODE_POST, MODE_PRE, EditorContext

SPIN_WIDTH = 82
ROTATE_STEPS = ("5", "10", "15", "30", "45", "60", "90", "180")
MOVE_STEPS = ("0.01", "0.05", "0.1", "0.25", "0.5", "1")
SCALE_STEPS = ("105", "110", "125", "150", "200")


def _spin(parent: QWidget, lo: float = -1e6, hi: float = 1e6, decimals: int = 4, step: float = 0.05,
          suffix: str = "") -> QDoubleSpinBox:
    """A compact, right-aligned double spin box that only reports committed values."""
    box = QDoubleSpinBox(parent)
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setSuffix(suffix)
    box.setKeyboardTracking(False)
    box.setFixedWidth(SPIN_WIDTH)
    box.setAlignment(Qt.AlignmentFlag.AlignRight)
    return box


class _Tab(QWidget):
    """Base: holds the context and the re-entrancy guard of model → control updates."""

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(parent)
        self.context = context
        self._updating = False

    @property
    def document(self):
        """The document the tab edits."""
        return self.context.document

    def refresh(self) -> None:
        """Show the selected transform's values (subclasses fill their controls)."""


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
        for group in (self._corners_group(), self._operations_group(), self._pivot_group(), self._options_group()):
            layout.addWidget(group)
        layout.addStretch(1)

    def _corners_group(self) -> QGroupBox:
        """X / O / Y coordinate boxes."""
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
        return corners

    def _operations_group(self) -> QGroupBox:
        """The rotate / move / scale buttons around their step boxes, Apophysis's layout."""
        ops = QGroupBox("Rotate · move · scale", self)
        grid = QGridLayout(ops)
        self.rotate_left90 = self._tool("↶ 90°", "Rotate the triangle 90° counter-clockwise about the pivot")
        self.rotate_left = self._tool("↶", "Rotate counter-clockwise by the angle (Ctrl: ÷6, Shift: ×6)")
        self.rotate_right = self._tool("↷", "Rotate clockwise by the angle (Ctrl: ÷6, Shift: ×6)")
        self.rotate_right90 = self._tool("↷ 90°", "Rotate the triangle 90° clockwise about the pivot")
        self.move_up = self._tool("▲", "Move up by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_down = self._tool("▼", "Move down by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_left = self._tool("◀", "Move left by the step (Ctrl: ÷10, Shift: ×10)")
        self.move_right = self._tool("▶", "Move right by the step (Ctrl: ÷10, Shift: ×10)")
        self.scale_down = self._tool("−", "Shrink about the pivot by the percentage (Ctrl: √, Shift: squared)")
        self.scale_up = self._tool("+", "Grow about the pivot by the percentage (Ctrl: √, Shift: squared)")
        self.reset_triangle.setToolTip("Back to the reference triangle (the identity affine)")
        for box, items, default, tip in (
                (self.rotate_step, ROTATE_STEPS, "15", "Rotation step in degrees (also the snap angle when dragging with Shift)"),
                (self.move_step, MOVE_STEPS, "0.1", "Move step in fractal units (also the snap when scaling a corner with Shift)"),
                (self.scale_step, SCALE_STEPS, "125", "Scale step in percent (also the snap when scaling with Shift)")):
            box.setEditable(True)
            box.addItems(items)
            box.setCurrentText(default)
            box.setToolTip(tip)
        for widget, row, column in ((self.rotate_left90, 0, 0), (self.rotate_left, 0, 1), (self.rotate_step, 0, 2), (self.rotate_right, 0, 3),
                                    (self.rotate_right90, 0, 4), (self.move_up, 1, 2), (self.move_left, 2, 1), (self.move_step, 2, 2),
                                    (self.move_right, 2, 3), (self.move_down, 3, 2), (self.scale_down, 4, 1), (self.scale_step, 4, 2),
                                    (self.scale_up, 4, 3), (self.reset_triangle, 4, 4)):
            grid.addWidget(widget, row, column)
        return ops

    def _pivot_group(self) -> QGroupBox:
        pivot = QGroupBox("Pivot", self)
        grid = QGridLayout(pivot)
        self.pivot_mode.setCheckable(True)
        self.pivot_mode.setToolTip("Rotate and scale about the triangle's own point O (local) or about the world origin (world)")
        self.pivot_x.setToolTip("Pivot x: local (u, v) coordinates in the triangle, or world coordinates")
        self.pivot_y.setToolTip(self.pivot_x.toolTip())
        self.reset_pivot.setToolTip("Pivot back to O (local) or to the origin (world)")
        for widget, column in ((self.pivot_mode, 0), (QLabel("x", pivot), 1), (self.pivot_x, 2), (QLabel("y", pivot), 3), (self.pivot_y, 4),
                               (self.reset_pivot, 5)):
            grid.addWidget(widget, 0, column)
        return pivot

    def _options_group(self) -> QGroupBox:
        options = QGroupBox("Options", self)
        layout = QVBoxLayout(options)
        self.axis_lock.setChecked(True)
        self.axis_lock.setToolTip("Dragging corner O moves the whole triangle (off: O alone moves, shearing the triangle)")
        self.extended_edit.setChecked(True)
        self.extended_edit.setToolTip("Drag an axis edge to rotate, the hypotenuse to scale")
        self.auto_weights.setToolTip("Keep every transform's weight proportional to its triangle's area while editing")
        for box in (self.axis_lock, self.extended_edit, self.auto_weights):
            layout.addWidget(box)
        return options

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
        """The rotation step in degrees (15 when the box holds nonsense)."""
        return _parse(self.rotate_step.currentText(), 15.0)

    def move_amount(self) -> float:
        """The move step in fractal units (0.1 when the box holds nonsense)."""
        return _parse(self.move_step.currentText(), 0.1)

    def scale_factor(self) -> float:
        """The scale step as a factor (125 % → 1.25)."""
        return max(1e-6, _parse(self.scale_step.currentText(), 125.0) / 100.0)

    def auto_weights_enabled(self) -> bool:
        """Whether weights follow the triangles' areas (the *auto weights* option)."""
        return self.auto_weights.isChecked()

    def _steps_changed(self, *_args) -> None:
        self.view.drag_steps = DragSteps(self.rotate_degrees(), self.move_amount(), self.scale_factor())

    # --- model → controls -----------------------------------------------------------------------------------
    def refresh(self) -> None:
        """Show the corners of the triangle being edited and the pivot."""
        triangle = self.context.triangle()
        self.setEnabled(triangle is not None)
        self.mode_label.setText(f"Editing the <b>{MODE_LABELS[self.context.mode]}</b> triangle" if triangle is not None else "")
        with updating(self):
            if triangle is not None:
                for corner, (bx, by) in self.corner_boxes.items():
                    set_value_silently(bx, triangle[corner][0])
                    set_value_silently(by, triangle[corner][1])
            self.refresh_pivot()

    def refresh_pivot(self) -> None:
        """Show the canvas's pivot mode and coordinates."""
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
        with updating(self):
            for corner, (first, second) in self.boxes.items():
                x, y = triangle[corner]
                if corner != CORNER_O:
                    x, y = x - ox, y - oy
                second.setSuffix("°" if polar else "")
                if polar:
                    set_value_silently(first, math.hypot(x, y))
                    set_value_silently(second, math.degrees(math.atan2(y, x)))
                else:
                    set_value_silently(first, x)
                    set_value_silently(second, y)

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
        """Show all three affines as vectors, marking the one the canvas edits."""
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
VAR_PREVIEW_RANGE = (1, 5)      # Apophysis's trackbars: range ±1..5 units, depth 1..5 passes, density 1..5 (×5 per unit)
VAR_PREVIEW_DEFAULTS = {"range": 2, "depth": 1, "density": 2}


class ColorsTab(_Tab):
    """Transform colour, colour speed, opacity, direct colour, solo, and the variation preview's sliders.

    Signals:
        solo_toggled(bool): The *solo* box.
        var_preview_changed(): Range / depth / density of the variation preview changed.
    """
    solo_toggled = Signal(bool)
    var_preview_changed = Signal()

    def __init__(self, context: EditorContext, parent: QWidget | None = None):
        super().__init__(context, parent)
        self.palette = PaletteSlider(self)
        self.color_box = _spin(self, 0.0, 1.0, 3, 0.01)
        self.speed_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.symmetry_label = QLabel(self)
        self.opacity_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.var_color_box = _spin(self, 0.0, 1.0, 3, 0.05)
        self.solo = QCheckBox("Solo: show only this transform in the editor preview", self)
        self.var_preview_sliders: dict[str, QSlider] = {}
        self.var_preview_labels: dict[str, QLabel] = {}
        self.var_preview_group = QGroupBox("Variation preview", self)
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
        self.var_preview_group.setToolTip("The grid of dots the canvas shows for the selected transform when the toolbar's "
                                          "variation preview is on (no effect on the rendered image)")
        grid = QGridLayout(self.var_preview_group)
        for row, (key, title, tip) in enumerate((("range", "Range", "How far the grid of input points reaches: ±1 … ±5 units"),
                                                 ("depth", "Depth", "How many times each point goes through the transform"),
                                                 ("density", "Density", "Points per unit of the grid: 5 … 25"))):
            slider = QSlider(Qt.Orientation.Horizontal, self.var_preview_group)
            slider.setRange(*VAR_PREVIEW_RANGE)
            slider.setValue(VAR_PREVIEW_DEFAULTS[key])
            slider.setTickPosition(QSlider.TickPosition.TicksBelow)
            slider.setToolTip(tip)
            value = QLabel(self.var_preview_group)
            value.setMinimumWidth(22)
            grid.addWidget(QLabel(title, self.var_preview_group), row, 0)
            grid.addWidget(slider, row, 1)
            grid.addWidget(value, row, 2)
            self.var_preview_sliders[key] = slider
            self.var_preview_labels[key] = value
        layout.addWidget(self.var_preview_group)
        layout.addStretch(1)
        self._show_var_preview_values()

    def _connect(self) -> None:
        self.palette.value_changed.connect(lambda v: self._set("color", v))
        self.color_box.valueChanged.connect(lambda v: self._set("color", v))
        self.speed_box.valueChanged.connect(lambda v: self._set("color_speed", v))
        self.opacity_box.valueChanged.connect(lambda v: self._set("opacity", v))
        self.var_color_box.valueChanged.connect(lambda v: self._set("var_color", v))
        self.solo.toggled.connect(self.solo_toggled)
        for slider in self.var_preview_sliders.values():
            slider.valueChanged.connect(self._var_preview_slid)

    # --- variation preview --------------------------------------------------------------------------------
    def var_preview_settings(self) -> tuple[int, int, int]:
        """(range, depth, density) as chosen on the sliders."""
        return tuple(self.var_preview_sliders[k].value() for k in ("range", "depth", "density"))   # type: ignore[return-value]

    def set_var_preview_settings(self, range_units: int, depth: int, density: int) -> None:
        """Set the sliders (clamped to their range, no signal)."""
        for key, value in (("range", range_units), ("depth", depth), ("density", density)):
            set_value_silently(self.var_preview_sliders[key], max(VAR_PREVIEW_RANGE[0], min(VAR_PREVIEW_RANGE[1], int(value))))
        self._show_var_preview_values()

    def _show_var_preview_values(self) -> None:
        r, d, n = self.var_preview_settings()
        self.var_preview_labels["range"].setText(f"±{r}")
        self.var_preview_labels["depth"].setText(str(d))
        self.var_preview_labels["density"].setText(str(n * 5))

    def _var_preview_slid(self, *_args) -> None:
        self._show_var_preview_values()
        self.var_preview_changed.emit()

    def refresh(self) -> None:
        """Show the transform's colour, speed, opacity and direct colour on the current palette."""
        xform = self.context.xform()
        flame = self.context.flame
        self.setEnabled(xform is not None)
        if xform is None:
            return
        with updating(self):
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

    def _set(self, field: str, value: float) -> None:
        if not self._updating:
            self.document.set_xform_fields(self.context.selected, **{field: value})


def _parse(text: str, default: float) -> float:
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return default


__all__ = ["TriangleTab", "TransformTab", "ColorsTab", "AffineGroup"]
