"""The user's list of library directories, persisted with QSettings."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QSettings, Signal

KEY = "library/roots"


class LibraryRoots(QObject):
    """The list of folders in the library, persisted through QSettings.

    Signals:
        added(Path): A folder was added.
        removed(Path): A folder was removed.
    """
    added = Signal(Path)
    removed = Signal(Path)

    def __init__(self, settings: QSettings | None = None, parent: QObject | None = None, key: str = KEY):
        """Args:
            settings: Backing store; defaults to the application's QSettings.
            parent: Qt parent.
            key: Settings key of the folder list (each library has its own).
        """
        super().__init__(parent)
        self._settings = settings or QSettings()
        self._key = key
        self._paths: list[Path] = self._load()

    def paths(self) -> list[Path]:
        """The library folders, in the order they were added."""
        return list(self._paths)

    def add(self, path: Path) -> bool:
        """Add a folder. Returns False if it is already present or not a directory."""
        path = Path(path).resolve()
        if path in self._paths or not path.is_dir():
            return False
        self._paths.append(path)
        self._store()
        self.added.emit(path)
        return True

    def remove(self, path: Path) -> bool:
        """Remove a folder. Returns False if it was not in the library."""
        path = Path(path).resolve()
        if path not in self._paths:
            return False
        self._paths.remove(path)
        self._store()
        self.removed.emit(path)
        return True

    def _load(self) -> list[Path]:
        stored = self._settings.value(self._key, [])
        if isinstance(stored, str):  # QSettings collapses a one-item list to a string
            stored = [stored]
        return [Path(p) for p in stored or []]

    def _store(self) -> None:
        self._settings.setValue(self._key, [str(p) for p in self._paths])
        self._settings.sync()
