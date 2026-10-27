"""A labelled slider + spin box (with arrows) for a real-valued setting; both always agree."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractSpinBox, QDoubleSpinBox, QHBoxLayout, QLabel, QSlider, QWidget

from .silent import set_value_silently

SPINBOX_WIDTH = 68
MAX_SLIDER_STEPS = 100_000


class FloatRow(QWidget):
    """Label + slider + double spin box showing the same number.

    The slider covers `minimum..maximum` at `decimals` resolution; the spin box may be given a wider
    range (`spin_range`) for values the slider does not reach — the slider then sits at its end.

    Signals:
        value_changed(float): The user moved the slider or edited the number.
    """
    value_changed = Signal(float)

    def __init__(self, label: str, minimum: float, maximum: float, decimals: int = 2, step: float | None = None,
                 suffix: str = "", spin_range: tuple[float, float] | None = None, parent: QWidget | None = None):
        super().__init__(parent)
        self.label = QLabel(label, self)
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.spin = QDoubleSpinBox(self)
        self._min, self._max = float(minimum), float(maximum)
        self._scale = 10 ** decimals
        while (self._max - self._min) * self._scale > MAX_SLIDER_STEPS:
            self._scale /= 10
        self._build(decimals, step, suffix, spin_range)
        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _build(self, decimals: int, step: float | None, suffix: str, spin_range: tuple[float, float] | None) -> None:
        self.slider.setRange(round(self._min * self._scale), round(self._max * self._scale))
        self.slider.setTracking(True)
        lo, hi = spin_range if spin_range is not None else (self._min, self._max)
        self.spin.setRange(float(lo), float(hi))
        self.spin.setDecimals(decimals)
        self.spin.setSingleStep(step if step is not None else 10 ** -decimals * 10)
        self.spin.setSuffix(suffix)
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
        self.spin.setFixedWidth(SPINBOX_WIDTH)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.setKeyboardTracking(False)
        self.label.setMinimumWidth(64)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

    # --- API ----------------------------------------------------------------
    def value(self) -> float:
        return self.spin.value()

    def set_value(self, value: float) -> None:
        """Programmatic update: moves both controls without emitting value_changed."""
        set_value_silently(self.spin, float(value))
        set_value_silently(self.slider, round(float(value) * self._scale))

    def set_tooltip(self, text: str) -> "FloatRow":
        for w in (self.label, self.slider, self.spin):
            w.setToolTip(text)
        return self

    # --- sync ---------------------------------------------------------------
    def _from_slider(self, raw: int) -> None:
        value = raw / self._scale
        set_value_silently(self.spin, value)
        self.value_changed.emit(value)

    def _from_spin(self, value: float) -> None:
        set_value_silently(self.slider, round(value * self._scale))
        self.value_changed.emit(value)
