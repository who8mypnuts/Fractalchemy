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
    """A text file held in memory for span-based edits.

    Attributes:
        path: Where the text was read from / will be written to.
        text: The decoded content.
        newline: The file's line ending, used to normalise inserted text.
    """
    path: Path
    text: str
    newline: str

    @classmethod
    def read(cls, path: Path) -> "TextFile":
        """Load `path`, detecting its line ending."""
        raw = path.read_bytes()
        return cls(path, raw.decode("utf-8", errors="replace"), detect_newline(raw))

    @classmethod
    def empty(cls, path: Path, newline: str = "\r\n") -> "TextFile":
        """An in-memory file with no content yet (for creating new files)."""
        return cls(path, "", newline)

    def write(self) -> None:
        """Write the text back atomically."""
        atomic_write_bytes(self.path, self.text.encode("utf-8"))

    def nl(self, text: str) -> str:
        """Normalise '\\n' in generated text to this file's line ending."""
        return text.replace("\r\n", "\n").replace("\n", self.newline)

    def slice(self, span: Span) -> str:
        """The text inside `span`."""
        return self.text[span[0]:span[1]]

    def replace(self, span: Span, replacement: str) -> None:
        """Swap the text inside `span` for `replacement` (line endings normalised)."""
        self.text = self.text[:span[0]] + self.nl(replacement) + self.text[span[1]:]

    def remove(self, span: Span) -> None:
        """Delete the text inside `span`."""
        self.text = self.text[:span[0]] + self.text[span[1]:]

    def insert(self, offset: int, addition: str) -> None:
        """Insert `addition` at `offset` (line endings normalised)."""
        self.text = self.text[:offset] + self.nl(addition) + self.text[offset:]


def detect_newline(content: bytes | str) -> str:
    """The line ending a file uses: CRLF if it appears anywhere, else LF."""
    crlf = b"\r\n" if isinstance(content, bytes) else "\r\n"
    return "\r\n" if crlf in content else "\n"


def xml_attr(text: str) -> str:
    """Escape `text` for use inside a double-quoted XML attribute."""
    return text.replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")


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
    """Return `spans[index]`, raising a clear IndexError naming the file when out of range."""
    if not 0 <= index < len(spans):
        raise IndexError(f"{path.name} has {len(spans)} entries; no entry {index}")
    return spans[index]
