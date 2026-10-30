"""Drawing a mesh in the 3D Editor's viewport: points sampled on its faces through the solid shader.

The viewport shows images, not geometry, so the generated mesh is shown the way the fractal is: a point cloud
splatted into a G-buffer and shaded with the scene's materials, lights and shadows. The points are sampled
uniformly over the faces (area-weighted, `samples` of them), carry the vertex colours (quantised to a
256-entry palette, which is what the G-buffer stores), and see the same camera as the fractal — so the mesh
lands exactly over the solid render it came from.
"""

from __future__ import annotations

import numpy as np

from ..fractal.scene import Camera
from ..scene3d.model import Scene3D
from .gbuffer import GBuffer, ShadowMap
from .mesh import Mesh
from .shading import MAX_LIGHTS, shade
from .view import View

SHADOW_MAP_SIZE = 1024
SHADOW_BIAS_SCALE = 3.0       # point-sampled shadow maps need more bias than the fractal's dense ones (no acne)


class _Palette:
    """What `shade()` reads from a flame: the palette."""
    __slots__ = ("palette",)

    def __init__(self, palette: np.ndarray):
        self.palette = palette


def fallback_palette() -> np.ndarray:
    """A 6 × 6 × 6 colour cube plus 40 greys, `(256, 3)` uint8 — for meshes that did not come from a flame."""
    palette = np.zeros((256, 3), dtype=np.uint8)
    index = 0
    for r in range(6):
        for g in range(6):
            for b in range(6):
                palette[index] = (51 * r, 51 * g, 51 * b)
                index += 1
    for i in range(40):
        palette[index + i] = (round(255 * i / 39),) * 3
    return palette


def nearest_palette_index(colors: np.ndarray, palette: np.ndarray, chunk: int = 8192) -> np.ndarray:
    """The index of the nearest palette entry (`(256, 3)` uint8) for each colour (`(N, 3)` in 0..1)."""
    pal = palette.astype(np.float32) / 255.0
    out = np.empty(colors.shape[0], dtype=np.int16)
    for start in range(0, colors.shape[0], chunk):
        part = np.clip(colors[start:start + chunk], 0.0, 1.0).astype(np.float32)
        d = ((part[:, None, :] - pal[None, :, :]) ** 2).sum(axis=2)
        out[start:start + chunk] = np.argmin(d, axis=1)
    return out


def quantize_colors(mesh: Mesh, palette: np.ndarray | None) -> tuple[np.ndarray, np.ndarray]:
    """(palette `(256, 3)` uint8, palette index per *vertex*): the flame's palette when given, else `fallback_palette`."""
    pal = palette.astype(np.uint8) if palette is not None else fallback_palette()
    if mesh.colors is None:
        grey = int(np.argmin(np.abs(pal.astype(int) - 200).sum(axis=1)))
        return pal, np.full(mesh.vertex_count, grey, dtype=np.int16)
    return pal, nearest_palette_index(mesh.colors, pal)


def sample_surface(mesh: Mesh, samples: int, seed: int = 1) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """`samples` points uniformly over the faces: (positions `(S, 3)`, interpolated normals `(S, 3)`, the vertex nearest
    each point, the face index)."""
    rng = np.random.default_rng(seed)
    areas = mesh.face_areas()
    total = areas.sum()
    if mesh.face_count == 0 or total <= 0:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    cumulative = np.cumsum(areas)
    faces = np.minimum(np.searchsorted(cumulative, rng.random(samples) * total, side="right"), mesh.face_count - 1)
    r1, r2 = rng.random(samples), rng.random(samples)
    s1 = np.sqrt(r1)
    w = np.stack([1.0 - s1, s1 * (1.0 - r2), s1 * r2], axis=1)
    v = mesh.vertices
    f = mesh.faces[faces]
    points = w[:, 0:1] * v[f[:, 0]] + w[:, 1:2] * v[f[:, 1]] + w[:, 2:3] * v[f[:, 2]]
    vn = mesh.normals if mesh.normals is not None else mesh.compute_normals()
    normals = w[:, 0:1] * vn[f[:, 0]] + w[:, 1:2] * vn[f[:, 1]] + w[:, 2:3] * vn[f[:, 2]]
    length = np.linalg.norm(normals, axis=1, keepdims=True)
    normals = np.where(length > 1e-12, normals / np.maximum(length, 1e-12), mesh.face_normals()[faces])
    nearest_vertex = f[np.arange(samples), np.argmax(w, axis=1)]
    return points, normals, nearest_vertex, faces


def render_mesh(mesh: Mesh, camera: Camera, scene: Scene3D, width: int, height: int, oversample: int = 2,
                samples: int = 1_500_000, material_index: int | None = None, seed: int = 1) -> np.ndarray:
    """The mesh as the solid renderer would show a point cloud lying on it: RGBA8 `(height, width, 4)`.

    `camera` is the flame's (sized for `width × height`); the scene's materials (material `material_index`, or the
    first) / lights / environment / renderer settings apply; colours are quantised to the flame's palette.
    """
    view = View(camera, width, height, oversample)
    points, normals, nearest_vertex, _faces = sample_surface(mesh, samples, seed)
    flame_palette = np.asarray(scene.fractal.palette) if scene.fractal is not None else None
    palette, vertex_index = quantize_colors(mesh, flame_palette)
    color_index = vertex_index[nearest_vertex] if points.shape[0] else np.zeros(0, dtype=np.int16)
    gbuffer = GBuffer(*view.size, with_normals=True)
    shadow_maps: dict[int, ShadowMap] = {}
    material = np.full(points.shape[0], material_index if material_index is not None else 0, dtype=np.int16)
    if points.shape[0]:
        vx, vy, vz = view.to_view(points[:, 0], points[:, 1], points[:, 2])
        m = view.matrix
        view_normals = (normals @ m).astype(np.float32)      # rotate like positions (no depth offset)
        depth_range = view.depth_range(vz)
        bounds = view.bounds(vx, vy, vz)
        px, py = view.project(vx, vy, vz)
        gbuffer.splat(px, py, vx, vy, vz, color_index, material, view_normals)
        gbuffer.fill_gaps(1)                                 # a point splat leaves pin-holes: close them
        if scene.solid.display != "points":
            for index, light in enumerate(scene.lights[:MAX_LIGHTS]):
                if light.casts_shadows:
                    shadow = ShadowMap(light.altitude, light.azimuth, bounds, SHADOW_MAP_SIZE)
                    shadow.bias_scale = SHADOW_BIAS_SCALE
                    shadow.splat(vx, vy, vz)
                    shadow_maps[index] = shadow
    else:
        depth_range = (-1.0, 1.0)
    preview_scene = scene.copy()
    preview_scene.solid.min_hits = 1                       # the sampled cloud is dense and clean: every sample counts
    return shade(view, gbuffer, preview_scene, _Palette(palette), shadow_maps, depth_range)


__all__ = ["render_mesh", "sample_surface", "quantize_colors", "nearest_palette_index", "fallback_palette"]
