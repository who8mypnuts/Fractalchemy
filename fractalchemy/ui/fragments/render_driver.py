"""What to render when — the glue between a `FragDocument`, the viewport and the fragment render service.

FragM's `DisplayWidget` decides, from every change, whether the accumulation restarts (`requireRedraw(clear)`),
continues (`DontClearOnChange`), or only the buffer shader re-runs (`bufferShaderOnly`); it renders at one subframe
per timer tick while a button is down and keeps accumulating otherwise until *Subframe Max*. The driver does the same
with render-service requests: one key per document, `clear` / `redisplay_only` from the kind of change, the buffer
size from the `BufferSize` rule (scaled down while interacting), `subframes_per_pass` adapted so images arrive at
about the refresh rate, and the facts of the first pass (active / unused uniforms, compile time) handed to the
document. Build errors from the driver come back as diagnostics.
"""

from __future__ import annotations

import time

from PySide6.QtCore import QObject, QTimer, Signal

from ... import config
from ...fragments.gl.engine import FragBuildError
from ...fragments.gl.job import FragRenderSettings
from ...fragments.source import CRITICAL, Message
from ...render.service import PRIORITY_EDITOR, PRIORITY_VIEWPORT, RenderService
from ...render.settings import RenderStats
from .buffer_size import BufferSize
from .document import FragDocument

INTERACTIVE_SCALE = config.FRAG_INTERACTIVE_SCALE
SETTLE_MS = config.INTERACTION_SETTLE_MS
MAX_SUBFRAMES_PER_PASS = 64
DEFAULT_REFRESH_MS = 40


