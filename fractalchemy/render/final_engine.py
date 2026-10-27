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
from .samplers import RenderControl, create_sampler
from .tonemap import ToneParams, finish, log_scale, tonemap

PREVIEW_WIDTH = 512
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


ProgressCallback = Callable[[FinalProgress], None]


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
        self.sampler = None
        self.plan: TilePlan | None = None
        self._started = 0.0
        self._started_wall = 0.0
        self._render_seconds = 0.0
        self._post_seconds: list[float] = []
        self._tile_stats: list[TileStats] = []
        self._denoise_seconds = 0.0
        self._samples_done = 0
        self._preview = _Preview(settings, self.flame.coloring)
        self._last_preview = 0.0
        self._preview_cost = 0.0

    # --- driving ------------------------------------------------------------------------
    def run(self, progress: ProgressCallback = lambda p: None) -> FinalResult:
        """Render to completion (or cancellation); always closes the sampler."""
        self._started = time.perf_counter()
        self._started_wall = time.time()
        self.sampler, note = create_sampler(self.flame, self.compiled, self.settings.engine, self.settings.cpu_threads,
                                            self.settings.seed, self.settings.fuse)
        if note:
            self.notes.append(note)
        try:
            return self._render(progress)
        finally:
            self.sampler.close()

    def _render(self, progress: ProgressCallback) -> FinalResult:
        s = self.settings
        self.plan = plan_tiles(s, gpu=self.sampler.is_gpu, max_texture=self.sampler.max_side)
        image = np.zeros((s.height, s.width, 4), dtype=np.uint16)
        if not s.transparent:
            bg = [int(round(c / 255.0 * 65535)) for c in self.flame.coloring.background]
            image[...] = np.array(bg + [65535], dtype=np.uint16)
        complete = True
        for index, tile in enumerate(self.plan.tiles):
            samples = self._render_tile(index, tile, progress)
            stopped = self.control.cancelled()
            if stopped and not s.save_incomplete:
                complete = False
                break
            self._post_process_tile(index, tile, samples, image, progress)
            if stopped:
                complete = False
                break
        if complete:
            self._denoise(image, progress)
        result = FinalResult(image, complete, self._elapsed(), self._samples_done, self.sampler.name, self.notes, s,
                             self._tile_stats, self.plan, self._started_wall, time.time(), self.control.paused_seconds,
                             self._denoise_seconds)
        progress(self._progress(PHASE_DONE if complete else PHASE_CANCELLED, 1.0, len(self.plan.tiles), preview=True))
        return result

    def _render_tile(self, index: int, tile: Tile, progress: ProgressCallback) -> int:
        """Accumulate the tile's samples in batches, reporting between them; returns samples run."""
        s = self.settings
        width, height = tile.padded_size
        self.sampler.begin_tile(self._tile_affine(tile), width, height)
        target = s.samples_per_tile
        done = 0
        batch = FIRST_BATCH
        tile_started = self._elapsed()
        while done < target and not self.control.cancelled():
            started = time.perf_counter()
            ran = self.sampler.accumulate(min(batch, target - done), self.control)
            took = time.perf_counter() - started
            done += ran
            self._samples_done += ran
            self._render_seconds = self._elapsed() - sum(self._post_seconds)
            if took > 0 and ran > 0:
                batch = int(min(1 << 30, max(1 << 18, ran * BATCH_SECONDS / took)))
            progress(self._progress(PHASE_RENDER, self._fraction(index, done), index + 1, preview=self._preview_due(tile, done)))
        self._tile_stats.append(TileStats(index, tile.pixel_rect(s.oversample), tile.buckets, done, self._elapsed() - tile_started))
        return done

    def _preview_due(self, tile: Tile, samples: int) -> bool:
        now = time.perf_counter()
        if now - self._last_preview < max(PREVIEW_MIN_INTERVAL, 5.0 * self._preview_cost):
            return False
        started = now
        self._preview.tile_from_histogram(self.sampler.histogram(), tile, self.ppu * self.settings.oversample, samples)
        self._preview_cost = time.perf_counter() - started
        self._last_preview = time.perf_counter()
        return True

    def _post_process_tile(self, index: int, tile: Tile, samples: int, image: np.ndarray, progress: ProgressCallback) -> None:
        """Log-scale → density estimation → reconstruction filter → gamma; paste into the image."""
        started = time.perf_counter()
        progress(self._progress(PHASE_FILTER, self._fraction(index, self.settings.samples_per_tile), index + 1))
        params = ToneParams.derive(self.flame.coloring, self.ppu * self.settings.oversample, max(1, samples))
        histogram = self.sampler.histogram()
        self._record_histogram(histogram)
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
        self._post_seconds.append(time.perf_counter() - started)
        self._tile_stats[-1].filter_seconds = self._post_seconds[-1]
        progress(self._progress(PHASE_FILTER, self._fraction(index + 1, 0), index + 1, preview=True))

    def _record_histogram(self, histogram: np.ndarray) -> None:
        """Hit statistics of the current tile (one pass over the count plane)."""
        counts = histogram[3]
        stats = self._tile_stats[-1]
        stats.hits = float(counts.sum())
        stats.lit_buckets = int(np.count_nonzero(counts))
        stats.max_count = float(counts.max()) if counts.size else 0.0

    def _denoise(self, image: np.ndarray, progress: ProgressCallback) -> None:
        kind = denoiser_kind(self.settings.denoiser)
        if kind.key in ("none", "density") or not kind.available:
            return
        started = time.perf_counter()
        progress(self._progress(PHASE_DENOISE, 1.0, len(self.plan.tiles)))
        rgb = image[..., :3].astype(np.float32) / 65535.0
        rgb = denoise(rgb, kind.key, self.settings.denoise_strength)
        image[..., :3] = (np.clip(rgb, 0.0, 1.0) * 65535.0 + 0.5).astype(np.uint16)
        self._denoise_seconds = time.perf_counter() - started
        self._preview.whole(image)

    # --- geometry -----------------------------------------------------------------------
    def _tile_affine(self, tile: Tile) -> tuple[float, ...]:
        """Affine from fractal space to the tile's padded bucket grid."""
        os_ = self.settings.oversample
        a, b, c, d, e, f = self.camera.pixel_transform(self.settings.width, self.settings.height)
        return (a * os_, b * os_, c * os_, d * os_,
                e * os_ - (tile.x0 - tile.gutter), f * os_ - (tile.y0 - tile.gutter))

    # --- progress -----------------------------------------------------------------------
    def _elapsed(self) -> float:
        return time.perf_counter() - self._started - self.control.paused_seconds

    def _fraction(self, tiles_done: int, samples_in_tile: int) -> float:
        total = self.settings.samples_per_tile * len(self.plan.tiles)
        return min(1.0, (tiles_done * self.settings.samples_per_tile + samples_in_tile) / max(1, total))

    def _progress(self, phase: str, fraction: float, tile: int, preview: bool = False) -> FinalProgress:
        total = self.settings.samples_per_tile * len(self.plan.tiles)
        rate = self._samples_done / self._render_seconds if self._render_seconds > 0 else 0.0
        remaining = None
        if phase in (PHASE_DONE, PHASE_CANCELLED):
            remaining = 0.0
        elif rate > 0:
            render_left = (total - self._samples_done) / rate
            per_tile = (sum(self._post_seconds) / len(self._post_seconds) if self._post_seconds
                        else POST_SECONDS_PER_BUCKET * self.plan.tiles[0].buckets)
            tiles_left = len(self.plan.tiles) - (tile if phase == PHASE_FILTER else tile - 1)
            remaining = max(0.0, render_left + per_tile * max(0, tiles_left))
        return FinalProgress(phase, fraction, tile, len(self.plan.tiles), self._samples_done, total, self._elapsed(),
                             remaining, rate, self.sampler.name, self._preview.canvas() if preview else None)


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


