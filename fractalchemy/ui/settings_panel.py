"""The collapsible panel on the right of the viewport: an *Info* tab describing the loaded fractal and an
*Image* tab with the preview effort, camera, 3D camera and colouring controls.

The preview effort (and the tab you were on) persist in QSettings so they are there next time; the
camera / colouring controls edit the flame itself (see `ImagePanel`).
"""

from __future__ import annotations

from PySide6.QtCore import QSettings, Signal
from PySide6.QtWidgets import QTabWidget, QVBoxLayout, QWidget

from .. import config
from .fractal_document import FractalDocument
from .image_panel import ImagePanel
from .info_panel import InfoPanel

PASSES_KEY = "preview/passes"
QUALITY_KEY = "preview/quality"
TAB_KEY = "panel/tab"


class SettingsPanel(QWidget):
    """Tabbed panel: *Info* (facts about the fractal), *Image* (preview effort, camera, 3D, colouring).

    Signals:
        render_settings_changed(int, float): (passes, quality) whenever either preview box changes.
    """
    render_settings_changed = Signal(int, float)

    def __init__(self, parent: QWidget | None = None, settings: QSettings | None = None):
        super().__init__(parent)
        self._settings = settings
        self.tabs = QTabWidget(self)
        self.info = InfoPanel(self)
        self.image = ImagePanel(self)
        self.passes_box = self.image.passes_box
        self.quality_box = self.image.quality_box
        self._build()
        self._load()
        self.image.render_settings_changed.connect(self._changed)
        self.tabs.currentChanged.connect(self._tab_changed)
        self.setMinimumWidth(180)

    def attach_settings(self, settings: QSettings | None) -> None:
        """Persist to / load from `settings` (promoted widgets are built with just a parent)."""
        self._settings = settings
        self._load()

    def bind(self, document: FractalDocument) -> None:
        """Let the Image tab edit and follow `document`."""
        self.image.bind(document)

    def _build(self) -> None:
        self.tabs.addTab(self.info, "Info")
        self.tabs.addTab(self.image, "Image")
        self.tabs.setTabToolTip(0, "What the loaded fractal is made of")
        self.tabs.setTabToolTip(1, "Preview effort, camera, 3D camera and colouring")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.addWidget(self.tabs)

    # --- values --------------------------------------------------------------
    @property
    def passes(self) -> int:
        return self.image.passes

    @property
    def quality(self) -> float:
        return self.image.quality

    def set_values(self, passes: int, quality: float) -> None:
        """Set both boxes; emits once if anything changed."""
        if self.image.set_preview(passes, quality):
            self._changed()

    def _load(self) -> None:
        passes, quality = config.PREVIEW_PASSES, config.PREVIEW_QUALITY
        tab = 0
        if self._settings is not None:
            try:
                passes = int(self._settings.value(PASSES_KEY, passes))
                quality = float(self._settings.value(QUALITY_KEY, quality))
                tab = int(self._settings.value(TAB_KEY, 0))
            except (TypeError, ValueError):
                pass
        self.image.set_preview(passes, quality)
        if 0 <= tab < self.tabs.count():
            self.tabs.setCurrentIndex(tab)

    def _tab_changed(self, index: int) -> None:
        if self._settings is not None:
            self._settings.setValue(TAB_KEY, index)

    def _changed(self, *_args) -> None:
        if self._settings is not None:
            self._settings.setValue(PASSES_KEY, self.passes)
            self._settings.setValue(QUALITY_KEY, self.quality)
        self.render_settings_changed.emit(self.passes, self.quality)
