"""The "Fractal and Render Details" report written beside a rendered image.

One structured `Report` (sections of labelled items and tables) is built from the flame, the
settings and the `FinalResult`, then rendered three ways:

* **Markdown** and **HTML** for people: headings, two-column field tables, data tables.
* **Text** for pipelines: one `key<TAB>value` record per line, keys dotted and lower-case with no
  spaces (`render.samples_per_second`, `fractal.transforms.2.weight`), values in machine form
  (plain numbers, `true` / `false`, ISO timestamps), `#` for comment lines. So
  `grep '^timing\\.' render.txt | cut -f2` or `awk -F'\\t' '$1=="render.samples"'` just work, and a
  folder of reports can be tracked over time with ordinary tools.

Every item carries both a machine `value` and a human `display`, so the three outputs never
disagree about a number — they only format it differently.
"""

from __future__ import annotations

import html
import math
import os
import platform
import socket
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

import numpy as np

from .. import config
from ..fractal.scene import Flame, XForm
from ..fractal.variations import REGISTRY, canonical_name
from ..model.color import hue, luminance, rgb_to_hex, rgb_to_hsl
from .denoise import denoiser_kind
from .filters import filter_kind, make_taps
from .final_engine import FinalResult
from .final_settings import ENGINES, FinalRenderSettings, memory_budget_bytes, physical_memory_bytes
from .output import output_format

REPORT_FORMATS: tuple[tuple[str, str, str], ...] = (("md", "Markdown (.md)", ".md"), ("txt", "Text (.txt)", ".txt"),
                                                    ("html", "HTML (.html)", ".html"))
HUE_NAMES = ("red", "orange", "yellow", "chartreuse", "green", "spring green", "cyan", "azure", "blue", "violet",
             "magenta", "rose")


def report_extension(key: str) -> str:
    """File suffix for a report format key (unknown keys mean Markdown)."""
    return next((ext for k, _label, ext in REPORT_FORMATS if k == key), ".md")


# --- document model ----------------------------------------------------------------------------
@dataclass
class Item:
    """One labelled fact.

    Attributes:
        key: Machine name (no spaces).
        label: Human label.
        value: Machine value (number, bool, str, list).
        display: Human rendering; defaults to the machine value with units, if given.
    """
    key: str
    label: str
    value: object
    display: str | None = None

    @property
    def text(self) -> str:
        """Human text (booleans read as yes / no)."""
        if self.display is not None:
            return self.display
        if isinstance(self.value, bool):
            return "yes" if self.value else "no"
        return machine_text(self.value)


@dataclass
class Table:
    """Rows of facts sharing columns.

    Attributes:
        key: Machine name ("" when the table is the section's only content, so rows sit directly under the section).
        title: Human title.
        columns: (key, label) per column.
        rows: Dicts keyed by column key; values may be (machine, display) pairs or plain values.
        id_key: Column whose value names the row in text output (else the 1-based row number).
    """
    key: str
    title: str
    columns: list[tuple[str, str]]
    rows: list[dict] = field(default_factory=list)
    id_key: str | None = None


@dataclass
class Section:
    """A titled group of items and tables."""
    key: str
    title: str
    items: list[Item] = field(default_factory=list)
    tables: list[Table] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def add(self, key: str, label: str, value: object, display: str | None = None) -> None:
        """Append an item."""
        self.items.append(Item(key, label, value, display))


@dataclass
class Report:
    """The whole document."""
    title: str
    generated: datetime
    sections: list[Section] = field(default_factory=list)


