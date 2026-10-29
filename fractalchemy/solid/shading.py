"""Normals, ambient occlusion and lighting of a G-buffer — the numpy reference of the solid renderer.

* **Normals** from the view-space positions of each pixel's neighbours: the cross products of the eight
  neighbour pairs around a pixel (JWildfire's scheme), pairs that step across a depth discontinuity or into
  an empty pixel left out, the result smoothed and turned to face the camera.
* **Ambient occlusion** in screen space: hemisphere samples around each surface point, projected back into the
  G-buffer; a sample is an occluder when the surface there is nearer than the sample by more than a bias and
  by less than the radius.
* **Lighting**: per material — Lambert with light wrap, Blinn-Phong highlights, ambient from the environment —
  per distant light with its shadow map; fog by depth; exposure and sRGB encoding at the end.

`shade()` is the whole thing; `render/gpu_solid.py` reproduces it in GLSL and `tests/test_solid.py` keeps them equal.
"""

from __future__ import annotations

import math

import numpy as np

from ..fractal.scene import Flame
from ..scene3d.model import Scene3D
from .gbuffer import GBuffer, ShadowMap, downsample
from .view import View, light_direction

NEIGHBOUR_PAIRS = (((0, 1), (1, 0)), ((1, 0), (0, -1)), ((0, -1), (-1, 0)), ((-1, 0), (0, 1)),
                   ((-1, 1), (1, 1)), ((1, 1), (1, -1)), ((1, -1), (-1, -1)), ((-1, -1), (-1, 1)))   # (dy, dx) pairs, clockwise
DISCONTINUITY = 0.03       # a neighbour further away (in depth) than this × the depth span is another surface
AO_BIAS = 0.02             # fraction of the AO radius a sample must be behind the surface to count
MAX_LIGHTS = 8


