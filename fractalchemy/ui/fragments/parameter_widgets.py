"""The widgets that edit a fragment's parameters — FragM's `VariableWidget` family.

Every widget is a row: the lock button (a padlock; hidden for `NotLockable`, disabled for `AlwaysLocked`), the name
(with the annotation's comment as tooltip) and the editor — a `ComboSlider` (slider + spin box with nine significant
digits, eighteen for doubles, linear or logarithmic, a context menu to select the source line, edit the bounds or
switch to scientific notation) for floats, one per component for vectors (unit directions renormalise around the
edited component), an int slider, a combo for menus, a check box, a colour swatch with the host's live colour
picker, a slider + swatch for float colours, and a file combo with channel boxes for samplers. Widgets know nothing
of GL or the document: they show a value and emit `value_edited(name, value, merge_key)` (a `merge_key` while a
slider drags so the document makes one undo step), `lock_toggled`, `select_source` and `bounds_edited`.
"""

from __future__ import annotations

import math
from typing import Any

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFrame, QGridLayout, QHBoxLayout, QInputDialog, QLabel, QMenu,
                               QPushButton, QSlider, QToolButton, QWidget)

from ...fragments.parameters import (BoolParameter, ColorParameter, FDEC, FloatColorParameter, FloatParameter, GuiParameter,
                                     IntMenuParameter, IntParameter, LockType, SamplerParameter, SliderType, VectorParameter)
from ...widgets.color_dialog import ColorPickerDialog
from ...widgets.icons import lock_icon
from ...widgets.silent import blocked

SLIDER_STEPS = 100_000_000      # FragM's 1e8 slider resolution
LABEL_WIDTH = 110


