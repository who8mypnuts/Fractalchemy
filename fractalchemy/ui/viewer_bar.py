"""The strip under the viewport: view zoom and preview detail on the left, output resolution on the right.

Zoom: an editable combo listing Fit and common percentages up to 200 %; anything typed is
accepted and capped at 300 % (or the fit value when zooming out). Detail: the fraction of the
screen resolution the preview is rendered at (½ and ¼ render 4× / 16× faster and are scaled up).
Resolution: common screen and print sizes, the flame's own size, and Custom… with width/height boxes.
"""

from __future__ import annotations

import re

from PySide6.QtCore import QSize, Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QSpinBox, QToolButton, QWidget

from ..fractal.scene import Flame

ZOOM_PRESETS = (0.25, 0.5, 0.75, 1.0, 1.5, 2.0)
RESOLUTIONS: tuple[tuple[str, int, int], ...] = (
    ("1:1  —  1080 × 1080", 1080, 1080),
    ("4:3  —  1024 × 768", 1024, 768),
    ("4:3  —  1600 × 1200", 1600, 1200),
    ("16:9  —  1280 × 720 (HD)", 1280, 720),
    ("16:9  —  1920 × 1080 (Full HD)", 1920, 1080),
    ("16:9  —  2560 × 1440 (QHD)", 2560, 1440),
    ("16:9  —  3840 × 2160 (4K)", 3840, 2160),
    ("16:10  —  1920 × 1200", 1920, 1200),
    ("21:9  —  3440 × 1440", 3440, 1440),
    ("Print 4 × 6 in @ 300 dpi  —  1800 × 1200", 1800, 1200),
    ("Print 5 × 7 in @ 300 dpi  —  2100 × 1500", 2100, 1500),
    ("Print 8 × 10 in @ 300 dpi  —  3000 × 2400", 3000, 2400),
    ("Print A4 @ 300 dpi  —  3508 × 2480", 3508, 2480),
    ("Print 11 × 14 in @ 300 dpi  —  4200 × 3300", 4200, 3300),
    ("Print A3 @ 300 dpi  —  4961 × 3508", 4961, 3508),
    ("Print 16 × 20 in @ 300 dpi  —  6000 × 4800", 6000, 4800),
)
FLAME_SIZE = "flame"
CUSTOM = "custom"
DETAIL_PRESETS: tuple[tuple[str, float], ...] = (("Full", 1.0), ("½", 0.5), ("¼", 0.25))
MAX_DIMENSION = 32768


