"""The "Fractal and Render Details" report written beside a rendered image.

    report = build_report(flame, settings, result, image_path, sidecar, source, report_path)
    write_report(report, path, "md")          # or "txt" / "html"

`model.py` is the document (sections of items and tables, each fact with a machine value *and*
a human display), `render_facts.py` and `fractal_facts.py` fill it, `writers.py` renders it —
Markdown and HTML for people, `key<TAB>value` text for pipelines. The EXR header attributes come
from the same facts (`exr_attributes`).
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from ... import config
from ...fractal.scene import Flame
from ..final_engine import FinalResult
from ..final_settings import FinalRenderSettings
from .fractal_facts import (FlameFacts, camera_section, coloring_section, fractal_section, palette_section,
                            transforms_section, variations_section, xaos_section)
from .model import Cell, Item, Report, Section, Table, machine_text
from .render_facts import exr_attributes, output_section, render_section, system_section, timing_section
from .writers import render_report, to_html, to_markdown, to_text

REPORT_FORMATS: tuple[tuple[str, str, str], ...] = (("md", "Markdown (.md)", ".md"), ("txt", "Text (.txt)", ".txt"),
                                                    ("html", "HTML (.html)", ".html"))


def report_extension(key: str) -> str:
    """File suffix for a report format key (unknown keys mean Markdown)."""
    return next((ext for k, _label, ext in REPORT_FORMATS if k == key), ".md")


def build_report(flame: Flame, settings: FinalRenderSettings, result: FinalResult, image_path: Path | None,
                 sidecar: Path | None = None, source: str = "", report_path: Path | None = None) -> Report:
    """Gather every fact about the render and the fractal into a `Report`.

    Args:
        flame: The fractal that was rendered.
        settings: The render settings used.
        result: What the renderer produced.
        image_path: Where the image was written (None if it was not).
        sidecar: The `.flame` written beside it, if any.
        source: Where the flame came from, for the record.
        report_path: Where this report will be written, for the record.
    """
    now = datetime.now().astimezone()
    facts = FlameFacts.of(flame)
    report = Report(f"{config.APP_NAME} render report — {flame.name}", now)
    report.sections = [
        output_section(settings, result, image_path, sidecar, report_path, now),
        render_section(settings, result),
        timing_section(settings, result),
        system_section(result),
        fractal_section(facts, source),
        camera_section(flame, settings),
        coloring_section(flame),
        palette_section(flame),
        transforms_section(facts),
        variations_section(facts),
    ]
    xaos = xaos_section(facts)
    if xaos is not None:
        report.sections.append(xaos)
    if result.notes:
        report.sections.append(Section("notes", "Notes", notes=list(result.notes)))
    return report


def write_report(report: Report, path: Path, fmt: str) -> Path:
    """Write the report to `path` in format `fmt`; returns the path."""
    Path(path).write_text(render_report(report, fmt), encoding="utf-8")
    return Path(path)


__all__ = ["REPORT_FORMATS", "report_extension", "build_report", "write_report", "render_report", "exr_attributes",
           "Report", "Section", "Table", "Item", "Cell", "machine_text", "to_text", "to_markdown", "to_html"]
