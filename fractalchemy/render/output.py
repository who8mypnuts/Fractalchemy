"""Writing finished renders: the output formats, their limits, and 16-bit writers Pillow lacks.

The renderer hands over a (H, W, 4) uint16 RGBA array. Each `OutputFormat` says whether it can
carry alpha, 16-bit channels, lossy quality and how large a side it allows, so the Render window
can grey out what does not apply and refuse sizes a format cannot hold. Pillow writes the 8-bit
formats (and the optional AVIF / HEIF / JPEG XL when their plugins are present); 16-bit PNG and
TIFF are written here directly — a few dozen lines each — because Pillow has no 16-bit RGB(A)
encoder. OpenEXR (`exr.py`) is written as linear-light half / float channels with the render's
facts in header attributes for other DCCs. SVG wraps the PNG as an embedded image, which is what
"an SVG of a flame" can mean.

Parameters travel with the picture when asked: as a PNG text chunk, JPEG comment, TIFF
ImageDescription, EXR attribute or EXIF comment, and optionally as a `.flame` file beside the image.
"""

from __future__ import annotations

import base64
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
from PIL import Image, features

from .. import config
from ..fractal.formats.flame_xml import flames_to_xml
from ..fractal.scene import Flame
from .exr import read_exr_attributes, srgb_to_linear, write_exr
from .png_tiff import PARAMETERS_KEY, png_bytes, to_8bit, write_png, write_tiff16


@dataclass(frozen=True)
class OutputFormat:
    """One writable image format.

    Attributes:
        key: Identifier stored in settings.
        label: Name shown in the UI.
        extensions: File suffixes (the first is the default).
        alpha: Can store transparency.
        depth16: Can store 16 bits per channel.
        float_channels: Stores floating-point channels (16-bit half or 32-bit float) instead of integers.
        lossy: Has a quality setting.
        lossless_option: Has a lossless mode (for formats that are lossy by default).
        max_side: Largest width / height the format allows.
        available: Whether the encoder is present in this installation.
        hint: How to make an unavailable format available.
    """
    key: str
    label: str
    extensions: tuple[str, ...]
    alpha: bool = False
    depth16: bool = False
    float_channels: bool = False
    lossy: bool = False
    lossless_option: bool = False
    max_side: int = 1 << 31 - 1
    available: bool = True
    hint: str = ""

    @property
    def extension(self) -> str:
        """Default suffix, with the dot."""
        return self.extensions[0]


def _plugin(module: str) -> bool:
    try:
        __import__(module)
        return True
    except ImportError:
        return False


FORMATS: tuple[OutputFormat, ...] = (
    OutputFormat("png", "PNG", (".png",), alpha=True, depth16=True),
    OutputFormat("jpeg", "JPEG", (".jpg", ".jpeg"), lossy=True, max_side=65500),
    OutputFormat("tiff", "TIFF", (".tif", ".tiff"), alpha=True, depth16=True),
    OutputFormat("webp", "WebP", (".webp",), alpha=True, lossy=True, lossless_option=True, max_side=16383),
    OutputFormat("bmp", "Windows Bitmap", (".bmp",), max_side=65535),
    OutputFormat("avif", "AVIF", (".avif",), alpha=True, lossy=True, lossless_option=True, max_side=65536,
                 available=features.check("avif"), hint="a Pillow build with AVIF support (pip install -U pillow)"),
    OutputFormat("heif", "HEIF / HEIC", (".heif", ".heic"), alpha=True, lossy=True, max_side=16384,
                 available=_plugin("pillow_heif"), hint="pip install pillow-heif"),
    OutputFormat("jxl", "JPEG XL", (".jxl",), alpha=True, lossy=True, lossless_option=True, max_side=1 << 30,
                 available=_plugin("pillow_jxl"), hint="pip install pillow-jxl-plugin"),
    OutputFormat("exr", "OpenEXR (linear float)", (".exr",), alpha=True, depth16=True, float_channels=True),
    OutputFormat("svg", "SVG (embedded PNG)", (".svg",), alpha=True),
)
FORMAT_BY_KEY = {f.key: f for f in FORMATS}
_PIL_NAMES = {"jpeg": "JPEG", "tiff": "TIFF", "webp": "WEBP", "bmp": "BMP", "avif": "AVIF", "heif": "HEIF", "jxl": "JXL"}
DEPTH_LABELS = {8: "8 bits per channel", 16: "16 bits per channel"}
FLOAT_DEPTH_LABELS = {16: "16-bit half float", 32: "32-bit float"}


