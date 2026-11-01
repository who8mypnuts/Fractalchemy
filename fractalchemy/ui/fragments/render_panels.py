"""The option panels of the Render Fragment window — FragM's `OutputDialog` as groups of controls.

**Tiles**: tile width / height (with an aspect link and *From viewport*), tiles per side, padding, the image size, the
region of the frame to render (Ctrl+drag on the viewport sets it). **Quality**: subframes. **View**: stereo pairs and
the 360° panorama. **Animation**: render a frame range at the clock's fps. **Output**: file, format, depth,
embedded parameters, a `.fragparams` beside the image, the fragment saved with its settings (and includes) into a
`<name> Files` folder, unique names, EXR depth-to-alpha, save incomplete renders. Each panel shows and reads a
`FragFinalSettings` and announces edits with `changed`.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton,
                               QSlider, QSpinBox, QToolButton, QWidget)
from PySide6.QtCore import Qt

from ...animation.render import VIDEO_FORMATS
from ...fragments.animation import AnimationSettings
from ...fragments.render_settings import FragFinalSettings
from ...fragments.stereo import STEREO_LABELS, STEREO_MODES
from ...render.output import DEPTH_LABELS, FLOAT_DEPTH_LABELS, format_for_path, output_format, with_extension
from ...render.report import REPORT_FORMATS
from ...widgets.icons import link_icon
from ...widgets.layouts import row
from ...widgets.silent import blocked
from ..render_output_panel import fill_depth_combo, fill_format_combo
from .buffer_size import MAX_SIDE

MAX_TILES = 32


class TilesPanel(QGroupBox):
    """Tile size, tile count, padding and the resulting image size.

    Signals:
        changed(): Any value edited.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Size", parent)
        self.width_spin, self.height_spin = QSpinBox(self), QSpinBox(self)
        for spin in (self.width_spin, self.height_spin):
            spin.setRange(16, MAX_SIDE)
            spin.setKeyboardTracking(False)
        self.link = QToolButton(self)
        self.link.setCheckable(True)
        self.link.setAutoRaise(True)
        self.link.setToolTip("Keep the tile's aspect ratio")
        self.from_viewport = QPushButton("From viewport", self)
        self.from_viewport.setToolTip("Take the viewport's buffer size as the tile size")
        self.tiles_slider = QSlider(Qt.Orientation.Horizontal, self)
        self.tiles_slider.setRange(1, MAX_TILES)
        self.tiles_label = QLabel(self)
        self.padding_spin = QDoubleSpinBox(self)
        self.padding_spin.setRange(0.0, 1.0)
        self.padding_spin.setSingleStep(0.05)
        self.padding_spin.setDecimals(2)
        self.padding_spin.setToolTip("Extra view per tile (overlap cropped away when assembling); fixes edge artefacts of blurs")
        self.size_label = QLabel(self)
        self.region_label = QLabel("whole frame", self)
        self.region_clear = QPushButton("Clear", self)
        self.region_clear.setToolTip("Render the whole frame again (Ctrl+drag on the viewport chooses a region)")
        self.region_clear.setEnabled(False)
        self._region: tuple | None = None
        self._ratio = 16 / 9
        form = QFormLayout(self)
        form.addRow("Tile width", row(self.width_spin, self.link, QLabel("height", self), self.height_spin, self.from_viewport))
        form.addRow("Tiles per side", row(self.tiles_slider, self.tiles_label))
        form.addRow("Padding", self.padding_spin)
        form.addRow("Region", row(self.region_label, self.region_clear))
        form.addRow("Image", self.size_label)
        self.region_clear.clicked.connect(lambda: self.set_region(None))
        self.width_spin.valueChanged.connect(self._on_width)
        self.height_spin.valueChanged.connect(self._on_height)
        self.link.toggled.connect(lambda on: (self.link.setIcon(link_icon(on)), self._capture_ratio()))
        self.tiles_slider.valueChanged.connect(lambda _v: self._emit())
        self.padding_spin.valueChanged.connect(lambda _v: self._emit())
        self.link.setIcon(link_icon(False))

    def apply(self, s: FragFinalSettings) -> None:
        with blocked(self.width_spin, self.height_spin, self.tiles_slider, self.padding_spin):
            self.width_spin.setValue(s.tile_width)
            self.height_spin.setValue(s.tile_height)
            self.tiles_slider.setValue(s.tiles)
            self.padding_spin.setValue(s.padding)
        self._region = s.region
        self._show_region()
        self._capture_ratio()
        self.refresh(s)

    def read(self, s: FragFinalSettings) -> FragFinalSettings:
        return s.with_(tile_width=self.width_spin.value(), tile_height=self.height_spin.value(), tiles=self.tiles_slider.value(),
                       padding=self.padding_spin.value(), region=self._region)

    def set_region(self, region: tuple | None, frame_size: tuple[int, int] | None = None) -> None:
        """A region of the frame (fractions), or None for the whole frame; with `frame_size` the tile takes the region's aspect."""
        self._region = tuple(region) if region else None
        if self._region is not None and frame_size is not None:
            width = self.width_spin.value()
            aspect = (self._region[2] * frame_size[0]) / max(1e-6, self._region[3] * frame_size[1])
            with blocked(self.height_spin):
                self.height_spin.setValue(max(16, int(round(width / aspect))))
            self._capture_ratio()
        self._show_region()
        self._emit()

    def _show_region(self) -> None:
        r = self._region
        self.region_label.setText("whole frame" if r is None else f"x {r[0] * 100:.0f}%  y {r[1] * 100:.0f}%  ·  {r[2] * 100:.0f}% × {r[3] * 100:.0f}%")
        self.region_clear.setEnabled(r is not None)

    def refresh(self, s: FragFinalSettings) -> None:
        width, height = s.image_size
        self.tiles_label.setText(f"{s.tiles} × {s.tiles} = {s.tile_count} tiles")
        self.size_label.setText(f"{width} × {height} pixels")

    def set_tile_size(self, width: int, height: int) -> None:
        with blocked(self.width_spin, self.height_spin):
            self.width_spin.setValue(width)
            self.height_spin.setValue(height)
        self._capture_ratio()
        self._emit()

    def _capture_ratio(self) -> None:
        self._ratio = self.width_spin.value() / max(1, self.height_spin.value())

    def _on_width(self, value: int) -> None:
        if self.link.isChecked():
            with blocked(self.height_spin):
                self.height_spin.setValue(max(16, int(round(value / self._ratio))))
        self._emit()

    def _on_height(self, value: int) -> None:
        if self.link.isChecked():
            with blocked(self.width_spin):
                self.width_spin.setValue(max(16, int(round(value * self._ratio))))
        self._emit()

    def _emit(self) -> None:
        self.changed.emit()


