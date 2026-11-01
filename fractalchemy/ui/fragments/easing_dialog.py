"""The easing-curve dialog (`F7`) — FragM's `EasingWindow`: animate one slider component between two frames.

Pick the parameter and component, the curve (Qt's easing curves, each drawn as a small icon), the start and end
values, the frame range, the loop count and ping-pong, and — for the elastic / bounce / back curves — period,
amplitude and overshoot. The graph shows the value over the animation. When the component already has a curve the
buttons are *Apply* / *Discard* (remove it) / *Cancel*, as in FragM.
"""

from __future__ import annotations

from PySide6.QtCore import QRectF, Qt, QSize
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDialogButtonBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QListWidget, QListWidgetItem, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from ...fragments.animation import AnimationSettings
from ...fragments.easing import BACK, BOUNCE, CURVE_NAMES, ELASTIC, EasingSetting, curve_number, curve_type
from ...fragments.parameters import FloatColorParameter, FloatParameter, VectorParameter
from ...fragments.state import ParameterState
from ...widgets.silent import blocked

GRAPH_COLOR = QColor("#1e88e5")
AXIS_COLOR = QColor(120, 120, 120)


def curve_icon(number: int, size: int = 48) -> QIcon:
    """A small plot of the curve (FragM's easing picker shows these)."""
    pixmap = QPixmap(size, size)
    pixmap.fill(QColor(250, 250, 250))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(AXIS_COLOR, 1))
    painter.drawRect(2, 2, size - 5, size - 5)
    curve = EasingSetting("x", number, 0.0, 1.0, 0, 100).curve()
    path = QPainterPath()
    for i in range(0, 41):
        t = i / 40
        v = curve.valueForProgress(t)
        x = 4 + t * (size - 9)
        y = size - 4 - min(max(v, -0.5), 1.5) * (size - 9) * 0.6 - (size - 9) * 0.2
        path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
    painter.setPen(QPen(GRAPH_COLOR, 1.6))
    painter.drawPath(path)
    painter.end()
    return QIcon(pixmap)


