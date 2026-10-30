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
        show_fractal: Draw the fractal itself (off: only the instancers — a pure Holon scene).
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
    show_fractal: bool = True

    def copy(self) -> "SolidSettings":
        return replace(self)


@dataclass
class MeshAsset:
    """A mesh to instance along a fractal (the Holon IFS).

    Attributes:
        name: Display name (unique in the scene).
        kind: `primitive` (built from `primitive` + `detail`), `file` (read from `path`) or `fractal` (the clean mesh
            the Mesh tab generated, saved to `path` as a PLY beside the scene's assets).
        primitive: `sphere`, `cube`, `torus`, `tetrahedron`, `icosahedron` or `cylinder` for primitives.
        detail: Subdivision level of a primitive.
        path: The mesh file for `file` / `fractal` assets.
        digest: SHA-1 of the file when it was loaded (so a changed file is noticed).
        normalize: Centre the mesh and scale its longest side to 1 before instancing.
        mesh: The loaded geometry (run-time only; not written to the scene file).
    """
    name: str = "asset"
    kind: str = "primitive"
    primitive: str = "sphere"
    detail: int = 2
    path: str = ""
    digest: str = ""
    normalize: bool = True
    mesh: object = field(default=None, compare=False, repr=False)

    def copy(self) -> "MeshAsset":
        return replace(self)                       # the mesh is shared: it is never edited in place


@dataclass
class Instancer:
    """Instances of an asset at the points of a fractal's orbit, turned and scaled by the orbit's accumulated frames.

    Attributes:
        name: Display name.
        asset: Name of the `MeshAsset` instanced.
        source: `main` (the scene's fractal) or `own` (`flame`, a 3D IFS built in the Instances tab).
        flame: The own IFS (None until one is built).
        mode: `chaos` (orbit samples) or `tree` (every composition of the transforms to `depth`).
        count: Instances wanted in chaos mode.
        depth: Transforms composed per instance (chaos: the frame is the product of the last `depth` Jacobians;
            tree: the tree's depth).
        tree_levels: `all` (every node of the tree) or `leaves` (the deepest level only).
        frame_mode: `jacobian` (rotation and scale from the transforms' local Jacobians) or `translation` (no rotation,
            scale only).
        size: Base size of an instance (the asset's longest side, world units) before the frame's scale.
        size_falloff: Exponent on the accumulated scale (1 = exact, <1 flattens the size range).
        min_size: Instances smaller than this (world units) are dropped.
        max_instances: Cap on the number of instances (the largest are kept).
        color_mode: `palette` (the orbit's palette colour), `asset` (the mesh's vertex colours) or `fixed`.
        material: Surface of the instances (its `color` is the fixed colour).
        seed: Random seed of the chaos mode.
        visible: Drawn and rendered.
    """
    name: str = "instancer"
    asset: str = ""
    source: str = "main"
    flame: Flame | None = None
    mode: str = "chaos"
    count: int = 2000
    depth: int = 6
    tree_levels: str = "all"
    frame_mode: str = "jacobian"
    size: float = 0.1
    size_falloff: float = 1.0
    min_size: float = 0.002
    max_instances: int = 20000
    color_mode: str = "palette"
    material: Material = field(default_factory=Material)
    seed: int = 1
    visible: bool = True

    def copy(self) -> "Instancer":
        return replace(self, flame=self.flame.copy() if self.flame is not None else None, material=self.material.copy())

    def render_material(self) -> Material:
        """The material as the renderers see it: its colour mode follows the instancer's (`fixed` → the material's colour)."""
        return replace(self.material, color_mode="fixed" if self.color_mode == "fixed" else "palette")


