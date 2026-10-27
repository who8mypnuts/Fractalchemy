"""Image-space denoisers for finished renders, in the spirit of the denoise pass of 3D renderers.

A flame rendered at a modest density is grainy in its sparse regions. Density estimation
(`filters.py`) treats that at the histogram level; the denoisers here work on the tone-mapped
picture instead, so a quick render can be cleaned up afterwards — the trade Chaotica, Blender
and friends make. Each entry is registered with an availability probe: the numpy ones are always
present, the OpenCV and Intel Open Image Denoise ones appear when their packages are installed.

All denoisers take and return a float32 (H, W, 3) RGB array in 0..1 and a strength 0..100;
alpha is left alone by the caller. Strength maps onto each method's own parameters so that
"50" is a sensible middle for every method.
"""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Callable

import numpy as np

from .filters import box_blur

Denoiser = Callable[[np.ndarray, float], np.ndarray]


@dataclass(frozen=True)
class DenoiserKind:
    """A denoiser entry for the UI.

    Attributes:
        key: Identifier stored in settings ("none" and "density" are handled by the renderer itself).
        label: Name shown in the UI.
        description: Tooltip text.
        run: The function, or None when its package is missing.
        hint: How to make an unavailable denoiser available.
    """
    key: str
    label: str
    description: str
    run: Denoiser | None
    hint: str = ""

    @property
    def available(self) -> bool:
        """True if the denoiser can run in this installation."""
        return self.run is not None


# --- numpy implementations -------------------------------------------------------------------
def guided_filter(rgb: np.ndarray, strength: float) -> np.ndarray:
    """He et al.'s guided filter with the image as its own guide: edge-preserving, O(N), no halos.

    Strength scales both the window (2..10 px) and the regularisation ε (the variance below which a
    neighbourhood counts as noise) — small ε keeps gradients, large ε flattens them.
    """
    s = min(1.0, max(0.0, strength / 100.0))
    radius = int(round(2 + 6 * s))
    eps = (0.02 + 0.28 * s) ** 2
    width = 2 * radius + 1
    guide = rgb.astype(np.float32)
    mean_i = box_blur(guide, width)
    corr_ii = box_blur(guide * guide, width)
    var_i = corr_ii - mean_i * mean_i
    a = var_i / (var_i + np.float32(eps))
    b = mean_i - a * mean_i
    mean_a = box_blur(a, width)
    mean_b = box_blur(b, width)
    return np.clip(mean_a * guide + mean_b, 0.0, 1.0)


def bilateral_filter(rgb: np.ndarray, strength: float) -> np.ndarray:
    """Bilateral filter vectorised over window offsets: smooths within similar colours only.

    Strength sets the colour tolerance (σ_r 0.03..0.25) and the spatial radius (2..5 px).
    """
    s = min(1.0, max(0.0, strength / 100.0))
    radius = int(round(2 + 3 * s))
    sigma_r = 0.03 + 0.22 * s
    sigma_s = radius / 2.0
    img = rgb.astype(np.float32)
    padded = np.pad(img, ((radius, radius), (radius, radius), (0, 0)), mode="reflect")
    h, w = img.shape[:2]
    acc = np.zeros_like(img)
    norm = np.zeros(img.shape[:2], dtype=np.float32)
    inv_r = np.float32(-0.5 / (sigma_r * sigma_r))
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            spatial = np.exp(-0.5 * (dx * dx + dy * dy) / (sigma_s * sigma_s))
            shifted = padded[radius + dy:radius + dy + h, radius + dx:radius + dx + w]
            diff = shifted - img
            weight = np.float32(spatial) * np.exp(inv_r * (diff * diff).sum(axis=2))
            acc += weight[..., None] * shifted
            norm += weight
    return np.clip(acc / norm[..., None], 0.0, 1.0)


# --- optional packages ---------------------------------------------------------------------
def _opencv_nlmeans() -> Denoiser | None:
    try:
        cv2 = importlib.import_module("cv2")
    except ImportError:
        return None

    def run(rgb: np.ndarray, strength: float) -> np.ndarray:
        s = min(1.0, max(0.0, strength / 100.0))
        h = 2.0 + 18.0 * s
        image8 = np.clip(rgb * 255.0 + 0.5, 0, 255).astype(np.uint8)
        out = cv2.fastNlMeansDenoisingColored(np.ascontiguousarray(image8), None, h, h, 7, 21)
        return out.astype(np.float32) / 255.0
    return run


def _oidn() -> Denoiser | None:
    try:
        oidn = importlib.import_module("oidn")
    except ImportError:
        return None

    def run(rgb: np.ndarray, strength: float) -> np.ndarray:
        colour = np.ascontiguousarray(rgb.astype(np.float32))
        out = np.zeros_like(colour)
        device = oidn.NewDevice()
        oidn.CommitDevice(device)
        filt = oidn.NewFilter(device, "RT")
        h, w = colour.shape[:2]
        oidn.SetSharedFilterImage(filt, "color", colour, oidn.FORMAT_FLOAT3, w, h)
        oidn.SetSharedFilterImage(filt, "output", out, oidn.FORMAT_FLOAT3, w, h)
        oidn.SetFilter1b(filt, "hdr", False)
        oidn.CommitFilter(filt)
        oidn.ExecuteFilter(filt)
        oidn.ReleaseFilter(filt)
        oidn.ReleaseDevice(device)
        s = min(1.0, max(0.0, strength / 100.0))
        return np.clip(colour + (out - colour) * s, 0.0, 1.0)   # strength blends towards the AI result
    return run


DENOISERS: tuple[DenoiserKind, ...] = (
    DenoiserKind("none", "None", "Leave the render as it is", lambda rgb, s: rgb),
    DenoiserKind("density", "Density estimation (flam3)",
                 "Blur sparsely hit areas at the histogram level, as flam3 / Apophysis do; dense detail stays sharp",
                 lambda rgb, s: rgb),
    DenoiserKind("guided", "Guided filter (edge-aware)", "Fast edge-preserving smoothing without halos", guided_filter),
    DenoiserKind("bilateral", "Bilateral", "Smooths within similar colours only; keeps hard edges", bilateral_filter),
    DenoiserKind("nlmeans", "Non-local means (OpenCV)", "Patch-based denoising; best on fine grain (8-bit colour)",
                 _opencv_nlmeans(), "pip install opencv-python-headless"),
    DenoiserKind("oidn", "Intel Open Image Denoise (AI)", "Neural denoiser used by Blender and others",
                 _oidn(), "pip install oidn (needs the Intel OIDN library)"),
)
DENOISER_BY_KEY = {d.key: d for d in DENOISERS}


def denoiser_kind(key: str) -> DenoiserKind:
    """The denoiser for a settings key (unknown keys mean none)."""
    return DENOISER_BY_KEY.get(key, DENOISERS[0])


def denoise(rgb: np.ndarray, key: str, strength: float) -> np.ndarray:
    """Run the image-space denoiser `key` (no-op for none / density / unavailable)."""
    kind = denoiser_kind(key)
    if kind.run is None or key in ("none", "density"):
        return rgb
    return kind.run(rgb, strength)


__all__ = ["DenoiserKind", "DENOISERS", "DENOISER_BY_KEY", "denoiser_kind", "denoise", "guided_filter", "bilateral_filter"]
