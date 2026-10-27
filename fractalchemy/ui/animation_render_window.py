"""The Render Animation window: the Render Image window's size / quality panels, a folder instead of a file, frames, ffmpeg.

Opened from the Animation window's *Render Animation…*. A non-modal tool window: the batch runs on
its own thread (`AnimationRenderJob`) with a snapshot of the animation, so the Animation and main
windows stay usable. Settings persist in QSettings and travel with the `.faanim` file (the last
render settings are saved in it, so a render can be repeated later).

* **Output** — the folder, the frames' base name (`name_0001.png`), the image format with its options,
  the frame range and step, *skip existing frames* (resume a stopped batch), parameters beside / inside
  each frame.
* **Video** — *Make a video with ffmpeg* when ffmpeg is installed: the container / codec, the quality
  (CRF), the video's name, and whether to keep the frames afterwards. The video lands in the same folder.
"""

from __future__ import annotations

import json
import time
from dataclasses import replace
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFileDialog, QFormLayout, QGridLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QMainWindow, QMessageBox, QProgressBar, QPushButton, QScrollArea, QSpinBox, QSplitter,
                               QVBoxLayout, QWidget)

from ..animation.render import (DEFAULT_CRF, VIDEO_FORMATS, AnimationRenderSettings, ffmpeg_command, ffmpeg_path,
                                safe_stem)
from ..animation.render_job import PHASE_ENCODE, AnimationOutcome, AnimationProgress, AnimationRenderJob
from ..render.estimate import RenderEstimate, engine_kind
from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE
from ..render.final_settings import FinalRenderSettings, plan_tiles
from ..render.gpu_engine import gpu_available
from ..render.output import DEPTH_LABELS, FLOAT_DEPTH_LABELS, FORMATS, output_format
from ..render.units import format_rate, format_seconds
from ..widgets.icons import editor_icon
from ..widgets.images import rgba_to_qimage
from ..widgets.silent import blocked
from .animation_document import AnimationDocument
from .render_progress import _PreviewLabel
from .render_quality_panel import QualityPanel
from .render_size_panel import SizePanel

