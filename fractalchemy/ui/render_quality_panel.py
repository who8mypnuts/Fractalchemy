"""The Quality group of the Render window: density, oversample, filter, denoiser, engine, memory.

`apply(settings)` shows a `FinalRenderSettings`, `read(settings)` returns one with the panel's
values, and `changed` fires on every edit. Choosing a filter resets the radius to that filter's
textbook width, since the radius means different things for a Gaussian and a Lanczos window.
"""

from __future__ import annotations

from dataclasses import replace

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout, QLabel, QSlider, QSpinBox, QWidget

from ..render.denoise import DENOISERS
from ..render.filters import FILTERS, filter_kind
from ..render.final_settings import DENSITY_PRESETS, ENGINES, MAX_OVERSAMPLE, FinalRenderSettings
from ..widgets.silent import blocked


class QualityPanel(QGroupBox):
    """Density, oversample, reconstruction filter, denoiser, engine and memory.

    Signals:
        changed(): Any edit.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Quality", parent)
        self.density = QComboBox(self)
        self.oversample = QSpinBox(self)
        self.filter_box = QComboBox(self)
        self.radius = QDoubleSpinBox(self)
        self.denoiser = QComboBox(self)
        self.strength = QSlider(Qt.Orientation.Horizontal, self)
        self.strength_value = QLabel(self)
        self.de_max = QDoubleSpinBox(self)
        self.de_min = QDoubleSpinBox(self)
        self.de_curve = QDoubleSpinBox(self)
        self.engine = QComboBox(self)
        self.threads = QSpinBox(self)
        self.memory = QSpinBox(self)
        self.gpu_memory = QSpinBox(self)
        self._build()

    def _build(self) -> None:
        self._build_sampling_controls()
        self._build_denoise_controls()
        self._build_engine_controls()
        for box in (self.oversample, self.radius, self.de_max, self.de_min, self.de_curve, self.threads, self.memory, self.gpu_memory):
            box.setKeyboardTracking(False)
        self._layout()
        self._connect()

    def _build_sampling_controls(self) -> None:
        self.density.setEditable(True)
        for q in DENSITY_PRESETS:
            self.density.addItem(f"{q:,}", q)
        self.density.setToolTip("Samples per pixel (Apophysis 'density'). Higher = less grain, longer render")
        self.oversample.setRange(1, MAX_OVERSAMPLE)
        self.oversample.setToolTip("Buckets per pixel along each axis; the image is rendered that much larger and filtered down")
        for f in FILTERS:
            self.filter_box.addItem(f.label, f.key)
            self.filter_box.setItemData(self.filter_box.count() - 1, f.description, Qt.ItemDataRole.ToolTipRole)
        self.filter_box.setToolTip("How the oversampled buckets are blended into pixels (anti-aliasing)")
        self.radius.setRange(0.0, 5.0)
        self.radius.setSingleStep(0.1)
        self.radius.setDecimals(2)
        self.radius.setToolTip("Filter radius in output pixels (Apophysis 'filter radius'); larger = softer")

    def _build_denoise_controls(self) -> None:
        for d in DENOISERS:
            self.denoiser.addItem(d.label if d.available else f"{d.label} — not installed", d.key)
            self.denoiser.setItemData(self.denoiser.count() - 1, d.description + ("" if d.available else f" ({d.hint})"),
                                      Qt.ItemDataRole.ToolTipRole)
            if not d.available:
                self.denoiser.model().item(self.denoiser.count() - 1).setEnabled(False)
        self.denoiser.setToolTip("Clean up grain after rendering, so a lower density can do")
        self.strength.setRange(0, 100)
        self.strength.setToolTip("Denoiser strength")
        self.strength_value.setMinimumWidth(28)
        for box, rng, tip in ((self.de_max, (0.0, 50.0), "Largest blur radius, for the sparsest areas (flam3 'estimator')"),
                              (self.de_min, (0.0, 10.0), "Smallest blur radius, for dense areas (flam3 'estimator minimum')"),
                              (self.de_curve, (0.01, 2.0), "How fast the radius shrinks with density (flam3 'estimator curve')")):
            box.setRange(*rng)
            box.setDecimals(2)
            box.setSingleStep(0.1)
            box.setToolTip(tip)

    def _build_engine_controls(self) -> None:
        for key, label in ENGINES:
            self.engine.addItem(label, key)
        self.engine.setToolTip("GPU: fast, 32-bit floats. CPU: every core as a worker process, 64-bit floats (deep zooms, exactness)")
        self.threads.setRange(0, 256)
        self.threads.setSpecialValueText("all cores")
        self.threads.setToolTip("CPU worker processes (0 = every core)")
        _memory_box(self.memory, "auto (half of RAM)", 1024, "Histogram memory budget (no fixed ceiling: default is half of "
                    "installed RAM); bigger images are rendered in tiles to stay within it")
        _memory_box(self.gpu_memory, "auto (1 GB)", 512,
                    "Largest tile texture on the GPU; raise it on cards with plenty of memory to render in fewer tiles")

    def _layout(self) -> None:
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Density", self.density)
        form.addRow("Oversample", self.oversample)
        row = QHBoxLayout()
        row.addWidget(self.filter_box, 1)
        row.addWidget(QLabel("Radius", self))
        row.addWidget(self.radius)
        form.addRow("Filter", row)
        form.addRow("Denoiser", self.denoiser)
        row = QHBoxLayout()
        row.addWidget(self.strength, 1)
        row.addWidget(self.strength_value)
        form.addRow("Strength", row)
        self.de_row = QWidget(self)
        de = QHBoxLayout(self.de_row)
        de.setContentsMargins(0, 0, 0, 0)
        for label, box in (("Max radius", self.de_max), ("Min radius", self.de_min), ("Curve", self.de_curve)):
            de.addWidget(QLabel(label, self.de_row))
            de.addWidget(box, 1)
        form.addRow("", self.de_row)
        form.addRow("Engine", self.engine)
        form.addRow("Workers", self.threads)
        row = QHBoxLayout()
        row.addWidget(self.memory, 1)
        row.addWidget(QLabel("GPU", self))
        row.addWidget(self.gpu_memory, 1)
        form.addRow("Memory limit", row)

    def _connect(self) -> None:
        self.density.currentTextChanged.connect(self._emit)
        self.oversample.valueChanged.connect(self._emit)
        self.filter_box.currentIndexChanged.connect(self._on_filter_changed)
        self.radius.valueChanged.connect(self._emit)
        self.denoiser.currentIndexChanged.connect(self._on_denoiser_changed)
        self.strength.valueChanged.connect(self._on_strength)
        for box in (self.de_max, self.de_min, self.de_curve, self.threads, self.memory, self.gpu_memory):
            box.valueChanged.connect(self._emit)
        self.engine.currentIndexChanged.connect(self._emit)

    # --- API ---------------------------------------------------------------------------------
    def apply(self, s: FinalRenderSettings) -> None:
        """Show the settings' values (no signal)."""
        with blocked(self, self.density, self.oversample, self.filter_box, self.radius, self.denoiser, self.strength,
                     self.de_max, self.de_min, self.de_curve, self.engine, self.threads, self.memory, self.gpu_memory):
            self.density.setEditText(f"{s.quality:g}")
            self.oversample.setValue(s.oversample)
            self.filter_box.setCurrentIndex(max(0, self.filter_box.findData(s.filter_kind)))
            self.radius.setValue(s.filter_radius)
            self.denoiser.setCurrentIndex(max(0, self.denoiser.findData(s.denoiser)))
            self.strength.setValue(int(s.denoise_strength))
            self.de_max.setValue(s.de_max_radius)
            self.de_min.setValue(s.de_min_radius)
            self.de_curve.setValue(s.de_curve)
            self.engine.setCurrentIndex(max(0, self.engine.findData(s.engine)))
            self.threads.setValue(s.cpu_threads)
            self.memory.setValue(s.memory_limit_mb)
            self.gpu_memory.setValue(s.gpu_memory_mb)
        self._refresh_dependent()

    def read(self, s: FinalRenderSettings) -> FinalRenderSettings:
        """`s` with this panel's values."""
        return replace(s, quality=self.quality(), oversample=self.oversample.value(), filter_kind=self.filter_box.currentData(),
                       filter_radius=self.radius.value(), denoiser=self.denoiser.currentData(),
                       denoise_strength=float(self.strength.value()), de_max_radius=self.de_max.value(),
                       de_min_radius=self.de_min.value(), de_curve=self.de_curve.value(), engine=self.engine.currentData(),
                       cpu_threads=self.threads.value(), memory_limit_mb=self.memory.value(), gpu_memory_mb=self.gpu_memory.value())

    def quality(self) -> float:
        """The density typed or chosen (falls back to the first preset when unparsable)."""
        text = self.density.currentText().replace(",", "").replace(" ", "")
        try:
            return max(0.01, float(text))
        except ValueError:
            return float(DENSITY_PRESETS[0])

    # --- slots -------------------------------------------------------------------------------
    def _on_filter_changed(self, _index: int) -> None:
        self.radius.setValue(filter_kind(self.filter_box.currentData()).default_radius)   # the filter's textbook width
        self._emit()

    def _on_denoiser_changed(self, _index: int) -> None:
        self._refresh_dependent()
        self._emit()

    def _on_strength(self, value: int) -> None:
        self.strength_value.setText(str(value))
        self._emit()

    def _refresh_dependent(self) -> None:
        key = self.denoiser.currentData()
        self.de_row.setVisible(key == "density")
        image_space = key not in ("none", "density")
        self.strength.setEnabled(image_space)
        self.strength_value.setEnabled(image_space)
        self.strength_value.setText(str(self.strength.value()))
        self.threads.setEnabled(self.engine.currentData() != "gpu")
        self.gpu_memory.setEnabled(self.engine.currentData() != "cpu")

    def _emit(self, *_args) -> None:
        self._refresh_dependent()
        self.changed.emit()


def _memory_box(box: QSpinBox, special: str, step: int, tip: str) -> None:
    """Configure a megabyte spin box whose 0 means 'automatic'."""
    box.setRange(0, 1 << 24)
    box.setSuffix(" MB")
    box.setSpecialValueText(special)
    box.setSingleStep(step)
    box.setToolTip(tip)


__all__ = ["QualityPanel"]
