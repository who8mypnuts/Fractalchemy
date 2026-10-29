"""The 3D Editor's scene: the fractal to render as a solid, its materials, lights and environment. Pure Python.

A `Scene3D` holds a *copy* of a flame (the main window's, or one built in the editor), so the 3D Editor edits
nothing the other windows show. The flame's own 3D camera (`Camera.pitch / yaw / perspective / zpos / dof`)
is the camera here too — the viewport's orbit rig writes those fields — so a render looks the same from the
main viewport and from here, and a flame sent back carries the view.

Materials are per transform (index into `flame.xforms`, the final transform taking the last one); a scene with
fewer materials than transforms repeats the last. Lights are JWildfire-style distant lights placed relative
to the camera (altitude above the view plane, azimuth around it), so they turn with the view.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace

from ..fractal.scene import Flame

RGB = tuple[int, int, int]
FORMAT_VERSION = 1


@dataclass
class Material:
    """How one transform's surface reflects light.

    Attributes:
        diffuse: Strength of the diffuse (Lambert) term.
        ambient: Strength of the ambient term (the environment's ambient light).
        specular: Strength of the Blinn-Phong highlight.
        shininess: Highlight tightness (Phong exponent).
        specular_color: Colour of the highlight.
        color_mode: `palette` (the point's palette colour) or `fixed` (`color`).
        color: The fixed colour.
        wrap: Light wrap: 0 = plain Lambert, 1 = light reaches fully round the back (softer shading).
    """
    diffuse: float = 0.8
    ambient: float = 0.25
    specular: float = 0.35
    shininess: float = 24.0
    specular_color: RGB = (255, 255, 255)
    color_mode: str = "palette"
    color: RGB = (200, 200, 200)
    wrap: float = 0.0

    def copy(self) -> "Material":
        return replace(self)


@dataclass
class DistantLight:
    """A directional light placed relative to the camera.

    Attributes:
        altitude: Degrees above the view plane (90 = from the camera, 0 = along the view plane).
        azimuth: Degrees around the view axis (0 = from the right, 90 = from above).
        color: Light colour.
        intensity: Strength.
        shadows: Whether it casts shadows (a shadow map rendered from the light).
        shadow_intensity: How dark its shadows are (0 = none, 1 = black).
        shadow_softness: Blur of the shadow edge in shadow-map pixels.
    """
    altitude: float = 55.0
    azimuth: float = -22.0
    color: RGB = (255, 255, 255)
    intensity: float = 0.8
    shadows: bool = True
    shadow_intensity: float = 0.7
    shadow_softness: float = 1.5

    def copy(self) -> "DistantLight":
        return replace(self)


@dataclass
class Environment:
    """What surrounds the object: the background and the ambient light (an HDRI comes in a later phase).

    Attributes:
        color: Background colour (also the ambient light's colour).
        ambient: Ambient light strength.
        exposure: Multiplier on the shaded image before gamma.
        visible: Draw the background (else transparent).
        hdri: Path of an equirectangular HDR image (reserved: read in phase 4).
    """
    color: RGB = (30, 32, 40)
    ambient: float = 0.6
    exposure: float = 1.0
    visible: bool = True
    hdri: str = ""

    def copy(self) -> "Environment":
        return replace(self)


@dataclass
class SolidSettings:
    """The solid renderer's knobs.

    Attributes:
        ao: Ambient occlusion on / off.
        ao_radius: Sampling radius as a fraction of the image's shorter side.
        ao_intensity: How dark occluded corners get (0..1).
        ao_samples: Samples per pixel (more = smoother, slower).
        ao_falloff: How quickly occluders lose weight with distance (1 = linear).
        normal_smoothing: Blur of the normals in pixels (0 = none).
        min_hits: Density threshold: a G-buffer pixel needs this many samples to count as surface (1 = every sample
            counts). Stray points — the thin haze a flame's blur variations scatter everywhere — land in pixels with
            one or two hits, while a surface collects many, so a threshold of 3–5 removes the dust.
        fog: Fog on / off; `fog_start` / `fog_end` as fractions of the depth range; `fog_color`.
        display: `solid` (lit) or `points` (the palette colours, unlit — a quick look at the shape).
    """
    ao: bool = True
    ao_radius: float = 0.04
    ao_intensity: float = 0.8
    ao_samples: int = 16
    ao_falloff: float = 1.0
    normal_smoothing: float = 1.0
    min_hits: int = 3
    fog: bool = False
    fog_start: float = 0.3
    fog_end: float = 1.0
    fog_color: RGB = (30, 32, 40)
    display: str = "solid"

    def copy(self) -> "SolidSettings":
        return replace(self)


@dataclass
class Scene3D:
    """A 3D Editor scene (see the module docstring).

    Attributes:
        name: Display name (the flame's by default).
        fractal: The flame rendered as a solid (None: nothing loaded yet).
        follow_main: Re-pull the main window's fractal whenever it changes.
        solid: Renderer settings.
        materials: Per-transform materials (index = transform index; the last one repeats).
        lights: The distant lights.
        environment: Background and ambient light.
    """
    name: str = "scene"
    fractal: Flame | None = None
    follow_main: bool = False
    solid: SolidSettings = field(default_factory=SolidSettings)
    materials: list[Material] = field(default_factory=lambda: [Material()])
    lights: list[DistantLight] = field(default_factory=lambda: [DistantLight(), DistantLight(30.0, 150.0, (190, 205, 255), 0.35, False)])
    environment: Environment = field(default_factory=Environment)

    def material_for(self, index: int) -> Material:
        """The material of transform `index` (the last material repeats for transforms beyond the list)."""
        if not self.materials:
            return Material()
        return self.materials[min(max(0, index), len(self.materials) - 1)]

    def copy(self) -> "Scene3D":
        """Independent copy (the flame, every material and light duplicated)."""
        return Scene3D(self.name, self.fractal.copy() if self.fractal else None, self.follow_main, self.solid.copy(),
                       [m.copy() for m in self.materials], [li.copy() for li in self.lights], self.environment.copy())

    # --- serialisation (the .fa3d format and tests use this) -----------------------------------------------------
    def to_dict(self) -> dict:
        """Plain-data form (JSON-ready)."""
        return {
            "name": self.name,
            "fractal": self.fractal.to_dict() if self.fractal else None,
            "follow_main": self.follow_main,
            "solid": asdict(self.solid),
            "materials": [asdict(m) for m in self.materials],
            "lights": [asdict(li) for li in self.lights],
            "environment": asdict(self.environment),
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Scene3D":
        """Inverse of `to_dict`; missing keys take defaults, unknown ones are ignored."""
        return cls(
            name=str(data.get("name", "scene")),
            fractal=Flame.from_dict(data["fractal"]) if data.get("fractal") else None,
            follow_main=bool(data.get("follow_main", False)),
            solid=_load(SolidSettings, data.get("solid")),
            materials=[_load(Material, m) for m in data.get("materials", [])] or [Material()],
            lights=[_load(DistantLight, li) for li in data.get("lights", [])],
            environment=_load(Environment, data.get("environment")),
        )


def _load(cls, data: dict | None):
    """A dataclass from a dict, keeping only known fields and turning colour lists back into tuples."""
    if not data:
        return cls()
    known = {f.name for f in fields(cls)}
    values = {}
    for key, value in data.items():
        if key not in known:
            continue
        values[key] = tuple(int(v) for v in value) if key.endswith("color") or key == "fog_color" else value
    return cls(**values)


def materials_for(flame: Flame | None, existing: list[Material] | None = None) -> list[Material]:
    """One material per transform of `flame` (the final transform included), keeping `existing` ones where they are."""
    count = (len(flame.xforms) + (1 if flame.final else 0)) if flame is not None else 1
    out = [m.copy() for m in (existing or [])][:count]
    while len(out) < count:
        out.append(out[-1].copy() if out else Material())
    return out


__all__ = ["Scene3D", "Material", "DistantLight", "Environment", "SolidSettings", "materials_for", "FORMAT_VERSION", "RGB"]