@dataclass
class MeshSettings:
    """How the point cloud becomes a mesh (the Mesh tab).

    Attributes:
        points: Orbit points captured for the voxel grid.
        resolution: Voxels along the longest side of the bounding box.
        threshold: Iso-level on the normalized density (0..1; the histogram shows where the mass is).
        smoothing: Gaussian blur of the density in voxels before the isosurface.
        dilate, erode: Morphological radius in voxels (thicken / thin).
        colors: Carry the palette colours to the vertices.
        clean: The repair level of the clean mesh: `simple`, `aggressive` or `remesh`.
        min_piece_faces: Pieces with fewer faces are dropped by the clean-up.
        fill_holes: Boundary loops up to this many edges are closed (aggressive and remesh levels).
        smooth_iterations: Taubin smoothing passes on the clean mesh.
        target_faces: Decimate the clean mesh to about this many faces (0 = none).
        seed: Random seed of the capture.
    """
    points: int = 1_000_000
    resolution: int = 128
    threshold: float = 0.15
    smoothing: float = 1.0
    dilate: int = 0
    erode: int = 0
    colors: bool = True
    clean: str = "simple"
    min_piece_faces: int = 50
    fill_holes: int = 200
    smooth_iterations: int = 4
    target_faces: int = 200_000
    seed: int = 1

    def copy(self) -> "MeshSettings":
        return replace(self)


