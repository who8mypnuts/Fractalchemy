"""Texture files for `uniform sampler2D tex; file[…]` — decoded to numpy, ready for the GL side.

LDR images through Pillow as RGBA8 (FragM uploads Qt images unconverted, so no colour-space change), `.hdr` and
`.exr` as float RGBA (through the host's readers; `file[sky.exr, R;G;B;A]` picks which of the file's channels feed
r, g, b, a — `Z;Z;Z;A` puts a depth pass in every colour channel), cube maps from a strip of six faces in a row (`+x −x +y −y +z −z`,
FragM 2.5's layout), integer textures for `isampler2D` / `usampler2D`. `#TexParameter name GL_… GL_…` lines are kept
as names and translated to moderngl filters / wrapping on upload. A `TextureSpec` is what a request carries; the
`TextureImage` is what the GL cache uploads.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..solid.hdri import HdriError, exr_channel_names, read_exr_planes, read_hdr

GL_NEAREST, GL_LINEAR = 0x2600, 0x2601
GL_NEAREST_MIPMAP_NEAREST, GL_LINEAR_MIPMAP_NEAREST, GL_NEAREST_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_LINEAR = 0x2700, 0x2701, 0x2702, 0x2703
FILTER_NAMES = {"GL_NEAREST": GL_NEAREST, "GL_LINEAR": GL_LINEAR, "GL_NEAREST_MIPMAP_NEAREST": GL_NEAREST_MIPMAP_NEAREST,
                "GL_LINEAR_MIPMAP_NEAREST": GL_LINEAR_MIPMAP_NEAREST, "GL_NEAREST_MIPMAP_LINEAR": GL_NEAREST_MIPMAP_LINEAR,
                "GL_LINEAR_MIPMAP_LINEAR": GL_LINEAR_MIPMAP_LINEAR}
MIPMAP_FILTERS = {GL_NEAREST_MIPMAP_NEAREST, GL_LINEAR_MIPMAP_NEAREST, GL_NEAREST_MIPMAP_LINEAR, GL_LINEAR_MIPMAP_LINEAR}


class TextureError(ValueError):
    """A texture file could not be read."""


@dataclass(frozen=True)
class TextureSpec:
    """What a sampler uniform asks for.

    Attributes:
        name: The uniform.
        path: The resolved file (None when it could not be found).
        channels: EXR channel selection text (`"R;G;B;A"`), empty otherwise.
        cube: The sampler is a `samplerCube`.
        integer: `isampler2D` / `usampler2D` (`"i"` / `"u"`), `""` for floats.
        params: `#TexParameter` names → values for this uniform.
    """
    name: str
    path: Path | None
    channels: str = ""
    cube: bool = False
    integer: str = ""
    params: dict[str, str] = field(default_factory=dict)

    def cache_key(self) -> tuple | None:
        if self.path is None:
            return None
        try:
            mtime = self.path.stat().st_mtime_ns
        except OSError:
            return None
        return (str(self.path), mtime, self.channels, self.cube, self.integer)


@dataclass
class TextureImage:
    """Decoded pixels.

    Attributes:
        data: `(H, W, 4)` — uint8 for LDR images, float32 for HDR / EXR, int32 / uint32 for integer textures.
        faces: For cube maps, six `(S, S, 4)` arrays in `+x −x +y −y +z −z` order (then `data` is the strip).
    """
    data: np.ndarray
    faces: list[np.ndarray] | None = None

    @property
    def dtype(self) -> str:
        """moderngl's dtype string."""
        return {"uint8": "f1", "float32": "f4", "int32": "i4", "uint32": "u4"}[str(self.data.dtype)]


def load_texture(spec: TextureSpec) -> TextureImage:
    """Decode the file a spec names (see the module docstring)."""
    if spec.path is None:
        raise TextureError(f"{spec.name}: no file")
    path = spec.path
    suffix = path.suffix.lower()
    try:
        if suffix == ".hdr":
            rgb = read_hdr(path)
            data = np.dstack([rgb, np.ones(rgb.shape[:2], dtype=np.float32)])
        elif suffix == ".exr":
            data = exr_rgba(read_exr_planes(path), spec.channels)
        else:
            from PIL import Image
            with Image.open(path) as image:
                data = np.asarray(image.convert("RGBA"), dtype=np.uint8)
    except (OSError, HdriError, ValueError) as exc:
        raise TextureError(f"{spec.name}: cannot read {path.name} ({exc})") from exc
    data = np.ascontiguousarray(data[::-1])            # GL rows start at the bottom
    if spec.integer:
        data = data.astype(np.uint32 if spec.integer == "u" else np.int32)
    image = TextureImage(data)
    if spec.cube:
        image.faces = split_cube_strip(data)
    return image


