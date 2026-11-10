"""Crash-recovery files: what the main window keeps of unsaved fractal edits, and the small file helpers the Fragments
window's session autosave shares.

Layout under the recovery folder (`config.RECOVERY_DIR`, else the per-user cache folder's `recovery/`):

    sessions/<instance>/current.fa   the unsaved fractal of one running instance (+ current.json: where it came from)
    sessions/<instance>.lock         that instance's lock (held while it runs; see `ui/recovery.py`)
    shelf/<stamp>-<name>.fa          unsaved edits left behind when another fractal was shown (+ .json)

A clean exit removes its session folder, so a session folder whose instance is no longer running is what a crash left
behind (`RecoveryStore.orphans`). Whether an instance runs is the caller's question (`is_alive`), because the answer
needs OS locks (Qt's `QLockFile`); this module stays Qt-free. Nothing here is ever written next to the user's files.
"""

from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from .fractal.formats import fa
from .fractal.scene import Flame

CURRENT = "current"
SHELF_FOLDER = "shelf"
SESSIONS_FOLDER = "sessions"


# --- file helpers (shared with the Fragments session autosave) ------------------------------------------------------------------
def write_atomically(path: Path, text: str) -> bool:
    """Write `text` to `path` through a temporary file (a crash mid-write never leaves half a file); False on failure."""
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(text, encoding="utf-8")
        os.replace(tmp, path)
        return True
    except OSError:
        return False


def read_text(path: Path) -> str | None:
    """The file's text, or None if it is missing or unreadable."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def remove_quietly(*paths: Path) -> None:
    for path in paths:
        try:
            path.unlink()
        except OSError:
            pass


# --- recovery entries ------------------------------------------------------------------------------------------------------
@dataclass
class RecoveryEntry:
    """One recoverable fractal: where its files are and where it came from.

    Attributes:
        name: The flame's name.
        source_path: The file it was opened from (None: it never had one).
        source_index: Its entry in that file.
        time: When it was last written (`time.time()`).
        labels: The last few undo labels (what had been done), for the prompt.
        fa_path: The `.fa` file holding the flame.
    """
    name: str
    source_path: str | None
    source_index: int
    time: float
    labels: list[str] = field(default_factory=list)
    fa_path: Path = Path()

    def load(self) -> Flame:
        """The recovered flame (raises `fa.FaParseError` / `OSError` if the file is damaged)."""
        return fa.parse_file(self.fa_path)[0]

    @property
    def describe(self) -> str:
        """"'x' (from candy.flame #3, edited 14:03)"."""
        where = f"from {Path(self.source_path).name} #{self.source_index + 1}, " if self.source_path else ""
        return f"'{self.name}' ({where}edited {time.strftime('%H:%M', time.localtime(self.time))})"


def _meta(flame: Flame, source_path: Path | None, source_index: int, labels: list[str]) -> dict:
    return {"name": flame.name, "source_path": str(source_path) if source_path is not None else None,
            "source_index": int(source_index), "time": time.time(), "labels": list(labels)[-8:]}


def _entry(fa_path: Path) -> RecoveryEntry | None:
    text = read_text(fa_path.with_suffix(".json"))
    if text is None or not fa_path.is_file():
        return None
    try:
        data = json.loads(text)
        return RecoveryEntry(str(data.get("name", "")), data.get("source_path"), int(data.get("source_index", 0)),
                             float(data.get("time", 0.0)), list(data.get("labels", [])), fa_path)
    except (ValueError, TypeError):
        return None


def _write(fa_path: Path, flame: Flame, meta: dict) -> bool:
    return write_atomically(fa_path, fa.document_text([flame])) and write_atomically(fa_path.with_suffix(".json"), json.dumps(meta))


class RecoveryStore:
    """The recovery folder of one running instance (see the module docstring)."""

    def __init__(self, folder: Path, instance: str, shelf_size: int = 20):
        self.folder = Path(folder)
        self.instance = instance
        self.shelf_size = shelf_size

    @property
    def session_dir(self) -> Path:
        return self.folder / SESSIONS_FOLDER / self.instance

    def lock_path(self, instance: str | None = None) -> Path:
        return self.folder / SESSIONS_FOLDER / f"{instance or self.instance}.lock"

    # --- this instance's unsaved fractal ---------------------------------------------------------------------------------
    def write_current(self, flame: Flame, source_path: Path | None, source_index: int, labels: list[str]) -> bool:
        """Keep the unsaved fractal (replacing the previous copy)."""
        return _write(self.session_dir / f"{CURRENT}.fa", flame, _meta(flame, source_path, source_index, labels))

    def current(self) -> RecoveryEntry | None:
        return _entry(self.session_dir / f"{CURRENT}.fa")

    def clear_current(self) -> None:
        remove_quietly(self.session_dir / f"{CURRENT}.fa", self.session_dir / f"{CURRENT}.json")

    def close(self) -> None:
        """A clean exit: nothing of this session needs recovering."""
        self.clear_current()
        try:
            self.session_dir.rmdir()
        except OSError:
            pass

    # --- what crashed instances left -------------------------------------------------------------------------------------
    def orphans(self, is_alive: Callable[[str], bool]) -> list[RecoveryEntry]:
        """The unsaved fractals of instances that are not running any more (newest first)."""
        root = self.folder / SESSIONS_FOLDER
        if not root.is_dir():
            return []
        entries = []
        for folder in root.iterdir():
            if folder.is_dir() and folder.name != self.instance and not is_alive(folder.name):
                entry = _entry(folder / f"{CURRENT}.fa")
                if entry is not None:
                    entries.append(entry)
                else:
                    self._drop_folder(folder)
        return sorted(entries, key=lambda e: -e.time)

    def discard(self, entry: RecoveryEntry) -> None:
        """Forget a recoverable fractal (its files, and its session folder when that is now empty)."""
        remove_quietly(entry.fa_path, entry.fa_path.with_suffix(".json"))
        if entry.fa_path.parent.parent.name == SESSIONS_FOLDER:
            self._drop_folder(entry.fa_path.parent)

    @staticmethod
    def _drop_folder(folder: Path) -> None:
        for child in list(folder.glob("*")):
            remove_quietly(child)
        try:
            folder.rmdir()
        except OSError:
            pass

    # --- the shelf of edits left behind ------------------------------------------------------------------------------------
    def shelve(self, flame: Flame, source_path: Path | None, source_index: int, labels: list[str]) -> RecoveryEntry | None:
        """Keep unsaved edits that are about to be replaced by another fractal (oldest dropped beyond `shelf_size`)."""
        stem = re.sub(r"[^A-Za-z0-9_-]+", "_", flame.name).strip("_")[:40] or "fractal"
        fa_path = self.folder / SHELF_FOLDER / f"{time.strftime('%Y%m%d-%H%M%S')}-{int(time.time() * 1000) % 1000:03d}-{stem}.fa"
        if not _write(fa_path, flame, _meta(flame, source_path, source_index, labels)):
            return None
        for old in self.shelf()[self.shelf_size:]:
            self.discard(old)
        return _entry(fa_path)

    def shelf(self) -> list[RecoveryEntry]:
        """The shelved edits, newest first."""
        folder = self.folder / SHELF_FOLDER
        if not folder.is_dir():
            return []
        entries = [e for e in (_entry(p) for p in folder.glob("*.fa")) if e is not None]
        return sorted(entries, key=lambda e: (-e.time, str(e.fa_path)))

    def clear_shelf(self) -> None:
        for entry in self.shelf():
            self.discard(entry)


__all__ = ["RecoveryStore", "RecoveryEntry", "write_atomically", "read_text", "remove_quietly"]
