"""Colour grading of the accumulated image — a display-time stage after the buffer shader, never touching the fragment.

FragM leaves tone mapping to each fragment's buffer shader (the *Post* group). This is the grading a viewer expects
on top of that: exposure, gamma, contrast, saturation, a hue shift, a vignette, a tone-mapping operator and an
invert, plus a small post stack — bloom (a bright pass blurred and added back), chromatic aberration (the channels
sampled at slightly different radii), film grain, and a `.cube` colour LUT — applied to the displayed image (and to
hi-res renders) by `gl/grading.py`. The settings live in the `.fafrag` metadata, cost one or a few cheap full-screen
passes, and changing them only re-runs the display pass — the accumulation is untouched. `is_identity` lets the
engine skip the stage entirely.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, fields, replace

TONEMAPS = ("none", "reinhard", "filmic", "aces")


@dataclass(frozen=True)
class Grading:
    """The grading settings.

    Attributes:
        exposure: Exposure in stops (0 = as rendered).
        gamma: Output gamma applied after tone mapping (1 = none).
        contrast: Contrast about middle grey (1 = none).
        saturation: Colour saturation (1 = none, 0 = greyscale).
        hue: Hue rotation in degrees.
        vignette: Darkening towards the corners (0 = none, 1 = black corners).
        tonemap: `none`, `reinhard`, `filmic` (Hable) or `aces`.
        invert: Negative image.
        bloom: Strength of the glow added around bright parts (0 = none).
        bloom_threshold: Brightness above which a pixel glows.
        bloom_radius: Blur radius of the glow in pixels (at half resolution).
        aberration: Chromatic aberration: how far the red / blue channels drift towards the edges (0 = none).
        grain: Film grain amount (0 = none).
        lut: Path of a `.cube` LUT ("" = none).
        lut_strength: How much of the LUT's look is applied (1 = fully).
    """
    exposure: float = 0.0
    gamma: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue: float = 0.0
    vignette: float = 0.0
    tonemap: str = "none"
    invert: bool = False
    bloom: float = 0.0
    bloom_threshold: float = 0.8
    bloom_radius: float = 12.0
    aberration: float = 0.0
    grain: float = 0.0
    lut: str = ""
    lut_strength: float = 1.0

    @property
    def is_identity(self) -> bool:
        return self == Grading()

    def with_(self, **changes) -> "Grading":
        return replace(self, **changes)

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "Grading":
        if not data:
            return cls()
        values = {}
        for f in fields(cls):
            if f.name in data:
                try:
                    values[f.name] = _cast(f.name, data[f.name])
                except (TypeError, ValueError):
                    continue
        grading = cls(**values)
        return grading if grading.tonemap in TONEMAPS else grading.with_(tonemap="none")

    @property
    def has_bloom(self) -> bool:
        return self.bloom > 0.0

    @property
    def has_lut(self) -> bool:
        return bool(self.lut) and self.lut_strength > 0.0

    def uniforms(self) -> dict:
        """Name → value for the grading program (`gl/grading.py`; the samplers and `u_lut_size` are the stage's)."""
        return {"u_exposure": 2.0 ** float(self.exposure), "u_gamma": max(0.05, float(self.gamma)), "u_contrast": float(self.contrast),
                "u_saturation": float(self.saturation), "u_hue": float(self.hue) * 3.14159265 / 180.0, "u_vignette": float(self.vignette),
                "u_tonemap": TONEMAPS.index(self.tonemap), "u_invert": 1 if self.invert else 0, "u_bloom": float(self.bloom),
                "u_aberration": float(self.aberration) * 0.02, "u_grain": float(self.grain) * 0.25,
                "u_lut_strength": float(self.lut_strength) if self.has_lut else 0.0}


def _cast(name: str, value):
    if name == "invert":
        return value in (True, "true", "True", 1, "1")
    if name in ("tonemap", "lut"):
        return str(value)
    return float(value)


BRIGHT_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D frontbuffer;
uniform float u_threshold;
out vec4 fragColor;
void main() {
    vec3 c = max(texture(frontbuffer, v_uv).rgb, 0.0);
    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));
    fragColor = vec4(c * smoothstep(u_threshold, u_threshold + 0.5, luma), 1.0);
}
"""

BLUR_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D frontbuffer;
uniform vec2 u_step;            // one texel along the blur direction
uniform float u_radius;         // in texels (the Gaussian's sigma is a third of it)
out vec4 fragColor;
void main() {
    float sigma = max(0.5, u_radius / 3.0);
    int taps = int(min(32.0, ceil(u_radius)));
    vec3 sum = texture(frontbuffer, v_uv).rgb;
    float weight = 1.0;
    for (int i = 1; i <= 32; i++) {
        if (i > taps) break;
        float w = exp(-float(i * i) / (2.0 * sigma * sigma));
        vec2 o = u_step * float(i);
        sum += (texture(frontbuffer, v_uv + o).rgb + texture(frontbuffer, v_uv - o).rgb) * w;
        weight += 2.0 * w;
    }
    fragColor = vec4(sum / weight, 1.0);
}
"""

