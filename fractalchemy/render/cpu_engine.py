"""CPU preview engine: the chaos game vectorised with numpy and spread over threads.

Each worker thread owns an independent point population and a private histogram;
after every pass the partial histograms are summed and tone-mapped. numpy releases
the GIL inside its kernels, so the threads genuinely run in parallel. Arithmetic is
float64 — this engine is also the fallback when no OpenGL is available.
"""

from __future__ import annotations

import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

import numpy as np

from .. import config
from ..fractal.scene import Flame
from ..fractal.variations import Point
from .compiled import CompiledFlame, CompiledXForm
from .settings import RenderSettings, RenderStats
from .tonemap import ToneParams, tonemap

ITERATIONS_PER_CHUNK = 8      # plotted iterations between cancellation checks / histogram flushes
RESET_LIMIT = 1e10            # |x| beyond this (or NaN) re-seeds the point
SELECT_BINS = 1024            # resolution of the xform-selection lookup table (exact: see `_Worker._select`)


def thread_count() -> int:
    """Worker threads to use: the configured number, else one per core."""
    return config.CPU_RENDER_THREADS or max(1, os.cpu_count() or 1)


class CpuEngine:
    """Creates CPU render jobs."""
    name = "CPU"

    def __init__(self, threads: int | None = None):
        self.threads = threads or thread_count()

    def start(self, flame: Flame, settings: RenderSettings) -> "CpuRenderJob":
        return CpuRenderJob(flame, settings, self.threads)

    def close(self) -> None:
        pass


