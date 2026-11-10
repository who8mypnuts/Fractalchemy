"""One worker thread that owns the preview engine and renders requests progressively.

    service = RenderService(parent)
    service.pass_done.connect(show_image)       # (key, rgba ndarray, RenderStats) after every pass
    service.submit("viewport", flame, settings)  # a newer submit with the same key supersedes the old one
    service.submit(("thumb", path, 2), flame, small_settings, priority=1)

Keys identify *slots*: resubmitting a key cancels whatever that slot was doing, so a
stale render can never overwrite a newer view. Lower `priority` numbers run first;
a running low-priority job (thumbnail) yields between passes — and, on the CPU
engine, between chunks — when urgent work arrives, and a job that is *refining* (past
its configured passes) yields to any pending work. A pre-empted job is paused, not
restarted: its histogram is kept and it resumes when its turn comes again. The OpenGL
context is created on this thread because contexts are thread-bound; if that fails the
CPU engine is used.

**Re-colouring without re-rendering** (`retone(key, coloring)`): brightness, gamma, vibrancy, contrast, the background
and the curves only change the tone mapping, so a job of `key` — running (it is pre-empted: paused with its histogram,
like any urgent work), paused, or *retained* after finishing (`submit(..., retain=True)`, the viewport's renders; one
retained job at a time) — is tone-mapped again with the new colouring and the picture arrives as an ordinary
`pass_done` of that key, with no new samples; the job then carries on refining. When no such job exists,
`retone_missed(key)` says so and the caller renders afresh.

The engine is pluggable: an `EngineFactory` creates it on the worker thread (and names a
fallback for payloads it rejects). The default factory is the flame renderer (GPU, then the
CPU); the Fragments window runs a second service with its fragment-shader engine. A payload
is anything with `.copy()` that the engine's `start(payload, settings)` accepts, and a job
anything with `stats`, `run_pass(cancelled)` and `close()`.
"""

from __future__ import annotations

import threading
import time
from dataclasses import dataclass, field, replace
from itertools import count
from typing import Protocol

from PySide6.QtCore import QObject, QThread, Signal

from .settings import RenderStats

PRIORITY_EDITOR = -1     # the Transform Editor's small preview: it follows the mouse, so it goes first
PRIORITY_VIEWPORT = 0
PRIORITY_THUMBNAIL = 1
PRIORITY_REFINE = 2      # a paused job past its configured passes resumes behind everything else


class EngineFactory(Protocol):
    """Creates the engine a `RenderService` runs (on the worker thread) and its fallback."""

    def create(self) -> tuple[object, str]:
        """`(engine, name)`; the name is announced through `engine_ready`."""

    def fallback(self, engine: object) -> object | None:
        """A second engine for payloads `engine` could not start (None: there is none). Created once, kept."""


class DefaultEngineFactory:
    """The flame renderer: the OpenGL engine when it can be created, else the numpy one; the numpy one as fallback."""

    def __init__(self, prefer_gpu: bool = True):
        self._prefer_gpu = prefer_gpu
        self._cpu = None

    def create(self) -> tuple[object, str]:
        if self._prefer_gpu:
            try:
                from .gpu_engine import GpuEngine
                engine = GpuEngine()
                return engine, f"GPU ({engine.renderer})"
            except Exception as exc:  # noqa: BLE001 - fall back to the CPU on any GL failure
                reason = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
                return self._cpu_engine(), f"CPU fallback — OpenGL unavailable: {reason}"
        engine = self._cpu_engine()
        return engine, f"CPU (numpy, {engine.threads} threads)"

    def fallback(self, engine: object) -> object | None:
        """The CPU engine, for flames the GPU engine cannot compile (None when `engine` already is the CPU)."""
        return None if engine.name == "CPU" else self._cpu_engine()

    def _cpu_engine(self):
        if self._cpu is None:
            from .cpu_engine import CpuEngine
            self._cpu = CpuEngine()
        return self._cpu

    def close(self) -> None:
        if self._cpu is not None:
            self._cpu.close()
            self._cpu = None


@dataclass(order=True)
class _Request:
    priority: int
    seq: int
    key: object = field(compare=False)
    payload: object = field(compare=False)
    settings: object = field(compare=False)
    retain: bool = field(default=False, compare=False)


