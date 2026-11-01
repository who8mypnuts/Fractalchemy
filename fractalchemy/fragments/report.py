"""The render report written beside a fragment render — the host's `render.report` document model for fragments.

Sections: the output (files, format, size), the fragment (file, includes, preset, GLSL version, renderer), the render
plan (tiles, padding, subframes, animation), the parameters (the settings text as a table), timings (total, per
frame / tile, subframes per second) and the machine. The same `Report` renders as Markdown, tab-separated text or
HTML through `render.report.render_report`.
"""

from __future__ import annotations

import platform
import socket
from datetime import datetime
from pathlib import Path

from .. import config
from ..render.report import Report, Section, Table, render_report, report_extension
from .parameters import parse_settings


def build_fragment_report(name: str, path: Path | None, settings, result, settings_text: str, image_path: Path | None,
                          includes: list[Path] | None = None, preset: str = "", animation=None, frames_written: list[Path] | None = None) -> Report:
    """The report for one finished render (`settings`: `FragFinalSettings`, `result`: `FragFinalResult`)."""
    now = datetime.now().astimezone()
    report = Report(f"{name} — fragment render details", now)
    report.sections.append(_output(settings, result, image_path, frames_written or [], now))
    report.sections.append(_fragment(name, path, includes or [], preset, result))
    report.sections.append(_plan(settings, animation))
    report.sections.append(_parameters(settings_text))
    report.sections.append(_timings(result, settings))
    report.sections.append(_machine())
    return report


def _output(s, r, image_path, frames, now) -> Section:
    sec = Section("output", "Output")
    width, height = s.image_size
    sec.add("image", "Image", str(image_path) if image_path else "", str(image_path.name) if image_path else "—")
    sec.add("format", "Format", s.output_format)
    sec.add("bits", "Bits per channel", s.depth)
    sec.add("size", "Size", [width, height], f"{width} × {height} pixels ({width * height / 1e6:.2f} MP)")
    sec.add("complete", "Complete", r.complete)
    sec.add("frames", "Frames written", len(frames) if frames else (1 if image_path else 0))
    sec.add("depth_to_alpha", "Depth channel (EXR Z)", s.depth_to_alpha)
    sec.add("generated", "Generated", now)
    if frames:
        table = Table("frames", "Frame files", [("frame", "Frame"), ("file", "File")])
        for index, frame in enumerate(frames):
            table.add_row({"frame": index, "file": frame.name})
        sec.tables.append(table)
    return sec


def _fragment(name, path, includes, preset, r) -> Section:
    sec = Section("fragment", "Fragment")
    sec.add("name", "Name", name)
    sec.add("file", "File", str(path) if path else "", str(path) if path else "unsaved")
    sec.add("preset", "Preset", preset or "Default")
    sec.add("includes", "Includes", [str(p) for p in includes], ", ".join(p.name for p in includes) or "none")
    sec.add("glsl_version", "GLSL version", r.glsl_version)
    sec.add("renderer", "OpenGL renderer", r.renderer)
    sec.add("engine", "Engine", r.engine)
    sec.add("compile_ms", "Compile time", r.compile_ms, f"{r.compile_ms:.0f} ms")
    return sec


def _plan(s, animation) -> Section:
    sec = Section("plan", "Render plan")
    sec.add("tile_size", "Tile size", [s.tile_width, s.tile_height], f"{s.tile_width} × {s.tile_height}")
    sec.add("tiles", "Tiles", s.tiles, f"{s.tiles} × {s.tiles} = {s.tile_count}")
    sec.add("padding", "Padding", s.padding, f"{s.padding * 100:.0f}%")
    sec.add("subframes", "Subframes per tile", s.subframes)
    sec.add("animation", "Animation", s.animation)
    if s.animation:
        sec.add("frame_range", "Frame range", [s.start_frame, s.end_frame], f"{s.start_frame} – {s.end_frame}")
        if animation is not None:
            sec.add("fps", "Frames per second", animation.fps)
            sec.add("length", "Length", animation.length, f"{animation.length} s")
        if s.video:
            sec.add("video", "Video", s.video_format)
    sec.add("embed_parameters", "Parameters embedded in the image", s.embed_parameters)
    return sec


def _parameters(settings_text: str) -> Section:
    sec = Section("parameters", "Parameters")
    table = Table("", "Values", [("name", "Parameter"), ("value", "Value"), ("flags", "Flags")], id_key="name")
    parsed = parse_settings(settings_text)
    for line in parsed.lines:
        flags = []
        if line.lock is not None:
            flags.append(line.lock.value)
        if line.slider.value:
            flags.append(line.slider.value)
        table.add_row({"name": line.name, "value": line.value_text, "flags": " ".join(flags)})
    sec.tables.append(table)
    for easing in parsed.easing:
        sec.notes.append(f"easing curve: {easing}")
    return sec


def _timings(r, s) -> Section:
    sec = Section("timing", "Timing")
    total_subframes = s.subframes * s.tile_count * max(1, r.frames_rendered)
    sec.add("seconds", "Render time", r.seconds, f"{r.seconds:.1f} s")
    sec.add("subframes", "Subframes drawn", total_subframes)
    rate = total_subframes / r.seconds if r.seconds > 0 else 0.0
    sec.add("subframes_per_second", "Subframes per second", rate, f"{rate:.2f}")
    width, height = s.image_size
    pixel_rate = rate * width * height / max(1, s.tile_count)
    sec.add("pixels_per_second", "Pixel samples per second", pixel_rate, f"{pixel_rate / 1e6:.1f} M")
    if r.tile_seconds:
        table = Table("tiles", "Per tile", [("frame", "Frame"), ("tile", "Tile"), ("seconds", "Seconds"), ("rate", "Subframes / s")])
        for frame, tile, seconds in r.tile_seconds:
            table.add_row({"frame": frame, "tile": tile, "seconds": (seconds, f"{seconds:.2f}"),
                           "rate": (s.subframes / seconds if seconds > 0 else 0.0, f"{s.subframes / seconds:.1f}" if seconds > 0 else "—")})
        sec.tables.append(table)
        slowest = max(r.tile_seconds, key=lambda t: t[2])
        sec.add("slowest_tile", "Slowest tile", slowest[1], f"tile {slowest[1]} of frame {slowest[0]}: {slowest[2]:.2f} s")
    return sec


def _machine() -> Section:
    sec = Section("machine", "Machine")
    sec.add("host", "Host", socket.gethostname())
    sec.add("system", "System", f"{platform.system()} {platform.release()}")
    sec.add("python", "Python", platform.python_version())
    sec.add("application", "Application", f"{config.APP_NAME} {getattr(config, 'APP_VERSION', '')}".strip())
    return sec


def write_fragment_report(report: Report, beside: Path, fmt: str) -> Path:
    """Write `report` next to `beside` (same stem) in `fmt`; returns the path."""
    path = beside.with_suffix(report_extension(fmt))
    path.write_text(render_report(report, fmt), encoding="utf-8")
    return path


__all__ = ["build_fragment_report", "write_fragment_report"]