class ExpSpinBox(QDoubleSpinBox):
    """A spin box with many decimals that can show scientific notation (FragM's `ExpSpinBox`)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.scientific = False
        self.setKeyboardTracking(False)
        self.setGroupSeparatorShown(False)
        self.setDecimals(FDEC)
        self.setButtonSymbols(QDoubleSpinBox.ButtonSymbols.NoButtons)

    def textFromValue(self, value: float) -> str:  # noqa: N802 - Qt override
        if self.scientific:
            return f"{value:.{self.decimals()}e}"
        return f"{value:.{self.decimals()}g}"

    def valueFromText(self, text: str) -> float:  # noqa: N802 - Qt override
        try:
            return float(text.strip().replace(",", "."))
        except ValueError:
            return self.value()

    def validate(self, text: str, pos: int):  # noqa: D102 - Qt override: accept anything float() may read
        from PySide6.QtGui import QValidator
        return QValidator.State.Acceptable, text, pos


class ComboSlider(QWidget):
    """A slider with a spin box, mapping `[minimum, maximum]` linearly or logarithmically onto the slider.

    Signals:
        value_changed(float, bool): The new value and whether the edit is final (False while the slider drags).
        select_source(): The context menu's *Select source*.
        bound_edited(int, float): (1 = lower, 2 = upper) the user typed a new slider bound.
    """
    value_changed = Signal(float, bool)
    select_source = Signal()
    bound_edited = Signal(int, float)

    def __init__(self, default: float, minimum: float, maximum: float, logarithmic: bool = False, decimals: int = FDEC,
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.minimum, self.maximum, self.logarithmic = float(minimum), float(maximum), logarithmic
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.slider.setRange(0, SLIDER_STEPS)
        self.slider.setSingleStep(SLIDER_STEPS // 1000)
        self.slider.setPageStep(SLIDER_STEPS // 100)
        self.spinner = ExpSpinBox(self)
        self.spinner.setDecimals(decimals)
        self.spinner.setRange(-1e300, 1e300)
        self.spinner.setMinimumWidth(96)
        layout = QHBoxLayout(self)
        layout.setSpacing(2)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spinner)
        self._value = float(default)
        self.set_value(default)
        self.slider.valueChanged.connect(self._on_slider)
        self.slider.sliderReleased.connect(lambda: self.value_changed.emit(self._value, True))
        self.spinner.valueChanged.connect(self._on_spinner)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.DefaultContextMenu)

    # --- mapping ---------------------------------------------------------------------------------------------------------
    def _range(self) -> tuple[float, float]:
        if not self.logarithmic:
            return self.minimum, self.maximum
        lo, hi = sorted((abs(self.minimum), abs(self.maximum)))
        lo = max(lo, 1e-300)
        a, b = math.log(lo), math.log(hi)
        return (b, a) if self.maximum < 0 else (a, b)

    def _to_slider(self, value: float) -> int:
        lo, hi = self._range()
        v = math.log(max(abs(value), 1e-300)) if self.logarithmic else value
        if hi == lo:
            return 0
        return int(round(min(max((v - lo) / (hi - lo), 0.0), 1.0) * SLIDER_STEPS))

    def _from_slider(self, position: int) -> float:
        lo, hi = self._range()
        v = lo + (hi - lo) * position / SLIDER_STEPS
        if self.logarithmic:
            return math.copysign(math.exp(v), self.maximum if self.maximum != 0 else 1.0)
        return v

    # --- value -------------------------------------------------------------------------------------------------------------
    @property
    def value(self) -> float:
        return self._value

    def set_value(self, value: float) -> None:
        """Show `value` without announcing it."""
        self._value = float(value)
        with blocked(self.slider, self.spinner):
            self.slider.setValue(self._to_slider(self._value))
            self.spinner.setValue(self._value)

    def set_bounds(self, minimum: float, maximum: float) -> None:
        self.minimum, self.maximum = float(minimum), float(maximum)
        self.set_value(self._value)

    def _on_slider(self, position: int) -> None:
        self._value = self._from_slider(position)
        with blocked(self.spinner):
            self.spinner.setValue(self._value)
        self.value_changed.emit(self._value, not self.slider.isSliderDown())

    def _on_spinner(self, value: float) -> None:
        self._value = float(value)
        with blocked(self.slider):
            self.slider.setValue(self._to_slider(self._value))
        self.value_changed.emit(self._value, True)

    def contextMenuEvent(self, event) -> None:  # noqa: D102 - Qt override
        menu = QMenu(self)
        actions = {menu.addAction("Select source"): "source", menu.addAction("Scientific"): "sci", menu.addAction("Standard"): "std",
                   menu.addAction("Upper bound…"): "upper", menu.addAction("Lower bound…"): "lower"}
        choice = actions.get(menu.exec(event.globalPos()))
        if choice == "source":
            self.select_source.emit()
        elif choice in ("sci", "std"):
            self.spinner.scientific = choice == "sci"
            self.spinner.setValue(self.spinner.value())
        elif choice in ("upper", "lower"):
            which = 2 if choice == "upper" else 1
            current = self.maximum if which == 2 else self.minimum
            value, ok = QInputDialog.getDouble(self, "Slider bound", "Slider upper bound" if which == 2 else "Slider lower bound",
                                               current, -1e8, 1e8, 6)
            if ok:
                self.bound_edited.emit(which, value)


class VariableWidget(QWidget):
    """The row of one parameter: lock button, label, editor (see the module docstring).

    Signals:
        value_edited(str, object, object): (name, value, merge_key or None).
        row_action(str, str): (name, `reset` / `randomize` / `copy` / `paste`) from the row's context menu.
        lock_toggled(str, object): (name, the new `LockType`).
        select_source(str): *Select source* on one of its sliders.
        bounds_edited(str, int, int, float): (name, component 1-based, 1 = lower / 2 = upper, value).
    """
    value_edited = Signal(str, object, object)
    row_action = Signal(str, str)
    lock_toggled = Signal(str, object)
    select_source = Signal(str)
    bounds_edited = Signal(str, int, int, float)

    def __init__(self, param: GuiParameter, parent: QWidget | None = None):
        super().__init__(parent)
        self.param = param
        self.name = param.name
        self._lock = param.lock
        self.lock_button = QToolButton(self)
        self.lock_button.setCheckable(True)
        self.lock_button.setAutoRaise(True)
        self.lock_button.setFixedSize(18, 18)
        self.lock_button.setToolTip("Lock: bake the value into the shader (needs a rebuild; faster)")
        self.lock_button.toggled.connect(self._on_lock_button)
        self.label = QLabel(param.name, self)
        self.label.setMinimumWidth(LABEL_WIDTH)
        self.label.setToolTip(param.tooltip or param.name)
        self.editor = QWidget(self)
        layout = QHBoxLayout(self)
        layout.setSpacing(4)
        layout.setContentsMargins(2, 1, 2, 1)
        layout.addWidget(self.lock_button, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.label, 0, Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.editor, 1)
        self.set_lock(param.lock)

    def contextMenuEvent(self, event) -> None:  # noqa: N802 - Qt override
        """The row's menu (on the label / lock): reset, randomize, copy / paste the value."""
        menu = QMenu(self)
        actions = {menu.addAction("Reset to default"): "reset", menu.addAction("Randomize"): "randomize", menu.addAction("Copy value"): "copy",
                   menu.addAction("Paste value"): "paste"}
        choice = actions.get(menu.exec(event.globalPos()))
        if choice:
            self.row_action.emit(self.name, choice)

    # --- lock -----------------------------------------------------------------------------------------------------------
    def set_lock(self, lock: LockType) -> None:
        """Show a lock state."""
        self._lock = lock
        with blocked(self.lock_button):
            self.lock_button.setChecked(lock.locked)
        self.lock_button.setIcon(lock_icon(lock.locked))
        self.lock_button.setVisible(lock != LockType.NOT_LOCKABLE)
        self.lock_button.setEnabled(lock != LockType.ALWAYS_LOCKED)
        self.label.setStyleSheet("QLabel { border: 1px solid palette(mid); border-radius: 2px; padding: 0 2px; }" if lock.locked else "")

    def _on_lock_button(self, checked: bool) -> None:
        lock = LockType.LOCKED if checked else LockType.NOT_LOCKED
        self.set_lock(lock)
        self.lock_toggled.emit(self.name, lock)

    # --- value --------------------------------------------------------------------------------------------------------------
    def set_value(self, value: Any) -> None:
        """Show `value` without announcing it."""
        raise NotImplementedError

    def value(self) -> Any:
        raise NotImplementedError

    def set_slider_type(self, slider: SliderType) -> None:
        """Linear / logarithmic (float kinds only)."""

    def _emit(self, final: bool) -> None:
        self.value_edited.emit(self.name, self.value(), None if final else ("drag", self.name))

    def _slider(self, default: float, minimum: float, maximum: float, component: int) -> ComboSlider:
        slider = ComboSlider(default, minimum, maximum, self.param.slider == SliderType.LOGARITHMIC, self.param.precision, self.editor)
        slider.select_source.connect(lambda: self.select_source.emit(self.name))
        slider.bound_edited.connect(lambda which, value, c=component: self.bounds_edited.emit(self.name, c, which, value))
        return slider


