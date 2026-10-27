"""Log-density tone mapping (Apophysis / flam3 `ImageMaker` semantics), for numpy *and* GLSL.

The histogram holds, per pixel, the summed palette colour (0..1 per channel, opacity
weighted) in RGB and the opacity-weighted hit count in A. Both implementations derive
their constants from one `ToneParams`, and `tests/test_render.py` checks they agree.

Normalised form of Apophysis's maths (BRIGHT_ADJUST / PREFILTER_WHITE / white_level cancel out):

    q     = count · ppu² / (contrast · samples)          density relative to the expected
    L     = brightness · contrast · 268/256 · log10(1 + q)
    rgb   = L · mean colour
    alpha = L^(1/γ)             (blended linearly below gamma_threshold), clamped to 1
    out   = vibrancy · alpha · rgb / L + (1 − vibrancy) · rgb^(1/γ) + (1 − alpha) · background
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..fractal.scene import Coloring

K1_FACTOR = 268.0 / 256.0


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
    def derive(cls, coloring: Coloring, pixels_per_unit: float, samples: int) -> "ToneParams":
        """Constants for a histogram accumulated from `samples` iterations at `pixels_per_unit`."""
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
        """Values for the GLSL program's uniforms."""
        return {"u_k1": self.k1, "u_k2": self.k2, "u_inv_gamma": self.inv_gamma, "u_threshold": self.threshold,
                "u_funcval": self.funcval, "u_vibrancy": self.vibrancy, "u_background": self.background}


def tonemap(histogram: np.ndarray, params: ToneParams) -> np.ndarray:
    """Map an (H, W, 4) float histogram to an (H, W, 4) uint8 RGBA image (alpha = 255)."""
    rgba = finish(log_scale(histogram, params), params)
    image = np.empty(histogram.shape[:2] + (4,), dtype=np.uint8)
    image[..., :3] = np.clip(rgba[..., :3] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    image[..., 3] = 255
    return image


def log_scale(histogram: np.ndarray, params: ToneParams, out_dtype=np.float32) -> np.ndarray:
    """The first half of the tone map: per bucket, log-density brightness `L` and the colour `L · mean rgb`.

    Returns an (H, W, 4) array holding (r, g, b, L). This is the quantity flam3 / Apophysis spatially
    filter (and density-estimate) *before* applying gamma, so the final renderer runs its filters on it.
    """
    count = histogram[..., 3].astype(np.float64)
    lit = count > 0
    L = params.k1 * np.log10(1.0 + count * params.k2)
    ls = np.where(lit, L / np.where(lit, count, 1.0), 0.0)
    out = np.empty(histogram.shape[:2] + (4,), dtype=out_dtype)
    out[..., :3] = histogram[..., :3] * ls[..., None]
    out[..., 3] = L
    return out


def finish(scaled: np.ndarray, params: ToneParams, transparent: bool = False) -> np.ndarray:
    """The second half: gamma, vibrancy and background on (r, g, b, L) → float RGBA in 0..1.

    With `transparent` the background is not blended in and the colour is un-premultiplied
    (straight alpha), as flam3 does for transparent PNGs; otherwise alpha is 1 everywhere.
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
    if transparent:
        safe_alpha = np.where(alpha > 0, alpha, 1.0)
        out[..., :3] = np.where((alpha > 0)[..., None], out[..., :3] / safe_alpha[..., None], 0.0)
        out[..., 3] = alpha
    else:
        out[..., :3] += (1.0 - alpha)[..., None] * np.asarray(params.background)
        out[..., 3] = 1.0
    np.clip(out, 0.0, 1.0, out=out)
    return out


TONEMAP_GLSL = """
#version 330
uniform sampler2D u_histogram;
uniform float u_k1, u_k2, u_inv_gamma, u_threshold, u_funcval, u_vibrancy;
uniform vec3 u_background;
in vec2 v_uv;
out vec4 f_color;

void main() {
    vec4 h = texture(u_histogram, v_uv);
    float count = h.a;
    if (count <= 0.0) { f_color = vec4(u_background, 1.0); return; }
    float L = u_k1 * log(1.0 + count * u_k2) / log(10.0);
    vec3 rgb = L * (h.rgb / count);
    float alpha = pow(max(L, 0.0), u_inv_gamma);
    if (u_threshold > 0.0 && L <= u_threshold) {
        float frac = L / u_threshold;
        alpha = (1.0 - frac) * L * u_funcval + frac * alpha;
    }
    alpha = clamp(alpha, 0.0, 1.0);
    float ls = L > 0.0 ? u_vibrancy * alpha / L : 0.0;
    vec3 outc = ls * rgb + (1.0 - u_vibrancy) * pow(max(rgb, vec3(0.0)), vec3(u_inv_gamma));
    outc += (1.0 - alpha) * u_background;
    f_color = vec4(clamp(outc, 0.0, 1.0), 1.0);
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

__all__ = ["ToneParams", "tonemap", "log_scale", "finish", "TONEMAP_GLSL", "FULLSCREEN_VERTEX_GLSL"]
