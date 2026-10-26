"""Flame scene model: transforms, camera, colouring and palette. Pure Python, no Qt, no numpy.

Conventions follow flam3 / Apophysis so files round-trip faithfully:

* Affine `coefs = (a, b, c, d, e, f)` map `(x, y)` to `(a·x + c·y + e, b·x + d·y + f)`.
* Fractal-space y points *down* on screen, as in flam3.
* `color_speed` is flam3's: `c' = c·(1 − speed) + xform.color·speed`
  (Apophysis stores `symmetry = 1 − 2·speed` instead).
* `camera.scale` is pixels per unit at the flame's own `width`; `zoom` multiplies it by 2^zoom.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field, replace

from ..model import RGB, Gradient

Affine = tuple[float, float, float, float, float, float]
PALETTE_SIZE = 256


def identity_affine() -> Affine:
    """The do-nothing affine transform."""
    return (1.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def apply_affine(coefs: Affine, x: float, y: float) -> tuple[float, float]:
    """Map one point through `coefs` (flam3 column convention)."""
    a, b, c, d, e, f = coefs
    return a * x + c * y + e, b * x + d * y + f


@dataclass
class XForm:
    """One transform of the iterated function system.

    Attributes:
        weight: Relative probability of being chosen (final xforms ignore it).
        color: Palette position (0..1) this transform pulls the point colour towards.
        color_speed: How strongly it pulls (flam3 semantics, 0..1).
        opacity: Plot weight of points leaving this transform (0 = invisible).
        coefs: Pre-variation affine.
        post: Post-variation affine.
        variations: Variation name → weight (only non-zero ones are kept).
        params: Variation parameters, keyed `variation_param` as in flame files (`julian_power`).
        chaos: Xaos row — relative weights of choosing each xform *after* this one; None = all equal.
        name: Optional label from the file.
    """
    weight: float = 0.5
    color: float = 0.0
    color_speed: float = 0.5
    opacity: float = 1.0
    coefs: Affine = field(default_factory=identity_affine)
    post: Affine = field(default_factory=identity_affine)
    variations: dict[str, float] = field(default_factory=lambda: {"linear": 1.0})
    params: dict[str, float] = field(default_factory=dict)
    chaos: list[float] | None = None
    name: str = ""

    @property
    def symmetry(self) -> float:
        """Apophysis's `symmetry` attribute for this colour speed."""
        return 1.0 - 2.0 * self.color_speed

    @staticmethod
    def speed_from_symmetry(symmetry: float) -> float:
        """Convert Apophysis `symmetry` to flam3 `color_speed`."""
        return (1.0 - symmetry) / 2.0

    def param(self, variation: str, name: str, default: float = 0.0) -> float:
        """A variation parameter such as `param("julian", "power")`."""
        return self.params.get(f"{variation}_{name}", default)

    def has_post(self) -> bool:
        """True if the post affine does anything."""
        return tuple(self.post) != identity_affine()

    def copy(self) -> "XForm":
        """Deep enough copy: dicts and the chaos row are duplicated."""
        return replace(self, variations=dict(self.variations), params=dict(self.params),
                       chaos=None if self.chaos is None else list(self.chaos))


@dataclass
class Camera:
    """Where the flame is viewed from.

    Attributes:
        center: Fractal-space point at the image centre.
        scale: Pixels per fractal unit when the image is `width` pixels wide.
        zoom: Extra magnification, 2^zoom (Apophysis semantics).
        rotate: Rotation in degrees (Apophysis `rotate`; `angle` is −rotate in radians).
        width, height: The flame's own image size; other viewports scale from it.
    """
    center: tuple[float, float] = (0.0, 0.0)
    scale: float = 200.0
    zoom: float = 0.0
    rotate: float = 0.0
    width: int = 800
    height: int = 600

    def pixels_per_unit(self, view_width: int, view_height: int) -> float:
        """Scale for a viewport of another size: the flame's framed area always fits inside it."""
        fit = min(view_width / max(1, self.width), view_height / max(1, self.height))
        return self.scale * (2.0 ** self.zoom) * fit

    def pixel_transform(self, view_width: int, view_height: int) -> Affine:
        """Affine taking fractal coordinates to pixel coordinates (origin top-left, y down)."""
        ppu = self.pixels_per_unit(view_width, view_height)
        angle = math.radians(-self.rotate)   # Apophysis: FAngle = -rotate°
        cos_a, sin_a = math.cos(angle), math.sin(angle)
        cx, cy = self.center
        # q = R · (p − center);  px = W/2 + ppu·q.x ;  py = H/2 + ppu·q.y   (Apophysis RenderingImplementation)
        a, c = ppu * cos_a, ppu * sin_a
        b, d = -ppu * sin_a, ppu * cos_a
        e = view_width / 2.0 - (a * cx + c * cy)
        f = view_height / 2.0 - (b * cx + d * cy)
        return (a, b, c, d, e, f)

    def unproject(self, px: float, py: float, view_width: int, view_height: int) -> tuple[float, float]:
        """Fractal-space point under pixel `(px, py)`."""
        a, b, c, d, e, f = self.pixel_transform(view_width, view_height)
        det = a * d - b * c
        x, y = px - e, py - f
        return (d * x - c * y) / det, (a * y - b * x) / det

    def copy(self) -> "Camera":
        return replace(self)


