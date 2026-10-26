"""Ultra Fractal parameter text: `key=value` tokens in indented, wrapped sections.

    gradient:
      smooth=yes rotation=-6 index=46 color=16709120 index=98 color=74
      index=196 color=12320848 ...

Used by .ugr (gradient files) and .ufr (fractal files). Values may be quoted
strings containing spaces; UF wraps lines at 70 columns including indent.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .. import config
from ..model import RGB, ColorStop

LINE_WIDTH = 70
INDENT = "  "

_TOKEN = re.compile(r'(\w+)=("(?:[^"\\]|\\.)*"|\S*)')
_SECTION = re.compile(r"^(?P<name>\w+):[ \t]*\r?\n(?P<body>(?:[ \t]+[^\r\n]*\r?\n?)*)", re.MULTILINE)


@dataclass(frozen=True)
class Section:
    name: str
    body_start: int
    body_end: int
    body: str


def sections(text: str) -> list[Section]:
    return [Section(m.group("name"), m.start("body"), m.end("body"), m.group("body")) for m in _SECTION.finditer(text)]


def tokens(body: str) -> list[tuple[str, str]]:
    return [(m.group(1), m.group(2)) for m in _TOKEN.finditer(body)]


def unquote(value: str) -> str:
    return value[1:-1] if len(value) >= 2 and value[0] == value[-1] == '"' else value


def quote(value: str) -> str:
    return '"' + value.replace('"', "'") + '"'


# --- gradient stops ---------------------------------------------------------
def unpack_color(value: int) -> RGB:
    return value & 0xFF, (value >> 8) & 0xFF, (value >> 16) & 0xFF


def pack_color(rgb: RGB) -> int:
    r, g, b = rgb
    return r | (g << 8) | (b << 16)


def stops_from_tokens(pairs: list[tuple[str, str]]) -> list[ColorStop]:
    stops, pending_index = [], None
    for key, value in pairs:
        if key == "index":
            pending_index = int(value)
        elif key == "color" and pending_index is not None:
            stops.append(ColorStop(pending_index / config.UGR_MAX_INDEX, unpack_color(int(value))))
            pending_index = None
    return stops


def stop_tokens(stops) -> list[tuple[str, str]]:
    pairs = []
    for stop in stops:
        pairs.append(("index", str(round(stop.position * config.UGR_MAX_INDEX))))
        pairs.append(("color", str(pack_color(stop.color))))
    return pairs


def other_tokens(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Everything except the index/color stream (smooth=, rotation=, title=...)."""
    return [(k, v) for k, v in pairs if k not in ("index", "color")]


# --- writing ----------------------------------------------------------------
def wrap_tokens(pairs: list[tuple[str, str]], newline: str = "\n") -> str:
    """Lay tokens out the way UF does: 2-space indent, lines no longer than 70."""
    lines, current = [], INDENT
    for key, value in pairs:
        token = f"{key}={value}"
        if current != INDENT and len(current) + 1 + len(token) > LINE_WIDTH:
            lines.append(current)
            current = INDENT
        current = token if current == "" else (INDENT + token if current == INDENT else f"{current} {token}")
    if current != INDENT:
        lines.append(current)
    return newline.join(lines) + newline if lines else ""
