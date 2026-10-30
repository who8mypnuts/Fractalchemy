"""Points → voxels → isosurface → clean mesh, and the export of the result. Qt-free; the 3D Editor's jobs call this.

Three stages so the UI can redo only what changed: `capture_stage()` (the chaos game and the raw voxel grid —
the slow part, cached while the fractal and the capture settings stay), `build_mesh()` (filters, normalisation,
the isosurface, the clean-up, the reports — fast enough to re-run when the threshold moves) and
`export_result()` (units, materials, the files, the Blender script, the report).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

import numpy as np
from scipy import ndimage

from ..fractal.scene import Flame
from ..scene3d.model import ExportSettings, MeshSettings, Scene3D
from .capture import capture_points
from .holon import InstanceSet, bake_instances, scene_instance_sets
from .io.blender import write_blender_instances, write_blender_script
from .io.gltf import write_glb_instances
from .io.usd import write_usd_instances
from .io.write import export_format, write_mesh
from .isosurface import surface_nets
from .mesh import AGGRESSIVE_CLEAN, CleanSettings, Mesh, MeshReport, clean, remesh
from .uv import bake_vertex_colors, with_uvs
from .voxelize import VoxelGrid, dilate, erode, log_histogram, smooth, voxelize

Progress = Callable[[float, str], None]
Cancelled = Callable[[], bool]


@dataclass
class VoxelStage:
    """The capture and the raw voxel grid (what the filters and the isosurface start from)."""
    points: int
    grid: VoxelGrid
    seconds: float
    resolution: int
    seed: int
    colors: bool

    def matches(self, settings: MeshSettings) -> bool:
        """True when `settings` would produce this same stage again."""
        return (self.resolution == settings.resolution and self.seed == settings.seed and self.colors == settings.colors
                and self.points >= settings.points)


@dataclass
class MeshResult:
    """Everything meshing produced.

    Attributes:
        settings: The settings used (a copy).
        points: Points captured.
        grid_shape: Voxels on each axis (padding included).
        voxel_size: Voxel side in world units.
        normalized: The filtered, normalized density (the histogram's data; `threshold` applies to it).
        scale: Density that normalized to 1.
        histogram: (bin edges, counts) of the occupied voxels, log-spaced.
        inside: Occupancy at the threshold (`normalized > threshold`), for the thin-wall estimate and the remesh.
        full: The isosurface as extracted.
        clean: After the clean-up pipeline at the chosen level.
        full_report, clean_report: Their reports.
        seconds: Time per stage.
    """
    settings: MeshSettings
    points: int
    grid_shape: tuple[int, int, int]
    voxel_size: float
    normalized: np.ndarray
    scale: float
    histogram: tuple[np.ndarray, np.ndarray]
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


def capture_stage(flame: Flame, settings: MeshSettings, cancelled: Cancelled | None = None, progress: Progress | None = None,
                  threads: int = 1) -> VoxelStage | None:
    """Run the chaos game and voxelise (None when cancelled)."""
    started = time.perf_counter()
    report = progress or (lambda fraction, message: None)
    report(0.0, "Capturing points")
    cloud = capture_points(flame, settings.points, settings.seed, threads, cancelled=cancelled,
                           progress=lambda f: report(f * 0.8, f"Capturing points ({int(f * 100)} %)"))
    if cloud is None:
        return None
    report(0.85, "Building the voxel grid")
    grid = voxelize(cloud, settings.resolution, with_color=settings.colors)
    report(1.0, "Voxel grid ready")
    return VoxelStage(len(cloud), grid, time.perf_counter() - started, settings.resolution, settings.seed, settings.colors)


def clean_settings_for(settings: MeshSettings) -> CleanSettings:
    """The clean-up pipeline's settings for the chosen level."""
    if settings.clean == "aggressive" or settings.clean == "remesh":
        base = AGGRESSIVE_CLEAN
        return CleanSettings(weld=True, min_piece_faces=max(settings.min_piece_faces, base.min_piece_faces), keep_largest=1,
                             fill_holes_up_to=settings.fill_holes, smooth_iterations=settings.smooth_iterations,
                             target_faces=settings.target_faces, orient=True)
    return CleanSettings(weld=True, min_piece_faces=settings.min_piece_faces, keep_largest=0, fill_holes_up_to=0,
                         smooth_iterations=settings.smooth_iterations, target_faces=settings.target_faces, orient=True)


def filtered_grid(stage: VoxelStage, settings: MeshSettings) -> VoxelGrid:
    grid = stage.grid
    if settings.dilate:
        grid = dilate(grid, settings.dilate)
    if settings.erode:
        grid = erode(grid, settings.erode)
    if settings.smoothing > 0:
        grid = smooth(grid, settings.smoothing)
    return grid


def build_mesh(stage: VoxelStage, settings: MeshSettings, cancelled: Cancelled | None = None, progress: Progress | None = None
               ) -> MeshResult | None:
    """Filters, isosurface, clean-up and reports from a captured stage (None when cancelled)."""
    report = progress or (lambda fraction, message: None)
    cancelled = cancelled or (lambda: False)
    seconds: dict[str, float] = {"capture": stage.seconds}
    t = time.perf_counter()
    report(0.0, "Filtering the density")
    grid = filtered_grid(stage, settings)
    normalized, scale = grid.normalized()
    histogram = log_histogram(normalized)
    inside = normalized > settings.threshold
    seconds["filter"] = time.perf_counter() - t
    if cancelled():
        return None
    t = time.perf_counter()
    report(0.2, "Extracting the surface")
    full = surface_nets(grid, settings.threshold, normalized, with_color=settings.colors)
    seconds["isosurface"] = time.perf_counter() - t
    if cancelled():
        return None
    t = time.perf_counter()
    report(0.55, "Checking the full mesh")
    full_report = full.report()
    if cancelled():
        return None
    report(0.65, f"Cleaning ({settings.clean})")

    def decimation_progress(fraction: float, faces: int) -> None:
        report(0.7 + 0.28 * fraction, f"Decimating ({faces:,} faces)")
        if cancelled():
            raise _Cancelled()

    try:
        cleaned, clean_report = _clean_stage(settings, full, grid, inside, decimation_progress)
    except _Cancelled:
        return None
    seconds["clean"] = time.perf_counter() - t
    report(1.0, "Mesh ready")
    return MeshResult(settings.copy(), stage.points, grid.shape, grid.spacing, normalized, scale, histogram, inside,
                      full, cleaned, full_report, clean_report, seconds)


class _Cancelled(Exception):
    """Raised from the decimation progress callback to stop the clean-up."""


def _clean_stage(settings: MeshSettings, full: Mesh, grid: VoxelGrid, inside: np.ndarray, decimation_progress) -> tuple[Mesh, MeshReport]:
    """The clean mesh at the chosen level (the remesh level rebuilds the surface from the closed voxel occupancy)."""
    if settings.clean == "remesh":
        solid = remesh(inside, grid.origin, grid.spacing)
        soft = ndimage.gaussian_filter(solid.astype(np.float32), 1.0, mode="constant")
        source = VoxelGrid(soft, grid.color, grid.origin, grid.spacing)
        base = surface_nets(source, 0.5, soft, with_color=settings.colors)
        cleaned, clean_report = clean(base, clean_settings_for(settings), grid.spacing, solid, progress=decimation_progress)
        clean_report.notes.insert(0, "remeshed from the voxel occupancy (closed, cavities filled, largest piece)")
        return cleaned, clean_report
    return clean(full, clean_settings_for(settings), grid.spacing, inside, progress=decimation_progress)


@dataclass
class ExportOutcome:
    """What an export wrote."""
    files: list[Path] = field(default_factory=list)
    report: Path | None = None
    notes: list[str] = field(default_factory=list)
    seconds: float = 0.0


def export_result(result: MeshResult, scene: Scene3D, settings: ExportSettings, folder: Path, name: str,
                  progress: Progress | None = None) -> ExportOutcome:
    """Write the chosen form of the mesh in every chosen format (+ texture, Blender script, report) into `folder`.

    Raises:
        ValueError: When no format is chosen or a format is unavailable.
        OSError: When a file cannot be written.
    """
    started = time.perf_counter()
    report = progress or (lambda fraction, message: None)
    if not settings.formats:
        raise ValueError("choose at least one format")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    outcome = ExportOutcome()
    mesh = result.mesh(settings.form)
    if mesh.face_count == 0:
        raise ValueError("the mesh is empty — nothing to export")
    meters_per_unit = 1.0
    if settings.units == "mm":
        mesh = mesh.scaled_to(settings.size_mm)
        meters_per_unit = 0.001
        outcome.notes.append(f"scaled so the longest side is {settings.size_mm:g} mm (USD metersPerUnit = 0.001; other formats carry millimetres)")
    texture_path = None
    if settings.materials == "none":
        mesh = mesh.copy()
        mesh.colors = None
        mesh.uvs = None
    elif settings.materials == "texture":
        if mesh.colors is None:
            outcome.notes.append("no vertex colours to bake: exported without a texture")
        else:
            report(0.05, "Unwrapping and baking the texture")
            mesh = with_uvs(mesh, settings.uv_mode)
            texture = bake_vertex_colors(mesh, settings.texture_size)
            texture_path = folder / f"{name}_color.png"
            from PIL import Image
            Image.fromarray(texture).save(texture_path)
            outcome.files.append(texture_path)
    formats = [export_format(key) for key in settings.formats]
    for index, fmt in enumerate(formats):
        report(0.2 + 0.6 * index / max(1, len(formats)), f"Writing {fmt.label}")
        outcome.files.extend(write_mesh(mesh, folder / f"{name}{fmt.extension}", fmt, texture_path, name, meters_per_unit))
    if settings.blender:
        report(0.85, "Writing the Blender script")
        asset = next((p for p in outcome.files if p.suffix in (".glb", ".ply", ".obj", ".usdc", ".usda", ".stl")), None)
        if asset is None:
            asset = write_mesh(mesh, folder / f"{name}_blender.glb", "glb", texture_path, name)[0]
            outcome.files.append(asset)
        lo, hi = mesh.bounds()
        outcome.files.extend(write_blender_script(scene, folder / f"{name}_blender.py", asset, (lo + hi) / 2.0, float((hi - lo).max()),
                                                  name, texture_path))
    if settings.report:
        report(0.95, "Writing the report")
        outcome.report = folder / f"{name}_report.md"
        outcome.report.write_text(report_markdown(result, scene, settings, outcome, name), encoding="utf-8")
    outcome.seconds = time.perf_counter() - started
    report(1.0, "Export finished")
    return outcome


def instance_colour(instancer, palette: np.ndarray | None, instances: InstanceSet) -> tuple[tuple[float, float, float] | None, np.ndarray | None]:
    """(one colour for the whole instancer or None, per-instance colours `(N, 3)` or None) by the instancer's colour mode."""
    if instancer.color_mode == "fixed":
        return tuple(c / 255.0 for c in instancer.material.color), None
    if instancer.color_mode == "palette" and palette is not None and len(instances):
        return None, np.asarray(palette, dtype=np.float64)[instances.colors] / 255.0
    return None, None


def baked_scene_mesh(scene: Scene3D, max_faces: int = 5_000_000) -> Mesh:
    """Every visible instancer baked into one mesh, coloured by the instancers' colour modes."""
    sets = scene_instance_sets(scene)
    if not sets:
        return Mesh.empty()
    palette = np.asarray(scene.fractal.palette) if scene.fractal is not None else None
    parts = []
    budget = max(1, max_faces // len(sets))
    for _index, inst, instances, mesh in sets:
        baked = bake_instances(mesh, instances, budget)
        if baked.face_count == 0:
            continue
        fixed, per_instance = instance_colour(inst, palette, instances)
        if fixed is not None:
            baked.colors = np.tile(np.asarray(fixed, dtype=np.float32), (baked.vertex_count, 1))
        elif per_instance is not None and baked.vertex_count:
            kept = min(len(instances), baked.vertex_count // mesh.vertex_count)
            order = np.argsort(-instances.scales, kind="stable")[:kept] if len(instances) > kept else np.arange(kept)
            baked.colors = np.repeat(per_instance[np.sort(order)], mesh.vertex_count, axis=0).astype(np.float32)
        parts.append(baked)
    if not parts:
        return Mesh.empty()
    offsets = np.cumsum([0] + [p.vertex_count for p in parts[:-1]])
    out = Mesh(np.concatenate([p.vertices for p in parts]), np.concatenate([p.faces + o for p, o in zip(parts, offsets)]),
               np.concatenate([p.normals for p in parts]) if all(p.normals is not None for p in parts) else None,
               np.concatenate([p.colors for p in parts]) if all(p.colors is not None for p in parts) else None)
    return out


def export_instances(scene: Scene3D, settings: ExportSettings, folder: Path, name: str, progress: Progress | None = None) -> ExportOutcome:
    """Write the instancers: instanced files (USD PointInstancer, glTF EXT_mesh_gpu_instancing, the Blender script with
    Geometry Nodes) for the formats that can, the baked mesh for the rest — or everything baked when `settings.subject`
    is `baked`.

    Raises:
        ValueError: When there are no visible instancers or no format.
        OSError: When a file cannot be written.
    """
    started = time.perf_counter()
    report = progress or (lambda fraction, message: None)
    if not settings.formats:
        raise ValueError("choose at least one format")
    sets = scene_instance_sets(scene)
    if not sets:
        raise ValueError("no visible instancer with an asset — add one on the Instances tab")
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    outcome = ExportOutcome()
    palette = np.asarray(scene.fractal.palette) if scene.fractal is not None else None
    # units
    factor, meters_per_unit = 1.0, 1.0
    centres = np.concatenate([s.positions for _i, _inst, s, _m in sets])
    reach = np.concatenate([s.scales for _i, _inst, s, _m in sets]) / 2.0
    lo = (centres - reach[:, None]).min(axis=0)
    hi = (centres + reach[:, None]).max(axis=0)
    extent = float((hi - lo).max()) or 1.0
    if settings.units == "mm":
        factor = settings.size_mm / extent
        meters_per_unit = 0.001
        outcome.notes.append(f"scaled so the whole scene spans {settings.size_mm:g} mm")
    entries = []
    for _index, inst, instances, mesh in sets:
        fixed, per_instance = instance_colour(inst, palette, instances)
        entries.append((inst.name, mesh, instances.positions * factor, instances.quaternions(), instances.scales * factor, fixed, per_instance, inst))
    baked = None
    formats = [export_format(key) for key in settings.formats]
    for index, fmt in enumerate(formats):
        report(0.1 + 0.7 * index / max(1, len(formats)), f"Writing {fmt.label}")
        target = folder / f"{name}{fmt.extension}"
        if settings.subject == "instances" and fmt.key == "glb":
            outcome.files.extend(write_glb_instances([(label, m, p, q, sc, fixed) for label, m, p, q, sc, fixed, _pc, _inst in entries], target, name))
        elif settings.subject == "instances" and fmt.key in ("usda", "usdc", "usdz"):
            outcome.files.extend(write_usd_instances([(label, m, p, q, sc, pc) for label, m, p, q, sc, _fixed, pc, _inst in entries], target, name, meters_per_unit))
        else:
            if baked is None:
                report(0.1 + 0.7 * index / max(1, len(formats)), "Baking the instances into one mesh")
                baked = baked_scene_mesh(scene)
                if baked.face_count == 0:
                    raise ValueError("the instances bake to an empty mesh")
                if factor != 1.0:
                    baked = baked.transformed(scale=factor)
                if settings.subject == "instances":
                    outcome.notes.append(f"{fmt.label} cannot carry instances: the baked mesh was written instead")
            outcome.files.extend(write_mesh(baked, target, fmt, None, name, meters_per_unit))
    if settings.blender:
        report(0.85, "Writing the Blender script")
        if settings.subject == "instances":
            asset_files = []
            for label, m, _p, _q, _sc, _fixed, _pc, _inst in entries:
                asset_path = write_mesh(m, folder / f"{name}_asset_{_safe(label)}.glb", "glb", None, label)[0]
                outcome.files.append(asset_path)
                asset_files.append(asset_path.name)
            centre = (lo + hi) / 2.0 * factor
            outcome.files.extend(write_blender_instances(scene, folder / f"{name}_blender.py",
                                                         [(label, asset_files[i], p, q, sc, fixed, inst.material)
                                                          for i, (label, _m, p, q, sc, fixed, _pc, inst) in enumerate(entries)],
                                                         centre, extent * factor, name))
        else:
            if baked is None:
                baked = baked_scene_mesh(scene)
                if factor != 1.0:
                    baked = baked.transformed(scale=factor)
            asset = next((p for p in outcome.files if p.suffix in (".glb", ".ply", ".obj", ".usdc", ".usda", ".stl")), None)
            if asset is None:
                asset = write_mesh(baked, folder / f"{name}_blender.glb", "glb", None, name)[0]
                outcome.files.append(asset)
            blo, bhi = baked.bounds()
            outcome.files.extend(write_blender_script(scene, folder / f"{name}_blender.py", asset, (blo + bhi) / 2.0, float((bhi - blo).max()), name))
    if settings.report:
        report(0.95, "Writing the report")
        outcome.report = folder / f"{name}_report.md"
        outcome.report.write_text(instances_report_markdown(scene, settings, sets, outcome, name), encoding="utf-8")
    outcome.seconds = time.perf_counter() - started
    report(1.0, "Export finished")
    return outcome


def _safe(label: str) -> str:
    import re
    return re.sub(r"[^A-Za-z0-9_-]+", "_", label).strip("_") or "asset"


def instances_report_markdown(scene: Scene3D, export: ExportSettings, sets: list, outcome: ExportOutcome, name: str) -> str:
    lines = [f"# {name} — holon IFS export", "", f"Fractal: **{scene.fractal.name if scene.fractal else '—'}**  ·  "
             f"{sum(len(s) for _i, _inst, s, _m in sets):,} instances in {len(sets)} instancer{'s' if len(sets) != 1 else ''}", "",
             "## Instancers", "", "| instancer | asset | source | mode | instances | faces each | size range |", "|---|---|---|---|---|---|---|"]
    for _index, inst, instances, mesh in sets:
        lines.append(f"| {inst.name} | {inst.asset} | {inst.source} | {inst.mode} (depth {inst.depth}) | {len(instances):,} | {mesh.face_count:,} | "
                     f"{instances.scales.min():.4g} – {instances.scales.max():.4g} |")
    lines += ["", "## Export", "", f"subject *{export.subject}*, units *{export.units}*" + (f" ({export.size_mm:g} mm)" if export.units == "mm" else ""), ""]
    lines += [f"* `{p.name}`" for p in outcome.files]
    if outcome.notes:
        lines += ["", *[f"_{n}_" for n in outcome.notes]]
    return "\n".join(lines) + "\n"


def report_markdown(result: MeshResult, scene: Scene3D, export: ExportSettings, outcome: ExportOutcome, name: str) -> str:
    """The mesh report beside the export: settings, the full and clean meshes' checks, the files."""
    s = result.settings
    lines = [f"# {name} — 3D mesh export", "", f"Fractal: **{scene.fractal.name if scene.fractal else '—'}**  ·  "
             f"{result.points:,} points  ·  grid {'×'.join(map(str, result.grid_shape))}  ·  voxel {result.voxel_size:.5g} units", "",
             "## Meshing settings", "",
             f"resolution {s.resolution}, threshold {s.threshold:g}, smoothing {s.smoothing:g} voxels, dilate {s.dilate}, erode {s.erode}, "
             f"colours {'on' if s.colors else 'off'}, clean-up *{s.clean}* (min piece {s.min_piece_faces} faces, holes ≤ {s.fill_holes} edges, "
             f"{s.smooth_iterations} smoothing passes, target {s.target_faces:,} faces)", ""]
    for title, rep in (("Full mesh", result.full_report), ("Clean mesh", result.clean_report)):
        size = rep.size
        lines += [f"## {title}", "", "| | |", "|---|---|", f"| vertices | {rep.vertices:,} |", f"| faces | {rep.faces:,} |",
                  f"| pieces | {rep.components} |", f"| open edges | {rep.boundary_edges} |", f"| non-manifold edges | {rep.nonmanifold_edges} |",
                  f"| orientation | {'consistent' if rep.consistent else 'inconsistent'} |", f"| watertight | {'yes' if rep.watertight else 'no'} |",
                  f"| volume | {rep.volume:.5g} units³ |", f"| area | {rep.area:.5g} units² |",
                  f"| size | {size[0]:.4g} × {size[1]:.4g} × {size[2]:.4g} units |"]
        if rep.thin_wall is not None:
            lines.append(f"| thinnest wall (lower-bound estimate) | {rep.thin_wall:.4g} units |")
        lines += ["", f"**{rep.recommendation()}**", ""]
        if rep.notes:
            lines += ["Clean-up: " + "; ".join(rep.notes), ""]
    lines += ["## Export", "", f"form *{export.form}*, materials *{export.materials}*"
              + (f" ({export.uv_mode} UVs, {export.texture_size} px texture)" if export.materials == "texture" else "")
              + f", units *{export.units}*" + (f" ({export.size_mm:g} mm)" if export.units == "mm" else ""), ""]
    lines += [f"* `{p.name}`" for p in outcome.files]
    if outcome.notes:
        lines += ["", *[f"_{n}_" for n in outcome.notes]]
    lines += ["", "Times: " + ", ".join(f"{k} {v:.1f} s" for k, v in result.seconds.items()), ""]
    return "\n".join(lines)


__all__ = ["VoxelStage", "MeshResult", "ExportOutcome", "capture_stage", "build_mesh", "export_result", "report_markdown",
           "clean_settings_for", "filtered_grid", "export_instances", "baked_scene_mesh", "instances_report_markdown"]
