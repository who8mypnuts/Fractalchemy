"""Fractal file formats: Apophysis `.flame`, Fractalchemy `.fa`, Chaotica `.chaos`.

    load_flames(path)        -> list[Flame]
    flame_names(path)        -> list[str]        (cheap; used by the library scanner)
    fractal_format_for(path) -> FractalFormat    (entry operations for the library)
"""

from .registry import (
    DEFAULT_SAVE_FORMAT, FORMATS, PARSE_ERRORS, ChaosFileFormat, FaFileFormat, FlameFileFormat, FractalFormat,
    UnsupportedFractalFormat, flame_names, fractal_format_for, is_fractal_file, load_flame, load_flames,
    open_dialog_filter, save_dialog_filter,
)

__all__ = [
    "FORMATS", "DEFAULT_SAVE_FORMAT", "PARSE_ERRORS", "FractalFormat", "FlameFileFormat", "FaFileFormat",
    "ChaosFileFormat", "UnsupportedFractalFormat", "fractal_format_for", "is_fractal_file", "load_flames",
    "load_flame", "flame_names", "open_dialog_filter", "save_dialog_filter",
]
