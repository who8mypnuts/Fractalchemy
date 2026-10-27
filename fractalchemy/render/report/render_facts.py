"""Report sections about the render: output file, settings, timing and statistics, system — and the EXR attributes.

Everything here derives from `FinalRenderSettings` + `FinalResult`; nothing is parsed back out of
display strings. The same facts feed the OpenEXR header (`exr_attributes`) so a DCC sees what the
report says.
"""

from __future__ import annotations

import json
import os
import platform
import socket
from datetime import datetime
from pathlib import Path

import numpy as np

from ... import config
from ...fractal.scene import Flame
from ..denoise import denoiser_kind
from ..filters import filter_kind, make_taps
from ..final_engine import FinalResult
from ..final_settings import ENGINES, FinalRenderSettings
from ..memory import gpu_budget_bytes, memory_budget_bytes, physical_memory_bytes
from ..output import output_format
from ..units import aspect_text, format_bytes, format_count, format_seconds
from .model import Section, Table


def output_section(s: FinalRenderSettings, r: FinalResult, image_path: Path | None, sidecar: Path | None,
                   report_path: Path | None, now: datetime) -> Section:
    """The file that was written and how it was encoded."""
    sec = Section("output", "Output")
    fmt = output_format(s.output_format)
    sec.add("file", "Image file", str(image_path) if image_path else "", str(image_path) if image_path else "not saved")
    if image_path is not None and Path(image_path).exists():
        size = Path(image_path).stat().st_size
        sec.add("file_bytes", "File size", size, f"{format_bytes(size)} ({size:,} bytes)")
    sec.add("format", "Format", fmt.key, fmt.label)
    sec.add("width", "Width", s.width, f"{s.width:,} px")
    sec.add("height", "Height", s.height, f"{s.height:,} px")
    sec.add("megapixels", "Megapixels", round(s.width * s.height / 1e6, 3), f"{s.width * s.height / 1e6:.2f} Mpx")
    sec.add("aspect_ratio", "Aspect ratio", round(s.width / max(1, s.height), 6), aspect_text(s.width, s.height, ":"))
    if fmt.float_channels:
        depth = 32 if s.depth >= 32 else 16
        sec.add("bits_per_channel", "Bits per channel", depth, f"{depth}-bit {'half ' if depth == 16 else ''}float, linear light")
    else:
        sec.add("bits_per_channel", "Bits per channel", 16 if fmt.depth16 and s.depth >= 16 else 8)
    sec.add("transparent", "Transparent background", bool(s.transparent and fmt.alpha))
    if fmt.lossy:
        lossless = bool(s.lossless and fmt.lossless_option)
        sec.add("lossless", "Lossless", lossless)
        if not lossless:
            sec.add("quality_percent", "Encoding quality", s.lossy_quality, f"{s.lossy_quality} %")
    sec.add("parameters_embedded", "Parameters embedded in the image", bool(s.embed_parameters))
    sec.add("parameters_file", "Parameter file", str(sidecar) if sidecar else "", str(sidecar) if sidecar else "none")
    sec.add("details_file", "Details file", str(report_path) if report_path else "")
    sec.add("complete", "Render completed", bool(r.complete), "yes" if r.complete else "no — stopped early, partial image")
    sec.add("written_at", "Written", now, now.strftime("%Y-%m-%d %H:%M:%S %Z"))
    sec.add("software", "Software", f"{config.APP_NAME} {config.APP_VERSION}")
    return sec


def render_section(s: FinalRenderSettings, r: FinalResult) -> Section:
    """Every render setting, with the derived quantities (buckets, taps, tiles, budgets)."""
    sec = Section("render", "Render settings")
    kind = filter_kind(s.filter_kind)
    taps = make_taps(kind, s.filter_radius, s.oversample)
    bw, bh = s.bucket_size
    sec.add("density", "Density (samples per pixel)", s.quality, f"{s.quality:g}")
    sec.add("oversample", "Oversample", s.oversample, f"{s.oversample} × {s.oversample} buckets per pixel")
    sec.add("bucket_width", "Histogram width", bw, f"{bw:,} buckets")
    sec.add("bucket_height", "Histogram height", bh, f"{bh:,} buckets")
    sec.add("buckets", "Histogram buckets", bw * bh, f"{bw * bh:,} ({format_count(bw * bh)})")
    sec.add("filter", "Reconstruction filter", kind.key, kind.label)
    sec.add("filter_radius", "Filter radius", s.filter_radius, f"{s.filter_radius:g} px")
    sec.add("filter_taps", "Filter taps per axis", int(taps.offsets.size))
    sec.add("filter_reach", "Filter reach", taps.reach, f"{taps.reach} bucket{'s' if taps.reach != 1 else ''} beyond the pixel block")
    _add_denoiser_items(sec, s)
    _add_engine_items(sec, s, r)
    _add_tile_items(sec, s, r)
    sec.add("fuse", "Fuse (warm-up iterations)", s.fuse)
    sec.add("seed", "Random seed", s.seed)
    sec.add("save_incomplete", "Save incomplete renders", bool(s.save_incomplete))
    return sec


