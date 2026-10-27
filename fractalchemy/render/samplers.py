"""Samplers for the final renderer: run the chaos game and accumulate one tile's histogram.

A sampler is told about a tile (`begin_tile`: the affine from fractal space to the tile's
bucket grid), asked to `accumulate` a number of samples — possibly many times, so the caller can
report progress and previews in between — and finally hands over the tile's `histogram` as a
planar float64 array `(4, rows, cols)` = (r, g, b, count). Two implementations:

* `CpuSampler` — numpy, float64, one point population per worker *process* (threads do not scale
  here: a chaos-game step is many short numpy kernels, see `cpu_workers`). The histogram lives in
  shared memory. Each worker partitions its batch of hits by horizontal *band* (a radix sort on a
  small key) and adds each band under that band's lock, so no hit is ever lost to a race and workers
  rarely wait for each other. Partitioning also makes the adds cache-friendly, which matters more
  than anything else for multi-million-bucket tiles.
* `GpuSampler` — the preview engine's OpenGL population plotting into an RGBA32F texture; the
  texture is read back every few seconds into the float64 master and cleared, so float32
  accumulation never runs long enough to lose counts.

Both honour a `RenderControl` (cancel / pause) between chunks.
"""

from __future__ import annotations

import multiprocessing as mp
import queue as queue_module
import threading
import time

import numpy as np

from .. import config
from ..fractal.scene import Flame
from . import cpu_workers
from .compiled import CompiledFlame
from .cpu_engine import thread_count

GPU_POINTS = 1 << 20                  # population per draw
GPU_READBACK_SECONDS = 3.0            # float32 texture → float64 master at least this often
GPU_READBACK_SAMPLES = 1 << 28        # … and at least every this many samples


class RenderControl:
    """Cancel / pause flags shared between the GUI and the render thread; tracks time spent paused."""

    def __init__(self):
        self._cancel = threading.Event()
        self._resume = threading.Event()
        self._resume.set()
        self._paused_since: float | None = None
        self.paused_seconds = 0.0
        self._lock = threading.Lock()

    def cancel(self) -> None:
        """Stop as soon as possible (also releases a pause)."""
        self._cancel.set()
        self._resume.set()

    def pause(self) -> None:
        """Hold the render between chunks until `resume`."""
        with self._lock:
            if self._resume.is_set():
                self._resume.clear()
                self._paused_since = time.perf_counter()

    def resume(self) -> None:
        """Continue after `pause`."""
        with self._lock:
            if not self._resume.is_set():
                self.paused_seconds += time.perf_counter() - (self._paused_since or time.perf_counter())
                self._paused_since = None
                self._resume.set()

    @property
    def paused(self) -> bool:
        """True while paused."""
        return not self._resume.is_set()

    def cancelled(self) -> bool:
        """True once `cancel` was called."""
        return self._cancel.is_set()

    def wait_if_paused(self) -> bool:
        """Block while paused; returns False if cancelled (so callers can bail out)."""
        self._resume.wait()
        return not self._cancel.is_set()