@dataclass
class ExportSettings:
    """What *Export* writes (the Export tab).

    Attributes:
        subject: `mesh` (the Mesh tab's mesh), `instances` (the instancers as instanced files: USD PointInstancer,
            glTF instancing, Blender Geometry Nodes; other formats get the baked mesh) or `baked` (every instance
            transformed into one mesh).
        form: `clean` (the print-ready mesh) or `full` (every triangle the isosurface produced).
        formats: Format keys (`solid.io.EXPORT_FORMATS`).
        materials: `vertex` (vertex colours), `texture` (UVs + a baked PNG) or `none` (geometry only).
        uv_mode: `box`, `spherical`, `cylindrical` or `atlas` (xatlas when installed).
        texture_size: Side of the baked texture in pixels.
        units: `world` (the flame's units as metres) or `mm` (scaled so the longest side is `size_mm`).
        size_mm: Target longest side in millimetres for `mm` units.
        blender: Also write the Blender scene script.
        report: Also write the mesh report (`name_report.md`).
        folder, name: Destination folder and base file name ("" = ask / the scene's name).
    """
    subject: str = "mesh"
    form: str = "clean"
    formats: list[str] = field(default_factory=lambda: ["glb"])
    materials: str = "vertex"
    uv_mode: str = "box"
    texture_size: int = 1024
    units: str = "world"
    size_mm: float = 100.0
    blender: bool = True
    report: bool = True
    folder: str = ""
    name: str = ""

    def copy(self) -> "ExportSettings":
        return replace(self, formats=list(self.formats))


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
        mesh: Meshing settings.
        export: Export settings.
        assets: Meshes to instance.
        instancers: The instancers (Holon IFS).
    """
    name: str = "scene"
    fractal: Flame | None = None
    follow_main: bool = False
    solid: SolidSettings = field(default_factory=SolidSettings)
    materials: list[Material] = field(default_factory=lambda: [Material()])
    lights: list[DistantLight] = field(default_factory=lambda: [DistantLight(), DistantLight(30.0, 150.0, (190, 205, 255), 0.35, False)])
    environment: Environment = field(default_factory=Environment)
    mesh: MeshSettings = field(default_factory=MeshSettings)
    export: ExportSettings = field(default_factory=ExportSettings)
    assets: list[MeshAsset] = field(default_factory=list)
    instancers: list[Instancer] = field(default_factory=list)

    def transform_count(self) -> int:
        """Transforms of the fractal, the final one included (the material count when there is no fractal)."""
        if self.fractal is None:
            return max(1, len(self.materials))
        return max(1, len(self.fractal.xforms) + (1 if self.fractal.final is not None else 0))

    def material_for_transform(self, index: int) -> Material:
        """The material of transform `index` (the last material repeats for transforms beyond the list)."""
        if not self.materials:
            return Material()
        return self.materials[min(max(0, index), len(self.materials) - 1)]

    def render_materials(self, transform_count: int | None = None) -> list[Material]:
        """The table a render indexes: one entry per transform (`transform_count`, default the fractal's), then one
        per instancer (`instancer_material_index`)."""
        count = self.transform_count() if transform_count is None else max(1, transform_count)
        return [self.material_for_transform(i) for i in range(count)] + [inst.render_material() for inst in self.instancers]

    def material_for(self, index: int, transform_count: int | None = None) -> Material:
        """The material of render index `index` (see `render_materials`)."""
        mats = self.render_materials(transform_count)
        return mats[min(max(0, index), len(mats) - 1)]

    def instancer_material_index(self, instancer_index: int, transform_count: int | None = None) -> int:
        """The render material index of instancer `instancer_index`."""
        count = self.transform_count() if transform_count is None else max(1, transform_count)
        return count + instancer_index

    def asset_named(self, name: str) -> MeshAsset | None:
        for asset in self.assets:
            if asset.name == name:
                return asset
        return None

    def visible_instancers(self) -> list[Instancer]:
        """Instancers that are visible and have an asset with a loaded mesh."""
        out = []
        for inst in self.instancers:
            asset = self.asset_named(inst.asset)
            if inst.visible and asset is not None and asset.mesh is not None:
                out.append(inst)
        return out

    def copy(self) -> "Scene3D":
        """Independent copy (the flame, every material and light duplicated)."""
        return Scene3D(self.name, self.fractal.copy() if self.fractal else None, self.follow_main, self.solid.copy(),
                       [m.copy() for m in self.materials], [li.copy() for li in self.lights], self.environment.copy(),
                       self.mesh.copy(), self.export.copy(), [a.copy() for a in self.assets], [i.copy() for i in self.instancers])

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
            "mesh": asdict(self.mesh),
            "export": asdict(self.export),
            "assets": [{k: v for k, v in asdict(a).items() if k != "mesh"} for a in self.assets],
            "instancers": [_instancer_dict(i) for i in self.instancers],
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
            mesh=_load(MeshSettings, data.get("mesh")),
            export=_load(ExportSettings, data.get("export")),
            assets=[_load(MeshAsset, a) for a in data.get("assets", [])],
            instancers=[_load_instancer(i) for i in data.get("instancers", [])],
        )


def _instancer_dict(inst: Instancer) -> dict:
    out = {k: v for k, v in asdict(inst).items() if k not in ("flame", "material")}
    out["flame"] = inst.flame.to_dict() if inst.flame is not None else None
    out["material"] = asdict(inst.material)
    return out


def _load_instancer(data: dict) -> Instancer:
    flame = data.get("flame")
    material = data.get("material")
    inst = _load(Instancer, {k: v for k, v in data.items() if k not in ("flame", "material", "mesh")})
    inst.flame = Flame.from_dict(flame) if flame else None
    inst.material = _load(Material, material)
    return inst


def _load(cls, data: dict | None):
    """A dataclass from a dict, keeping only known fields and turning colour lists back into tuples."""
    if not data:
        return cls()
    known = {f.name for f in fields(cls)}
    values = {}
    for key, value in data.items():
        if key not in known:
            continue
        if key.endswith("color") or key == "fog_color":
            value = tuple(int(v) for v in value)
        elif key == "formats":
            value = [str(v) for v in value]
        values[key] = value
    return cls(**values)


def materials_for(flame: Flame | None, existing: list[Material] | None = None) -> list[Material]:
    """One material per transform of `flame` (the final transform included), keeping `existing` ones where they are."""
    count = (len(flame.xforms) + (1 if flame.final else 0)) if flame is not None else 1
    out = [m.copy() for m in (existing or [])][:count]
    while len(out) < count:
        out.append(out[-1].copy() if out else Material())
    return out


__all__ = ["Scene3D", "Material", "DistantLight", "Environment", "SolidSettings", "MeshSettings", "ExportSettings", "MeshAsset",
           "Instancer", "materials_for", "FORMAT_VERSION", "RGB"]
