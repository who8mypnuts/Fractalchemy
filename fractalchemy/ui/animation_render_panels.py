"""The Render Animation window's own panels: output folder / frames, the ffmpeg video, and the batch's progress.

The size and quality panels are the Render Image window's; these three cover what a batch needs
instead of one file: where the frames go and how they are named, which frames, the optional video,
and progress counted in frames.
"""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog, QFormLayout, QGroupBox, QLabel, QLineEdit, QPushButton, QSpinBox, QWidget

from ..animation.render import DEFAULT_CRF, VIDEO_FORMATS, AnimationRenderSettings, ffmpeg_command, ffmpeg_path, safe_stem, video_format
from ..animation.render_job import AnimationOutcome, AnimationProgress
from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE
from ..render.output import DEPTH_LABELS, output_format
from ..render.units import format_rate, format_seconds
from ..widgets.images import rgba_to_qimage
from ..widgets.layouts import row
from ..widgets.silent import blocked
from .render_output_panel import fill_depth_combo, fill_format_combo, sync_format_controls
from .render_progress import PROGRESS_STEPS, RenderProgressPanel

MAX_FRAME_NUMBER = 10 ** 9


class AnimationOutputPanel(QGroupBox):
    """Folder, base name, image format and options, frame range.

    Signals:
        changed(): Any edit.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Output", parent)
        self.folder = QLineEdit(self)
        self.browse = QPushButton("Browse…", self)
        self.base_name = QLineEdit(self)
        self.format_box = QComboBox(self)
        self.depth = QComboBox(self)
        self.quality = QSpinBox(self)
        self.lossless = QCheckBox("Lossless", self)
        self.transparent = QCheckBox("Transparent background", self)
        self.start_box = QSpinBox(self)
        self.end_box = QSpinBox(self)
        self.step_box = QSpinBox(self)
        self.skip_existing = QCheckBox("Skip frames whose file already exists (resume)", self)
        self.save_parameters = QCheckBox("Save parameters (.flame) beside every frame", self)
        self.embed_parameters = QCheckBox("Embed parameters in the frames", self)
        self.save_incomplete = QCheckBox("Keep a stopped frame (grainier) instead of dropping it", self)
        self.example = QLabel(self)
        self._total_frames = 1
        self._build_controls()
        self._layout()
        self._connect()
        self._refresh_dependent()

    def _build_controls(self) -> None:
        self.folder.setPlaceholderText("Folder the frames are written to")
        self.base_name.setPlaceholderText("frame")
        self.base_name.setToolTip("Frames are named <base>_0001.<ext>, <base>_0002.<ext>, …")
        fill_format_combo(self.format_box)
        fill_depth_combo(self.depth, DEPTH_LABELS)
        self.quality.setRange(1, 100)
        self.quality.setSuffix(" %")
        self.quality.setToolTip("Compression quality for lossy formats")
        for box in (self.start_box, self.end_box):
            box.setRange(0, MAX_FRAME_NUMBER)
        self.step_box.setRange(1, MAX_FRAME_NUMBER)
        for box in (self.quality, self.start_box, self.end_box, self.step_box):
            box.setKeyboardTracking(False)
        self.start_box.setToolTip("First frame to render")
        self.end_box.setToolTip("Last frame to render (inclusive)")
        self.step_box.setToolTip("Render every Nth frame (a quick look at the motion; the video needs 1)")
        self.example.setEnabled(False)

    def _layout(self) -> None:
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Folder", row(self.folder, self.browse, stretch_first=True))
        form.addRow("Base name", row(self.base_name, self.example, stretch_first=True))
        form.addRow("Format", row(self.format_box, self.depth, stretch_all=True))
        form.addRow("Encoding", row(self.quality, self.lossless, self.transparent, trailing_stretch=True))
        form.addRow("Frames", row(QLabel("from", self), self.start_box, QLabel("to", self), self.end_box, QLabel("every", self),
                                  self.step_box, trailing_stretch=True))
        for box in (self.skip_existing, self.save_parameters, self.embed_parameters, self.save_incomplete):
            form.addRow(box)

    def _connect(self) -> None:
        self.browse.clicked.connect(self._browse)
        self.folder.editingFinished.connect(self._emit)
        self.base_name.editingFinished.connect(self._emit)
        self.format_box.currentIndexChanged.connect(self._emit)
        self.depth.currentIndexChanged.connect(self._emit)
        for box in (self.quality, self.start_box, self.end_box, self.step_box):
            box.valueChanged.connect(self._emit)
        for box in (self.lossless, self.transparent, self.skip_existing, self.save_parameters, self.embed_parameters, self.save_incomplete):
            box.toggled.connect(self._emit)

    # --- API ------------------------------------------------------------------------------------------------------
    def set_base_name(self, name: str) -> None:
        """Set the frames' base name (refreshes the example file name)."""
        self.base_name.setText(name)
        self._refresh_dependent()

    def set_total_frames(self, total: int) -> None:
        """The animation's length: bounds the range boxes (an end at the last frame follows the length)."""
        at_end = self.end_box.value() >= self._total_frames - 1
        self._total_frames = max(1, total)
        with blocked(self.start_box, self.end_box):
            self.start_box.setMaximum(self._total_frames - 1)
            self.end_box.setMaximum(self._total_frames - 1)
            if at_end:
                self.end_box.setValue(self._total_frames - 1)
        self._refresh_dependent()

    def apply(self, s: AnimationRenderSettings, total_frames: int) -> None:
        """Show the settings' values (no signal)."""
        self._total_frames = max(1, total_frames)
        with blocked(self.folder, self.base_name, self.format_box, self.depth, self.quality, self.lossless, self.transparent,
                     self.start_box, self.end_box, self.step_box, self.skip_existing, self.save_parameters, self.embed_parameters,
                     self.save_incomplete):
            self.folder.setText(s.folder)
            self.base_name.setText(s.base_name)
            self.format_box.setCurrentIndex(max(0, self.format_box.findData(s.image.output_format)))
            self.depth.setCurrentIndex(max(0, self.depth.findData(s.image.depth)))
            self.quality.setValue(s.image.lossy_quality)
            self.lossless.setChecked(s.image.lossless)
            self.transparent.setChecked(s.image.transparent)
            self.start_box.setMaximum(self._total_frames - 1)
            self.end_box.setMaximum(self._total_frames - 1)
            self.start_box.setValue(max(0, min(s.start_frame, self._total_frames - 1)))
            self.end_box.setValue(self._total_frames - 1 if s.end_frame < 0 else min(s.end_frame, self._total_frames - 1))
            self.step_box.setValue(max(1, s.step))
            self.skip_existing.setChecked(s.skip_existing)
            self.save_parameters.setChecked(s.image.save_parameters)
            self.embed_parameters.setChecked(s.image.embed_parameters)
            self.save_incomplete.setChecked(s.image.save_incomplete)
        self._refresh_dependent()

    def read(self, s: AnimationRenderSettings) -> AnimationRenderSettings:
        """`s` with this panel's values."""
        image = replace(s.image, output_format=self.format_box.currentData(), depth=self.depth.currentData(),
                        lossy_quality=self.quality.value(), lossless=self.lossless.isChecked(), transparent=self.transparent.isChecked(),
                        save_parameters=self.save_parameters.isChecked(), embed_parameters=self.embed_parameters.isChecked(),
                        save_incomplete=self.save_incomplete.isChecked(), output_path="")
        end = self.end_box.value()
        return replace(s, image=image, folder=self.folder.text().strip(), base_name=self.base_name.text().strip() or "frame",
                       start_frame=self.start_box.value(), end_frame=-1 if end >= self._total_frames - 1 else end,
                       step=self.step_box.value(), skip_existing=self.skip_existing.isChecked())

    # --- slots ----------------------------------------------------------------------------------------------------
    def _browse(self) -> None:
        start = self.folder.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Render the frames into", start)
        if chosen:
            self.folder.setText(chosen)
            self._emit()

    def _refresh_dependent(self) -> None:
        fmt = output_format(self.format_box.currentData())
        sync_format_controls(fmt, self.depth, self.quality, self.lossless, self.transparent, self.embed_parameters)
        digits = max(4, len(str(max(0, self._total_frames - 1))))
        self.example.setText(f"→ {safe_stem(self.base_name.text()) or 'frame'}_{'0' * (digits - 1)}1{fmt.extension}")

    def _emit(self, *_args) -> None:
        self._refresh_dependent()
        self.changed.emit()


