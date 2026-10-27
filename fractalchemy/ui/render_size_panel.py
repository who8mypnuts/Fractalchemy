"""The Size group of the Render window: presets, width × height, aspect lock, swap.

The first preset is the viewer's current image size ("Preview size"), so the window always
offers to render exactly what the preview frames. With the link on, typing one dimension
updates the other from the ratio captured when the link was engaged (or the last preset).
"""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QGridLayout, QGroupBox, QLabel, QSpinBox, QToolButton, QWidget

from ..render.final_settings import MAX_DIMENSION
from ..render.units import aspect_text
from ..widgets.icons import link_icon
from ..widgets.silent import set_value_silently
from .viewer_bar import RESOLUTIONS

PREVIEW_SIZE, CUSTOM_SIZE = "preview", "custom"


class SizePanel(QGroupBox):
    """Output size: presets (starting with the preview's current size), width × height, aspect lock, swap.

    Signals:
        size_changed(int, int): Whenever the size changes.
    """
    size_changed = Signal(int, int)

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Size", parent)
        self.presets = QComboBox(self)
        self.width_box = QSpinBox(self)
        self.height_box = QSpinBox(self)
        self.link = QToolButton(self)
        self.swap = QToolButton(self)
        self.aspect = QLabel(self)
        self._ratio = 16 / 9
        self._preview_size = (1920, 1080)
        self._build()

    def _build(self) -> None:
        self.presets.addItem("Preview size", PREVIEW_SIZE)
        for label, w, h in RESOLUTIONS:
            self.presets.addItem(label, (w, h))
        self.presets.addItem("Custom…", CUSTOM_SIZE)
        self.presets.setToolTip("Common screen and print sizes; 'Preview size' follows the image size chosen under the viewer")
        for box in (self.width_box, self.height_box):
            box.setRange(1, MAX_DIMENSION)
            box.setKeyboardTracking(False)
            box.setAccelerated(True)
            box.setSuffix(" px")
            box.setMinimumWidth(110)
        self.link.setCheckable(True)
        self.link.setChecked(True)
        self.link.setIcon(link_icon(True))
        self.link.setToolTip("Aspect ratio linked: typing a width updates the height and vice versa (click to unlink)")
        self.swap.setText("⇄")
        self.swap.setToolTip("Swap width and height (portrait / landscape)")
        self.swap.setAutoRaise(True)
        grid = QGridLayout(self)
        grid.addWidget(self.presets, 0, 0, 1, 5)
        grid.addWidget(QLabel("Width", self), 1, 0)
        grid.addWidget(self.width_box, 1, 1)
        grid.addWidget(self.link, 1, 2)
        grid.addWidget(QLabel("Height", self), 1, 3)
        grid.addWidget(self.height_box, 1, 4)
        grid.addWidget(self.swap, 1, 5)
        grid.addWidget(self.aspect, 2, 0, 1, 6)
        self.presets.activated.connect(self._on_preset)
        self.width_box.valueChanged.connect(self._on_width)
        self.height_box.valueChanged.connect(self._on_height)
        self.link.toggled.connect(self._on_link)
        self.swap.clicked.connect(self._on_swap)
        self._refresh_aspect()

    # --- API ---------------------------------------------------------------------------------
    def size(self) -> tuple[int, int]:
        """(width, height)."""
        return self.width_box.value(), self.height_box.value()

    def set_size(self, width: int, height: int) -> None:
        """Show a size (re-captures the locked ratio); emits if it changed."""
        before = self.size()
        set_value_silently(self.width_box, max(1, int(width)))
        set_value_silently(self.height_box, max(1, int(height)))
        self._capture_ratio()
        self._select_matching_preset()
        self._refresh_aspect()
        if self.size() != before:
            self.size_changed.emit(*self.size())

    def set_preview_size(self, width: int, height: int) -> None:
        """Tell the panel the viewer's current image size; applies it if that preset is selected."""
        self._preview_size = (max(1, int(width)), max(1, int(height)))
        self.presets.setItemText(0, f"Preview size  —  {width} × {height}")
        if self.presets.currentData() == PREVIEW_SIZE:
            self.set_size(*self._preview_size)
        else:
            self._select_matching_preset()

    @property
    def linked(self) -> bool:
        """True while the aspect ratio is locked."""
        return self.link.isChecked()

    # --- slots -------------------------------------------------------------------------------
    def preset_index(self, size: tuple[int, int]) -> int:
        """Row of the preset for `size`, or -1 (QComboBox.findData cannot compare tuples)."""
        return next((i for i in range(1, self.presets.count() - 1) if tuple(self.presets.itemData(i)) == tuple(size)), -1)

    def choose_preset(self, index: int) -> None:
        """Select a preset row as the user would."""
        self.presets.setCurrentIndex(index)
        self._on_preset(index)

    def _on_preset(self, index: int) -> None:
        data = self.presets.itemData(index)
        if data == PREVIEW_SIZE:
            self.set_size(*self._preview_size)
        elif isinstance(data, (tuple, list)):
            self.set_size(*data)

    def _on_width(self, width: int) -> None:
        if self.linked:
            set_value_silently(self.height_box, max(1, int(round(width / self._ratio))))
        self._after_edit()

    def _on_height(self, height: int) -> None:
        if self.linked:
            set_value_silently(self.width_box, max(1, int(round(height * self._ratio))))
        self._after_edit()

    def _on_link(self, linked: bool) -> None:
        self.link.setIcon(link_icon(linked))
        self.link.setToolTip("Aspect ratio linked: typing a width updates the height and vice versa (click to unlink)"
                             if linked else "Width and height are independent (click to link the aspect ratio)")
        if linked:
            self._capture_ratio()

    def _on_swap(self) -> None:
        w, h = self.size()
        self.set_size(h, w)

    def _after_edit(self) -> None:
        if not self.linked:
            self._capture_ratio()
        self._select_matching_preset()
        self._refresh_aspect()
        self.size_changed.emit(*self.size())

    def _capture_ratio(self) -> None:
        w, h = self.size()
        self._ratio = w / max(1, h)

    def _select_matching_preset(self) -> None:
        size = self.size()
        if size == self._preview_size:
            index = 0
        else:
            found = self.preset_index(size)
            index = found if found >= 0 else self.presets.count() - 1
        self.presets.setCurrentIndex(index)

    def _refresh_aspect(self) -> None:
        w, h = self.size()
        self.aspect.setText(f"{w:,} × {h:,} px  ·  {w * h / 1e6:.1f} Mpx  ·  {aspect_text(w, h)}")


__all__ = ["SizePanel", "PREVIEW_SIZE", "CUSTOM_SIZE"]
