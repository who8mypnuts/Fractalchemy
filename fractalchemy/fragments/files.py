"""Where a fragment's includes and textures are found — FragM's `FileManager`.

A name is resolved in FragM's order: an absolute path as-is; then beside the file doing the including; then each
include path in order. The bundled `Include/` folder is always the last include path, so every example finds
`DE-Raytracer.frag` without configuration and a user folder can shadow a bundled include. A failed lookup raises
`IncludeNotFound` carrying every path that was tried, which the log shows as FragM does ("Tried path: …").
"""

from __future__ import annotations

from pathlib import Path

from .examples import INCLUDE_DIR

IMAGE_SUFFIXES = (".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tif", ".tiff", ".webp", ".hdr", ".exr", ".pbm", ".pgm", ".ppm")


class IncludeNotFound(FileNotFoundError):
    """A `#include` / `file[...]` name could not be resolved; `tried` lists the candidate paths."""

    def __init__(self, name: str, tried: list[Path]):
        super().__init__(f"Could not resolve path for file: {name}")
        self.name = name
        self.tried = tried


class FileManager:
    """Include-path resolution for one fragment (see the module docstring).

    Attributes:
        original: The fragment file being built (None for an unsaved tab: only the include paths are searched).
    """

    def __init__(self, include_paths: list[Path] | None = None, original: Path | None = None):
        self.original = original
        self._include_paths: list[Path] = []
        self._file_cache: dict[str, list[str]] = {}
        self.set_include_paths(include_paths or [])

    @property
    def include_paths(self) -> list[Path]:
        """The search folders in order, the bundled include folder last."""
        return list(self._include_paths)

    def set_include_paths(self, paths: list[Path]) -> None:
        """Replace the user include paths (the bundled folder is appended when missing)."""
        ordered = [Path(p) for p in paths if str(p).strip()]
        if INCLUDE_DIR not in ordered:
            ordered.append(INCLUDE_DIR)
        self._include_paths = ordered
        self._file_cache.clear()

    def candidates(self, name: str, origin: Path | None = None) -> list[Path]:
        """The paths `name` may refer to, in search order (an absolute name is its own only candidate)."""
        path = Path(name)
        if path.is_absolute():
            return [path]
        bases: list[Path] = []
        for anchor in (origin, self.original):
            if anchor is not None and anchor.parent not in bases:
                bases.append(anchor.parent)
        bases += [p for p in self._include_paths if p not in bases]
        return [base / name for base in bases]

    def resolve_name(self, name: str, origin: Path | None = None) -> Path:
        """The existing file `name` refers to, or `IncludeNotFound`.

        Args:
            name: As written in the fragment (`"MathUtils.frag"`, `"textures/wood.png"`, or absolute).
            origin: The file containing the reference (its folder is searched first).
        """
        tried = self.candidates(name, origin)
        for path in tried:
            if path.is_file():
                return path
        raise IncludeNotFound(name, tried)

    def file_exists(self, name: str, origin: Path | None = None) -> bool:
        """Whether `resolve_name` would succeed."""
        return any(p.is_file() for p in self.candidates(name, origin))

    def get_files(self, suffixes: tuple[str, ...]) -> list[str]:
        """File names with one of `suffixes` beside the fragment and on the include paths (cached, de-duplicated)."""
        key = ";".join(suffixes)
        if key not in self._file_cache:
            folders = ([self.original.parent] if self.original is not None else []) + self._include_paths
            names: list[str] = []
            for folder in folders:
                if folder.is_dir():
                    names += sorted(p.name for p in folder.iterdir() if p.is_file() and p.suffix.lower() in suffixes)
            self._file_cache[key] = list(dict.fromkeys(names))
        return list(self._file_cache[key])

    def image_files(self) -> list[str]:
        """Texture candidates for the sampler widgets."""
        return self.get_files(IMAGE_SUFFIXES)

    def fragment_files(self) -> list[str]:
        """`.frag` files the *Insert include* menu offers."""
        return self.get_files((".frag",))


__all__ = ["FileManager", "IncludeNotFound", "IMAGE_SUFFIXES"]
