"""Minimal-diff editing of text files that hold several gradient entries.

Both flame and UGR files are "a sequence of entries in a text file". This
helper owns the parts they share: line-ending detection, span replacement,
removal and insertion, so each format only has to say where its entries are.
"""

from __future__ import annotations

import os
import tempfile
from dataclasses import dataclass
from pathlib import Path

Span = tuple[int, int]  # [start, end) offsets into the text


@dataclass
class TextFile:
    path: Path
    text: str
    newline: str

    @classmethod
    def read(cls, path: Path) -> "TextFile":
        raw = path.read_bytes()
        return cls(path, raw.decode("utf-8", errors="replace"), "\r\n" if b"\r\n" in raw else "\n")

    @classmethod
    def empty(cls, path: Path, newline: str = "\r\n") -> "TextFile":
        return cls(path, "", newline)

    def write(self) -> None:
        atomic_write_bytes(self.path, self.text.encode("utf-8"))

    def nl(self, text: str) -> str:
        """Normalise '\\n' in generated text to this file's line ending."""
        return text.replace("\r\n", "\n").replace("\n", self.newline)

    def slice(self, span: Span) -> str:
        return self.text[span[0]:span[1]]

    def replace(self, span: Span, replacement: str) -> None:
        self.text = self.text[:span[0]] + self.nl(replacement) + self.text[span[1]:]

    def remove(self, span: Span) -> None:
        self.text = self.text[:span[0]] + self.text[span[1]:]

    def insert(self, offset: int, addition: str) -> None:
        self.text = self.text[:offset] + self.nl(addition) + self.text[offset:]


def atomic_write_bytes(path: Path, data: bytes) -> None:
    """Write to a temp file then rename over `path`, so readers never see a partial file."""
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        Path(tmp_name).unlink(missing_ok=True)
        raise


def require_index(spans: list, index: int, path: Path):
    if not 0 <= index < len(spans):
        raise IndexError(f"{path.name} has {len(spans)} entries; no entry {index}")
    return spans[index]
