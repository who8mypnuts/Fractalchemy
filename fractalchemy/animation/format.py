"""The `.faanim` file: JSON, one animation per file.

    {"format": "fractalchemy-animation", "version": 1, ... Animation.to_dict() ...}

Like `.fa`, JSON keeps it diff-friendly and extensible: unknown keys are ignored and missing
keys take defaults (`Animation.from_dict`). Every keyframe carries a complete flame (as in `.fa`),
so an animation file stands on its own.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import Animation

FORMAT_ID = "fractalchemy-animation"
FORMAT_VERSION = 1
EXTENSION = ".faanim"
FILE_FILTER = "Fractalchemy animations (*.faanim)"


class AnimationParseError(ValueError):
    """The text / file is not a Fractalchemy animation."""


def animation_to_text(animation: Animation) -> str:
    """The JSON text of an animation."""
    return json.dumps({"format": FORMAT_ID, "version": FORMAT_VERSION, **animation.to_dict()}, indent=1)


def animation_from_text(text: str) -> Animation:
    """An animation from its JSON text.

    Raises:
        AnimationParseError: Not JSON, or not an animation document.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise AnimationParseError(f"not a Fractalchemy animation: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != FORMAT_ID or not isinstance(data.get("keyframes", []), list):
        raise AnimationParseError("not a Fractalchemy animation (expected a .faanim document)")
    try:
        return Animation.from_dict(data)
    except (TypeError, ValueError, KeyError) as exc:
        raise AnimationParseError(f"damaged animation: {exc}") from exc


def load_animation(path: str | Path) -> Animation:
    """Read a `.faanim` file."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AnimationParseError(f"cannot read {path.name}: {exc}") from exc
    return animation_from_text(text)


def save_animation(animation: Animation, path: str | Path) -> Path:
    """Write the animation to `path` (`.faanim` is appended when the suffix is something else); returns the path."""
    path = Path(path)
    if path.suffix.lower() != EXTENSION:
        path = path.with_name(path.name + EXTENSION)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(animation_to_text(animation), encoding="utf-8")
    tmp.replace(path)
    return path


__all__ = ["animation_to_text", "animation_from_text", "load_animation", "save_animation", "AnimationParseError",
           "EXTENSION", "FILE_FILTER", "FORMAT_ID"]