class CpuRenderJob:
    """One progressive render; call `run_pass()` repeatedly until `stats.finished`."""

    def __init__(self, flame: Flame, settings: RenderSettings, threads: int):
        self.settings = settings
        self.compiled = CompiledFlame.build(flame)
        self.threads = max(1, min(threads, settings.points // 256 or 1))
        self.ppu = flame.camera.pixels_per_unit(settings.width, settings.height)
        self.pixel_transform = flame.camera.pixel_transform(settings.width, settings.height)
        self.coloring = flame.coloring
        self.histogram = np.zeros((settings.height, settings.width, 4), dtype=np.float64)
        self.stats = RenderStats(engine=f"CPU (numpy, {self.threads} threads)", passes_total=settings.passes,
                                 width=settings.width, height=settings.height, notes=list(self.compiled.notes))
        per_thread = max(64, settings.points // self.threads)
        self._workers = [_Worker(self.compiled, per_thread, settings.seed * 7919 + i, self.pixel_transform,
                                 settings.width, settings.height) for i in range(self.threads)]
        self._pool = ThreadPoolExecutor(max_workers=self.threads, thread_name_prefix="render-cpu")
        self._elapsed = 0.0
        self._fused = False

    def run_pass(self, cancelled: Callable[[], bool] = lambda: False) -> np.ndarray | None:
        """Iterate one pass on all threads, merge, tone-map. Returns None if cancelled."""
        started = time.perf_counter()
        if not self._fused:
            list(self._pool.map(lambda w: w.fuse(self.settings.fuse), self._workers))
            self._fused = True
        per_worker = max(1, self.settings.samples_per_pass // self.threads)
        results = list(self._pool.map(lambda w: w.run(per_worker, cancelled), self._workers))
        if cancelled():
            return None
        for hist, samples, hits in results:
            self.histogram += hist
            self.stats.samples += samples
            self.stats.hits += hits
        self.stats.passes_done += 1
        self._elapsed += time.perf_counter() - started
        self.stats.seconds = self._elapsed
        return self.image()

    def image(self) -> np.ndarray:
        """The current histogram tone-mapped to RGBA8."""
        params = ToneParams.derive(self.coloring, self.ppu, self.stats.samples)
        return tonemap(self.histogram, params)

    def close(self) -> None:
        self._pool.shutdown(wait=False)


class _Worker:
    """One thread's point population and private histogram."""

    def __init__(self, compiled: CompiledFlame, points: int, seed: int, pixel_transform, width: int, height: int):
        self.compiled = compiled
        self.rng = np.random.default_rng(seed)
        self.x = self.rng.uniform(-1.0, 1.0, points)
        self.y = self.rng.uniform(-1.0, 1.0, points)
        self.c = self.rng.random(points)
        self.prev = np.zeros(points, dtype=np.intp)
        self.pixel_transform = pixel_transform
        self.width, self.height = width, height
        self.opacities = np.array([x.opacity for x in compiled.xforms])
        bins = np.arange(SELECT_BINS) / SELECT_BINS
        self._select_lut = np.stack([np.searchsorted(row, bins, side="right") for row in compiled.selection])

    def fuse(self, iterations: int) -> None:
        """Warm-up iterations that are not plotted (the population converges onto the attractor)."""
        for _ in range(iterations):
            self._step()

    def run(self, samples: int, cancelled: Callable[[], bool]) -> tuple[np.ndarray, int, int]:
        """Plot about `samples` iterations; returns (histogram, samples done, hits)."""
        hist = np.zeros(self.width * self.height * 4, dtype=np.float64)
        n = self.x.shape[0]
        done = hits = 0
        iterations = max(1, -(-samples // n))
        while done < iterations * n and not cancelled():
            chunk = min(ITERATIONS_PER_CHUNK, iterations - done // n)
            idx_parts, weight_parts, color_parts = [], [], []
            for _ in range(chunk):
                xi = self._step()
                idx, op, ci = self._project(xi)
                idx_parts.append(idx)
                weight_parts.append(op)
                color_parts.append(ci)
            idx = np.concatenate(idx_parts)
            op = np.concatenate(weight_parts)
            ci = np.concatenate(color_parts)
            hits += idx.shape[0]
            done += chunk * n
            if idx.shape[0]:
                palette = self.compiled.palette[ci]
                bins = self.width * self.height
                for ch in range(3):
                    hist[ch::4] += np.bincount(idx, weights=op * palette[:, ch], minlength=bins)[:bins]
                hist[3::4] += np.bincount(idx, weights=op, minlength=bins)[:bins]
        return hist.reshape(self.height, self.width, 4), done, hits

    # --- one iteration --------------------------------------------------------
    def _step(self) -> np.ndarray:
        """Advance every point by one chosen xform; returns the chosen xform indices."""
        xi = self._select(self.rng.random(self.x.shape[0]))
        for i, xform in enumerate(self.compiled.xforms):
            sel = np.nonzero(xi == i)[0]
            if sel.shape[0]:
                self.x[sel], self.y[sel], self.c[sel] = apply_xform(xform, self.x[sel], self.y[sel], self.c[sel], self.rng)
        bad = ~(np.abs(self.x) < RESET_LIMIT) | ~(np.abs(self.y) < RESET_LIMIT)
        if bad.any():
            k = int(bad.sum())
            self.x[bad] = self.rng.uniform(-1.0, 1.0, k)
            self.y[bad] = self.rng.uniform(-1.0, 1.0, k)
            self.c[bad] = self.rng.random(k)
        self.prev = xi
        return xi

    def _select(self, r: np.ndarray) -> np.ndarray:
        """The xform each point moves to: the first whose cumulative probability exceeds `r` (xaos row = previous xform).

        A lookup table on the top bits of `r` gives a lower bound; the few points whose bin straddles
        a boundary advance until the cumulative value is above `r`. Exact, and O(n) instead of O(n · xforms).
        """
        cum = self.compiled.selection
        xi = self._select_lut[self.prev, (r * SELECT_BINS).astype(np.intp)]
        last = cum.shape[1] - 1
        for _ in range(last):
            behind = (cum[self.prev, xi] <= r) & (xi < last)
            if not behind.any():
                break
            xi = xi + behind
        return xi

    def _project(self, xi: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Pixel indices, plot weights and palette indices of the points that land in the image."""
        x, y, c = self.x, self.y, self.c
        if self.compiled.final is not None:
            x, y, c = apply_xform(self.compiled.final, x, y, c, self.rng)
        a, b, cc, d, e, f = self.pixel_transform
        px = a * x + cc * y + e
        py = b * x + d * y + f
        op = self.opacities[xi]
        inside = (px >= 0) & (px < self.width) & (py >= 0) & (py < self.height) & (op > 0)
        sel = np.nonzero(inside)[0]
        idx = py[sel].astype(np.intp) * self.width + px[sel].astype(np.intp)
        ci = np.clip(c[sel] * 255.0 + 0.5, 0, 255).astype(np.intp)
        return idx, op[sel], ci


def apply_xform(xform: CompiledXForm, x: np.ndarray, y: np.ndarray, c: np.ndarray, rng: np.random.Generator):
    """Map arrays of points through one xform (affine → variations → post affine, colour blend)."""
    a, b, cc, d, e, f = xform.coefs
    tx = a * x + cc * y + e
    ty = b * x + d * y + f
    if xform.pre_blur:
        ang = rng.random(x.shape[0]) * 2.0 * np.pi
        k = xform.pre_blur * (rng.random(x.shape[0]) + rng.random(x.shape[0]) + rng.random(x.shape[0]) + rng.random(x.shape[0]) - 2.0)
        tx = tx + k * np.cos(ang)
        ty = ty + k * np.sin(ang)
    vx = np.zeros_like(tx)
    vy = np.zeros_like(ty)
    for cv in xform.variations:
        dx, dy = cv.variation.numpy(Point(tx, ty, cv.weight, xform.coefs, cv.params, rng))
        vx += dx
        vy += dy
    if xform.has_post:
        a, b, cc, d, e, f = xform.post
        vx, vy = a * vx + cc * vy + e, b * vx + d * vy + f
    speed = xform.color_speed
    return vx, vy, c * (1.0 - speed) + xform.color * speed
