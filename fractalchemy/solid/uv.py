"""Texture coordinates for exported meshes, and baking vertex colours into a texture.

Three projections: **box** (each face goes to the atlas tile of its dominant normal axis — six tiles in a
3 × 2 grid; vertices are split per face so tiles do not bleed), **spherical** and **cylindrical** (per vertex,
around the z axis; the seam is left as it is). `xatlas`, when installed, gives a proper atlas instead.
`bake_vertex_colors()` paints the mesh's vertex colours into a texture through its UVs: every triangle is
rasterised in UV space with barycentric colour interpolation, then the empty texels are filled from their
nearest painted neighbour so samplers at tile edges never read black.
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from .mesh import Mesh

TILE_MARGIN = 0.01


def unweld(mesh: Mesh) -> Mesh:
    """Every face gets its own three vertices (what per-face UVs need)."""
    f = mesh.faces.reshape(-1)
    out = Mesh(mesh.vertices[f], np.arange(f.shape[0]).reshape(-1, 3),
               None if mesh.normals is None else mesh.normals[f], None if mesh.colors is None else mesh.colors[f],
               None if mesh.uvs is None else mesh.uvs[f])
    return out


def box_uvs(mesh: Mesh) -> Mesh:
    """Per-face box projection into a 3 × 2 tile atlas (the mesh is unwelded first)."""
    out = unweld(mesh)
    if out.face_count == 0:
        out.uvs = np.zeros((0, 2), dtype=np.float32)
        return out
    normals = out.face_normals()
    axis = np.argmax(np.abs(normals), axis=1)                         # dominant axis per face
    sign = np.sign(normals[np.arange(normals.shape[0]), axis])
    lo, hi = out.bounds()
    span = np.maximum(hi - lo, 1e-12)
    rel = (out.vertices - lo) / span                                   # 0..1 in the box
    uvs = np.zeros((out.vertex_count, 2), dtype=np.float64)
    face_axis = np.repeat(axis, 3)
    face_sign = np.repeat(sign, 3)
    for a in range(3):
        u_axis, v_axis = [(1, 2), (0, 2), (0, 1)][a]
        sel = face_axis == a
        u = rel[sel, u_axis]
        v = rel[sel, v_axis]
        u = np.where(face_sign[sel] < 0, 1.0 - u, u)                  # mirror the back faces so they read the same way
        tile_x = a
        tile_y = (face_sign[sel] > 0).astype(np.float64)
        uvs[sel, 0] = (tile_x + TILE_MARGIN + u * (1 - 2 * TILE_MARGIN)) / 3.0
        uvs[sel, 1] = (tile_y + TILE_MARGIN + v * (1 - 2 * TILE_MARGIN)) / 2.0
    out.uvs = uvs.astype(np.float32)
    return out


def spherical_uvs(mesh: Mesh) -> Mesh:
    """Longitude / latitude around the z axis through the bounding-box centre."""
    out = mesh.copy()
    lo, hi = out.bounds()
    p = out.vertices - (lo + hi) / 2.0
    r = np.maximum(np.linalg.norm(p, axis=1), 1e-12)
    u = (np.arctan2(p[:, 1], p[:, 0]) / (2 * np.pi)) % 1.0
    v = np.arccos(np.clip(p[:, 2] / r, -1.0, 1.0)) / np.pi
    out.uvs = np.stack([u, 1.0 - v], axis=1).astype(np.float32)
    return out


def cylindrical_uvs(mesh: Mesh) -> Mesh:
    """Angle around the z axis, height along it."""
    out = mesh.copy()
    lo, hi = out.bounds()
    p = out.vertices - (lo + hi) / 2.0
    u = (np.arctan2(p[:, 1], p[:, 0]) / (2 * np.pi)) % 1.0
    span = max(float(hi[2] - lo[2]), 1e-12)
    v = (out.vertices[:, 2] - lo[2]) / span
    out.uvs = np.stack([u, v], axis=1).astype(np.float32)
    return out


def atlas_uvs(mesh: Mesh) -> Mesh | None:
    """UVs from `xatlas` (None when it is not installed)."""
    try:
        import xatlas  # type: ignore
    except ImportError:
        return None
    vmapping, indices, uvs = xatlas.parametrize(mesh.vertices.astype(np.float32), mesh.faces.astype(np.uint32))
    out = Mesh(mesh.vertices[vmapping], indices.astype(np.int64), None if mesh.normals is None else mesh.normals[vmapping],
               None if mesh.colors is None else mesh.colors[vmapping], uvs.astype(np.float32))
    return out


def with_uvs(mesh: Mesh, mode: str) -> Mesh:
    """The mesh with UVs by `mode`: `box`, `spherical`, `cylindrical` or `atlas` (falls back to box without xatlas)."""
    if mode == "atlas":
        out = atlas_uvs(mesh)
        if out is not None:
            return out
        mode = "box"
    if mode == "spherical":
        return spherical_uvs(mesh)
    if mode == "cylindrical":
        return cylindrical_uvs(mesh)
    return box_uvs(mesh)


def bake_vertex_colors(mesh: Mesh, size: int = 1024) -> np.ndarray:
    """An `(size, size, 3)` uint8 texture of the mesh's vertex colours painted through its UVs (row 0 = v 1, image order).

    Raises:
        ValueError: When the mesh has no UVs or no colours.
    """
    if mesh.uvs is None or mesh.colors is None:
        raise ValueError("baking needs a mesh with UVs and vertex colours")
    size = int(size)
    image = np.zeros((size, size, 3), dtype=np.float64)
    weight = np.zeros((size, size), dtype=np.float64)
    uv = mesh.uvs.astype(np.float64)
    px = np.stack([uv[:, 0] * (size - 1), (1.0 - uv[:, 1]) * (size - 1)], axis=1)   # image coordinates (x right, y down)
    faces = mesh.faces
    colors = mesh.colors.astype(np.float64)
    # rasterise triangle by triangle in UV space, grouped by bounding-box size so small ones are cheap
    tri = px[faces]                                                     # (M, 3, 2)
    lo = np.floor(tri.min(axis=1)).astype(int)
    hi = np.ceil(tri.max(axis=1)).astype(int)
    small = (hi - lo).max(axis=1) <= 1                                  # sub-texel triangles: paint the centroid texel, vectorised
    if small.any():
        centre = np.rint(tri[small].mean(axis=1)).astype(int)
        ok = (centre[:, 0] >= 0) & (centre[:, 0] < size) & (centre[:, 1] >= 0) & (centre[:, 1] < size)
        idx = centre[ok, 1] * size + centre[ok, 0]
        mean = colors[faces[small][ok]].mean(axis=1)
        flat = image.reshape(-1, 3)
        for ch in range(3):
            flat[:, ch] += np.bincount(idx, weights=mean[:, ch], minlength=size * size)
        weight.reshape(-1)[:] += np.bincount(idx, minlength=size * size)
    for m in np.nonzero(~small)[0]:
        x0, y0 = max(lo[m, 0], 0), max(lo[m, 1], 0)
        x1, y1 = min(hi[m, 0], size - 1), min(hi[m, 1], size - 1)
        if x1 < x0 or y1 < y0:
            continue
        ys, xs = np.mgrid[y0:y1 + 1, x0:x1 + 1]
        a, b, c = tri[m]
        det = (b[0] - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (b[1] - a[1])
        if abs(det) < 1e-12:
            w_a = w_b = w_c = np.full(xs.shape, 1 / 3)
            inside = np.ones(xs.shape, dtype=bool)
        else:
            w_b = ((xs - a[0]) * (c[1] - a[1]) - (c[0] - a[0]) * (ys - a[1])) / det
            w_c = ((b[0] - a[0]) * (ys - a[1]) - (xs - a[0]) * (b[1] - a[1])) / det
            w_a = 1.0 - w_b - w_c
            inside = (w_a >= -0.02) & (w_b >= -0.02) & (w_c >= -0.02)
        if not inside.any():
            # a sub-pixel triangle: paint its centroid texel
            cx, cy = int(round(tri[m, :, 0].mean())), int(round(tri[m, :, 1].mean()))
            if 0 <= cx < size and 0 <= cy < size:
                image[cy, cx] += colors[faces[m]].mean(axis=0)
                weight[cy, cx] += 1.0
            continue
        ca, cb, cc = colors[faces[m]]
        col = w_a[..., None] * ca + w_b[..., None] * cb + w_c[..., None] * cc
        image[ys[inside], xs[inside]] += col[inside]
        weight[ys[inside], xs[inside]] += 1.0
    painted = weight > 0
    image[painted] /= weight[painted][:, None]
    if painted.any() and not painted.all():
        # fill the gaps from the nearest painted texel (so bilinear sampling at edges stays clean)
        _dist, (iy, ix) = ndimage.distance_transform_edt(~painted, return_indices=True)
        image = image[iy, ix]
    return np.clip(image * 255.0 + 0.5, 0, 255).astype(np.uint8)


__all__ = ["unweld", "box_uvs", "spherical_uvs", "cylindrical_uvs", "atlas_uvs", "with_uvs", "bake_vertex_colors"]
