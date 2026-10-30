"""The G-buffer: per pixel, the nearest point's view-space position, palette colour and material — and shadow maps.

Points are *splatted* with a depth test (`np.minimum.at` on the depth buffer, then the winners are gathered),
so after any number of passes every pixel holds the front-most sample seen so far; the image only gets more
complete. A `ShadowMap` is the same thing seen from a light: the nearest depth along the light's direction on
an orthographic grid over the scene's bounding box.
"""

from __future__ import annotations

import numpy as np

from .view import View, light_direction

EMPTY_DEPTH = np.inf


class GBuffer:
    """The nearest sample per pixel of a `width × height` grid (the view's supersampled size).

    Attributes:
        depth: `(H, W)` float32, `inf` where nothing landed.
        pos: `(H, W, 3)` float32 view-space position of the nearest sample.
        color: `(H, W)` int16 palette index (0..255), −1 where empty.
        material: `(H, W)` int16 material (transform) index, −1 where empty.
        count: `(H, W)` int32 number of samples that landed in the pixel (the density threshold reads it).
        normal: `(H, W, 3)` float32 surface normals given with the samples (a mesh preview), or None — then the
            shader derives normals from the positions.
    """

    def __init__(self, width: int, height: int, with_normals: bool = False):
        self.width, self.height = int(width), int(height)
        self.depth = np.full((self.height, self.width), EMPTY_DEPTH, dtype=np.float32)
        self.pos = np.zeros((self.height, self.width, 3), dtype=np.float32)
        self.color = np.full((self.height, self.width), -1, dtype=np.int16)
        self.material = np.full((self.height, self.width), -1, dtype=np.int16)
        self.count = np.zeros((self.height, self.width), dtype=np.int32)
        self.normal = np.zeros((self.height, self.width, 3), dtype=np.float32) if with_normals else None

    @property
    def hits(self) -> np.ndarray:
        """`(H, W)` bool: where a sample landed."""
        return np.isfinite(self.depth)

    @property
    def coverage(self) -> float:
        """Fraction of pixels with a sample."""
        return float(self.hits.mean()) if self.depth.size else 0.0

    def splat(self, px: np.ndarray, py: np.ndarray, vx: np.ndarray, vy: np.ndarray, vz: np.ndarray,
              color: np.ndarray, material: np.ndarray, normal: np.ndarray | None = None) -> int:
        """Depth-test points into the buffer (pixel coordinates `px, py` as floats); returns how many landed inside.
        `normal` (`(N, 3)` view-space) is stored for the winning samples when the buffer carries normals."""
        inside = (px >= 0) & (px < self.width) & (py >= 0) & (py < self.height) & np.isfinite(vz) & np.isfinite(px) & np.isfinite(py)
        if not inside.any():
            return 0
        sel = np.nonzero(inside)[0]
        idx = py[sel].astype(np.intp) * self.width + px[sel].astype(np.intp)
        depth = (-vz[sel]).astype(np.float32)
        flat = self.depth.reshape(-1)
        np.add.at(self.count.reshape(-1), idx, 1)
        np.minimum.at(flat, idx, depth)
        winners = depth <= flat[idx]            # the samples that now hold their pixel's minimum
        w = sel[winners]
        wi = idx[winners]
        pos = self.pos.reshape(-1, 3)
        pos[wi, 0] = vx[w]
        pos[wi, 1] = vy[w]
        pos[wi, 2] = vz[w]
        self.color.reshape(-1)[wi] = color[w]
        self.material.reshape(-1)[wi] = material[w]
        if self.normal is not None and normal is not None:
            self.normal.reshape(-1, 3)[wi] = normal[w]
        return int(sel.size)

    def merge(self, other: "GBuffer") -> None:
        """Take every pixel where `other` is nearer (the threads' buffers into one)."""
        nearer = other.depth < self.depth
        self.depth[nearer] = other.depth[nearer]
        self.pos[nearer] = other.pos[nearer]
        self.color[nearer] = other.color[nearer]
        self.material[nearer] = other.material[nearer]
        if self.normal is not None:
            self.normal[nearer] = other.normal[nearer] if other.normal is not None else 0.0   # no given normal: derived later
        self.count += other.count

    def fill_gaps(self, passes: int = 1) -> None:
        """Fill empty pixels from their nearest (in depth) filled 8-neighbour — closes the holes of a sparse point splat."""
        for _ in range(passes):
            empty = ~self.hits
            if not empty.any():
                return
            best_depth = np.full_like(self.depth, EMPTY_DEPTH)
            best_src = np.full(self.depth.shape + (2,), -1, dtype=np.int64)
            ys, xs = np.indices(self.depth.shape)
            for dy in (-1, 0, 1):
                for dx in (-1, 0, 1):
                    if dy == 0 and dx == 0:
                        continue
                    sy = np.clip(ys + dy, 0, self.height - 1)
                    sx = np.clip(xs + dx, 0, self.width - 1)
                    d = self.depth[sy, sx]
                    better = empty & (d < best_depth)
                    best_depth[better] = d[better]
                    best_src[better, 0] = sy[better]
                    best_src[better, 1] = sx[better]
            fill = empty & np.isfinite(best_depth)
            if not fill.any():
                return
            sy, sx = best_src[fill, 0], best_src[fill, 1]
            self.depth[fill] = self.depth[sy, sx]
            self.pos[fill] = self.pos[sy, sx]
            self.color[fill] = self.color[sy, sx]
            self.material[fill] = self.material[sy, sx]
            self.count[fill] = self.count[sy, sx]
            if self.normal is not None:
                self.normal[fill] = self.normal[sy, sx]

    def thresholded(self, min_hits: int) -> "GBuffer":
        """A copy with every pixel that collected fewer than `min_hits` samples emptied (the density threshold)."""
        if min_hits <= 1:
            return self
        out = GBuffer.__new__(GBuffer)
        out.width, out.height = self.width, self.height
        sparse = self.count < min_hits
        out.depth = np.where(sparse, EMPTY_DEPTH, self.depth).astype(np.float32)
        out.pos = self.pos
        out.color = np.where(sparse, -1, self.color).astype(np.int16)
        out.material = np.where(sparse, -1, self.material).astype(np.int16)
        out.count = self.count
        out.normal = self.normal
        return out