class QualityPanel(QGroupBox):
    """Subframes per tile."""
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Quality", parent)
        self.subframes_spin = QSpinBox(self)
        self.subframes_spin.setRange(1, 65535)
        self.subframes_spin.setToolTip("Subframes accumulated per tile (more = less noise, longer)")
        form = QFormLayout(self)
        form.addRow("Subframes", self.subframes_spin)
        self.subframes_spin.valueChanged.connect(lambda _v: self.changed.emit())

    def apply(self, s: FragFinalSettings) -> None:
        with blocked(self.subframes_spin):
            self.subframes_spin.setValue(s.subframes)

    def read(self, s: FragFinalSettings) -> FragFinalSettings:
        return s.with_(subframes=self.subframes_spin.value())


class ViewPanel(QGroupBox):
    """Stereo pairs and the 360° panorama."""
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("View", parent)
        self.stereo = QComboBox(self)
        for mode in STEREO_MODES:
            self.stereo.addItem(STEREO_LABELS[mode], mode)
        self.stereo.setToolTip("Two renders with the eye shifted left / right, composited for glasses or a 3D display (3D fragments)")
        self.separation = QDoubleSpinBox(self)
        self.separation.setRange(0.001, 1.0)
        self.separation.setSingleStep(0.005)
        self.separation.setDecimals(3)
        self.separation.setToolTip("Eye distance as a fraction of the eye–target distance (0.03 feels natural)")
        self.panorama = QCheckBox("360° equirectangular panorama (2:1)", self)
        self.panorama.setToolTip("Render the fragment's EquiRectangular view: the whole sphere around the eye, for VR viewers and sky maps")
        form = QFormLayout(self)
        form.addRow("Stereo", row(self.stereo, QLabel("separation", self), self.separation))
        form.addRow(self.panorama)
        self.stereo.currentIndexChanged.connect(lambda _i: self.changed.emit())
        self.separation.valueChanged.connect(lambda _v: self.changed.emit())
        self.panorama.toggled.connect(lambda _on: self.changed.emit())

    def apply(self, s: FragFinalSettings) -> None:
        with blocked(self.stereo, self.separation, self.panorama):
            self.stereo.setCurrentIndex(max(0, self.stereo.findData(s.stereo)))
            self.separation.setValue(s.eye_separation)
            self.panorama.setChecked(s.panorama)

    def read(self, s: FragFinalSettings) -> FragFinalSettings:
        return s.with_(stereo=str(self.stereo.currentData()), eye_separation=self.separation.value(), panorama=self.panorama.isChecked())


