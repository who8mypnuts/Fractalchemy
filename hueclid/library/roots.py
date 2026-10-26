"""The user's list of library directories, persisted with QSettings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

KEY = "library/roots"


class LibraryRoots(QObject):
    added = Signal(Path)
    removed = Signal(Path)

    def __init__(self, settings: QSettings | None = None, parent: QObject | None = None):
        super().__init__(parent)
        self._settings = settings or QSettings()
        self._paths: list[Path] = self._load()

    def paths(self) -> list[Path]:
        return list(self._paths)

    def add(self, path: Path) -> bool:
        path = Path(path).resolve()
        if path in self._paths or not path.is_dir():
            return False
        self._paths.append(path)
        self._store()
        self.added.emit(path)
        return True

    def remove(self, path: Path) -> bool:
        path = Path(path).resolve()
        if path not in self._paths:
            return False
        self._paths.remove(path)
        self._store()
        self.removed.emit(path)
        return True

    def _load(self) -> list[Path]:
        stored = self._settings.value(KEY, [])
        if isinstance(stored, str):  # QSettings collapses a one-item list to a string
            stored = [stored]
        return [Path(p) for p in stored or []]

    def _store(self) -> None:
        self._settings.setValue(KEY, [str(p) for p in self._paths])
        self._settings.sync()
