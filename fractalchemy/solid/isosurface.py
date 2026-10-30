"""The isosurface of a voxel grid as a triangle mesh: *naive surface nets*, vectorised in numpy.

Why surface nets rather than marching cubes: no 256-case tables to get wrong, no ambiguous cases (so no
holes where neighbouring cubes disagree), a mesh that is watertight by construction and one vertex per
surface cube, placed at the mean of the cube's edge crossings — smoother than marching cubes' edge vertices
and a better start for smoothing and decimation. Each grid edge whose ends lie on opposite sides of the
iso-level yields one quad joining the four cubes around it (two triangles), wound so the normals point
towards the lower density (outwards).

The grid's outermost layer is treated as outside whatever its density, so the surface always closes.
Vertex colours come from the colour grid (trilinear), vertex normals from the faces (`Mesh.compute_normals`).
"""

from __future__ import annotations

import numpy as np
from scipy import ndimage

from .mesh import Mesh
from .voxelize import VoxelGrid


def surface_nets(grid: VoxelGrid, iso: float, density: np.ndarray | None = None, with_color: bool = True) -> Mesh:
    """The iso-surface `density > iso` of `grid` (or of `density`, an array of the grid's shape: the normalized one).

    Returns an empty mesh when nothing crosses the level.
    """
    d = np.asarray(grid.density if density is None else density, dtype=np.float32)
    nx, ny, nz = d.shape
    if min(nx, ny, nz) < 3:
        return Mesh.empty()
    inside = d > iso
    inside[0, :, :] = inside[-1, :, :] = False
    inside[:, 0, :] = inside[:, -1, :] = False
    inside[:, :, 0] = inside[:, :, -1] = False
    inside = resolve_ambiguities(inside)
    # crossings along each axis: mask, interpolation parameter
    cross = []
    for axis in range(3):
        lo = _slice(inside, axis, 0, -1)
        hi = _slice(inside, axis, 1, None)
        mask = lo != hi
        d0 = _slice(d, axis, 0, -1)
        d1 = _slice(d, axis, 1, None)
        with np.errstate(divide="ignore", invalid="ignore"):
            t = np.where(mask, (iso - d0) / (d1 - d0), 0.0)
        t = np.clip(np.nan_to_num(t, nan=0.5), 0.0, 1.0).astype(np.float32)
        cross.append((mask, t))
    if not any(m.any() for m, _t in cross):
        return Mesh.empty()
    # one vertex per cube with crossings: the mean of its edges' crossing points (cube (a,b,c) spans grid points a..a+1 …)
    cube_shape = (nx - 1, ny - 1, nz - 1)
    count = np.zeros(cube_shape, dtype=np.int32)
    views = []                                                        # (axis, da, db, mask view, t view) per cube edge
    for axis in range(3):
        mask, t = cross[axis]
        others = [o for o in range(3) if o != axis]
        for da in (0, 1):
            for db in (0, 1):
                shifts = {others[0]: da, others[1]: db}
                sub_mask = _cube_view(mask, axis, shifts, cube_shape)
                views.append((axis, others, da, db, sub_mask, _cube_view(t, axis, shifts, cube_shape)))
                count += sub_mask
    active = count > 0
    active_idx = np.nonzero(active)
    n_vertices = int(active_idx[0].shape[0])
    vertex_index = np.full(cube_shape, -1, dtype=np.int64)
    vertex_index[active] = np.arange(n_vertices)
    base = np.stack(active_idx, axis=1).astype(np.float64)           # (V, 3) corner grid coordinates of the active cubes
    total = np.zeros((n_vertices, 3), dtype=np.float64)
    for axis, others, da, db, sub_mask, sub_t in views:
        m = sub_mask[active_idx]
        if not m.any():
            continue
        pos = base.copy()
        pos[:, axis] += sub_t[active_idx]
        pos[:, others[0]] += da
        pos[:, others[1]] += db
        total += pos * m[:, None]
    grid_pos = total / count[active_idx][:, None]
    # quads: one per crossing edge, joining the four cubes around it
    faces = []
    for axis in range(3):
        mask, _t = cross[axis]
        others = [(axis + 1) % 3, (axis + 2) % 3]      # cyclic, so every axis winds the same way
        idx = np.argwhere(mask)
        if idx.shape[0] == 0:
            continue
        low_inside = inside[tuple(idx.T)]
        corners = []
        for da, db in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            c = idx.copy()
            c[:, others[0]] += da
            c[:, others[1]] += db
            corners.append(vertex_index[tuple(c.T)])
        v0, v1, v2, v3 = corners
        quad = np.stack([v0, v1, v2, v3], axis=1)
        flip = ~low_inside                               # density rising along the edge: the surface faces −axis
        quad[flip] = quad[flip][:, ::-1]
        faces.append(quad[:, [0, 1, 2]])
        faces.append(quad[:, [0, 2, 3]])
    faces = np.concatenate(faces) if faces else np.zeros((0, 3), dtype=np.int64)
    faces = faces[(faces >= 0).all(axis=1)]
    vertices = grid.to_world(grid_pos)
    colors = None
    if with_color and grid.color is not None:
        # the mean colour at the vertices: interpolate the colour sums and the density separately, then divide
        coords = grid_pos.T
        weight = ndimage.map_coordinates(grid.density, coords, order=1, mode="nearest")
        sums = np.stack([ndimage.map_coordinates(grid.color[..., ch], coords, order=1, mode="nearest") for ch in range(3)], axis=1)
        colors = np.where(weight[:, None] > 1e-12, sums / np.maximum(weight, 1e-12)[:, None], 0.5)
        colors = np.clip(colors, 0.0, 1.0).astype(np.float32)
    mesh = Mesh(vertices, faces, colors=colors)
    if mesh.faces.shape[0] and mesh.signed_volume() < 0:
        mesh = mesh.flipped()
    mesh.compute_normals()
    return mesh


