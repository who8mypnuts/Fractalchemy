"""Human formatting of the quantities the renderer talks about: counts, durations, bytes, aspect ratios.

Qt-free, so the status bar, the Render window and the details report all phrase "12.3 M samples/s"
or "3 min 07 s" the same way.
"""

from __future__ import annotations

import math


def format_count(value: float, precision: int = 3) -> str:
    """A large count with an SI letter: '1.23 G', '12.3 M', '456 k', '42'.

    Args:
        value: The number.
        precision: Significant digits for the scaled number.
    """
    for letter, scale in (("G", 1e9), ("M", 1e6), ("k", 1e3)):
        text = f"{value / scale:.{precision}g}"
        if abs(float(text)) >= 1.0:          # judged after rounding, so 999 999 999 reads "1 G", not "1e+03 M"
            return f"{text} {letter}"
    return f"{value:.0f}"


def format_rate(samples_per_second: float) -> str:
    """'12.3 M samples/s'."""
    return f"{format_count(samples_per_second)} samples/s"


def format_seconds(seconds: float | None) -> str:
    """'—' for unknown, else '42 s', '3 min 07 s', '2 h 15 min', '3 d 4 h'.

    Sub-minute times keep one decimal ('4.2 s') so short renders still read meaningfully.
    """
    if seconds is None:
        return "—"
    seconds = max(0.0, float(seconds))
    if seconds < 60:
        return f"{seconds:.1f} s" if seconds < 10 else f"{seconds:.0f} s"
    minutes, sec = divmod(int(round(seconds)), 60)
    if minutes < 60:
        return f"{minutes} min {sec:02d} s"
    hours, minutes = divmod(minutes, 60)
    if hours < 48:
        return f"{hours} h {minutes:02d} min"
    days, hours = divmod(hours, 24)
    return f"{days} d {hours} h"


def format_bytes(n: float) -> str:
    """'1.23 GB' style (decimal units)."""
    for unit in ("B", "kB", "MB", "GB", "TB"):
        if abs(n) < 1000 or unit == "TB":
            return f"{n:.0f} {unit}" if unit == "B" else f"{n:.2f} {unit}"
        n /= 1000.0
    return f"{n:.2f} TB"


def format_memory(n: int) -> str:
    """Binary-unit memory size as the Render window plans it: '768 MB', '1.5 GB'."""
    return f"{n / (1 << 30):,.1f} GB" if n >= (1 << 30) else f"{n / (1 << 20):,.0f} MB"


def aspect_text(width: int, height: int, separator: str = " : ") -> str:
    """Reduced aspect ratio ('16 : 9'), or a decimal ratio when the reduced terms are unwieldy ('1.667 : 1')."""
    width, height = max(1, int(width)), max(1, int(height))
    g = math.gcd(width, height)
    a, b = width // g, height // g
    if a > 50 or b > 50:
        return f"{width / height:.3f}{separator}1"
    return f"{a}{separator}{b}"


__all__ = ["format_count", "format_rate", "format_seconds", "format_bytes", "format_memory", "aspect_text"]
