"""The Grading dock: exposure, tone mapping, gamma, contrast, saturation, hue, vignette and invert on the displayed image.

Every change goes to `FragDocument.set_grading`, which re-runs only the display pass — the accumulation is kept,
so the sliders respond instantly even on a heavy fragment. The settings travel with the `.fafrag` and apply to
hi-res renders as well. *Reset* returns to the identity (no grading at all, the stage is skipped).
"""

from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ...fragments.grading import TONEMAPS, Grading
from ...widgets.float_row import FloatRow
from ...widgets.silent import blocked
from .document import FragDocument

TONEMAP_LABELS = {"none": "None (clamp)", "reinhard": "Reinhard", "filmic": "Filmic (Hable)", "aces": "ACES"}


class GradingPanel(QWidget):
    """The grading controls bound to the current document (see the module docstring)."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.document: FragDocument | None = None
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        form = QFormLayout()
        self.tonemap = QComboBox()
        for key in TONEMAPS:
            self.tonemap.addItem(TONEMAP_LABELS[key], key)
        self.tonemap.currentIndexChanged.connect(lambda _i: self._changed())
        form.addRow("Tone mapping", self.tonemap)
        layout.addLayout(form)
        self.rows = {
            "exposure": FloatRow("Exposure (stops)", -6.0, 6.0, 2, 0.1),
            "gamma": FloatRow("Gamma", 0.2, 4.0, 2, 0.05),
            "contrast": FloatRow("Contrast", 0.0, 3.0, 2, 0.05),
            "saturation": FloatRow("Saturation", 0.0, 3.0, 2, 0.05),
            "hue": FloatRow("Hue shift", -180.0, 180.0, 1, 1.0, "°"),
            "vignette": FloatRow("Vignette", 0.0, 1.0, 2, 0.05),
        }
        for row in self.rows.values():
            row.value_changed.connect(lambda _v: self._changed())
            layout.addWidget(row)
        bottom = QHBoxLayout()
        self.invert = QCheckBox("Invert")
        self.invert.toggled.connect(lambda _on: self._changed())
        self.reset = QPushButton("Reset")
        self.reset.clicked.connect(lambda: self.show_grading(Grading(), announce=True))
        self.state = QLabel("")
        bottom.addWidget(self.invert)
        bottom.addStretch(1)
        bottom.addWidget(self.state)
        bottom.addWidget(self.reset)
        layout.addLayout(bottom)
        layout.addStretch(1)
        self.show_grading(Grading())

    def set_document(self, document: FragDocument | None) -> None:
        self.document = document
        self.setEnabled(document is not None)
        self.show_grading(document.grading if document is not None else Grading())

    def show_grading(self, grading: Grading, announce: bool = False) -> None:
        """Put `grading` into the controls (and into the document when `announce`)."""
        with blocked(self.tonemap, self.invert, *self.rows.values()):
            self.tonemap.setCurrentIndex(max(0, self.tonemap.findData(grading.tonemap)))
            for name, row in self.rows.items():
                row.set_value(getattr(grading, name))
            self.invert.setChecked(grading.invert)
        self.state.setText("" if grading.is_identity else "active")
        if announce and self.document is not None:
            self.document.set_grading(grading)

    def grading(self) -> Grading:
        """The settings as shown."""
        return Grading(tonemap=self.tonemap.currentData(), invert=self.invert.isChecked(),
                       **{name: row.value() for name, row in self.rows.items()})

    def _changed(self) -> None:
        grading = self.grading()
        self.state.setText("" if grading.is_identity else "active")
        if self.document is not None:
            self.document.set_grading(grading)


__all__ = ["GradingPanel"]
