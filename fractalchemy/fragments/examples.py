"""The bundled fragment library: FragM's include files and example fragments shipped as package data.

`library/Include` holds the include files every fragment builds on (`DE-Raytracer.frag`, `Progressive2D.frag`, …)
and is always the last include path; `library/Examples/<category>/…` are the example fragments, listed by category
for the *Library ▸ Examples* menu and the library pane's read-only root. `ATTRIBUTION.md` beside them says where they
come from.
"""

from __future__ import annotations

from pathlib import Path

LIBRARY_DIR = Path(__file__).resolve().parent / "library"
INCLUDE_DIR = LIBRARY_DIR / "Include"
EXAMPLES_DIR = LIBRARY_DIR / "Examples"
FRAGMENT_SUFFIXES = (".frag", ".fafrag")
DONOTRUN = "#donotrun"


def include_dir() -> Path:
    """The bundled include folder (the last entry of every include path)."""
    return INCLUDE_DIR


def examples_dir() -> Path:
    """The bundled examples root."""
    return EXAMPLES_DIR


def is_fragment_file(path: Path) -> bool:
    """True for the file suffixes the Fragments window opens."""
    return path.suffix.lower() in FRAGMENT_SUFFIXES


def is_include(path: Path) -> bool:
    """True when the fragment declares itself not runnable (`#donotrun` on its first non-blank line region).

    FragM logs "Not a runnable fragment" for these; the library lists them as includes.
    """
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            head = handle.read(2048)
    except OSError:
        return False
    return any(line.strip().lower().startswith(DONOTRUN) for line in head.splitlines()[:40])


def example_tree(root: Path | None = None) -> list[tuple[Path, list[Path]]]:
    """(folder, fragments) for every folder under `root` holding fragments, folders sorted, depth first.

    Args:
        root: The examples root (the bundled one by default).
    """
    root = root or EXAMPLES_DIR
    tree: list[tuple[Path, list[Path]]] = []
    if not root.is_dir():
        return tree
    for folder in sorted([root] + [p for p in root.rglob("*") if p.is_dir()], key=lambda p: str(p).lower()):
        fragments = sorted((p for p in folder.iterdir() if p.is_file() and is_fragment_file(p)), key=lambda p: p.name.lower())
        if fragments:
            tree.append((folder, fragments))
    return tree


def all_examples(root: Path | None = None) -> list[Path]:
    """Every runnable example fragment (includes excluded), sorted."""
    return [p for _folder, fragments in example_tree(root) for p in fragments if not is_include(p)]


__all__ = ["LIBRARY_DIR", "INCLUDE_DIR", "EXAMPLES_DIR", "FRAGMENT_SUFFIXES", "include_dir", "examples_dir", "is_fragment_file",
           "is_include", "example_tree", "all_examples"]
