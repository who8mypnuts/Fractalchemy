"""Apophysis's spatial filter: the Gaussian kernel that sums supersampled buckets into output pixels.

Straight from `TImageMaker.CreateFilter` (Apophysis 7X) / `flam3_create_spatial_filter`:

    fw      = trunc(2 · FILTER_CUTOFF · oversample · radius)
    width   = fw + 1, made to have the parity of `oversample` (so the kernel is centred on a pixel's buckets)
    adjust  = FILTER_CUTOFF · width / fw
    w(i, j) = exp(−2 (ii² + jj²)),  ii = ((2i + 1) / width − 1) · adjust
    normalised to sum 1

Output pixel (x, y) gathers buckets (x·oversample + j − gutter, y·oversample + i − gutter) for i, j < width,
where gutter = (width − oversample) / 2; the histogram carries that many extra buckets on each side.
"""

from __future__ import annotations

import math

import numpy as np

FILTER_CUTOFF = 1.8


def filter_width(oversample: int, radius: float) -> int:
    """Side of the kernel in buckets."""
    oversample = max(1, int(oversample))
    fw = int(2.0 * FILTER_CUTOFF * oversample * max(0.0, radius))
    width = fw + 1
    if (width + oversample) % 2:
        width += 1
    return width


def kernel_adjust(oversample: int, radius: float) -> float:
    """The coordinate scale `adjust` of the kernel (1 when there is no filtering)."""
    fw = int(2.0 * FILTER_CUTOFF * max(1, int(oversample)) * max(0.0, radius))
    return FILTER_CUTOFF * filter_width(oversample, radius) / fw if fw > 0 else 1.0


def spatial_filter(oversample: int, radius: float) -> np.ndarray:
    """The normalised (width × width) kernel."""
    width = filter_width(oversample, radius)
    adjust = kernel_adjust(oversample, radius)
    coords = ((2.0 * np.arange(width) + 1.0) / width - 1.0) * adjust
    one_d = np.exp(-2.0 * coords * coords)
    kernel = np.outer(one_d, one_d)
    return kernel / kernel.sum()


def kernel_norm(oversample: int, radius: float) -> float:
    """1 / sum of the un-normalised weights (what the GLSL gather multiplies by)."""
    width = filter_width(oversample, radius)
    adjust = kernel_adjust(oversample, radius)
    total = 0.0
    for i in range(width):
        ii = ((2.0 * i + 1.0) / width - 1.0) * adjust
        for j in range(width):
            jj = ((2.0 * j + 1.0) / width - 1.0) * adjust
            total += math.exp(-2.0 * (ii * ii + jj * jj))
    return 1.0 / total


def bucket_transform(pixel_transform, oversample: int, gutter: int):
    """The affine taking fractal coordinates to *bucket* coordinates (pixel coords scaled, gutter added)."""
    a, b, c, d, e, f = pixel_transform
    return (a * oversample, b * oversample, c * oversample, d * oversample, e * oversample + gutter, f * oversample + gutter)