class VideoPanel(QGroupBox):
    """The ffmpeg video options.

    Signals:
        changed(): Any edit.
    """
    changed = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__("Video", parent)
        self.enable = QCheckBox("Make a video with ffmpeg after the frames", self)
        self.format_box = QComboBox(self)
        self.crf = QSpinBox(self)
        self.name = QLineEdit(self)
        self.keep_frames = QCheckBox("Keep the frame images", self)
        self.status = QLabel(self)
        self.command = QLabel(self)
        self._build()

    def _build(self) -> None:
        path = ffmpeg_path()
        self.status.setText(f"ffmpeg found: {path}" if path else "ffmpeg was not found on this system — install it to make videos")
        self.status.setWordWrap(True)
        self.status.setEnabled(False)
        self.enable.setEnabled(path is not None)
        self.enable.setToolTip("Encode the rendered frames into a video in the same folder")
        for fmt in VIDEO_FORMATS:
            self.format_box.addItem(fmt.label, fmt.key)
        self.crf.setRange(0, 63)
        self.crf.setValue(DEFAULT_CRF)
        self.crf.setKeyboardTracking(False)
        self.crf.setToolTip("Constant rate factor: lower is better and bigger (H.264: 18 is visually lossless, 23 default; VP9: 31)")
        self.name.setPlaceholderText("same as the base name")
        self.name.setToolTip("The video's file name (without extension); the frames' base name when empty")
        self.keep_frames.setChecked(True)
        self.keep_frames.setToolTip("Off: the frame images are deleted once the video is written")
        self.command.setWordWrap(True)
        self.command.setEnabled(False)
        self.command.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow(self.enable)
        form.addRow("Format", self.format_box)
        form.addRow("Quality (CRF)", row(self.crf, self.keep_frames, trailing_stretch=True))
        form.addRow("Name", self.name)
        form.addRow(self.status)
        form.addRow(self.command)
        self.enable.toggled.connect(self._emit)
        self.format_box.currentIndexChanged.connect(self._emit)
        self.crf.valueChanged.connect(self._emit)
        self.name.editingFinished.connect(self._emit)
        self.keep_frames.toggled.connect(self._emit)
        self._refresh_dependent()

    def apply(self, s: AnimationRenderSettings) -> None:
        """Show the settings' values (no signal)."""
        with blocked(self.enable, self.format_box, self.crf, self.name, self.keep_frames):
            self.enable.setChecked(s.video and ffmpeg_path() is not None)
            self.format_box.setCurrentIndex(max(0, self.format_box.findData(s.video_format)))
            self.crf.setValue(s.video_quality)
            self.name.setText(s.video_name)
            self.keep_frames.setChecked(s.keep_frames)
        self._refresh_dependent()

    def read(self, s: AnimationRenderSettings) -> AnimationRenderSettings:
        """`s` with this panel's values."""
        return replace(s, video=self.enable.isChecked(), video_format=self.format_box.currentData(), video_quality=self.crf.value(),
                       video_name=self.name.text().strip(), keep_frames=self.keep_frames.isChecked())

    def show_command(self, s: AnimationRenderSettings, fps: int, total_frames: int, first_frame: int) -> None:
        """Show the ffmpeg command line that will run (empty when the video is off)."""
        if not s.video:
            self.command.setText("")
            return
        self.command.setText("ffmpeg " + " ".join(_quote(a) for a in ffmpeg_command(s, fps, total_frames, first_frame, "ffmpeg")[1:]))

    def _refresh_dependent(self) -> None:
        on = self.enable.isChecked() and self.enable.isEnabled()
        for w in (self.format_box, self.name, self.keep_frames):
            w.setEnabled(on)
        self.crf.setEnabled(on and video_format(self.format_box.currentData()).has_crf)

    def _emit(self, *_args) -> None:
        self._refresh_dependent()
        self.changed.emit()


