"""Points → voxel grids: a density grid and a colour grid, with the pre-filters meshing wants.

The grid is cubic-voxelled (`spacing` world units on each axis) over a bounding box taken from the points
(percentile-trimmed, so a few runaway points do not shrink everything else into a corner), `resolution`
voxels along the longest side, and one voxel of empty padding all round so the isosurface closes. Density
is the number of points per voxel; the colour grid holds the sum of the points' colours, so `colour / density`
is the mean colour. The filters (`smooth`, `dilate`, `erode`) are `scipy.ndimage` on the density;
`normalized()` scales the density so the isosurface threshold can be a 0..1 number the UI shows on a
log-histogram (`log_histogram`).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import ndimage

from .capture import PointCloud

PADDING = 1
TRIM_PERCENTILE = 0.2          # points outside this percentile range (each side) do not stretch the box
NORMALISE_PERCENTILE = 99.0    # density at this percentile (of occupied voxels) becomes 1.0
MAX_RESOLUTION = 512


@dataclass
class VoxelGrid:
    """Density and colour on a regular grid.

    Attributes:
        density: `(nx, ny, nz)` float32, points per voxel (after filters: a smoothed count).
        color: `(nx, ny, nz, 3)` float32 colour sums (None when the capture had no colours wanted).
        origin: World position of the corner of voxel (0, 0, 0).
        spacing: Voxel size in world units.
    """
    density: np.ndarray
    color: np.ndarray | None
    origin: np.ndarray
    spacing: float

    @property
    def shape(self) -> tuple[int, int, int]:
        return tuple(int(n) for n in self.density.shape)

    @property
    def occupied(self) -> int:
        """Voxels with any density."""
        return int(np.count_nonzero(self.density > 0))

    def voxel_centres(self, ijk: np.ndarray) -> np.ndarray:
        """World positions of voxel centres given `(…, 3)` indices."""
        return self.origin + (np.asarray(ijk, dtype=np.float64) + 0.5) * self.spacing

    def to_world(self, grid_xyz: np.ndarray) -> np.ndarray:
        """World positions of `(…, 3)` continuous grid coordinates (grid-point `i` is voxel `i`'s centre)."""
        return self.origin + (np.asarray(grid_xyz, dtype=np.float64) + 0.5) * self.spacing

    def mean_color(self) -> np.ndarray | None:
        """`(nx, ny, nz, 3)` mean colour per voxel (grey where empty)."""
        if self.color is None:
            return None
        weight = np.maximum(self.density, 1e-12)[..., None]
        mean = self.color / weight
        mean[self.density <= 0] = 0.5
        return np.clip(mean, 0.0, 1.0).astype(np.float32)

    def normalized(self, percentile: float = NORMALISE_PERCENTILE) -> tuple[np.ndarray, float]:
        """(density / scale, scale): the density at `percentile` of the occupied voxels becomes 1 (0 for an empty grid)."""
        occupied = self.density[self.density > 0]
        if occupied.size == 0:
            return self.density, 0.0
        scale = float(np.percentile(occupied, percentile))
        scale = scale if scale > 0 else float(occupied.max())
        return self.density / scale, scale

    def memory_bytes(self) -> int:
        return int(self.density.nbytes + (self.color.nbytes if self.color is not None else 0))


def grid_bounds(xyz: np.ndarray, trim: float = TRIM_PERCENTILE) -> tuple[np.ndarray, np.ndarray]:
    """A bounding box of the points with the outermost `trim` percent on each side ignored."""
    if xyz.shape[0] == 0:
        return np.array([-1.0, -1.0, -1.0]), np.array([1.0, 1.0, 1.0])
    lo = np.percentile(xyz, trim, axis=0).astype(np.float64)
    hi = np.percentile(xyz, 100.0 - trim, axis=0).astype(np.float64)
    span = np.maximum(hi - lo, 1e-6)
    return lo - 0.01 * span, hi + 0.01 * span


def voxelize(cloud: PointCloud, resolution: int, bounds: tuple[np.ndarray, np.ndarray] | None = None,
             with_color: bool = True) -> VoxelGrid:
    """Accumulate the points into a grid with `resolution` voxels along the longest side of `bounds`.

    Raises:
        ValueError: For a resolution outside 8..MAX_RESOLUTION.
    """
    resolution = int(resolution)
    if not 8 <= resolution <= MAX_RESOLUTION:
        raise ValueError(f"resolution must be between 8 and {MAX_RESOLUTION}, got {resolution}")
    lo, hi = bounds if bounds is not None else grid_bounds(cloud.xyz)
    lo, hi = np.asarray(lo, dtype=np.float64), np.asarray(hi, dtype=np.float64)
    span = np.maximum(hi - lo, 1e-9)
    spacing = float(span.max()) / resolution
    size = np.maximum(1, np.ceil(span / spacing).astype(int)) + 2 * PADDING
    origin = lo - PADDING * spacing
    ijk = np.floor((cloud.xyz.astype(np.float64) - origin) / spacing).astype(np.int64)
    inside = np.all((ijk >= 0) & (ijk < size), axis=1)
    ijk = ijk[inside]
    flat = np.ravel_multi_index((ijk[:, 0], ijk[:, 1], ijk[:, 2]), tuple(size))
    cells = int(np.prod(size))
    density = np.bincount(flat, minlength=cells).astype(np.float32).reshape(tuple(size))
    color = None
    if with_color:
        rgb = cloud.rgb[inside]
        color = np.stack([np.bincount(flat, weights=rgb[:, ch], minlength=cells) for ch in range(3)], axis=-1)
        color = color.astype(np.float32).reshape((*size, 3))
    return VoxelGrid(density, color, origin, spacing)


def smooth(grid: VoxelGrid, sigma: float) -> VoxelGrid:
    """Gaussian-blur the density (and the colour sums alike) by `sigma` voxels (0 = unchanged)."""
    if sigma <= 0:
        return grid
    density = ndimage.gaussian_filter(grid.density, sigma, mode="constant")
    color = None
    if grid.color is not None:
        color = np.stack([ndimage.gaussian_filter(grid.color[..., ch], sigma, mode="constant") for ch in range(3)], axis=-1)
    return VoxelGrid(density.astype(np.float32), color, grid.origin, grid.spacing)


def dilate(grid: VoxelGrid, radius: int) -> VoxelGrid:
    """Grey dilation of the density by `radius` voxels (thickens thin parts); 0 = unchanged."""
    if radius <= 0:
        return grid
    size = 2 * int(radius) + 1
    density = ndimage.grey_dilation(grid.density, size=(size, size, size), mode="constant")
    color = None
    if grid.color is not None:
        color = np.stack([ndimage.grey_dilation(grid.color[..., ch], size=(size, size, size), mode="constant") for ch in range(3)], axis=-1)
    return VoxelGrid(density.astype(np.float32), color, grid.origin, grid.spacing)


def erode(grid: VoxelGrid, radius: int) -> VoxelGrid:
    """Grey erosion of the density by `radius` voxels (removes thin parts and noise); 0 = unchanged."""
    if radius <= 0:
        return grid
    size = 2 * int(radius) + 1
    density = ndimage.grey_erosion(grid.density, size=(size, size, size), mode="constant")
    return VoxelGrid(density.astype(np.float32), grid.color, grid.origin, grid.spacing)


def log_histogram(density: np.ndarray, bins: int = 64) -> tuple[np.ndarray, np.ndarray]:
    """(bin edges in normalized density, counts) of the occupied voxels on a log scale, for the threshold slider."""
    occupied = density[density > 0]
    if occupied.size == 0:
        return np.linspace(0.0, 1.0, bins + 1), np.zeros(bins)
    lo = max(float(occupied.min()), 1e-6)
    hi = max(float(occupied.max()), lo * 1.0001)
    edges = np.geomspace(lo, hi, bins + 1)
    counts, _ = np.histogram(occupied, bins=edges)
    return edges, counts


def suggest_threshold(normalized_density: np.ndarray) -> float:
    """A starting iso-level: the geometric middle of the occupied range, clamped to 0.02..0.5."""
    occupied = normalized_density[normalized_density > 0]
    if occupied.size == 0:
        return 0.1
    lo, hi = max(float(occupied.min()), 1e-6), max(float(np.percentile(occupied, 99)), 1e-6)
    return float(np.clip(np.sqrt(lo * hi), 0.02, 0.5))


__all__ = ["VoxelGrid", "voxelize", "grid_bounds", "smooth", "dilate", "erode", "log_histogram", "suggest_threshold",
           "MAX_RESOLUTION", "PADDING"]
