"""HDRI environments: readers for Radiance `.hdr` (RGBE) and OpenEXR (scanline, half / float, none / ZIP / ZIPS —
the mirror of `render/exr.py`), LDR images through Pillow, and an equirectangular map ready for lighting.

`EnvironmentMap` holds the linear-RGB image, its **SH9 projection** (irradiance for the diffuse term — Ramamoorthi &
Hanrahan's nine coefficients), **prefiltered levels** (increasingly blurred copies for the specular term by material
roughness, and for the blurred background) and the lookup. **Key lights** can be extracted from the map: the
brightest regions become distant lights with shadows — HDRI lighting with shadows without path tracing.

Directions are world vectors of the fractal's space with +z up: `u` runs around z (from +x towards +y), `v` from the
top (+z) to the bottom. `rotation` turns the map about z. `load_environment()` caches by path and modification time
(the render threads read it for every frame).
"""

from __future__ import annotations

import math
import struct
import threading
import zlib
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from scipy import ndimage

EXR_MAGIC = 20000630
PIXEL_UINT, PIXEL_HALF, PIXEL_FLOAT = 0, 1, 2
COMPRESSION_NONE, COMPRESSION_RLE, COMPRESSION_ZIPS, COMPRESSION_ZIP = 0, 1, 2, 3
MAP_WIDTH = 512                     # the working size of the map (the file may be far larger)
LEVELS = 6                          # prefiltered levels (level 0 sharp … level 5 very blurred)
KEY_LIGHT_RADIUS = 30.0             # degrees suppressed around an extracted light


class HdriError(ValueError):
    """The file is not an image this module can read."""


# --- readers ----------------------------------------------------------------------------------------------------------
def read_hdr(path: Path | str) -> np.ndarray:
    """A Radiance RGBE `.hdr` as `(H, W, 3)` float32 linear RGB.

    Raises:
        HdriError: When the file is not RGBE.
    """
    data = Path(path).read_bytes()
    if not data.startswith(b"#?"):
        raise HdriError(f"{Path(path).name}: not a Radiance HDR file")
    pos = 0
    width = height = None
    while True:
        end = data.find(b"\n", pos)
        if end < 0:
            raise HdriError(f"{Path(path).name}: truncated header")
        line = data[pos:end].strip()
        pos = end + 1
        if line.startswith(b"-Y") or line.startswith(b"+Y"):
            parts = line.split()
            if len(parts) != 4 or parts[2] not in (b"+X", b"-X"):
                raise HdriError(f"{Path(path).name}: unsupported orientation {line!r}")
            height, width = int(parts[1]), int(parts[3])
            flip_y = parts[0] == b"+Y"
            flip_x = parts[2] == b"-X"
            break
    if width is None or width <= 0 or height <= 0:
        raise HdriError(f"{Path(path).name}: no resolution line")
    raw = np.frombuffer(data, dtype=np.uint8, offset=pos)
    rgbe = np.empty((height, width, 4), dtype=np.uint8)
    i = 0
    for y in range(height):
        if 8 <= width < 32768 and i + 4 <= raw.size and raw[i] == 2 and raw[i + 1] == 2 and (raw[i + 2] << 8 | raw[i + 3]) == width:
            i += 4
            for ch in range(4):                                  # new-style run-length encoding, one channel at a time
                x = 0
                row = rgbe[y, :, ch]
                while x < width:
                    count = int(raw[i])
                    i += 1
                    if count > 128:
                        count -= 128
                        row[x:x + count] = raw[i]
                        i += 1
                    else:
                        row[x:x + count] = raw[i:i + count]
                        i += count
                    x += count
        else:                                                   # flat RGBE
            rgbe[y] = raw[i:i + width * 4].reshape(width, 4)
            i += width * 4
    exponent = rgbe[..., 3].astype(np.int32)
    scale = np.where(exponent > 0, np.ldexp(1.0, exponent - 136), 0.0).astype(np.float32)
    rgb = rgbe[..., :3].astype(np.float32) * scale[..., None]
    if flip_y:
        rgb = rgb[::-1]
    if flip_x:
        rgb = rgb[:, ::-1]
    return np.ascontiguousarray(rgb)