class EasingGraph(QWidget):
    """The value of the curve over the animation's frames."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setting: EasingSetting | None = None
        self.frames = 250
        self.setMinimumSize(320, 160)

    def show_setting(self, setting: EasingSetting, frames: int) -> None:
        self.setting, self.frames = setting, max(1, frames)
        self.update()

    def paintEvent(self, event) -> None:  # noqa: D102 - Qt override
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(250, 250, 250))
        rect = self.rect().adjusted(8, 8, -8, -8)
        painter.setPen(QPen(AXIS_COLOR, 1))
        painter.drawRect(rect)
        if self.setting is None:
            painter.end()
            return
        s = self.setting
        low, high = min(s.start, s.end), max(s.start, s.end)
        margin = max(abs(high - low) * 0.25, 1e-6)
        low, high = low - margin, high + margin
        values = [s.value_at(f) for f in range(self.frames + 1)]
        low, high = min(low, min(values)), max(high, max(values))
        path = QPainterPath()
        for frame, value in enumerate(values):
            x = rect.left() + frame / self.frames * rect.width()
            y = rect.bottom() - (value - low) / (high - low) * rect.height()
            path.moveTo(x, y) if frame == 0 else path.lineTo(x, y)
        painter.setPen(QPen(QColor(200, 60, 60, 120), 1, Qt.PenStyle.DashLine))
        for frame in (s.first_frame, s.end_frame):
            x = rect.left() + min(max(frame, 0), self.frames) / self.frames * rect.width()
            painter.drawLine(int(x), rect.top(), int(x), rect.bottom())
        painter.setPen(QPen(GRAPH_COLOR, 2))
        painter.drawPath(path)
        painter.setPen(AXIS_COLOR)
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft, f" {high:g}")
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignLeft, f" {low:g}")
        painter.drawText(QRectF(rect), Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignRight, f"{self.frames} frames ")
        painter.end()


class EasingDialog(QDialog):
    """Edit the easing curve of one slider component (see the module docstring).

    `result_setting` holds the curve when the dialog was accepted; `discarded` is True when *Discard* removed it.
    """

    def __init__(self, state: ParameterState, animation: AnimationSettings, existing: list[EasingSetting], slider: str = "",
                 parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Easing curve")
        self.state = state
        self.animation = animation
        self.existing = {c.slider: c for c in existing}
        self.result_setting: EasingSetting | None = None
        self.discarded = False
        self.slider_combo = QComboBox(self)
        self._fill_sliders()
        self.curves = QListWidget(self)
        self.curves.setIconSize(QSize(40, 40))
        self.curves.setMaximumWidth(230)
        for name in CURVE_NAMES:
            item = QListWidgetItem(curve_icon(curve_number(name), 40), name)
            item.setData(Qt.ItemDataRole.UserRole, curve_number(name))
            self.curves.addItem(item)
        self.start_spin, self.end_spin = self._double(), self._double()
        self.first_spin, self.last_spin, self.loops_spin = QSpinBox(self), QSpinBox(self), QSpinBox(self)
        for spin in (self.first_spin, self.last_spin):
            spin.setRange(0, 10_000_000)
        self.loops_spin.setRange(1, 100000)
        self.pong_check = QCheckBox("Ping-pong (reverse every other loop)", self)
        self.period_spin, self.amplitude_spin, self.overshoot_spin = self._double(0.3), self._double(1.0), self._double(1.70158)
        self.graph = EasingGraph(self)
        self.buttons = QDialogButtonBox(self)
        self.apply_button = self.buttons.addButton("Apply", QDialogButtonBox.ButtonRole.AcceptRole)
        self.discard_button = QPushButton("Discard curve", self)
        self.buttons.addButton(self.discard_button, QDialogButtonBox.ButtonRole.DestructiveRole)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        self._layout()
        self._connect()
        self.select_slider(slider)

    def _double(self, value: float = 0.0) -> QDoubleSpinBox:
        spin = QDoubleSpinBox(self)
        spin.setDecimals(6)
        spin.setRange(-1e9, 1e9)
        spin.setValue(value)
        spin.setKeyboardTracking(False)
        return spin

    def _fill_sliders(self) -> None:
        """Every float component: `Power1`, `JuliaC1..3`, the value of a float colour as `Glow4` (FragM's slider names)."""
        for name, param in self.state.params.items():
            if isinstance(param, FloatParameter):
                self.slider_combo.addItem(f"{name}", f"{name}1")
            elif isinstance(param, VectorParameter):
                for i in range(param.components):
                    self.slider_combo.addItem(f"{name} [{'xyzw'[i]}]", f"{name}{i + 1}")
            elif isinstance(param, FloatColorParameter):
                self.slider_combo.addItem(f"{name} [value]", f"{name}4")

    def _layout(self) -> None:
        form = QFormLayout()
        form.addRow("Parameter", self.slider_combo)
        form.addRow("Value start", self.start_spin)
        form.addRow("Value end", self.end_spin)
        form.addRow("Frame in", self.first_spin)
        form.addRow("Frame out", self.last_spin)
        form.addRow("Loops", self.loops_spin)
        form.addRow("", self.pong_check)
        props = QGroupBox("Curve properties", self)
        props_form = QFormLayout(props)
        props_form.addRow("Period (elastic)", self.period_spin)
        props_form.addRow("Amplitude (elastic, bounce)", self.amplitude_spin)
        props_form.addRow("Overshoot (back)", self.overshoot_spin)
        right = QVBoxLayout()
        right.addLayout(form)
        right.addWidget(props)
        right.addWidget(QLabel("Value over the animation:", self))
        right.addWidget(self.graph, 1)
        top = QHBoxLayout()
        top.addWidget(self.curves)
        top.addLayout(right, 1)
        layout = QVBoxLayout(self)
        layout.addLayout(top, 1)
        layout.addWidget(self.buttons)
        self.resize(760, 560)

    def _connect(self) -> None:
        self.slider_combo.currentIndexChanged.connect(lambda _i: self._load_slider())
        self.curves.currentRowChanged.connect(lambda _r: self._refresh())
        for widget in (self.start_spin, self.end_spin, self.first_spin, self.last_spin, self.loops_spin, self.period_spin,
                       self.amplitude_spin, self.overshoot_spin):
            widget.valueChanged.connect(lambda _v: self._refresh())
        self.pong_check.toggled.connect(lambda _c: self._refresh())
        self.buttons.accepted.connect(self._accept)
        self.buttons.rejected.connect(self.reject)
        self.discard_button.clicked.connect(self._discard)

    # --- state ------------------------------------------------------------------------------------------------------------
    @property
    def slider(self) -> str:
        return str(self.slider_combo.currentData() or "")

    def select_slider(self, slider: str) -> None:
        index = self.slider_combo.findData(slider) if slider else -1
        if index < 0 and self.slider_combo.count():
            index = 0
        with blocked(self.slider_combo):
            self.slider_combo.setCurrentIndex(index)
        self._load_slider()

    def _current_value(self) -> float:
        param = self.state.params.get(EasingSetting(self.slider, 0, 0, 0, 0, 0).parameter)
        value = self.state.get(param.name) if param else 0.0
        component = int(self.slider[-1]) if self.slider[-1:].isdigit() else 1
        if isinstance(value, (tuple, list)):
            return float(value[component - 1]) if component - 1 < len(value) else 0.0
        return float(value or 0.0)

    def _load_slider(self) -> None:
        """Show the existing curve of the chosen component, or a fresh one from the current value over the whole animation."""
        existing = self.existing.get(self.slider)
        has = existing is not None
        self.discard_button.setEnabled(has)
        self.apply_button.setText("Apply" if has else "Add curve")
        setting = existing or EasingSetting(self.slider, 0, self._current_value(), self._current_value(), 0, self.animation.frames)
        self._show(setting)
        self._refresh()

    def _show(self, s: EasingSetting) -> None:
        with blocked(self.curves, self.start_spin, self.end_spin, self.first_spin, self.last_spin, self.loops_spin, self.pong_check,
                     self.period_spin, self.amplitude_spin, self.overshoot_spin):
            for row in range(self.curves.count()):
                if self.curves.item(row).data(Qt.ItemDataRole.UserRole) == s.type_number:
                    self.curves.setCurrentRow(row)
            self.start_spin.setValue(s.start)
            self.end_spin.setValue(s.end)
            self.first_spin.setValue(s.first_frame)
            self.last_spin.setValue(s.last_frame)
            self.loops_spin.setValue(max(1, s.loops))
            self.pong_check.setChecked(s.pingpong)
            self.period_spin.setValue(s.period)
            self.amplitude_spin.setValue(s.amplitude)
            self.overshoot_spin.setValue(s.overshoot)

    def setting(self) -> EasingSetting:
        """The curve as the dialog shows it."""
        item = self.curves.currentItem()
        number = int(item.data(Qt.ItemDataRole.UserRole)) if item else 0
        return EasingSetting(self.slider, number, self.start_spin.value(), self.end_spin.value(), self.first_spin.value(),
                             max(self.first_spin.value(), self.last_spin.value()), self.period_spin.value(), self.amplitude_spin.value(),
                             self.overshoot_spin.value(), self.loops_spin.value(), self.pong_check.isChecked())

    def _refresh(self) -> None:
        setting = self.setting()
        kind = curve_type(setting.type_number)
        self.period_spin.setEnabled(kind in ELASTIC)
        self.amplitude_spin.setEnabled(kind in ELASTIC or kind in BOUNCE)
        self.overshoot_spin.setEnabled(kind in BACK)
        self.graph.show_setting(setting, self.animation.frames)
        self.apply_button.setEnabled(bool(self.slider))

    def _accept(self) -> None:
        self.result_setting = self.setting()
        self.accept()

    def _discard(self) -> None:
        self.discarded = True
        self.accept()


__all__ = ["EasingDialog", "EasingGraph", "curve_icon"]
