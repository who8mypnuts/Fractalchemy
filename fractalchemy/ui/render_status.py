"""Status-bar widgets for the main window: fractal facts, render facts, pass counter, progress."""

from __future__ import annotations

from PySide6.QtWidgets import QLabel, QProgressBar, QSizePolicy, QStatusBar

from ..fractal.scene import Flame
from ..render.settings import RenderStats


class RenderStatus:
    """Fills the main window's status bar with fractal information and render progress."""

    def __init__(self, bar: QStatusBar):
        self.bar = bar
        self.fractal = QLabel(bar)
        self.render = QLabel(bar)
        self.passes = QLabel(bar)
        self.progress = QProgressBar(bar)
        self.progress.setFixedWidth(160)
        self.progress.setTextVisible(False)
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        # long texts must never force the window wider: these labels clip instead
        self.fractal.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.render.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.render.setMinimumWidth(260)
        bar.addWidget(self.fractal, 1)
        bar.addPermanentWidget(self.render)
        bar.addPermanentWidget(self.passes)
        bar.addPermanentWidget(self.progress)
        self.engine_name = ""
        self.show_fractal(None)
        self.show_idle()

    # --- slots --------------------------------------------------------------
    def show_fractal(self, flame: Flame | None, source: str = "") -> None:
        """Describe the loaded flame (name, transforms, size, origin)."""
        if flame is None:
            self.fractal.setText("No fractal loaded")
            return
        parts = [flame.name, f"{len(flame.xforms)} transform{'s' if len(flame.xforms) != 1 else ''}"
                 + (" + final" if flame.final else ""), f"{flame.camera.width}×{flame.camera.height}"]
        if source:
            parts.append(source)
        if flame.unsupported:
            parts.append(f"ignored: {', '.join(flame.unsupported)}")
        self.fractal.setText("  ·  ".join(parts))
        self.fractal.setToolTip(self.fractal.text())

    def set_engine(self, name: str) -> None:
        self.engine_name = name
        self.render.setToolTip(name)
        if not self.render.text():
            self.render.setText(name)

    def show_idle(self) -> None:
        self.passes.setText("")
        self.progress.setRange(0, 1)
        self.progress.setValue(0)
        self.render.setText(self.engine_name)

    def show_progress(self, stats: RenderStats) -> None:
        """Update after a pass: engine, samples, speed, pass counter and the bar."""
        facts = [stats.engine.split(" (")[0], f"{stats.width}×{stats.height}", _count(stats.samples) + " samples"]
        if stats.seconds > 0:
            facts.append(f"{_count(stats.samples_per_second)}/s")
        self.render.setText("  ·  ".join(facts))
        self.render.setToolTip(stats.engine)
        self.passes.setText(f"Pass {stats.passes_done} of {stats.passes_total}" + ("  ✓" if stats.finished else ""))
        self.progress.setRange(0, stats.passes_total)
        self.progress.setValue(stats.passes_done)
        self.progress.setToolTip("\n".join(stats.notes) if stats.notes else "")


def _count(value: float) -> str:
    if value >= 1e9:
        return f"{value / 1e9:.2f} G"
    if value >= 1e6:
        return f"{value / 1e6:.1f} M"
    if value >= 1e3:
        return f"{value / 1e3:.0f} k"
    return f"{value:.0f}"
