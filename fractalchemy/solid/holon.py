"""The Holon IFS: meshes instanced along a fractal, turned and scaled by the orbit's accumulated frames.

Every transform of a flame maps a neighbourhood of a point somewhere else, turning and squashing it on the way.
The local **Jacobian** (by finite differences — exact for affine transforms, sensible for `spherical`,
`julia3D` and the rest) says how; its polar decomposition gives a rotation and a scale. Composing the
Jacobians along the orbit gives each orbit point a **frame**, and an instance of a mesh placed with that frame
sits in the fractal the way a Xenodream holon does.

Two ways to pick the points: the **chaos game** (`chaos_instances`: orbit samples, each frame the product of
the last `depth` Jacobians, so the sizes are those of depth-`depth` holons) and the **tree** (`tree_instances`:
every composition of the transforms to depth `depth` from the origin — deterministic and gap-free, the classic
structure). The result is an `InstanceSet`; `instance_points()` samples the asset's surface per instance for
the renderers, `bake_instances()` writes them out as one mesh, `primitive()` makes the built-in assets, and
`affine3d_xform()` / `read_affine3d()` are the Instances tab's representation of a 3D affine transform as a
normal flame transform (`linear3D` + `zscale` + `ztranslate` + `post_rotate_x/y`).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ..fractal.scene import Flame, XForm
from ..render.compiled import CompiledFlame, CompiledXForm
from ..render.cpu_engine import PointPopulation, apply_xform
from .mesh import Mesh
from .mesh_preview import nearest_palette_index

EPSILON = 1e-4
MIN_SCALE, MAX_SCALE = 1e-9, 1e9
PRIMITIVES = ("sphere", "cube", "torus", "tetrahedron", "icosahedron", "cylinder", "dla")


@dataclass
class InstanceSet:
    """Where the instances go.

    Attributes:
        positions: `(N, 3)` world positions.
        rotations: `(N, 3, 3)` rotation matrices (columns = the instance's axes in world space).
        scales: `(N,)` uniform scale factors accumulated along the orbit (before the instancer's base size).
        colors: `(N,)` uint8 palette index of the orbit point.
        xform: `(N,)` int16 transform that produced the point (−1 for the tree's root).
        level: `(N,)` int16 tree depth (chaos mode: `depth`).
    """
    positions: np.ndarray
    rotations: np.ndarray
    scales: np.ndarray
    colors: np.ndarray
    xform: np.ndarray
    level: np.ndarray

    def __len__(self) -> int:
        return int(self.positions.shape[0])

    @classmethod
    def empty(cls) -> "InstanceSet":
        return cls(np.zeros((0, 3)), np.zeros((0, 3, 3)), np.zeros(0), np.zeros(0, np.uint8), np.zeros(0, np.int16), np.zeros(0, np.int16))

    def subset(self, mask) -> "InstanceSet":
        return InstanceSet(self.positions[mask], self.rotations[mask], self.scales[mask], self.colors[mask], self.xform[mask], self.level[mask])

    def transforms(self, size: float = 1.0) -> np.ndarray:
        """`(N, 4, 4)` matrices taking the asset (unit size) to each instance."""
        n = len(self)
        out = np.zeros((n, 4, 4))
        out[:, :3, :3] = self.rotations * (self.scales * size)[:, None, None]
        out[:, :3, 3] = self.positions
        out[:, 3, 3] = 1.0
        return out

    def quaternions(self) -> np.ndarray:
        """`(N, 4)` unit quaternions `(x, y, z, w)` of the rotations."""
        return rotation_to_quaternion(self.rotations)

    def sized(self, size: float, falloff: float = 1.0, min_size: float = 0.0, cap: int = 0) -> "InstanceSet":
        """Apply the instancer's size rules: scale `size · s^falloff`, drop instances under `min_size`, keep the largest `cap`."""
        scales = size * np.power(np.maximum(self.scales, MIN_SCALE), falloff)
        out = InstanceSet(self.positions, self.rotations, scales, self.colors, self.xform, self.level)
        if min_size > 0:
            out = out.subset(scales >= min_size)
        if cap > 0 and len(out) > cap:
            keep = np.argsort(-out.scales, kind="stable")[:cap]
            out = out.subset(np.sort(keep))
        return out


# --- frames ----------------------------------------------------------------------------------------------------------
def polar_decompose(m: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """(rotation `(N, 3, 3)` with det +1, uniform scale `(N,)` = ∛|det|) of `(N, 3, 3)` matrices (SVD)."""
    m = np.asarray(m, dtype=np.float64)
    finite = np.isfinite(m).all(axis=(1, 2))
    safe = np.where(finite[:, None, None], m, np.eye(3))
    u, sigma, vt = np.linalg.svd(safe)
    rotation = u @ vt
    det = np.linalg.det(rotation)
    flip = det < 0
    if flip.any():
        u = u.copy()
        u[flip, :, 2] *= -1
        rotation = u @ vt
    scale = np.cbrt(np.abs(np.prod(sigma, axis=1)))
    scale = np.clip(np.where(finite, scale, 1.0), MIN_SCALE, MAX_SCALE)
    return rotation, scale


def rotation_to_quaternion(r: np.ndarray) -> np.ndarray:
    """`(N, 4)` unit quaternions `(x, y, z, w)` from `(N, 3, 3)` rotation matrices (Shepperd's method, vectorised)."""
    r = np.asarray(r, dtype=np.float64)
    n = r.shape[0]
    q = np.zeros((n, 4))
    trace = r[:, 0, 0] + r[:, 1, 1] + r[:, 2, 2]
    a = trace > 0
    s = np.sqrt(np.maximum(trace[a] + 1.0, 1e-30)) * 2.0
    q[a, 3] = 0.25 * s
    q[a, 0] = (r[a, 2, 1] - r[a, 1, 2]) / s
    q[a, 1] = (r[a, 0, 2] - r[a, 2, 0]) / s
    q[a, 2] = (r[a, 1, 0] - r[a, 0, 1]) / s
    b = ~a & (r[:, 0, 0] > r[:, 1, 1]) & (r[:, 0, 0] > r[:, 2, 2])
    s = np.sqrt(np.maximum(1.0 + r[b, 0, 0] - r[b, 1, 1] - r[b, 2, 2], 1e-30)) * 2.0
    q[b, 3] = (r[b, 2, 1] - r[b, 1, 2]) / s
    q[b, 0] = 0.25 * s
    q[b, 1] = (r[b, 0, 1] + r[b, 1, 0]) / s
    q[b, 2] = (r[b, 0, 2] + r[b, 2, 0]) / s
    c = ~a & ~b & (r[:, 1, 1] > r[:, 2, 2])
    s = np.sqrt(np.maximum(1.0 + r[c, 1, 1] - r[c, 0, 0] - r[c, 2, 2], 1e-30)) * 2.0
    q[c, 3] = (r[c, 0, 2] - r[c, 2, 0]) / s
    q[c, 0] = (r[c, 0, 1] + r[c, 1, 0]) / s
    q[c, 1] = 0.25 * s
    q[c, 2] = (r[c, 1, 2] + r[c, 2, 1]) / s
    d = ~a & ~b & ~c
    s = np.sqrt(np.maximum(1.0 + r[d, 2, 2] - r[d, 0, 0] - r[d, 1, 1], 1e-30)) * 2.0
    q[d, 3] = (r[d, 1, 0] - r[d, 0, 1]) / s
    q[d, 0] = (r[d, 0, 2] + r[d, 2, 0]) / s
    q[d, 1] = (r[d, 1, 2] + r[d, 2, 1]) / s
    q[d, 2] = 0.25 * s
    return q / np.maximum(np.linalg.norm(q, axis=1, keepdims=True), 1e-30)


def apply_with_jacobian(xform: CompiledXForm, x: np.ndarray, y: np.ndarray, z: np.ndarray, c: np.ndarray,
                        rng: np.random.Generator, eps: float = EPSILON) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """`apply_xform` plus the local Jacobian `(N, 3, 3)` by central differences (column j = ∂T/∂x_j)."""
    seed = int(rng.integers(0, 2 ** 31 - 1))
    base = apply_xform(xform, x, y, z, c, np.random.default_rng(seed))
    jac = np.zeros((x.shape[0], 3, 3))
    for j, (dx, dy, dz) in enumerate(((eps, 0.0, 0.0), (0.0, eps, 0.0), (0.0, 0.0, eps))):
        # the same random stream on both sides, so random variations do not swamp the difference
        plus = apply_xform(xform, x + dx, y + dy, z + dz, c, np.random.default_rng(seed))
        minus = apply_xform(xform, x - dx, y - dy, z - dz, c, np.random.default_rng(seed))
        for i in range(3):
            jac[:, i, j] = (plus[i] - minus[i]) / (2.0 * eps)
    return base[0], base[1], base[2], base[3], jac


class _FramePopulation(PointPopulation):
    """A population that also carries a frame (rotation, scale) per point, reset to identity on request."""

    def __init__(self, compiled: CompiledFlame, points: int, seed: int):
        super().__init__(compiled, points, seed, (1, 0, 0, 1, 0, 0), 1, 1)
        self.rotation = np.tile(np.eye(3), (points, 1, 1))
        self.scale = np.ones(points)

    def reset_frames(self) -> None:
        self.rotation[:] = np.eye(3)
        self.scale[:] = 1.0

    def step_with_frames(self, frame_mode: str) -> np.ndarray:
        """One iteration that also composes each point's frame with the chosen transform's Jacobian."""
        xi = self._select(self.rng.random(self.x.shape[0]))
        for i, xform in enumerate(self.compiled.xforms):
            sel = np.nonzero(xi == i)[0]
            if sel.shape[0] == 0:
                continue
            x, y, z, c, jac = apply_with_jacobian(xform, self.x[sel], self.y[sel], self.z[sel], self.c[sel], self.rng)
            self.x[sel], self.y[sel], self.z[sel], self.c[sel] = x, y, z, c
            rotation, scale = polar_decompose(jac)
            if frame_mode == "jacobian":
                self.rotation[sel] = rotation @ self.rotation[sel]
            self.scale[sel] = np.clip(self.scale[sel] * scale, MIN_SCALE, MAX_SCALE)
        bad = ~(np.abs(self.x) < 1e10) | ~(np.abs(self.y) < 1e10) | ~(np.abs(self.z) < 1e10)
        if bad.any():
            k = int(bad.sum())
            self.x[bad] = self.rng.uniform(-1.0, 1.0, k)
            self.y[bad] = self.rng.uniform(-1.0, 1.0, k)
            self.z[bad] = 0.0
            self.c[bad] = self.rng.random(k)
            self.rotation[bad] = np.eye(3)
            self.scale[bad] = 1.0
        self.prev = xi
        return xi


def _with_final(compiled: CompiledFlame, x, y, z, c, rotation, rng, frame_mode: str):
    """Positions and frames after the final transform (when there is one)."""
    if compiled.final is None:
        return x, y, z, c, rotation, np.ones(x.shape[0])
    fx, fy, fz, fc, jac = apply_with_jacobian(compiled.final, x, y, z, c, rng)
    frot, fscale = polar_decompose(jac)
    if frame_mode == "jacobian":
        rotation = frot @ rotation
    return fx, fy, fz, fc, rotation, fscale


def chaos_instances(flame: Flame, count: int, depth: int = 6, seed: int = 1, frame_mode: str = "jacobian", fuse: int = 20,
                    population: int = 8192, cancelled=None) -> InstanceSet | None:
    """Orbit samples with frames: each frame is the product of the Jacobians of the last `depth` transforms
    (so the scales are those of depth-`depth` holons). Returns None when cancelled.

    Raises:
        ValueError: For a flame with no usable transform.
    """
    compiled = CompiledFlame.build(flame)
    count = max(1, int(count))
    depth = max(1, int(depth))
    pop = _FramePopulation(compiled, min(population, count), seed * 7919 + 13)
    pop.fuse(fuse)
    parts = []
    collected = 0
    while collected < count:
        if cancelled is not None and cancelled():
            return None
        pop.reset_frames()
        for _ in range(depth):
            pop.step_with_frames(frame_mode)
        x, y, z, c, rotation, fscale = _with_final(compiled, pop.x.copy(), pop.y.copy(), pop.z.copy(), pop.c.copy(),
                                                   pop.rotation.copy(), pop.rng, frame_mode)
        keep = np.isfinite(x) & np.isfinite(y) & np.isfinite(z) & (pop.opacities[pop.prev] > 0)
        parts.append(InstanceSet(np.stack([x, y, z], axis=1)[keep], rotation[keep], (pop.scale * fscale)[keep],
                                 np.clip(c[keep] * 255.0 + 0.5, 0, 255).astype(np.uint8), pop.prev[keep].astype(np.int16),
                                 np.full(int(keep.sum()), depth, dtype=np.int16)))
        collected += int(keep.sum())
    out = _concat(parts)
    return out.subset(np.arange(min(len(out), count)))


def tree_instances(flame: Flame, depth: int = 4, levels: str = "all", frame_mode: str = "jacobian", cap: int = 200_000,
                   seed: int = 1, start=(0.0, 0.0, 0.0), cancelled=None) -> InstanceSet | None:
    """Every composition of the transforms to `depth`, applied to `start` with frames composed on the way.

    `levels` = `all` keeps every node of the tree (the root excluded), `leaves` the deepest level only. The tree
    is cut once it holds more than `cap` nodes (the deepest level is then sampled). Returns None when cancelled.
    """
    compiled = CompiledFlame.build(flame)
    rng = np.random.default_rng(seed)
    active = [i for i, x in enumerate(compiled.xforms) if x.opacity > 0] or list(range(compiled.count))
    x = np.array([start[0]], dtype=np.float64)
    y = np.array([start[1]], dtype=np.float64)
    z = np.array([start[2]], dtype=np.float64)
    c = np.array([0.5])
    rotation = np.eye(3)[None]
    scale = np.ones(1)
    collected = []
    for level in range(1, max(1, int(depth)) + 1):
        if cancelled is not None and cancelled():
            return None
        nx, ny, nz, nc, nrot, nscale, nxf = [], [], [], [], [], [], []
        for i in active:
            px, py, pz, pc, jac = apply_with_jacobian(compiled.xforms[i], x, y, z, c, rng)
            rot, sc = polar_decompose(jac)
            nx.append(px)
            ny.append(py)
            nz.append(pz)
            nc.append(pc)
            nrot.append(rot @ rotation if frame_mode == "jacobian" else rotation)
            nscale.append(np.clip(scale * sc, MIN_SCALE, MAX_SCALE))
            nxf.append(np.full(px.shape[0], i, dtype=np.int16))
        x, y, z, c = np.concatenate(nx), np.concatenate(ny), np.concatenate(nz), np.concatenate(nc)
        rotation, scale, xf = np.concatenate(nrot), np.concatenate(nscale), np.concatenate(nxf)
        finite = np.isfinite(x) & np.isfinite(y) & np.isfinite(z)
        if not finite.all():
            x, y, z, c, rotation, scale, xf = x[finite], y[finite], z[finite], c[finite], rotation[finite], scale[finite], xf[finite]
        too_many = x.shape[0] > cap
        if too_many:
            pick = np.sort(rng.choice(x.shape[0], size=cap, replace=False))
            x, y, z, c, rotation, scale, xf = x[pick], y[pick], z[pick], c[pick], rotation[pick], scale[pick], xf[pick]
        if levels == "all" or level == depth or too_many:
            fx, fy, fz, fc, frot, fscale = _with_final(compiled, x, y, z, c, rotation, rng, frame_mode)
            collected.append(InstanceSet(np.stack([fx, fy, fz], axis=1), frot, scale * fscale,
                                         np.clip(fc * 255.0 + 0.5, 0, 255).astype(np.uint8), xf, np.full(x.shape[0], level, dtype=np.int16)))
        if too_many:
            break
    return _concat(collected) if collected else InstanceSet.empty()


def _concat(parts: list[InstanceSet]) -> InstanceSet:
    if not parts:
        return InstanceSet.empty()
    return InstanceSet(np.concatenate([p.positions for p in parts]), np.concatenate([p.rotations for p in parts]),
                       np.concatenate([p.scales for p in parts]), np.concatenate([p.colors for p in parts]),
                       np.concatenate([p.xform for p in parts]), np.concatenate([p.level for p in parts]))


def instances_for(flame: Flame, instancer, cancelled=None) -> InstanceSet | None:
    """The `InstanceSet` of a `scene3d.model.Instancer` (its size rules applied). None when cancelled."""
    if instancer.mode == "tree":
        raw = tree_instances(flame, instancer.depth, instancer.tree_levels, instancer.frame_mode, max(instancer.max_instances, 1) * 4,
                             instancer.seed, cancelled=cancelled)
    else:
        raw = chaos_instances(flame, instancer.count, instancer.depth, instancer.seed, instancer.frame_mode, cancelled=cancelled)
    if raw is None:
        return None
    return raw.sized(instancer.size, instancer.size_falloff, instancer.min_size, instancer.max_instances)


# --- assets ------------------------------------------------------------------------------------------------------------
def normalized_mesh(mesh: Mesh) -> Mesh:
    """The mesh centred on its bounding box with the longest side scaled to 1 (what `size` then means)."""
    lo, hi = mesh.bounds()
    longest = float((hi - lo).max()) if mesh.vertex_count else 1.0
    out = mesh.copy()
    out.vertices = (out.vertices - (lo + hi) / 2.0) / (longest if longest > 0 else 1.0)
    return out


def primitive(kind: str, detail: int = 2) -> Mesh:
    """A built-in asset mesh, unit-sized and centred: `sphere` (icosphere, `detail` subdivisions), `cube`, `torus`,
    `tetrahedron`, `icosahedron`, `cylinder`, or `dla` — a coral grown by diffusion-limited aggregation (`detail`
    sets the particle count: 800 · (detail + 1)).

    Raises:
        ValueError: For an unknown kind.
    """
    detail = max(0, int(detail))
    if kind == "sphere":
        mesh = _icosahedron()
        for _ in range(min(detail, 5)):
            mesh = _subdivide(mesh)
            mesh.vertices /= np.linalg.norm(mesh.vertices, axis=1, keepdims=True)
    elif kind == "icosahedron":
        mesh = _icosahedron()
    elif kind == "tetrahedron":
        mesh = Mesh(np.array([[1, 1, 1], [1, -1, -1], [-1, 1, -1], [-1, -1, 1]], dtype=float) / math.sqrt(3),
                    np.array([[0, 1, 2], [0, 3, 1], [0, 2, 3], [1, 3, 2]]))
    elif kind == "cube":
        mesh = _cube()
        for _ in range(min(detail, 4)):
            mesh = _subdivide(mesh)
    elif kind == "torus":
        mesh = _torus(16 * (detail + 1), 8 * (detail + 1))
    elif kind == "cylinder":
        mesh = _cylinder(12 * (detail + 1))
    elif kind == "dla":
        return dla_mesh(800 * (detail + 1), 48 + 16 * min(detail, 3), seed=detail + 1)
    else:
        raise ValueError(f"unknown primitive {kind!r} (known: {', '.join(PRIMITIVES)})")
    if mesh.signed_volume() < 0:
        mesh = mesh.flipped()
    mesh = normalized_mesh(mesh)
    mesh.compute_normals()
    return mesh


def _icosahedron() -> Mesh:
    t = (1.0 + math.sqrt(5.0)) / 2.0
    v = np.array([[-1, t, 0], [1, t, 0], [-1, -t, 0], [1, -t, 0], [0, -1, t], [0, 1, t], [0, -1, -t], [0, 1, -t],
                  [t, 0, -1], [t, 0, 1], [-t, 0, -1], [-t, 0, 1]], dtype=float)
    v /= np.linalg.norm(v, axis=1, keepdims=True)
    f = np.array([[0, 11, 5], [0, 5, 1], [0, 1, 7], [0, 7, 10], [0, 10, 11], [1, 5, 9], [5, 11, 4], [11, 10, 2], [10, 7, 6], [7, 1, 8],
                  [3, 9, 4], [3, 4, 2], [3, 2, 6], [3, 6, 8], [3, 8, 9], [4, 9, 5], [2, 4, 11], [6, 2, 10], [8, 6, 7], [9, 8, 1]])
    return Mesh(v, f)


def _cube() -> Mesh:
    v = np.array([[x, y, z] for x in (-1, 1) for y in (-1, 1) for z in (-1, 1)], dtype=float) * 0.5
    quads = [(0, 1, 3, 2), (4, 6, 7, 5), (0, 4, 5, 1), (2, 3, 7, 6), (0, 2, 6, 4), (1, 5, 7, 3)]
    faces = []
    for a, b, c, d in quads:
        faces += [[a, b, c], [a, c, d]]
    mesh = Mesh(v, np.array(faces))
    return mesh.oriented()


def _subdivide(mesh: Mesh) -> Mesh:
    """Loop-style 1 → 4 split of every face (flat), vertices welded."""
    v, f = mesh.vertices, mesh.faces
    mid = lambda a, b: (v[a] + v[b]) / 2.0  # noqa: E731
    new_v = [v]
    new_f = []
    base = v.shape[0]
    for a, b, c in f:
        i = base
        new_v.append(np.array([mid(a, b), mid(b, c), mid(c, a)]))
        new_f += [[a, i, i + 2], [b, i + 1, i], [c, i + 2, i + 1], [i, i + 1, i + 2]]
        base += 3
    return Mesh(np.concatenate(new_v), np.array(new_f)).weld(1e-9)


def _torus(segments: int, sides: int, radius: float = 1.0, tube: float = 0.35) -> Mesh:
    u = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    w = np.linspace(0, 2 * np.pi, sides, endpoint=False)
    uu, ww = np.meshgrid(u, w, indexing="ij")
    x = (radius + tube * np.cos(ww)) * np.cos(uu)
    y = (radius + tube * np.cos(ww)) * np.sin(uu)
    z = tube * np.sin(ww)
    v = np.stack([x.reshape(-1), y.reshape(-1), z.reshape(-1)], axis=1)
    faces = []
    for i in range(segments):
        for j in range(sides):
            a = i * sides + j
            b = ((i + 1) % segments) * sides + j
            c = ((i + 1) % segments) * sides + (j + 1) % sides
            d = i * sides + (j + 1) % sides
            faces += [[a, b, c], [a, c, d]]
    return Mesh(v, np.array(faces))


def _cylinder(segments: int) -> Mesh:
    a = np.linspace(0, 2 * np.pi, segments, endpoint=False)
    ring_bottom = np.stack([np.cos(a), np.sin(a), np.full(segments, -0.5)], axis=1)
    ring_top = np.stack([np.cos(a), np.sin(a), np.full(segments, 0.5)], axis=1)
    v = np.concatenate([ring_bottom, ring_top, [[0, 0, -0.5], [0, 0, 0.5]]])
    bottom_centre, top_centre = 2 * segments, 2 * segments + 1
    faces = []
    for i in range(segments):
        j = (i + 1) % segments
        faces += [[i, j, segments + j], [i, segments + j, segments + i]]
        faces += [[bottom_centre, j, i], [top_centre, segments + i, segments + j]]
    return Mesh(v, np.array(faces))


# --- instance geometry for the renderers and the exports -----------------------------------------------------------------
def instance_points(mesh: Mesh, instances: InstanceSet, budget: int, seed: int = 1
                    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """About `budget` surface points over all instances, more on the bigger ones: (positions `(S, 3)`, normals `(S, 3)`,
    the asset vertex nearest each sample `(S,)`, the instance of each sample `(S,)`)."""
    n = len(instances)
    if n == 0 or mesh.face_count == 0 or budget <= 0:
        return np.zeros((0, 3)), np.zeros((0, 3)), np.zeros(0, dtype=np.int64), np.zeros(0, dtype=np.int64)
    from .mesh_preview import sample_surface
    area = instances.scales ** 2
    share = area / max(area.sum(), 1e-30)
    counts = np.maximum(8, np.rint(share * budget).astype(np.int64))
    pool = int(counts.max())
    points, normals, nearest, _faces = sample_surface(mesh, pool, seed)
    instance_of = np.repeat(np.arange(n), counts)
    offsets = np.repeat(np.cumsum(counts) - counts, counts)
    pool_index = (np.arange(instance_of.shape[0]) - offsets) % pool
    local = points[pool_index] * instances.scales[instance_of][:, None]
    rot = instances.rotations[instance_of]
    world = np.einsum("sij,sj->si", rot, local) + instances.positions[instance_of]
    world_normals = np.einsum("sij,sj->si", rot, normals[pool_index])
    return world, world_normals, nearest[pool_index], instance_of


def bake_instances(mesh: Mesh, instances: InstanceSet, max_faces: int = 5_000_000) -> Mesh:
    """One mesh of every instance transformed and concatenated (the largest instances first when `max_faces` cuts)."""
    n = len(instances)
    if n == 0 or mesh.face_count == 0:
        return Mesh.empty()
    limit = max(1, max_faces // mesh.face_count)
    if n > limit:
        keep = np.argsort(-instances.scales, kind="stable")[:limit]
        instances = instances.subset(np.sort(keep))
        n = limit
    v, f = mesh.vertices, mesh.faces
    local = v[None, :, :] * instances.scales[:, None, None]                       # (N, V, 3)
    world = np.einsum("nij,nvj->nvi", instances.rotations, local) + instances.positions[:, None, :]
    vertices = world.reshape(-1, 3)
    offsets = (np.arange(n) * v.shape[0])[:, None, None]
    faces = (f[None, :, :] + offsets).reshape(-1, 3)
    out = Mesh(vertices, faces)
    if mesh.colors is not None:
        out.colors = np.tile(mesh.colors, (n, 1))
    if mesh.normals is not None:
        out.normals = np.einsum("nij,nvj->nvi", instances.rotations, np.broadcast_to(mesh.normals, (n, *mesh.normals.shape))).reshape(-1, 3)
    else:
        out.compute_normals()
    return out


def instance_colors(instances: InstanceSet, color_mode: str, asset: Mesh, nearest_vertex: np.ndarray, instance_of: np.ndarray,
                    palette: np.ndarray) -> np.ndarray:
    """Palette indices per sample for `instance_points`: the orbit's colour, the asset's vertex colours (nearest palette
    entry) or a fixed colour (index 0 — the material's fixed colour takes over in the shader)."""
    if color_mode == "asset" and asset.colors is not None:
        vertex_index = nearest_palette_index(asset.colors, np.asarray(palette, dtype=np.uint8))
        return vertex_index[nearest_vertex].astype(np.int16)
    if color_mode == "fixed":
        return np.zeros(instance_of.shape[0], dtype=np.int16)
    return instances.colors[instance_of].astype(np.int16)


# --- a 3D affine transform as a flame transform (the Instances tab's own IFS) ------------------------------------------------
def _rotation_matrix(rx: float, ry: float, rz: float) -> np.ndarray:
    """R = Ry · Rx · Rz for angles in degrees (the order the flame transform applies them: z in the affine, then the
    post rotations x then y)."""
    ax, ay, az = math.radians(rx), math.radians(ry), math.radians(rz)
    rzm = np.array([[math.cos(az), -math.sin(az), 0], [math.sin(az), math.cos(az), 0], [0, 0, 1]])
    rxm = np.array([[1, 0, 0], [0, math.cos(ax), -math.sin(ax)], [0, math.sin(ax), math.cos(ax)]])
    rym = np.array([[math.cos(ay), 0, math.sin(ay)], [0, 1, 0], [-math.sin(ay), 0, math.cos(ay)]])
    return rym @ rxm @ rzm


def affine3d_xform(position=(0.0, 0.0, 0.0), rotation=(0.0, 0.0, 0.0), scale: float = 0.5, weight: float = 1.0, color: float = 0.5,
                   name: str = "") -> XForm:
    """A flame transform computing `p' = R · s · p + t` in 3D: the xy part in the affine, `zscale` for the z scale,
    `ztranslate` for the z offset (pre-rotation, compensated) and `post_rotate_x` / `post_rotate_y` for the tilts."""
    rx, ry, rz = rotation
    s = scale if abs(scale) > 1e-9 else 1e-9
    post = _rotation_matrix(rx, ry, 0.0)                          # the part applied after the affine and ztranslate
    t_pre = post.T @ np.asarray(position, dtype=np.float64)     # so that post · t_pre = position
    az = math.radians(rz)
    a, d = s * math.cos(az), s * math.cos(az)
    b, c = s * math.sin(az), -s * math.sin(az)
    variations = {"linear3D": 1.0}
    if abs(s - 1.0) > 1e-12:
        variations["zscale"] = s - 1.0
    if abs(t_pre[2]) > 1e-12:
        variations["ztranslate"] = float(t_pre[2])
    if abs(rx) > 1e-9:
        variations["post_rotate_x"] = -rx / 90.0                  # the post rotations turn by −(weight · 90°)
    if abs(ry) > 1e-9:
        variations["post_rotate_y"] = -ry / 90.0
    return XForm(weight=weight, color=color, coefs=(a, b, c, d, float(t_pre[0]), float(t_pre[1])), variations=variations, name=name)


def read_affine3d(xform: XForm) -> dict | None:
    """The (position, rotation, scale) of a transform `affine3d_xform` built — None when the transform is not of that shape."""
    allowed = {"linear3D", "linear", "zscale", "ztranslate", "post_rotate_x", "post_rotate_y"}
    if set(xform.variations) - allowed or abs(xform.variations.get("linear3D", xform.variations.get("linear", 0.0)) - 1.0) > 1e-9:
        return None
    if xform.has_post() or xform.has_pre():
        return None
    a, b, c, d, e, f = xform.coefs
    if abs(a - d) > 1e-7 or abs(b + c) > 1e-7:
        return None
    s = math.hypot(a, b)
    if abs((1.0 + xform.variations.get("zscale", 0.0)) - s) > 1e-6:
        return None
    rz = math.degrees(math.atan2(b, a))
    rx = -xform.variations.get("post_rotate_x", 0.0) * 90.0
    ry = -xform.variations.get("post_rotate_y", 0.0) * 90.0
    post = _rotation_matrix(rx, ry, 0.0)
    position = post @ np.array([e, f, xform.variations.get("ztranslate", 0.0)])
    return {"position": tuple(float(v) for v in position), "rotation": (rx, ry, rz), "scale": s, "weight": xform.weight, "color": xform.color}


def default_own_ifs() -> Flame:
    """A starter 3D IFS: four shrinking copies at the corners of a tetrahedron, turned a little."""
    corners = [((0.0, 0.0, 0.55), (0, 0, 0)), ((0.5, 0.0, -0.3), (0, 0, 120)), ((-0.25, 0.43, -0.3), (0, 0, 240)), ((-0.25, -0.43, -0.3), (0, 0, 0))]
    xforms = [affine3d_xform(position, rotation, 0.5, 1.0, i / 3, f"holon {i + 1}") for i, (position, rotation) in enumerate(corners)]
    flame = Flame("holon IFS", xforms)
    flame.camera.scale = 120
    flame.camera.pitch, flame.camera.yaw, flame.camera.perspective = 0.9, 0.4, 0.25
    return flame




# --- the scene's instances as a point cloud for the renderers -----------------------------------------------------------
@dataclass
class InstanceCloud:
    """Surface points of every visible instancer, ready to splat.

    Attributes:
        xyz: `(S, 3)` world positions.
        normals: `(S, 3)` world normals.
        color: `(S,)` int16 palette index.
        material: `(S,)` int16 render material index (`Scene3D.instancer_material_index`).
        count: Instances over all instancers.
    """
    xyz: np.ndarray
    normals: np.ndarray
    color: np.ndarray
    material: np.ndarray
    count: int


_instance_cache: dict[str, InstanceSet] = {}
_CACHE_LIMIT = 16


def _instancer_key(flame: Flame, instancer) -> str:
    import hashlib
    import json
    fields = (instancer.mode, instancer.count, instancer.depth, instancer.tree_levels, instancer.frame_mode, instancer.seed)
    payload = json.dumps([flame.to_dict(), fields], sort_keys=True, default=str)
    return hashlib.sha1(payload.encode("utf-8")).hexdigest()


def cached_instances(flame: Flame, instancer) -> InstanceSet:
    """`instances_for` with the raw (unsized) set cached by content: the viewport re-renders far more often than the
    instancer changes."""
    key = _instancer_key(flame, instancer)
    raw = _instance_cache.get(key)
    if raw is None:
        if instancer.mode == "tree":
            raw = tree_instances(flame, instancer.depth, instancer.tree_levels, instancer.frame_mode, max(instancer.max_instances, 1) * 4,
                                 instancer.seed)
        else:
            raw = chaos_instances(flame, instancer.count, instancer.depth, instancer.seed, instancer.frame_mode)
        if len(_instance_cache) >= _CACHE_LIMIT:
            _instance_cache.pop(next(iter(_instance_cache)))
        _instance_cache[key] = raw
    return raw.sized(instancer.size, instancer.size_falloff, instancer.min_size, instancer.max_instances)


def instancer_flame(scene, instancer) -> Flame | None:
    """The fractal an instancer follows: its own, or the scene's."""
    if instancer.source == "own":
        return instancer.flame
    return scene.fractal


def scene_instance_sets(scene) -> list[tuple[int, "object", InstanceSet, Mesh]]:
    """(instancer index, instancer, its instances, the asset mesh normalised as the instancer wants) for every visible instancer."""
    out = []
    for index, inst in enumerate(scene.instancers):
        asset = scene.asset_named(inst.asset)
        flame = instancer_flame(scene, inst)
        if not inst.visible or asset is None or asset.mesh is None or flame is None or not flame.renderable():
            continue
        mesh = normalized_mesh(asset.mesh) if asset.normalize else asset.mesh
        try:
            instances = cached_instances(flame, inst)
        except ValueError:
            continue
        if len(instances):
            out.append((index, inst, instances, mesh))
    return out


def scene_instance_cloud(scene, budget: int = 1_500_000, transform_count: int | None = None, seed: int = 1) -> InstanceCloud | None:
    """The point cloud of all visible instancers (None when there are none), `budget` samples shared by projected area."""
    sets = scene_instance_sets(scene)
    if not sets:
        return None
    palette = np.asarray(scene.fractal.palette, dtype=np.uint8) if scene.fractal is not None else None
    areas = np.array([float((s.scales ** 2).sum()) for _i, _inst, s, _m in sets])
    shares = areas / max(areas.sum(), 1e-30)
    parts = []
    total = 0
    for (index, inst, instances, mesh), share in zip(sets, shares):
        points, normals, nearest, instance_of = instance_points(mesh, instances, max(1000, int(budget * share)), seed)
        if points.shape[0] == 0:
            continue
        own_palette = palette if palette is not None else (np.asarray(inst.flame.palette, dtype=np.uint8) if inst.flame is not None else None)
        if own_palette is None:
            from .mesh_preview import fallback_palette
            own_palette = fallback_palette()
        color = instance_colors(instances, inst.color_mode, mesh, nearest, instance_of, own_palette)
        material = np.full(points.shape[0], scene.instancer_material_index(index, transform_count), dtype=np.int16)
        parts.append((points, normals, color, material))
        total += len(instances)
    if not parts:
        return None
    return InstanceCloud(np.concatenate([p[0] for p in parts]), np.concatenate([p[1] for p in parts]),
                         np.concatenate([p[2] for p in parts]), np.concatenate([p[3] for p in parts]), total)




# --- grown assets: diffusion-limited aggregation ----------------------------------------------------------------------------
def dla_grid(particles: int = 2000, size: int = 64, seed: int = 1, stickiness: float = 1.0, walkers: int = 256) -> np.ndarray:
    """Diffusion-limited aggregation on a cubic lattice: `(size, size, size)` bool occupancy of a coral-like cluster.

    `walkers` random-walk at once (vectorised): each starts on a sphere just outside the cluster, sticks when it
    touches it (with probability `stickiness`; lower values give denser, rounder growth) and is relaunched when it
    wanders far away or leaves the grid.
    """
    rng = np.random.default_rng(seed)
    grid = np.zeros((size, size, size), dtype=bool)
    centre = size // 2
    grid[centre, centre, centre] = True
    radius = 1.0
    steps = np.array([[1, 0, 0], [-1, 0, 0], [0, 1, 0], [0, -1, 0], [0, 0, 1], [0, 0, -1]])
    limit = centre - 2
    placed = 0

    def launch(count: int) -> np.ndarray:
        d = rng.normal(size=(count, 3))
        d /= np.maximum(np.linalg.norm(d, axis=1, keepdims=True), 1e-9)
        return np.rint(centre + d * min(radius + 4.0, limit - 1.0)).astype(np.int64)

    positions = launch(walkers)
    for _round in range(200_000):
        if placed >= particles:
            break
        positions = positions + steps[rng.integers(0, 6, size=positions.shape[0])]
        off = positions - centre
        kill = min(radius * 2.0 + 6.0, float(limit))
        lost = (np.einsum("ij,ij->i", off, off) > kill * kill) | (np.abs(off) >= limit).any(axis=1)
        if lost.any():
            positions[lost] = launch(int(lost.sum()))
        x, y, z = positions[:, 0], positions[:, 1], positions[:, 2]
        touching = (grid[x + 1, y, z] | grid[x - 1, y, z] | grid[x, y + 1, z] | grid[x, y - 1, z] | grid[x, y, z + 1] | grid[x, y, z - 1])
        if stickiness < 1.0:
            touching &= rng.random(positions.shape[0]) < stickiness
        touching &= ~grid[x, y, z]
        if touching.any():
            stuck = positions[touching]
            grid[stuck[:, 0], stuck[:, 1], stuck[:, 2]] = True
            placed += int(touching.sum())
            radius = max(radius, float(np.sqrt(np.einsum("ij,ij->i", stuck - centre, stuck - centre).max())))
            positions[touching] = launch(int(touching.sum()))
    return grid


def dla_mesh(particles: int = 2000, size: int = 64, seed: int = 1, stickiness: float = 1.0, thickness: float = 0.9) -> Mesh:
    """A DLA cluster as a mesh (the occupancy blurred by `thickness` voxels and surfaced), unit-sized and centred."""
    from scipy import ndimage
    from .isosurface import surface_nets
    from .voxelize import VoxelGrid
    occupancy = dla_grid(particles, size, seed, stickiness)
    field = ndimage.gaussian_filter(occupancy.astype(np.float32), thickness, mode="constant")
    grid = VoxelGrid(field, None, np.zeros(3), 1.0 / size)
    mesh = surface_nets(grid, 0.2 if thickness > 0 else 0.5, field, with_color=False)
    if mesh.face_count == 0:
        return primitive("sphere", 1)
    mesh = mesh.keep_components(largest=1)[0]
    mesh = normalized_mesh(mesh)
    mesh.compute_normals()
    return mesh


__all__ = ["InstanceSet", "InstanceCloud", "cached_instances", "scene_instance_sets", "scene_instance_cloud", "instancer_flame",
           "polar_decompose", "rotation_to_quaternion", "apply_with_jacobian", "chaos_instances", "tree_instances",
           "instances_for", "primitive", "normalized_mesh", "instance_points", "bake_instances", "instance_colors", "affine3d_xform",
           "read_affine3d", "default_own_ifs", "PRIMITIVES", "dla_grid", "dla_mesh"]