def _add_denoiser_items(sec: Section, s: FinalRenderSettings) -> None:
    dn = denoiser_kind(s.denoiser)
    sec.add("denoiser", "Denoiser", dn.key, dn.label)
    if dn.key == "density":
        sec.add("de_max_radius", "Density estimation max radius", s.de_max_radius, f"{s.de_max_radius:g} px")
        sec.add("de_min_radius", "Density estimation min radius", s.de_min_radius, f"{s.de_min_radius:g} px")
        sec.add("de_curve", "Density estimation curve", s.de_curve, f"{s.de_curve:g}")
    elif dn.key != "none":
        sec.add("denoise_strength", "Denoiser strength", s.denoise_strength, f"{s.denoise_strength:g} / 100")


def _add_engine_items(sec: Section, s: FinalRenderSettings, r: FinalResult) -> None:
    sec.add("engine_requested", "Engine requested", s.engine, next((label for key, label in ENGINES if key == s.engine), s.engine))
    sec.add("engine_used", "Engine used", r.engine)
    sec.add("engine_kind", "Engine kind", r.engine_kind)
    sec.add("device", "Device", r.device)
    if r.engine_kind == "cpu":
        sec.add("cpu_workers", "CPU workers", r.workers)
    sec.add("memory_limit_mb", "Memory limit setting", s.memory_limit_mb, f"{s.memory_limit_mb} MB" if s.memory_limit_mb else "automatic")
    budget = memory_budget_bytes(s)
    sec.add("memory_budget_bytes", "Histogram memory budget", budget, format_bytes(budget))
    if r.engine_kind == "gpu":
        gpu = gpu_budget_bytes(s)
        sec.add("gpu_memory_bytes", "GPU tile memory budget", gpu, format_bytes(gpu) + ("" if s.gpu_memory_mb else " (automatic)"))


def _add_tile_items(sec: Section, s: FinalRenderSettings, r: FinalResult) -> None:
    plan = r.plan
    tiles = plan.count if plan else 1
    if plan is not None:
        columns = len({t.x0 for t in plan.tiles})
        rows = len({t.y0 for t in plan.tiles})
        largest = max(t.buckets for t in plan.tiles)
        sec.add("tiles", "Tiles (slices)", plan.count, f"{plan.count} ({columns} × {rows})")
        sec.add("tile_columns", "Tile columns", columns)
        sec.add("tile_rows", "Tile rows", rows)
        sec.add("tiles_rendered", "Tiles rendered", len(r.tiles))
        sec.add("gutter", "Tile gutter", plan.tiles[0].gutter, f"{plan.tiles[0].gutter} buckets")
        sec.add("tile_peak_buckets", "Largest tile", largest, f"{largest:,} buckets")
        sec.add("tile_peak_bytes", "Largest tile memory", plan.peak_bytes, format_bytes(plan.peak_bytes))
        sec.add("bytes_per_bucket", "Host bytes per bucket", plan.bytes_per_bucket)
    sec.add("samples_per_tile", "Samples per tile (target)", s.samples_per_tile, format_count(s.samples_per_tile))
    sec.add("samples_planned", "Samples planned", s.samples_per_tile * tiles, format_count(s.samples_per_tile * tiles))