class AnimationPanel(QGroupBox):
    """A frame range instead of a still (the fps and length come from the window's clock)."""
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Animation", parent)
        self.setCheckable(True)
        self.start_spin, self.end_spin = QSpinBox(self), QSpinBox(self)
        for spin in (self.start_spin, self.end_spin):
            spin.setRange(0, 10_000_000)
        self.clock_label = QLabel(self)
        self.preview_check = QCheckBox("Preview only (show the frame instead of writing it)", self)
        self.video_check = QCheckBox("Make a video with ffmpeg afterwards", self)
        self.video_combo = QComboBox(self)
        for fmt in VIDEO_FORMATS:
            self.video_combo.addItem(fmt.label, fmt.key)
        self.crf_spin = QSpinBox(self)
        self.crf_spin.setRange(0, 63)
        self.crf_spin.setToolTip("Constant rate factor: lower is better (18 is visually lossless for H.264)")
        self.keep_check = QCheckBox("Keep the frame images", self)
        self.video_label = QLabel(self)
        self.video_label.setWordWrap(True)
        form = QFormLayout(self)
        form.addRow("Start frame", self.start_spin)
        form.addRow("End frame", self.end_spin)
        form.addRow("Clock", self.clock_label)
        form.addRow("", self.preview_check)
        form.addRow("", self.video_check)
        form.addRow("Video", row(self.video_combo, QLabel("CRF", self), self.crf_spin, self.keep_check, stretch_first=True))
        form.addRow("", self.video_label)
        self.toggled.connect(lambda _on: self.changed.emit())
        self.start_spin.valueChanged.connect(lambda _v: self.changed.emit())
        self.end_spin.valueChanged.connect(lambda _v: self.changed.emit())
        self.preview_check.toggled.connect(lambda _on: self.changed.emit())
        for widget in (self.video_check, self.keep_check):
            widget.toggled.connect(lambda _on: self.changed.emit())
        self.video_combo.currentIndexChanged.connect(lambda _i: self.changed.emit())
        self.crf_spin.valueChanged.connect(lambda _v: self.changed.emit())

    def apply(self, s: FragFinalSettings, clock: AnimationSettings) -> None:
        with blocked(self, self.start_spin, self.end_spin, self.preview_check, self.video_check, self.video_combo, self.crf_spin, self.keep_check):
            self.setChecked(s.animation)
            self.start_spin.setValue(s.start_frame)
            self.end_spin.setValue(s.end_frame)
            self.preview_check.setChecked(s.preview)
            self.video_check.setChecked(s.video)
            self.video_combo.setCurrentIndex(max(0, self.video_combo.findData(s.video_format)))
            self.crf_spin.setValue(s.video_quality)
            self.keep_check.setChecked(s.keep_frames)
        self.show_clock(clock)
        self.show_video_state(s)

    def show_video_state(self, s: FragFinalSettings) -> None:
        """What the video needs, and the ffmpeg command line it will run."""
        problems = s.video_problems() if s.video else []
        if s.video and not problems:
            self.video_label.setText(" ".join(s.ffmpeg_command(25, 100, 0)))
        else:
            self.video_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>" if problems else "")
        for widget in (self.video_combo, self.crf_spin, self.keep_check):
            widget.setEnabled(s.video)

    def show_clock(self, clock: AnimationSettings) -> None:
        self.clock_label.setText(f"{clock.fps} fps · {clock.length} s · {clock.frames} frames (the Fragments window's time toolbar)")
        self.end_spin.setMaximum(max(1, clock.frames))

    def read(self, s: FragFinalSettings) -> FragFinalSettings:
        return s.with_(animation=self.isChecked(), start_frame=self.start_spin.value(), end_frame=self.end_spin.value(),
                       preview=self.preview_check.isChecked(), video=self.video_check.isChecked(),
                       video_format=str(self.video_combo.currentData() or "mp4"), video_quality=self.crf_spin.value(),
                       keep_frames=self.keep_check.isChecked())