class ShadowMap:
    """The nearest depth along a light's direction, on an orthographic grid over the scene's bounding box.

    Attributes:
        direction: Unit vector towards the light (view space).
        size: Grid resolution.
        depth: `(size, size)` float32 distance along the light (smaller = nearer to the light), `inf` where empty.
    """

    def __init__(self, altitude: float, azimuth: float, bounds: np.ndarray, size: int = 1024):
        self.direction = light_direction(altitude, azimuth)
        self.size = int(size)
        self.basis = light_basis(self.direction)
        corners = np.array([[bounds[i][0], bounds[j][1], bounds[k][2]] for i in (0, 1) for j in (0, 1) for k in (0, 1)])
        projected = corners @ self.basis.T                     # (8, 3): u, v, along
        lo, hi = projected.min(axis=0), projected.max(axis=0)
        pad = 0.02 * (hi - lo).max() + 1e-6
        self.origin = lo[:2] - pad
        self.scale = (self.size - 1) / (hi[:2] - lo[:2] + 2 * pad)
        self.depth = np.full((self.size, self.size), EMPTY_DEPTH, dtype=np.float32)
        self.extent = float((hi - lo).max())
        # the GPU stores the distance along the light normalised to 0..1 over this range (a clear of 1.0 is then safe on
        # drivers that clamp clear colours; the range is padded so nothing lands outside it)
        self.along_min = float(lo[2] - pad - 0.5 * self.extent)
        self.along_scale = 1.0 / max(float(hi[2] - lo[2] + 2 * pad + self.extent), 1e-9)
        self.bias_scale = 1.0          # multiplies the default depth bias (mesh previews use more: their maps are point-sampled)

    def light_coords(self, vx: np.ndarray, vy: np.ndarray, vz: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Grid coordinates (u, v) and the distance along the light of view-space points."""
        b = self.basis
        u = b[0, 0] * vx + b[0, 1] * vy + b[0, 2] * vz
        v = b[1, 0] * vx + b[1, 1] * vy + b[1, 2] * vz
        along = b[2, 0] * vx + b[2, 1] * vy + b[2, 2] * vz
        return (u - self.origin[0]) * self.scale[0], (v - self.origin[1]) * self.scale[1], along

    def splat(self, vx: np.ndarray, vy: np.ndarray, vz: np.ndarray) -> None:
        """Record the nearest distance to the light in every cell the points fall into."""
        u, v, along = self.light_coords(vx, vy, vz)
        inside = (u >= 0) & (u < self.size) & (v >= 0) & (v < self.size) & np.isfinite(along)
        if not inside.any():
            return
        idx = v[inside].astype(np.intp) * self.size + u[inside].astype(np.intp)
        np.minimum.at(self.depth.reshape(-1), idx, along[inside].astype(np.float32))

    def empty_copy(self) -> "ShadowMap":
        """A map with the same grid and nothing in it (a worker thread's own)."""
        clone = ShadowMap.__new__(ShadowMap)
        clone.direction, clone.size, clone.basis = self.direction, self.size, self.basis
        clone.origin, clone.scale, clone.extent = self.origin, self.scale, self.extent
        clone.along_min, clone.along_scale = self.along_min, self.along_scale
        clone.bias_scale = self.bias_scale
        clone.depth = np.full((self.size, self.size), EMPTY_DEPTH, dtype=np.float32)
        return clone

    def merge(self, other: "ShadowMap") -> None:
        """The nearer of the two maps, cell by cell."""
        np.minimum(self.depth, other.depth, out=self.depth)

    def occlusion(self, pos: np.ndarray, softness: float = 1.5, bias: float | None = None) -> np.ndarray:
        """How much each view-space position `(…, 3)` is in this light's shadow (0 = lit, 1 = shadowed), with a
        `softness`-cell box blur (percentage-closer filtering)."""
        flat = pos.reshape(-1, 3)
        u, v, along = self.light_coords(flat[:, 0], flat[:, 1], flat[:, 2])
        bias = self.extent * 0.004 * self.bias_scale if bias is None else bias
        taps = max(1, int(round(softness)))
        offsets = range(-taps, taps + 1)
        total = np.zeros(flat.shape[0], dtype=np.float32)
        for du in offsets:
            for dv in offsets:
                ui = np.clip(np.floor(u).astype(np.intp) + du, 0, self.size - 1)
                vi = np.clip(np.floor(v).astype(np.intp) + dv, 0, self.size - 1)
                nearest = self.depth[vi, ui]
                total += (nearest + bias < along).astype(np.float32)
        return (total / len(offsets) ** 2).reshape(pos.shape[:-1])


def light_basis(direction: np.ndarray) -> np.ndarray:
    """Rows: two unit axes spanning the plane perpendicular to `direction`, then `−direction` (distance along the
    light grows away from it)."""
    d = direction / np.linalg.norm(direction)
    helper = np.array([0.0, 1.0, 0.0]) if abs(d[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
    u = np.cross(helper, d)
    u /= np.linalg.norm(u)
    v = np.cross(d, u)
    return np.array([u, v, -d])


def downsample(image: np.ndarray, factor: int) -> np.ndarray:
    """Average `factor × factor` blocks of an `(H, W, C)` image (the anti-aliasing of a supersampled render)."""
    if factor <= 1:
        return image
    h, w = image.shape[0] // factor, image.shape[1] // factor
    return image[:h * factor, :w * factor].reshape(h, factor, w, factor, -1).mean(axis=(1, 3))


__all__ = ["GBuffer", "ShadowMap", "light_basis", "downsample", "EMPTY_DEPTH", "View"]
