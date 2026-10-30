"""glTF 2.0: a GLB writer (positions, normals, `COLOR_0`, `TEXCOORD_0`, a PBR material with an embedded PNG texture
when there is one) and a reader for `.glb` / `.gltf` (embedded, data-URI or external buffers)."""

from __future__ import annotations

import base64
import io
import json
import struct
from pathlib import Path

import numpy as np

from ..mesh import Mesh

MAGIC = b"glTF"
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
FLOAT, UNSIGNED_BYTE, UNSIGNED_SHORT, UNSIGNED_INT = 5126, 5121, 5123, 5125
_DTYPES = {5120: np.int8, 5121: np.uint8, 5122: np.int16, 5123: np.uint16, 5125: np.uint32, 5126: np.float32}
_WIDTHS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def _pad(data: bytes, to: int = 4, fill: bytes = b"\0") -> bytes:
    return data + fill * (-len(data) % to)


def write_glb(mesh: Mesh, path: Path, texture: np.ndarray | None = None, name: str = "fractal") -> list[Path]:
    """Write a GLB; `texture` is an `(H, W, 3)` uint8 image used as the base colour through the mesh's UVs."""
    path = Path(path)
    buffer = bytearray()
    views, accessors = [], []

    def add(array: np.ndarray, component: int, kind: str, target: int | None, minmax: bool = False, normalized: bool = False) -> int:
        nonlocal buffer
        data = np.ascontiguousarray(array).tobytes()
        offset = len(buffer)
        buffer += _pad(data)
        view = {"buffer": 0, "byteOffset": offset, "byteLength": len(data)}
        if target is not None:
            view["target"] = target
        views.append(view)
        accessor = {"bufferView": len(views) - 1, "componentType": component, "count": int(array.shape[0]), "type": kind}
        if normalized:
            accessor["normalized"] = True
        if minmax:
            accessor["min"] = [float(v) for v in array.min(axis=0)]
            accessor["max"] = [float(v) for v in array.max(axis=0)]
        accessors.append(accessor)
        return len(accessors) - 1

    positions = mesh.vertices.astype(np.float32)
    attributes = {"POSITION": add(positions, FLOAT, "VEC3", 34962, minmax=True)}
    if mesh.normals is not None:
        attributes["NORMAL"] = add(mesh.normals.astype(np.float32), FLOAT, "VEC3", 34962)
    if mesh.colors is not None:
        attributes["COLOR_0"] = add(np.clip(mesh.colors, 0, 1).astype(np.float32), FLOAT, "VEC3", 34962)
    if mesh.uvs is not None:
        uv = mesh.uvs.astype(np.float32).copy()
        uv[:, 1] = 1.0 - uv[:, 1]                         # glTF's v runs downwards
        attributes["TEXCOORD_0"] = add(uv, FLOAT, "VEC2", 34962)
    indices = add(mesh.faces.astype(np.uint32).reshape(-1), UNSIGNED_INT, "SCALAR", 34963)
    material = {"name": name, "pbrMetallicRoughness": {"baseColorFactor": [1.0, 1.0, 1.0, 1.0], "metallicFactor": 0.0, "roughnessFactor": 0.7},
                "doubleSided": False}
    doc = {"asset": {"version": "2.0", "generator": "Fractalchemy"}, "scene": 0, "scenes": [{"nodes": [0]}],
           "nodes": [{"mesh": 0, "name": name}],
           "meshes": [{"name": name, "primitives": [{"attributes": attributes, "indices": indices, "material": 0, "mode": 4}]}],
           "materials": [material], "bufferViews": views, "accessors": accessors}
    if texture is not None and mesh.uvs is not None:
        from PIL import Image
        png = io.BytesIO()
        Image.fromarray(np.ascontiguousarray(texture)).save(png, format="PNG")
        data = png.getvalue()
        offset = len(buffer)
        buffer += _pad(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        doc["images"] = [{"bufferView": len(views) - 1, "mimeType": "image/png", "name": f"{name}_color"}]
        doc["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 33071, "wrapT": 33071}]
        doc["textures"] = [{"sampler": 0, "source": 0}]
        material["pbrMetallicRoughness"]["baseColorTexture"] = {"index": 0, "texCoord": 0}
    doc["buffers"] = [{"byteLength": len(buffer)}]
    json_bytes = _pad(json.dumps(doc, separators=(",", ":")).encode("utf-8"), fill=b" ")
    bin_bytes = _pad(bytes(buffer))
    total = 12 + 8 + len(json_bytes) + 8 + len(bin_bytes)
    with open(path, "wb") as fh:
        fh.write(MAGIC + struct.pack("<II", 2, total))
        fh.write(struct.pack("<II", len(json_bytes), JSON_CHUNK) + json_bytes)
        fh.write(struct.pack("<II", len(bin_bytes), BIN_CHUNK) + bin_bytes)
    return [path]


def read_gltf(path: Path) -> Mesh:
    """Read the first mesh of a `.glb` or `.gltf` (all its triangle primitives merged).

    Raises:
        ValueError: When the file is not glTF or has no triangle mesh.
    """
    path = Path(path)
    raw = path.read_bytes()
    binary = None
    if raw[:4] == MAGIC:
        length = struct.unpack("<I", raw[8:12])[0]
        offset = 12
        doc = None
        while offset < min(length, len(raw)):
            chunk_length, chunk_type = struct.unpack("<II", raw[offset:offset + 8])
            chunk = raw[offset + 8:offset + 8 + chunk_length]
            if chunk_type == JSON_CHUNK:
                doc = json.loads(chunk.decode("utf-8"))
            elif chunk_type == BIN_CHUNK:
                binary = chunk
            offset += 8 + chunk_length
        if doc is None:
            raise ValueError(f"{path.name}: GLB without a JSON chunk")
    else:
        try:
            doc = json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{path.name}: not a glTF file") from exc
    buffers = []
    for entry in doc.get("buffers", []):
        uri = entry.get("uri")
        if uri is None:
            buffers.append(binary or b"")
        elif uri.startswith("data:"):
            buffers.append(base64.b64decode(uri.split(",", 1)[1]))
        else:
            buffers.append((path.parent / uri).read_bytes())

    def accessor(index: int) -> np.ndarray:
        acc = doc["accessors"][index]
        view = doc["bufferViews"][acc["bufferView"]]
        dtype = np.dtype(_DTYPES[acc["componentType"]])
        width = _WIDTHS[acc["type"]]
        count = acc["count"]
        start = view.get("byteOffset", 0) + acc.get("byteOffset", 0)
        stride = view.get("byteStride", 0)
        data = buffers[view["buffer"]]
        if stride and stride != dtype.itemsize * width:
            rows = np.frombuffer(data, dtype=np.uint8, count=stride * (count - 1) + dtype.itemsize * width, offset=start)
            rows = np.lib.stride_tricks.as_strided(rows, shape=(count, dtype.itemsize * width), strides=(stride, 1))
            array = np.ascontiguousarray(rows).view(dtype).reshape(count, width)
        else:
            array = np.frombuffer(data, dtype=dtype, count=count * width, offset=start).reshape(count, width)
        array = array.astype(np.float64) if dtype.kind == "f" else array.astype(np.int64)
        if acc.get("normalized") and dtype.kind == "u":
            array = array / np.iinfo(dtype).max
        return array

    meshes = doc.get("meshes", [])
    if not meshes:
        raise ValueError(f"{path.name}: no mesh")
    parts: list[Mesh] = []
    for primitive in meshes[0].get("primitives", []):
        if primitive.get("mode", 4) != 4:
            continue
        attributes = primitive["attributes"]
        positions = accessor(attributes["POSITION"])
        if "indices" in primitive:
            faces = accessor(primitive["indices"]).reshape(-1, 3)
        else:
            faces = np.arange(positions.shape[0]).reshape(-1, 3)
        part = Mesh(positions, faces)
        if "NORMAL" in attributes:
            part.normals = accessor(attributes["NORMAL"])
        if "COLOR_0" in attributes:
            part.colors = accessor(attributes["COLOR_0"])[:, :3].astype(np.float32)
        if "TEXCOORD_0" in attributes:
            uv = accessor(attributes["TEXCOORD_0"]).astype(np.float32)
            uv[:, 1] = 1.0 - uv[:, 1]
            part.uvs = uv
        parts.append(part)
    if not parts:
        raise ValueError(f"{path.name}: no triangle primitive")
    mesh = parts[0] if len(parts) == 1 else _merge(parts)
    if mesh.normals is None:
        mesh.compute_normals()
    return mesh


def _merge(parts: list[Mesh]) -> Mesh:
    offsets = np.cumsum([0] + [p.vertex_count for p in parts[:-1]])
    vertices = np.concatenate([p.vertices for p in parts])
    faces = np.concatenate([p.faces + o for p, o in zip(parts, offsets)])
    normals = np.concatenate([p.normals for p in parts]) if all(p.normals is not None for p in parts) else None
    colors = np.concatenate([p.colors for p in parts]) if all(p.colors is not None for p in parts) else None
    uvs = np.concatenate([p.uvs for p in parts]) if all(p.uvs is not None for p in parts) else None
    return Mesh(vertices, faces, normals, colors, uvs)


__all__ = ["write_glb", "read_gltf"]
