"""Gradient text for the clipboard — UGR, which Ultra Fractal and Apophysis both exchange.

Pasting is lenient: a full UGR block, a bare run of `index=… color=…` tokens,
or a flame `<palette>` element all parse.
"""

from __future__ import annotations

import re

from ..model import Gradient, hex_to_rgb
from . import ufparams as uf
from .ugr import parse_blocks, serialize

_PALETTE_BODY = re.compile(r"<palette\b[^>]*>(.*?)</palette>", re.DOTALL)
_HEX_TRIPLET = re.compile(r"[0-9A-Fa-f]{6}")


def gradient_to_text(gradient: Gradient) -> str:
    """Render `gradient` as a UGR block for the clipboard."""
    return serialize(gradient)


def text_to_gradient(text: str) -> Gradient | None:
    """The first gradient found in `text`, or None if it isn't gradient text."""
    return _from_ugr(text) or _from_palette(text)


def _from_ugr(text: str) -> Gradient | None:
    for block in parse_blocks(text):  # a proper `name { ... }` block, possibly several
        gradient = block.gradient()
        if gradient is not None:
            return gradient
    stops = uf.stops_from_tokens(uf.tokens(text))  # bare tokens, e.g. copied out of a .ufr
    return Gradient(uf.title_of(text) or "pasted", stops) if stops else None


def _from_palette(text: str) -> Gradient | None:
    match = _PALETTE_BODY.search(text)
    if not match:
        return None
    colors = [hex_to_rgb(h) for h in _HEX_TRIPLET.findall(match.group(1))]
    return Gradient.from_colors("pasted", colors) if colors else None

