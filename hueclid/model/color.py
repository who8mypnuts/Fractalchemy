"""Small, dependency-free helpers for 8-bit RGB triples."""

from __future__ import annotations

import colorsys
import math

RGB = tuple[int, int, int]


def clamp_channel(value: float) -> int:
    """Round and clamp a channel value into the 8-bit range 0..255."""
    return max(0, min(255, int(round(value))))


def clamp_unit(value: float) -> float:
    """Clamp a float into 0.0..1.0."""
    return max(0.0, min(1.0, value))


def lerp_rgb(a: RGB, b: RGB, t: float) -> RGB:
    """Linearly blend two colours.

    Args:
        a: Colour at t = 0.
        b: Colour at t = 1.
        t: Blend factor; values outside 0..1 extrapolate and are clamped per channel.

    Returns:
        The blended 8-bit RGB triple.
    """
    return tuple(clamp_channel(ca + (cb - ca) * t) for ca, cb in zip(a, b))  # type: ignore[return-value]


def rgb_to_hex(rgb: RGB) -> str:
    """Format a colour as six upper-case hex digits without a leading '#'."""
    return "%02X%02X%02X" % rgb


def hex_to_rgb(text: str) -> RGB:
    """Parse 'RRGGBB' or '#RRGGBB' into an RGB triple.

    Raises:
        ValueError: If the text is not six hex digits.
    """
    text = text.strip().lstrip("#")
    return int(text[0:2], 16), int(text[2:4], 16), int(text[4:6], 16)


def luminance(rgb: RGB) -> float:
    """Rec. 709 relative luminance on the 0..255 scale (perceived brightness)."""
    r, g, b = rgb
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def hue(rgb: RGB) -> float:
    """Hue of a colour as a fraction 0..1 (0 = red, 1/3 = green, 2/3 = blue)."""
    r, g, b = (c / 255.0 for c in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[0]


HSL = tuple[float, float, float]  # hue, saturation, lightness, each 0..1


def rgb_to_hsl(rgb: RGB) -> HSL:
    """Convert 8-bit RGB to (hue, saturation, lightness) with every component in 0..1."""
    h, l, s = colorsys.rgb_to_hls(*(c / 255.0 for c in rgb))
    return h, s, l


def hsl_to_rgb(hue: float, saturation: float, lightness: float) -> RGB:
    """Convert (hue, saturation, lightness) in 0..1 back to clamped 8-bit RGB; hue wraps."""
    r, g, b = colorsys.hls_to_rgb(hue % 1.0, clamp_unit(lightness), clamp_unit(saturation))
    return clamp_channel(r * 255), clamp_channel(g * 255), clamp_channel(b * 255)


def distance(a: RGB, b: RGB) -> float:
    """Euclidean distance between two colours in RGB space."""
    return math.sqrt(sum((ca - cb) ** 2 for ca, cb in zip(a, b)))


def max_channel_delta(a: RGB, b: RGB) -> int:
    """Largest absolute per-channel difference between two colours."""
    return max(abs(ca - cb) for ca, cb in zip(a, b))
