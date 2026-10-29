"""The `.fa3d` file: a 3D Editor scene as JSON.

    {"format": "fa3d", "version": 1, "scene": {… Scene3D.to_dict() …}}

The flame inside is the same dict the `.fa` format writes, so a `.fa3d` carries a complete fractal; the rest
(materials, lights, environment, later the assets and instancers) is what `.fa` should not carry.
"""

from __future__ import annotations

import json
from pathlib import Path

from .model import FORMAT_VERSION, Scene3D

EXTENSION = ".fa3d"
FILE_FILTER = "Fractalchemy 3D scenes (*.fa3d);;All files (*)"


class Scene3DFormatError(ValueError):
    """The file is not a `.fa3d` scene."""


def scene_to_text(scene: Scene3D) -> str:
    """The scene as `.fa3d` text."""
    return json.dumps({"format": "fa3d", "version": FORMAT_VERSION, "scene": scene.to_dict()}, indent=1)


def scene_from_text(text: str) -> Scene3D:
    """Parse `.fa3d` text.

    Raises:
        Scene3DFormatError: When the text is not a scene.
    """
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise Scene3DFormatError(f"not a .fa3d file: {exc}") from exc
    if not isinstance(data, dict) or data.get("format") != "fa3d" or not isinstance(data.get("scene"), dict):
        raise Scene3DFormatError("not a .fa3d file (no 'format': 'fa3d' / 'scene')")
    return Scene3D.from_dict(data["scene"])


def save_scene(scene: Scene3D, path: Path) -> None:
    """Write the scene to `path` (the folder is created)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(scene_to_text(scene), encoding="utf-8")


def load_scene(path: Path) -> Scene3D:
    """Read a scene from `path`.

    Raises:
        Scene3DFormatError: When the file is not a scene.
        OSError: When it cannot be read.
    """
    return scene_from_text(path.read_text(encoding="utf-8"))


__all__ = ["EXTENSION", "FILE_FILTER", "Scene3DFormatError", "scene_to_text", "scene_from_text", "save_scene", "load_scene"]
