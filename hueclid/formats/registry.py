"""Single place that knows which formats exist and how to pick one for a path."""

from __future__ import annotations

from pathlib import Path

from .. import config
from ..imaging import decoder_hint
from ..model import Gradient, simplify
from .base import FormatError, GradientFormat
from .chaos import ChaosFormat
from .flame import FlameFormat
from .image import ImageFormat
from .map import MapFormat
from .ufr import UfrFormat
from .ugr import UgrFormat

FORMATS: tuple[GradientFormat, ...] = (FlameFormat(), UgrFormat(), UfrFormat(), MapFormat(), ChaosFormat(), ImageFormat())
DEFAULT_SAVE_FORMAT: GradientFormat = FORMATS[1]  # UGR


class UnsupportedFormatError(FormatError):
    pass


def format_for(path: Path | str) -> GradientFormat:
    path = Path(path)
    for fmt in FORMATS:
        if fmt.matches(path):
            return fmt
    suffix = path.suffix or path.name
    hint = decoder_hint(suffix)
    raise UnsupportedFormatError(f"No reader for '{suffix}'" + (f" — needs {hint}" if hint else ""))


def save_format_for(path: Path | str) -> GradientFormat:
    fmt = format_for(path)
    if not fmt.can_save:
        raise UnsupportedFormatError(f"{fmt.name} files cannot be written")
    return fmt


def load_gradients(path: Path | str, simplify_tolerance: int | None = None) -> list[Gradient]:
    """Every gradient in the file, with redundant stops dropped (see config)."""
    tolerance = config.IMPORT_SIMPLIFY_TOLERANCE if simplify_tolerance is None else simplify_tolerance
    return [_simplified(g, tolerance) for g in format_for(path).load(Path(path))]


def load_gradient(path: Path | str, index: int = 0, simplify_tolerance: int | None = None) -> Gradient:
    """Convenience: one gradient (by default the first) from the file."""
    gradients = load_gradients(path, simplify_tolerance)
    if not 0 <= index < len(gradients):
        raise FormatError(f"{Path(path).name} has no gradient #{index + 1}")
    return gradients[index]


def _simplified(gradient: Gradient, tolerance: int) -> Gradient:
    return Gradient(gradient.name, simplify(gradient.stops, tolerance))


def save_gradient(gradient: Gradient, path: Path | str, index: int = 0) -> None:
    save_format_for(path).save(gradient, Path(path), index)


def entry_names(path: Path | str) -> list[str]:
    """Names of the gradients in a file, cheaply (no colour parsing)."""
    fmt = format_for(path)
    return fmt.names(Path(path)) if fmt.multi_entry else [Path(path).stem]


def open_dialog_filter() -> str:
    all_patterns = " ".join(f"*{ext}" for fmt in FORMATS for ext in fmt.extensions)
    return ";;".join([f"All supported ({all_patterns})", *(f.dialog_filter() for f in FORMATS)])


def save_dialog_filter() -> str:
    """Formats that can hold a brand-new file."""
    return ";;".join(f.dialog_filter() for f in FORMATS if f.can_create)


def append_dialog_filter() -> str:
    """Formats an extra gradient can be added to."""
    return ";;".join(f.dialog_filter() for f in FORMATS if f.can_append)
