"""Log-density tone mapping (Apophysis / flam3 `ImageMaker` semantics), for numpy *and* GLSL.

The histogram holds, per bucket, the summed palette colour (0..1 per channel, opacity
weighted) in RGB and the opacity-weighted hit count in A. Buckets are the output pixels
supersampled `oversample` times per side (plus a gutter); the spatial filter of
`filtering.py` sums them into pixels. Both implementations derive their constants from one
`ToneParams`, and `tests/test_render.py` checks they agree.

Normalised form of Apophysis's maths (BRIGHT_ADJUST / PREFILTER_WHITE / white_level cancel out):

    q     = count · ppu² / (contrast · samples)          bucket density relative to the expected
    L     = brightness · contrast · 268/256 · log10(1 + q)     (per bucket; ppu is the *bucket* density)
    rgb   = L · mean colour
    --- the spatial filter averages (rgb, L) of a pixel's buckets here ---
    alpha = L^(1/γ)             (blended linearly below gamma_threshold), clamped to 1
    out   = vibrancy · alpha · rgb / L + (1 − vibrancy) · rgb^(1/γ) + (1 − alpha) · background
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..fractal.curves import CHANNELS, LUT_SIZE, Curves
from ..fractal.scene import Coloring
from .filtering import filter_width, kernel_adjust, kernel_norm, spatial_filter

K1_FACTOR = 268.0 / 256.0


def curve_luts(curves: Curves | None) -> np.ndarray | None:
    """(5, 256) lookup tables in `CHANNELS` order, or None when every curve is the identity."""
    if curves is None or curves.is_default():
        return None
    return np.array([curves.lut(c, LUT_SIZE) for c in CHANNELS], dtype=np.float64)


def apply_luts(values: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """Map 0..1 values through a 256-entry table with linear interpolation."""
    return np.interp(np.clip(values, 0.0, 1.0), np.linspace(0.0, 1.0, lut.shape[0]), lut)


@dataclass(frozen=True)
class ToneParams:
    """Constants both tone-map implementations use."""
    k1: float            # brightness · contrast · 268/256
    k2: float            # ppu² / (contrast · samples)
    inv_gamma: float
    threshold: float
    funcval: float       # threshold^(inv_gamma − 1), the linear-blend slope below the threshold
    vibrancy: float
    background: tuple[float, float, float]   # 0..1

    @classmethod
    def derive(cls, coloring: Coloring, pixels_per_unit: float, samples: int, oversample: int = 1) -> "ToneParams":
        """Constants for a histogram accumulated from `samples` iterations at `pixels_per_unit` output
        pixels per unit, with `oversample` buckets per pixel side (so a bucket sees 1/oversample² of a pixel)."""
        pixels_per_unit = pixels_per_unit * max(1, int(oversample))
        contrast = coloring.contrast if coloring.contrast > 0 else 1.0
        gamma = coloring.gamma if coloring.gamma > 0 else 1.0
        inv_gamma = 1.0 / gamma
        threshold = max(0.0, coloring.gamma_threshold)
        funcval = threshold ** (inv_gamma - 1.0) if threshold > 0 else 0.0
        return cls(
            k1=coloring.brightness * contrast * K1_FACTOR,
            k2=(pixels_per_unit ** 2) / (contrast * max(1, samples)),
            inv_gamma=inv_gamma, threshold=threshold, funcval=funcval,
            vibrancy=min(1.0, max(0.0, coloring.vibrancy)),
            background=tuple(c / 255.0 for c in coloring.background),
        )

    def as_uniforms(self) -> dict[str, object]:
        """Values for the GLSL programs' uniforms (both passes; each takes what it declares)."""
        return {"u_k1": self.k1, "u_k2": self.k2, "u_inv_gamma": self.inv_gamma, "u_threshold": self.threshold,
                "u_funcval": self.funcval, "u_vibrancy": self.vibrancy, "u_background": self.background}


def filter_uniforms(oversample: int, filter_radius: float) -> dict[str, object]:
    """Kernel uniforms of `TONEMAP_GLSL`."""
    return {"u_oversample": int(oversample), "u_fwidth": filter_width(oversample, filter_radius),
            "u_adjust": kernel_adjust(oversample, filter_radius), "u_norm": kernel_norm(oversample, filter_radius)}


def log_scale(histogram: np.ndarray, params: ToneParams, out_dtype=np.float64) -> np.ndarray:
    """Per-bucket log-density scaling: (…, 4) array of (L · mean colour, L)."""
    count = histogram[..., 3].astype(np.float64)
    lit = count > 0
    L = params.k1 * np.log10(1.0 + count * params.k2)
    ls = np.where(lit, L / np.where(lit, count, 1.0), 0.0)   # L / count: scales the summed colour to L · mean
    scaled = np.empty(histogram.shape, dtype=out_dtype)
    scaled[..., :3] = histogram[..., :3] * ls[..., None] if out_dtype is np.float64 else histogram[..., :3].astype(np.float64) * ls[..., None]
    scaled[..., 3] = L
    return scaled