class RenderService(QThread):
    """Background renderer.

    Signals:
        engine_ready(str): Which engine is in use (emitted once, before the first image).
        pass_done(object, object, object): (key, RGBA uint8 array (H, W, 4), RenderStats) after each pass.
        job_finished(object, object): (key, RenderStats) when all passes completed.
        job_failed(object, str): (key, message) when a render could not be set up.
        job_error(object, object): (key, exception) — the same failure with the exception itself, for engines whose
            errors carry more than a message (the fragment engine's diagnostics).
        retone_missed(object): (key) `retone` found no job of that key to re-colour.
    """
    engine_ready = Signal(str)
    pass_done = Signal(object, object, object)
    job_finished = Signal(object, object)
    job_failed = Signal(object, str)
    job_error = Signal(object, object)
    retone_missed = Signal(object)

    def __init__(self, parent: QObject | None = None, prefer_gpu: bool = True, factory: EngineFactory | None = None):
        """Args:
            parent: Qt owner.
            prefer_gpu: For the default factory: try the OpenGL flame engine first.
            factory: What to render with (the flame engines by default).
        """
        super().__init__(parent)
        self._factory = factory if factory is not None else DefaultEngineFactory(prefer_gpu)
        self._fallback = None
        self._queue: list[_Request] = []
        self._cond = threading.Condition()
        self._seq = count()
        self._stop = False
        self._running_key: object = None
        self._superseded = False
        self._paused: dict[object, tuple] = {}   # key -> (job, request) pre-empted mid-way (worker thread only)
        self._retained: dict[object, object] = {}   # key -> a finished job kept for re-colouring (worker thread only)
        self._retones: dict[object, object] = {}    # key -> the colouring to re-tone it with (GUI → worker)
        self._drop: set = set()                     # keys whose retained job the worker should close
        self.engine_name = ""
        self.engine = None

    # --- API (GUI thread) ---------------------------------------------------
    def submit(self, key: object, payload, settings, priority: int = PRIORITY_VIEWPORT, retain: bool = False) -> None:
        """Queue a render of `payload` (copied; a `Flame` for the flame engines) for `key`, replacing any queued or
        running render with the same key. With `retain` the finished job is kept for `retone` (see the module docstring)."""
        with self._cond:
            self._queue = [r for r in self._queue if r.key != key]
            self._retones.pop(key, None)
            self._queue.append(_Request(priority, next(self._seq), key, payload.copy(), settings, retain))
            if self._running_key == key:
                self._superseded = True
            self._cond.notify()

    def cancel(self, key: object) -> None:
        """Drop any queued render for `key` and stop it if it is running (a retained job of `key` is released too)."""
        with self._cond:
            self._queue = [r for r in self._queue if r.key != key]
            self._retones.pop(key, None)
            self._drop.add(key)
            if self._running_key == key:
                self._superseded = True
            self._cond.notify()

    def retone(self, key: object, coloring) -> None:
        """Re-colour `key`'s job with `coloring` without new samples (see the module docstring)."""
        with self._cond:
            self._retones[key] = coloring.copy()
            self._cond.notify()

    def cancel_where(self, predicate) -> None:
        """Drop queued renders whose key satisfies `predicate`."""
        with self._cond:
            self._queue = [r for r in self._queue if not predicate(r.key)]

    def stop(self, timeout_ms: int = 5000) -> None:
        """Finish the current pass, release the engine and join the thread."""
        with self._cond:
            self._stop = True
            self._superseded = True
            self._queue.clear()
            self._cond.notify()
        self.wait(timeout_ms)

    def pending(self) -> int:
        with self._cond:
            return len(self._queue)

    # --- worker thread ------------------------------------------------------
    def run(self) -> None:  # noqa: D401 - QThread entry point
        self.engine, self.engine_name = self._factory.create()
        self.engine_ready.emit(self.engine_name)
        try:
            while True:
                request = self._next()
                if request is None:
                    return
                self._render(request)
        finally:
            for job, _request in self._paused.values():
                job.close()
            self._paused.clear()
            for job in self._retained.values():
                job.close()
            self._retained.clear()
            self.engine.close()
            if self._fallback is not None and self._fallback is not self.engine:
                self._fallback.close()

    def _next(self) -> _Request | None:
        while True:
            with self._cond:
                while not self._queue and not self._retones and not self._drop and not self._stop:
                    self._cond.wait()
                if self._stop:
                    return None
                drop, self._drop = self._drop, set()
                retones, self._retones = self._retones, {}
            for key in drop:                                  # released retained jobs (GL objects: closed on this thread)
                job = self._retained.pop(key, None)
                if job is not None:
                    job.close()
            for key, coloring in retones.items():
                self._retone(key, coloring)
            with self._cond:
                if self._queue or self._stop:
                    break
        with self._cond:
            if self._stop:
                return None
            request = min(self._queue)
            self._queue.remove(request)
            self._running_key = request.key
            self._superseded = False
            queued = {r.key for r in self._queue} | {request.key}
        for key in [k for k in self._paused if k not in queued]:   # paused jobs nobody will resume
            self._paused.pop(key)[0].close()
        return request

    def _urgent_pending(self, priority: int) -> bool:
        with self._cond:
            return bool(self._retones) or any(r.priority < priority for r in self._queue)

    def _retone(self, key: object, coloring) -> None:
        """Re-colour the paused or retained job of `key` (worker thread)."""
        paused = self._paused.get(key)
        job = paused[0] if paused is not None else self._retained.get(key)
        if job is None or not hasattr(job, "retone"):
            self.retone_missed.emit(key)
            return
        image = job.retone(coloring)
        if image is not None:
            self.pass_done.emit(key, image, _snapshot(job.stats))

    def _any_pending(self) -> bool:
        with self._cond:
            return bool(self._queue)

    def _start_job(self, request: _Request):
        """A job for `request`: the paused one if it was pre-empted, else a fresh one (CPU fallback if needed)."""
        paused = self._paused.pop(request.key, None)
        if paused is not None and paused[1].seq == request.seq:
            return paused[0]
        if paused is not None:
            paused[0].close()
        try:
            return self.engine.start(request.payload, request.settings)
        except ValueError:   # the payload itself is unusable
            raise
        except Exception as exc:  # noqa: BLE001 - e.g. a formula's GLSL that this driver rejects: use the fallback for it
            if self._fallback is None:
                self._fallback = self._factory.fallback(self.engine)
            if self._fallback is None:
                raise
            try:
                job = self._fallback.start(request.payload, request.settings)
            except Exception as exc2:  # noqa: BLE001 - report the more telling error
                raise exc2 from exc
            job.stats.notes.append(f"rendered on the CPU — the GPU rejected the shader: {str(exc).splitlines()[0][:200]}")
            return job

    def _render(self, request: _Request) -> None:
        def cancelled() -> bool:
            if self._superseded or self._stop or self._urgent_pending(request.priority):
                return True
            return job.stats.passes_finished and self._any_pending()   # refining: let anything else go first

        try:
            job = self._start_job(request)
        except Exception as exc:  # noqa: BLE001
            self._finish(request.key)
            self.job_error.emit(request.key, exc)
            self.job_failed.emit(request.key, str(exc))
            return
        keep = False
        try:
            while not job.stats.finished:
                image = job.run_pass(cancelled)
                if image is None:
                    break
                self.pass_done.emit(request.key, image, _snapshot(job.stats))
            else:
                self.job_finished.emit(request.key, _snapshot(job.stats))
                self._finish(request.key)
                if request.retain and hasattr(job, "retone"):
                    for other in list(self._retained):        # one retained job at a time
                        self._retained.pop(other).close()
                    with self._cond:
                        dropped = request.key in self._drop
                    if not dropped:
                        self._retained[request.key] = job
                        keep = True
                return
            # pre-empted (not superseded): pause the job and queue the request again to resume it later
            # (a refining job goes to the back of the queue, so the work it yielded to really runs first)
            with self._cond:
                if not self._superseded and not self._stop:
                    if job.stats.passes_finished:
                        request = replace(request, priority=max(request.priority, PRIORITY_REFINE))
                    self._paused[request.key] = (job, request)
                    self._queue.append(request)
                    keep = True
            self._finish(request.key)
        except Exception as exc:  # noqa: BLE001
            self._finish(request.key)
            self.job_error.emit(request.key, exc)
            self.job_failed.emit(request.key, str(exc))
        finally:
            if not keep:
                job.close()

    def _finish(self, key: object) -> None:
        with self._cond:
            if self._running_key == key:
                self._running_key = None


def _snapshot(stats: RenderStats) -> RenderStats:
    return RenderStats(stats.engine, stats.passes_done, stats.passes_total, stats.samples, stats.hits, stats.seconds,
                       stats.width, stats.height, list(stats.notes), stats.samples_target, stats.facts)


def wait_for(predicate, timeout: float = 10.0, interval: float = 0.02) -> bool:
    """Poll `predicate` (tests / scripts)."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if predicate():
            return True
        time.sleep(interval)
    return predicate()
