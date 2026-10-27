"""A small OpenEXR writer: scanline, single-part, ZIP-compressed, float or half channels, with metadata.

Written here rather than through a binding because the format is simple, the official Python
package is a heavy optional wheel, and we want to embed our own attributes. The layout follows the
OpenEXR file-format specification:

    magic · version · header attributes (name\\0 type\\0 size value …) \\0 · chunk offset table · chunks

Each ZIP chunk holds 16 scanlines; its payload is the scanlines' channel rows (channels in header
order, i.e. alphabetical), byte-interleaved into two halves and delta-predicted before zlib —
exactly what `ImfZip.cpp` does, so any OpenEXR reader decodes it.

Values are written **linear**: DCCs treat EXR as scene/linear light, so display-referred output is
linearised with the inverse sRGB curve and the conversion is recorded in the attributes.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

MAGIC = 20000630
VERSION = 2
COMPRESSION_NONE, COMPRESSION_ZIP = 0, 3
PIXEL_HALF, PIXEL_FLOAT = 1, 2
LINES_PER_CHUNK = 16


def srgb_to_linear(values: np.ndarray) -> np.ndarray:
    """Inverse sRGB transfer function on 0..1 values (float32 in, float32 out)."""
    v = np.asarray(values, dtype=np.float32)
    return np.where(v <= 0.04045, v / 12.92, np.power((v + 0.055) / 1.055, 2.4)).astype(np.float32)


def write_exr(path: str | Path, channels: dict[str, np.ndarray], attributes: dict[str, str] | None = None,
              half: bool = False, compress: bool = True) -> None:
    """Write float channels (e.g. {"R": …, "G": …, "B": …, "A": …}, each (H, W) float) as an EXR file.

    Args:
        path: Destination.
        channels: Channel name → (H, W) array; all the same shape.
        attributes: Extra string attributes (metadata) to store in the header.
        half: Store 16-bit half floats instead of 32-bit floats.
        compress: ZIP-compress the scanlines (recommended; lossless).
    """
    names = sorted(channels)                       # OpenEXR stores channels alphabetically
    height, width = channels[names[0]].shape
    dtype = "<f2" if half else "<f4"
    pixel_type = PIXEL_HALF if half else PIXEL_FLOAT
    planes = [np.ascontiguousarray(channels[n], dtype=dtype) for n in names]
    header = _header(names, width, height, pixel_type, compress, attributes or {})
    lines_per_chunk = LINES_PER_CHUNK if compress else 1
    chunk_count = -(-height // lines_per_chunk)
    chunks = []
    for y0 in range(0, height, lines_per_chunk):
        raw = _chunk_bytes(planes, y0, min(lines_per_chunk, height - y0))
        data = _zip(raw) if compress else raw
        chunks.append(struct.pack("<ii", y0, len(data)) + data)
    offset = len(header) + 8 * chunk_count
    table = bytearray()
    for chunk in chunks:
        table += struct.pack("<Q", offset)
        offset += len(chunk)
    with open(path, "wb") as f:
        f.write(header)
        f.write(table)
        for chunk in chunks:
            f.write(chunk)


def _chunk_bytes(planes: list[np.ndarray], y0: int, lines: int) -> bytes:
    """Scanlines y0 .. y0+lines, each scanline = every channel's row in channel order."""
    parts = []
    for y in range(y0, y0 + lines):
        for plane in planes:
            parts.append(plane[y].tobytes())
    return b"".join(parts)


def _zip(raw: bytes) -> bytes:
    """OpenEXR ZIP pre-processing (interleave split + delta predictor) then zlib; raw if that is not smaller."""
    data = np.frombuffer(raw, dtype=np.uint8)
    half = (data.size + 1) // 2
    reordered = np.empty_like(data)
    reordered[:half] = data[0::2]
    reordered[half:] = data[1::2]
    predicted = reordered.astype(np.int16)
    predicted[1:] = (reordered[1:].astype(np.int16) - reordered[:-1].astype(np.int16) + 128) & 0xFF
    compressed = zlib.compress(predicted.astype(np.uint8).tobytes(), 6)
    return compressed if len(compressed) < len(raw) else raw


def _attribute(name: str, kind: str, value: bytes) -> bytes:
    return name.encode("ascii") + b"\0" + kind.encode("ascii") + b"\0" + struct.pack("<i", len(value)) + value


def _header(names: list[str], width: int, height: int, pixel_type: int, compress: bool, extra: dict[str, str]) -> bytes:
    chlist = b"".join(n.encode("ascii") + b"\0" + struct.pack("<iBBBBii", pixel_type, 0, 0, 0, 0, 1, 1) for n in names) + b"\0"
    box = struct.pack("<iiii", 0, 0, width - 1, height - 1)
    parts = [struct.pack("<ii", MAGIC, VERSION),
             _attribute("channels", "chlist", chlist),
             _attribute("compression", "compression", bytes([COMPRESSION_ZIP if compress else COMPRESSION_NONE])),
             _attribute("dataWindow", "box2i", box),
             _attribute("displayWindow", "box2i", box),
             _attribute("lineOrder", "lineOrder", bytes([0])),
             _attribute("pixelAspectRatio", "float", struct.pack("<f", 1.0)),
             _attribute("screenWindowCenter", "v2f", struct.pack("<ff", 0.0, 0.0)),
             _attribute("screenWindowWidth", "float", struct.pack("<f", 1.0))]
    for name, value in extra.items():
        parts.append(_attribute(name, "string", value.encode("utf-8")))
    parts.append(b"\0")
    return b"".join(parts)


def read_exr_attributes(path: str | Path) -> dict[str, str]:
    """The string attributes of an EXR header (our own metadata reader; values decoded as UTF-8)."""
    data = Path(path).read_bytes()
    magic, _version = struct.unpack_from("<ii", data, 0)
    if magic != MAGIC:
        raise ValueError("not an OpenEXR file")
    pos = 8
    found: dict[str, str] = {}
    while data[pos] != 0:
        end = data.index(b"\0", pos)
        name = data[pos:end].decode("ascii")
        pos = end + 1
        end = data.index(b"\0", pos)
        kind = data[pos:end].decode("ascii")
        pos = end + 1
        size = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        if kind == "string":
            found[name] = data[pos:pos + size].decode("utf-8", "replace")
        pos += size
    return found


__all__ = ["write_exr", "read_exr_attributes", "srgb_to_linear"]
