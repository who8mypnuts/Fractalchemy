"""The final renderer: precise, tiled, filtered, with progress and previews — the counterpart of the preview engine.

    renderer = FinalRenderer(flame, settings, control)
    result = renderer.run(progress)        # blocks; `progress(FinalProgress)` is called along the way

Per tile (see `final_settings.plan_tiles`): the sampler accumulates `quality × width × height`
iterations into the tile's bucket histogram (gutter included), then the histogram is log-scaled
(`tonemap.log_scale`), optionally density-estimated, reduced to pixels through the chosen
reconstruction filter (`filters.downsample`), and finished with gamma / vibrancy / background
(`tonemap.finish`) into the 16-bit output image. Image-space denoisers run once on the whole
picture at the end. Every phase reports progress; previews are a small canvas of the whole image
that fills in tile by tile.

Cancelling with `save_incomplete` finishes the current tile with the samples it has (correctly
exposed, just noisier) and leaves the remaining tiles as background, so a long render that is
stopped early still yields a usable picture.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable

import numpy as np

from ..fractal.scene import Flame
from .compiled import CompiledFlame
from .denoise import denoise, denoiser_kind
from .filters import density_estimate, downsample, filter_kind, make_taps
from .final_settings import FinalRenderSettings, Tile, TilePlan, plan_tiles
from .preview_canvas import PreviewCanvas
from .control import RenderControl
from .samplers import Sampler, create_sampler
from .tonemap import ToneParams, finish, log_scale

PREVIEW_MIN_INTERVAL = 1.0          # seconds between preview updates (scaled by how long one takes)
FIRST_BATCH = 1 << 21               # samples per sampler call to start with; then ~BATCH_SECONDS worth
BATCH_SECONDS = 1.5
LOG_SCALE_ROWS = 1 << 20            # buckets per chunk when log-scaling (bounds the float64 temporaries)
PHASE_RENDER, PHASE_FILTER, PHASE_DENOISE, PHASE_SAVE, PHASE_DONE, PHASE_CANCELLED = (
    "Rendering", "Filtering", "Denoising", "Saving", "Finished", "Stopped")
POST_SECONDS_PER_BUCKET = 2e-8      # first guess for the filter phase before it has been measured


@dataclass
class FinalProgress:
    """A progress report for the Render window.

    Attributes:
        phase: One of the PHASE_* strings.
        fraction: Overall progress 0..1.
        tile, tiles: Current tile (1-based) and the tile count.
        samples_done, samples_total: Iterations over the whole render.
        elapsed: Seconds spent (pauses excluded).
        remaining: Estimated seconds to go, or None before a rate is known.
        rate: Samples per second measured so far.
        engine: Sampler name.
        engine_kind: "gpu" or "cpu".
        preview: RGBA8 (h, w, 4) canvas of the whole image so far, or None if unchanged.
    """
    phase: str = PHASE_RENDER
    fraction: float = 0.0
    tile: int = 0
    tiles: int = 0
    samples_done: int = 0
    samples_total: int = 0
    elapsed: float = 0.0
    remaining: float | None = None
    rate: float = 0.0
    engine: str = ""
    engine_kind: str = "cpu"
    preview: np.ndarray | None = None


@dataclass
class TileStats:
    """Facts about one rendered tile (for the render report).

    Attributes:
        index: 0-based tile number.
        pixel_rect: (x, y, width, height) of the output pixels it produced.
        buckets: Buckets accumulated, gutter included.
        samples: Iterations run for it.
        render_seconds, filter_seconds: Time sampling and time filtering / tone-mapping.
        hits: Opacity-weighted points that landed in the tile (gutter included).
        lit_buckets: Buckets hit at least once.
        max_count: Largest bucket count.
    """
    index: int
    pixel_rect: tuple[int, int, int, int]
    buckets: int
    samples: int
    render_seconds: float
    filter_seconds: float = 0.0
    hits: float = 0.0
    lit_buckets: int = 0
    max_count: float = 0.0

    def record_hits(self, counts: np.ndarray) -> None:
        """Fill the hit statistics from the tile's count plane (one pass)."""
        self.hits = float(counts.sum())
        self.lit_buckets = int(np.count_nonzero(counts))
        self.max_count = float(counts.max()) if counts.size else 0.0


