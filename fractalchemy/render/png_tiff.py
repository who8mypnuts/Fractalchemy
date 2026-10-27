"""Hand-written PNG and TIFF encoders for 16-bit RGB(A), which Pillow cannot write.

Both formats are simple enough to emit directly: PNG is a handful of CRC-checked chunks around a
zlib stream of filter-prefixed rows; baseline TIFF is a header, one image file directory and
deflate-compressed strips. Output is verified bit-exact by an independent decoder in the tests.
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path

import numpy as np

from .. import config

PARAMETERS_KEY = "flame"   # PNG tEXt keyword carrying the parameters


def to_8bit(image: np.ndarray) -> np.ndarray:
    """Round 16-bit channels to 8-bit (65535 → 255 exactly, halves rounded up)."""
    return ((image.astype(np.uint32) + 128) // 257).astype(np.uint8)


def png_bytes(image: np.ndarray, alpha: bool, depth16: bool, parameters: str) -> bytes:
    """Encode a (H, W, 4) uint16 array as PNG (RGB or RGBA, 8 or 16 bit) with an optional parameters text chunk."""
    height, width = image.shape[:2]
    pixels = image if alpha else image[..., :3]
    rows = np.ascontiguousarray(pixels).astype(">u2") if depth16 else to_8bit(pixels)
    raw = np.concatenate([np.zeros((height, 1), dtype=np.uint8), rows.reshape(height, -1).view(np.uint8)], axis=1)
    chunks = [_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 16 if depth16 else 8, 6 if alpha else 2, 0, 0, 0))]
    if parameters:
        chunks.append(_chunk(b"tEXt", PARAMETERS_KEY.encode("latin-1") + b"\0" + parameters.encode("latin-1", "replace")))
        chunks.append(_chunk(b"tEXt", b"Software\0" + f"{config.APP_NAME} {config.APP_VERSION}".encode("latin-1")))
    compressor = zlib.compressobj(6)
    data = bytearray()
    step = max(1, (1 << 24) // max(1, raw.shape[1]))   # compress in ~16 MB slabs
    for r0 in range(0, height, step):
        data += compressor.compress(raw[r0:r0 + step].tobytes())
    data += compressor.flush()
    chunks.append(_chunk(b"IDAT", bytes(data)))
    chunks.append(_chunk(b"IEND", b""))
    return b"\x89PNG\r\n\x1a\n" + b"".join(chunks)


def _chunk(kind: bytes, body: bytes) -> bytes:
    return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", zlib.crc32(kind + body) & 0xFFFFFFFF)


def write_png(path: Path, image: np.ndarray, alpha: bool, depth16: bool, parameters: str) -> None:
    """Write `png_bytes(...)` to `path`."""
    path.write_bytes(png_bytes(image, alpha, depth16, parameters))


def write_tiff16(path: Path, image: np.ndarray, alpha: bool, parameters: str) -> None:
    """Little-endian baseline TIFF, 16 bits per channel, deflate-compressed strips."""
    height, width = image.shape[:2]
    channels = 4 if alpha else 3
    pixels = np.ascontiguousarray(image if alpha else image[..., :3]).astype("<u2")
    rows_per_strip = max(1, (1 << 22) // max(1, width * channels * 2))
    strips = [zlib.compress(pixels[r:r + rows_per_strip].tobytes(), 6) for r in range(0, height, rows_per_strip)]
    entries = _tiff_entries(width, height, channels, alpha, rows_per_strip, strips, parameters)
    ifd_size = 2 + 12 * len(entries) + 4
    extras_offset = 8 + ifd_size
    extras_size = sum(_even(len(v)) for _, _, _, v in entries if len(v) > 4)
    data_offset = extras_offset + extras_size
    offsets = np.cumsum([data_offset] + [_even(len(s)) for s in strips[:-1]]).tolist()
    entries = [(tag, typ, count, _pack(4, offsets) if tag == 273 else value) for tag, typ, count, value in entries]
    ifd = bytearray(struct.pack("<H", len(entries)))
    extras = bytearray()
    for tag, typ, count, value in entries:
        if len(value) <= 4:
            ifd += struct.pack("<HHI", tag, typ, count) + value.ljust(4, b"\0")
        else:
            ifd += struct.pack("<HHII", tag, typ, count, extras_offset + len(extras))
            extras += value.ljust(_even(len(value)), b"\0")
    ifd += struct.pack("<I", 0)
    with open(path, "wb") as f:
        f.write(b"II*\0" + struct.pack("<I", 8) + ifd + extras)
        for s in strips:
            f.write(s.ljust(_even(len(s)), b"\0"))


def _tiff_entries(width, height, channels, alpha, rows_per_strip, strips, parameters) -> list[tuple[int, int, int, bytes]]:
    """Sorted IFD entries as (tag, type, count, packed value); strip offsets are a placeholder of the right size."""
    entries = [
        (256, 4, 1, _pack(4, [width])), (257, 4, 1, _pack(4, [height])),
        (258, 3, channels, _pack(3, [16] * channels)), (259, 3, 1, _pack(3, [8])), (262, 3, 1, _pack(3, [2])),
        (273, 4, len(strips), _pack(4, [0] * len(strips))), (277, 3, 1, _pack(3, [channels])),
        (278, 4, 1, _pack(4, [rows_per_strip])), (279, 4, len(strips), _pack(4, [len(s) for s in strips])),
        (284, 3, 1, _pack(3, [1])),
    ]
    if parameters:
        text = parameters.encode("utf-8") + b"\0"
        entries.append((270, 2, len(text), text))
    if alpha:
        entries.append((338, 3, 1, _pack(3, [2])))    # unassociated alpha
    return sorted(entries)


def _pack(typ: int, values) -> bytes:
    return b"".join(struct.pack({3: "<H", 4: "<I"}[typ], int(v)) for v in values)


def _even(n: int) -> int:
    return n + (n % 2)


__all__ = ["PARAMETERS_KEY", "to_8bit", "png_bytes", "write_png", "write_tiff16"]
