"""Small, dependency-free helpers for 8-bit RGB triples."""

from __future__ import annotations

import colorsys
import math

RGB = tuple[int, int, int]


def clamp_channel(value: float) -> int:
    return max(0, min(255, int(round(value))))


def clamp_unit(value: float) -> float:
    return max(0.0, min(1.0, value))


def lerp_rgb(a: RGB, b: RGB, t: float) -> RGB:
    return tuple(clamp_channel(ca + (cb - ca) * t) for ca, cb in zip(a, b))  # type: ignore[return-value]


def rgb_to_hex(rgb: RGB) -> str:
    return "%02X%02X%02X" % rgb


def hex_to_rgb(text: str) -> RGB:
    text = text.strip().lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def luminance(rgb: RGB) -> float:
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hue(rgb: RGB) -> float:
    r, g, b = (c / 255.0 for c in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[0]


def distance(a: RGB, b: RGB) -> float:
    return math.sqrt(sum((ca - cb) ** 2 for ca, cb in zip(a, b)))


def max_channel_delta(a: RGB, b: RGB) -> int:
    return max(abs(ca - cb) for ca, cb in zip(a, b))
