"""Fragment files: `.fafrag` / `.frag` text with Fractalchemy's metadata block, `.fragparams`, parameters inside images.

A `.fafrag` is a `.frag` — the presets, keyframes and ranges stay FragM `#preset` blocks, so FragM opens it unchanged —
plus, at most once, a JSON block that FragM's preprocessor sees as a comment:

    /*[fractalchemy]
    {"version": 1, "render": {…}, "animation": {…}, "library": {"tags": […], "thumbnail": "<base64 PNG>"}}
    [/fractalchemy]*/

The block is stripped before preprocessing and re-emitted on save; saving as `.frag` omits it. `.fragparams` files are
the settings text (*Parameters ▸ Save to file*). Images carry the settings under the `frAg` key (FragM's PNG text key,
so FragM reads our screenshots and we read its), through the render package's writers and readers.
"""

from __future__ import annotations

import base64
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ..render.output import read_embedded_parameters

BLOCK_START = "/*[fractalchemy]"
BLOCK_END = "[/fractalchemy]*/"
RE_BLOCK = re.compile(r"\n?/\*\[fractalchemy\]\s*\n(.*?)\n\[/fractalchemy\]\*/\s*", re.DOTALL)
IMAGE_KEY = "frAg"
VERSION = 1
PARAMS_SUFFIX = ".fragparams"


class FragmentFormatError(ValueError):
    """The metadata block is not valid JSON."""


@dataclass
class FragmentMetadata:
    """What Fractalchemy keeps beside a fragment's source.

    Attributes:
        render: The render window's settings for this fragment (size, tiles, subframes, format …).
        animation: fps, length, interpolation mode, loop flags.
        library: Tags, author, a thumbnail (base64 PNG) for the library pane.
        tabs: Editor state worth keeping (the current preset name, camera bookmarks).
        grading: The display colour grading (`fragments.grading.Grading`).
    """
    render: dict[str, Any] = field(default_factory=dict)
    animation: dict[str, Any] = field(default_factory=dict)
    library: dict[str, Any] = field(default_factory=dict)
    tabs: dict[str, Any] = field(default_factory=dict)
    grading: dict[str, Any] = field(default_factory=dict)

    SECTIONS = ("render", "animation", "library", "tabs", "grading")

    @property
    def empty(self) -> bool:
        return not any(getattr(self, name) for name in self.SECTIONS)

    def to_dict(self) -> dict:
        out: dict[str, Any] = {"version": VERSION}
        for name in self.SECTIONS:
            if getattr(self, name):
                out[name] = getattr(self, name)
        return out

    @classmethod
    def from_dict(cls, data: dict) -> "FragmentMetadata":
        if not isinstance(data, dict):
            raise FragmentFormatError("the fractalchemy block must hold a JSON object")
        return cls(**{name: dict(data.get(name) or {}) for name in cls.SECTIONS})

    @property
    def thumbnail_png(self) -> bytes | None:
        """The embedded thumbnail as PNG bytes, if any."""
        encoded = self.library.get("thumbnail")
        if not encoded:
            return None
        try:
            return base64.b64decode(encoded)
        except (ValueError, TypeError):
            return None

    def set_thumbnail_png(self, data: bytes | None) -> None:
        if data:
            self.library["thumbnail"] = base64.b64encode(data).decode("ascii")
        else:
            self.library.pop("thumbnail", None)


def split_metadata(text: str) -> tuple[str, FragmentMetadata | None]:
    """`(source without the block, metadata or None)`; a malformed block raises `FragmentFormatError`."""
    match = RE_BLOCK.search(text)
    if not match:
        return text, None
    try:
        data = json.loads(match.group(1))
    except json.JSONDecodeError as exc:
        raise FragmentFormatError(f"the fractalchemy block is not valid JSON: {exc}") from exc
    return text[:match.start()] + text[match.end():], FragmentMetadata.from_dict(data)


def join_metadata(source: str, metadata: FragmentMetadata | None) -> str:
    """The source with the block appended (no block when the metadata is empty). `*/` inside the JSON is escaped."""
    body, _old = split_metadata(source)
    if metadata is None or metadata.empty:
        return body
    encoded = json.dumps(metadata.to_dict(), indent=1, sort_keys=True).replace("*/", "*\\/")
    return body.rstrip("\n") + f"\n\n{BLOCK_START}\n{encoded}\n{BLOCK_END}\n"


def read_fragment(path: Path) -> tuple[str, FragmentMetadata | None]:
    """A fragment file's source (block removed) and its metadata."""
    return split_metadata(Path(path).read_text(encoding="utf-8", errors="replace"))


def write_fragment(path: Path, source: str, metadata: FragmentMetadata | None) -> None:
    """Write `source`; the metadata block only goes into `.fafrag` files (a `.frag` stays pure Fragmentarium)."""
    path = Path(path)
    keep = path.suffix.lower() == ".fafrag"
    path.write_text(join_metadata(source, metadata if keep else None), encoding="utf-8")


def write_parameters(path: Path, settings_text: str) -> None:
    """A `.fragparams` file (FragM's *Save to File*)."""
    Path(path).write_text(settings_text, encoding="utf-8")


def read_parameters(path: Path) -> str:
    """Settings text from a `.fragparams` file or from an image that carries them (FragM's *Load from File*)."""
    path = Path(path)
    if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".tif", ".tiff", ".webp", ".exr", ".svg"):
        text = read_embedded_parameters(path, IMAGE_KEY)
        if text is None:
            raise FragmentFormatError(f"{path.name} carries no fragment settings")
        return text
    return path.read_text(encoding="utf-8", errors="replace")


__all__ = ["FragmentMetadata", "FragmentFormatError", "split_metadata", "join_metadata", "read_fragment", "write_fragment",
           "write_parameters", "read_parameters", "IMAGE_KEY", "PARAMS_SUFFIX", "BLOCK_START", "BLOCK_END"]