DEFAULT_EXR_CHANNELS = ("R", "G", "B", "A")


def exr_rgba(planes: dict[str, np.ndarray], channels: str = "") -> np.ndarray:
    """`(H, W, 4)` float32 from an EXR's planes: `channels` names the file channels for r, g, b, a (`"R;G;B;A"`,
    `"Z;Z;Z;A"` …, FragM's syntax); a missing or unknown name fills with 0 (1 for alpha), as FragM does; without a
    selection R G B A are taken (Y alone gives grey)."""
    names = [n.strip() for n in channels.split(";")] if channels.strip() else list(DEFAULT_EXR_CHANNELS)
    names = (names + [""] * 4)[:4]
    if not channels.strip() and "R" not in planes and "Y" in planes:
        names = ["Y", "Y", "Y", "A"]
    first = next(iter(planes.values()))
    out = np.empty((*first.shape, 4), dtype=np.float32)
    for index, name in enumerate(names):
        plane = planes.get(name)
        out[..., index] = plane if plane is not None else (1.0 if index == 3 else 0.0)
    return out


def exr_channels_of(path: Path | None) -> list[str]:
    """The channel names of an EXR file (empty for other files or unreadable ones) — the sampler widget's channel boxes."""
    if path is None or Path(path).suffix.lower() != ".exr":
        return []
    try:
        return exr_channel_names(path)
    except (OSError, HdriError):
        return []


def texture_specs(source, state, files) -> dict[str, TextureSpec]:
    """The `TextureSpec` of every sampler parameter: its current file (resolved like an include) and `#TexParameter`s.

    Args:
        source: The preprocessed fragment (sampler types, texture parameters).
        state: The parameter state (the sampler widgets' current values).
        files: A `FileManager` for the fragment (resolution beside the fragment, then the include paths).
    """
    from .parameters import SamplerParameter
    specs: dict[str, TextureSpec] = {}
    for name, param in state.params.items():
        if not isinstance(param, SamplerParameter):
            continue
        file_name, channels = SamplerParameter.split_value(str(state.get(name, "")))
        path = None
        if file_name:
            try:
                path = files.resolve_name(file_name)
            except FileNotFoundError:
                path = None
        specs[name] = TextureSpec(name, path, channels or param.channels, param.glsl_type == "samplerCube",
                                  param.glsl_type[0] if param.glsl_type[0] in "iu" and param.glsl_type != "sampler2D" else "",
                                  dict(source.texture_params.get(name, {})))
    return specs


def split_cube_strip(data: np.ndarray) -> list[np.ndarray]:
    """Six square faces from a `6S × S` strip (`+x −x +y −y +z −z`); a square image is used for every face."""
    height, width = data.shape[:2]
    if width == 6 * height:
        return [np.ascontiguousarray(data[:, i * height:(i + 1) * height]) for i in range(6)]
    if height == 6 * width:
        return [np.ascontiguousarray(data[i * width:(i + 1) * width, :]) for i in range(6)]
    side = min(width, height)
    square = np.ascontiguousarray(data[:side, :side])
    return [square] * 6


def filter_pair(params: dict[str, str]) -> tuple[int, int, bool]:
    """`(min filter, mag filter, mipmaps wanted)` from `#TexParameter` names; FragM's defaults are linear."""
    min_filter = FILTER_NAMES.get(params.get("GL_TEXTURE_MIN_FILTER", ""), GL_LINEAR)
    mag_filter = FILTER_NAMES.get(params.get("GL_TEXTURE_MAG_FILTER", ""), GL_LINEAR)
    if mag_filter in MIPMAP_FILTERS:
        mag_filter = GL_LINEAR
    return min_filter, mag_filter, min_filter in MIPMAP_FILTERS


def wrap_pair(params: dict[str, str]) -> tuple[bool, bool]:
    """`(repeat s, repeat t)`: GL_REPEAT (the default) repeats, GL_CLAMP* clamps."""
    def repeats(name: str) -> bool:
        value = params.get(name, "GL_REPEAT")
        return "REPEAT" in value
    return repeats("GL_TEXTURE_WRAP_S"), repeats("GL_TEXTURE_WRAP_T")


def anisotropy(params: dict[str, str]) -> float:
    try:
        return max(1.0, float(params.get("GL_TEXTURE_MAX_ANISOTROPY", "1")))
    except ValueError:
        return 1.0


__all__ = ["TextureSpec", "TextureImage", "TextureError", "load_texture", "exr_rgba", "exr_channels_of", "texture_specs", "split_cube_strip", "filter_pair", "wrap_pair",
           "anisotropy"]