@dataclass
class Coloring:
    """Tone-mapping settings (Apophysis semantics and defaults).

    Attributes:
        brightness: Overall log-density brightness.
        gamma: Display gamma (output ∝ density^(1/gamma)).
        gamma_threshold: Below this density gamma blends linearly (avoids noisy speckle).
        vibrancy: 1 = colour from palette ratios, 0 = per-channel gamma.
        contrast: Density scaling.
        background: RGB 0..255.
    """
    brightness: float = 4.0
    gamma: float = 4.0
    gamma_threshold: float = 0.01
    vibrancy: float = 1.0
    contrast: float = 1.0
    background: RGB = (0, 0, 0)

    def copy(self) -> "Coloring":
        return replace(self)


@dataclass
class Flame:
    """A complete fractal flame: IFS, camera, colouring, palette.

    Attributes:
        name: Display name.
        xforms: The iterated transforms (at least one for a renderable flame).
        final: Optional final transform applied before plotting (not iterated).
        camera: View.
        coloring: Tone mapping.
        palette: 256 RGB triples (0..255); indexed by the point colour 0..1.
        unsupported: Variation names present in the file that no engine implements (ignored when rendering).
        source_version: The `version` attribute of the file the flame came from, for messages.
    """
    name: str = "flame"
    xforms: list[XForm] = field(default_factory=list)
    final: XForm | None = None
    camera: Camera = field(default_factory=Camera)
    coloring: Coloring = field(default_factory=Coloring)
    palette: list[RGB] = field(default_factory=lambda: [(int(255 * i / 255),) * 3 for i in range(PALETTE_SIZE)])
    unsupported: list[str] = field(default_factory=list)
    source_version: str = ""

    @property
    def gradient(self) -> Gradient:
        """The palette as an editable Gradient (for the Gradient Library)."""
        return Gradient.from_colors(self.name, self.palette)

    def set_gradient(self, gradient: Gradient) -> None:
        """Replace the palette by sampling a Gradient."""
        self.palette = list(gradient.sample(PALETTE_SIZE))

    def renderable(self) -> bool:
        """True if there is at least one transform with positive weight."""
        return any(x.weight > 0 for x in self.xforms)

    def copy(self) -> "Flame":
        """Independent copy (transforms, camera, colouring and palette duplicated)."""
        return Flame(self.name, [x.copy() for x in self.xforms], self.final.copy() if self.final else None,
                     self.camera.copy(), self.coloring.copy(), list(self.palette), list(self.unsupported),
                     self.source_version)

    # --- serialisation (the .fa format and tests use this) ------------------
    def to_dict(self) -> dict:
        """Plain-data form (JSON-ready)."""
        return {
            "name": self.name,
            "camera": {"center": list(self.camera.center), "scale": self.camera.scale, "zoom": self.camera.zoom,
                       "rotate": self.camera.rotate, "width": self.camera.width, "height": self.camera.height},
            "coloring": {"brightness": self.coloring.brightness, "gamma": self.coloring.gamma,
                         "gamma_threshold": self.coloring.gamma_threshold, "vibrancy": self.coloring.vibrancy,
                         "contrast": self.coloring.contrast, "background": list(self.coloring.background)},
            "palette": ["%02x%02x%02x" % tuple(c) for c in self.palette],
            "xforms": [_xform_to_dict(x) for x in self.xforms],
            "final": _xform_to_dict(self.final) if self.final else None,
            "unsupported": list(self.unsupported),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Flame":
        """Inverse of `to_dict`; missing keys take defaults."""
        cam, col = data.get("camera", {}), data.get("coloring", {})
        palette = [tuple(int(h[i:i + 2], 16) for i in (0, 2, 4)) for h in data.get("palette", [])]
        return cls(
            name=data.get("name", "flame"),
            xforms=[_xform_from_dict(x) for x in data.get("xforms", [])],
            final=_xform_from_dict(data["final"]) if data.get("final") else None,
            camera=Camera(tuple(cam.get("center", (0.0, 0.0))), cam.get("scale", 200.0), cam.get("zoom", 0.0),
                          cam.get("rotate", 0.0), int(cam.get("width", 800)), int(cam.get("height", 600))),
            coloring=Coloring(col.get("brightness", 4.0), col.get("gamma", 4.0), col.get("gamma_threshold", 0.01),
                              col.get("vibrancy", 1.0), col.get("contrast", 1.0), tuple(col.get("background", (0, 0, 0)))),
            palette=palette or Flame().palette,
            unsupported=list(data.get("unsupported", [])),
        )


def _xform_to_dict(x: XForm) -> dict:
    return {"weight": x.weight, "color": x.color, "color_speed": x.color_speed, "opacity": x.opacity,
            "coefs": list(x.coefs), "post": list(x.post), "variations": dict(x.variations), "params": dict(x.params),
            "chaos": x.chaos, "name": x.name}


def _xform_from_dict(d: dict) -> XForm:
    return XForm(d.get("weight", 0.5), d.get("color", 0.0), d.get("color_speed", 0.5), d.get("opacity", 1.0),
                 tuple(d.get("coefs", identity_affine())), tuple(d.get("post", identity_affine())),
                 dict(d.get("variations", {"linear": 1.0})), dict(d.get("params", {})), d.get("chaos"), d.get("name", ""))