class _Preview:
    """A small RGBA8 canvas of the whole image, updated tile by tile."""

    def __init__(self, settings: FinalRenderSettings, coloring):
        self.settings = settings
        self.coloring = coloring
        self.width = max(1, min(PREVIEW_WIDTH, settings.width))
        self.height = max(1, int(round(settings.height * self.width / settings.width)))
        self.scale = self.width / settings.width
        self._canvas = np.zeros((self.height, self.width, 4), dtype=np.uint8)
        self._canvas[..., :3] = np.array(coloring.background, dtype=np.uint8)
        self._canvas[..., 3] = 255

    def canvas(self) -> np.ndarray:
        """A copy of the canvas."""
        return self._canvas.copy()

    def _rect(self, px: int, py: int, pw: int, ph: int) -> tuple[int, int, int, int]:
        x0, y0 = int(round(px * self.scale)), int(round(py * self.scale))
        x1, y1 = int(round((px + pw) * self.scale)), int(round((py + ph) * self.scale))
        return x0, y0, max(x1, x0 + 1) - x0, max(y1, y0 + 1) - y0

    def tile_from_histogram(self, histogram: np.ndarray, tile: Tile, bucket_ppu: float, samples: int) -> None:
        """Tone-map a block-averaged view of the tile's interior into its preview rectangle."""
        os_ = self.settings.oversample
        px, py, pw, ph = tile.pixel_rect(os_)
        x0, y0, w, h = self._rect(px, py, pw, ph)
        g = tile.gutter
        interior = histogram[:, g:g + tile.height, g:g + tile.width]
        mean = _block_means(interior, h, w)
        params = ToneParams.derive(self.coloring, bucket_ppu, max(1, samples))
        self._canvas[y0:y0 + h, x0:x0 + w] = tonemap(np.moveaxis(mean, 0, -1), params)

    def tile_from_pixels(self, rgba: np.ndarray, px: int, py: int) -> None:
        """Replace the tile's preview with its finished pixels (nearest-neighbour, composited over the background)."""
        ph, pw = rgba.shape[:2]
        x0, y0, w, h = self._rect(px, py, pw, ph)
        ys = np.minimum((np.arange(h) * ph / h).astype(int), ph - 1)
        xs = np.minimum((np.arange(w) * pw / w).astype(int), pw - 1)
        self._canvas[y0:y0 + h, x0:x0 + w] = self._composite(rgba[ys][:, xs])

    def whole(self, image: np.ndarray) -> None:
        """Replace the whole preview from the (H, W, 4) uint16 image."""
        ys = np.minimum((np.arange(self.height) / self.scale).astype(int), image.shape[0] - 1)
        xs = np.minimum((np.arange(self.width) / self.scale).astype(int), image.shape[1] - 1)
        self._canvas[...] = self._composite(image[ys][:, xs].astype(np.float32) / 65535.0)

    def _composite(self, rgba: np.ndarray) -> np.ndarray:
        """RGBA8 for the canvas; straight-alpha (transparent) renders are shown over the background colour."""
        if not self.settings.transparent:
            return _to_rgba8(rgba)
        alpha = rgba[..., 3:4]
        background = np.asarray(self.coloring.background, dtype=np.float32) / 255.0
        out = np.empty_like(rgba)
        out[..., :3] = rgba[..., :3] * alpha + background * (1.0 - alpha)
        out[..., 3] = 1.0
        return _to_rgba8(out)


def _block_means(planes: np.ndarray, rows: int, cols: int) -> np.ndarray:
    """Average a (4, R, C) array down to (4, rows, cols) over variable-size blocks."""
    _, R, C = planes.shape
    row_edges = np.minimum((np.arange(rows) * R // rows), R - 1)
    col_edges = np.minimum((np.arange(cols) * C // cols), C - 1)
    sums = np.add.reduceat(np.add.reduceat(planes, row_edges, axis=1), col_edges, axis=2)
    row_sizes = np.diff(np.append(row_edges, R))
    col_sizes = np.diff(np.append(col_edges, C))
    return sums / (row_sizes[:, None] * col_sizes[None, :])[None]


def _to_rgba8(rgba: np.ndarray) -> np.ndarray:
    return (np.clip(rgba, 0.0, 1.0) * 255.0 + 0.5).astype(np.uint8)


__all__ = ["FinalRenderer", "FinalProgress", "FinalResult", "TileStats", "PHASE_RENDER", "PHASE_FILTER", "PHASE_DENOISE",
           "PHASE_SAVE", "PHASE_DONE", "PHASE_CANCELLED"]