def resolve_ambiguities(inside: np.ndarray, max_passes: int = 16) -> np.ndarray:
    """Fill the diagonal 2 × 2 patterns (two inside voxels touching only along an edge) on every grid face.

    Such a face has all four of its edges crossing, so the four quads around them would share one cube-to-cube
    edge — a non-manifold edge. Filling the two outside voxels of each pattern makes every face unambiguous;
    a few passes settle the patterns the fills create. The outermost layer stays outside.
    """
    inside = inside.copy()
    for _ in range(max_passes):
        changed = False
        for axis in range(3):
            a, b = [o for o in range(3) if o != axis]
            s00 = _shift2(inside, a, b, 0, 0)
            s10 = _shift2(inside, a, b, 1, 0)
            s01 = _shift2(inside, a, b, 0, 1)
            s11 = _shift2(inside, a, b, 1, 1)
            diagonal = (s00 & s11 & ~s10 & ~s01) | (~s00 & ~s11 & s10 & s01)
            if not diagonal.any():
                continue
            changed = True
            fill = np.zeros_like(inside)
            for da, db in ((0, 0), (1, 0), (0, 1), (1, 1)):
                index = [slice(None)] * 3
                index[a] = slice(da, inside.shape[a] - 1 + da)
                index[b] = slice(db, inside.shape[b] - 1 + db)
                fill[tuple(index)] |= diagonal
            inside |= fill
        inside[0, :, :] = inside[-1, :, :] = False
        inside[:, 0, :] = inside[:, -1, :] = False
        inside[:, :, 0] = inside[:, :, -1] = False
        if not changed:
            break
    return inside


def _shift2(a: np.ndarray, axis_a: int, axis_b: int, da: int, db: int) -> np.ndarray:
    """`a` cropped by one along `axis_a` and `axis_b`, offset by (da, db): the four corners of every 2 × 2 face."""
    index = [slice(None)] * 3
    index[axis_a] = slice(da, a.shape[axis_a] - 1 + da)
    index[axis_b] = slice(db, a.shape[axis_b] - 1 + db)
    return a[tuple(index)]


def _slice(a: np.ndarray, axis: int, start: int, stop: int | None) -> np.ndarray:
    index = [slice(None)] * 3
    index[axis] = slice(start, stop)
    return a[tuple(index)]


def _cube_view(edge_array: np.ndarray, axis: int, shifts: dict[int, int], cube_shape: tuple[int, int, int]) -> np.ndarray:
    """The part of an edge array (edges along `axis`) belonging to cube corners shifted by `shifts` on the other axes."""
    index = []
    for a in range(3):
        if a == axis:
            index.append(slice(0, cube_shape[a]))
        else:
            s = shifts[a]
            index.append(slice(s, s + cube_shape[a]))
    return edge_array[tuple(index)]


__all__ = ["surface_nets", "resolve_ambiguities"]
