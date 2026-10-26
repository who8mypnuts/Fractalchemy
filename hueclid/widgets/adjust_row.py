"""A labelled slider + compact spin box that always agree with each other."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QAbstractSpinBox, QHBoxLayout, QLabel, QSlider, QSpinBox, QWidget

from .silent import set_value_silently

SPINBOX_WIDTH = 64


class AdjustRow(QWidget):
    """Label + slider + spin box that always show the same integer.

    Signals:
        value_changed(int): The user moved the slider or edited the number.
    """
    value_changed = Signal(int)

    def __init__(self, label: str, minimum: int, maximum: int, suffix: str = "", parent: QWidget | None = None):
        """Args:
            label: Text shown left of the slider.
            minimum: Lowest value.
            maximum: Highest value.
            suffix: Unit appended in the spin box, e.g. '%'.
            parent: Qt parent.
        """
        super().__init__(parent)
        self.label = QLabel(label, self)
        self.slider = QSlider(Qt.Orientation.Horizontal, self)
        self.spin = QSpinBox(self)
        self._build(minimum, maximum, suffix)
        self.slider.valueChanged.connect(self._from_slider)
        self.spin.valueChanged.connect(self._from_spin)

    def _build(self, minimum: int, maximum: int, suffix: str) -> None:
        self.slider.setRange(minimum, maximum)
        self.slider.setTracking(True)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval((maximum - minimum) // 4 or 1)
        self.spin.setRange(minimum, maximum)
        self.spin.setSuffix(suffix)
        self.spin.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)  # small, stacked arrows
        self.spin.setFixedWidth(SPINBOX_WIDTH)
        self.spin.setAlignment(Qt.AlignmentFlag.AlignRight)
        self.spin.setKeyboardTracking(False)  # emit once the number is typed, not per keystroke
        self.label.setMinimumWidth(70)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.label)
        layout.addWidget(self.slider, 1)
        layout.addWidget(self.spin)

    # --- API ----------------------------------------------------------------
    def value(self) -> int:
        """The current value."""
        return self.slider.value()

    def set_value(self, value: int) -> None:
        """Programmatic update: moves both controls without emitting value_changed."""
        set_value_silently(self.slider, value)
        set_value_silently(self.spin, value)

    # --- sync ---------------------------------------------------------------
    def _from_slider(self, value: int) -> None:
        set_value_silently(self.spin, value)
        self.value_changed.emit(value)

    def _from_spin(self, value: int) -> None:
        set_value_silently(self.slider, value)
        self.value_changed.emit(value)