WINDOW_TITLE = "Render Animation"
SETTINGS_KEY = "animation_render/settings"
FOLDER_KEY = "animation_render/folder"
PROGRESS_STEPS = 10000
RateHint = Callable[[], tuple[str, float] | None]


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
        self._build()

    def _build(self) -> None:
        self.folder.setPlaceholderText("Folder the frames are written to")
        self.base_name.setPlaceholderText("frame")
        self.base_name.setToolTip("Frames are named <base>_0001.<ext>, <base>_0002.<ext>, …")
        for f in FORMATS:
            self.format_box.addItem(f.label if f.available else f"{f.label} — not installed", f.key)
            if not f.available:
                self.format_box.model().item(self.format_box.count() - 1).setEnabled(False)
        self._fill_depths(DEPTH_LABELS)
        self.quality.setRange(1, 100)
        self.quality.setSuffix(" %")
        self.quality.setToolTip("Compression quality for lossy formats")
        self.quality.setKeyboardTracking(False)
        for box in (self.start_box, self.end_box):
            box.setRange(0, 10 ** 9)
            box.setKeyboardTracking(False)
        self.step_box.setRange(1, 10 ** 6)
        self.step_box.setKeyboardTracking(False)
        self.start_box.setToolTip("First frame to render")
        self.end_box.setToolTip("Last frame to render (inclusive)")
        self.step_box.setToolTip("Render every Nth frame (a quick look at the motion; the video needs 1)")
        self.example.setEnabled(False)
        form = QFormLayout(self)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        form.addRow("Folder", _row(self.folder, self.browse, stretch_first=True))
        form.addRow("Base name", _row(self.base_name, self.example, stretch_first=True))
        form.addRow("Format", _row(self.format_box, self.depth, stretch_all=True))
        form.addRow("Encoding", _row(self.quality, self.lossless, self.transparent, trailing_stretch=True))
        form.addRow("Frames", _row(QLabel("from", self), self.start_box, QLabel("to", self), self.end_box, QLabel("every", self), self.step_box,
                                   trailing_stretch=True))
        for box in (self.skip_existing, self.save_parameters, self.embed_parameters, self.save_incomplete):
            form.addRow(box)
        self.browse.clicked.connect(self._browse)
        self.folder.editingFinished.connect(self._emit)
        self.base_name.editingFinished.connect(self._emit)
        self.format_box.currentIndexChanged.connect(self._emit)
        self.depth.currentIndexChanged.connect(self._emit)
        for box in (self.quality, self.start_box, self.end_box, self.step_box):
            box.valueChanged.connect(self._emit)
        for box in (self.lossless, self.transparent, self.skip_existing, self.save_parameters, self.embed_parameters, self.save_incomplete):
            box.toggled.connect(self._emit)
        self._refresh_dependent()

    def set_base_name(self, name: str) -> None:
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

    def _browse(self) -> None:
        start = self.folder.text().strip() or str(Path.home())
        chosen = QFileDialog.getExistingDirectory(self, "Render the frames into", start)
        if chosen:
            self.folder.setText(chosen)
            self._emit()

    def _fill_depths(self, labels: dict[int, str]) -> None:
        current = self.depth.currentData()
        with blocked(self.depth):
            self.depth.clear()
            for depth, label in labels.items():
                self.depth.addItem(label, depth)
            index = self.depth.findData(current)
            self.depth.setCurrentIndex(index if index >= 0 else 0)

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
        for key, label, _suffix, _codec, _quality in VIDEO_FORMATS:
            self.format_box.addItem(label, key)
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
        form.addRow("Quality (CRF)", _row(self.crf, self.keep_frames, trailing_stretch=True))
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
        with blocked(self.enable, self.format_box, self.crf, self.name, self.keep_frames):
            self.enable.setChecked(s.video and ffmpeg_path() is not None)
            self.format_box.setCurrentIndex(max(0, self.format_box.findData(s.video_format)))
            self.crf.setValue(s.video_quality)
            self.name.setText(s.video_name)
            self.keep_frames.setChecked(s.keep_frames)
        self._refresh_dependent()

    def read(self, s: AnimationRenderSettings) -> AnimationRenderSettings:
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
        quality_kind = VIDEO_FORMATS[max(0, self.format_box.currentIndex())][4]
        for w in (self.format_box, self.name, self.keep_frames):
            w.setEnabled(on)
        self.crf.setEnabled(on and quality_kind == "crf")

    def _emit(self, *_args) -> None:
        self._refresh_dependent()
        self.changed.emit()


