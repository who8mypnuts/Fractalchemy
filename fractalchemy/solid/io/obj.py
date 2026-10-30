"""Wavefront OBJ (+ MTL): vertices with the colour extension (`v x y z r g b`), normals, UVs, a material."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..mesh import Mesh


def write_obj(mesh: Mesh, path: Path, texture: Path | None = None, name: str = "fractal") -> list[Path]:
    """Write `path` (and `path.with_suffix('.mtl')` when there are UVs and a texture). Returns the files written."""
    path = Path(path)
    written = [path]
    lines = [f"# Fractalchemy mesh: {mesh.vertex_count} vertices, {mesh.face_count} faces", f"o {name}"]
    mtl_path = None
    if texture is not None and mesh.uvs is not None:
        mtl_path = path.with_suffix(".mtl")
        lines.append(f"mtllib {mtl_path.name}")
        lines.append(f"usemtl {name}")
    v = mesh.vertices
    if mesh.colors is not None:
        c = np.clip(mesh.colors, 0.0, 1.0)
        lines.extend(f"v {x:.6g} {y:.6g} {z:.6g} {r:.4f} {g:.4f} {b:.4f}" for (x, y, z), (r, g, b) in zip(v.tolist(), c.tolist()))
    else:
        lines.extend(f"v {x:.6g} {y:.6g} {z:.6g}" for x, y, z in v.tolist())
    has_uv = mesh.uvs is not None
    has_n = mesh.normals is not None
    if has_uv:
        lines.extend(f"vt {u:.6f} {w:.6f}" for u, w in mesh.uvs.tolist())
    if has_n:
        lines.extend(f"vn {x:.5f} {y:.5f} {z:.5f}" for x, y, z in mesh.normals.tolist())
    f = mesh.faces + 1
    if has_uv and has_n:
        lines.extend(f"f {a}/{a}/{a} {b}/{b}/{b} {c}/{c}/{c}" for a, b, c in f.tolist())
    elif has_uv:
        lines.extend(f"f {a}/{a} {b}/{b} {c}/{c}" for a, b, c in f.tolist())
    elif has_n:
        lines.extend(f"f {a}//{a} {b}//{b} {c}//{c}" for a, b, c in f.tolist())
    else:
        lines.extend(f"f {a} {b} {c}" for a, b, c in f.tolist())
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    if mtl_path is not None:
        mtl_path.write_text(f"newmtl {name}\nKa 1.0 1.0 1.0\nKd 1.0 1.0 1.0\nKs 0.2 0.2 0.2\nNs 24\nmap_Kd {Path(texture).name}\n", encoding="utf-8")
        written.append(mtl_path)
    return written


def read_obj(path: Path) -> Mesh:
    """Read an OBJ: positions (with optional colours), normals and UVs (re-indexed per vertex), polygons fan-triangulated.

    Raises:
        ValueError: When the file has no faces / vertices.
    """
    positions, colors, normals, uvs = [], [], [], []
    corners: list[tuple[int, int | None, int | None]] = []
    faces: list[list[int]] = []
    for raw in Path(path).read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split()
        tag = parts[0]
        if tag == "v" and len(parts) >= 4:
            positions.append([float(parts[1]), float(parts[2]), float(parts[3])])
            if len(parts) >= 7:
                colors.append([float(parts[4]), float(parts[5]), float(parts[6])])
        elif tag == "vn" and len(parts) >= 4:
            normals.append([float(parts[1]), float(parts[2]), float(parts[3])])
        elif tag == "vt" and len(parts) >= 3:
            uvs.append([float(parts[1]), float(parts[2])])
        elif tag == "f" and len(parts) >= 4:
            poly = []
            for token in parts[1:]:
                fields = token.split("/")
                vi = int(fields[0])
                ti = int(fields[1]) if len(fields) > 1 and fields[1] else None
                ni = int(fields[2]) if len(fields) > 2 and fields[2] else None
                vi = vi - 1 if vi > 0 else len(positions) + vi
                ti = None if ti is None else (ti - 1 if ti > 0 else len(uvs) + ti)
                ni = None if ni is None else (ni - 1 if ni > 0 else len(normals) + ni)
                poly.append(len(corners))
                corners.append((vi, ti, ni))
            for i in range(1, len(poly) - 1):
                faces.append([poly[0], poly[i], poly[i + 1]])
    if not positions or not faces:
        raise ValueError(f"{Path(path).name}: no mesh in the file")
    # one vertex per distinct (position, uv, normal) corner
    keys = np.array([(vi, -1 if ti is None else ti, -1 if ni is None else ni) for vi, ti, ni in corners], dtype=np.int64)
    unique, inverse = np.unique(keys, axis=0, return_inverse=True)
    inverse = inverse.reshape(-1)
    pos = np.asarray(positions, dtype=np.float64)[unique[:, 0]]
    mesh = Mesh(pos, inverse[np.asarray(faces, dtype=np.int64)])
    if colors and len(colors) == len(positions):
        mesh.colors = np.asarray(colors, dtype=np.float32)[unique[:, 0]]
    if uvs and (unique[:, 1] >= 0).all():
        mesh.uvs = np.asarray(uvs, dtype=np.float32)[unique[:, 1]]
    if normals and (unique[:, 2] >= 0).all():
        mesh.normals = np.asarray(normals, dtype=np.float64)[unique[:, 2]]
    else:
        mesh.compute_normals()
    return mesh


__all__ = ["write_obj", "read_obj"]
