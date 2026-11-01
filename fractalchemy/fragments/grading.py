"""Colour grading of the accumulated image — a display-time stage after the buffer shader, never touching the fragment.

FragM leaves tone mapping to each fragment's buffer shader (the *Post* group). This is the grading a viewer expects
on top of that: exposure, gamma, contrast, saturation, a hue shift, a vignette, a tone-mapping operator and an
invert, applied to the displayed image (and to hi-res renders) by `gl/grading.py`. The settings live in the
`.fafrag` metadata, cost one cheap full-screen pass, and changing them only re-runs the display pass — the
accumulation is untouched. `is_identity` lets the engine skip the stage entirely.
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
    """
    exposure: float = 0.0
    gamma: float = 1.0
    contrast: float = 1.0
    saturation: float = 1.0
    hue: float = 0.0
    vignette: float = 0.0
    tonemap: str = "none"
    invert: bool = False

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

    def uniforms(self) -> dict:
        """Name → value for the grading program (`gl/grading.py`)."""
        return {"u_exposure": 2.0 ** float(self.exposure), "u_gamma": max(0.05, float(self.gamma)), "u_contrast": float(self.contrast),
                "u_saturation": float(self.saturation), "u_hue": float(self.hue) * 3.14159265 / 180.0, "u_vignette": float(self.vignette),
                "u_tonemap": TONEMAPS.index(self.tonemap), "u_invert": 1 if self.invert else 0}


def _cast(name: str, value):
    if name == "invert":
        return value in (True, "true", "True", 1, "1")
    if name == "tonemap":
        return str(value)
    return float(value)


GRADING_FRAGMENT = """#version 330 core
in vec2 v_uv;
uniform sampler2D frontbuffer;
uniform float u_exposure, u_gamma, u_contrast, u_saturation, u_hue, u_vignette;
uniform int u_tonemap, u_invert;
out vec4 fragColor;

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
    vec4 src = texture(frontbuffer, v_uv);
    vec3 c = max(src.rgb, 0.0) * u_exposure;
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
    if (u_invert != 0) c = 1.0 - c;
    fragColor = vec4(clamp(c, 0.0, 1.0), src.a);
}
"""

__all__ = ["Grading", "TONEMAPS", "GRADING_FRAGMENT"]
