"""Tiny helpers for writing XML by hand (the flame and Chaotica writers share them)."""

from __future__ import annotations


def number_text(value: float) -> str:
    """Shortest text that reads back to the same float (`1.0` → `1`)."""
    text = repr(float(value))
    return text[:-2] if text.endswith(".0") else text


def attr_text(text: str) -> str:
    """Escape a string for use inside a double-quoted XML attribute."""
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")
