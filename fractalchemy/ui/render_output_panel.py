"""The Output group of the Render window: destination, format and encoding options.

The format combo and the file suffix are kept in step both ways: typing `picture.jpg` selects
JPEG, choosing TIFF renames to `.tif`. Options a format cannot use (16-bit, alpha, quality) are
greyed out, and formats whose encoder is not installed are listed but disabled with a hint.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLineEdit, QPushButton,
                               QSpinBox, QWidget)

from ..render.final_settings import FinalRenderSettings
from ..render.output import DEPTH_LABELS, FLOAT_DEPTH_LABELS, FORMATS, format_for_path, output_format, with_extension
from ..render.report import REPORT_FORMATS
from ..widgets.silent import blocked


class OutputPanel(QGroupBox):
    """Destination file, format and encoding options.

    Signals:
        changed(): Any edit.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Output", parent)
        self.path = QLineEdit(self)
        self.browse = QPushButton("Browse…", self)
        self.format_box = QComboBox(self)
        self.depth = QComboBox(self)
        self.quality = QSpinBox(self)
        self.lossless = QCheckBox("Lossless", self)
        self.transparent = QCheckBox("Transparent background", self)
        self.save_parameters = QCheckBox("Save parameters (.flame) beside the image", self)
        self.embed_parameters = QCheckBox("Embed parameters in the image", self)
        self.save_incomplete = QCheckBox("Save incomplete renders when stopped", self)
        self.save_details = QCheckBox("Save fractal and render details beside the image", self)
        self.details_format = QComboBox(self)
        self._build()

    def _build(self) -> None:
        self._build_controls()
        self._layout()
        self._connect()
        self._refresh_dependent()

    def _build_controls(self) -> None:
        self.path.setPlaceholderText("Where to save the image")
        for f in FORMATS:
            self.format_box.addItem(f.label if f.available else f"{f.label} — not installed", f.key)
            if not f.available:
                self.format_box.model().item(self.format_box.count() - 1).setEnabled(False)
        self._fill_depths(DEPTH_LABELS)
        self.depth.setToolTip("16-bit PNG / TIFF keep smooth gradients for later editing; OpenEXR stores half or full floats")
        self.quality.setRange(1, 100)
        self.quality.setSuffix(" %")
        self.quality.setToolTip("Compression quality for lossy formats")
        self.quality.setKeyboardTracking(False)
        self.transparent.setToolTip("Write the background as transparency instead of the background colour")
        self.embed_parameters.setToolTip("Store the flame's parameters in the file's metadata (PNG text, JPEG comment, TIFF description)")
        self.save_incomplete.setToolTip("Stopping early still writes the tiles finished so far (correctly exposed, grainier)")
        self.save_details.setToolTip("Write a report with every render setting, timing and statistic, and a full breakdown "
                                     "of the fractal (transforms, variations, palette, camera) next to the image")
        for key, label, _ext in REPORT_FORMATS:
            self.details_format.addItem(label, key)
        self.details_format.setToolTip("Markdown and HTML read nicely; the text form is one key<TAB>value per line for grep / awk / cut")

    def _layout(self) -> None:
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("File", _row(self.path, self.browse, stretch_first=True))
        form.addRow("Format", _row(self.format_box, self.depth, stretch_all=True))
        form.addRow("Encoding", _row(self.quality, self.lossless, self.transparent, trailing_stretch=True))
        form.addRow(self.save_parameters)
        form.addRow(self.embed_parameters)
        form.addRow(self.save_incomplete)
        form.addRow(_row(self.save_details, self.details_format, stretch_first=True))

    def _connect(self) -> None:
        self.browse.clicked.connect(self._browse)
        self.path.editingFinished.connect(self._on_path_edited)
        self.format_box.currentIndexChanged.connect(self._on_format_changed)
        for widget in (self.depth, self.details_format):
            widget.currentIndexChanged.connect(self._emit)
        self.quality.valueChanged.connect(self._emit)
        for box in (self.lossless, self.transparent, self.save_parameters, self.embed_parameters, self.save_incomplete,
                    self.save_details):
            box.toggled.connect(self._emit)

    # --- API ---------------------------------------------------------------------------------
    def apply(self, s: FinalRenderSettings) -> None:
        """Show the settings' values (no signal)."""
        with blocked(self.path, self.format_box, self.depth, self.quality, self.lossless, self.transparent,
                     self.save_parameters, self.embed_parameters, self.save_incomplete, self.save_details, self.details_format):
            self._show(s)
        self._refresh_dependent()

    def _show(self, s: FinalRenderSettings) -> None:
        self.path.setText(s.output_path)
        self.format_box.setCurrentIndex(max(0, self.format_box.findData(s.output_format)))
        self.depth.setCurrentIndex(max(0, self.depth.findData(s.depth)))
        self.quality.setValue(s.lossy_quality)
        self.lossless.setChecked(s.lossless)
        self.transparent.setChecked(s.transparent)
        self.save_parameters.setChecked(s.save_parameters)
        self.embed_parameters.setChecked(s.embed_parameters)
        self.save_incomplete.setChecked(s.save_incomplete)
        self.save_details.setChecked(s.save_details)
        self.details_format.setCurrentIndex(max(0, self.details_format.findData(s.details_format)))

    def read(self, s: FinalRenderSettings) -> FinalRenderSettings:
        """`s` with this panel's values."""
        return replace(s, output_path=self.path.text().strip(), output_format=self.format_box.currentData(),
                       depth=self.depth.currentData(), lossy_quality=self.quality.value(), lossless=self.lossless.isChecked(),
                       transparent=self.transparent.isChecked(), save_parameters=self.save_parameters.isChecked(),
                       embed_parameters=self.embed_parameters.isChecked(), save_incomplete=self.save_incomplete.isChecked(),
                       save_details=self.save_details.isChecked(), details_format=self.details_format.currentData())

    def set_path(self, path: str) -> None:
        """Set the destination (selects the matching format for its suffix, or fixes the suffix)."""
        self.path.setText(path)
        self._on_path_edited()

    # --- slots -------------------------------------------------------------------------------
    def _browse(self) -> None:
        fmt = output_format(self.format_box.currentData())
        filters = ";;".join(f"{f.label} (*{' *'.join(f.extensions)})" for f in FORMATS if f.available)
        current = f"{fmt.label} (*{' *'.join(fmt.extensions)})"
        start = self.path.text().strip() or str(Path.home())
        chosen, selected = QFileDialog.getSaveFileName(self, "Render to file", start, filters, current)
        if not chosen:
            return
        if format_for_path(chosen) is None:
            label = selected.split(" (")[0]
            picked = next((f for f in FORMATS if f.label == label), fmt)
            chosen = with_extension(chosen, picked)
        self.set_path(chosen)

    def _on_path_edited(self) -> None:
        fmt = format_for_path(self.path.text().strip())
        if fmt is not None and fmt.available and fmt.key != self.format_box.currentData():
            with blocked(self.format_box):
                self.format_box.setCurrentIndex(self.format_box.findData(fmt.key))
        elif fmt is None and self.path.text().strip():
            self.path.setText(with_extension(self.path.text().strip(), output_format(self.format_box.currentData())))
        self._emit()

    def _on_format_changed(self, _index: int) -> None:
        fmt = output_format(self.format_box.currentData())
        if self.path.text().strip():
            self.path.setText(with_extension(self.path.text().strip(), fmt))
        self._emit()

    def _fill_depths(self, labels: dict[int, str]) -> None:
        """Offer the depths a format family has, keeping the current choice when it still exists."""
        current = self.depth.currentData()
        with blocked(self.depth):
            self.depth.clear()
            for depth, label in labels.items():
                self.depth.addItem(label, depth)
            index = self.depth.findData(current)
            self.depth.setCurrentIndex(index if index >= 0 else (self.depth.count() - 1 if current and current > max(labels) else 0))

    def _refresh_dependent(self) -> None:
        fmt = output_format(self.format_box.currentData())
        labels = FLOAT_DEPTH_LABELS if fmt.float_channels else DEPTH_LABELS
        if [self.depth.itemData(i) for i in range(self.depth.count())] != list(labels):
            self._fill_depths(labels)
        self.depth.setEnabled(fmt.depth16)
        self.quality.setEnabled(fmt.lossy and not (fmt.lossless_option and self.lossless.isChecked()))
        self.lossless.setEnabled(fmt.lossless_option)
        self.transparent.setEnabled(fmt.alpha)
        self.embed_parameters.setEnabled(fmt.key in ("png", "jpeg", "tiff", "svg", "webp", "avif", "heif", "jxl", "exr"))
        self.details_format.setEnabled(self.save_details.isChecked())

    def _emit(self, *_args) -> None:
        self._refresh_dependent()
        self.changed.emit()


def _row(*widgets: QWidget, stretch_first: bool = False, stretch_all: bool = False, trailing_stretch: bool = False) -> QHBoxLayout:
    """Widgets side by side: optionally the first (or every one) takes the spare width, or the spare width trails."""
    row = QHBoxLayout()
    for i, widget in enumerate(widgets):
        row.addWidget(widget, 1 if stretch_all or (stretch_first and i == 0) else 0)
    if trailing_stretch:
        row.addStretch(1)
    return row


__all__ = ["OutputPanel"]
