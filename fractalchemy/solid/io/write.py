"""The export formats and one `write_mesh()` entry point."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ..mesh import Mesh
from .gltf import write_glb
from .obj import write_obj
from .ply import write_ply
from .stl import write_stl
from .usd import usd_core_available, write_usd


@dataclass(frozen=True)
class ExportFormat:
    """One mesh file format.

    Attributes:
        key: Identifier stored in settings.
        label: Name shown in the UI.
        extension: File suffix.
        colors: Carries vertex colours.
        texture: Carries UVs and can reference a texture.
        available: Writable in this installation.
        hint: Why not, when not available.
    """
    key: str
    label: str
    extension: str
    colors: bool = True
    texture: bool = True
    available: bool = True
    hint: str = ""


EXPORT_FORMATS: tuple[ExportFormat, ...] = (
    ExportFormat("obj", "Wavefront OBJ (+ MTL)", ".obj"),
    ExportFormat("stl", "STL (binary, geometry only)", ".stl", colors=False, texture=False),
    ExportFormat("ply", "PLY (binary)", ".ply"),
    ExportFormat("glb", "glTF binary (GLB)", ".glb"),
    ExportFormat("usda", "OpenUSD text (.usda)", ".usda"),
    ExportFormat("usdc", "OpenUSD binary (.usdc)", ".usdc", available=usd_core_available(), hint="install usd-core"),
    ExportFormat("usdz", "OpenUSD package (.usdz)", ".usdz", available=usd_core_available(), hint="install usd-core"),
)


def export_format(key: str) -> ExportFormat:
    """The format called `key` (OBJ when unknown)."""
    for fmt in EXPORT_FORMATS:
        if fmt.key == key:
            return fmt
    return EXPORT_FORMATS[0]


def write_mesh(mesh: Mesh, path: Path, fmt: ExportFormat | str, texture: Path | None = None, name: str = "fractal",
               meters_per_unit: float = 1.0) -> list[Path]:
    """Write `mesh` as `fmt` to `path` (the suffix is made to match). `texture` is a PNG beside it for formats with UVs.

    Returns the files written.

    Raises:
        ValueError: For a format that is not available here.
        OSError: When a file cannot be written.
    """
    fmt = export_format(fmt) if isinstance(fmt, str) else fmt
    if not fmt.available:
        raise ValueError(f"{fmt.label} is not available: {fmt.hint}")
    path = Path(path)
    if path.suffix.lower() != fmt.extension:
        path = path.with_suffix(fmt.extension)
    path.parent.mkdir(parents=True, exist_ok=True)
    out = mesh
    if not fmt.colors and out.colors is not None:
        out = out.copy()
        out.colors = None
    if not fmt.texture and out.uvs is not None:
        out = out.copy()
        out.uvs = None
    if fmt.key == "obj":
        return write_obj(out, path, texture, name)
    if fmt.key == "stl":
        return write_stl(out, path, name)
    if fmt.key == "ply":
        return write_ply(out, path, name)
    if fmt.key == "glb":
        image = None
        if texture is not None and out.uvs is not None:
            from PIL import Image
            with Image.open(texture) as im:
                image = np.asarray(im.convert("RGB"))
        return write_glb(out, path, image, name)
    return write_usd(out, path, texture, name, meters_per_unit)


__all__ = ["ExportFormat", "EXPORT_FORMATS", "export_format", "write_mesh"]
