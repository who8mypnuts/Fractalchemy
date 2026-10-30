"""Binary STL: geometry only (the print format)."""

from __future__ import annotations

import struct
from pathlib import Path

import numpy as np

from ..mesh import Mesh

HEADER = 80


def write_stl(mesh: Mesh, path: Path, name: str = "fractal") -> list[Path]:
    """Write a binary STL; returns `[path]`."""
    path = Path(path)
    f = mesh.faces
    n = f.shape[0]
    record = np.zeros(n, dtype=np.dtype([("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")]))
    record["normal"] = mesh.face_normals().astype(np.float32)
    record["v"] = mesh.vertices[f].astype(np.float32)
    header = f"Fractalchemy {name}".encode("ascii", "replace")[:HEADER].ljust(HEADER, b"\0")
    with open(path, "wb") as fh:
        fh.write(header)
        fh.write(struct.pack("<I", n))
        fh.write(record.tobytes())
    return [path]


def read_stl(path: Path) -> Mesh:
    """Read a binary or ASCII STL (vertices welded).

    Raises:
        ValueError: When the file is not an STL.
    """
    path = Path(path)
    data = path.read_bytes()
    if len(data) < HEADER + 4:
        raise ValueError(f"{path.name}: not an STL file")
    count = struct.unpack("<I", data[HEADER:HEADER + 4])[0]
    if len(data) == HEADER + 4 + count * 50:
        record = np.frombuffer(data[HEADER + 4:], dtype=np.dtype([("normal", "<f4", 3), ("v", "<f4", (3, 3)), ("attr", "<u2")]), count=count)
        triangles = record["v"].astype(np.float64)
    else:
        text = data.decode("ascii", errors="replace")
        if "facet" not in text:
            raise ValueError(f"{path.name}: not an STL file")
        verts = [list(map(float, line.split()[1:4])) for line in text.splitlines() if line.strip().startswith("vertex")]
        if len(verts) % 3:
            raise ValueError(f"{path.name}: malformed ASCII STL")
        triangles = np.asarray(verts, dtype=np.float64).reshape(-1, 3, 3)
    flat = triangles.reshape(-1, 3)
    mesh = Mesh(flat, np.arange(flat.shape[0]).reshape(-1, 3)).weld(1e-9 * max(float(np.ptp(flat, axis=0).max()), 1e-9) if flat.shape[0] else None)
    mesh.compute_normals()
    return mesh


__all__ = ["write_stl", "read_stl"]