class RenderDriver(QObject):
    """Submits renders of the current document (see the module docstring).

    Signals:
        stats_changed(object): `RenderStats` after every delivered image.
        fps_changed(float): Images per second, measured over the last second (-1: nothing rendering).
        building(bool): True from a submit until its first image (the viewport shows *Building…*).
        failed(str): A render could not be set up (a message for the status bar; build errors go to the document).
        image_ready(object): The RGBA8 image of every delivered pass (the viewport paints it).
    """
    stats_changed = Signal(object)
    fps_changed = Signal(float)
    building = Signal(bool)
    failed = Signal(str)
    image_ready = Signal(object)

    def __init__(self, service: RenderService, buffer_size: BufferSize, parent: QObject | None = None):
        super().__init__(parent)
        self.service = service
        self.buffer_size = buffer_size
        self.document: FragDocument | None = None
        self.subframe_max = config.FRAG_DEFAULT_SUBFRAMES
        self.time = 0.0
        self.refresh_ms = DEFAULT_REFRESH_MS
        self.interactive_scale = INTERACTIVE_SCALE
        self.interactive = False
        self.depth_probe: tuple[int, int] | None = None
        self.window_size = (640, 360)
        self.stats: RenderStats | None = None
        self.probe_depth: float | None = None
        self._key: object = None
        self._generation = 0           # part of every key, so a pass of a superseded job is never mistaken for the new one
        self._facts_seen = False
        self._per_pass = 1
        self._last_pass_at = 0.0
        self._pass_times: list[float] = []
        self._settle = QTimer(self, singleShot=True, interval=SETTLE_MS)
        self._settle.timeout.connect(self._after_interaction)
        service.pass_done.connect(self._on_pass)
        service.job_error.connect(self._on_error)
        service.job_finished.connect(self._on_finished)

    # --- the document -------------------------------------------------------------------------------------------------
    def set_document(self, document: FragDocument | None) -> None:
        """Follow another document (a tab switch): its last request is rendered afresh."""
        if self.document is document:
            return
        if self.document is not None:
            self.document.built.disconnect(self._on_built)
            self.document.parameters_changed.disconnect(self._on_parameters)
            self.cancel()
        self.document = document
        self._facts_seen = False
        if document is not None:
            document.built.connect(self._on_built)
            document.parameters_changed.connect(self._on_parameters)
            if document.request() is not None:
                self.render(clear=True)

    def cancel(self) -> None:
        if self._key is not None:
            self.service.cancel(self._key)
            self._key = None
        self.building.emit(False)

    # --- deciding ------------------------------------------------------------------------------------------------------
    def _on_built(self, _source) -> None:
        self._facts_seen = False
        self.render(clear=True)

    def _on_parameters(self, names: list, recompile: bool, buffer_only: bool) -> None:
        if recompile or self.document is None or self.document.request() is None:
            return
        if buffer_only:
            self.render(clear=False, redisplay_only=True)
        else:
            self.render(clear=self.document.source.clear_on_change)

    def set_interactive(self, interactive: bool) -> None:
        """A mouse button or camera key is held: render small and one subframe at a time; release settles to full size."""
        if interactive == self.interactive:
            return
        self.interactive = interactive
        if interactive:
            self._settle.stop()
        else:
            self._settle.start()

    def _after_interaction(self) -> None:
        if not self.interactive and self.document is not None and self.document.request() is not None:
            self.render(clear=True)

    def set_subframe_max(self, value: int) -> None:
        """FragM's *Subframe Max*; a finished accumulation resumes when the limit grows (0 = unlimited)."""
        self.subframe_max = max(0, int(value))
        if self.stats is not None and (self.subframe_max == 0 or self.stats.passes_done < self.subframe_max):
            self.render(clear=False)

    def set_time(self, seconds: float, render: bool = True) -> None:
        """The `time` uniform moved (the animation clock / slider); a frame change restarts the accumulation."""
        self.time = float(seconds)
        if render and self.document is not None and self.document.request() is not None:
            self.render(clear=True)

    def set_window_size(self, width: int, height: int) -> None:
        self.window_size = (max(1, width), max(1, height))

    def render_size(self) -> tuple[int, int]:
        """The buffer size for the next render (the window's or the custom one, scaled down while interacting)."""
        width, height = self.buffer_size.resolve(*self.window_size)
        if self.interactive:
            width, height = max(1, int(width * self.interactive_scale)), max(1, int(height * self.interactive_scale))
        return width, height

    # --- submitting ---------------------------------------------------------------------------------------------------
    def render(self, clear: bool = True, redisplay_only: bool = False) -> None:
        """Submit a render of the current document (superseding the previous one for this document)."""
        document = self.document
        request = document.request() if document is not None else None
        if request is None:
            return
        width, height = self.render_size()
        settings = FragRenderSettings(width, height, subframe_max=1 if self.interactive else self.subframe_max,
                                      subframes_per_pass=1 if self.interactive else self._per_pass, time=self.time,
                                      clear=clear or self.interactive, redisplay_only=redisplay_only and not self.interactive,
                                      surface_key=("surface", id(document)), depth_probe=self.depth_probe)
        if self._key is not None:
            self.service.cancel(self._key)
        self._generation += 1
        self._key = ("frag", id(document), self._generation)
        self.service.submit(self._key, request, settings, PRIORITY_EDITOR if self.interactive else PRIORITY_VIEWPORT)
        self.building.emit(True)

    # --- results -------------------------------------------------------------------------------------------------------
    def _on_pass(self, key: object, image, stats: RenderStats) -> None:
        if key != self._key:
            return
        self.stats = stats
        self.building.emit(False)
        if stats.facts is not None:
            self.probe_depth = stats.facts.probe_depth
            if not self._facts_seen and self.document is not None:
                self._facts_seen = True
                self.document.set_build_facts(stats.facts)
        self._measure(stats)
        self.image_ready.emit(image)
        self.stats_changed.emit(stats)

    def _measure(self, stats: RenderStats) -> None:
        """Adapt subframes per pass to the refresh rate and keep an images-per-second figure."""
        now = time.perf_counter()
        if self._last_pass_at:
            elapsed = now - self._last_pass_at
            self._pass_times = [t for t in self._pass_times if now - t < 1.0] + [now]
            self.fps_changed.emit(len(self._pass_times) / 1.0)
            if not self.interactive and not stats.finished:
                target = self.refresh_ms / 1000.0
                if elapsed < target / 2 and self._per_pass < MAX_SUBFRAMES_PER_PASS:
                    self._per_pass *= 2
                elif elapsed > target * 2 and self._per_pass > 1:
                    self._per_pass = max(1, self._per_pass // 2)
        self._last_pass_at = now

    def _on_finished(self, key: object, stats: RenderStats) -> None:
        if key == self._key:
            self.stats = stats
            self.fps_changed.emit(-1.0)
            self._last_pass_at = 0.0

    def _on_error(self, key: object, exc: Exception) -> None:
        if key != self._key:
            return
        self.building.emit(False)
        if isinstance(exc, FragBuildError) and self.document is not None:
            self.document.set_build_error(exc.diagnostics)
        elif self.document is not None:
            self.document.set_build_error([Message(CRITICAL, str(exc) or exc.__class__.__name__, self.document.path)])
        self.failed.emit(str(exc))


__all__ = ["RenderDriver"]