GRADING_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D frontbuffer;
uniform sampler2D bloomTex;
uniform sampler3D lutTex;
uniform float u_exposure, u_gamma, u_contrast, u_saturation, u_hue, u_vignette, u_bloom, u_aberration, u_grain, u_lut_strength, u_lut_size;
uniform int u_tonemap, u_invert;
out vec4 fragColor;

float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
vec4 fetch(vec2 uv) {
    if (u_aberration <= 0.0) return texture(frontbuffer, uv);
    vec2 d = (uv - 0.5) * u_aberration;
    return vec4(texture(frontbuffer, uv - d).r, texture(frontbuffer, uv).g, texture(frontbuffer, uv + d).b, texture(frontbuffer, uv).a);
}

vec3 hable(vec3 x) {
    const float A = 0.15, B = 0.50, C = 0.10, D = 0.20, E = 0.02, F = 0.30;
    return ((x * (A * x + C * B) + D * E) / (x * (A * x + B) + D * F)) - E / F;
}
vec3 aces(vec3 x) { return clamp((x * (2.51 * x + 0.03)) / (x * (2.43 * x + 0.59) + 0.14), 0.0, 1.0); }
vec3 hueShift(vec3 c, float a) {
    const vec3 k = vec3(0.57735);
    float cs = cos(a), sn = sin(a);
    return c * cs + cross(k, c) * sn + k * dot(k, c) * (1.0 - cs);
}

void main() {
    vec4 src = fetch(v_uv);
    vec3 c = max(src.rgb, 0.0);
    if (u_bloom > 0.0) c += texture(bloomTex, v_uv).rgb * u_bloom;
    c *= u_exposure;
    if (u_tonemap == 1) c = c / (1.0 + c);
    else if (u_tonemap == 2) c = hable(c) / hable(vec3(11.2));
    else if (u_tonemap == 3) c = aces(c);
    c = (c - 0.5) * u_contrast + 0.5;
    float luma = dot(c, vec3(0.2126, 0.7152, 0.0722));
    c = mix(vec3(luma), c, u_saturation);
    if (u_hue != 0.0) c = hueShift(c, u_hue);
    if (u_vignette > 0.0) {
        vec2 d = v_uv - 0.5;
        c *= 1.0 - u_vignette * smoothstep(0.2, 0.9, dot(d, d) * 2.0);
    }
    c = pow(max(c, 0.0), vec3(1.0 / u_gamma));
    if (u_lut_strength > 0.0) {
        vec3 uvw = clamp(c, 0.0, 1.0) * (u_lut_size - 1.0) / u_lut_size + 0.5 / u_lut_size;      // sample cell centres
        c = mix(c, texture(lutTex, uvw).rgb, u_lut_strength);
    }
    if (u_grain > 0.0) c += (hash(v_uv * 1024.0) - 0.5) * u_grain * (0.3 + 0.7 * (1.0 - clamp(dot(c, vec3(0.333)), 0.0, 1.0)));
    if (u_invert != 0) c = 1.0 - c;
    fragColor = vec4(clamp(c, 0.0, 1.0), src.a);
}
"""

__all__ = ["Grading", "TONEMAPS", "GRADING_FRAGMENT", "BRIGHT_FRAGMENT", "BLUR_FRAGMENT"]
