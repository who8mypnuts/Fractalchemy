"""The collapsible panel on the right of the viewport: tabs of options, starting with render settings.

Values persist in QSettings so the preview quality you chose is there next time.
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QDoubleSpinBox, QFormLayout, QLabel, QSpinBox, QTabWidget, QVBoxLayout, QWidget

from .. import config

PASSES_KEY = "preview/passes"
QUALITY_KEY = "preview/quality"
PASSES_RANGE = (1, 50)
QUALITY_RANGE = (0.5, 500.0)


class SettingsPanel(QWidget):
    """Tabbed options panel.

    Signals:
        render_settings_changed(int, float): (passes, quality) whenever either box changes.
    """
    render_settings_changed = Signal(int, float)

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None):
        super().__init__(parent)
        self._settings = settings
        self.tabs = QTabWidget(self)
        self.passes_box = QSpinBox(self)
        self.quality_box = QDoubleSpinBox(self)
        self._build()
        self._load()
        self.passes_box.valueChanged.connect(self._changed)
        self.quality_box.valueChanged.connect(self._changed)
        self.setMinimumWidth(180)

    def attach_settings(self, settings: QSettings | None) -> None:
        """Persist to / load from `settings` (promoted widgets are built with just a parent)."""
        self._settings = settings
        self._load()

    def _build(self) -> None:
        self.passes_box.setRange(*PASSES_RANGE)
        self.passes_box.setToolTip("Progressive passes per preview render; the image is refreshed after each")
        self.quality_box.setRange(*QUALITY_RANGE)
        self.quality_box.setDecimals(1)
        self.quality_box.setSingleStep(1.0)
        self.quality_box.setToolTip("Samples per pixel over the whole preview (Apophysis 'quality')")
        for box in (self.passes_box, self.quality_box):
            box.setKeyboardTracking(False)
        render = QWidget(self)
        form = QFormLayout(render)
        self.preview_heading = QLabel("Fractal Preview", render)
        font = self.preview_heading.font()
        font.setBold(True)
        self.preview_heading.setFont(font)
        form.addRow(self.preview_heading)
        form.addRow("Passes", self.passes_box)
        form.addRow("Quality", self.quality_box)
        note = QLabel("Preview only. Final render settings will have their own tab.", render)
        note.setWordWrap(True)
        note.setEnabled(False)
        form.addRow(note)
        self.tabs.addTab(render, "Render")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tabs)

    # --- values --------------------------------------------------------------
    @property
    def passes(self) -> int:
        """Progressive passes per preview render."""
        return self.passes_box.value()

    @property
    def quality(self) -> float:
        """Samples per pixel over the whole preview."""
        return self.quality_box.value()

    def set_values(self, passes: int, quality: float) -> None:
        """Set both boxes; emits once if anything changed."""
        self.passes_box.blockSignals(True)
        self.quality_box.blockSignals(True)
        before = (self.passes, self.quality)
        self.passes_box.setValue(int(passes))
        self.quality_box.setValue(float(quality))
        self.passes_box.blockSignals(False)
        self.quality_box.blockSignals(False)
        if (self.passes, self.quality) != before:
            self._changed()

    def _load(self) -> None:
        passes, quality = config.PREVIEW_PASSES, config.PREVIEW_QUALITY
        if self._settings is not None:
            try:
                passes = int(self._settings.value(PASSES_KEY, passes))
                quality = float(self._settings.value(QUALITY_KEY, quality))
            except (TypeError, ValueError):
                pass
        self.passes_box.setValue(passes)
        self.quality_box.setValue(quality)

    def _changed(self, *_args) -> None:
        if self._settings is not None:
            self._settings.setValue(PASSES_KEY, self.passes)
            self._settings.setValue(QUALITY_KEY, self.quality)
        self.render_settings_changed.emit(self.passes, self.quality)