def timing_section(s: FinalRenderSettings, r: FinalResult) -> Section:
    """Wall / active / paused time, time per phase, throughput and hit statistics, plus the per-tile table."""
    sec = Section("timing", "Timing and statistics")
    started = datetime.fromtimestamp(r.started_at).astimezone() if r.started_at else None
    finished = datetime.fromtimestamp(r.finished_at).astimezone() if r.finished_at else None
    wall = (r.finished_at - r.started_at) if r.started_at and r.finished_at else r.seconds + r.paused_seconds
    sampling, filtering = r.sampling_seconds, r.filter_seconds
    overhead = max(0.0, r.seconds - sampling - filtering - r.denoise_seconds)
    if started:
        sec.add("started_at", "Started", started, started.strftime("%Y-%m-%d %H:%M:%S %Z"))
    if finished:
        sec.add("finished_at", "Finished", finished, finished.strftime("%Y-%m-%d %H:%M:%S %Z"))
    sec.add("wall_seconds", "Wall-clock time", round(wall, 3), format_seconds(wall))
    sec.add("active_seconds", "Active time (pauses excluded)", round(r.seconds, 3), format_seconds(r.seconds))
    sec.add("paused_seconds", "Paused", round(r.paused_seconds, 3), format_seconds(r.paused_seconds))
    for key, label, value in (("sampling_seconds", "Sampling (chaos game)", sampling),
                              ("filtering_seconds", "Filtering and tone mapping", filtering),
                              ("denoising_seconds", "Denoising", r.denoise_seconds),
                              ("startup_seconds", "Engine start-up and overhead", overhead)):
        sec.add(key, label, round(value, 3), f"{format_seconds(value)} ({_pct(value, r.seconds)})")
    _add_throughput_items(sec, s, r, sampling)
    sec.tables.append(tiles_table(r))
    return sec


def _add_throughput_items(sec: Section, s: FinalRenderSettings, r: FinalResult, sampling: float) -> None:
    pixels = s.width * s.height
    sec.add("samples", "Samples (iterations) run", r.samples, f"{r.samples:,} ({format_count(r.samples)})")
    sec.add("samples_per_pixel", "Samples per output pixel", round(r.samples / max(1, pixels), 3), f"{r.samples / max(1, pixels):.1f}")
    for key, label, numerator, denominator, unit in (
            ("samples_per_second", "Sampling speed", r.samples, sampling, "samples/s"),
            ("samples_per_second_overall", "Overall speed (all phases)", r.samples, r.seconds, "samples/s"),
            ("pixels_per_second", "Output pixels per second", pixels, r.seconds, "px/s")):
        rate = numerator / denominator if denominator > 0 else 0.0
        sec.add(key, label, round(rate, 1), f"{format_count(rate)} {unit}" if denominator > 0 else "—")
    hits = sum(t.hits for t in r.tiles)
    tile_samples = sum(t.samples for t in r.tiles)
    buckets = sum(t.buckets for t in r.tiles)
    lit = sum(t.lit_buckets for t in r.tiles)
    densest = max((t.max_count for t in r.tiles), default=0.0)
    sec.add("hits", "Hits (opacity-weighted points inside the tiles)", round(hits, 1), format_count(hits))
    sec.add("hit_ratio", "Hit ratio (hits / samples)", round(hits / tile_samples, 6) if tile_samples else 0, _pct(hits, tile_samples))
    sec.add("lit_buckets", "Buckets hit at least once", lit, f"{lit:,} of {buckets:,} ({_pct(lit, buckets)})")
    sec.add("max_bucket_count", "Densest bucket", round(densest, 1), f"{densest:,.0f} hits")
    sec.add("mean_hits_per_lit_bucket", "Mean hits per lit bucket", round(hits / lit, 3) if lit else 0, f"{hits / lit:.2f}" if lit else "—")


def _pct(part: float, whole: float) -> str:
    return f"{100.0 * part / whole:.1f} %" if whole > 0 else "—"