def read_exr(path: Path | str) -> np.ndarray:
    """A scanline OpenEXR (half / float / uint channels, none / ZIP / ZIPS compression) as `(H, W, 3)` float32.

    Channels R, G, B are used (Y alone gives grey); other names are ignored.

    Raises:
        HdriError: When the file is not an EXR this reader understands.
    """
    name = Path(path).name
    data = Path(path).read_bytes()
    if len(data) < 8 or struct.unpack("<i", data[:4])[0] != EXR_MAGIC:
        raise HdriError(f"{name}: not an OpenEXR file")
    version = struct.unpack("<i", data[4:8])[0]
    if version & 0x200 or version & 0x1000 or version & 0x800:
        raise HdriError(f"{name}: tiled, deep or multi-part EXR files are not supported")
    pos = 8
    channels: list[tuple[str, int]] = []
    compression = COMPRESSION_NONE
    window = None
    while True:
        end = data.index(b"\0", pos)
        attr_name = data[pos:end].decode("ascii", errors="replace")
        pos = end + 1
        if attr_name == "":
            break
        end = data.index(b"\0", pos)
        kind = data[pos:end].decode("ascii", errors="replace")
        pos = end + 1
        size = struct.unpack("<i", data[pos:pos + 4])[0]
        pos += 4
        value = data[pos:pos + size]
        pos += size
        if attr_name == "channels" and kind == "chlist":
            cp = 0
            while cp < len(value) and value[cp] != 0:
                cend = value.index(b"\0", cp)
                ch_name = value[cp:cend].decode("ascii", errors="replace")
                cp = cend + 1
                pixel_type = struct.unpack("<i", value[cp:cp + 4])[0]
                cp += 16
                channels.append((ch_name, pixel_type))
        elif attr_name == "compression":
            compression = value[0]
        elif attr_name == "dataWindow" and kind == "box2i":
            window = struct.unpack("<iiii", value)
    if window is None or not channels:
        raise HdriError(f"{name}: header without channels / data window")
    if compression not in (COMPRESSION_NONE, COMPRESSION_ZIPS, COMPRESSION_ZIP):
        raise HdriError(f"{name}: compression {compression} is not supported (only none, ZIP and ZIPS)")
    x0, y0, x1, y1 = window
    width, height = x1 - x0 + 1, y1 - y0 + 1
    lines_per_chunk = 16 if compression == COMPRESSION_ZIP else 1
    chunk_count = -(-height // lines_per_chunk)
    offsets = struct.unpack(f"<{chunk_count}Q", data[pos:pos + 8 * chunk_count])
    sizes = {PIXEL_UINT: 4, PIXEL_HALF: 2, PIXEL_FLOAT: 4}
    dtypes = {PIXEL_UINT: "<u4", PIXEL_HALF: "<f2", PIXEL_FLOAT: "<f4"}
    row_bytes = sum(width * sizes[t] for _n, t in channels)
    planes = {ch: np.zeros((height, width), dtype=np.float32) for ch, _t in channels}
    for offset in offsets:
        y, size = struct.unpack("<ii", data[offset:offset + 8])
        chunk = data[offset + 8:offset + 8 + size]
        lines = min(lines_per_chunk, y1 - y + 1)
        expected = row_bytes * lines
        if compression != COMPRESSION_NONE and size < expected:
            chunk = _unzip(chunk, expected)
        cursor = 0
        for line in range(lines):
            for ch, pixel_type in channels:
                n = width * sizes[pixel_type]
                planes[ch][y - y0 + line] = np.frombuffer(chunk, dtype=dtypes[pixel_type], count=width, offset=cursor).astype(np.float32)
                cursor += n
    if all(c in planes for c in "RGB"):
        rgb = np.stack([planes["R"], planes["G"], planes["B"]], axis=-1)
    elif "Y" in planes:
        rgb = np.repeat(planes["Y"][..., None], 3, axis=-1)
    else:
        first = next(iter(planes.values()))
        rgb = np.repeat(first[..., None], 3, axis=-1)
    return np.ascontiguousarray(rgb, dtype=np.float32)


def _unzip(chunk: bytes, expected: int) -> bytes:
    """Undo OpenEXR's ZIP: zlib, the delta predictor, the interleave split (`render/exr.py` does the reverse)."""
    raw = np.frombuffer(zlib.decompress(chunk), dtype=np.uint8).astype(np.int16)
    if raw.size != expected:
        raise HdriError("corrupt ZIP chunk")
    # predictor: d[i] = d[i-1] + d[i] - 128
    restored = np.cumsum(np.concatenate([raw[:1], raw[1:] - 128]).astype(np.int64)) & 0xFF
    restored = restored.astype(np.uint8)
    half = (restored.size + 1) // 2
    out = np.empty_like(restored)
    out[0::2] = restored[:half]
    out[1::2] = restored[half:]
    return out.tobytes()


def read_image_linear(path: Path | str) -> np.ndarray:
    """Any image as `(H, W, 3)` float32 linear RGB: `.hdr`, `.exr`, or an LDR image (sRGB decoded) through Pillow.

    Raises:
        HdriError: When the file cannot be read as an image.
    """
    path = Path(path)
    suffix = path.suffix.lower()
    if suffix == ".hdr":
        return read_hdr(path)
    if suffix == ".exr":
        return read_exr(path)
    try:
        from PIL import Image
        with Image.open(path) as image:
            rgb = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0
    except Exception as exc:  # noqa: BLE001 - Pillow raises many kinds
        raise HdriError(f"{path.name}: cannot read the image ({exc})") from exc
    linear = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    return np.ascontiguousarray(linear, dtype=np.float32)


# --- the environment map -----------------------------------------------------------------------------------------------
def direction_to_uv(directions: np.ndarray) -> np.ndarray:
    """Equirectangular `(…, 2)` coordinates in 0..1 of unit world directions (z up)."""
    d = np.asarray(directions, dtype=np.float64)
    u = (np.arctan2(d[..., 1], d[..., 0]) / (2.0 * np.pi)) % 1.0
    v = np.arccos(np.clip(d[..., 2], -1.0, 1.0)) / np.pi
    return np.stack([u, v], axis=-1)


def uv_to_direction(u: np.ndarray, v: np.ndarray) -> np.ndarray:
    """Unit world directions `(…, 3)` of equirectangular coordinates."""
    phi = np.asarray(u) * 2.0 * np.pi
    theta = np.asarray(v) * np.pi
    s = np.sin(theta)
    return np.stack([s * np.cos(phi), s * np.sin(phi), np.cos(theta)], axis=-1)


def sample_equirect(image: np.ndarray, uv: np.ndarray) -> np.ndarray:
    """Bilinear lookup of `(…, 2)` uv in an `(H, W, 3)` map (wrapping in u, clamped in v)."""
    h, w = image.shape[:2]
    x = uv[..., 0] * w - 0.5
    y = np.clip(uv[..., 1] * h - 0.5, 0.0, h - 1.0)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    x1 = (x0 + 1) % w
    x0 = x0 % w
    y1 = np.minimum(y0 + 1, h - 1)
    top = image[y0, x0] * (1 - fx) + image[y0, x1] * fx
    bottom = image[y1, x0] * (1 - fx) + image[y1, x1] * fx
    return top * (1 - fy) + bottom * fy


def resize_equirect(image: np.ndarray, width: int) -> np.ndarray:
    """Box-downsample (or keep) an equirect map to `width` × `width / 2`."""
    h, w = image.shape[:2]
    if w <= width:
        return image.astype(np.float32)
    factor = w / width
    zoom = (1.0 / factor, 1.0 / factor, 1.0)
    # average before shrinking so bright pixels are not lost
    smoothed = ndimage.uniform_filter(image, size=(max(1, int(factor)), max(1, int(factor)), 1), mode=("nearest", "wrap", "nearest"))
    small = ndimage.zoom(smoothed, zoom, order=1, mode="nearest")
    return np.ascontiguousarray(small, dtype=np.float32)


def solid_angle_weights(height: int, width: int) -> np.ndarray:
    """`(H, W)` solid angle of each texel of an equirect map (sums to 4π)."""
    theta = (np.arange(height) + 0.5) / height * np.pi
    w = np.sin(theta) * (np.pi / height) * (2.0 * np.pi / width)
    return np.repeat(w[:, None], width, axis=1)


def sh9_basis(directions: np.ndarray) -> np.ndarray:
    """`(…, 9)` real spherical harmonics (bands 0–2) of unit directions."""
    d = np.asarray(directions, dtype=np.float64)
    x, y, z = d[..., 0], d[..., 1], d[..., 2]
    return np.stack([
        np.full_like(x, 0.282095),
        0.488603 * y, 0.488603 * z, 0.488603 * x,
        1.092548 * x * y, 1.092548 * y * z, 0.315392 * (3.0 * z * z - 1.0), 1.092548 * x * z, 0.546274 * (x * x - y * y),
    ], axis=-1)


def sh9_project(image: np.ndarray) -> np.ndarray:
    """`(9, 3)` SH coefficients of the radiance in an equirect map."""
    h, w = image.shape[:2]
    v, u = np.mgrid[0:h, 0:w]
    dirs = uv_to_direction((u + 0.5) / w, (v + 0.5) / h)
    basis = sh9_basis(dirs)                                    # (H, W, 9)
    weights = solid_angle_weights(h, w)
    return np.einsum("hwk,hw,hwc->kc", basis, weights, image.astype(np.float64))


_IRRADIANCE = np.array([math.pi, 2.094395, 2.094395, 2.094395, 0.785398, 0.785398, 0.785398, 0.785398, 0.785398])


def sh9_irradiance(coefficients: np.ndarray, normals: np.ndarray) -> np.ndarray:
    """Irradiance `(…, 3)` (already divided by π — the diffuse radiance for an albedo of 1) at unit normals."""
    basis = sh9_basis(normals)                                 # (…, 9)
    return np.maximum(np.einsum("...k,k,kc->...c", basis, _IRRADIANCE, coefficients) / math.pi, 0.0)


def prefiltered_levels(image: np.ndarray, levels: int = LEVELS) -> list[np.ndarray]:
    """Increasingly blurred copies, each half the size of the previous (level 0 = the map itself)."""
    out = [image.astype(np.float32)]
    current = image.astype(np.float32)
    for level in range(1, levels):
        h, w = current.shape[:2]
        blurred = ndimage.gaussian_filter(current, sigma=(1.0, 1.0, 0.0), mode=("nearest", "wrap", "nearest"))
        small = blurred[: h - h % 2, : w - w % 2].reshape(h // 2, 2, w // 2, 2, 3).mean(axis=(1, 3)) if h >= 2 and w >= 2 else blurred
        # an extra blur proportional to the level: level n covers a cone of roughly 8·n degrees
        small = ndimage.gaussian_filter(small, sigma=(0.6 * level, 0.6 * level, 0.0), mode=("nearest", "wrap", "nearest"))
        out.append(np.ascontiguousarray(small, dtype=np.float32))
        current = small
    return out


def roughness_to_level(roughness: np.ndarray, levels: int = LEVELS) -> np.ndarray:
    """Which prefiltered level a roughness in 0..1 samples (fractional, for blending)."""
    return np.clip(np.asarray(roughness, dtype=np.float64), 0.0, 1.0) * (levels - 1)


def shininess_to_roughness(shininess: float) -> float:
    """Blinn-Phong exponent → a 0..1 roughness (200 = mirror-like, 1 = matte)."""
    return float(np.clip(1.0 - math.log(max(shininess, 1.0)) / math.log(200.0), 0.0, 1.0))


def rotation_about_z(degrees: float) -> np.ndarray:
    a = math.radians(degrees)
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]])