class AnimationProgressPanel(QWidget):
    """Preview of the latest frame, the batch's progress bar, facts and the outcome."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.preview = _PreviewLabel(self)
        self.bar = QProgressBar(self)
        self.phase = QLabel(self)
        self.frame = QLabel(self)
        self.elapsed = QLabel(self)
        self.remaining = QLabel(self)
        self.rate = QLabel(self)
        self.result = QLabel(self)
        self.bar.setRange(0, PROGRESS_STEPS)
        self.bar.setFormat("%p %")
        self.result.setWordWrap(True)
        self.result.setOpenExternalLinks(False)
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.result.linkActivated.connect(lambda link: QDesktopServices.openUrl(QUrl.fromLocalFile(link.removeprefix("file:"))))
        grid = QGridLayout()
        grid.addWidget(QLabel("Frame", self), 0, 0)
        grid.addWidget(self.frame, 0, 1)
        grid.addWidget(QLabel("Speed", self), 0, 2)
        grid.addWidget(self.rate, 0, 3)
        grid.addWidget(QLabel("Elapsed", self), 1, 0)
        grid.addWidget(self.elapsed, 1, 1)
        grid.addWidget(QLabel("Remaining", self), 1, 2)
        grid.addWidget(self.remaining, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.phase)
        layout.addWidget(self.bar)
        layout.addLayout(grid)
        layout.addWidget(self.result)
        self.show_idle("")

    def show_idle(self, estimate: str) -> None:
        self.bar.setValue(0)
        self.phase.setText("Ready")
        self.frame.setText("—")
        self.elapsed.setText("—")
        self.remaining.setText(estimate or "—")
        self.rate.setText("—")

    def show_progress(self, p: AnimationProgress) -> None:
        self.bar.setValue(int(p.fraction * PROGRESS_STEPS))
        self.phase.setText(p.phase if p.phase in (PHASE_DONE, PHASE_CANCELLED) else f"{p.phase}…")
        self.frame.setText(f"{p.frame}  ({p.index} of {p.count})" if p.count else "—")
        self.elapsed.setText(format_seconds(p.elapsed))
        self.remaining.setText(format_seconds(p.remaining) if p.remaining is not None else "—")
        fp = p.frame_progress
        self.rate.setText(format_rate(fp.rate) if fp is not None and fp.rate > 0 else "—")
        self.rate.setToolTip(p.engine)
        if p.preview is not None:
            self.preview.set_image(QPixmap.fromImage(rgba_to_qimage(p.preview)))

    def show_elapsed(self, seconds: float) -> None:
        self.elapsed.setText(format_seconds(seconds))

    def show_paused(self, paused: bool) -> None:
        text = self.phase.text().replace(" (paused)", "")
        self.phase.setText(text + (" (paused)" if paused else ""))

    def show_outcome(self, outcome: AnimationOutcome, folder: Path) -> None:
        count = len(outcome.frames)
        line = (f"{'Finished' if outcome.complete else 'Stopped early'} after {format_seconds(outcome.seconds)}: "
                f"{count} frame{'s' if count != 1 else ''} written" + (f", {len(outcome.skipped)} skipped" if outcome.skipped else "")
                + (f"  ·  {outcome.samples / 1e9:.2f} G samples" if outcome.samples else "") + (f"  ·  {outcome.engine}" if outcome.engine else ""))
        line += f'<br>Folder: <a href="file:{folder}">{folder}</a>'
        if outcome.video is not None:
            line += f'<br>Video: <a href="file:{outcome.video}">{outcome.video.name}</a>'
        notes = [n for n in outcome.notes if n]
        if notes:
            line += "<br><i>" + "; ".join(notes) + "</i>"
        self.result.setText(line)

    def show_failure(self, message: str) -> None:
        self.result.setText(f'<span style="color:#c0392b">{message}</span>')
        self.phase.setText("Failed")

    def clear_result(self) -> None:
        self.result.setText("")
        self.preview.set_image(None)
        self.preview.setText("Rendering…")


class AnimationRenderWindow(QMainWindow):
    """Non-modal batch render dialog bound to an AnimationDocument (see the module docstring)."""

    def __init__(self, document: AnimationDocument, parent: QWidget | None = None, settings: QSettings | None = None,
                 rate_hint: RateHint | None = None):
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(editor_icon("anim-render"))
        self.document = document
        self._settings = settings if settings is not None else QSettings()
        self._rate_hint = rate_hint
        self._estimate = RenderEstimate()
        self.job: AnimationRenderJob | None = None
        self.last_outcome: AnimationOutcome | None = None
        self._showing_result = False
        self._job_started = 0.0
        self._clock = QTimer(self, interval=1000)
        self._clock.timeout.connect(self._tick)
        self.size_panel = SizePanel(self)
        self.quality_panel = QualityPanel(self)
        self.output_panel = AnimationOutputPanel(self)
        self.video_panel = VideoPanel(self)
        self.plan_label = QLabel(self)
        self.estimate_label = QLabel(self)
        self.progress_panel = AnimationProgressPanel(self)
        self.start_button = QPushButton("Start render", self)
        self.pause_button = QPushButton("Pause", self)
        self.stop_button = QPushButton("Stop", self)
        self.close_button = QPushButton("Close", self)
        self._build()
        self._load()
        self._connect()
        self._on_animation_replaced()

    # --- construction -----------------------------------------------------------------------------------------
    def _build(self) -> None:
        for label in (self.plan_label, self.estimate_label):
            label.setWordWrap(True)
        self.size_panel.preview_label = "Keyframe size"
        self.size_panel.presets.setItemText(0, "Keyframe size")
        self.size_panel.presets.setToolTip("Common screen and print sizes; 'Keyframe size' is the first keyframe's own image size")
        options = QWidget(self)
        column = QVBoxLayout(options)
        column.addWidget(self.size_panel)
        column.addWidget(self.quality_panel)
        column.addWidget(self.output_panel)
        column.addWidget(self.video_panel)
        column.addWidget(self.plan_label)
        column.addWidget(self.estimate_label)
        column.addStretch(1)
        scroll = QScrollArea(self)
        scroll.setWidget(options)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setMinimumWidth(540)
        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        splitter.addWidget(scroll)
        splitter.addWidget(self.progress_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        self.start_button.setDefault(True)
        self.pause_button.setEnabled(False)
        self.stop_button.setEnabled(False)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        for button in (self.start_button, self.pause_button, self.stop_button, self.close_button):
            buttons.addWidget(button)
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.addWidget(splitter, 1)
        layout.addLayout(buttons)
        self.setCentralWidget(central)
        self.resize(1160, 780)

    def _connect(self) -> None:
        self.size_panel.size_changed.connect(self._on_options_changed)
        self.quality_panel.changed.connect(self._on_options_changed)
        self.output_panel.changed.connect(self._on_options_changed)
        self.video_panel.changed.connect(self._on_options_changed)
        self.document.animation_replaced.connect(self._on_animation_replaced)
        self.document.settings_changed.connect(self._on_settings_changed)
        self.document.keyframes_changed.connect(self._on_settings_changed)
        self.start_button.clicked.connect(lambda: self.start())
        self.pause_button.clicked.connect(self.toggle_pause)
        self.stop_button.clicked.connect(self.stop)
        self.close_button.clicked.connect(self.close)

    def _load(self) -> None:
        settings = AnimationRenderSettings()
        stored = self._settings.value(SETTINGS_KEY, "")
        if stored:
            try:
                settings = AnimationRenderSettings.from_dict(json.loads(stored))
            except (TypeError, ValueError):
                pass
        self._apply(settings)

    def _apply(self, settings: AnimationRenderSettings) -> None:
        self.size_panel.set_size(settings.image.width, settings.image.height)
        self.quality_panel.apply(settings.image)
        self.output_panel.apply(settings, self.document.animation.total_frames)
        self.video_panel.apply(settings)

    # --- settings ---------------------------------------------------------------------------------------------
    def current_settings(self) -> AnimationRenderSettings:
        """What the panels currently describe."""
        image = self.quality_panel.read(FinalRenderSettings().with_size(*self.size_panel.size()))
        settings = self.output_panel.read(AnimationRenderSettings(image=image))
        return self.video_panel.read(settings)

    def _persist(self) -> None:
        s = self.current_settings()
        self._settings.setValue(SETTINGS_KEY, json.dumps(s.to_dict()))
        if s.folder:
            self._settings.setValue(FOLDER_KEY, s.folder)
        self.document.set_render_settings(s.to_dict())

    def _engine_kind(self, s: FinalRenderSettings) -> str:
        return engine_kind(s, gpu_available()[0])

    # --- document ---------------------------------------------------------------------------------------------
    def _on_animation_replaced(self) -> None:
        anim = self.document.animation
        self.setWindowTitle(f"{WINDOW_TITLE} — {self.document.title}")
        if anim.render:
            try:
                self._apply(AnimationRenderSettings.from_dict(anim.render))
            except (TypeError, ValueError):
                pass
        self._on_settings_changed()
        if not self.output_panel.folder.text().strip():
            self.output_panel.folder.setText(self._default_folder())
        if not self.output_panel.base_name.text().strip() or self.output_panel.base_name.text() == "frame":
            self.output_panel.set_base_name(safe_stem(anim.name) or "frame")
        self._on_options_changed()

    def _on_settings_changed(self) -> None:
        anim = self.document.animation
        if anim.keyframes:
            cam = anim.keyframes[0].flame.camera
            self.size_panel.set_preview_size(cam.width, cam.height)
        self.output_panel.set_total_frames(anim.total_frames)
        self._on_options_changed()

    def _default_folder(self) -> str:
        stored = self._settings.value(FOLDER_KEY)
        base = Path(stored) if stored else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation) or Path.home())
        return str(base / (safe_stem(self.document.animation.name) or "animation"))

    # --- plan / estimate ----------------------------------------------------------------------------------------
    def _on_options_changed(self, *_args) -> None:
        s = self.current_settings()
        anim = self.document.animation
        self._persist()
        problems = s.problems(anim.total_frames)
        if not anim.keyframes:
            problems.append("The animation has no keyframes")
        self.start_button.setEnabled(not problems and self.job is None)
        self.start_button.setToolTip("\n".join(problems))
        frames = s.frames(anim.total_frames)
        self.video_panel.show_command(s, anim.fps, anim.total_frames, frames[0] if frames else 0)
        if problems and self.job is None:
            self.plan_label.setText('<span style="color:#c0392b">' + "; ".join(problems) + "</span>")
            self.estimate_label.setText("")
            return
        kind = self._engine_kind(s.image)
        plan = plan_tiles(s.image, gpu=kind == "gpu")
        hint = self._rate_hint() if self._rate_hint is not None else None
        per_frame = s.image.samples_per_tile * plan.count
        total = per_frame * len(frames)
        self.plan_label.setText(f"{len(frames)} frame{'s' if len(frames) != 1 else ''} of {s.image.width} × {s.image.height}"
                                + (f" in {plan.count} tiles each" if plan.count > 1 else "") + f" → {s.frame_path(frames[0], anim.total_frames).name}"
                                + (f" … {s.frame_path(frames[-1], anim.total_frames).name}" if len(frames) > 1 else "")
                                + (f", then {s.video_path().name}" if s.video else ""))
        rate = self._estimate.rate_for(kind, hint)
        if rate is None:
            self.estimate_label.setText(f"{total / 1e9:.2f} G samples to run. Time unknown until an engine has measured its speed.")
        else:
            self.estimate_label.setText(f"{total / 1e9:.2f} G samples to run — roughly {format_seconds(total / rate[1])} at {rate[0]} "
                                        f"({format_rate(rate[1])}), plus filtering and saving.")
        if self.job is None and not self._showing_result:
            self.progress_panel.show_idle(f"≈ {format_seconds(total / rate[1])}" if rate else "")

    # --- rendering ---------------------------------------------------------------------------------------------
    @property
    def rendering(self) -> bool:
        return self.job is not None

    def start(self, ask_overwrite: bool = True) -> None:
        """Snapshot the animation and settings and start the batch thread."""
        if self.job is not None:
            return
        anim = self.document.animation
        s = self.current_settings()
        problems = s.problems(anim.total_frames)
        if not anim.keyframes:
            problems.append("The animation has no keyframes")
        if problems:
            QMessageBox.warning(self, WINDOW_TITLE, "\n".join(problems))
            return
        frames = s.frames(anim.total_frames)
        existing = [f for f in frames if s.frame_path(f, anim.total_frames).exists()]
        if ask_overwrite and existing and not s.skip_existing:
            answer = QMessageBox.question(self, WINDOW_TITLE, f"{len(existing)} of the {len(frames)} frame files already exist in "
                                          f"{s.folder}. Overwrite them?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if answer != QMessageBox.StandardButton.Yes:
                return
        self._persist()
        self.last_outcome = None
        self.job = AnimationRenderJob(anim, s, self)
        self.job.progressed.connect(self._on_progress)
        self.job.succeeded.connect(self._on_succeeded)
        self.job.failed.connect(self._on_failed)
        self.job.finished.connect(self._on_thread_finished)
        self._set_running(True)
        self._showing_result = False
        self.progress_panel.clear_result()
        self.progress_panel.show_progress(AnimationProgress(phase="Starting the engine", count=len(frames)))
        self._job_started = time.perf_counter()
        self._clock.start()
        self.job.start()

    def _tick(self) -> None:
        if self.job is not None and not self.job.paused:
            self.progress_panel.show_elapsed(time.perf_counter() - self._job_started - self.job.control.paused_seconds)

    def toggle_pause(self) -> None:
        if self.job is None:
            return
        if self.job.paused:
            self.job.resume()
        else:
            self.job.pause()
        self.pause_button.setText("Resume" if self.job.paused else "Pause")
        self.progress_panel.show_paused(self.job.paused)

    def stop(self) -> None:
        if self.job is not None:
            self.job.cancel()
            self.stop_button.setEnabled(False)

    def wait_for_job(self, timeout_ms: int = 60000) -> None:
        if self.job is not None:
            self.job.wait(timeout_ms)

    def _set_running(self, running: bool) -> None:
        for panel in (self.size_panel, self.quality_panel, self.output_panel, self.video_panel):
            panel.setEnabled(not running)
        self.start_button.setEnabled(not running)
        self.pause_button.setEnabled(running)
        self.pause_button.setText("Pause")
        self.stop_button.setEnabled(running)

    def _on_progress(self, progress: AnimationProgress) -> None:
        fp = progress.frame_progress
        if fp is not None and fp.phase in (PHASE_DONE, PHASE_CANCELLED):
            self._estimate.record(fp.engine_kind, fp.rate)
        self.progress_panel.show_progress(progress)
        if progress.phase == PHASE_ENCODE:
            self.pause_button.setEnabled(False)

    def _on_succeeded(self, outcome: AnimationOutcome) -> None:
        self.last_outcome = outcome
        self._showing_result = True
        self.progress_panel.show_outcome(outcome, Path(self.current_settings().folder))

    def _on_failed(self, message: str) -> None:
        self._showing_result = True
        self.progress_panel.show_failure(message)

    def _on_thread_finished(self) -> None:
        job = self.job
        self.job = None
        self._clock.stop()
        if job is not None:
            job.deleteLater()
        self._set_running(False)
        self._on_options_changed()

    # --- window ------------------------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def confirm_quit(self) -> bool:
        """Ask before quitting with a batch running; stops it if the user agrees. False = keep running."""
        if self.job is None:
            return True
        answer = QMessageBox.question(self, WINDOW_TITLE, "An animation render is still running. Stop it and quit?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.job.cancel()
        self.wait_for_job()
        return True

    def closeEvent(self, event) -> None:
        """Closing hides the window; a running batch carries on."""
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        if self.job is not None:
            self.job.cancel()
            self.wait_for_job()
        super().closeEvent(event)


def _row(*widgets: QWidget, stretch_first: bool = False, stretch_all: bool = False, trailing_stretch: bool = False) -> QHBoxLayout:
    row = QHBoxLayout()
    for i, widget in enumerate(widgets):
        row.addWidget(widget, 1 if stretch_all or (stretch_first and i == 0) else 0)
    if trailing_stretch:
        row.addStretch(1)
    return row


def _quote(arg: str) -> str:
    return f'"{arg}"' if " " in arg or ";" in arg or "[" in arg else arg


__all__ = ["AnimationRenderWindow", "AnimationOutputPanel", "VideoPanel", "AnimationProgressPanel", "WINDOW_TITLE"]