def tiles_table(r: FinalResult) -> Table:
    """One row per rendered tile."""
    table = Table("tiles", "Tiles", [("index", "#"), ("x", "x"), ("y", "y"), ("width", "width"), ("height", "height"),
                                     ("buckets", "buckets"), ("samples", "samples"), ("render_seconds", "sampling s"),
                                     ("filter_seconds", "filter s"), ("samples_per_second", "samples/s"), ("hits", "hits"),
                                     ("hit_ratio", "hit ratio"), ("lit_fraction", "lit buckets"), ("max_count", "densest")],
                  id_key="index")
    for t in r.tiles:
        x, y, w, h = t.pixel_rect
        rate = t.samples / t.render_seconds if t.render_seconds > 0 else 0.0
        table.add_row({
            "index": t.index + 1, "x": x, "y": y, "width": w, "height": h, "buckets": t.buckets,
            "samples": (t.samples, format_count(t.samples)),
            "render_seconds": (round(t.render_seconds, 3), f"{t.render_seconds:.1f}"),
            "filter_seconds": (round(t.filter_seconds, 3), f"{t.filter_seconds:.1f}"),
            "samples_per_second": (round(rate, 1), format_count(rate)), "hits": (round(t.hits, 1), format_count(t.hits)),
            "hit_ratio": (round(t.hits / t.samples, 6) if t.samples else 0, _pct(t.hits, t.samples)),
            "lit_fraction": (round(t.lit_buckets / t.buckets, 6) if t.buckets else 0, _pct(t.lit_buckets, t.buckets)),
            "max_count": (round(t.max_count, 1), f"{t.max_count:,.0f}"),
        })
    return table


def system_section(r: FinalResult) -> Section:
    """The machine and the library versions."""
    sec = Section("system", "System")
    sec.add("hostname", "Host", socket.gethostname())
    sec.add("platform", "Platform", platform.platform())
    sec.add("machine", "Machine", platform.machine())
    if platform.processor():
        sec.add("processor", "Processor", platform.processor())
    sec.add("cpu_count", "Logical CPUs", os.cpu_count() or 0)
    mem = physical_memory_bytes()
    sec.add("memory_bytes", "Physical memory", mem, format_bytes(mem))
    if r.engine_kind == "gpu":
        sec.add("gpu", "GPU", r.device)
    sec.add("python", "Python", platform.python_version())
    sec.add("numpy", "numpy", np.__version__)
    for module, label, missing in (("scipy", "scipy", "not installed (numpy blur fallback)"), ("moderngl", "moderngl", "not installed")):
        try:
            sec.add(module, label, __import__(module).__version__)
        except ImportError:
            sec.add(module, label, "", missing)
    return sec


def exr_attributes(flame: Flame, settings: FinalRenderSettings, result: FinalResult, source: str) -> dict[str, str]:
    """Header attributes for an OpenEXR file: the standard `comments` / `capDate` / `utcOffset` plus `fractalchemy:*` facts."""
    s = settings
    finished = datetime.fromtimestamp(result.finished_at or datetime.now().timestamp()).astimezone()
    offset = finished.utcoffset()
    cam, col = flame.camera, flame.coloring
    return {
        "comments": f"{flame.name} — rendered by {config.APP_NAME} {config.APP_VERSION} at {s.quality:g} samples/px, "
                    f"oversample {s.oversample}, {result.engine}",
        "capDate": finished.strftime("%Y:%m:%d %H:%M:%S"),
        "utcOffset": f"{-offset.total_seconds() + 0.0:.0f}" if offset is not None else "0",   # OpenEXR: seconds *behind* UTC
        "fractalchemy:name": flame.name,
        "fractalchemy:source": source,
        "fractalchemy:engine": result.engine,
        "fractalchemy:complete": "true" if result.complete else "false",
        "fractalchemy:samples": str(result.samples),
        "fractalchemy:samplesPerPixel": f"{result.samples / max(1, s.width * s.height):.3f}",
        "fractalchemy:renderSeconds": f"{result.seconds:.3f}",
        "fractalchemy:tiles": str(result.plan.count if result.plan else 1),
        "fractalchemy:density": f"{s.quality:g}",
        "fractalchemy:oversample": str(s.oversample),
        "fractalchemy:filter": f"{s.filter_kind} radius {s.filter_radius:g}",
        "fractalchemy:denoiser": s.denoiser,
        "fractalchemy:camera": f"center {cam.center[0] + 0.0:g} {cam.center[1] + 0.0:g} scale {cam.scale:g} "
                               f"zoom {cam.zoom + 0.0:g} rotate {cam.rotate + 0.0:g}",
        "fractalchemy:coloring": f"brightness {col.brightness:g} gamma {col.gamma:g} vibrancy {col.vibrancy:g} contrast {col.contrast:g}",
        "fractalchemy:settings": json.dumps(s.to_dict(), sort_keys=True),
    }


__all__ = ["output_section", "render_section", "timing_section", "tiles_table", "system_section", "exr_attributes"]