@dataclass
class EnvironmentMap:
    """An HDRI ready for lighting (see the module docstring).

    Attributes:
        image: `(H, W, 3)` float32 linear RGB at the working size.
        levels: Prefiltered copies (level 0 = `image`).
        sh: `(9, 3)` SH coefficients.
        path: Where it came from.
        average: Mean radiance (the ambient level, for information).
    """
    image: np.ndarray
    levels: list[np.ndarray] = field(default_factory=list)
    sh: np.ndarray = field(default_factory=lambda: np.zeros((9, 3)))
    path: str = ""
    average: tuple[float, float, float] = (0.0, 0.0, 0.0)

    @classmethod
    def from_image(cls, image: np.ndarray, path: str = "", width: int = MAP_WIDTH) -> "EnvironmentMap":
        small = resize_equirect(np.nan_to_num(image, nan=0.0, posinf=1e4, neginf=0.0), width)
        levels = prefiltered_levels(small)
        sh = sh9_project(levels[min(2, len(levels) - 1)])
        weights = solid_angle_weights(*small.shape[:2])
        average = tuple(float(v) for v in (small * weights[..., None]).sum(axis=(0, 1)) / weights.sum())
        return cls(small, levels, sh, path, average)

    def sample(self, directions: np.ndarray, level: float | np.ndarray = 0.0, rotation: float = 0.0) -> np.ndarray:
        """Radiance `(…, 3)` along world directions, from prefiltered `level` (fractional: blended), the map turned by `rotation` degrees."""
        d = np.asarray(directions, dtype=np.float64)
        if rotation:
            d = d @ rotation_about_z(rotation)                    # rows: d · R → the inverse turn of the map
        uv = direction_to_uv(d)
        level = np.clip(np.asarray(level, dtype=np.float64), 0.0, len(self.levels) - 1)
        lo = np.floor(level).astype(int)
        hi = np.minimum(lo + 1, len(self.levels) - 1)
        t = (level - lo)[..., None] if np.ndim(level) else float(level - lo)
        if np.ndim(level) == 0:
            a = sample_equirect(self.levels[int(lo)], uv)
            if int(hi) == int(lo) or float(t) <= 0:
                return a
            return a * (1 - t) + sample_equirect(self.levels[int(hi)], uv) * t
        out = np.zeros(d.shape[:-1] + (3,))
        for index in np.unique(lo):
            mask = lo == index
            a = sample_equirect(self.levels[int(index)], uv[mask])
            b = sample_equirect(self.levels[int(min(index + 1, len(self.levels) - 1))], uv[mask])
            out[mask] = a * (1 - t[mask]) + b * t[mask]
        return out

    def irradiance(self, normals: np.ndarray, rotation: float = 0.0) -> np.ndarray:
        """Diffuse radiance `(…, 3)` for unit world normals."""
        n = np.asarray(normals, dtype=np.float64)
        if rotation:
            n = n @ rotation_about_z(rotation)
        return sh9_irradiance(self.sh, n)

    def key_lights(self, count: int = 3, radius: float = KEY_LIGHT_RADIUS) -> list[tuple[np.ndarray, tuple[float, float, float], float]]:
        """The `count` brightest regions as (unit world direction, colour 0..1, relative intensity): candidates for distant lights."""
        source = self.levels[0]
        h, w = source.shape[:2]
        luminance = source @ np.array([0.2126, 0.7152, 0.0722])
        weights = solid_angle_weights(h, w)
        energy = luminance * weights
        v, u = np.mgrid[0:h, 0:w]
        dirs = uv_to_direction((u + 0.5) / w, (v + 0.5) / h)
        cos_radius = math.cos(math.radians(radius))
        found = []
        remaining = energy.copy()
        for _ in range(max(0, count)):
            if remaining.max() <= 0:
                break
            iy, ix = np.unravel_index(int(np.argmax(remaining)), remaining.shape)
            centre = dirs[iy, ix]
            cap = (dirs @ centre) >= cos_radius
            cap_energy = float((remaining * cap).sum())          # energy not yet claimed by an earlier light
            colour = (source * (weights * cap * (remaining > 0))[..., None]).sum(axis=(0, 1))
            colour = colour / max(colour.max(), 1e-12)
            found.append((centre, tuple(float(c) for c in np.clip(colour, 0.0, 1.0)), cap_energy))
            remaining[cap] = 0.0
        if not found:
            return []
        strongest = max(e for _d, _c, e in found) or 1.0
        return [(d, c, e / strongest) for d, c, e in found]