@dataclass
class FinalResult:
    """What a render produced.

    Attributes:
        image: (H, W, 4) uint16 RGBA.
        complete: False if the render was stopped early (then `image` holds what was finished).
        seconds: Render time (pauses excluded).
        samples: Iterations run.
        engine: Sampler name.
        notes: Remarks (engine fallback, ignored variations, …).
        settings: The settings used.
        tiles: Per-tile statistics, in render order (tiles never started are absent).
        plan: The tile plan followed.
        started_at, finished_at: Wall-clock times (`time.time()`).
        paused_seconds: Time spent paused.
        denoise_seconds: Time of the image-space denoiser (0 when none ran).
        engine_kind: "gpu" or "cpu".
        device: The GPU renderer string or the processor.
        workers: CPU worker processes (0 on the GPU).
    """
    image: np.ndarray
    complete: bool
    seconds: float
    samples: int
    engine: str
    notes: list[str] = field(default_factory=list)
    settings: FinalRenderSettings = field(default_factory=FinalRenderSettings)
    tiles: list[TileStats] = field(default_factory=list)
    plan: TilePlan | None = None
    started_at: float = 0.0
    finished_at: float = 0.0
    paused_seconds: float = 0.0
    denoise_seconds: float = 0.0
    engine_kind: str = "cpu"
    device: str = ""
    workers: int = 0

    @property
    def sampling_seconds(self) -> float:
        """Time spent in the chaos game over all tiles."""
        return sum(t.render_seconds for t in self.tiles)

    @property
    def filter_seconds(self) -> float:
        """Time spent filtering and tone-mapping over all tiles."""
        return sum(t.filter_seconds for t in self.tiles)


ProgressCallback = Callable[[FinalProgress], None]


class _Clock:
    """Time and throughput bookkeeping for one render: elapsed (pauses excluded), phase times, rate and ETA."""

    def __init__(self, control: RenderControl, samples_total: int, tiles: int, started: float | None = None):
        self.control = control
        self.samples_total = samples_total
        self.tiles = tiles
        self.started = time.perf_counter() if started is None else started
        self.started_wall = time.time() - (time.perf_counter() - self.started)
        self.samples_done = 0
        self.sampling_seconds = 0.0
        self.post_seconds: list[float] = []
        self.denoise_seconds = 0.0

    def elapsed(self) -> float:
        """Seconds since the start, pauses excluded."""
        return time.perf_counter() - self.started - self.control.paused_seconds

    def add_samples(self, samples: int, seconds: float) -> None:
        """Account for a sampling batch."""
        self.samples_done += samples
        self.sampling_seconds += seconds

    @property
    def rate(self) -> float:
        """Samples per second of sampling so far (0 before any)."""
        return self.samples_done / self.sampling_seconds if self.sampling_seconds > 0 else 0.0

    def fraction(self, tiles_done: int, samples_in_tile: int) -> float:
        """Overall progress 0..1 by samples."""
        per_tile = self.samples_total / max(1, self.tiles)
        return min(1.0, (tiles_done * per_tile + samples_in_tile) / max(1, self.samples_total))

    def remaining(self, phase: str, tile: int, first_tile_buckets: int) -> float | None:
        """Estimated seconds to go: sampling left at the measured rate plus the timed filter phases of the tiles left."""
        if phase in (PHASE_DONE, PHASE_CANCELLED):
            return 0.0
        if self.rate <= 0:
            return None
        render_left = (self.samples_total - self.samples_done) / self.rate
        per_tile = (sum(self.post_seconds) / len(self.post_seconds) if self.post_seconds
                    else POST_SECONDS_PER_BUCKET * first_tile_buckets)
        tiles_left = self.tiles - (tile if phase == PHASE_FILTER else tile - 1)
        return max(0.0, render_left + per_tile * max(0, tiles_left))


