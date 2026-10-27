"""The small picture of the whole render that fills in tile by tile while the final renderer works.

While a tile is being sampled its histogram is block-averaged and tone-mapped into the tile's
rectangle of the canvas; once the tile is filtered, its finished pixels replace that; after an
image-space denoiser, the whole image does. Transparent renders are composited over the
background colour so the preview looks like the saved file would on a plain backdrop.
"""

from __future__ import annotations

import numpy as np

from .final_settings import FinalRenderSettings, Tile
from .tonemap import ToneParams, tonemap

PREVIEW_WIDTH = 512


class PreviewCanvas:
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


__all__ = ["PreviewCanvas", "PREVIEW_WIDTH"]
