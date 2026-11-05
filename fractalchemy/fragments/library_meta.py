"""What the fragment library knows about its files beyond their names: tags, ratings, favourites, and an index of
what each fragment declares (its parameters, includes, presets, camera kind, `#info` lines) — the search box
matches all of it.

Tags, ratings and favourites live in one JSON file in the cache folder (`library_meta.json`, keyed by absolute path),
never in the fragments — the bundled examples stay pristine and FragM never sees them. The index is rebuilt from a
quick regex scan of each file (by modification time, cached in memory) on the thread pool after a library rescan.
`search_text` turns both into the words the search filter sees: the name, `tag:<tag>`, `rating:<n>` and as many `★`,
`fav` for favourites, `recent` for recently opened files, `param:<Name>` and the parameter names themselves,
`include:<file>`, the preset names, `2d` / `3d` and `fp64` for fragments that use double precision (`double`, `dvec`,
`#version 4xx`, the fp64 extension — they need an OpenGL 4 context; the library badges them); typing `tag:ifs`,
`param:Power fav` or `★★★★` filters the tree.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path

RE_UNIFORM = re.compile(r"^\s*uniform\s+\w+\s+([A-Za-z_]\w*)\s*;\s*(slider|color|checkbox|menu|file)\s*\[", re.IGNORECASE | re.MULTILINE)
RE_INCLUDE = re.compile(r'^\s*#include\s+"([^"]+)"', re.IGNORECASE | re.MULTILINE)
RE_PRESET = re.compile(r"^\s*#preset\s+(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
RE_INFO = re.compile(r"^\s*#info\s+(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
RE_CAMERA = re.compile(r"^\s*#camera\s+(2D|3D)", re.IGNORECASE | re.MULTILINE)
RE_GROUP = re.compile(r"^\s*#group\s+(.+?)\s*$", re.IGNORECASE | re.MULTILINE)
RE_FP64 = re.compile(r"\b(?:double|dvec[234]|dmat[234](?:x[234])?)\b|GL_ARB_gpu_shader_fp64|^\s*#version\s+4[0-9]{2}", re.MULTILINE)
RE_VERSION_GUARD = re.compile(r"^\s*#if\b[^\n]*(?:__VERSION__|fp64)[^\n]*\n.*?^\s*#(?:else|endif)\b", re.MULTILINE | re.DOTALL)
RE_COMMENTS = re.compile(r"/\*.*?\*/|//[^\n]*", re.DOTALL)
MAX_RATING = 5


@dataclass
class FragmentInfo:
    """The quick scan of one fragment."""
    params: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    presets: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    info: list[str] = field(default_factory=list)
    camera: str = ""
    needs_fp64: bool = False

    @property
    def caption_line(self) -> str:
        """`3D · 5 presets · 12 parameters · fp64` for the thumbnail caption."""
        parts = [self.camera or "2D?"]
        if self.presets:
            parts.append(f"{len(self.presets)} preset{'s' if len(self.presets) != 1 else ''}")
        parts.append(f"{len(self.params)} parameter{'s' if len(self.params) != 1 else ''}")
        if self.needs_fp64:
            parts.append("fp64")
        return " · ".join(parts)


def scan_fragment(text: str) -> FragmentInfo:
    """The declarations `search_text` indexes (a regex pass, no preprocessing)."""
    camera = RE_CAMERA.search(text)
    code = RE_VERSION_GUARD.sub("", RE_COMMENTS.sub("", text))        # comments and `#if __VERSION__ >= 400` blocks do not need fp64
    return FragmentInfo([m.group(1) for m in RE_UNIFORM.finditer(text)], [m.group(1) for m in RE_INCLUDE.finditer(text)],
                        [m.group(1) for m in RE_PRESET.finditer(text)], [m.group(1) for m in RE_GROUP.finditer(text)],
                        [m.group(1) for m in RE_INFO.finditer(text)],
                        camera.group(1).upper() if camera else ("3D" if "Raytracer" in text or "DE(vec3" in text else "2D"),
                        RE_FP64.search(code) is not None)


def read_info(path: Path) -> FragmentInfo:
    return scan_fragment(Path(path).read_text(encoding="utf-8", errors="replace"))


class LibraryMeta:
    """Tags, ratings and favourites per file, persisted as JSON (see the module docstring)."""

    def __init__(self, store: Path | None):
        self.store = store
        self._data: dict[str, dict] = {}
        self._infos: dict[tuple[str, int], FragmentInfo] = {}
        self.load()

    # --- persistence ---------------------------------------------------------------------------------------------------
    def load(self) -> None:
        if self.store is None or not self.store.is_file():
            return
        try:
            data = json.loads(self.store.read_text(encoding="utf-8"))
            self._data = {k: v for k, v in data.items() if isinstance(v, dict)} if isinstance(data, dict) else {}
        except (OSError, ValueError):
            self._data = {}

    def save(self) -> None:
        if self.store is None:
            return
        try:
            self.store.parent.mkdir(parents=True, exist_ok=True)
            self.store.write_text(json.dumps(self._data, indent=1, sort_keys=True), encoding="utf-8")
        except OSError:
            pass

    def _entry(self, path: Path) -> dict:
        return self._data.setdefault(str(Path(path).resolve()), {})

    def _get(self, path: Path) -> dict:
        return self._data.get(str(Path(path).resolve()), {})

    # --- tags / rating / favourite ---------------------------------------------------------------------------------------
    def tags(self, path: Path) -> list[str]:
        return [str(t) for t in self._get(path).get("tags", [])]

    def set_tags(self, path: Path, tags: list[str]) -> None:
        clean = sorted({t.strip().lower().replace(" ", "-") for t in tags if t.strip()})
        entry = self._entry(path)
        if clean:
            entry["tags"] = clean
        else:
            entry.pop("tags", None)
        self.save()

    def rating(self, path: Path) -> int:
        return int(self._get(path).get("rating", 0))

    def set_rating(self, path: Path, rating: int) -> None:
        entry = self._entry(path)
        if rating > 0:
            entry["rating"] = max(0, min(MAX_RATING, int(rating)))
        else:
            entry.pop("rating", None)
        self.save()

    def favourite(self, path: Path) -> bool:
        return bool(self._get(path).get("favourite", False))

    def set_favourite(self, path: Path, on: bool) -> None:
        entry = self._entry(path)
        if on:
            entry["favourite"] = True
        else:
            entry.pop("favourite", None)
        self.save()

    def all_tags(self) -> list[str]:
        return sorted({t for entry in self._data.values() for t in entry.get("tags", [])})

    # --- the index -----------------------------------------------------------------------------------------------------------
    def info(self, path: Path) -> FragmentInfo:
        """The scan of `path` (cached by modification time; an unreadable file scans as empty). `needs_fp64` also holds
        when one of the files it includes (beside it, or in the bundled include folder) uses double precision outright."""
        try:
            key = (str(path), Path(path).stat().st_mtime_ns)
        except OSError:
            return FragmentInfo()
        cached = self._infos.get(key)
        if cached is None:
            try:
                cached = read_info(path)
            except OSError:
                cached = FragmentInfo()
            self._infos[key] = cached                     # stored before looking at the includes: files include each other
            if not cached.needs_fp64:
                cached.needs_fp64 = self._includes_need_fp64(Path(path), cached.includes)
        return cached

    def _includes_need_fp64(self, origin: Path, includes: list[str]) -> bool:
        """Whether one of `includes` (beside `origin`, else bundled) uses double precision, transitively."""
        from .examples import INCLUDE_DIR
        for name in includes:
            for folder in (origin.parent, INCLUDE_DIR):
                candidate = folder / name
                if candidate.is_file():
                    if candidate != origin and self.info(candidate).needs_fp64:
                        return True
                    break
        return False

    def search_text(self, path: Path, recent: bool = False) -> str:
        """The words the search filter matches for `path` (see the module docstring)."""
        info = self.info(path)
        words = [Path(path).name, Path(path).stem, info.camera.lower()]
        rating = self.rating(path)
        words += [f"tag:{t}" for t in self.tags(path)] + list(self.tags(path))
        if rating:
            words += [f"rating:{rating}", "★" * rating]
        if self.favourite(path):
            words += ["fav", "favourite"]
        if recent:
            words.append("recent")
        if info.needs_fp64:
            words += ["fp64", "needs:fp64", "double"]
        words += [f"param:{n}" for n in info.params] + info.params
        words += [f"include:{Path(i).stem}" for i in info.includes] + [f"preset:{p}" for p in info.presets] + info.presets + info.groups + info.info
        return " ".join(words)

    def caption(self, path: Path) -> str:
        """`name\\n3D · 5 presets · 12 parameters ★★★` for the thumbnail view."""
        info = self.info(path)
        stars = "★" * self.rating(path)
        tags = ", ".join(self.tags(path))
        second = info.caption_line + (f"  {stars}" if stars else "") + ("  ♥" if self.favourite(path) else "")
        return f"{Path(path).name}\n{second}" + (f"\n{tags}" if tags else "")


__all__ = ["LibraryMeta", "FragmentInfo", "scan_fragment", "read_info", "MAX_RATING"]