def machine_text(value: object) -> str:
    """Pipeline-friendly rendering of a value: numbers unadorned, booleans lower-case, lists comma-joined."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float):
        if math.isnan(value) or math.isinf(value):
            return str(value)
        return f"{value + 0.0:.10g}".replace("-0", "0") if value == 0 else f"{value:.10g}"
    if isinstance(value, (list, tuple)):
        return ", ".join(machine_text(v) for v in value)
    if isinstance(value, datetime):
        return value.isoformat(timespec="seconds")
    if value is None:
        return ""
    return str(value)


def _cell(value) -> tuple[object, str]:
    return value if isinstance(value, tuple) and len(value) == 2 and isinstance(value[1], str) else (value, machine_text(value))


# --- helpers -----------------------------------------------------------------------------------
def human_bytes(n: float) -> str:
    """'1.23 GB' style."""
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(n) < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1000.0
    return f"{n:.2f} TB"


def human_count(n: float) -> str:
    """'12.3 M' / '4.56 G' style."""
    for unit, scale in (("G", 1e9), ("M", 1e6), ("k", 1e3)):
        if abs(n) >= scale:
            return f"{n / scale:.3g} {unit}"
    return f"{n:.0f}"


def human_seconds(seconds: float) -> str:
    """'1 h 02 min 03 s' style, always with the exact seconds in brackets below a minute."""
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f} s"
    minutes, sec = divmod(int(round(seconds)), 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min {sec:02d} s" if hours else f"{minutes} min {sec:02d} s"


def _affine_text(coefs) -> str:
    return "[" + ", ".join(f"{c:.6g}" for c in coefs) + "]"


def _gcd_aspect(width: int, height: int) -> str:
    g = math.gcd(max(1, width), max(1, height))
    a, b = width // g, height // g
    return f"{a}:{b}" if a <= 64 and b <= 64 else f"{width / height:.4f}:1"


def _hue_name(rgb) -> str:
    return HUE_NAMES[int(hue(rgb) * 12 + 0.5) % 12]   # hue() is 0..1


# --- building -----------------------------------------------------------------------------------
def build_report(flame: Flame, settings: FinalRenderSettings, result: FinalResult, image_path: Path | None,
                 sidecar: Path | None = None, source: str = "", report_path: Path | None = None) -> Report:
    """Gather every fact about the render and the fractal into a `Report`."""
    now = datetime.now().astimezone()
    report = Report(f"{config.APP_NAME} render report — {flame.name}", now)
    report.sections.append(_output_section(settings, result, image_path, sidecar, report_path, now))
    report.sections.append(_render_section(settings, result))
    report.sections.append(_timing_section(settings, result))
    report.sections.append(_system_section(result))
    report.sections.append(_fractal_section(flame, source))
    report.sections.append(_camera_section(flame, settings))
    report.sections.append(_coloring_section(flame))
    report.sections.append(_palette_section(flame))
    report.sections.append(_transforms_section(flame))
    report.sections.append(_variations_section(flame))
    xaos = _xaos_section(flame)
    if xaos is not None:
        report.sections.append(xaos)
    if result.notes:
        report.sections.append(Section("notes", "Notes", notes=list(result.notes)))
    return report


def _output_section(s: FinalRenderSettings, r: FinalResult, image_path, sidecar, report_path, now) -> Section:
    sec = Section("output", "Output")
    fmt = output_format(s.output_format)
    sec.add("file", "Image file", str(image_path) if image_path else "", str(image_path) if image_path else "not saved")
    if image_path is not None and Path(image_path).exists():
        size = Path(image_path).stat().st_size
        sec.add("file_bytes", "File size", size, f"{human_bytes(size)} ({size:,} bytes)")
    sec.add("format", "Format", fmt.key, fmt.label)
    sec.add("width", "Width", s.width, f"{s.width:,} px")
    sec.add("height", "Height", s.height, f"{s.height:,} px")
    sec.add("megapixels", "Megapixels", round(s.width * s.height / 1e6, 3), f"{s.width * s.height / 1e6:.2f} Mpx")
    sec.add("aspect_ratio", "Aspect ratio", round(s.width / max(1, s.height), 6), _gcd_aspect(s.width, s.height))
    depth = s.depth if fmt.depth16 else 8
    sec.add("bits_per_channel", "Bits per channel", depth)
    sec.add("transparent", "Transparent background", bool(s.transparent and fmt.alpha))
    if fmt.lossy:
        lossless = bool(s.lossless and fmt.lossless_option)
        sec.add("lossless", "Lossless", lossless)
        if not lossless:
            sec.add("quality_percent", "Encoding quality", s.lossy_quality, f"{s.lossy_quality} %")
    sec.add("parameters_embedded", "Parameters embedded in the image", bool(s.embed_parameters))
    sec.add("parameters_file", "Parameter file", str(sidecar) if sidecar else "", str(sidecar) if sidecar else "none")
    sec.add("details_file", "Details file", str(report_path) if report_path else "", str(report_path) if report_path else "")
    sec.add("complete", "Render completed", bool(r.complete), "yes" if r.complete else "no — stopped early, partial image")
    sec.add("written_at", "Written", now, now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    sec.add("software", "Software", f"{config.APP_NAME} {config.APP_VERSION}")
    return sec


def _render_section(s: FinalRenderSettings, r: FinalResult) -> Section:
    sec = Section("render", "Render settings")
    kind = filter_kind(s.filter_kind)
    taps = make_taps(kind, s.filter_radius, s.oversample)
    bw, bh = s.bucket_size
    sec.add("density", "Density (samples per pixel)", s.quality, f"{s.quality:g}")
    sec.add("oversample", "Oversample", s.oversample, f"{s.oversample} × {s.oversample} buckets per pixel")
    sec.add("bucket_width", "Histogram width", bw, f"{bw:,} buckets")
    sec.add("bucket_height", "Histogram height", bh, f"{bh:,} buckets")
    sec.add("buckets", "Histogram buckets", bw * bh, f"{bw * bh:,} ({human_count(bw * bh)})")
    sec.add("filter", "Reconstruction filter", kind.key, kind.label)
    sec.add("filter_radius", "Filter radius", s.filter_radius, f"{s.filter_radius:g} px")
    sec.add("filter_taps", "Filter taps per axis", int(taps.offsets.size))
    sec.add("filter_reach", "Filter reach", taps.reach, f"{taps.reach} bucket{'s' if taps.reach != 1 else ''} beyond the pixel block")
    dn = denoiser_kind(s.denoiser)
    sec.add("denoiser", "Denoiser", dn.key, dn.label)
    if dn.key == "density":
        sec.add("de_max_radius", "Density estimation max radius", s.de_max_radius, f"{s.de_max_radius:g} px")
        sec.add("de_min_radius", "Density estimation min radius", s.de_min_radius, f"{s.de_min_radius:g} px")
        sec.add("de_curve", "Density estimation curve", s.de_curve, f"{s.de_curve:g}")
    elif dn.key != "none":
        sec.add("denoise_strength", "Denoiser strength", s.denoise_strength, f"{s.denoise_strength:g} / 100")
    engine_label = next((label for key, label in ENGINES if key == s.engine), s.engine)
    sec.add("engine_requested", "Engine requested", s.engine, engine_label)
    sec.add("engine_used", "Engine used", r.engine)
    sec.add("engine_kind", "Engine kind", "gpu" if r.engine.startswith("GPU") else "cpu")
    if not r.engine.startswith("GPU"):
        sec.add("cpu_workers", "CPU workers", _workers_used(r.engine, s.cpu_threads))
    sec.add("memory_limit_mb", "Memory limit setting", s.memory_limit_mb, f"{s.memory_limit_mb} MB" if s.memory_limit_mb else "automatic")
    budget = memory_budget_bytes(s)
    sec.add("memory_budget_bytes", "Histogram memory budget", budget, human_bytes(budget))
    plan = r.plan
    if plan is not None:
        columns = len({t.x0 for t in plan.tiles})
        rows = len({t.y0 for t in plan.tiles})
        sec.add("tiles", "Tiles (slices)", plan.count, f"{plan.count} ({columns} × {rows})")
        sec.add("tile_columns", "Tile columns", columns)
        sec.add("tile_rows", "Tile rows", rows)
        sec.add("tiles_rendered", "Tiles rendered", len(r.tiles))
        sec.add("gutter", "Tile gutter", plan.tiles[0].gutter, f"{plan.tiles[0].gutter} buckets")
        sec.add("tile_peak_buckets", "Largest tile", max(t.buckets for t in plan.tiles), f"{max(t.buckets for t in plan.tiles):,} buckets")
        sec.add("tile_peak_bytes", "Largest tile memory", plan.peak_bytes, human_bytes(plan.peak_bytes))
        sec.add("bytes_per_bucket", "Host bytes per bucket", plan.bytes_per_bucket)
    sec.add("samples_per_tile", "Samples per tile (target)", s.samples_per_tile, human_count(s.samples_per_tile))
    sec.add("samples_planned", "Samples planned", s.samples_per_tile * (plan.count if plan else 1),
            human_count(s.samples_per_tile * (plan.count if plan else 1)))
    sec.add("fuse", "Fuse (warm-up iterations)", s.fuse)
    sec.add("seed", "Random seed", s.seed)
    sec.add("save_incomplete", "Save incomplete renders", bool(s.save_incomplete))
    return sec


def _workers_used(engine_name: str, setting: int) -> int:
    digits = "".join(ch for ch in engine_name.split(",")[-1] if ch.isdigit())
    return int(digits) if digits else (setting or os.cpu_count() or 1)


def _timing_section(s: FinalRenderSettings, r: FinalResult) -> Section:
    sec = Section("timing", "Timing and statistics")
    started = datetime.fromtimestamp(r.started_at).astimezone() if r.started_at else None
    finished = datetime.fromtimestamp(r.finished_at).astimezone() if r.finished_at else None
    wall = (r.finished_at - r.started_at) if r.started_at and r.finished_at else r.seconds + r.paused_seconds
    sampling = sum(t.render_seconds for t in r.tiles)
    filtering = sum(t.filter_seconds for t in r.tiles)
    overhead = max(0.0, r.seconds - sampling - filtering - r.denoise_seconds)
    pixels = s.width * s.height
    if started:
        sec.add("started_at", "Started", started, started.strftime("%Y-%m-%d %H:%M:%S %Z"))
    if finished:
        sec.add("finished_at", "Finished", finished, finished.strftime("%Y-%m-%d %H:%M:%S %Z"))
    sec.add("wall_seconds", "Wall-clock time", round(wall, 3), human_seconds(wall))
    sec.add("active_seconds", "Active time (pauses excluded)", round(r.seconds, 3), human_seconds(r.seconds))
    sec.add("paused_seconds", "Paused", round(r.paused_seconds, 3), human_seconds(r.paused_seconds))
    sec.add("sampling_seconds", "Sampling (chaos game)", round(sampling, 3), f"{human_seconds(sampling)} ({_pct(sampling, r.seconds)})")
    sec.add("filtering_seconds", "Filtering and tone mapping", round(filtering, 3), f"{human_seconds(filtering)} ({_pct(filtering, r.seconds)})")
    sec.add("denoising_seconds", "Denoising", round(r.denoise_seconds, 3), f"{human_seconds(r.denoise_seconds)} ({_pct(r.denoise_seconds, r.seconds)})")
    sec.add("startup_seconds", "Engine start-up and overhead", round(overhead, 3), f"{human_seconds(overhead)} ({_pct(overhead, r.seconds)})")
    sec.add("samples", "Samples (iterations) run", r.samples, f"{r.samples:,} ({human_count(r.samples)})")
    sec.add("samples_per_pixel", "Samples per output pixel", round(r.samples / max(1, pixels), 3), f"{r.samples / max(1, pixels):.1f}")
    sec.add("samples_per_second", "Sampling speed", round(r.samples / sampling, 1) if sampling > 0 else 0,
            f"{human_count(r.samples / sampling)} samples/s" if sampling > 0 else "—")
    sec.add("samples_per_second_overall", "Overall speed (all phases)", round(r.samples / r.seconds, 1) if r.seconds > 0 else 0,
            f"{human_count(r.samples / r.seconds)} samples/s" if r.seconds > 0 else "—")
    sec.add("pixels_per_second", "Output pixels per second", round(pixels / r.seconds, 1) if r.seconds > 0 else 0,
            f"{human_count(pixels / r.seconds)} px/s" if r.seconds > 0 else "—")
    hits = sum(t.hits for t in r.tiles)
    sec.add("hits", "Hits (opacity-weighted points inside the tiles)", round(hits, 1), f"{human_count(hits)}")
    tile_samples = sum(t.samples for t in r.tiles)
    sec.add("hit_ratio", "Hit ratio (hits / samples)", round(hits / tile_samples, 6) if tile_samples else 0,
            f"{100 * hits / tile_samples:.1f} %" if tile_samples else "—")
    buckets = sum(t.buckets for t in r.tiles)
    lit = sum(t.lit_buckets for t in r.tiles)
    sec.add("lit_buckets", "Buckets hit at least once", lit, f"{lit:,} of {buckets:,} ({_pct(lit, buckets)})")
    sec.add("max_bucket_count", "Densest bucket", round(max((t.max_count for t in r.tiles), default=0.0), 1),
            f"{max((t.max_count for t in r.tiles), default=0.0):,.0f} hits")
    sec.add("mean_hits_per_lit_bucket", "Mean hits per lit bucket", round(hits / lit, 3) if lit else 0, f"{hits / lit:.2f}" if lit else "—")
    sec.tables.append(_tiles_table(r))
    return sec


def _pct(part: float, whole: float) -> str:
    return f"{100.0 * part / whole:.1f} %" if whole > 0 else "—"


def _tiles_table(r: FinalResult) -> Table:
    table = Table("tiles", "Tiles", [("index", "#"), ("x", "x"), ("y", "y"), ("width", "width"), ("height", "height"),
                                     ("buckets", "buckets"), ("samples", "samples"), ("render_seconds", "sampling s"),
                                     ("filter_seconds", "filter s"), ("samples_per_second", "samples/s"), ("hits", "hits"),
                                     ("hit_ratio", "hit ratio"), ("lit_fraction", "lit buckets"), ("max_count", "densest")],
                  id_key="index")
    for t in r.tiles:
        x, y, w, h = t.pixel_rect
        rate = t.samples / t.render_seconds if t.render_seconds > 0 else 0.0
        table.rows.append({
            "index": t.index + 1, "x": x, "y": y, "width": w, "height": h, "buckets": t.buckets,
            "samples": (t.samples, human_count(t.samples)), "render_seconds": (round(t.render_seconds, 3), f"{t.render_seconds:.1f}"),
            "filter_seconds": (round(t.filter_seconds, 3), f"{t.filter_seconds:.1f}"),
            "samples_per_second": (round(rate, 1), human_count(rate)), "hits": (round(t.hits, 1), human_count(t.hits)),
            "hit_ratio": (round(t.hits / t.samples, 6) if t.samples else 0, _pct(t.hits, t.samples)),
            "lit_fraction": (round(t.lit_buckets / t.buckets, 6) if t.buckets else 0, _pct(t.lit_buckets, t.buckets)),
            "max_count": (round(t.max_count, 1), f"{t.max_count:,.0f}"),
        })
    return table


def _system_section(r: FinalResult) -> Section:
    sec = Section("system", "System")
    sec.add("hostname", "Host", socket.gethostname())
    sec.add("platform", "Platform", platform.platform())
    sec.add("machine", "Machine", platform.machine())
    if platform.processor():
        sec.add("processor", "Processor", platform.processor())
    sec.add("cpu_count", "Logical CPUs", os.cpu_count() or 0)
    mem = physical_memory_bytes()
    sec.add("memory_bytes", "Physical memory", mem, human_bytes(mem))
    if r.engine.startswith("GPU"):
        sec.add("gpu", "GPU", r.engine[len("GPU ("):].split(", single")[0])
    sec.add("python", "Python", platform.python_version())
    sec.add("numpy", "numpy", np.__version__)
    try:
        import scipy
        sec.add("scipy", "scipy", scipy.__version__)
    except ImportError:
        sec.add("scipy", "scipy", "", "not installed (numpy blur fallback)")
    try:
        import moderngl
        sec.add("moderngl", "moderngl", moderngl.__version__)
    except ImportError:
        pass
    return sec


def _fractal_section(flame: Flame, source: str) -> Section:
    sec = Section("fractal", "Fractal")
    xforms = flame.xforms
    all_xforms = [*xforms, *([flame.final] if flame.final else [])]
    terms = [(canonical_name(n), w) for x in all_xforms for n, w in x.variations.items() if w != 0]
    names = {n for n, _ in terms}
    parametric = {n for n in names if n in REGISTRY and REGISTRY[n].params}
    sec.add("name", "Name", flame.name)
    sec.add("source", "Source", source, source or "not from a file")
    if flame.source_version:
        sec.add("source_version", "Written by", flame.source_version)
    sec.add("flame_width", "Flame's own width", flame.camera.width, f"{flame.camera.width} px")
    sec.add("flame_height", "Flame's own height", flame.camera.height, f"{flame.camera.height} px")
    sec.add("transforms", "Transforms", len(xforms))
    sec.add("active_transforms", "Transforms with positive weight", sum(1 for x in xforms if x.weight > 0))
    sec.add("final_transform", "Final transform", flame.final is not None)
    sec.add("total_weight", "Total weight", round(sum(x.weight for x in xforms), 6), f"{sum(x.weight for x in xforms):g}")
    sec.add("variation_terms", "Variation terms (all transforms)", len(terms))
    sec.add("distinct_variations", "Distinct variations", len(names))
    sec.add("parametric_variations", "Parametric variations", len(parametric), ", ".join(sorted(parametric)) or "none")
    sec.add("variations_mean_per_transform", "Variations per transform (mean)", round(len(terms) / max(1, len(all_xforms)), 3),
            f"{len(terms) / max(1, len(all_xforms)):.2f}")
    sec.add("pre_blur_transforms", "Transforms with pre_blur", sum(1 for x in all_xforms if x.variations.get("pre_blur")))
    sec.add("post_affine_transforms", "Transforms with a post affine", sum(1 for x in all_xforms if x.has_post()))
    sec.add("xaos", "Xaos in use", any(x.chaos is not None and any(c != 1 for c in x.chaos) for x in xforms))
    sec.add("invisible_transforms", "Invisible transforms (opacity 0)", sum(1 for x in xforms if x.opacity <= 0))
    sec.add("unsupported_variations", "Unsupported variations (ignored)", list(flame.unsupported), ", ".join(flame.unsupported) or "none")
    sec.add("palette_entries", "Palette entries", len(flame.palette))
    return sec


def _camera_section(flame: Flame, s: FinalRenderSettings) -> Section:
    sec = Section("camera", "Camera")
    cam = flame.camera
    at = cam.at_size(s.width, s.height)
    ppu = at.pixels_per_unit(s.width, s.height)
    span_w, span_h = s.width / ppu, s.height / ppu
    sec.add("center_x", "Centre x", cam.center[0], f"{cam.center[0]:.6g}")
    sec.add("center_y", "Centre y", cam.center[1], f"{cam.center[1]:.6g}")
    sec.add("scale", "Scale (pixels per unit at the flame's width)", cam.scale, f"{cam.scale:.6g}")
    sec.add("zoom", "Zoom (powers of two)", cam.zoom, f"{cam.zoom:g} (× {2 ** cam.zoom:.4g})")
    sec.add("rotate", "Rotation", cam.rotate, f"{cam.rotate:g}°")
    sec.add("pixels_per_unit", "Pixels per unit at the output size", round(ppu, 6), f"{ppu:.6g}")
    sec.add("units_per_pixel", "Fractal units per output pixel", 1.0 / ppu, f"{1.0 / ppu:.4g}")
    sec.add("span_width", "Visible width", round(span_w, 6), f"{span_w:.6g} units")
    sec.add("span_height", "Visible height", round(span_h, 6), f"{span_h:.6g} units")
    sec.add("left", "Left edge (unrotated)", round(cam.center[0] - span_w / 2, 6), f"{cam.center[0] - span_w / 2:.6g}")
    sec.add("right", "Right edge (unrotated)", round(cam.center[0] + span_w / 2, 6), f"{cam.center[0] + span_w / 2:.6g}")
    sec.add("top", "Top edge (unrotated)", round(cam.center[1] - span_h / 2, 6), f"{cam.center[1] - span_h / 2:.6g}")
    sec.add("bottom", "Bottom edge (unrotated)", round(cam.center[1] + span_h / 2, 6), f"{cam.center[1] + span_h / 2:.6g}")
    return sec


def _coloring_section(flame: Flame) -> Section:
    sec = Section("coloring", "Colouring")
    c = flame.coloring
    sec.add("brightness", "Brightness", c.brightness, f"{c.brightness:g}")
    sec.add("gamma", "Gamma", c.gamma, f"{c.gamma:g}")
    sec.add("gamma_threshold", "Gamma threshold", c.gamma_threshold, f"{c.gamma_threshold:g}")
    sec.add("vibrancy", "Vibrancy", c.vibrancy, f"{c.vibrancy:g}")
    sec.add("contrast", "Contrast", c.contrast, f"{c.contrast:g}")
    sec.add("background", "Background", rgb_to_hex(tuple(c.background)), f"{rgb_to_hex(tuple(c.background))} (rgb {c.background[0]}, {c.background[1]}, {c.background[2]})")
    return sec


def _palette_section(flame: Flame) -> Section:
    sec = Section("palette", "Palette")
    colours = [tuple(int(v) for v in c) for c in flame.palette]
    if not colours:
        sec.add("entries", "Entries", 0)
        return sec
    lum = [luminance(c) for c in colours]
    hsl = [rgb_to_hsl(c) for c in colours]
    mean = tuple(int(round(sum(c[i] for c in colours) / len(colours))) for i in range(3))
    deltas = [max(abs(a[i] - b[i]) for i in range(3)) for a, b in zip(colours, colours[1:])]
    families: dict[str, int] = {}
    for c, (h, sat, light) in zip(colours, hsl):
        if sat > 0.15 and 0.05 < light < 0.95:
            families[_hue_name(c)] = families.get(_hue_name(c), 0) + 1
    dominant = sorted(families.items(), key=lambda kv: -kv[1])[:3]
    sec.add("entries", "Entries", len(colours))
    sec.add("unique_colors", "Unique colours", len(set(colours)))
    sec.add("mean_color", "Mean colour", rgb_to_hex(mean), f"{rgb_to_hex(mean)} (rgb {mean[0]}, {mean[1]}, {mean[2]})")
    sec.add("mean_luminance", "Mean luminance", round(sum(lum) / len(lum), 3), f"{sum(lum) / len(lum):.1f} / 255")
    dark, bright = int(np.argmin(lum)), int(np.argmax(lum))
    sec.add("darkest", "Darkest entry", rgb_to_hex(colours[dark]), f"{rgb_to_hex(colours[dark])} at index {dark} (luminance {lum[dark]:.1f})")
    sec.add("brightest", "Brightest entry", rgb_to_hex(colours[bright]), f"{rgb_to_hex(colours[bright])} at index {bright} (luminance {lum[bright]:.1f})")
    sec.add("mean_saturation", "Mean saturation", round(sum(h[1] for h in hsl) / len(hsl), 4), f"{100 * sum(h[1] for h in hsl) / len(hsl):.1f} %")
    sec.add("grey_entries", "Near-grey entries", sum(1 for h in hsl if h[1] <= 0.15))
    sec.add("dominant_hues", "Dominant hues", [name for name, _ in dominant],
            ", ".join(f"{name} ({count})" for name, count in dominant) or "none (grey palette)")
    sec.add("max_step", "Largest step between neighbours", max(deltas) if deltas else 0,
            f"{max(deltas) if deltas else 0} / 255 per channel")
    sec.add("mean_step", "Mean step between neighbours", round(sum(deltas) / len(deltas), 3) if deltas else 0,
            f"{sum(deltas) / len(deltas):.2f} / 255" if deltas else "—")
    sec.add("first", "First entry", rgb_to_hex(colours[0]))
    sec.add("last", "Last entry", rgb_to_hex(colours[-1]))
    return sec


def _transforms_section(flame: Flame) -> Section:
    sec = Section("transforms", "Transforms")
    total = sum(x.weight for x in flame.xforms) or 1.0
    table = Table("", "Transforms", [
        ("index", "#"), ("name", "name"), ("weight", "weight"), ("probability", "probability"), ("color", "colour"),
        ("color_speed", "colour speed"), ("opacity", "opacity"), ("variations", "variations"), ("params", "parameters"),
        ("coefs", "pre affine [a b c d e f]"), ("post", "post affine"), ("determinant", "det"), ("scale_factor", "scale"),
        ("xaos", "xaos row")], id_key="index")
    for i, x in enumerate(flame.xforms, start=1):
        table.rows.append(_xform_row(i, x, x.weight / total))
    if flame.final is not None:
        row = _xform_row("final", flame.final, 0.0)
        row["weight"] = ("", "—")
        row["probability"] = ("", "—")
        table.rows.append(row)
    sec.tables.append(table)
    return sec


def _xform_row(index, x: XForm, probability: float) -> dict:
    a, b, c, d, e, f = x.coefs
    det = a * d - b * c
    variations = [(canonical_name(n), w) for n, w in x.variations.items() if w != 0]
    return {
        "index": index, "name": x.name or "", "weight": (x.weight, f"{x.weight:g}"),
        "probability": (round(probability, 6), f"{100 * probability:.2f} %"), "color": (x.color, f"{x.color:g}"),
        "color_speed": (x.color_speed, f"{x.color_speed:g}"), "opacity": (x.opacity, f"{x.opacity:g}"),
        "variations": (" ".join(f"{n}={w:g}" for n, w in variations), ", ".join(f"{n} {w:g}" for n, w in variations) or "none"),
        "params": (" ".join(f"{k}={v:g}" for k, v in sorted(x.params.items())), ", ".join(f"{k} {v:g}" for k, v in sorted(x.params.items())) or "—"),
        "coefs": (" ".join(f"{v:.10g}" for v in x.coefs), _affine_text(x.coefs)),
        "post": (" ".join(f"{v:.10g}" for v in x.post) if x.has_post() else "", _affine_text(x.post) if x.has_post() else "identity"),
        "determinant": (round(det, 6), f"{det:.4g}"), "scale_factor": (round(math.sqrt(abs(det)), 6), f"{math.sqrt(abs(det)):.4g}"),
        "xaos": (" ".join(f"{v:g}" for v in x.chaos) if x.chaos else "", ", ".join(f"{v:g}" for v in x.chaos) if x.chaos else "—"),
    }


def _variations_section(flame: Flame) -> Section:
    sec = Section("variations", "Variations")
    usage: dict[str, list[tuple[str, float]]] = {}
    all_xforms = [(str(i), x) for i, x in enumerate(flame.xforms, start=1)]
    if flame.final is not None:
        all_xforms.append(("final", flame.final))
    for label, x in all_xforms:
        for name, weight in x.variations.items():
            if weight != 0:
                usage.setdefault(canonical_name(name), []).append((label, weight))
    table = Table("", "Variations", [
        ("name", "variation"), ("transforms", "used by"), ("transform_list", "transforms"), ("total_weight", "total weight"),
        ("mean_weight", "mean weight"), ("min_weight", "min"), ("max_weight", "max"), ("parameters", "parameters"),
        ("kind", "kind"), ("supported", "supported")], id_key="name")
    for name in sorted(usage, key=lambda n: (-len(usage[n]), n)):
        uses = usage[name]
        weights = [w for _, w in uses]
        var = REGISTRY.get(name)
        kind = "pre_blur" if name == "pre_blur" else ("random" if var and var.random else ("affine-dependent" if var and var.uses_affine else "plain"))
        params = sorted(var.params) if var else []
        table.rows.append({
            "name": name, "transforms": len(uses), "transform_list": (" ".join(l for l, _ in uses), ", ".join(l for l, _ in uses)),
            "total_weight": (round(sum(weights), 6), f"{sum(weights):g}"), "mean_weight": (round(sum(weights) / len(weights), 6), f"{sum(weights) / len(weights):g}"),
            "min_weight": (round(min(weights), 6), f"{min(weights):g}"), "max_weight": (round(max(weights), 6), f"{max(weights):g}"),
            "parameters": (" ".join(params), ", ".join(params) or "—"), "kind": kind,
            "supported": var is not None or name == "pre_blur",
        })
    sec.add("terms", "Variation terms", sum(len(u) for u in usage.values()))
    sec.add("most_used", "Most used", table.rows[0]["name"] if table.rows else "", table.rows[0]["name"] if table.rows else "none")
    sec.tables.append(table)
    return sec


def _xaos_section(flame: Flame) -> Section | None:
    xforms = [x for x in flame.xforms if x.weight > 0]
    if not any(x.chaos is not None and any(c != 1 for c in x.chaos) for x in xforms):
        return None
    sec = Section("xaos", "Xaos (transform-to-transform weights)")
    n = len(xforms)
    table = Table("", "Xaos matrix (row = from, column = to)", [("from", "from")] + [(f"to_{j}", f"→ {j}") for j in range(1, n + 1)], id_key="from")
    for i, x in enumerate(xforms, start=1):
        row = {"from": i}
        chaos = (list(x.chaos) + [1.0] * n)[:n] if x.chaos is not None else [1.0] * n
        for j, v in enumerate(chaos, start=1):
            row[f"to_{j}"] = (v, f"{v:g}")
        table.rows.append(row)
    sec.tables.append(table)
    sec.add("dead_links", "Forbidden links (weight 0)", sum(1 for x in xforms if x.chaos for c in x.chaos[:n] if c == 0))
    return sec


# --- rendering ----------------------------------------------------------------------------------
def to_text(report: Report) -> str:
    """Pipeline-friendly `key<TAB>value` lines (see the module docstring)."""
    lines = [f"# {report.title}", f"# generated\t{machine_text(report.generated)}",
             "# format: one record per line, key<TAB>value; keys are dotted, values machine-readable"]
    for sec in report.sections:
        lines.append(f"# {sec.title}")
        for item in sec.items:
            lines.append(f"{sec.key}.{item.key}\t{_escape_text(machine_text(item.value))}")
        for table in sec.tables:
            prefix = f"{sec.key}.{table.key}" if table.key else sec.key
            lines.append(f"{prefix}.count\t{len(table.rows)}")
            for n, row in enumerate(table.rows, start=1):
                row_id = machine_text(_cell(row[table.id_key])[0]) if table.id_key else str(n)
                for key, _label in table.columns:
                    if key == table.id_key:
                        continue
                    value, _display = _cell(row.get(key, ""))
                    lines.append(f"{prefix}.{row_id}.{key}\t{_escape_text(machine_text(value))}")
        for n, note in enumerate(sec.notes, start=1):
            lines.append(f"{sec.key}.{n}\t{_escape_text(note)}")
    return "\n".join(lines) + "\n"


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def to_markdown(report: Report) -> str:
    """A readable Markdown document."""
    out = [f"# {report.title}", "", f"_Generated {report.generated.strftime('%Y-%m-%d %H:%M:%S %Z')}_", ""]
    for sec in report.sections:
        out.append(f"## {sec.title}")
        out.append("")
        if sec.items:
            out.append("| Field | Value |")
            out.append("|---|---|")
            for item in sec.items:
                out.append(f"| {_md(item.label)} | {_md(item.text)} |")
            out.append("")
        for table in sec.tables:
            out.append(f"### {table.title}")
            out.append("")
            out.append("| " + " | ".join(_md(label) for _key, label in table.columns) + " |")
            out.append("|" + "---|" * len(table.columns))
            for row in table.rows:
                out.append("| " + " | ".join(_md(_cell(row.get(key, ""))[1]) for key, _label in table.columns) + " |")
            out.append("")
        for note in sec.notes:
            out.append(f"- {_md(note)}")
        if sec.notes:
            out.append("")
    return "\n".join(out)


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


_HTML_STYLE = """
body { font: 14px/1.45 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; color: #222; background: #fafafa;
       max-width: 1100px; margin: 2em auto; padding: 0 1em; }