# --- CPU ------------------------------------------------------------------------------------
class CpuSampler:
    """Multiprocess numpy sampler (float64); see the module docstring and `cpu_workers` for the scheme.

    Workers are started when the sampler is created (spawned, so Qt and its threads are never
    forked) and fuse their populations while the caller prepares the first tile.
    """
    is_gpu = False
    max_side = 1 << 30

    def __init__(self, flame: Flame, threads: int = 0, seed: int = 1, fuse: int = 30):
        self.threads = max(1, threads or thread_count())
        self.name = f"CPU (numpy float64, {self.threads} process{'es' if self.threads != 1 else ''})"
        self._ctx = mp.get_context("spawn")
        self._flags = self._ctx.Array("i", [0, 0])
        self._locks = [self._ctx.Lock() for _ in range(cpu_workers.BAND_LOCKS)]
        self._results = self._ctx.Queue()
        self._commands = [self._ctx.Queue() for _ in range(self.threads)]
        data = flame.to_dict()
        self._processes = [
            self._ctx.Process(target=cpu_workers.worker_main, daemon=True, name=f"final-cpu-{i}",
                              args=(data, seed * 7919 + i, fuse, self._commands[i], self._results, self._flags, self._locks))
            for i in range(self.threads)]
        for proc in self._processes:
            proc.start()
        self._histogram: cpu_workers.SharedHistogram | None = None

    def begin_tile(self, affine, width: int, height: int) -> None:
        """Allocate the tile's shared histogram and aim every worker at it."""
        self.end_tile()
        self._histogram = cpu_workers.SharedHistogram(width, height, create=True)
        for queue in self._commands:
            queue.put(("tile", self._histogram.name, width, height, tuple(float(v) for v in affine)))
        self._collect("ready")

    def accumulate(self, samples: int, control: RenderControl) -> int:
        """Run about `samples` iterations spread over the workers; returns the number actually run."""
        per_worker = max(1, samples // self.threads)
        for queue in self._commands:
            queue.put(("run", per_worker))
        return self._collect("done", control)

    def _collect(self, until: str, control: RenderControl | None = None) -> int:
        """Drain results until every worker sent `until`; mirrors the control's flags to the workers meanwhile."""
        waiting = self.threads
        total = 0
        while waiting:
            if control is not None:
                self._flags[cpu_workers.FLAG_CANCEL] = int(control.cancelled())
                self._flags[cpu_workers.FLAG_PAUSE] = int(control.paused)
            try:
                message = self._results.get(timeout=0.1)
            except queue_module.Empty:
                if not any(p.is_alive() for p in self._processes):
                    raise RuntimeError("the CPU render workers died") from None
                continue
            if message[0] == until:
                waiting -= 1
                if until == "done":
                    total += int(message[2])
        return total

    def histogram(self) -> np.ndarray:
        """The tile's histogram as (4, rows, cols) float64 (a view of shared memory; valid until `end_tile`)."""
        return self._histogram.array()

    def end_tile(self) -> None:
        """Release the tile's histogram."""
        if self._histogram is not None:
            self._histogram.close(unlink=True)
            self._histogram = None

    def close(self) -> None:
        """Stop the workers (they exit on their own; anything still running is cancelled first)."""
        self._flags[cpu_workers.FLAG_CANCEL] = 1
        for queue in self._commands:
            try:
                queue.put(("stop",))
            except (ValueError, OSError):
                pass
        for proc in self._processes:
            proc.join(timeout=2.0)
            if proc.is_alive():
                proc.terminate()
        self.end_tile()


# --- GPU ------------------------------------------------------------------------------------
class GpuSampler:
    """OpenGL sampler (float32 iteration) accumulating into a float64 master through periodic readbacks."""
    is_gpu = True

    def __init__(self, engine, compiled: CompiledFlame, seed: int = 1, fuse: int = 30, points: int = GPU_POINTS,
                 owns_engine: bool = False):
        from .gpu_engine import GpuPopulation

        self.engine = engine
        self._owns_engine = owns_engine
        self.ctx = engine.ctx
        self.name = f"GPU ({engine.renderer}, single precision)"
        self.max_side = int(self.ctx.info.get("GL_MAX_TEXTURE_SIZE", 8192))
        self.points = points
        self.population = GpuPopulation(engine, compiled, points, seed)
        self._fuse = fuse
        self._fused = False
        self._hist: np.ndarray | None = None
        self._tex = self._fbo = None
        self._width = self._height = 0
        self._since_readback = 0
        self._last_readback = 0.0

    def begin_tile(self, affine, width: int, height: int) -> None:
        """Create the tile's texture and master histogram."""
        self._release_targets()
        self._width, self._height = width, height
        self._tex = self.ctx.texture((width, height), 4, dtype="f4")
        self._tex.filter = (self.engine.gl.NEAREST, self.engine.gl.NEAREST)
        self._fbo = self.ctx.framebuffer([self._tex])
        self._fbo.clear(0.0, 0.0, 0.0, 0.0)
        self._hist = np.zeros((4, height, width), dtype=np.float64)
        self.population.set_pixel_transform(affine, width, height)
        self._since_readback = 0
        self._last_readback = time.perf_counter()

    def accumulate(self, samples: int, control: RenderControl) -> int:
        """Plot about `samples` iterations into the texture (reading back as needed); returns the number run."""
        gl = self.engine.gl
        self.population.bind()
        if not self._fused:
            self.population.iterate(self._fuse)
            self._fused = True
        draws = max(1, -(-samples // self.points))
        self._fbo.use()
        self.ctx.viewport = (0, 0, self._width, self._height)
        self.ctx.enable(gl.BLEND)
        self.ctx.blend_func = gl.ONE, gl.ONE
        done = 0
        for _ in range(draws):
            if not control.wait_if_paused():
                break
            self.population.iterate(1)
            self.population.plot()
            done += self.points
            self._since_readback += self.points
            if self._since_readback >= GPU_READBACK_SAMPLES or time.perf_counter() - self._last_readback >= GPU_READBACK_SECONDS:
                self._read_back()
        self.ctx.disable(gl.BLEND)
        return done

    def _read_back(self) -> None:
        self.ctx.finish()
        data = np.frombuffer(self._fbo.read(components=4, dtype="f4"), dtype=np.float32).reshape(self._height, self._width, 4)
        for ch in range(4):
            self._hist[ch] += data[..., ch]
        self._fbo.clear(0.0, 0.0, 0.0, 0.0)
        self._since_readback = 0
        self._last_readback = time.perf_counter()

    def histogram(self) -> np.ndarray:
        """The tile's histogram so far as (4, rows, cols) float64 (flushes the texture first)."""
        if self._since_readback:
            self._read_back()
        return self._hist

    def end_tile(self) -> None:
        """Release the tile's texture and histogram."""
        self._release_targets()
        self._hist = None

    def _release_targets(self) -> None:
        for obj in (self._fbo, self._tex):
            if obj is not None:
                obj.release()
        self._fbo = self._tex = None

    def close(self) -> None:
        """Free the GPU objects (and the context, if this sampler created it)."""
        self._release_targets()
        self.population.release()
        self._hist = None
        if self._owns_engine:
            self.engine.close()


def create_sampler(flame: Flame, compiled: CompiledFlame, engine: str, threads: int, seed: int, fuse: int) -> tuple[object, str]:
    """The sampler for an engine preference ("auto" / "gpu" / "cpu"); returns (sampler, note).

    The GPU is tried on the calling thread (contexts are thread-bound); any failure falls back to
    the CPU with a note saying why.
    """
    note = ""
    if engine in ("auto", "gpu"):
        try:
            from .gpu_engine import GpuEngine
            return GpuSampler(GpuEngine(), compiled, seed, fuse, owns_engine=True), note
        except Exception as exc:  # noqa: BLE001 - any GL failure → CPU
            reason = str(exc).splitlines()[0] if str(exc) else exc.__class__.__name__
            note = f"OpenGL unavailable ({reason}); rendered on the CPU"
    return CpuSampler(flame, threads or config.CPU_RENDER_THREADS, seed, fuse), note


__all__ = ["RenderControl", "CpuSampler", "GpuSampler", "create_sampler"]
