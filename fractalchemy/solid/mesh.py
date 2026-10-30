"""A triangle mesh and the operations the clean-up pipeline is made of. numpy + scipy.sparse, no Qt.

`Mesh` holds vertices, faces and optional per-vertex normals, colours and UVs. Everything is vectorised:
welding is a quantise-and-unique, components come from `scipy.sparse.csgraph`, orientation propagates over
the edge graph level by level, hole filling works on boundary loops (few and short in practice), Taubin
smoothing is a sparse Laplacian, decimation is quadric edge collapse through `fast_simplification` when that
is installed and **vertex clustering** otherwise. `report()` is the print-readiness check: watertight,
manifold, consistently oriented, component count, volume, bounding box, thin-wall estimate.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage, sparse
from scipy.sparse import csgraph


@dataclass
class MeshReport:
    """What the print-readiness check found.

    Attributes:
        vertices, faces: Counts.
        components: Connected pieces.
        boundary_edges: Edges with one face (holes, open surfaces).
        nonmanifold_edges: Edges with more than two faces.
        consistent: Every shared edge is traversed in opposite directions by its two faces.
        watertight: No boundary and no non-manifold edges.
        volume: Enclosed volume (world units³; meaningful when watertight and consistent).
        area: Surface area.
        bounds: `((min x, y, z), (max x, y, z))`.
        thin_wall: Estimated thinnest wall, a lower bound (world units; None when not estimated).
        degenerate_faces: Zero-area faces found (removed by `clean`).
        self_intersections: Intersecting triangle pairs found among `pairs_checked` nearby pairs (a sample; None = not checked).
        pairs_checked: How many triangle pairs the self-intersection check looked at.
        notes: Remarks (what was repaired, what could not be).
    """
    vertices: int = 0
    faces: int = 0
    components: int = 0
    boundary_edges: int = 0
    nonmanifold_edges: int = 0
    consistent: bool = True
    watertight: bool = False
    volume: float = 0.0
    area: float = 0.0
    bounds: tuple[tuple[float, float, float], tuple[float, float, float]] = ((0.0, 0.0, 0.0), (0.0, 0.0, 0.0))
    thin_wall: float | None = None
    degenerate_faces: int = 0
    self_intersections: int | None = None
    pairs_checked: int = 0
    notes: list[str] = field(default_factory=list)

    @property
    def size(self) -> tuple[float, float, float]:
        lo, hi = self.bounds
        return tuple(h - l for l, h in zip(lo, hi))

    @property
    def printable(self) -> bool:
        """Watertight, manifold, consistently oriented, one piece."""
        return self.watertight and self.consistent and self.components == 1 and self.faces > 0 and not self.self_intersections

    def recommendation(self) -> str:
        """What to do next, in a sentence."""
        if self.faces == 0:
            return "The mesh is empty: lower the threshold or raise the resolution."
        problems = []
        if self.boundary_edges:
            problems.append(f"{self.boundary_edges} open edges")
        if self.nonmanifold_edges:
            problems.append(f"{self.nonmanifold_edges} non-manifold edges")
        if not self.consistent:
            problems.append("inconsistent face orientation")
        if self.components > 1:
            problems.append(f"{self.components} separate pieces")
        if self.self_intersections:
            problems.append(f"{self.self_intersections} self-intersecting triangle pairs (in a sample of {self.pairs_checked:,})")
        if not problems:
            return "Ready to print: watertight, manifold and in one piece."
        return "Needs repair (" + ", ".join(problems) + "): try the simple clean-up, then the aggressive one, then a remesh."

    def to_dict(self) -> dict:
        return {"vertices": self.vertices, "faces": self.faces, "components": self.components, "boundary_edges": self.boundary_edges,
                "nonmanifold_edges": self.nonmanifold_edges, "consistent": self.consistent, "watertight": self.watertight,
                "volume": self.volume, "area": self.area, "bounds": [list(self.bounds[0]), list(self.bounds[1])],
                "thin_wall": self.thin_wall, "degenerate_faces": self.degenerate_faces, "self_intersections": self.self_intersections,
                "pairs_checked": self.pairs_checked, "notes": list(self.notes)}


@dataclass
class Mesh:
    """Vertices `(N, 3)` float64, faces `(M, 3)` int64 (counter-clockwise = outward), optional per-vertex attributes.

    Attributes:
        normals: `(N, 3)` unit normals or None.
        colors: `(N, 3)` float32 in 0..1 or None.
        uvs: `(N, 2)` float32 or None.
    """
    vertices: np.ndarray
    faces: np.ndarray
    normals: np.ndarray | None = None
    colors: np.ndarray | None = None
    uvs: np.ndarray | None = None

    def __post_init__(self) -> None:
        self.vertices = np.asarray(self.vertices, dtype=np.float64).reshape(-1, 3)
        self.faces = np.asarray(self.faces, dtype=np.int64).reshape(-1, 3)
        if self.normals is not None:
            self.normals = np.asarray(self.normals, dtype=np.float64).reshape(-1, 3)
        if self.colors is not None:
            self.colors = np.asarray(self.colors, dtype=np.float32).reshape(-1, 3)
        if self.uvs is not None:
            self.uvs = np.asarray(self.uvs, dtype=np.float32).reshape(-1, 2)

    @classmethod
    def empty(cls) -> "Mesh":
        return cls(np.zeros((0, 3)), np.zeros((0, 3), dtype=np.int64))

    # --- basics ---------------------------------------------------------------------------------------------------
    @property
    def vertex_count(self) -> int:
        return int(self.vertices.shape[0])

    @property
    def face_count(self) -> int:
        return int(self.faces.shape[0])

    def copy(self) -> "Mesh":
        return Mesh(self.vertices.copy(), self.faces.copy(), None if self.normals is None else self.normals.copy(),
                    None if self.colors is None else self.colors.copy(), None if self.uvs is None else self.uvs.copy())

    def bounds(self) -> tuple[np.ndarray, np.ndarray]:
        if self.vertex_count == 0:
            return np.zeros(3), np.zeros(3)
        return self.vertices.min(axis=0), self.vertices.max(axis=0)

    def extent(self) -> np.ndarray:
        lo, hi = self.bounds()
        return hi - lo

    def face_normals(self, normalize: bool = True) -> np.ndarray:
        """`(M, 3)` face normals (area-weighted when `normalize` is False)."""
        v = self.vertices
        f = self.faces
        n = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]]) * 0.5
        if normalize:
            length = np.linalg.norm(n, axis=1, keepdims=True)
            n = np.where(length > 1e-300, n / np.maximum(length, 1e-300), 0.0)
        return n

    def face_areas(self) -> np.ndarray:
        return np.linalg.norm(self.face_normals(normalize=False), axis=1)

    def area(self) -> float:
        return float(self.face_areas().sum())

    def signed_volume(self) -> float:
        """The enclosed volume, positive for outward (counter-clockwise) winding."""
        v = self.vertices
        f = self.faces
        if f.shape[0] == 0:
            return 0.0
        a, b, c = v[f[:, 0]], v[f[:, 1]], v[f[:, 2]]
        return float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)

    def compute_normals(self) -> np.ndarray:
        """Area-weighted per-vertex normals (stored and returned)."""
        weighted = self.face_normals(normalize=False)
        normals = np.zeros_like(self.vertices)
        for corner in range(3):
            np.add.at(normals, self.faces[:, corner], weighted)
        length = np.linalg.norm(normals, axis=1, keepdims=True)
        self.normals = np.where(length > 1e-300, normals / np.maximum(length, 1e-300), 0.0)
        return self.normals

    def flipped(self) -> "Mesh":
        """Every face wound the other way (normals negated)."""
        out = self.copy()
        out.faces = out.faces[:, ::-1].copy()
        if out.normals is not None:
            out.normals = -out.normals
        return out

    def transformed(self, scale: float = 1.0, offset=(0.0, 0.0, 0.0)) -> "Mesh":
        out = self.copy()
        out.vertices = out.vertices * scale + np.asarray(offset, dtype=np.float64)
        return out

    def scaled_to(self, size: float) -> "Mesh":
        """Uniformly scaled so the longest side of the bounding box is `size`, centred on the origin."""
        lo, hi = self.bounds()
        longest = float((hi - lo).max())
        factor = size / longest if longest > 0 else 1.0
        centre = (lo + hi) / 2.0
        out = self.copy()
        out.vertices = (out.vertices - centre) * factor
        return out

    # --- topology -------------------------------------------------------------------------------------------------
    def edges(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """(unique undirected edges `(E, 2)` sorted, per-edge face count, the edge id of every face corner `(M, 3)`)."""
        f = self.faces
        directed = np.stack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1).reshape(-1, 2)    # (3M, 2) in face order
        undirected = np.sort(directed, axis=1)
        unique, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
        return unique, counts, inverse.reshape(-1, 3)

    def boundary_edges(self) -> np.ndarray:
        """`(B, 2)` directed boundary edges (as the faces traverse them)."""
        f = self.faces
        directed = np.stack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1).reshape(-1, 2)
        undirected = np.sort(directed, axis=1)
        _unique, inverse, counts = np.unique(undirected, axis=0, return_inverse=True, return_counts=True)
        return directed[counts[inverse.reshape(-1)] == 1]

    def is_consistently_oriented(self) -> bool:
        """True when every edge shared by two faces is traversed once in each direction."""
        f = self.faces
        if f.shape[0] == 0:
            return True
        directed = np.stack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1).reshape(-1, 2)
        _unique, counts = np.unique(directed, axis=0, return_counts=True)
        return bool((counts == 1).all())

    def components(self) -> tuple[int, np.ndarray]:
        """(number of connected pieces, the piece of every face)."""
        if self.face_count == 0:
            return 0, np.zeros(0, dtype=np.int64)
        f = self.faces
        n = self.vertex_count
        rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2]])
        cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0]])
        graph = sparse.coo_matrix((np.ones(rows.shape[0], dtype=np.int8), (rows, cols)), shape=(n, n))
        count, labels = csgraph.connected_components(graph, directed=False)
        face_labels = labels[f[:, 0]]
        _unique, face_labels = np.unique(face_labels, return_inverse=True)
        return int(face_labels.max() + 1) if face_labels.size else 0, face_labels

    # --- the clean-up operations ----------------------------------------------------------------------------------
    def subset(self, keep_faces: np.ndarray) -> "Mesh":
        """The mesh of the faces where `keep_faces` (bool or indices) is set, unreferenced vertices dropped."""
        faces = self.faces[keep_faces]
        used, inverse = np.unique(faces.reshape(-1), return_inverse=True)
        out = Mesh(self.vertices[used], inverse.reshape(-1, 3), None if self.normals is None else self.normals[used],
                   None if self.colors is None else self.colors[used], None if self.uvs is None else self.uvs[used])
        return out

    def remove_unreferenced(self) -> "Mesh":
        return self.subset(np.ones(self.face_count, dtype=bool))

    def remove_degenerate(self) -> tuple["Mesh", int]:
        """Drop faces with a repeated vertex or zero area, and exact duplicate faces. Returns (mesh, dropped)."""
        f = self.faces
        if f.shape[0] == 0:
            return self, 0
        distinct = (f[:, 0] != f[:, 1]) & (f[:, 1] != f[:, 2]) & (f[:, 0] != f[:, 2])
        areas = self.face_areas()
        scale = float(self.extent().max()) if self.vertex_count else 1.0
        keep = distinct & (areas > 1e-14 * max(scale, 1e-12) ** 2)
        sorted_faces = np.sort(f, axis=1)
        _unique, first = np.unique(sorted_faces, axis=0, return_index=True)
        duplicate = np.ones(f.shape[0], dtype=bool)
        duplicate[first] = False
        keep &= ~duplicate
        dropped = int((~keep).sum())
        return (self.subset(keep) if dropped else self), dropped

    def weld(self, tolerance: float | None = None) -> "Mesh":
        """Merge vertices closer than `tolerance` (default: 1e-6 of the extent); attributes averaged."""
        if self.vertex_count == 0:
            return self
        tol = tolerance if tolerance is not None else 1e-6 * max(float(self.extent().max()), 1e-12)
        keys = np.round(self.vertices / tol).astype(np.int64)
        _unique, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
        inverse = inverse.reshape(-1)
        n = first.shape[0]
        counts = np.bincount(inverse, minlength=n).astype(np.float64)[:, None]
        vertices = np.zeros((n, 3))
        np.add.at(vertices, inverse, self.vertices)
        vertices /= counts
        colors = None
        if self.colors is not None:
            colors = np.zeros((n, 3))
            np.add.at(colors, inverse, self.colors)
            colors = (colors / counts).astype(np.float32)
        uvs = None if self.uvs is None else self.uvs[first]
        out = Mesh(vertices, inverse[self.faces], None, colors, uvs)
        out, _dropped = out.remove_degenerate()
        if self.normals is not None:
            out.compute_normals()
        return out

    def keep_components(self, min_faces: int = 0, largest: int = 0) -> tuple["Mesh", int]:
        """Keep the pieces with at least `min_faces` faces (and / or only the `largest` N); returns (mesh, pieces dropped)."""
        count, labels = self.components()
        if count <= 1:
            return self, 0
        sizes = np.bincount(labels, minlength=count)
        keep_label = sizes >= max(0, min_faces)
        if largest > 0:
            order = np.argsort(-sizes)
            allowed = np.zeros(count, dtype=bool)
            allowed[order[:largest]] = True
            keep_label &= allowed
        if keep_label.all():
            return self, 0
        return self.subset(keep_label[labels]), int((~keep_label).sum())

    def oriented(self) -> "Mesh":
        """Faces wound consistently across every edge (propagated over the edge graph), each piece outward."""
        if self.face_count == 0:
            return self
        if self.is_consistently_oriented():
            return self._outward()
        faces = self.faces.copy()
        m = faces.shape[0]
        _unique, counts, edge_of_corner = self.edges()
        # the (up to two) faces on each manifold edge
        face_ids = np.repeat(np.arange(m), 3)
        edge_ids = edge_of_corner.reshape(-1)
        order = np.argsort(edge_ids, kind="stable")
        edge_sorted, face_sorted = edge_ids[order], face_ids[order]
        starts = np.searchsorted(edge_sorted, np.arange(counts.shape[0]))
        two = counts == 2
        fa = np.full(counts.shape[0], -1, dtype=np.int64)
        fb = np.full(counts.shape[0], -1, dtype=np.int64)
        fa[two] = face_sorted[starts[two]]
        fb[two] = face_sorted[starts[two] + 1]
        pair_a, pair_b = fa[two], fb[two]
        neighbours = sparse.coo_matrix((np.ones(pair_a.shape[0] * 2, dtype=np.int8),
                                        (np.concatenate([pair_a, pair_b]), np.concatenate([pair_b, pair_a]))), shape=(m, m)).tocsr()
        visited = np.zeros(m, dtype=bool)
        flipped = np.zeros(m, dtype=bool)
        remaining = np.arange(m)
        while remaining.size:
            seed = remaining[0]
            visited[seed] = True
            frontier = np.array([seed])
            while frontier.size:
                next_faces = []
                for f in frontier:
                    start, stop = neighbours.indptr[f], neighbours.indptr[f + 1]
                    nbrs = neighbours.indices[start:stop]
                    nbrs = nbrs[~visited[nbrs]]
                    if nbrs.size == 0:
                        continue
                    # a neighbour agrees when the shared edge runs the opposite way in it
                    fv = faces[f]
                    for g in nbrs:
                        gv = faces[g]
                        shared = np.intersect1d(fv, gv)
                        if shared.size != 2:
                            visited[g] = True
                            continue
                        a, b = shared
                        dir_f = _edge_direction(fv, a, b)
                        dir_g = _edge_direction(gv, a, b)
                        if dir_f == dir_g:
                            faces[g] = gv[::-1]
                            flipped[g] = True
                        visited[g] = True
                        next_faces.append(g)
                frontier = np.array(next_faces, dtype=np.int64)
            remaining = remaining[~visited[remaining]]
        return Mesh(self.vertices, faces, None, self.colors, self.uvs)._outward()

    def _outward(self) -> "Mesh":
        """Each piece wound outward: pieces with a negative volume are flipped."""
        out = Mesh(self.vertices, self.faces.copy(), None, self.colors, self.uvs)
        count, labels = out.components()
        if count:
            v = out.vertices
            f = out.faces
            contrib = np.einsum("ij,ij->i", v[f[:, 0]], np.cross(v[f[:, 1]], v[f[:, 2]])) / 6.0
            volumes = np.bincount(labels, weights=contrib, minlength=count)
            negative = volumes[labels] < 0
            if negative.any():
                out.faces[negative] = out.faces[negative][:, ::-1]
        out.compute_normals()
        return out

    def boundary_loops(self) -> list[np.ndarray]:
        """The boundary as closed vertex loops (directed as the faces traverse them)."""
        edges = self.boundary_edges()
        if edges.shape[0] == 0:
            return []
        outgoing: dict[int, list[int]] = {}
        for a, b in edges.tolist():
            outgoing.setdefault(a, []).append(b)      # a vertex where two holes touch has two outgoing edges
        loops = []
        for start, targets in list(outgoing.items()):
            while targets:
                loop = [start]
                position = {start: 0}
                cur = targets.pop()
                steps = 0
                while cur != start and steps <= edges.shape[0]:
                    if cur in position:                     # a figure-of-eight: split the inner loop off
                        i = position[cur]
                        inner = loop[i:]
                        if len(inner) >= 3:
                            loops.append(np.array(inner, dtype=np.int64))
                        for v in inner:
                            del position[v]
                        del loop[i:]
                    position[cur] = len(loop)
                    loop.append(cur)
                    nxt = outgoing.get(cur)
                    if not nxt:
                        break
                    cur = nxt.pop()
                    steps += 1
                if cur == start and len(loop) >= 3:
                    loops.append(np.array(loop, dtype=np.int64))
        return loops

    def fill_holes(self, max_edges: int = 64) -> tuple["Mesh", int]:
        """Close boundary loops of at most `max_edges` edges with a fan from their centroid. Returns (mesh, holes filled)."""
        loops = [loop for loop in self.boundary_loops() if loop.shape[0] <= max_edges]
        if not loops:
            return self, 0
        vertices = [self.vertices]
        colors = [self.colors] if self.colors is not None else None
        uvs = [self.uvs] if self.uvs is not None else None
        new_faces = []
        next_index = self.vertex_count
        for loop in loops:
            centre = self.vertices[loop].mean(axis=0)
            vertices.append(centre[None, :])
            if colors is not None:
                colors.append(self.colors[loop].mean(axis=0, keepdims=True))
            if uvs is not None:
                uvs.append(self.uvs[loop].mean(axis=0, keepdims=True))
            a = loop
            b = np.roll(loop, -1)
            # the boundary runs a→b as the existing faces traverse it; the new face must traverse it b→a
            new_faces.append(np.stack([b, a, np.full(a.shape[0], next_index)], axis=1))
            next_index += 1
        out = Mesh(np.concatenate(vertices), np.concatenate([self.faces, *new_faces]), None,
                   None if colors is None else np.concatenate(colors), None if uvs is None else np.concatenate(uvs))
        out.compute_normals()
        return out, len(loops)

    def taubin_smoothed(self, iterations: int = 10, lam: float = 0.5, mu: float = -0.53) -> "Mesh":
        """Taubin (shrink-free) smoothing: alternate Laplacian steps of `lam` and `mu`."""
        if iterations <= 0 or self.vertex_count == 0 or self.face_count == 0:
            return self
        n = self.vertex_count
        f = self.faces
        rows = np.concatenate([f[:, 0], f[:, 1], f[:, 2], f[:, 1], f[:, 2], f[:, 0]])
        cols = np.concatenate([f[:, 1], f[:, 2], f[:, 0], f[:, 0], f[:, 1], f[:, 2]])
        adjacency = sparse.coo_matrix((np.ones(rows.shape[0]), (rows, cols)), shape=(n, n)).tocsr()
        adjacency.data[:] = 1.0
        degree = np.asarray(adjacency.sum(axis=1)).reshape(-1)
        inv = np.where(degree > 0, 1.0 / np.maximum(degree, 1), 0.0)
        weights = sparse.diags(inv) @ adjacency
        v = self.vertices.copy()
        for _ in range(int(iterations)):
            v = v + lam * (weights @ v - v)
            v = v + mu * (weights @ v - v)
        out = Mesh(v, self.faces, None, self.colors, self.uvs)
        out.compute_normals()
        return out

    def decimated(self, target_faces: int, progress=None) -> "Mesh":
        """About `target_faces` faces by quadric edge collapse: `fast_simplification` when installed, else the built-in
        batched collapser (`quadric_decimate`, which reports `progress(fraction, faces left)` per round)."""
        if target_faces <= 0 or self.face_count <= target_faces:
            return self
        try:
            import fast_simplification  # type: ignore
        except ImportError:
            fast_simplification = None
        if fast_simplification is not None:
            reduction = 1.0 - target_faces / self.face_count
            points, faces = fast_simplification.simplify(self.vertices, self.faces, target_reduction=reduction)
            out = Mesh(points, faces)
            if self.colors is not None:
                out.colors = _nearest_attribute(self.vertices, self.colors, out.vertices)
            out.compute_normals()
            return out
        return quadric_decimate(self, target_faces, progress=progress)

    def clustered(self, target_faces: int) -> "Mesh":
        """Vertex-clustering decimation: vertices in the same cell of a grid merge; the grid is sized to hit the target."""
        if self.face_count <= target_faces or self.vertex_count == 0:
            return self
        lo, hi = self.bounds()
        extent = float((hi - lo).max())
        if extent <= 0:
            return self
        # faces scale roughly with the square of the cells along a side; refine by bisection on the cell count
        best = None
        low, high = 2.0, 2048.0
        for _ in range(18):
            cells = (low * high) ** 0.5
            out = self._cluster(cells)
            if best is None or abs(out.face_count - target_faces) < abs(best.face_count - target_faces):
                best = out
            if out.face_count > target_faces * 1.05:
                high = cells
            elif out.face_count < target_faces * 0.95:
                low = cells
            else:
                break
            if high - low < 1.0:
                break
        return best if best is not None else self

    def _cluster(self, cells: float) -> "Mesh":
        lo, hi = self.bounds()
        size = float((hi - lo).max()) / cells
        keys = np.floor((self.vertices - lo) / size).astype(np.int64)
        _unique, first, inverse = np.unique(keys, axis=0, return_index=True, return_inverse=True)
        inverse = inverse.reshape(-1)
        n = first.shape[0]
        counts = np.bincount(inverse, minlength=n).astype(np.float64)[:, None]
        vertices = np.zeros((n, 3))
        np.add.at(vertices, inverse, self.vertices)
        vertices /= counts
        colors = None
        if self.colors is not None:
            colors = np.zeros((n, 3))
            np.add.at(colors, inverse, self.colors)
            colors = (colors / counts).astype(np.float32)
        out = Mesh(vertices, inverse[self.faces], None, colors, None)
        out, _dropped = out.remove_degenerate()
        out = out.remove_unreferenced()
        out.compute_normals()
        return out

    # --- the report --------------------------------------------------------------------------------------------------
    def report(self, voxel_size: float | None = None, inside: np.ndarray | None = None, intersections: bool = True) -> MeshReport:
        """The print-readiness report. `inside` (a voxel occupancy grid) and `voxel_size` enable the thin-wall estimate;
        `intersections` runs the sampled self-intersection check."""
        rep = MeshReport(vertices=self.vertex_count, faces=self.face_count)
        if self.face_count == 0:
            rep.notes.append("empty mesh")
            return rep
        _unique, counts, _corner = self.edges()
        rep.boundary_edges = int((counts == 1).sum())
        rep.nonmanifold_edges = int((counts > 2).sum())
        rep.consistent = self.is_consistently_oriented()
        rep.watertight = rep.boundary_edges == 0 and rep.nonmanifold_edges == 0
        rep.components = self.components()[0]
        rep.volume = abs(self.signed_volume()) if rep.watertight else 0.0
        rep.area = self.area()
        lo, hi = self.bounds()
        rep.bounds = (tuple(float(x) for x in lo), tuple(float(x) for x in hi))
        if inside is not None and voxel_size is not None and inside.any():
            rep.thin_wall = thin_wall_estimate(inside, voxel_size)
        if intersections:
            rep.self_intersections, rep.pairs_checked = self_intersections(self)
        return rep


COST_BANDS = 8


def quadric_decimate(mesh: Mesh, target_faces: int, max_rounds: int = 400, progress=None) -> Mesh:
    """Edge collapse with quadric error metrics, in vectorised rounds.

    Every round: per-vertex quadrics from the face planes; for every interior edge the optimal collapse point
    and its cost; only edges passing the link condition (the two ends share exactly two neighbours — the
    collapse keeps the surface a manifold) are candidates; an *independent set* of them — an edge is taken when
    it is the cheapest candidate of both its vertices — collapses at once. Boundary edges and vertices are
    left alone so open meshes keep their rims. Rounds repeat until the target is reached or nothing collapses.
    """
    out = mesh.copy()
    if out.colors is None:
        colors = None
    else:
        colors = out.colors.astype(np.float64)
    v = out.vertices.copy()
    f = out.faces.copy()
    start_faces = f.shape[0]
    rng_rounds = np.random.default_rng(12345)
    for _round in range(max_rounds):
        if f.shape[0] <= target_faces or f.shape[0] == 0:
            break
        if progress is not None:
            progress((start_faces - f.shape[0]) / max(1, start_faces - target_faces), f.shape[0])
        n = v.shape[0]
        # --- face planes and per-vertex quadrics (10 coefficients of the symmetric 4 × 4) ---
        normals = np.cross(v[f[:, 1]] - v[f[:, 0]], v[f[:, 2]] - v[f[:, 0]])
        areas = np.linalg.norm(normals, axis=1)
        ok = areas > 1e-300
        normals = np.where(ok[:, None], normals / np.maximum(areas, 1e-300)[:, None], 0.0)
        d = -np.einsum("ij,ij->i", normals, v[f[:, 0]])
        plane = np.concatenate([normals, d[:, None]], axis=1)                      # (M, 4)
        weight = np.sqrt(np.maximum(areas, 1e-300))[:, None] * 0 + 1.0              # unit weights (area weighting over-smooths thin parts)
        iu, ju = np.triu_indices(4)
        face_q = (plane[:, iu] * plane[:, ju]) * weight                              # (M, 10)
        quadric = np.zeros((n, 10))
        for corner in range(3):
            np.add.at(quadric, f[:, corner], face_q)
        # --- edges (as 1-D integer keys: far quicker to make unique than rows) ---
        directed = np.stack([f[:, [0, 1]], f[:, [1, 2]], f[:, [2, 0]]], axis=1).reshape(-1, 2)
        undirected = np.sort(directed, axis=1)
        keys, counts = np.unique(undirected[:, 0] * n + undirected[:, 1], return_counts=True)
        edges = np.stack([keys // n, keys % n], axis=1)
        boundary_vertex = np.zeros(n, dtype=bool)
        boundary_vertex[edges[counts != 2].reshape(-1)] = True
        interior = (counts == 2) & ~boundary_vertex[edges[:, 0]] & ~boundary_vertex[edges[:, 1]]
        cand = edges[interior]
        if cand.shape[0] == 0:
            break
        # link condition: exactly two common neighbours
        rows = np.concatenate([edges[:, 0], edges[:, 1]])
        cols = np.concatenate([edges[:, 1], edges[:, 0]])
        adjacency = sparse.csr_matrix((np.ones(rows.shape[0]), (rows, cols)), shape=(n, n))
        common = np.asarray(adjacency[cand[:, 0]].multiply(adjacency[cand[:, 1]]).sum(axis=1)).reshape(-1)
        cand = cand[common == 2]
        if cand.shape[0] == 0:
            break
        # --- optimal point and cost per candidate ---
        q = quadric[cand[:, 0]] + quadric[cand[:, 1]]                                # (E, 10)
        a = np.zeros((q.shape[0], 3, 3))
        a[:, 0, 0], a[:, 0, 1], a[:, 0, 2] = q[:, 0], q[:, 1], q[:, 2]
        a[:, 1, 0], a[:, 1, 1], a[:, 1, 2] = q[:, 1], q[:, 4], q[:, 5]
        a[:, 2, 0], a[:, 2, 1], a[:, 2, 2] = q[:, 2], q[:, 5], q[:, 7]
        b = -np.stack([q[:, 3], q[:, 6], q[:, 8]], axis=1)
        midpoint = (v[cand[:, 0]] + v[cand[:, 1]]) / 2.0
        det = np.linalg.det(a)
        scale = np.abs(a).max(axis=(1, 2))
        solvable = np.abs(det) > 1e-9 * np.maximum(scale, 1e-300) ** 3
        point = midpoint.copy()
        if solvable.any():
            solved = np.linalg.solve(a[solvable], b[solvable][..., None])[..., 0]
            # keep the solution near the edge (a far-away minimum means an ill-conditioned quadric)
            span = np.linalg.norm(v[cand[solvable, 0]] - v[cand[solvable, 1]], axis=1)
            near = np.linalg.norm(solved - midpoint[solvable], axis=1) <= 2.0 * span + 1e-12
            point[solvable] = np.where(near[:, None], solved, midpoint[solvable])
        px, py, pz = point[:, 0], point[:, 1], point[:, 2]
        cost = (q[:, 0] * px * px + q[:, 4] * py * py + q[:, 7] * pz * pz + q[:, 9]
                + 2.0 * (q[:, 1] * px * py + q[:, 2] * px * pz + q[:, 5] * py * pz + q[:, 3] * px + q[:, 6] * py + q[:, 8] * pz))
        cost = np.maximum(cost, 0.0)
        # --- an independent set of cheap, safe collapses: no chosen edge has an end inside another's 1-ring, so the
        #     faces the collapses reshape are disjoint; edges that would turn a face over are skipped ---
        wanted = max(1, (f.shape[0] - target_faces) // 2)
        order = np.argsort(cost, kind="stable")[:max(wanted * 12, 4096)]             # the cheapest: enough for an independent set
        # rank by cost *band* with a random order inside each band: neighbouring edges have similar costs, and a strict
        # cost order would let each edge block the next along a chain, leaving a handful of winners per pass
        band = (np.arange(order.shape[0]) * COST_BANDS) // max(1, order.shape[0])
        order = order[np.lexsort((rng_rounds.random(order.shape[0]), band))]
        cand, point = cand[order], point[order]
        n_cand = cand.shape[0]
        hood = (adjacency[cand[:, 0]] + adjacency[cand[:, 1]]).tocoo()            # (E, n): the two ends' neighbours
        pair_edge = np.concatenate([hood.row, np.arange(n_cand), np.arange(n_cand)])
        pair_vertex = np.concatenate([hood.col, cand[:, 0], cand[:, 1]])
        remaining = np.ones(n_cand, dtype=bool)
        blocked = np.zeros(n, dtype=bool)
        chosen_parts = []
        chosen_count = 0
        for _pass in range(4):
            live = remaining[pair_edge]
            pe, pv = pair_edge[live], pair_vertex[live]
            if pe.shape[0] == 0 or chosen_count >= wanted:
                break
            best = np.full(n, n_cand, dtype=np.int64)                                 # per vertex: the cheapest edge whose 1-ring holds it
            np.minimum.at(best, pv, pe)
            ranks = np.arange(n_cand)
            winners = np.nonzero(remaining & (best[cand[:, 0]] == ranks) & (best[cand[:, 1]] == ranks))[0]
            if winners.size == 0:
                break
            flips = _flips_faces(v, f, cand[winners], point[winners])
            if flips.any():                                                           # the quadric point turns a face: try the midpoint
                retry = winners[flips]
                midpoint_retry = (v[cand[retry, 0]] + v[cand[retry, 1]]) / 2.0
                still = _flips_faces(v, f, cand[retry], midpoint_retry)
                point[retry[~still]] = midpoint_retry[~still]
                flips[flips] = still
            safe = winners[~flips]
            remaining[winners] = False                                                # flipping edges wait for another round
            if safe.size:
                chosen_parts.append(safe)
                chosen_count += safe.size
                safe_mask = np.zeros(n_cand, dtype=bool)
                safe_mask[safe] = True
                blocked[pair_vertex[safe_mask[pair_edge]]] = True                     # the chosen edges' 1-rings
                remaining &= ~(blocked[cand[:, 0]] | blocked[cand[:, 1]])
        if not chosen_parts:
            break
        chosen_idx = np.sort(np.concatenate(chosen_parts))[:wanted]
        keep_u, drop_v = cand[chosen_idx, 0], cand[chosen_idx, 1]
        # --- apply: v merges into u at the optimal point ---
        v[keep_u] = point[chosen_idx]
        if colors is not None:
            colors[keep_u] = (colors[keep_u] + colors[drop_v]) / 2.0
        remap = np.arange(n)
        remap[drop_v] = keep_u
        f = remap[f]
        degenerate = (f[:, 0] == f[:, 1]) | (f[:, 1] == f[:, 2]) | (f[:, 0] == f[:, 2])
        f = f[~degenerate]
        # faces folded onto each other (the same three vertices twice) cancel: drop both
        sorted_faces = np.sort(f, axis=1)
        face_keys = (sorted_faces[:, 0] * n + sorted_faces[:, 1]) * n + sorted_faces[:, 2] if n < 2_000_000 else None
        if face_keys is not None:
            _unique, inverse, dup_counts = np.unique(face_keys, return_inverse=True, return_counts=True)
        else:
            _unique, inverse, dup_counts = np.unique(sorted_faces, axis=0, return_inverse=True, return_counts=True)
        folded = dup_counts[inverse.reshape(-1)] > 1
        if folded.any():
            f = f[~folded]
    result = Mesh(v, f, None, None if colors is None else colors.astype(np.float32), None).remove_unreferenced()
    result.compute_normals()
    return result


def _flips_faces(v: np.ndarray, f: np.ndarray, cand: np.ndarray, point: np.ndarray) -> np.ndarray:
    """For each candidate edge (u, v) → `point`: would any face around u or v (other than the two that vanish) turn over?"""
    m = f.shape[0]
    n = v.shape[0]
    incidence = sparse.csr_matrix((np.ones(3 * m, dtype=np.int8), (f.reshape(-1), np.repeat(np.arange(m), 3))), shape=(n, m))
    around = (incidence[cand[:, 0]] + incidence[cand[:, 1]]).tocoo()               # (E, M): faces touching u or v
    e, face = around.row, around.col
    both = (around.data >= 2)                                                        # faces containing both ends: they vanish
    e, face = e[~both], face[~both]
    if e.shape[0] == 0:
        return np.zeros(cand.shape[0], dtype=bool)
    corners = f[face]                                                                # (P, 3)
    u, w = cand[e, 0], cand[e, 1]
    moved = (corners == u[:, None]) | (corners == w[:, None])
    old_pos = v[corners]                                                             # (P, 3, 3)
    new_pos = np.where(moved[..., None], point[e][:, None, :], old_pos)
    old_n = np.cross(old_pos[:, 1] - old_pos[:, 0], old_pos[:, 2] - old_pos[:, 0])
    new_n = np.cross(new_pos[:, 1] - new_pos[:, 0], new_pos[:, 2] - new_pos[:, 0])
    flip = np.einsum("ij,ij->i", old_n, new_n) <= 1e-12 * np.maximum(np.einsum("ij,ij->i", old_n, old_n), 1e-300)
    return np.bincount(e, weights=flip, minlength=cand.shape[0]) > 0


def _segments_hit_triangles(p0: np.ndarray, p1: np.ndarray, a: np.ndarray, b: np.ndarray, c: np.ndarray) -> np.ndarray:
    """Möller–Trumbore: does segment p0→p1 cross triangle (a, b, c)? `(N,)` bool, vectorised over N."""
    d = p1 - p0
    e1, e2 = b - a, c - a
    h = np.cross(d, e2)
    det = np.einsum("ij,ij->i", e1, h)
    ok = np.abs(det) > 1e-14
    inv = np.where(ok, 1.0 / np.where(ok, det, 1.0), 0.0)
    s_ = p0 - a
    u = np.einsum("ij,ij->i", s_, h) * inv
    q = np.cross(s_, e1)
    v = np.einsum("ij,ij->i", d, q) * inv
    t = np.einsum("ij,ij->i", e2, q) * inv
    eps = 1e-9
    return ok & (u > eps) & (v > eps) & (u + v < 1.0 - eps) & (t > eps) & (t < 1.0 - eps)


def self_intersections(mesh: Mesh, max_pairs: int = 300_000, seed: int = 1) -> tuple[int, int]:
    """(intersecting triangle pairs found, pairs checked): triangles sharing a grid cell are paired (at most `max_pairs`,
    sampled), pairs sharing a vertex skipped, each pair tested edge-against-triangle both ways."""
    f = mesh.faces
    m = f.shape[0]
    if m < 2:
        return 0, 0
    v = mesh.vertices
    tri = v[f]                                                          # (M, 3, 3)
    lo, hi = tri.min(axis=1), tri.max(axis=1)
    extent = float((v.max(axis=0) - v.min(axis=0)).max()) or 1.0
    edge = np.linalg.norm(tri[:, 1] - tri[:, 0], axis=1)
    cell = max(float(np.median(edge)) * 2.0, extent / 256.0, 1e-12)
    centre = (lo + hi) / 2.0
    keys = np.floor((centre - v.min(axis=0)) / cell).astype(np.int64)
    flat = (keys[:, 0] * 73856093) ^ (keys[:, 1] * 19349663) ^ (keys[:, 2] * 83492791)
    order = np.argsort(flat, kind="stable")
    sorted_keys = flat[order]
    starts = np.r_[0, np.nonzero(np.diff(sorted_keys))[0] + 1, m]
    pairs_a, pairs_b = [], []
    rng = np.random.default_rng(seed)
    budget = max_pairs
    for i in range(starts.shape[0] - 1):
        members = order[starts[i]:starts[i + 1]]
        n = members.shape[0]
        if n < 2:
            continue
        ia, ib = np.triu_indices(n, 1)
        if ia.shape[0] > budget:
            pick = rng.choice(ia.shape[0], size=budget, replace=False)
            ia, ib = ia[pick], ib[pick]
        pairs_a.append(members[ia])
        pairs_b.append(members[ib])
        budget -= ia.shape[0]
        if budget <= 0:
            break
    if not pairs_a:
        return 0, 0
    pa, pb = np.concatenate(pairs_a), np.concatenate(pairs_b)
    # pairs sharing a vertex touch legitimately; boxes that do not overlap cannot intersect
    share = (f[pa][:, :, None] == f[pb][:, None, :]).any(axis=(1, 2))
    overlap = (lo[pa] <= hi[pb]).all(axis=1) & (lo[pb] <= hi[pa]).all(axis=1)
    keep = ~share & overlap
    pa, pb = pa[keep], pb[keep]
    checked = int(pa.shape[0])
    if checked == 0:
        return 0, int(keep.shape[0])
    ta, tb = tri[pa], tri[pb]
    hit = np.zeros(checked, dtype=bool)
    for i in range(3):
        hit |= _segments_hit_triangles(ta[:, i], ta[:, (i + 1) % 3], tb[:, 0], tb[:, 1], tb[:, 2])
        hit |= _segments_hit_triangles(tb[:, i], tb[:, (i + 1) % 3], ta[:, 0], ta[:, 1], ta[:, 2])
    return int(hit.sum()), int(keep.shape[0])


def _edge_direction(face: np.ndarray, a: int, b: int) -> int:
    """+1 when `face` traverses a→b, −1 for b→a."""
    for i in range(3):
        if face[i] == a and face[(i + 1) % 3] == b:
            return 1
    return -1


def _nearest_attribute(source_points: np.ndarray, attribute: np.ndarray, query: np.ndarray) -> np.ndarray:
    from scipy.spatial import cKDTree
    _d, idx = cKDTree(source_points).query(query)
    return attribute[idx]


def thin_wall_estimate(inside: np.ndarray, voxel_size: float) -> float:
    """A lower-bound estimate of the thinnest wall of an occupancy grid: twice the 5th-percentile distance to the
    surface along the medial axis (the medial sheets near sharp edges pull it down, so it errs on the thin side)."""
    edt = ndimage.distance_transform_edt(inside)
    ridge = (edt > 0) & (edt >= ndimage.maximum_filter(edt, size=3) - 1e-9)
    values = edt[ridge]
    if values.size == 0:
        return 0.0
    return float(2.0 * np.percentile(values, 5) * voxel_size)


@dataclass
class CleanSettings:
    """What the clean-up pipeline does (the three repair levels are presets of this).

    Attributes:
        weld: Merge coincident vertices.
        min_piece_faces: Drop pieces with fewer faces (0 = keep all).
        keep_largest: Keep only the N largest pieces (0 = all that pass `min_piece_faces`).
        fill_holes_up_to: Close boundary loops up to this many edges (0 = none).
        smooth_iterations: Taubin smoothing passes.
        target_faces: Decimate to about this many faces (0 = no decimation).
        orient: Make the winding consistent and outward.
    """
    weld: bool = True
    min_piece_faces: int = 50
    keep_largest: int = 0
    fill_holes_up_to: int = 0
    smooth_iterations: int = 0
    target_faces: int = 0
    orient: bool = True


SIMPLE_CLEAN = CleanSettings()
AGGRESSIVE_CLEAN = CleanSettings(min_piece_faces=200, keep_largest=1, fill_holes_up_to=200, smooth_iterations=8, target_faces=200_000)


def clean(mesh: Mesh, settings: CleanSettings = SIMPLE_CLEAN, voxel_size: float | None = None,
          inside: np.ndarray | None = None, progress=None) -> tuple[Mesh, MeshReport]:
    """Run the clean-up pipeline; returns the mesh and its report with a note per step (`progress(fraction, faces)` follows
    the decimation, the slow step)."""
    notes = []
    out = mesh
    out, dropped = out.remove_degenerate()
    if dropped:
        notes.append(f"{dropped} degenerate faces removed")
    if settings.weld:
        before = out.vertex_count
        out = out.weld()
        if out.vertex_count != before:
            notes.append(f"{before - out.vertex_count} vertices welded")
    if settings.min_piece_faces or settings.keep_largest:
        out, pieces = out.keep_components(settings.min_piece_faces, settings.keep_largest)
        if pieces:
            notes.append(f"{pieces} small pieces dropped")
    if settings.fill_holes_up_to:
        out, holes = out.fill_holes(settings.fill_holes_up_to)
        if holes:
            notes.append(f"{holes} holes filled")
    if settings.orient:
        if not out.is_consistently_oriented():
            notes.append("face orientation made consistent")
        out = out.oriented()
    if settings.smooth_iterations:
        out = out.taubin_smoothed(settings.smooth_iterations)
        notes.append(f"smoothed ({settings.smooth_iterations} Taubin passes)")
    if settings.target_faces and out.face_count > settings.target_faces:
        before = out.face_count
        out = out.decimated(settings.target_faces, progress)
        notes.append(f"decimated from {before} to {out.face_count} faces")
    if out.normals is None:
        out.compute_normals()
    rep = out.report(voxel_size, inside)
    rep.notes = notes + rep.notes
    return out, rep


def remesh(inside: np.ndarray, grid_origin: np.ndarray, spacing: float, close_radius: int = 1) -> np.ndarray:
    """The last-resort repair: a voxel remesh. Morphologically close the occupancy by `close_radius`, fill enclosed
    cavities, keep the largest connected blob; returns the new occupancy grid (the caller re-runs the isosurface)."""
    solid = inside.astype(bool)
    if close_radius > 0:
        solid = ndimage.binary_closing(solid, iterations=int(close_radius))
    solid = ndimage.binary_fill_holes(solid)
    labels, count = ndimage.label(solid)
    if count > 1:
        sizes = ndimage.sum(solid, labels, range(1, count + 1))
        solid = labels == (int(np.argmax(sizes)) + 1)
    solid[0, :, :] = solid[-1, :, :] = False
    solid[:, 0, :] = solid[:, -1, :] = False
    solid[:, :, 0] = solid[:, :, -1] = False
    return solid


__all__ = ["Mesh", "MeshReport", "CleanSettings", "SIMPLE_CLEAN", "AGGRESSIVE_CLEAN", "clean", "remesh", "thin_wall_estimate",
           "quadric_decimate", "self_intersections"]
