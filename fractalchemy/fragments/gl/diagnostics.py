"""Driver compiler logs → `(file, line, message)` the log panel can click.

moderngl raises one `Error` whose text holds the stage (`vertex_shader` / `fragment_shader`) and the driver's log.
Three log dialects cover the drivers in use — Mesa `0:12(5): error: …`, NVIDIA `0(12) : error C1008: …`,
AMD / Intel `ERROR: 0:12: …` — each giving a line in the *emitted* source, which the `LineMap` turns into the
original file and line (None for the compatibility prelude, reported as such).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from ..source import LineMap

RE_MESA = re.compile(r"^\s*\d+:(\d+)\((\d+)\):\s*(error|warning):\s*(.*)$")
RE_NVIDIA = re.compile(r"^\s*\d+\((\d+)\)\s*:\s*(error|warning)\s*(.*)$")
RE_AMD = re.compile(r"^\s*(ERROR|WARNING):\s*\d+:(\d+):\s*(.*)$")
STAGES = ("vertex_shader", "fragment_shader", "geometry_shader")


@dataclass(frozen=True)
class Diagnostic:
    """One compiler remark.

    Attributes:
        stage: `vertex` or `fragment`.
        severity: `error` or `warning`.
        emitted_line: 1-based line in the text handed to the driver (0 when the log gave none).
        file: The original file (None: generated text or an unsaved tab).
        line: 1-based line in `file` (0 when unknown or generated).
        message: The driver's text.
        source_line: The offending emitted line's text, when known.
    """
    stage: str
    severity: str
    emitted_line: int
    file: Path | None
    line: int
    message: str
    source_line: str = ""

    def location(self) -> str:
        if self.file is not None and self.line:
            return f"{self.file.name}:{self.line}"
        if self.emitted_line and not self.line:
            return f"{self.stage} shader line {self.emitted_line} (generated code)"
        return f"{self.stage} shader"

    def text(self) -> str:
        return f"{self.location()} — {self.message}"


def parse_log(text: str, vertex_map: LineMap, fragment_map: LineMap, vertex_text: str = "", fragment_text: str = "") -> list[Diagnostic]:
    """Every error / warning in a moderngl compile error message, mapped through the line maps."""
    stage = "fragment"
    out: list[Diagnostic] = []
    for raw in text.splitlines():
        line = raw.strip()
        if line in STAGES:
            stage = line.split("_")[0]
            continue
        parsed = _parse_line(line)
        if parsed is None:
            continue
        emitted, severity, message = parsed
        line_map, source = (vertex_map, vertex_text) if stage == "vertex" else (fragment_map, fragment_text)
        origin = line_map.origin(emitted) if emitted else None
        file, number = origin if origin else (None, 0)
        lines = source.splitlines()
        snippet = lines[emitted - 1].strip() if 0 < emitted <= len(lines) else ""
        out.append(Diagnostic(stage, severity, emitted, file, number, message, snippet))
    if not out and text.strip():
        out.append(Diagnostic(stage, "error", 0, None, 0, text.strip().splitlines()[-1]))
    return out


def _parse_line(line: str) -> tuple[int, str, str] | None:
    match = RE_MESA.match(line)
    if match:
        return int(match.group(1)), match.group(3), match.group(4).strip()
    match = RE_NVIDIA.match(line)
    if match:
        return int(match.group(1)), match.group(2), match.group(3).strip()
    match = RE_AMD.match(line)
    if match:
        return int(match.group(2)), match.group(1).lower(), match.group(3).strip()
    return None


__all__ = ["Diagnostic", "parse_log"]