_cache: dict[tuple[str, float], EnvironmentMap] = {}
_cache_lock = threading.Lock()


def load_environment(path: str | Path) -> EnvironmentMap:
    """The `EnvironmentMap` of an image file, cached by path and modification time.

    Raises:
        HdriError: When the file cannot be read.
        OSError: When it does not exist.
    """
    path = Path(path)
    key = (str(path.resolve()), path.stat().st_mtime)
    with _cache_lock:
        cached = _cache.get(key)
    if cached is not None:
        return cached
    env = EnvironmentMap.from_image(read_image_linear(path), str(path))
    with _cache_lock:
        if len(_cache) >= 4:
            _cache.pop(next(iter(_cache)))
        _cache[key] = env
    return env


def environment_for(environment) -> EnvironmentMap | None:
    """The map of a `scene3d.model.Environment` (None when it has no HDRI or the file cannot be read)."""
    if not environment.hdri:
        return None
    try:
        return load_environment(environment.hdri)
    except (OSError, HdriError, ValueError):
        return None


def write_hdr(path: Path | str, image: np.ndarray) -> None:
    """Write `(H, W, 3)` float RGB as a flat (unencoded) Radiance `.hdr` — for tests and for saving generated skies."""
    image = np.asarray(image, dtype=np.float32)
    h, w = image.shape[:2]
    maximum = image.max(axis=2)
    exponent = np.where(maximum > 1e-32, np.floor(np.log2(np.maximum(maximum, 1e-32))) + 1, 0).astype(np.int32)
    scale = np.where(maximum > 1e-32, 256.0 / np.ldexp(1.0, exponent), 0.0)
    rgbe = np.zeros((h, w, 4), dtype=np.uint8)
    rgbe[..., :3] = np.clip(image * scale[..., None], 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(maximum > 1e-32, exponent + 128, 0).astype(np.uint8)
    with open(path, "wb") as fh:
        fh.write(b"#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n")
        fh.write(f"-Y {h} +X {w}\n".encode("ascii"))
        fh.write(rgbe.tobytes())


__all__ = ["EnvironmentMap", "HdriError", "read_hdr", "read_exr", "read_image_linear", "write_hdr", "load_environment", "environment_for",
           "direction_to_uv", "uv_to_direction", "sample_equirect", "sh9_project", "sh9_irradiance", "sh9_basis", "prefiltered_levels",
           "roughness_to_level", "shininess_to_roughness", "rotation_about_z", "solid_angle_weights", "MAP_WIDTH", "LEVELS"]