class AnimationProgressPanel(RenderProgressPanel):
    """The Render window's progress panel counting frames instead of tiles, with the batch's outcome."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.tiles_caption.setText("Frame")

    def show_progress(self, p: AnimationProgress) -> None:   # type: ignore[override]
        """Update everything from a batch progress report."""
        self.bar.setValue(int(p.fraction * PROGRESS_STEPS))
        self.phase.setText(p.phase if p.phase in (PHASE_DONE, PHASE_CANCELLED) else f"{p.phase}…")
        self.tiles.setText(f"{p.frame}  ({p.index} of {p.count})" if p.count else "—")
        self.elapsed.setText(format_seconds(p.elapsed))
        self.remaining.setText(format_seconds(p.remaining) if p.remaining is not None else "—")
        fp = p.frame_progress
        self.rate.setText(format_rate(fp.rate) if fp is not None and fp.rate > 0 else "—")
        self.rate.setToolTip(p.engine)
        if p.preview is not None:
            self.preview.set_image(QPixmap.fromImage(rgba_to_qimage(p.preview)))

    def show_outcome(self, outcome: AnimationOutcome, folder: Path | None = None) -> None:   # type: ignore[override]
        """Describe a finished batch, with links to the folder and the video."""
        count = len(outcome.frames)
        line = (f"{'Finished' if outcome.complete else 'Stopped early'} after {format_seconds(outcome.seconds)}: "
                f"{count} frame{'s' if count != 1 else ''} written" + (f", {len(outcome.skipped)} skipped" if outcome.skipped else "")
                + (f"  ·  {outcome.samples / 1e9:.2f} G samples" if outcome.samples else "") + (f"  ·  {outcome.engine}" if outcome.engine else ""))
        if folder is not None:
            line += f"<br>Folder: {self.file_link(folder, str(folder))}"
        if outcome.video is not None:
            line += f"<br>Video: {self.file_link(outcome.video)}"
        notes = [n for n in outcome.notes if n]
        if notes:
            line += "<br><i>" + "; ".join(notes) + "</i>"
        self.result.setText(line)


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg or ";" in arg or "[" in arg else arg


__all__ = ["AnimationOutputPanel", "VideoPanel", "AnimationProgressPanel"]
