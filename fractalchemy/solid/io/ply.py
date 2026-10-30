"""PLY (binary little-endian writer; binary and ASCII reader): positions, normals, colours, UVs."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..mesh import Mesh


def write_ply(mesh: Mesh, path: Path, name: str = "fractal") -> list[Path]:
    path = Path(path)
    fields = [("x", "<f4"), ("y", "<f4"), ("z", "<f4")]
    header = ["ply", "format binary_little_endian 1.0", f"comment Fractalchemy {name}", f"element vertex {mesh.vertex_count}",
              "property float x", "property float y", "property float z"]
    if mesh.normals is not None:
        fields += [("nx", "<f4"), ("ny", "<f4"), ("nz", "<f4")]
        header += ["property float nx", "property float ny", "property float nz"]
    if mesh.colors is not None:
        fields += [("red", "u1"), ("green", "u1"), ("blue", "u1")]
        header += ["property uchar red", "property uchar green", "property uchar blue"]
    if mesh.uvs is not None:
        fields += [("s", "<f4"), ("t", "<f4")]
        header += ["property float s", "property float t"]
    header += [f"element face {mesh.face_count}", "property list uchar int vertex_indices", "end_header"]
    vertices = np.zeros(mesh.vertex_count, dtype=np.dtype(fields))
    vertices["x"], vertices["y"], vertices["z"] = mesh.vertices.T.astype(np.float32)
    if mesh.normals is not None:
        vertices["nx"], vertices["ny"], vertices["nz"] = mesh.normals.T.astype(np.float32)
    if mesh.colors is not None:
        rgb = np.clip(mesh.colors * 255.0 + 0.5, 0, 255).astype(np.uint8)
        vertices["red"], vertices["green"], vertices["blue"] = rgb.T
    if mesh.uvs is not None:
        vertices["s"], vertices["t"] = mesh.uvs.T.astype(np.float32)
    faces = np.zeros(mesh.face_count, dtype=np.dtype([("n", "u1"), ("i", "<i4", 3)]))
    faces["n"] = 3
    faces["i"] = mesh.faces.astype(np.int32)
    with open(path, "wb") as fh:
        fh.write(("\n".join(header) + "\n").encode("ascii"))
        fh.write(vertices.tobytes())
        fh.write(faces.tobytes())
    return [path]


_TYPES = {"char": "i1", "uchar": "u1", "int8": "i1", "uint8": "u1", "short": "i2", "ushort": "u2", "int16": "i2", "uint16": "u2",
          "int": "i4", "uint": "u4", "int32": "i4", "uint32": "u4", "float": "f4", "float32": "f4", "double": "f8", "float64": "f8"}


def read_ply(path: Path) -> Mesh:
    """Read a PLY with a vertex element (x y z [nx ny nz] [red green blue] [s t | u v]) and a face list.

    Raises:
        ValueError: When the file is not a PLY this reader understands.
    """
    path = Path(path)
    data = path.read_bytes()
    end = data.find(b"end_header")
    if not data.startswith(b"ply") or end < 0:
        raise ValueError(f"{path.name}: not a PLY file")
    header_end = data.find(b"\n", end) + 1
    header = data[:header_end].decode("ascii", errors="replace").splitlines()
    fmt = "ascii"
    elements: list[tuple[str, int, list]] = []
    for line in header:
        parts = line.split()
        if not parts:
            continue
        if parts[0] == "format":
            fmt = parts[1]
        elif parts[0] == "element":
            elements.append((parts[1], int(parts[2]), []))
        elif parts[0] == "property" and elements:
            if parts[1] == "list":
                elements[-1][2].append(("list", parts[2], parts[3], parts[4]))
            else:
                elements[-1][2].append(("scalar", parts[1], parts[2]))
    body = data[header_end:]
    vertex_array = None
    faces = None
    if fmt == "ascii":
        tokens = body.decode("ascii", errors="replace").split()
        pos = 0
        for name, count, props in elements:
            if name == "vertex":
                width = len(props)
                rows = np.array(tokens[pos:pos + count * width], dtype=np.float64).reshape(count, width)
                pos += count * width
                vertex_array = {p[2]: rows[:, i] for i, p in enumerate(props)}
            elif name == "face":
                out = []
                for _ in range(count):
                    n = int(tokens[pos])
                    idx = [int(t) for t in tokens[pos + 1:pos + 1 + n]]
                    pos += 1 + n
                    for i in range(1, n - 1):
                        out.append([idx[0], idx[i], idx[i + 1]])
                faces = np.asarray(out, dtype=np.int64).reshape(-1, 3)
            else:
                for _ in range(count):
                    pos += sum(1 + int(tokens[pos]) if p[0] == "list" else 1 for p in props)
    else:
        endian = "<" if "little" in fmt else ">"
        offset = 0
        for name, count, props in elements:
            if all(p[0] == "scalar" for p in props):
                dtype = np.dtype([(p[2], endian + _TYPES[p[1]]) for p in props])
                rows = np.frombuffer(body, dtype=dtype, count=count, offset=offset)
                offset += count * dtype.itemsize
                if name == "vertex":
                    vertex_array = {p[2]: rows[p[2]].astype(np.float64) for p in props}
            elif name == "face" and len(props) == 1 and props[0][0] == "list":
                count_type = np.dtype(endian + _TYPES[props[0][1]])
                index_type = np.dtype(endian + _TYPES[props[0][2]])
                out = []
                for _ in range(count):
                    n = int(np.frombuffer(body, dtype=count_type, count=1, offset=offset)[0])
                    offset += count_type.itemsize
                    idx = np.frombuffer(body, dtype=index_type, count=n, offset=offset).astype(np.int64)
                    offset += n * index_type.itemsize
                    for i in range(1, n - 1):
                        out.append([idx[0], idx[i], idx[i + 1]])
                faces = np.asarray(out, dtype=np.int64).reshape(-1, 3)
            else:
                raise ValueError(f"{path.name}: PLY element '{name}' is not supported")
    if vertex_array is None or faces is None:
        raise ValueError(f"{path.name}: no vertices / faces")
    mesh = Mesh(np.stack([vertex_array["x"], vertex_array["y"], vertex_array["z"]], axis=1), faces)
    if all(k in vertex_array for k in ("nx", "ny", "nz")):
        mesh.normals = np.stack([vertex_array["nx"], vertex_array["ny"], vertex_array["nz"]], axis=1)
    else:
        mesh.compute_normals()
    if all(k in vertex_array for k in ("red", "green", "blue")):
        mesh.colors = (np.stack([vertex_array["red"], vertex_array["green"], vertex_array["blue"]], axis=1) / 255.0).astype(np.float32)
    for u_key, v_key in (("s", "t"), ("u", "v"), ("texture_u", "texture_v")):
        if u_key in vertex_array and v_key in vertex_array:
            mesh.uvs = np.stack([vertex_array[u_key], vertex_array[v_key]], axis=1).astype(np.float32)
            break
    return mesh


__all__ = ["write_ply", "read_ply"]
