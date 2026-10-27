"""Spatial filtering for the final renderer: oversample reconstruction filters and density estimation.

The final renderer accumulates `oversample × oversample` buckets per output pixel. Turning buckets
into pixels is a *reconstruction filter* — the anti-aliasing choice Chaotica exposes and Apophysis
fixes to a Gaussian. Every filter here is a 1-D profile `f(u)` (u in output pixels, scaled by the
user's radius) applied separably, so a 2-D kernel is never materialised and cost is `taps × buckets`.

Density estimation (flam3's `estimator` / `estimator_minimum` / `estimator_curve`) blurs sparsely
hit buckets with wide kernels and dense ones hardly at all. flam3 scatters every bucket through its
own kernel; this implementation gets the same result by splitting buckets into a handful of kernel
*levels* (geometric widths), blurring each level's share once and summing — a few separable blurs
instead of one variable kernel per bucket, which is what makes it viable in numpy.

Everything works on (rows, cols, channels) float arrays and is independent of the tone map, so
`tests/test_final_render.py` can check normalisation, energy conservation and symmetry directly.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

try:  # scipy's C blur is ~10x faster than the numpy fallback for density estimation
    from scipy.ndimage import gaussian_filter1d as _scipy_gaussian1d
except Exception:  # noqa: BLE001 - scipy is optional
    _scipy_gaussian1d = None

GAUSSIAN_CUTOFF = 1.8   # Apophysis FILTER_CUTOFF: the Gaussian is truncated at 1.8 radii


@dataclass(frozen=True)
class FilterKind:
    """One reconstruction filter.

    Attributes:
        key: Identifier stored in settings.
        label: Name shown in the UI.
        support: Half-width of the profile in output pixels at radius 1.
        profile: `f(u)` for |u| < support (not necessarily normalised).
        default_radius: Radius that gives the filter its textbook shape.
        description: One-line character note for tooltips.
    """
    key: str
    label: str
    support: float
    profile: Callable[[np.ndarray], np.ndarray]
    default_radius: float
    description: str


def _box(u):
    return (np.abs(u) < 0.5).astype(np.float64)


def _triangle(u):
    return np.maximum(0.0, 1.0 - np.abs(u))


def _gaussian(u):
    return np.where(np.abs(u) < GAUSSIAN_CUTOFF, np.exp(-2.0 * u * u), 0.0)


def _blackman_harris(u):
    x = np.clip(u / 1.5, -1.0, 1.0) * 0.5 + 0.5   # window over [-1.5, 1.5]
    w = (0.35875 - 0.48829 * np.cos(2 * np.pi * x) + 0.14128 * np.cos(4 * np.pi * x) - 0.01168 * np.cos(6 * np.pi * x))
    return np.where(np.abs(u) < 1.5, w, 0.0)


def _cubic(b: float, c: float):
    """Mitchell-Netravali family (B, C): Mitchell 1/3, 1/3 · Catmull-Rom 0, 1/2 · B-spline 1, 0."""
    def f(u):
        x = np.abs(u)
        near = ((12 - 9 * b - 6 * c) * x ** 3 + (-18 + 12 * b + 6 * c) * x ** 2 + (6 - 2 * b)) / 6.0
        far = ((-b - 6 * c) * x ** 3 + (6 * b + 30 * c) * x ** 2 + (-12 * b - 48 * c) * x + (8 * b + 24 * c)) / 6.0
        return np.where(x < 1, near, np.where(x < 2, far, 0.0))
    return f


def _lanczos(a: int):
    def f(u):
        x = np.asarray(u, dtype=np.float64)
        return np.where(np.abs(x) < a, np.sinc(x) * np.sinc(x / a), 0.0)
    return f


FILTERS: tuple[FilterKind, ...] = (
    FilterKind("gaussian", "Gaussian (Apophysis)", GAUSSIAN_CUTOFF, _gaussian, 0.5, "Soft and smooth; Apophysis's filter"),
    FilterKind("box", "Box", 0.5, _box, 1.0, "Plain average of the oversampled buckets; sharpest, may alias"),
    FilterKind("triangle", "Triangle (tent)", 1.0, _triangle, 1.0, "Bilinear blend; sharp with mild smoothing"),
    FilterKind("mitchell", "Mitchell-Netravali", 2.0, _cubic(1 / 3, 1 / 3), 1.0, "Balanced cubic; Chaotica's default style"),
    FilterKind("catmull_rom", "Catmull-Rom", 2.0, _cubic(0.0, 0.5), 1.0, "Crisp cubic with slight sharpening"),
    FilterKind("bspline", "B-spline (cubic)", 2.0, _cubic(1.0, 0.0), 1.0, "Softest cubic; never rings"),
    FilterKind("lanczos2", "Lanczos 2", 2.0, _lanczos(2), 1.0, "Windowed sinc; sharp, may ring at hard edges"),
    FilterKind("lanczos3", "Lanczos 3", 3.0, _lanczos(3), 1.0, "Sharpest; strongest ringing"),
    FilterKind("blackman_harris", "Blackman-Harris", 1.5, _blackman_harris, 1.0, "Very smooth window; no ringing"),
)
FILTER_BY_KEY = {f.key: f for f in FILTERS}


def filter_kind(key: str) -> FilterKind:
    """The filter for a settings key (unknown keys fall back to the Gaussian)."""
    return FILTER_BY_KEY.get(key, FILTERS[0])


# --- oversample downsampling --------------------------------------------------------------------
@dataclass(frozen=True)
class Taps:
    """A 1-D strided kernel: output pixel X sums `weights[i] · buckets[os·X + offsets[i]]`."""
    offsets: np.ndarray     # int, relative to the first bucket of the pixel's block
    weights: np.ndarray     # float64, sums to 1
    block: int              # buckets per pixel (the oversample)

    @property
    def reach(self) -> int:
        """Buckets needed beyond the image on either side (the gutter this kernel requires)."""
        return int(max(-self.offsets.min(), 0, self.offsets.max() - (self.block - 1)))


def make_taps(kind: FilterKind, radius: float, oversample: int) -> Taps:
    """Kernel taps for reducing `oversample` buckets to one pixel with `kind` at `radius` (output pixels).

    A radius too small to cover the block degrades to a plain block average rather than dropping
    buckets (Apophysis's filter size 1 would keep only one bucket of the block).
    """
    os_ = max(1, int(oversample))
    centre = os_ / 2.0                          # pixel centre in bucket coordinates (block-relative)
    half = os_ * kind.support * max(0.0, radius)
    lo, hi = math.ceil(centre - 0.5 - half), math.floor(centre - 0.5 + half)
    offsets = np.arange(lo, hi + 1)
    if offsets.size:
        u = ((offsets + 0.5) - centre) / (os_ * radius) if radius > 0 else np.zeros_like(offsets, dtype=float)
        weights = kind.profile(u.astype(np.float64))
        weights = np.where(np.abs(u) < kind.support, weights, 0.0)
    else:
        weights = np.zeros(0)
    if offsets.size < os_ or weights.sum() <= 1e-12:
        offsets = np.arange(os_)
        weights = np.ones(os_)
    return Taps(offsets, weights / weights.sum(), os_)


def downsample(buckets: np.ndarray, taps: Taps, gutter: int, width: int, height: int) -> np.ndarray:
    """Reduce a (gutter + height·os + gutter, gutter + width·os + gutter, C) array to (height, width, C).

    `gutter` must be ≥ `taps.reach`; the array's interior starts at `gutter` on both axes.
    Separable: rows first (halving the work for the column pass), float32 arithmetic.
    """
    if gutter < taps.reach:
        raise ValueError(f"gutter {gutter} is smaller than the filter reach {taps.reach}")
    rows = _reduce_axis(buckets, taps, gutter, height, axis=0)
    del buckets
    return _reduce_axis(rows, taps, gutter, width, axis=1)


def _reduce_axis(array: np.ndarray, taps: Taps, gutter: int, count: int, axis: int) -> np.ndarray:
    os_ = taps.block
    shape = list(array.shape)
    shape[axis] = count
    out = np.zeros(shape, dtype=np.float32)
    for offset, weight in zip(taps.offsets.tolist(), taps.weights.tolist()):
        start = gutter + offset
        sl = [slice(None)] * array.ndim
        sl[axis] = slice(start, start + os_ * count, os_)
        out += np.float32(weight) * array[tuple(sl)]
    return out


# --- density estimation ------------------------------------------------------------------------
@dataclass(frozen=True)
class DensityEstimation:
    """flam3 density-estimation parameters (radii in output pixels)."""
    max_radius: float = 9.0     # flam3 `estimator`
    min_radius: float = 0.0     # flam3 `estimator_minimum`
    curve: float = 0.4          # flam3 `estimator_curve`
    levels: int = 8

    def kernel_widths(self, oversample: int) -> np.ndarray:
        """Geometric ladder of kernel half-widths (buckets) from the minimum to the maximum radius."""
        hi = max(1.0, self.max_radius * oversample + 1.0)
        lo = min(hi, max(1.0, self.min_radius * oversample + 1.0))
        if hi - lo < 1e-9:
            return np.array([lo])
        n = max(2, min(self.levels, int(math.ceil(math.log(hi / lo) / math.log(1.6))) + 1))
        return np.geomspace(lo, hi, n)

    def reach(self, oversample: int) -> int:
        """Gutter needed so the widest kernel sees real neighbours at tile edges."""
        return int(math.ceil(self.max_radius * oversample + 1.0))


def density_estimate(scaled: np.ndarray, counts: np.ndarray, oversample: int, de: DensityEstimation) -> np.ndarray:
    """Blur sparsely hit buckets more than dense ones (flam3 semantics), returning a new array.

    Args:
        scaled: (rows, cols, C) float32 values to spread (the log-scaled colour + brightness).
        counts: (rows, cols) raw hit counts deciding each bucket's kernel width.
        oversample: Buckets per output pixel (radii are given in output pixels).
        de: Radii and curve.
    """
    widths = de.kernel_widths(oversample)
    os_ = max(1, int(oversample))
    density = _block_sum(counts.astype(np.float32), os_)
    hi, lo = float(widths[-1]), float(widths[0])
    width = np.clip(hi / np.power(np.maximum(density, 1.0), de.curve), lo, hi)
    out = np.zeros_like(scaled, dtype=np.float32)
    if widths.size == 1:
        return _blur_share(scaled, None, float(widths[0]), out)
    position = np.interp(np.log(width), np.log(widths), np.arange(widths.size))   # fractional level index
    for level, h in enumerate(widths.tolist()):
        share = np.maximum(0.0, 1.0 - np.abs(position - level)).astype(np.float32)   # linear membership
        if not share.any():
            continue
        _blur_share(scaled, share, h, out)
    return out


def _blur_share(scaled: np.ndarray, share: np.ndarray | None, h: float, out: np.ndarray) -> np.ndarray:
    part = scaled if share is None else scaled * share[..., None]
    if h <= 1.0 + 1e-6:
        out += part   # a one-bucket kernel is the identity
        return out
    sigma = h / (2.0 * GAUSSIAN_CUTOFF)   # flam3: exp(-2·(1.8·d/h)²)  →  σ = h / 3.6
    out += gaussian_blur(part, sigma, truncate=h)
    return out


def _block_sum(counts: np.ndarray, os_: int) -> np.ndarray:
    """Sum of counts over the os × os neighbourhood of every bucket (flam3's density probe)."""
    if os_ <= 1:
        return counts
    return box_blur(counts[..., None], os_)[..., 0] * float(os_ * os_)


def gaussian_blur(array: np.ndarray, sigma: float, truncate: float) -> np.ndarray:
    """Separable Gaussian blur of a (rows, cols, C) array, truncated at ±`truncate` buckets."""
    if sigma <= 0:
        return array.copy()
    if _scipy_gaussian1d is not None:
        out = _scipy_gaussian1d(array, sigma, axis=0, mode="nearest", truncate=max(0.5, truncate / sigma))
        return _scipy_gaussian1d(out, sigma, axis=1, mode="nearest", truncate=max(0.5, truncate / sigma), output=out)
    return _box_gaussian(array, sigma)


def _box_gaussian(array: np.ndarray, sigma: float, passes: int = 3) -> np.ndarray:
    """Repeated box blurs ≈ Gaussian (numpy fallback when scipy is absent); O(N) regardless of σ.

    Box widths follow Kutskir's "fast Gaussian blur": odd widths `wl` / `wu` mixed so their
    combined variance matches σ².
    """
    ideal = math.sqrt(12.0 * sigma * sigma / passes + 1.0)
    wl = int(math.floor(ideal))
    wl -= 1 - wl % 2
    wu = wl + 2
    m = int(round((12 * sigma * sigma - passes * wl * wl - 4 * passes * wl - 3 * passes) / (-4 * wl - 4)))
    out = array
    for i in range(passes):
        out = box_blur(out, wl if i < m else wu)
    return out


def box_blur(array: np.ndarray, width: int) -> np.ndarray:
    """Mean over a `width`-wide window along both axes (windows are clipped at the edges), via cumulative sums."""
    width = max(1, int(width))
    if width == 1:
        return array.astype(np.float32, copy=True)
    out = _box_axis(array, width, 0)
    return _box_axis(out, width, 1)


def _box_axis(array: np.ndarray, width: int, axis: int) -> np.ndarray:
    before, after = (width - 1) // 2, width // 2
    n = array.shape[axis]
    csum = np.cumsum(array, axis=axis, dtype=np.float64)
    idx = np.arange(n)
    hi = np.minimum(idx + after, n - 1)
    lo = idx - before - 1                       # window is (lo, hi]; lo < 0 means "from the start"
    total = np.take(csum, hi, axis=axis)
    has_lo = lo >= 0
    if has_lo.any():
        total -= np.take(csum, np.maximum(lo, 0), axis=axis) * _along(has_lo.astype(np.float64), array.ndim, axis)
    count = (hi - np.maximum(lo, -1)).astype(np.float64)
    return (total / _along(count, array.ndim, axis)).astype(np.float32)


def _along(values: np.ndarray, ndim: int, axis: int) -> np.ndarray:
    """Reshape a 1-D array so it broadcasts along `axis` of an `ndim`-dimensional array."""
    shape = [1] * ndim
    shape[axis] = values.size
    return values.reshape(shape)


__all__ = ["FilterKind", "FILTERS", "FILTER_BY_KEY", "filter_kind", "Taps", "make_taps", "downsample",
           "DensityEstimation", "density_estimate", "gaussian_blur", "box_blur"]