def filter_buckets(scaled: np.ndarray, oversample: int, filter_radius: float, width: int, height: int) -> np.ndarray:
    """Sum the log-scaled buckets into (height, width, 4) pixels with the spatial filter kernel.

    `scaled` is (height·oversample + 2·gutter, width·oversample + 2·gutter, 4).
    """
    kernel = spatial_filter(oversample, filter_radius)
    fw = kernel.shape[0]
    out = np.zeros((height, width, 4), dtype=np.float64)
    for i in range(fw):
        rows = slice(i, i + height * oversample, oversample)
        for j in range(fw):
            out += kernel[i, j] * scaled[rows, j:j + width * oversample:oversample]
    return out


def tonemap(histogram: np.ndarray, params: ToneParams, oversample: int = 1, filter_radius: float = 0.0,
            size: tuple[int, int] | None = None, luts: np.ndarray | None = None) -> np.ndarray:
    """Map a float histogram to a (H, W, 4) uint8 RGBA image (alpha = 255).

    With `oversample` / `filter_radius` the histogram is the supersampled bucket grid (gutter included)
    and `size` = (width, height) of the output; otherwise the histogram is the image itself.
    `luts` are the tone curves from `curve_luts()` (None = identity).
    """
    scaled = log_scale(histogram, params)
    if size is not None and (oversample > 1 or filter_width(oversample, filter_radius) > 1):
        scaled = filter_buckets(scaled, oversample, filter_radius, size[0], size[1])
    rgba = finish(scaled, params, luts=luts)
    image = np.empty(scaled.shape[:2] + (4,), dtype=np.uint8)
    image[..., :3] = np.clip(rgba[..., :3] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    image[..., 3] = 255
    return image


def finish(scaled: np.ndarray, params: ToneParams, transparent: bool = False,
           luts: np.ndarray | None = None) -> np.ndarray:
    """Gamma, vibrancy, background and tone curves on (r, g, b, L) → float RGBA in 0..1.

    With `transparent` the background is not blended in and the colour is un-premultiplied
    (straight alpha), as flam3 does for transparent PNGs; otherwise alpha is 1 everywhere.
    `luts` are the tone curves from `curve_luts()` (None = identity).
    """
    rgb = np.maximum(scaled[..., :3].astype(np.float64), 0.0)
    L = np.maximum(scaled[..., 3].astype(np.float64), 0.0)
    lit = L > 0
    alpha = np.where(lit, np.power(L, params.inv_gamma), 0.0)
    if params.threshold > 0:
        below = lit & (L <= params.threshold)
        frac = L / params.threshold
        alpha = np.where(below, (1.0 - frac) * L * params.funcval + frac * alpha, alpha)
    alpha = np.clip(alpha, 0.0, 1.0)

    safe_L = np.where(lit, L, 1.0)
    ls = np.where(lit, params.vibrancy * alpha / safe_L, 0.0)
    out = np.empty(scaled.shape[:2] + (4,), dtype=np.float64)
    out[..., :3] = ls[..., None] * rgb + (1.0 - params.vibrancy) * np.power(rgb, params.inv_gamma)
    if luts is not None:
        coverage = apply_luts(alpha, luts[4])                    # the alpha curve remaps how much background shows
        out[..., :3] *= np.where(alpha > 0, coverage / np.where(alpha > 0, alpha, 1.0), 0.0)[..., None]
        alpha = coverage
    if transparent:
        safe_alpha = np.where(alpha > 0, alpha, 1.0)
        out[..., :3] = np.where((alpha > 0)[..., None], out[..., :3] / safe_alpha[..., None], 0.0)
        out[..., 3] = alpha
    else:
        out[..., :3] += (1.0 - alpha)[..., None] * np.asarray(params.background)
        out[..., 3] = 1.0
        if luts is not None:
            out = np.clip(out, 0.0, 1.0)
            overall = apply_luts(out, luts[0])
            out = np.stack([apply_luts(overall[..., ch], luts[1 + ch]) for ch in range(3)], axis=-1)
            out = np.concatenate([out, np.ones(out.shape[:2] + (1,), dtype=np.float64)], axis=-1)
    np.clip(out, 0.0, 1.0, out=out)
    return out


SCALE_GLSL = """
#version 330
// per bucket: (L * mean colour, L) from (summed colour, count)
uniform sampler2D u_histogram;
uniform float u_k1, u_k2;
in vec2 v_uv;
out vec4 f_color;

void main() {
    vec4 h = texture(u_histogram, v_uv);
    float count = h.a;
    if (count <= 0.0) { f_color = vec4(0.0); return; }
    float L = u_k1 * log(1.0 + count * u_k2) / log(10.0);
    f_color = vec4(h.rgb * (L / count), L);
}
"""

TONEMAP_GLSL = """
#version 330
// per output pixel: gather the log-scaled buckets with the spatial filter, then gamma / vibrancy / background
uniform sampler2D u_scaled;      // bucket grid, gutter included
uniform int u_oversample, u_fwidth;
uniform float u_adjust, u_norm;  // kernel coordinate scale and 1 / weight sum (filtering.py)
uniform float u_inv_gamma, u_threshold, u_funcval, u_vibrancy;
uniform vec3 u_background;
uniform sampler2D u_curves;      // 256 x 2: row 0 = (overall, red, green, blue) tables, row 1 = (alpha, -, -, -)
uniform bool u_has_curves;
out vec4 f_color;

float curve(float v, int channel, float row) {
    vec4 t = texture(u_curves, vec2((clamp(v, 0.0, 1.0) * 255.0 + 0.5) / 256.0, row));
    return channel == 0 ? t.r : channel == 1 ? t.g : channel == 2 ? t.b : t.a;
}

void main() {
    ivec2 bsize = textureSize(u_scaled, 0);
    ivec2 origin = ivec2(gl_FragCoord.xy) * u_oversample;   // gutter offset and kernel offset cancel: taps start here
    vec4 acc = vec4(0.0);
    for (int i = 0; i < u_fwidth; i++) {
        float ii = ((2.0 * float(i) + 1.0) / float(u_fwidth) - 1.0) * u_adjust;
        for (int j = 0; j < u_fwidth; j++) {
            float jj = ((2.0 * float(j) + 1.0) / float(u_fwidth) - 1.0) * u_adjust;
            ivec2 at = clamp(origin + ivec2(j, i), ivec2(0), bsize - 1);
            acc += exp(-2.0 * (ii * ii + jj * jj)) * texelFetch(u_scaled, at, 0);
        }
    }
    acc *= u_norm;
    float L = acc.a;
    if (L <= 0.0) {
        vec3 bg = u_background;   // empty pixel: the background, still through the overall / colour curves
        if (u_has_curves) {
            bg = vec3(curve(bg.r, 0, 0.25), curve(bg.g, 0, 0.25), curve(bg.b, 0, 0.25));
            bg = vec3(curve(bg.r, 1, 0.25), curve(bg.g, 2, 0.25), curve(bg.b, 3, 0.25));
        }
        f_color = vec4(bg, 1.0);
        return;
    }
    vec3 rgb = acc.rgb;
    float alpha = pow(max(L, 0.0), u_inv_gamma);
    if (u_threshold > 0.0 && L <= u_threshold) {
        float frac = L / u_threshold;
        alpha = (1.0 - frac) * L * u_funcval + frac * alpha;
    }
    alpha = clamp(alpha, 0.0, 1.0);
    float ls = L > 0.0 ? u_vibrancy * alpha / L : 0.0;
    vec3 outc = ls * rgb + (1.0 - u_vibrancy) * pow(max(rgb, vec3(0.0)), vec3(u_inv_gamma));
    if (u_has_curves) {
        float coverage = curve(alpha, 0, 0.75);
        outc *= alpha > 0.0 ? coverage / alpha : 0.0;
        alpha = coverage;
    }
    outc += (1.0 - alpha) * u_background;
    outc = clamp(outc, 0.0, 1.0);
    if (u_has_curves) {
        outc = vec3(curve(outc.r, 0, 0.25), curve(outc.g, 0, 0.25), curve(outc.b, 0, 0.25));
        outc = vec3(curve(outc.r, 1, 0.25), curve(outc.g, 2, 0.25), curve(outc.b, 3, 0.25));
    }
    f_color = vec4(outc, 1.0);
}
"""

FULLSCREEN_VERTEX_GLSL = """
#version 330
out vec2 v_uv;
void main() {
    // one oversized triangle covering the viewport; uv in 0..1
    vec2 pos = vec2((gl_VertexID == 1) ? 3.0 : -1.0, (gl_VertexID == 2) ? 3.0 : -1.0);
    v_uv = pos * 0.5 + 0.5;
    gl_Position = vec4(pos, 0.0, 1.0);
}
"""

__all__ = ["ToneParams", "tonemap", "log_scale", "filter_buckets", "finish", "filter_uniforms", "curve_luts", "apply_luts",
           "SCALE_GLSL", "TONEMAP_GLSL", "FULLSCREEN_VERTEX_GLSL"]
