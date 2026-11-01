"""*Render ▸ Batch render…*: one image per preset (or per keyframe) of the current fragment — FragM's `renderPresets.fqs`.

Uses the Render Fragment window's tile size, subframes and format, writes `<fragment>-<preset>.<ext>` into a folder
of your choice, and runs on a thread with its own OpenGL context (`fragments.batch`). The fragment must be saved
first: the batch renders from the file.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import (QComboBox, QDialog, QDialogButtonBox, QFileDialog, QFormLayout, QLabel, QLineEdit, QListWidget, QProgressBar,
                               QPushButton, QVBoxLayout, QWidget)

from ...fragments import batch
from ...fragments.gl.engine import FragEngine
from ...fragments.render_settings import FragFinalSettings
from ...widgets.layouts import row


class BatchJob(QThread):
    """Renders every preset of a fragment file on a worker thread.

    Signals:
        file_written(object): A `Path` per image.
        finished_with(list): Every path written.
        failed(str): Could not start or a fragment problem.
    """
    file_written = Signal(object)
    finished_with = Signal(list)
    failed = Signal(str)

    def __init__(self, path: Path, settings: FragFinalSettings, folder: Path, keyframes_only: bool, parent=None):
        super().__init__(parent)
        self.path, self.settings, self.folder, self.keyframes_only = path, settings, folder, keyframes_only
        self._cancel = False

    def cancel(self) -> None:
        self._cancel = True

    def run(self) -> None:  # noqa: D401 - QThread entry point
        engine = None
        written: list[Path] = []
        try:
            engine = FragEngine()
            probe = batch.prepare(self.path, engine, None)
            names = probe.source.keyframe_names() if self.keyframes_only else list(probe.source.presets)
            suffix = Path(self.settings.output_path).suffix or ".png"
            for name in names:
                if self._cancel:
                    break
                target = self.folder / f"{batch.safe_stem(self.path.stem)}-{batch.safe_stem(name)}{suffix}"
                result = batch.render(self.path, self.settings.with_(output_path=str(target), animation=False, preview=False), engine, name)
                written += result.paths
                for path in result.paths:
                    self.file_written.emit(path)
        except Exception as exc:  # noqa: BLE001 - reported, never raised on a thread
            self.failed.emit(str(exc) or exc.__class__.__name__)
            return
        finally:
            if engine is not None:
                engine.close()
        self.finished_with.emit(written)


class BatchDialog(QDialog):
    """Choose what to render and where; watch the files arrive (see the module docstring)."""

    def __init__(self, path: Path, settings: FragFinalSettings, preset_count: int, keyframe_count: int, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle("Batch render")
        self.path = path
        self.settings = settings
        self.job: BatchJob | None = None
        self.mode = QComboBox(self)
        self.mode.addItem(f"Every preset ({preset_count})", False)
        self.mode.addItem(f"Every keyframe ({keyframe_count})", True)
        self.folder_edit = QLineEdit(str(Path(settings.output_path).parent if settings.output_path else Path.home()), self)
        browse = QPushButton("Browse…", self)
        browse.clicked.connect(self._browse)
        self.plan = QLabel(f"{settings.tile_width * settings.tiles} × {settings.tile_height * settings.tiles}, {settings.subframes} subframes, "
                           f"{settings.output_format} — from the Render Fragment window's settings", self)
        self.plan.setWordWrap(True)
        self.files = QListWidget(self)
        self.bar = QProgressBar(self)
        self.bar.setRange(0, 0)
        self.bar.hide()
        self.buttons = QDialogButtonBox(self)
        self.start_button = self.buttons.addButton("Start", QDialogButtonBox.ButtonRole.AcceptRole)
        self.stop_button = self.buttons.addButton("Stop", QDialogButtonBox.ButtonRole.ActionRole)
        self.buttons.addButton(QDialogButtonBox.StandardButton.Close)
        self.stop_button.setEnabled(False)
        form = QFormLayout()
        form.addRow("Render", self.mode)
        form.addRow("Into folder", row(self.folder_edit, browse, stretch_first=True))
        form.addRow("Settings", self.plan)
        layout = QVBoxLayout(self)
        layout.addLayout(form)
        layout.addWidget(self.files, 1)
        layout.addWidget(self.bar)
        layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.start)
        self.buttons.rejected.connect(self.reject)
        self.stop_button.clicked.connect(self.stop)
        self.resize(640, 420)

    def _browse(self) -> None:
        chosen = QFileDialog.getExistingDirectory(self, "Render into", self.folder_edit.text())
        if chosen:
            self.folder_edit.setText(chosen)

    def start(self) -> None:
        if self.job is not None:
            return
        folder = Path(self.folder_edit.text().strip() or ".")
        folder.mkdir(parents=True, exist_ok=True)
        self.files.clear()
        self.job = BatchJob(self.path, self.settings, folder, bool(self.mode.currentData()), self)
        self.job.file_written.connect(lambda p: self.files.addItem(str(p)))
        self.job.finished_with.connect(self._done)
        self.job.failed.connect(lambda message: (self.files.addItem(f"Failed: {message}"), self._done([])))
        self.job.finished.connect(self._thread_done)
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.bar.show()
        self.job.start()

    def stop(self) -> None:
        if self.job is not None:
            self.job.cancel()

    def _done(self, written: list) -> None:
        self.files.addItem(f"{len(written)} file(s) written")

    def _thread_done(self) -> None:
        job, self.job = self.job, None
        if job is not None:
            job.deleteLater()
        self.bar.hide()
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)

    def wait(self, timeout_ms: int = 120000) -> None:
        """Block until the job ends (tests / closing)."""
        if self.job is not None:
            self.job.wait(timeout_ms)

    def reject(self) -> None:  # noqa: D102 - Qt override: a running job is stopped first
        if self.job is not None:
            self.job.cancel()
            self.job.wait(30000)
        super().reject()


__all__ = ["BatchDialog", "BatchJob"]
