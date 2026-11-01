"""Where a name is defined in fragment sources — functions, uniforms, `#define`s, globals and structs — for *go to
definition* (Ctrl+click) and the hover signatures.

A plain text scan: the fragment's own text first, then the files it includes (the preprocessor's dependency list or
an include path), so clicking `DE` in a raytraced fragment lands on the user's estimator while `trace` leads into
`DE-Raytracer.frag`. The match is the declaring line; its text doubles as the signature shown on hover.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

TYPES = r"(?:void|float|int|bool|uint|double|[biud]?vec[234]|d?mat[234](?:x[234])?|sampler2D|samplerCube)"
RE_FUNCTION = re.compile(rf"^[ \t]*(?:[a-z]+\s+)?({TYPES})\s+(?P<name>[A-Za-z_]\w*)\s*\(([^)]*)\)\s*(?:\{{|;|$)", re.MULTILINE)
RE_UNIFORM = re.compile(rf"^[ \t]*uniform\s+{TYPES}\s+(?P<name>[A-Za-z_]\w*)\s*;", re.MULTILINE)
RE_DEFINE = re.compile(r"^[ \t]*#define\s+(?P<name>[A-Za-z_]\w*)", re.MULTILINE)
RE_GLOBAL = re.compile(rf"^[ \t]*(?:const\s+)?{TYPES}\s+(?P<name>[A-Za-z_]\w*)\s*(?:=|;)", re.MULTILINE)
RE_STRUCT = re.compile(r"^[ \t]*struct\s+(?P<name>[A-Za-z_]\w*)", re.MULTILINE)
KINDS = (("function", RE_FUNCTION), ("uniform", RE_UNIFORM), ("define", RE_DEFINE), ("struct", RE_STRUCT), ("variable", RE_GLOBAL))


@dataclass(frozen=True)
class Definition:
    """One declaring line.

    Attributes:
        name: The identifier.
        kind: `function`, `uniform`, `define`, `struct` or `variable`.
        file: The file holding it (None: the text that was searched directly).
        line: 1-based line.
        text: The declaring line, stripped.
    """
    name: str
    kind: str
    file: Path | None
    line: int
    text: str

    @property
    def signature(self) -> str:
        """The declaration without its body / trailing brace (what the hover shows)."""
        if self.kind == "function":
            return self.text.split("{", 1)[0].rstrip()
        return self.text.rstrip("{ ").rstrip()


def find_definition(text: str, name: str, file: Path | None = None) -> Definition | None:
    """The first declaration of `name` in `text` (functions before uniforms, defines, structs, globals; a function's
    definition before its prototype)."""
    prototype = None
    for kind, pattern in KINDS:
        for match in pattern.finditer(text):
            if match.group("name") != name:
                continue
            found = Definition(name, kind, file, text.count("\n", 0, match.start()) + 1, _line_of(text, match.start()))
            if kind == "function" and found.text.rstrip().endswith(";"):
                prototype = prototype or found
                continue
            return found
    return prototype


def _line_of(text: str, start: int) -> str:
    end = text.find("\n", start)
    return text[start:end if end >= 0 else len(text)].strip()


def find_in_files(name: str, files: list[Path]) -> Definition | None:
    """`find_definition` over `files` in order (unreadable files are skipped)."""
    for path in files:
        try:
            text = Path(path).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        found = find_definition(text, name, Path(path))
        if found is not None:
            return found
    return None


def all_definitions(text: str, file: Path | None = None) -> list[Definition]:
    """Every definition in `text`, in order of appearance (the walkthrough / outline uses it)."""
    found: dict[tuple[str, int], Definition] = {}
    for kind, pattern in KINDS:
        for match in pattern.finditer(text):
            line = text.count("\n", 0, match.start()) + 1
            key = (match.group("name"), line)
            if key not in found:
                found[key] = Definition(match.group("name"), kind, file, line, _line_of(text, match.start()))
    return sorted(found.values(), key=lambda d: d.line)


__all__ = ["Definition", "find_definition", "find_in_files", "all_definitions"]