# --- normals ----------------------------------------------------------------------------------------------------
def _shift(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """`a` moved so that `out[y, x] = a[y + dy, x + dx]` (edges repeat)."""
    out = np.roll(np.roll(a, -dy, axis=0), -dx, axis=1)
    if dy > 0:
        out[-dy:] = a[-1:]
    elif dy < 0:
        out[:-dy] = a[:1]
    if dx > 0:
        out[:, -dx:] = out[:, -dx - 1:-dx]
    elif dx < 0:
        out[:, :-dx] = out[:, -dx:-dx + 1]
    return out


def normals_from_positions(pos: np.ndarray, hits: np.ndarray, smoothing: float = 1.0, limit: float | None = None) -> np.ndarray:
    """Unit normals `(H, W, 3)` of the surface in a G-buffer (zero where empty), facing +z (the camera side).

    Neighbours further away in depth than `limit` (default: `DISCONTINUITY` × the depth span of what was hit) are
    taken to belong to another surface and do not contribute.
    """
    pos = pos.astype(np.float64)
    depth = -pos[..., 2]
    if limit is None:
        finite = depth[hits]
        limit = DISCONTINUITY * max(float(finite.max() - finite.min()) if finite.size else 1.0, 1e-9)
    normal = np.zeros_like(pos)
    offsets = {}
    valid = {}
    for (dy, dx) in {p for pair in NEIGHBOUR_PAIRS for p in pair}:
        offsets[(dy, dx)] = _shift(pos, dy, dx) - pos
        valid[(dy, dx)] = _shift(hits, dy, dx) & (np.abs(_shift(depth, dy, dx) - depth) < limit)
    for a, b in NEIGHBOUR_PAIRS:
        ok = valid[a] & valid[b]
        cross = np.cross(offsets[a], offsets[b])
        normal += np.where(ok[..., None], cross, 0.0)
    if smoothing > 0:
        normal = box_blur(normal, int(round(smoothing)), hits)
    length = np.linalg.norm(normal, axis=-1, keepdims=True)
    normal = np.where(length > 1e-20, normal / np.maximum(length, 1e-20), 0.0)
    flip = normal[..., 2] < 0                        # towards the camera (+z)
    normal[flip] = -normal[flip]
    normal[~hits] = 0.0
    return normal


def box_blur(field: np.ndarray, radius: int, mask: np.ndarray) -> np.ndarray:
    """Average over a `(2r+1)²` window, counting only pixels in `mask` (empty pixels do not pull the field)."""
    if radius <= 0:
        return field
    weight = mask.astype(np.float64)
    total = np.zeros_like(field)
    count = np.zeros(field.shape[:2])
    for dy in range(-radius, radius + 1):
        for dx in range(-radius, radius + 1):
            total += _shift(field, dy, dx) * _shift(weight, dy, dx)[..., None]
            count += _shift(weight, dy, dx)
    return np.where(count[..., None] > 0, total / np.maximum(count, 1e-9)[..., None], field)


# --- ambient occlusion ------------------------------------------------------------------------------------------
def ao_kernel(samples: int) -> np.ndarray:
    """`samples` unit vectors spread over the upper hemisphere (z > 0), weighted towards the normal — a fixed
    pattern so numpy and GLSL agree."""
    out = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(samples):
        t = (i + 0.5) / samples
        z = 0.15 + 0.85 * t                                   # never grazing
        r = math.sqrt(max(0.0, 1.0 - z * z))
        a = i * golden
        out.append((r * math.cos(a), r * math.sin(a), z))
    return np.array(out)


def tangent_frame(normal: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Two unit tangents `(H, W, 3)` perpendicular to each normal (zero normals give zero tangents)."""
    helper = np.where(np.abs(normal[..., 1:2]) < 0.9, np.array([0.0, 1.0, 0.0]), np.array([1.0, 0.0, 0.0]))
    t = np.cross(helper, normal)
    length = np.linalg.norm(t, axis=-1, keepdims=True)
    t = np.where(length > 1e-12, t / np.maximum(length, 1e-12), 0.0)
    b = np.cross(normal, t)
    return t, b


def ambient_occlusion(view: View, gbuffer: GBuffer, normal: np.ndarray, radius: float, samples: int, falloff: float,
                      intensity: float) -> np.ndarray:
    """`(H, W)` occlusion factor in 0..1 (1 = open): hemisphere samples of world radius `radius` around each surface
    point, each an occluder when the G-buffer surface at its pixel is nearer to the camera than the sample."""
    hits = gbuffer.hits
    pos = gbuffer.pos.astype(np.float64)
    t, b = tangent_frame(normal)
    kernel = ao_kernel(samples)
    depth = gbuffer.depth.astype(np.float64)
    occluded = np.zeros(pos.shape[:2])
    h, w = pos.shape[:2]
    for kx, ky, kz in kernel:
        sample = pos + radius * (kx * t + ky * b + kz * normal)
        px, py = view.project(sample[..., 0].reshape(-1), sample[..., 1].reshape(-1), sample[..., 2].reshape(-1))
        xi = np.clip(np.rint(px).astype(np.intp), 0, w - 1).reshape(h, w)
        yi = np.clip(np.rint(py).astype(np.intp), 0, h - 1).reshape(h, w)
        surface = depth[yi, xi]
        sample_depth = -sample[..., 2]
        diff = sample_depth - surface                         # > 0: the surface is in front of the sample
        inside = np.isfinite(surface) & (diff > AO_BIAS * radius) & (diff < radius)
        weight = np.where(inside, 1.0 - np.clip(diff / radius, 0.0, 1.0) ** max(falloff, 1e-3), 0.0)   # near occluders count most
        occluded += weight
    ao = 1.0 - intensity * occluded / max(1, samples)
    ao[~hits] = 1.0
    return box_blur(ao[..., None], 1, hits)[..., 0]


# --- lighting ----------------------------------------------------------------------------------------------------
def shade(view: View, gbuffer: GBuffer, scene: Scene3D, flame: Flame, shadow_maps: dict[int, ShadowMap] | None = None,
          depth_range: tuple[float, float] | None = None) -> np.ndarray:
    """The lit image `(height, width, 4)` uint8 of the G-buffer (downsampled from the supersampled size).

    `shadow_maps` holds one map per shadow-casting light index; `depth_range` scales the fog and the AO radius.
    """
    solid, env = scene.solid, scene.environment
    gbuffer = gbuffer.thresholded(int(solid.min_hits))
    hits = gbuffer.hits
    h, w = gbuffer.depth.shape
    palette = np.asarray(flame.palette, dtype=np.float64) / 255.0
    color_index = np.clip(gbuffer.color, 0, 255)
    base = palette[color_index]                                   # (H, W, 3)
    material_index = np.clip(gbuffer.material, 0, max(0, len(scene.materials) - 1))
    mats = [scene.material_for(i) for i in range(max(1, len(scene.materials)))]
    table = np.array([[m.diffuse, m.ambient, m.specular, m.shininess, m.wrap, 1.0 if m.color_mode == "fixed" else 0.0,
                       *(c / 255.0 for c in m.specular_color), *(c / 255.0 for c in m.color)] for m in mats])
    mat = table[material_index]                                   # (H, W, 12)
    fixed = mat[..., 5:6]
    base = base * (1.0 - fixed) + mat[..., 9:12] * fixed
    if solid.display == "points":
        rgb = base
        normal = np.zeros_like(base)
        ao = np.ones((h, w))
    else:
        near, far = depth_range if depth_range is not None else view.depth_range(gbuffer.pos[hits][:, 2] if hits.any() else np.array([0.0]))
        span = max(far - near, 1e-6)
        normal = normals_from_positions(gbuffer.pos, hits, solid.normal_smoothing, DISCONTINUITY * span)
        ao = np.ones((h, w))
        if solid.ao and hits.any():
            ao = ambient_occlusion(view, gbuffer, normal, solid.ao_radius * span * 4.0, solid.ao_samples, solid.ao_falloff, solid.ao_intensity)
        v = view.view_direction(gbuffer.pos.astype(np.float64))
        env_color = np.array(env.color) / 255.0
        rgb = base * (mat[..., 1:2] * env.ambient * env_color) * ao[..., None]
        for index, light in enumerate(scene.lights[:MAX_LIGHTS]):
            L = light_direction(light.altitude, light.azimuth)
            ndl = (normal @ L)
            wrap = mat[..., 4]
            lambert = np.clip((ndl + wrap) / (1.0 + wrap), 0.0, 1.0)
            half = v + L
            half /= np.maximum(np.linalg.norm(half, axis=-1, keepdims=True), 1e-12)
            ndh = np.clip((normal * half).sum(axis=-1), 0.0, 1.0)
            spec = np.where(ndl > 0, ndh ** np.maximum(mat[..., 3], 1.0), 0.0)
            lit = np.ones((h, w))
            if light.shadows and shadow_maps and index in shadow_maps:
                lit = 1.0 - light.shadow_intensity * shadow_maps[index].occlusion(gbuffer.pos.astype(np.float64), light.shadow_softness)
            light_color = np.array(light.color) / 255.0 * light.intensity
            rgb = rgb + base * (mat[..., 0:1] * lambert[..., None]) * light_color * (lit * ao)[..., None]
            rgb = rgb + mat[..., 6:9] * (mat[..., 2:3] * spec[..., None]) * light_color * lit[..., None]
        if solid.fog:
            depth = gbuffer.depth.astype(np.float64)
            t = np.clip((depth - (near + solid.fog_start * span)) / max((solid.fog_end - solid.fog_start) * span, 1e-6), 0.0, 1.0)
            rgb = rgb * (1.0 - t[..., None]) + (np.array(solid.fog_color) / 255.0) * t[..., None]
    rgb = np.clip(rgb * env.exposure, 0.0, 1.0)
    background = np.array(env.color) / 255.0
    rgba = np.empty((h, w, 4))
    rgba[..., :3] = np.where(hits[..., None], rgb, background if env.visible else 0.0)
    rgba[..., 3] = np.where(hits, 1.0, 1.0 if env.visible else 0.0)
    rgba = downsample(rgba, view.oversample)
    encoded = np.where(rgba[..., :3] <= 0.0031308, rgba[..., :3] * 12.92, 1.055 * np.power(np.maximum(rgba[..., :3], 1e-9), 1 / 2.4) - 0.055)
    out = np.empty(rgba.shape, dtype=np.uint8)
    out[..., :3] = np.clip(encoded * 255.0 + 0.5, 0, 255).astype(np.uint8)
    out[..., 3] = np.clip(rgba[..., 3] * 255.0 + 0.5, 0, 255).astype(np.uint8)
    return out


__all__ = ["shade", "normals_from_positions", "ambient_occlusion", "ao_kernel", "tangent_frame", "box_blur", "NEIGHBOUR_PAIRS", "MAX_LIGHTS"]