def output_format(key: str) -> OutputFormat:
    """The format for a settings key (unknown keys mean PNG)."""
    return FORMAT_BY_KEY.get(key, FORMATS[0])


def format_for_path(path: str | Path) -> OutputFormat | None:
    """The format matching a file's suffix, or None."""
    suffix = Path(path).suffix.lower()
    return next((f for f in FORMATS if suffix in f.extensions), None)


def with_extension(path: str, fmt: OutputFormat) -> str:
    """`path` with the format's default suffix (replacing any known image suffix)."""
    p = Path(path)
    if not path:
        return path
    if format_for_path(p) is fmt:
        return path
    return str(p.with_suffix(fmt.extension))


def size_problem(fmt: OutputFormat, width: int, height: int) -> str | None:
    """Why `fmt` cannot hold a `width × height` image, or None if it can."""
    if max(width, height) > fmt.max_side:
        return f"{fmt.label} allows at most {fmt.max_side:,} pixels per side"
    return None


@dataclass(frozen=True)
class SaveOptions:
    """How to encode.

    Attributes:
        depth: Bits per channel: 8 or 16 for integer formats; 16 (half) or 32 (float) for OpenEXR.
        transparent: Write alpha where the format allows it.
        quality: 1..100 for lossy formats.
        lossless: Prefer lossless encoding where offered.
        parameters: Flame XML to embed ("" = none).
        attributes: Extra metadata (name → text) for formats with free-form headers (OpenEXR).
    """
    depth: int = 8
    transparent: bool = False
    quality: int = 95
    lossless: bool = False
    parameters: str = ""
    attributes: dict[str, str] = field(default_factory=dict)


def parameters_text(flame: Flame) -> str:
    """The flame as Apophysis XML, for embedding and for the `.flame` sidecar."""
    return flames_to_xml([flame], config.APP_NAME)


def save_image(image: np.ndarray, path: str | Path, fmt: OutputFormat, options: SaveOptions) -> None:
    """Write a (H, W, 4) uint16 RGBA array as `fmt` to `path`.

    Raises:
        ValueError: If the format cannot hold the image (size) or is not installed.
        OSError: If the file cannot be written.
    """
    path = Path(path)
    if not fmt.available:
        raise ValueError(f"{fmt.label} output is not available: {fmt.hint}")
    problem = size_problem(fmt, image.shape[1], image.shape[0])
    if problem:
        raise ValueError(problem)
    alpha = options.transparent and fmt.alpha
    depth16 = options.depth >= 16 and fmt.depth16
    if fmt.key == "exr":
        _write_exr_image(path, image, alpha, options)
    elif fmt.key == "png":
        write_png(path, image, alpha, depth16, options.parameters)
    elif fmt.key == "tiff" and depth16:
        write_tiff16(path, image, alpha, options.parameters)
    elif fmt.key == "svg":
        _write_svg(path, image, alpha, options.parameters)
    else:
        _write_pillow(path, image, fmt, alpha, options)


def write_sidecar(flame: Flame, image_path: str | Path) -> Path:
    """Write `<image>.flame` next to the image; returns its path."""
    sidecar = Path(image_path).with_suffix(".flame")
    sidecar.write_text(parameters_text(flame), encoding="utf-8")
    return sidecar


# --- Pillow formats -----------------------------------------------------------------------------
def _to_pil(image: np.ndarray, alpha: bool) -> Image.Image:
    data8 = to_8bit(image)
    return Image.fromarray(data8 if alpha else np.ascontiguousarray(data8[..., :3]), "RGBA" if alpha else "RGB")