class FinalRenderer:
    """Runs one final render on the calling thread (the GPU context, if any, is created here)."""

    def __init__(self, flame: Flame, settings: FinalRenderSettings, control: RenderControl | None = None):
        self.flame = flame.copy()
        self.settings = settings
        self.control = control or RenderControl()
        self.compiled = CompiledFlame.build(self.flame)
        self.notes = list(self.compiled.notes)
        self.camera = self.flame.camera.at_size(settings.width, settings.height)
        self.ppu = self.camera.pixels_per_unit(settings.width, settings.height)
        self.taps = make_taps(filter_kind(settings.filter_kind), settings.filter_radius, settings.oversample)
        self.sampler: Sampler | None = None
        self.plan: TilePlan | None = None
        self.clock: _Clock | None = None
        self._tile_stats: list[TileStats] = []
        self._preview = PreviewCanvas(settings, self.flame.coloring)
        self._last_preview = 0.0
        self._preview_cost = 0.0

    # --- driving ------------------------------------------------------------------------
    def run(self, progress: ProgressCallback = lambda p: None) -> FinalResult:
        """Render to completion (or cancellation); always closes the sampler."""
        started = time.perf_counter()
        self.sampler, note = create_sampler(self.flame, self.compiled, self.settings.engine, self.settings.cpu_threads,
                                            self.settings.seed, self.settings.fuse)
        if note:
            self.notes.append(note)
        try:
            self.plan = plan_tiles(self.settings, gpu=self.sampler.is_gpu, max_texture=self.sampler.max_side)
            self.clock = _Clock(self.control, self.settings.samples_per_tile * self.plan.count, self.plan.count, started)
            return self._render(progress)
        finally:
            self.sampler.close()

    def _render(self, progress: ProgressCallback) -> FinalResult:
        image = self._blank_image()
        complete = True
        for index, tile in enumerate(self.plan.tiles):
            stats = self._render_tile(index, tile, progress)
            stopped = self.control.cancelled()
            if not stopped or self.settings.save_incomplete:
                self._post_process_tile(index, tile, stats, image, progress)
            if stopped:
                complete = False
                break
        if complete:
            self._denoise(image, progress)
        result = self._result(image, complete)
        progress(self._progress(PHASE_DONE if complete else PHASE_CANCELLED, 1.0, self.plan.count, preview=True))
        return result

    def _blank_image(self) -> np.ndarray:
        s = self.settings
        image = np.zeros((s.height, s.width, 4), dtype=np.uint16)
        if not s.transparent:
            bg = [int(round(c / 255.0 * 65535)) for c in self.flame.coloring.background]
            image[...] = np.array(bg + [65535], dtype=np.uint16)
        return image

    def _result(self, image: np.ndarray, complete: bool) -> FinalResult:
        clock = self.clock
        return FinalResult(image, complete, clock.elapsed(), clock.samples_done, self.sampler.name, self.notes, self.settings,
                           self._tile_stats, self.plan, clock.started_wall, time.time(), self.control.paused_seconds,
                           clock.denoise_seconds, self.sampler.kind, self.sampler.device, self.sampler.workers)

    def _render_tile(self, index: int, tile: Tile, progress: ProgressCallback) -> TileStats:
        """Accumulate the tile's samples in batches, reporting between them."""
        s = self.settings
        width, height = tile.padded_size
        self.sampler.begin_tile(self._tile_affine(tile), width, height)
        target = s.samples_per_tile
        done = 0
        batch = FIRST_BATCH
        tile_started = self.clock.elapsed()
        while done < target and not self.control.cancelled():
            started = time.perf_counter()
            ran = self.sampler.accumulate(min(batch, target - done), self.control)
            took = time.perf_counter() - started
            done += ran
            self.clock.add_samples(ran, took)
            if took > 0 and ran > 0:
                batch = int(min(1 << 30, max(1 << 18, ran * BATCH_SECONDS / took)))
            progress(self._progress(PHASE_RENDER, self.clock.fraction(index, done), index + 1,
                                    preview=self._preview_due(tile, done)))
        stats = TileStats(index, tile.pixel_rect(s.oversample), tile.buckets, done, self.clock.elapsed() - tile_started)
        self._tile_stats.append(stats)
        return stats

    def _preview_due(self, tile: Tile, samples: int) -> bool:
        now = time.perf_counter()
        if now - self._last_preview < max(PREVIEW_MIN_INTERVAL, 5.0 * self._preview_cost):
            return False
        started = now
        self._preview.tile_from_histogram(self.sampler.histogram(), tile, self.ppu * self.settings.oversample, samples)
        self._preview_cost = time.perf_counter() - started
        self._last_preview = time.perf_counter()
        return True

    def _post_process_tile(self, index: int, tile: Tile, stats: TileStats, image: np.ndarray, progress: ProgressCallback) -> None:
        """Log-scale → density estimation → reconstruction filter → gamma; paste into the image."""
        started = time.perf_counter()
        progress(self._progress(PHASE_FILTER, self.clock.fraction(index, self.settings.samples_per_tile), index + 1))
        params = ToneParams.derive(self.flame.coloring, self.ppu * self.settings.oversample, max(1, stats.samples))
        histogram = self.sampler.histogram()
        stats.record_hits(histogram[3])
        scaled = _log_scale_planar(histogram, params)
        de = self.settings.density_estimation
        if de is not None:
            scaled = density_estimate(scaled, histogram[3], self.settings.oversample, de)
        self.sampler.end_tile()
        px, py, pw, ph = tile.pixel_rect(self.settings.oversample)
        pixels = downsample(scaled, self.taps, tile.gutter, pw, ph)
        del scaled
        rgba = finish(pixels, params, self.settings.transparent)
        image[py:py + ph, px:px + pw] = (rgba * 65535.0 + 0.5).astype(np.uint16)
        self._preview.tile_from_pixels(rgba, px, py)
        stats.filter_seconds = time.perf_counter() - started
        self.clock.post_seconds.append(stats.filter_seconds)
        progress(self._progress(PHASE_FILTER, self.clock.fraction(index + 1, 0), index + 1, preview=True))

    def _denoise(self, image: np.ndarray, progress: ProgressCallback) -> None:
        kind = denoiser_kind(self.settings.denoiser)
        if kind.key in ("none", "density") or not kind.available:
            return
        started = time.perf_counter()
        progress(self._progress(PHASE_DENOISE, 1.0, self.plan.count))
        rgb = image[..., :3].astype(np.float32) / 65535.0
        rgb = denoise(rgb, kind.key, self.settings.denoise_strength)
        image[..., :3] = (np.clip(rgb, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)
        self.clock.denoise_seconds = time.perf_counter() - started
        self._preview.whole(image)

    # --- geometry -----------------------------------------------------------------------
    def _tile_affine(self, tile: Tile) -> tuple[float, ...]:
        """Affine from fractal space to the tile's padded bucket grid."""
        os_ = self.settings.oversample
        a, b, c, d, e, f = self.camera.pixel_transform(self.settings.width, self.settings.height)
        return (a * os_, b * os_, c * os_, d * os_,
                e * os_ - (tile.x0 - tile.gutter), f * os_ - (tile.y0 - tile.gutter))

    # --- progress -----------------------------------------------------------------------
    def _progress(self, phase: str, fraction: float, tile: int, preview: bool = False) -> FinalProgress:
        clock = self.clock
        return FinalProgress(phase, fraction, tile, self.plan.count, clock.samples_done, clock.samples_total, clock.elapsed(),
                             clock.remaining(phase, tile, self.plan.tiles[0].buckets), clock.rate, self.sampler.name,
                             self.sampler.kind, self._preview.canvas() if preview else None)


def _log_scale_planar(histogram: np.ndarray, params: ToneParams) -> np.ndarray:
    """`tonemap.log_scale` for a planar (4, rows, cols) histogram, in row chunks to bound temporaries."""
    _, rows, cols = histogram.shape
    out = np.empty((rows, cols, 4), dtype=np.float32)
    step = max(1, LOG_SCALE_ROWS // max(1, cols))
    for r0 in range(0, rows, step):
        chunk = histogram[:, r0:r0 + step]
        interleaved = np.moveaxis(chunk, 0, -1)
        out[r0:r0 + step] = log_scale(interleaved, params)
    return out


__all__ = ["FinalRenderer", "FinalProgress", "FinalResult", "TileStats", "PHASE_RENDER", "PHASE_FILTER", "PHASE_DENOISE",
           "PHASE_SAVE", "PHASE_DONE", "PHASE_CANCELLED"]
