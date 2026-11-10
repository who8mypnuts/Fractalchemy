"""*File ▸ Open Recent*: the fractals opened or saved lately, most recent first.

`RecentFiles` keeps up to `MAX_RECENT` entries — (path, entry index, flame name, time) — in QSettings (`recent/fractals`,
JSON), moves an entry to the front whenever it is opened or saved again (one entry per path + index), and fills a
`QMenu`: "name — file.flame (#3)", missing files shown disabled, and *Clear list*. Choosing an entry calls the
`open_entry(path, index)` callback the main window supplies.
"""

from __future__ import annotations

import json
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtWidgets import QMenu

MAX_RECENT = 10
SETTINGS_KEY = "recent/fractals"


@dataclass(frozen=True)
class RecentEntry:
    """One remembered fractal."""
    path: str
    index: int
    name: str
    time: float

    @property
    def exists(self) -> bool:
        return Path(self.path).is_file()

    @property
    def title(self) -> str:
        """"name — file.flame (#3)"."""
        return f"{self.name or Path(self.path).stem} — {Path(self.path).name} (#{self.index + 1})"


class RecentFiles(QObject):
    """The recent-fractals list (see the module docstring).

    Signals:
        changed(): The list changed (menus rebuild themselves on show, so this is for other views).
    """
    changed = Signal()

    def __init__(self, settings: QSettings, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings
        self._entries: list[RecentEntry] = self._load()

    def _load(self) -> list[RecentEntry]:
        try:
            data = json.loads(self._settings.value(SETTINGS_KEY, "[]") or "[]")
            return [RecentEntry(str(d["path"]), int(d.get("index", 0)), str(d.get("name", "")), float(d.get("time", 0.0)))
                    for d in data][:MAX_RECENT]
        except (TypeError, ValueError, KeyError, json.JSONDecodeError):
            return []

    def _save(self) -> None:
        self._settings.setValue(SETTINGS_KEY, json.dumps([asdict(e) for e in self._entries]))
        self.changed.emit()

    @property
    def entries(self) -> list[RecentEntry]:
        return list(self._entries)

    def add(self, path: Path, index: int, name: str) -> None:
        """Put (path, index) at the front (replacing an older entry for the same place)."""
        key = (str(Path(path)), int(index))
        self._entries = [e for e in self._entries if (e.path, e.index) != key]
        self._entries.insert(0, RecentEntry(key[0], key[1], name, time.time()))
        del self._entries[MAX_RECENT:]
        self._save()

    def remove(self, path: str, index: int) -> None:
        self._entries = [e for e in self._entries if (e.path, e.index) != (path, index)]
        self._save()

    def clear(self) -> None:
        self._entries = []
        self._save()

    def populate(self, menu: QMenu, open_entry: Callable[[Path, int], None]) -> None:
        """Fill `menu` with the entries (missing files disabled) and *Clear list*."""
        menu.clear()
        for entry in self._entries:
            action = menu.addAction(entry.title + ("" if entry.exists else "  (missing)"),
                                    lambda _checked=False, e=entry: open_entry(Path(e.path), e.index))
            action.setToolTip(entry.path)
            action.setEnabled(entry.exists)
        if not self._entries:
            menu.addAction("No recent fractals").setEnabled(False)
        menu.addSeparator()
        clear = menu.addAction("Clear list", self.clear)
        clear.setEnabled(bool(self._entries))


__all__ = ["RecentFiles", "RecentEntry", "MAX_RECENT"]