class FloatWidget(VariableWidget):
    """`slider[from, default, to]` on a float."""

    def __init__(self, param: FloatParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.slider = self._slider(param.default, param.from_, param.to, 1)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.slider)
        self.slider.value_changed.connect(lambda _v, final: self._emit(final))

    def set_value(self, value):
        self.slider.set_value(float(value))

    def value(self):
        return self.slider.value

    def set_slider_type(self, slider: SliderType) -> None:
        self.slider.logarithmic = slider == SliderType.LOGARITHMIC
        self.slider.set_value(self.slider.value)


class VectorWidget(VariableWidget):
    """`slider[(…),(…),(…)]` on a vector: one slider per component, renormalising when the parameter is a unit direction."""

    def __init__(self, param: VectorParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.sliders = [self._slider(param.default[i], param.from_[i], param.to[i], i + 1) for i in range(param.components)]
        self.last_component = 1                 # which component was edited last (the F7 easing dialog starts there)
        layout = QGridLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        for i, slider in enumerate(self.sliders):
            layout.addWidget(slider, i, 0)
            slider.value_changed.connect(lambda _v, final, index=i: self._on_component(index, final))

    def _on_component(self, index: int, final: bool) -> None:
        self.last_component = index + 1
        if self.param.normalize:
            self._renormalize(index)
        self._emit(final)

    def _renormalize(self, edited: int) -> None:
        """FragM's `nNChanged`: keep the edited component, scale the others so the vector stays unit length."""
        values = [s.value for s in self.sliders]
        x = min(max(values[edited], -1.0), 1.0)
        rest = sum(v * v for i, v in enumerate(values) if i != edited)
        if rest == 0:
            self.sliders[edited].set_value(1.0 if x >= 0 else -1.0)
            return
        a = math.sqrt(max(1.0 - x * x, 0.0) / rest)
        self.sliders[edited].set_value(x)
        for i, slider in enumerate(self.sliders):
            if i != edited:
                slider.set_value(values[i] * a)

    def set_value(self, value):
        for slider, v in zip(self.sliders, value):
            slider.set_value(float(v))

    def value(self):
        return tuple(s.value for s in self.sliders)

    def set_slider_type(self, slider: SliderType) -> None:
        for s in self.sliders:
            s.logarithmic = slider == SliderType.LOGARITHMIC
            s.set_value(s.value)


class IntWidget(VariableWidget):
    """`slider[from, default, to]` on an int."""

    def __init__(self, param: IntParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.slider = QSlider(Qt.Orientation.Horizontal, self.editor)
        self.slider.setRange(min(param.from_, param.to), max(param.from_, param.to))
        self.spinner = QDoubleSpinBox(self.editor)
        self.spinner.setDecimals(0)
        self.spinner.setRange(-1e9, 1e9)
        self.spinner.setKeyboardTracking(False)
        self.spinner.setMinimumWidth(70)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spinner)
        self.set_value(param.default)
        self.slider.valueChanged.connect(self._on_slider)
        self.slider.sliderReleased.connect(lambda: self._emit(True))
        self.spinner.valueChanged.connect(self._on_spinner)
        self.slider.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.slider.customContextMenuRequested.connect(self._menu)

    def _on_slider(self, value: int) -> None:
        with blocked(self.spinner):
            self.spinner.setValue(value)
        self._emit(not self.slider.isSliderDown())

    def _on_spinner(self, value: float) -> None:
        with blocked(self.slider):
            self.slider.setValue(int(value))
        self._emit(True)

    def _menu(self, pos: QPoint) -> None:
        menu = QMenu(self)
        source = menu.addAction("Select source")
        upper = menu.addAction("Upper bound…")
        choice = menu.exec(self.slider.mapToGlobal(pos))
        if choice is source:
            self.select_source.emit(self.name)
        elif choice is upper:
            value, ok = QInputDialog.getInt(self, "Slider bound", "Slider upper bound", self.slider.maximum(), -100000000, 100000000)
            if ok:
                self.bounds_edited.emit(self.name, 1, 2, float(value))

    def set_value(self, value):
        with blocked(self.slider, self.spinner):
            self.slider.setValue(int(value))
            self.spinner.setValue(int(value))

    def value(self):
        return int(self.spinner.value())


class IntMenuWidget(VariableWidget):
    """`menu[default, a;b;c]`: a combo box."""

    def __init__(self, param: IntMenuParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.combo = QComboBox(self.editor)
        self.combo.addItems([t.strip() for t in param.texts])
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.combo, 1)
        self.set_value(param.default)
        self.combo.currentIndexChanged.connect(lambda _i: self._emit(True))

    def set_value(self, value):
        with blocked(self.combo):
            self.combo.setCurrentIndex(min(max(int(value), 0), self.combo.count() - 1))

    def value(self):
        return self.combo.currentIndex()


class BoolWidget(VariableWidget):
    """`checkbox[true|false]`."""

    def __init__(self, param: BoolParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.check = QCheckBox(self.editor)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.check)
        layout.addStretch(1)
        self.set_value(param.default)
        self.check.toggled.connect(lambda _c: self._emit(True))

    def set_value(self, value):
        with blocked(self.check):
            self.check.setChecked(bool(value))

    def value(self):
        return self.check.isChecked()


class KeepingColorPicker(ColorPickerDialog):
    """The host's picker, except that closing its window keeps the colour (only *Cancel* reverts) — the colour is
    applied live while picking, so a close must not silently undo what the viewport already shows."""

    def closeEvent(self, event) -> None:  # noqa: N802 - Qt override
        event.accept()
        self.accept()


class ColorSwatch(QFrame):
    """A clickable colour rectangle opening the host's live colour picker (closing the picker keeps the colour).

    Signals:
        color_changed(tuple, bool): (r, g, b) in 0..1 and whether the edit is final (the dialog closed with OK).
    """
    color_changed = Signal(tuple, bool)

    def __init__(self, rgb: tuple[float, float, float], parent: QWidget | None = None):
        super().__init__(parent)
        self._rgb = tuple(float(c) for c in rgb)
        self._dialog: ColorPickerDialog | None = None
        self.setFixedSize(48, 20)
        self.setFrameShape(QFrame.Shape.StyledPanel)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Click to pick a colour")

    @property
    def rgb(self) -> tuple[float, float, float]:
        return self._rgb

    def set_rgb(self, rgb) -> None:
        self._rgb = tuple(min(max(float(c), 0.0), 1.0) for c in rgb)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: D102 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect().adjusted(1, 1, -1, -1), QColor.fromRgbF(*self._rgb))
        painter.end()

    def mousePressEvent(self, event) -> None:  # noqa: D102 - Qt override
        if event.button() != Qt.MouseButton.LeftButton:
            return
        if self._dialog is None:
            self._dialog = KeepingColorPicker(self.window())
            self._dialog.color_changed.connect(lambda c: self._on_picked(c, False))
            self._dialog.finished_with.connect(self._on_finished)
        original = self._rgb
        self._dialog.set_color(tuple(int(round(c * 255)) for c in self._rgb), as_original=True)
        self._original = original
        self._dialog.show_beside(self)

    def _on_picked(self, color: tuple, final: bool) -> None:
        self.set_rgb(tuple(c / 255.0 for c in color))
        self.color_changed.emit(self._rgb, final)

    def _on_finished(self, accepted: bool) -> None:
        if not accepted:
            self.set_rgb(self._original)
        self.color_changed.emit(self._rgb, True)