class ViewerBar(QWidget):
    """Zoom and resolution controls for the viewport.

    Signals:
        zoom_requested(object): A zoom factor (float), or None for Fit.
        resolution_chosen(object): (width, height), or None to follow the flame's own size.
        detail_chosen(float): Render-resolution fraction for the preview (1, 0.5, 0.25).
    """
    zoom_requested = Signal(object)
    resolution_chosen = Signal(object)
    detail_chosen = Signal(float)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.zoom_box = QComboBox(self)
        self.fit_button = QToolButton(self)
        self.detail_box = QComboBox(self)
        self.resolution_box = QComboBox(self)
        self.width_box = QSpinBox(self)
        self.height_box = QSpinBox(self)
        self._fit_zoom = 1.0
        self._build()
        self._connect()

    def _build(self) -> None:
        self.zoom_box.setEditable(True)
        self.zoom_box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        self.zoom_box.addItem("Fit", None)
        for z in ZOOM_PRESETS:
            self.zoom_box.addItem(f"{z * 100:.0f} %", z)
        self.zoom_box.setMinimumContentsLength(7)
        self.zoom_box.setToolTip("View zoom: screen pixels per image pixel (does not change the fractal). Type any value up to 300 %.")
        self.fit_button.setText("Fit")
        self.fit_button.setToolTip("Show the whole image")
        self.fit_button.setAutoRaise(True)

        self.resolution_box.addItem("Flame size", FLAME_SIZE)
        for label, w, h in RESOLUTIONS:
            self.resolution_box.addItem(label, (w, h))
        self.resolution_box.addItem("Custom…", CUSTOM)
        self.resolution_box.setToolTip("Output resolution: sets the image's aspect ratio and framing (the window does not change)")
        self.resolution_box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        self.resolution_box.setMinimumContentsLength(12)   # the popup shows the full labels; the bar stays narrow
        for box in (self.width_box, self.height_box):
            box.setRange(16, MAX_DIMENSION)
            box.setKeyboardTracking(False)
            box.setAccelerated(True)
            box.setVisible(False)
        self.width_box.setToolTip("Custom width in pixels")
        self.height_box.setToolTip("Custom height in pixels")
        self.times = QLabel("×", self)
        self.times.setVisible(False)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(6, 2, 6, 2)
        layout.addWidget(QLabel("Zoom", self))
        layout.addWidget(self.zoom_box)
        layout.addWidget(self.fit_button)
        for label, fraction in DETAIL_PRESETS:
            self.detail_box.addItem(label, fraction)
        self.detail_box.setToolTip("Preview detail: render at this fraction of the screen resolution and scale up — "
                                   "½ is 4× faster, ¼ is 16× faster; the saved image size is not affected")
        layout.addSpacing(12)
        layout.addWidget(QLabel("Detail", self))
        layout.addWidget(self.detail_box)
        layout.addStretch(1)
        layout.addWidget(QLabel("Image size", self))
        layout.addWidget(self.resolution_box)
        layout.addWidget(self.width_box)
        layout.addWidget(self.times)
        layout.addWidget(self.height_box)

    def _connect(self) -> None:
        self.zoom_box.activated.connect(self._on_zoom_activated)
        self.zoom_box.lineEdit().editingFinished.connect(self._on_zoom_typed)
        self.fit_button.clicked.connect(lambda: self.zoom_requested.emit(None))
        self.resolution_box.activated.connect(self._on_resolution_activated)
        self.detail_box.activated.connect(lambda index: self.detail_chosen.emit(float(self.detail_box.itemData(index))))
        self.width_box.valueChanged.connect(self._on_custom_changed)
        self.height_box.valueChanged.connect(self._on_custom_changed)

    # --- detail ---------------------------------------------------------------------
    def detail(self) -> float:
        return float(self.detail_box.currentData())

    def select_detail(self, fraction: float) -> None:
        """Programmatically pick a detail fraction; emits like a user choice."""
        index = max(0, self.detail_box.findData(fraction))
        self.detail_box.setCurrentIndex(index)
        self.detail_chosen.emit(float(self.detail_box.itemData(index)))

    # --- zoom -------------------------------------------------------------------
    def show_zoom(self, zoom: float, fit_zoom: float) -> None:
        """Reflect the viewport's state (called on every view change)."""
        self._fit_zoom = fit_zoom
        self.zoom_box.blockSignals(True)
        self.zoom_box.setEditText(f"{zoom * 100:.0f} %")
        self.zoom_box.blockSignals(False)

    def _on_zoom_activated(self, index: int) -> None:
        self.zoom_requested.emit(self.zoom_box.itemData(index))

    def _on_zoom_typed(self) -> None:
        text = self.zoom_box.currentText().strip().lower()
        if text == "fit":
            self.zoom_requested.emit(None)
            return
        match = re.search(r"-?\d+(?:[.,]\d+)?", text)
        if match is None:
            self.show_zoom(self._current_zoom(), self._fit_zoom)
            return
        self.zoom_requested.emit(float(match.group().replace(",", ".")) / 100.0)

    def _current_zoom(self) -> float:
        match = re.search(r"\d+(?:[.,]\d+)?", self.zoom_box.currentText())
        return float(match.group().replace(",", ".")) / 100.0 if match else self._fit_zoom

    # --- resolution -----------------------------------------------------------------
    def show_flame(self, flame: Flame | None) -> None:
        """Update the 'Flame size' entry's label for the loaded flame."""
        label = "Flame size" if flame is None else f"Flame size  —  {flame.camera.width} × {flame.camera.height}"
        self.resolution_box.setItemText(0, label)

    def current_resolution(self) -> tuple[int, int] | None:
        data = self.resolution_box.currentData()
        if data == FLAME_SIZE:
            return None
        if data == CUSTOM:
            return (self.width_box.value(), self.height_box.value())
        return data

    def select_resolution(self, size: tuple[int, int] | None) -> None:
        """Programmatically pick a resolution (None = flame size); emits like a user choice."""
        if size is None:
            self.resolution_box.setCurrentIndex(0)
        else:
            index = next((i for i in range(self.resolution_box.count())
                          if self.resolution_box.itemData(i) == tuple(size)), -1)   # findData can't compare tuples
            if index < 0:
                index = self.resolution_box.count() - 1
                for box, value in ((self.width_box, size[0]), (self.height_box, size[1])):
                    box.blockSignals(True)
                    box.setValue(int(value))
                    box.blockSignals(False)
            self.resolution_box.setCurrentIndex(index)
        self._on_resolution_activated(self.resolution_box.currentIndex())

    def _on_resolution_activated(self, index: int) -> None:
        custom = self.resolution_box.itemData(index) == CUSTOM
        for widget in (self.width_box, self.times, self.height_box):
            widget.setVisible(custom)
        if custom and self.width_box.value() == self.width_box.minimum():
            self.width_box.setValue(1920)
            self.height_box.setValue(1080)
        self.resolution_chosen.emit(self.current_resolution())

    def _on_custom_changed(self, _value: int) -> None:
        if self.resolution_box.currentData() == CUSTOM:
            self.resolution_chosen.emit(self.current_resolution())

    def sizeHint(self) -> QSize:
        hint = super().sizeHint()
        return QSize(hint.width(), max(hint.height(), 30))


__all__ = ["ViewerBar", "RESOLUTIONS", "ZOOM_PRESETS"]
