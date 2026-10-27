"""Fractal parameters as clipboard text: Fractalchemy (.fa JSON), Apophysis (<flame> XML) or Chaotica (<world> XML).

    text = flame_to_text(flame, "fa")          # "fa" | "flame" | "chaos"
    flames = text_to_flames(text)              # any of the three, auto-detected
"""

from __future__ import annotations

import json

from ...formats.fa_document import is_document
from ..scene import Flame
from . import chaos_world, chaos_writer, fa, flame_xml

CLIPBOARD_FORMATS = {
    "fa": "Fractalchemy parameters",
    "flame": "Apophysis parameters",
    "chaos": "Chaotica parameters",
}


class ClipboardError(ValueError):
    """The text holds no fractal we can read."""


def flame_to_text(flame: Flame, fmt: str = "fa") -> str:
    """Serialise one flame for the clipboard."""
    if fmt == "fa":
        return json.dumps({"format": fa.FORMAT_ID, "version": fa.FORMAT_VERSION, "flames": [flame.to_dict()]}, indent=1)
    if fmt == "flame":
        return flame_xml.flame_to_xml(flame)
    if fmt == "chaos":
        return chaos_writer.flames_to_world([flame], flame.name)
    raise ValueError(f"unknown clipboard format '{fmt}'")


def detect_format(text: str) -> str | None:
    """Which of the three formats `text` looks like, or None."""
    head = text.lstrip()[:2000]
    if head.startswith("{") and f'"{fa.FORMAT_ID}"' in head:
        return "fa"
    if "<flame" in head:
        return "flame"
    if "<world" in head or "<IFS" in head or "<flam3_IFS" in head:
        return "chaos"
    return None


def text_to_flames(text: str) -> list[Flame]:
    """Every flame in clipboard text of any supported format.

    Raises:
        ClipboardError: If the text is not fractal parameters.
    """
    fmt = detect_format(text)
    try:
        if fmt == "fa":
            doc = json.loads(text)
            if not is_document(doc):
                raise ClipboardError("Fractalchemy text without a valid flames list")
            return [Flame.from_dict(d) for d in doc["flames"]]
        if fmt == "flame":
            return flame_xml.parse_text(text)
        if fmt == "chaos":
            return chaos_world.parse_text(text)
    except (ValueError, KeyError, TypeError, AttributeError) as exc:   # includes JSON / XML parse errors
        raise ClipboardError(f"The clipboard does not hold readable fractal parameters: {exc}") from exc
    raise ClipboardError("The clipboard does not hold fractal parameters (Fractalchemy, Apophysis or Chaotica)")