class FragOutputPanel(QGroupBox):
    """File, format, depth and what travels with the image."""
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Output", parent)
        self.path_edit = QLineEdit(self)
        self.browse = QPushButton("Browse…", self)
        self.format_combo = QComboBox(self)
        fill_format_combo(self.format_combo)
        self.depth_combo = QComboBox(self)
        fill_depth_combo(self.depth_combo, DEPTH_LABELS)
        self.embed_check = QCheckBox("Embed the parameters in the image (FragM reads them back)", self)
        self.params_check = QCheckBox("Write a .fragparams file beside the image", self)
        self.fragment_check = QCheckBox("Save the fragment with its settings in a '<name> Files' folder", self)
        self.includes_check = QCheckBox("… with the included files", self)
        self.unique_check = QCheckBox("Unique file names (time stamp)", self)
        self.depth_alpha_check = QCheckBox("OpenEXR: depth buffer as the Z channel (DepthToAlpha)", self)
        self.incomplete_check = QCheckBox("Keep the frames written when stopped", self)
        self.report_check = QCheckBox("Save the fragment and render details (report)", self)
        self.report_check.setToolTip("A report beside the image: the fragment, includes, preset, every parameter, the tile plan, timings per tile, the machine")
        self.report_combo = QComboBox(self)
        for key, label, _ext in REPORT_FORMATS:
            self.report_combo.addItem(label, key)
        self.report_combo.currentIndexChanged.connect(lambda _i: self.changed.emit())
        form = QFormLayout(self)
        form.addRow("File", row(self.path_edit, self.browse, stretch_first=True))
        form.addRow("Format", row(self.format_combo, self.depth_combo))
        for check in (self.embed_check, self.params_check, self.fragment_check, self.includes_check, self.unique_check,
                      self.depth_alpha_check, self.incomplete_check):
            form.addRow("", check)
            check.toggled.connect(lambda _on: self.changed.emit())
        form.addRow("", row(self.report_check, self.report_combo, stretch_first=True))
        self.report_check.toggled.connect(lambda on: (self.report_combo.setEnabled(on), self.changed.emit()))
        self.report_combo.setEnabled(False)
        self.path_edit.editingFinished.connect(self._on_path_edited)
        self.browse.clicked.connect(self._browse)
        self.format_combo.currentIndexChanged.connect(self._on_format)
        self.depth_combo.currentIndexChanged.connect(lambda _i: self.changed.emit())

    def apply(self, s: FragFinalSettings) -> None:
        with blocked(self.path_edit, self.format_combo, self.depth_combo, self.embed_check, self.params_check, self.fragment_check,
                     self.includes_check, self.unique_check, self.depth_alpha_check, self.incomplete_check):
            self.path_edit.setText(s.output_path)
            index = self.format_combo.findData(s.output_format)
            self.format_combo.setCurrentIndex(max(0, index))
            self._refresh_depths(s.output_format)
            depth_index = self.depth_combo.findData(s.depth)
            self.depth_combo.setCurrentIndex(max(0, depth_index))
            self.embed_check.setChecked(s.embed_parameters)
            self.params_check.setChecked(s.save_parameters)
            self.fragment_check.setChecked(s.save_fragment)
            self.includes_check.setChecked(s.include_files)
            self.unique_check.setChecked(s.unique_name)
            self.depth_alpha_check.setChecked(s.depth_to_alpha)
            self.incomplete_check.setChecked(s.save_incomplete)
        with blocked(self.report_check, self.report_combo):
            self.report_check.setChecked(s.report)
            self.report_combo.setCurrentIndex(max(0, self.report_combo.findData(s.report_format)))
            self.report_combo.setEnabled(s.report)
        self._sync()

    def read(self, s: FragFinalSettings) -> FragFinalSettings:
        return s.with_(output_path=self.path_edit.text().strip(), output_format=str(self.format_combo.currentData() or "png"),
                       depth=int(self.depth_combo.currentData() or 8), embed_parameters=self.embed_check.isChecked(),
                       save_parameters=self.params_check.isChecked(), save_fragment=self.fragment_check.isChecked(),
                       include_files=self.includes_check.isChecked(), unique_name=self.unique_check.isChecked(),
                       depth_to_alpha=self.depth_alpha_check.isChecked(), save_incomplete=self.incomplete_check.isChecked(),
                       report=self.report_check.isChecked(), report_format=str(self.report_combo.currentData() or "md"))

    def set_path(self, path: str) -> None:
        with blocked(self.path_edit):
            self.path_edit.setText(path)

    def _refresh_depths(self, key: str) -> None:
        fmt = output_format(key)
        labels = FLOAT_DEPTH_LABELS if fmt.float_channels else DEPTH_LABELS
        if [self.depth_combo.itemData(i) for i in range(self.depth_combo.count())] != list(labels):
            fill_depth_combo(self.depth_combo, labels)

    def _sync(self) -> None:
        fmt = output_format(str(self.format_combo.currentData() or "png"))
        self.depth_combo.setEnabled(fmt.depth16)
        self.depth_alpha_check.setEnabled(fmt.key == "exr")
        self.includes_check.setEnabled(self.fragment_check.isChecked())

    def _on_format(self, _index: int) -> None:
        key = str(self.format_combo.currentData() or "png")
        self._refresh_depths(key)
        path = self.path_edit.text().strip()
        if path:
            with blocked(self.path_edit):
                self.path_edit.setText(with_extension(path, output_format(key)))
        self._sync()
        self.changed.emit()

    def _on_path_edited(self) -> None:
        fmt = format_for_path(self.path_edit.text().strip())
        if fmt is not None and fmt.key != self.format_combo.currentData():
            with blocked(self.format_combo):
                self.format_combo.setCurrentIndex(self.format_combo.findData(fmt.key))
            self._refresh_depths(fmt.key)
            self._sync()
        self.changed.emit()

    def _browse(self) -> None:
        start = self.path_edit.text().strip() or str(Path.home() / "fragment.png")
        fmt = output_format(str(self.format_combo.currentData() or "png"))
        chosen, _filter = QFileDialog.getSaveFileName(self, "Render to", start, f"{fmt.label} (*{' *'.join(fmt.extensions)});;All files (*)")
        if chosen:
            self.path_edit.setText(with_extension(chosen, fmt))
            self._on_path_edited()


__all__ = ["ViewPanel", "TilesPanel", "QualityPanel", "AnimationPanel", "FragOutputPanel"]
