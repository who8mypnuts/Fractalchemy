"""The progress half of the Render window: preview, bar, elapsed / remaining, outcome.

The remaining time is the engine's estimate from its measured sample rate plus the filter
phases it has timed; formatting comes from `render.units` so it matches the report.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QSize, Qt, QUrl
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtWidgets import QGridLayout, QLabel, QProgressBar, QSizePolicy, QVBoxLayout, QWidget

from ..render.final_engine import PHASE_CANCELLED, PHASE_DONE, FinalProgress
from ..render.final_service import FinalOutcome
from ..render.units import format_rate, format_seconds
from ..widgets.images import rgba_to_qimage

PREVIEW_MIN = QSize(320, 200)
PROGRESS_STEPS = 10000


class PreviewLabel(QLabel):
    """Shows a pixmap scaled to fit, keeping its aspect ratio."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._pixmap: QPixmap | None = None
        self.setMinimumSize(PREVIEW_MIN)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("background: #181818; color: #888;")
        self.setText("The render preview appears here")

    def set_image(self, pixmap: QPixmap | None) -> None:
        """Show (or clear) the preview."""
        self._pixmap = pixmap
        self._rescale()

    def resizeEvent(self, event) -> None:  # noqa: D102 - Qt override
        super().resizeEvent(event)
        self._rescale()

    def _rescale(self) -> None:
        if self._pixmap is None:
            return
        self.setPixmap(self._pixmap.scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio,
                                           Qt.TransformationMode.SmoothTransformation))


class RenderProgressPanel(QWidget):
    """Preview + progress bar + facts + result line."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.preview = PreviewLabel(self)
        self.bar = QProgressBar(self)
        self.phase = QLabel(self)
        self.elapsed = QLabel(self)
        self.remaining = QLabel(self)
        self.rate = QLabel(self)
        self.tiles_caption = QLabel("Tile", self)
        self.tiles = QLabel(self)
        self.result = QLabel(self)
        self._build()
        self.show_idle("")

    def _build(self) -> None:
        self.bar.setRange(0, PROGRESS_STEPS)
        self.bar.setTextVisible(True)
        self.bar.setFormat("%p %")
        self.result.setOpenExternalLinks(False)
        self.result.linkActivated.connect(self._open_link)
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        grid = QGridLayout()
        grid.addWidget(QLabel("Elapsed", self), 0, 0)
        grid.addWidget(self.elapsed, 0, 1)
        grid.addWidget(QLabel("Remaining", self), 0, 2)
        grid.addWidget(self.remaining, 0, 3)
        grid.addWidget(QLabel("Speed", self), 1, 0)
        grid.addWidget(self.rate, 1, 1)
        grid.addWidget(self.tiles_caption, 1, 2)
        grid.addWidget(self.tiles, 1, 3)
        grid.setColumnStretch(1, 1)
        grid.setColumnStretch(3, 1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.preview, 1)
        layout.addWidget(self.phase)
        layout.addWidget(self.bar)
        layout.addLayout(grid)
        layout.addWidget(self.result)

    # --- slots ------------------------------------------------------------------------------
    def show_idle(self, estimate: str) -> None:
        """Nothing running: clear the bar and show the pre-render estimate."""
        self.bar.setValue(0)
        self.phase.setText("Ready")
        self.elapsed.setText("—")
        self.remaining.setText(estimate or "—")
        self.rate.setText("—")
        self.tiles.setText("—")

    def show_progress(self, p: FinalProgress) -> None:
        """Update everything from a progress report."""
        self.bar.setValue(int(p.fraction * PROGRESS_STEPS))
        self.phase.setText(p.phase if p.phase in (PHASE_DONE, PHASE_CANCELLED) else f"{p.phase}…")
        self.elapsed.setText(format_seconds(p.elapsed))
        self.remaining.setText(format_seconds(p.remaining))
        self.rate.setText(format_rate(p.rate) if p.rate > 0 else "—")
        self.tiles.setText(f"{p.tile} of {p.tiles}" if p.tiles else "—")
        self.tiles.setToolTip(p.engine)
        if p.preview is not None:
            self.preview.set_image(QPixmap.fromImage(rgba_to_qimage(p.preview)))

    def show_elapsed(self, seconds: float) -> None:
        """Update only the elapsed time (the window's clock between engine reports)."""
        self.elapsed.setText(format_seconds(seconds))

    def show_paused(self, paused: bool) -> None:
        """Reflect a pause in the phase line."""
        text = self.phase.text().replace(" (paused)", "")
        self.phase.setText(text + (" (paused)" if paused else ""))

    def show_outcome(self, outcome: FinalOutcome) -> None:
        """Describe a finished render, with links to the file and its folder."""
        r = outcome.result
        facts = [f"{'Finished' if r.complete else 'Stopped early'} after {format_seconds(r.seconds)}",
                 f"{r.samples / 1e9:.2f} G samples", r.engine]
        line = "  ·  ".join(facts)
        if outcome.path is not None:
            p = outcome.path
            line += f"<br>Saved {self.file_link(p)} in {self.file_link(p.parent, str(p.parent))}"
            extras = [x for x in (outcome.sidecar, outcome.report) if x is not None]
            if extras:
                line += " (+ " + ", ".join(self.file_link(x) for x in extras) + ")"
        elif not r.complete:
            line += "<br>Nothing was saved (stopped before completion; see 'Save incomplete renders')."
        notes = [n for n in outcome.notes if n]
        if notes:
            line += "<br><i>" + "; ".join(notes) + "</i>"
        self.result.setText(line)

    def show_failure(self, message: str) -> None:
        """Show an error."""
        self.result.setText(f'<span style="color:#c0392b">{message}</span>')
        self.phase.setText("Failed")

    def clear_result(self) -> None:
        """Blank the result line (a new render is starting)."""
        self.result.setText("")
        self.preview.set_image(None)
        self.preview.setText("Rendering…")

    @staticmethod
    def _open_link(link: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(link.removeprefix("file:")))))

    @staticmethod
    def file_link(path: Path, text: str | None = None) -> str:
        """An HTML link that `_open_link` opens with the system's file handler."""
        return f'<a href="file:{path}">{text if text is not None else path.name}</a>'


__all__ = ["RenderProgressPanel", "PreviewLabel"]