class ColorWidget(VariableWidget):
    """`color[r,g,b]` on a vec3."""

    def __init__(self, param: ColorParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        self.swatch = ColorSwatch(param.default, self.editor)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.swatch)
        layout.addStretch(1)
        self.swatch.color_changed.connect(lambda _c, final: self._emit(final))

    def set_value(self, value):
        self.swatch.set_rgb(value)

    def value(self):
        return self.swatch.rgb


class FloatColorWidget(VariableWidget):
    """`color[min, default, max, r, g, b]` on a vec4: a value slider and a colour, as `(r, g, b, value)`."""

    def __init__(self, param: FloatColorParameter, parent: QWidget | None = None):
        super().__init__(param, parent)
        r, g, b, v = param.default
        self.slider = self._slider(v, param.from_, param.to, 4)
        self.swatch = ColorSwatch((r, g, b), self.editor)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.swatch)
        self.slider.value_changed.connect(lambda _v, final: self._emit(final))
        self.swatch.color_changed.connect(lambda _c, final: self._emit(final))

    def set_value(self, value):
        r, g, b, v = value
        self.swatch.set_rgb((r, g, b))
        self.slider.set_value(float(v))

    def value(self):
        return (*self.swatch.rgb, self.slider.value)


class SamplerWidget(VariableWidget):
    """`file[name]` / `file[name, channels]`: an editable file combo, channel boxes for EXR and a browse button.

    Signals:
        browse_requested(str): The `…` button (the panel opens the file dialog and calls `set_value`).
    """
    browse_requested = Signal(str)

    def __init__(self, param: SamplerParameter, files: list[str], parent: QWidget | None = None):
        super().__init__(param, parent)
        self.combo = QComboBox(self.editor)
        self.combo.setEditable(True)
        self.combo.addItems(files)
        self.channels = [QComboBox(self.editor) for _ in range(4)]
        self.browse = QPushButton("…", self.editor)
        self.browse.setFixedWidth(28)
        layout = QHBoxLayout(self.editor)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        layout.addWidget(self.combo, 1)
        for box in self.channels:
            layout.addWidget(box)
            box.hide()
        layout.addWidget(self.browse)
        self.set_value(param.default + (f" {param.channels}" if param.channels else ""))
        self.combo.lineEdit().editingFinished.connect(lambda: self._emit(True))
        self.combo.activated.connect(lambda _i: self._emit(True))
        self.browse.clicked.connect(lambda: self.browse_requested.emit(self.name))

    def set_channels(self, available: list[str]) -> None:
        """Offer EXR channel names (hidden when the file is not an EXR)."""
        for box in self.channels:
            box.setVisible(bool(available))
            with blocked(box):
                box.clear()
                box.addItems(available)

    def set_value(self, value):
        file, channels = SamplerParameter.split_value(str(value))
        with blocked(self.combo):
            self.combo.setEditText(file)
        names = channels.split(";") if channels else []
        for box, name in zip(self.channels, names):
            index = box.findText(name)
            if index >= 0:
                with blocked(box):
                    box.setCurrentIndex(index)

    def value(self):
        file = self.combo.currentText().strip()
        if self.channels[0].isVisible():
            return file + " " + ";".join(box.currentText() for box in self.channels)
        return file

    def set_missing(self, missing: bool) -> None:
        """Red background when the file cannot be found (FragM's hint)."""
        self.combo.setStyleSheet("QComboBox { background: #ffb3b3; }" if missing else "")


def make_widget(param: GuiParameter, files: list[str] = (), parent: QWidget | None = None) -> VariableWidget:
    """The widget class for a parameter kind."""
    if isinstance(param, FloatParameter):
        return FloatWidget(param, parent)
    if isinstance(param, VectorParameter):
        return VectorWidget(param, parent)
    if isinstance(param, FloatColorParameter):
        return FloatColorWidget(param, parent)
    if isinstance(param, ColorParameter):
        return ColorWidget(param, parent)
    if isinstance(param, IntMenuParameter):
        return IntMenuWidget(param, parent)
    if isinstance(param, IntParameter):
        return IntWidget(param, parent)
    if isinstance(param, BoolParameter):
        return BoolWidget(param, parent)
    if isinstance(param, SamplerParameter):
        return SamplerWidget(param, list(files), parent)
    raise TypeError(f"no widget for {param!r}")


__all__ = ["ComboSlider", "ExpSpinBox", "VariableWidget", "FloatWidget", "VectorWidget", "IntWidget", "IntMenuWidget", "BoolWidget",
           "ColorWidget", "FloatColorWidget", "SamplerWidget", "ColorSwatch", "make_widget"]
