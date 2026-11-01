"""The render buffer's size: locked to the viewport, or a custom width × height with an optional aspect lock.

FragM's *Buffer Dimensions* toolbar: `X` / `Y` spin boxes, a padlock keeping the aspect ratio, and a menu with
*Lock to window size* / *Custom size*. `BufferSize` is the rule (`getBufferSize`), `BufferSizeBar` the widgets.
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QLabel, QMenu, QPushButton, QSpinBox, QToolButton, QWidget

from ...widgets.icons import link_icon
from ...widgets.layouts import row
from ...widgets.silent import blocked

MAX_SIDE = 8192
MIN_SIDE = 16


class BufferSize:
    """The size rule.

    Attributes:
        locked_to_window: The buffer follows the viewport widget.
        width, height: The custom size.
        lock_aspect: Keep `width / height` when one side is edited.
    """

    def __init__(self, width: int = 1280, height: int = 720, locked_to_window: bool = True, lock_aspect: bool = False):
        self.width, self.height = width, height
        self.locked_to_window = locked_to_window
        self.lock_aspect = lock_aspect

    @property
    def aspect(self) -> float:
        return self.width / max(1, self.height)

    def resolve(self, window_width: int, window_height: int) -> tuple[int, int]:
        """The buffer size for a viewport of the given size."""
        if self.locked_to_window:
            return max(1, window_width), max(1, window_height)
        return max(1, self.width), max(1, self.height)

    def set_width(self, width: int) -> None:
        width = min(max(int(width), MIN_SIDE), MAX_SIDE)
        if self.lock_aspect:
            self.height = min(max(int(round(width / self.aspect)), MIN_SIDE), MAX_SIDE)
        self.width = width

    def set_height(self, height: int) -> None:
        height = min(max(int(height), MIN_SIDE), MAX_SIDE)
        if self.lock_aspect:
            self.width = min(max(int(round(height * self.aspect)), MIN_SIDE), MAX_SIDE)
        self.height = height


class BufferSizeBar(QWidget):
    """The toolbar widgets editing a `BufferSize`.

    Signals:
        changed(): Any of the three settings changed.
    """
    changed = Signal()

    def __init__(self, model: BufferSize, parent: QWidget | None = None):
        super().__init__(parent)
        self.model = model
        self.x_spin = QSpinBox(self)
        self.y_spin = QSpinBox(self)
        for spin in (self.x_spin, self.y_spin):
            spin.setRange(MIN_SIDE, MAX_SIDE)
            spin.setKeyboardTracking(False)
        self.lock_button = QToolButton(self)
        self.lock_button.setCheckable(True)
        self.lock_button.setAutoRaise(True)
        self.lock_button.setToolTip("Keep the aspect ratio when one side is edited")
        self.mode_button = QPushButton(self)
        menu = QMenu(self.mode_button)
        self.window_action = menu.addAction("Lock to window size")
        menu.addSeparator()
        self.custom_action = menu.addAction("Custom size")
        self.mode_button.setMenu(menu)
        menu.triggered.connect(self._on_mode)
        self.x_spin.valueChanged.connect(self._on_width)
        self.y_spin.valueChanged.connect(self._on_height)
        self.lock_button.toggled.connect(self._on_lock)
        layout = row(QLabel("Buffer size X:", self), self.x_spin, self.lock_button, QLabel("Y:", self), self.y_spin, self.mode_button)
        layout.setContentsMargins(4, 0, 4, 0)
        self.setLayout(layout)
        self.refresh()

    def refresh(self) -> None:
        """Show the model."""
        m = self.model
        with blocked(self.x_spin, self.y_spin, self.lock_button):
            self.x_spin.setValue(m.width)
            self.y_spin.setValue(m.height)
            self.lock_button.setChecked(m.lock_aspect)
        self.lock_button.setIcon(link_icon(m.lock_aspect))
        for widget in (self.x_spin, self.y_spin, self.lock_button):
            widget.setEnabled(not m.locked_to_window)
        self.mode_button.setText("Lock to window size" if m.locked_to_window else "Custom size")

    def show_window_size(self, width: int, height: int) -> None:
        """While locked to the window the boxes mirror the viewport's size (disabled)."""
        if self.model.locked_to_window:
            with blocked(self.x_spin, self.y_spin):
                self.x_spin.setValue(min(max(width, MIN_SIDE), MAX_SIDE))
                self.y_spin.setValue(min(max(height, MIN_SIDE), MAX_SIDE))

    def _on_width(self, value: int) -> None:
        self.model.set_width(value)
        self.refresh()
        self.changed.emit()

    def _on_height(self, value: int) -> None:
        self.model.set_height(value)
        self.refresh()
        self.changed.emit()

    def _on_lock(self, locked: bool) -> None:
        self.model.lock_aspect = locked
        self.refresh()
        self.changed.emit()

    def _on_mode(self, action) -> None:
        self.model.locked_to_window = action is self.window_action
        if not self.model.locked_to_window:
            self.model.width, self.model.height = self.x_spin.value(), self.y_spin.value()
        self.refresh()
        self.changed.emit()


__all__ = ["BufferSize", "BufferSizeBar", "MAX_SIDE", "MIN_SIDE"]