h1 { font-size: 1.6em; border-bottom: 2px solid #ddd; padding-bottom: .3em; }
h2 { font-size: 1.2em; margin-top: 2em; color: #333; }
h3 { font-size: 1em; color: #555; }
table { border-collapse: collapse; margin: .5em 0 1em; background: #fff; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: .3em .6em; text-align: left; vertical-align: top; }
th { background: #f0f0f0; font-weight: 600; }
tr:nth-child(even) td { background: #f7f7f7; }
.fields td:first-child { color: #555; white-space: nowrap; }
.generated { color: #777; font-style: italic; }
"""


def to_html(report: Report) -> str:
    """A standalone HTML page."""
    e = html.escape
    out = ["<!DOCTYPE html>", "<html lang=\"en\"><head><meta charset=\"utf-8\">", f"<title>{e(report.title)}</title>",
           f"<style>{_HTML_STYLE}</style></head><body>", f"<h1>{e(report.title)}</h1>",
           f"<p class=\"generated\">Generated {e(report.generated.strftime('%Y-%m-%d %H:%M:%S %Z'))}</p>"]
    for sec in report.sections:
        out.append(f"<h2 id=\"{e(sec.key)}\">{e(sec.title)}</h2>")
        if sec.items:
            out.append("<table class=\"fields\"><tbody>")
            for item in sec.items:
                out.append(f"<tr><td>{e(item.label)}</td><td>{e(item.text)}</td></tr>")
            out.append("</tbody></table>")
        for table in sec.tables:
            out.append(f"<h3>{e(table.title)}</h3>")
            out.append("<table><thead><tr>" + "".join(f"<th>{e(label)}</th>" for _key, label in table.columns) + "</tr></thead><tbody>")
            for row in table.rows:
                out.append("<tr>" + "".join(f"<td>{e(_cell(row.get(key, ''))[1])}</td>" for key, _label in table.columns) + "</tr>")
            out.append("</tbody></table>")
        if sec.notes:
            out.append("<ul>" + "".join(f"<li>{e(note)}</li>" for note in sec.notes) + "</ul>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


RENDERERS = {"md": to_markdown, "txt": to_text, "html": to_html}


def render_report(report: Report, fmt: str) -> str:
    """The report as text in format `fmt` ("md" / "txt" / "html"; unknown → Markdown)."""
    return RENDERERS.get(fmt, to_markdown)(report)


def write_report(report: Report, path: Path, fmt: str) -> Path:
    """Write the report to `path`; returns the path."""
    Path(path).write_text(render_report(report, fmt), encoding="utf-8")
    return Path(path)


__all__ = ["REPORT_FORMATS", "report_extension", "Report", "Section", "Table", "Item", "build_report", "render_report",
           "write_report", "to_text", "to_markdown", "to_html", "machine_text"]
