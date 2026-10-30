"""Reading meshes: OBJ, STL, PLY, glTF / GLB and USD, by file suffix."""

from __future__ import annotations

from pathlib import Path

from ..mesh import Mesh
from .gltf import read_gltf
from .obj import read_obj
from .ply import read_ply
from .stl import read_stl
from .usd import read_usd

READERS = {".obj": read_obj, ".stl": read_stl, ".ply": read_ply, ".glb": read_gltf, ".gltf": read_gltf,
           ".usda": read_usd, ".usdc": read_usd, ".usdz": read_usd, ".usd": read_usd}
MESH_READ_FILTER = "Meshes (*.obj *.stl *.ply *.glb *.gltf *.usd *.usda *.usdc *.usdz);;All files (*)"


def read_mesh(path: Path | str) -> Mesh:
    """Read a mesh file.

    Raises:
        ValueError: For an unknown suffix or a file the reader cannot parse.
        OSError: When the file cannot be read.
    """
    path = Path(path)
    reader = READERS.get(path.suffix.lower())
    if reader is None:
        raise ValueError(f"{path.name}: unknown mesh format '{path.suffix}' (known: {', '.join(sorted(READERS))})")
    return reader(path)


__all__ = ["read_mesh", "READERS", "MESH_READ_FILTER"]