def _write_pillow(path: Path, image: np.ndarray, fmt: OutputFormat, alpha: bool, options: SaveOptions) -> None:
    pil = _to_pil(image, alpha)
    kwargs: dict = {}
    if fmt.lossy:
        kwargs["quality"] = int(min(100, max(1, options.quality)))
    if fmt.key == "jpeg":
        kwargs.update(subsampling=0 if options.quality >= 90 else 2, optimize=True)
        if options.parameters:
            kwargs["comment"] = options.parameters.encode("utf-8")
    elif fmt.key == "webp":
        kwargs["lossless"] = bool(options.lossless)
        kwargs["method"] = 6
    elif fmt.key == "tiff":
        kwargs["compression"] = "tiff_deflate"
        if options.parameters:
            kwargs["description"] = options.parameters
    elif fmt.key in ("avif", "jxl") and options.lossless:
        kwargs["quality"] = 100
        if fmt.key == "jxl":
            kwargs["lossless"] = True
    if fmt.key in ("webp", "avif", "heif", "jxl") and options.parameters:
        try:
            exif = Image.Exif()
            exif[0x9286] = options.parameters   # UserComment
            kwargs["exif"] = exif.tobytes()
        except Exception:  # noqa: BLE001 - metadata is best effort
            pass
    pil.save(path, _PIL_NAMES[fmt.key], **kwargs)


# --- OpenEXR ------------------------------------------------------------------------------------------
def _write_exr_image(path: Path, image: np.ndarray, alpha: bool, options: SaveOptions) -> None:
    """Linear-light float channels with associated (premultiplied) alpha, plus metadata attributes."""
    rgb = srgb_to_linear(image[..., :3].astype(np.float32) / 65535.0)
    channels = {"R": rgb[..., 0], "G": rgb[..., 1], "B": rgb[..., 2]}
    if alpha:
        a = image[..., 3].astype(np.float32) / 65535.0
        channels = {name: plane * a for name, plane in channels.items()}
        channels["A"] = a
    attributes = {
        "writer": f"{config.APP_NAME} {config.APP_VERSION}",
        "fractalchemy:colorspace": "linear Rec.709 / sRGB primaries; display values linearised with the inverse sRGB curve",
        "fractalchemy:alpha": "associated (premultiplied)" if alpha else "none (opaque)",
    }
    attributes.update(options.attributes)
    if options.parameters:
        attributes[PARAMETERS_KEY] = options.parameters
    write_exr(path, channels, attributes, half=options.depth <= 16)


# --- SVG ------------------------------------------------------------------------------------------
def _write_svg(path: Path, image: np.ndarray, alpha: bool, parameters: str) -> None:
    height, width = image.shape[:2]
    png = base64.b64encode(png_bytes(image, alpha, False, "")).decode("ascii")
    comment = f"<!--\n{_xml_comment_safe(parameters)}\n-->\n" if parameters else ""
    svg = (f'<?xml version="1.0" encoding="UTF-8"?>\n{comment}'
           f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
           f'width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
           f'  <image width="{width}" height="{height}" xlink:href="data:image/png;base64,{png}"/>\n</svg>\n')
    path.write_text(svg, encoding="utf-8")


def _xml_comment_safe(text: str) -> str:
    return text.replace("--", "- -")


def read_embedded_parameters(path: str | Path) -> str | None:
    """The flame XML stored in an image by `save_image`, if any (PNG / JPEG / TIFF / SVG)."""
    p = Path(path)
    if p.suffix.lower() == ".exr":
        return read_exr_attributes(p).get(PARAMETERS_KEY)
    if p.suffix.lower() == ".svg":
        text = p.read_text(encoding="utf-8", errors="replace")
        start, end = text.find("<!--\n"), text.find("\n-->")
        return text[start + 5:end] if start >= 0 and end > start else None
    with Image.open(p) as im:
        info = im.info
        if PARAMETERS_KEY in info:
            return info[PARAMETERS_KEY]
        if "comment" in info:
            comment = info["comment"]
            return comment.decode("utf-8", "replace") if isinstance(comment, bytes) else comment
        if im.format == "TIFF" and 270 in getattr(im, "tag_v2", {}):
            return im.tag_v2[270]
    return None


__all__ = ["OutputFormat", "FORMATS", "FORMAT_BY_KEY", "DEPTH_LABELS", "FLOAT_DEPTH_LABELS", "output_format", "format_for_path",
           "with_extension", "size_problem",
           "SaveOptions", "save_image", "write_sidecar", "parameters_text", "read_embedded_parameters"]
