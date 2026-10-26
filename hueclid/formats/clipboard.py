"""Gradient text for the clipboard — UGR, which Ultra Fractal and Apophysis both exchange.

Pasting is lenient: a full UGR block, a bare run of `index=… color=…` tokens,
or a flame `<palette>` element all parse.
"""

from __future__ import annotations

import re

from ..model import ColorStop, Gradient, hex_to_rgb
from . import ufparams as uf
from .ugr import serialize

_PALETTE_BODY = re.compile(r"<palette\b[^>]*>(.*?)</palette>", re.DOTALL)
_HEX_TRIPLET = re.compile(r"[0-9A-Fa-f]{6}")
_TITLE = re.compile(r'title="([^"]*)"')
_BLOCK_NAME = re.compile(r"^\s*([^{\r\n]*?)\s*\{", re.MULTILINE)


def gradient_to_text(gradient: Gradient) -> str:
    return serialize(gradient)


def text_to_gradient(text: str) -> Gradient | None:
    """The first gradient found in `text`, or None if it isn't gradient text."""
    return _from_ugr(text) or _from_palette(text)


def _from_ugr(text: str) -> Gradient | None:
    stops = uf.stops_from_tokens(uf.tokens(text))
    if not stops:
        return None
    title = _TITLE.search(text)
    name_match = _BLOCK_NAME.search(text)
    name = title.group(1) if title else (name_match.group(1).strip() if name_match else "") or "pasted"
    return Gradient(name, stops)


def _from_palette(text: str) -> Gradient | None:
    match = _PALETTE_BODY.search(text)
    if not match:
        return None
    colors = [hex_to_rgb(h) for h in _HEX_TRIPLET.findall(match.group(1))]
    return Gradient.from_colors("pasted", colors) if colors else None


__all__ = ["ColorStop", "gradient_to_text", "text_to_gradient"]
