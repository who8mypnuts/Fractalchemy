"""A fragment's distance estimator as a mesh: probe result → voxel grid → isosurface → clean mesh → files. Qt-free.

The second half of *Export mesh…* (the GPU sampling is `gl/mesh.py`). The distance field becomes a `VoxelGrid`
whose density is `-DE` so the host's surface nets (`solid.isosurface`) extract the level `DE = threshold` — a
threshold of half a voxel is the classic way to turn an estimated distance into a closed shell, since many
estimators never go negative inside the set. The clean-up levels and the print report are the host's
(`solid.mesh.clean`), the writers the host's (`solid.io.write_mesh`); the report is a small markdown file beside
the export.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Callable

import numpy as np

from ..solid.io.write import export_format, write_mesh
from ..solid.isosurface import surface_nets
from ..solid.mesh import AGGRESSIVE_CLEAN, SIMPLE_CLEAN, CleanSettings, Mesh, MeshReport, clean
from ..solid.voxelize import VoxelGrid
from .gl.mesh import Bounds, ProbeResult

Progress = Callable[[float, str], None]
Cancelled = Callable[[], bool]
CLEAN_LEVELS = ("none", "simple", "aggressive")
MAX_RESOLUTION = 512
MAX_SPARSE_RESOLUTION = 4096
MEMORY_GUARD_BYTES = 1_500_000_000  # distance + colour + working copies
BLOCK_PAD = 2                        # voxel layers sampled around a block so its surface continues into the neighbours


@dataclass
class DEMeshSettings:
    """How the DE is sampled and meshed.

    Attributes:
        resolution: Voxels per axis.
        bounds: The sampling box (the *fit* pass may shrink it).
        fit: Run a coarse pass first and shrink the box to where the fractal is.
        threshold_voxels: The shell is `DE = threshold_voxels × voxel size` (0.5 closes most estimators).
        colors: Sample `baseColor` for vertex colours (when the fragment provides it).
        clean: `none`, `simple` or `aggressive` (the host's clean-up levels).
        smooth_iterations: Taubin passes in the clean-up.
        target_faces: Decimate to about this many faces (0 = keep all).
        sparse: Sample the grid block by block and skip blocks the coarse pass shows empty — the way to resolutions
            beyond the memory of one dense grid (`MAX_SPARSE_RESOLUTION`).
        block: Voxels per block side in sparse mode.
    """
    resolution: int = 128
    bounds: Bounds = field(default_factory=Bounds)
    fit: bool = True
    threshold_voxels: float = 0.5
    colors: bool = True
    clean: str = "simple"
    smooth_iterations: int = 0
    target_faces: int = 0
    sparse: bool = False
    block: int = 96

    def copy(self) -> "DEMeshSettings":
        return replace(self)

    def check(self) -> list[str]:
        """Problems that make the settings unusable (empty when fine)."""
        problems = []
        top = MAX_SPARSE_RESOLUTION if self.sparse else MAX_RESOLUTION
        if not 8 <= self.resolution <= top:
            problems.append(f"resolution must be between 8 and {top}" + ("" if self.sparse else " (more with sparse blocks)"))
        if not self.sparse and estimated_bytes(self.resolution, self.colors) > MEMORY_GUARD_BYTES:
            problems.append(f"{self.resolution}³ voxels would need about {estimated_bytes(self.resolution, self.colors) / 1e9:.1f} GB")
        if self.sparse and not 16 <= self.block <= 256:
            problems.append("the block size must be between 16 and 256 voxels")
        if self.bounds.size <= 0:
            problems.append("the box size must be positive")
        if self.clean not in CLEAN_LEVELS:
            problems.append(f"unknown clean level {self.clean!r}")
        return problems


def estimated_bytes(resolution: int, colors: bool) -> int:
    """Rough peak memory of the probe + meshing for `resolution`³ voxels."""
    voxels = resolution ** 3
    return voxels * 4 * (3 + (3 if colors else 0))


@dataclass
class DEMeshResult:
    """Everything meshing produced.

    Attributes:
        settings: The settings used (the bounds as actually sampled).
        grid_shape: Voxels on each axis.
        voxel_size: Voxel side in world units.
        inside: Occupancy at the threshold (for the thin-wall estimate).
        full: The isosurface as extracted.
        clean: After the clean-up (the same mesh for level `none`).
        full_report, clean_report: Their reports.
        seconds: Time per stage.
    """
    settings: DEMeshSettings
    grid_shape: tuple[int, int, int]
    voxel_size: float
    inside: np.ndarray
    full: Mesh
    clean: Mesh
    full_report: MeshReport
    clean_report: MeshReport
    seconds: dict[str, float] = field(default_factory=dict)

    def mesh(self, form: str) -> Mesh:
        return self.full if form == "full" else self.clean

    def report(self, form: str) -> MeshReport:
        return self.full_report if form == "full" else self.clean_report


# --- grid ---------------------------------------------------------------------
def grid_from_probe(probe: ProbeResult) -> VoxelGrid:
    """The probe as a voxel grid: density `-DE`, so *inside* is `density > -threshold` and the crossing interpolation is
    linear in the distance. Colours are not put on the grid (the host weights them by density, which is negative here);
    `vertex_colors` samples them at the vertices instead."""
    return VoxelGrid((-probe.distance).astype(np.float32), None, probe.origin, probe.spacing)


def vertex_colors(mesh: Mesh, probe: ProbeResult) -> np.ndarray | None:
    """`(V, 3)` float32 colours: the probe's `baseColor` samples interpolated at the vertices (None without colours)."""
    if probe.color is None or mesh.vertex_count == 0:
        return None
    from scipy import ndimage

    coords = ((np.asarray(mesh.vertices, dtype=np.float64) - probe.origin) / probe.spacing - 0.5).T
    channels = [ndimage.map_coordinates(probe.color[..., ch], coords, order=1, mode="nearest") for ch in range(3)]
    return np.clip(np.stack(channels, axis=1), 0.0, 1.0).astype(np.float32)


def clean_settings_for(settings: DEMeshSettings) -> CleanSettings:
    """The host's clean-up settings for the chosen level."""
    base = AGGRESSIVE_CLEAN if settings.clean == "aggressive" else SIMPLE_CLEAN
    return replace(base, smooth_iterations=settings.smooth_iterations, target_faces=settings.target_faces)


def build_de_mesh(probe: ProbeResult, settings: DEMeshSettings, progress: Progress | None = None, cancelled: Cancelled | None = None
                  ) -> DEMeshResult | None:
    """Isosurface, clean-up and reports from a probe (None when cancelled)."""
    report = progress or (lambda fraction, message: None)
    cancelled = cancelled or (lambda: False)
    seconds: dict[str, float] = {}
    started = time.perf_counter()
    report(0.0, "Building the voxel grid")
    grid = grid_from_probe(probe)
    iso = -settings.threshold_voxels * probe.spacing
    inside = grid.density > iso
    report(0.1, "Extracting the surface")
    full = surface_nets(grid, iso, with_color=False)
    if settings.colors:
        full.colors = vertex_colors(full, probe)
    seconds["isosurface"] = time.perf_counter() - started
    if cancelled():
        return None
    started = time.perf_counter()
    report(0.5, "Checking the full mesh")
    full_report = full.report(probe.spacing, inside)
    if cancelled():
        return None
    if settings.clean == "none" or full.face_count == 0:
        cleaned, clean_report = full, full_report
    else:
        report(0.65, f"Cleaning ({settings.clean})")
        cleaned, clean_report = _clean(full, settings, probe, inside, report, cancelled)
        if cleaned is None:
            return None
    seconds["clean"] = time.perf_counter() - started
    report(1.0, "Mesh ready")
    used = replace(settings, bounds=probe.bounds)
    return DEMeshResult(used, probe.distance.shape, probe.spacing, inside, full, cleaned, full_report, clean_report, seconds)


# --- sparse blocks ---------------------------------------------------------------------------------------------------
def active_blocks(coarse: ProbeResult, bounds: Bounds, resolution: int, block: int, threshold_world: float) -> list[tuple[int, int, int]]:
    """The block indices a coarse probe shows the surface may cross (DE below the threshold plus the coarse cell's reach)."""
    blocks_per_side = -(-resolution // block)
    cell = coarse.spacing
    reach = threshold_world + cell * 1.8                     # a coarse sample can miss the surface by its cell's diagonal
    near = np.argwhere(coarse.distance <= reach)
    if near.shape[0] == 0:
        return []
    block_world = bounds.spacing(resolution) * block
    centres = coarse.origin + (near + 0.5) * cell
    found: set[tuple[int, int, int]] = set()
    origin = np.asarray(bounds.origin)
    for offset in np.array([[dx, dy, dz] for dx in (-1, 0, 1) for dy in (-1, 0, 1) for dz in (-1, 0, 1)]) * cell:
        index = np.floor((centres + offset - origin) / block_world).astype(int)
        ok = np.all((index >= 0) & (index < blocks_per_side), axis=1)
        found.update(map(tuple, index[ok].tolist()))
    return sorted(found)


def block_mesh(probe_result: ProbeResult, core_lo: np.ndarray, core_hi: np.ndarray, iso: float, colors: bool) -> Mesh:
    """The isosurface of one padded block, trimmed to the faces whose centroid lies in the block's own box."""
    grid = grid_from_probe(probe_result)
    mesh = surface_nets(grid, iso, with_color=False)
    if mesh.face_count == 0:
        return Mesh.empty()
    centroids = mesh.vertices[mesh.faces].mean(axis=1)
    keep = np.all((centroids >= core_lo) & (centroids < core_hi), axis=1)
    faces = mesh.faces[keep]
    used = np.unique(faces)
    remap = np.full(mesh.vertex_count, -1, dtype=np.int64)
    remap[used] = np.arange(used.shape[0])
    trimmed = Mesh(mesh.vertices[used], remap[faces])
    if colors:
        trimmed.colors = vertex_colors(trimmed, probe_result)
    return trimmed


def build_de_mesh_sparse(probe, settings: DEMeshSettings, progress: Progress | None = None, cancelled: Cancelled | None = None
                         ) -> DEMeshResult | None:
    """Block-by-block meshing at `settings.resolution` over `settings.bounds` (None when cancelled).

    A coarse probe picks the blocks near the surface; each is sampled with `BLOCK_PAD` voxel layers of padding, meshed
    on its own and trimmed to its box, so neighbouring blocks produce identical vertices along their shared cubes; a
    weld joins them into one mesh.
    """
    report = progress or (lambda fraction, message: None)
    cancelled = cancelled or (lambda: False)
    started = time.perf_counter()
    seconds: dict[str, float] = {}
    bounds, res, block = settings.bounds, settings.resolution, settings.block
    spacing = bounds.spacing(res)
    iso = -settings.threshold_voxels * spacing
    report(0.0, "Coarse pass: finding the blocks near the surface")
    coarse = probe.sample(bounds, max(16, min(64, -(-res // block) * 4)))
    if coarse is None:
        return None
    blocks = active_blocks(coarse, bounds, res, block, settings.threshold_voxels * spacing)
    origin = np.asarray(bounds.origin)
    pieces: list[Mesh] = []
    padded = block + 2 * BLOCK_PAD
    for n, (bx, by, bz) in enumerate(blocks):
        if cancelled():
            return None
        report(0.05 + 0.6 * n / max(1, len(blocks)), f"Sampling block {n + 1} of {len(blocks)} ({padded}³ voxels)")
        core_lo = origin + np.array([bx, by, bz]) * block * spacing
        core_hi = core_lo + block * spacing
        centre = tuple(float(c) for c in (core_lo + core_hi) / 2.0)
        sampled = probe.sample(Bounds(centre, padded * spacing), padded, settings.colors)
        if sampled is None:
            return None
        piece = block_mesh(sampled, core_lo - 1e-9, core_hi - 1e-9, iso, settings.colors and sampled.color is not None)
        if piece.face_count:
            pieces.append(piece)
    seconds["isosurface"] = time.perf_counter() - started
    started = time.perf_counter()
    report(0.7, "Joining the blocks")
    full = _join(pieces, spacing)
    full_report = full.report(spacing, None)
    if cancelled():
        return None
    if settings.clean == "none" or full.face_count == 0:
        cleaned, clean_report = full, full_report
    else:
        report(0.8, f"Cleaning ({settings.clean})")
        cleaned, clean_report = _clean_sparse(full, settings, spacing, report, cancelled)
        if cleaned is None:
            return None
    seconds["clean"] = time.perf_counter() - started
    report(1.0, f"Mesh ready ({len(blocks)} of {(-(-res // block)) ** 3} blocks held surface)")
    inside = np.zeros((1, 1, 1), dtype=bool)
    return DEMeshResult(settings.copy(), (res, res, res), spacing, inside, full, cleaned, full_report, clean_report, seconds)


def _join(pieces: list[Mesh], spacing: float) -> Mesh:
    if not pieces:
        return Mesh.empty()
    offsets = np.cumsum([0] + [p.vertex_count for p in pieces[:-1]])
    vertices = np.concatenate([p.vertices for p in pieces])
    faces = np.concatenate([p.faces + o for p, o in zip(pieces, offsets)])
    colors = np.concatenate([p.colors for p in pieces]) if all(p.colors is not None for p in pieces) else None
    mesh = Mesh(vertices, faces, colors=colors).weld(spacing * 1e-3)
    mesh, _dropped = mesh.remove_degenerate()
    if mesh.face_count and mesh.signed_volume() < 0:
        mesh = mesh.flipped()
    mesh.compute_normals()
    return mesh


def _clean_sparse(full: Mesh, settings: DEMeshSettings, spacing: float, report: Progress, cancelled: Cancelled):
    def decimation_progress(fraction: float, faces: int) -> None:
        report(0.85 + 0.14 * fraction, f"Decimating ({faces:,} faces)")
        if cancelled():
            raise _Cancelled()

    try:
        return clean(full, clean_settings_for(settings), spacing, None, progress=decimation_progress)
    except _Cancelled:
        return None, None


class _Cancelled(Exception):
    """Raised from the decimation progress callback to stop the clean-up."""


def _clean(full: Mesh, settings: DEMeshSettings, probe: ProbeResult, inside: np.ndarray, report: Progress, cancelled: Cancelled):
    def decimation_progress(fraction: float, faces: int) -> None:
        report(0.7 + 0.28 * fraction, f"Decimating ({faces:,} faces)")
        if cancelled():
            raise _Cancelled()

    try:
        return clean(full, clean_settings_for(settings), probe.spacing, inside, progress=decimation_progress)
    except _Cancelled:
        return None, None


# --- export -------------------------------------------------------------------
@dataclass
class DEExportSettings:
    """What *Export* writes.

    Attributes:
        form: `clean` or `full`.
        formats: Format keys (`solid.io.EXPORT_FORMATS`).
        colors: Keep vertex colours (formats that carry them).
        units: `world` or `mm` (scaled so the longest side is `size_mm`).
        size_mm: Target longest side for `mm`.
        report: Also write `<name>_report.md`.
    """
    form: str = "clean"
    formats: list[str] = field(default_factory=lambda: ["ply"])
    colors: bool = True
    units: str = "world"
    size_mm: float = 100.0
    report: bool = True

    def copy(self) -> "DEExportSettings":
        return replace(self, formats=list(self.formats))


@dataclass
class DEExportOutcome:
    """What an export wrote."""
    files: list[Path] = field(default_factory=list)
    report: Path | None = None
    notes: list[str] = field(default_factory=list)


def export_de_mesh(result: DEMeshResult, settings: DEExportSettings, folder: Path, name: str, fragment_name: str = "",
                   progress: Progress | None = None) -> DEExportOutcome:
    """Write the chosen form in every chosen format (+ the report) into `folder`.

    Raises:
        ValueError: No format chosen, a format unavailable here, or an empty mesh.
        OSError: When a file cannot be written.
    """
    report = progress or (lambda fraction, message: None)
    if not settings.formats:
        raise ValueError("choose at least one format")
    mesh = result.mesh(settings.form)
    if mesh.face_count == 0:
        raise ValueError("the mesh is empty — nothing to export")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    outcome = DEExportOutcome()
    meters_per_unit = 1.0
    if settings.units == "mm":
        mesh = mesh.scaled_to(settings.size_mm)
        meters_per_unit = 0.001
        outcome.notes.append(f"scaled so the longest side is {settings.size_mm:g} mm")
    if not settings.colors and mesh.colors is not None:
        mesh = mesh.copy()
        mesh.colors = None
    formats = [export_format(key) for key in settings.formats]
    for index, fmt in enumerate(formats):
        report(index / max(1, len(formats)), f"Writing {fmt.label}")
        outcome.files.extend(write_mesh(mesh, folder / f"{name}{fmt.extension}", fmt, None, name, meters_per_unit))
    if settings.report:
        outcome.report = folder / f"{name}_report.md"
        outcome.report.write_text(report_markdown(result, settings, outcome, name, fragment_name), encoding="utf-8")
    report(1.0, "Export finished")
    return outcome


def report_markdown(result: DEMeshResult, export: DEExportSettings, outcome: DEExportOutcome, name: str, fragment_name: str) -> str:
    """The report beside the export: sampling settings, both meshes' checks, the files."""
    s = result.settings
    c = s.bounds.center
    lines = [f"# {name} — mesh from the distance estimator", "",
             f"Fragment: **{fragment_name or '—'}**  ·  grid {'×'.join(map(str, result.grid_shape))}  ·  voxel {result.voxel_size:.5g} units", "",
             "## Sampling", "",
             f"resolution {s.resolution}, box centre ({c[0]:.4g}, {c[1]:.4g}, {c[2]:.4g}) size {s.bounds.size:.4g}, "
             f"threshold {s.threshold_voxels:g} voxels, colours {'on' if s.colors else 'off'}, clean-up *{s.clean}* "
             f"({s.smooth_iterations} smoothing passes, target {s.target_faces:,} faces)", ""]
    for title, rep in (("Full mesh", result.full_report), ("Clean mesh", result.clean_report)):
        lines += _report_table(title, rep)
    lines += ["## Export", "", f"form *{export.form}*, units *{export.units}*" + (f" ({export.size_mm:g} mm)" if export.units == "mm" else ""), ""]
    lines += [f"* `{p.name}`" for p in outcome.files]
    if outcome.notes:
        lines += ["", *[f"_{n}_" for n in outcome.notes]]
    lines += ["", "Times: " + ", ".join(f"{k} {v:.1f} s" for k, v in result.seconds.items()), ""]
    return "\n".join(lines)


def _report_table(title: str, rep: MeshReport) -> list[str]:
    size = rep.size
    lines = [f"## {title}", "", "| | |", "|---|---|", f"| vertices | {rep.vertices:,} |", f"| faces | {rep.faces:,} |",
             f"| pieces | {rep.components} |", f"| open edges | {rep.boundary_edges} |", f"| non-manifold edges | {rep.nonmanifold_edges} |",
             f"| watertight | {'yes' if rep.watertight else 'no'} |", f"| volume | {rep.volume:.5g} units³ |",
             f"| size | {size[0]:.4g} × {size[1]:.4g} × {size[2]:.4g} units |"]
    if rep.thin_wall is not None:
        lines.append(f"| thinnest wall (estimate) | {rep.thin_wall:.4g} units |")
    lines += ["", f"**{rep.recommendation()}**", ""]
    if rep.notes:
        lines += ["Clean-up: " + "; ".join(rep.notes), ""]
    return lines


__all__ = ["DEMeshSettings", "DEMeshResult", "DEExportSettings", "DEExportOutcome", "CLEAN_LEVELS", "MAX_RESOLUTION", "MAX_SPARSE_RESOLUTION",
           "build_de_mesh_sparse", "active_blocks", "block_mesh",
           "grid_from_probe", "vertex_colors", "build_de_mesh", "export_de_mesh", "report_markdown", "estimated_bytes"]
