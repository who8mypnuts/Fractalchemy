"""Notice files changed by other programs and ask for a rescan of the affected root.

After every scan the controller hands us the directories and files it saw;
we keep QFileSystemWatcher in step with that list. Events are debounced so a
burst (e.g. Apophysis saving several files) becomes one rescan.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QFileSystemWatcher, QObject, QTimer, Signal

from .scanner import ScannedDir

DEBOUNCE_MS = 600
MAX_WATCHED_FILES = 4000  # stay well under typical inotify limits; dirs are always watched


_LOOSE = Path("<opened file>")   # pseudo root for the single watched loose file


class LibraryWatcher(QObject):
    """Keeps a QFileSystemWatcher in step with scan results and debounces its events.

    Signals:
        root_changed(Path): Something under this root changed; rescan it.
        file_changed(Path): A watched file was modified or replaced.
        loose_file_changed(Path): The opened (loose) file was modified or replaced.
    """
    root_changed = Signal(Path)
    file_changed = Signal(Path)
    loose_file_changed = Signal(Path)

    def __init__(self, parent: QObject | None = None):
        """Create the watcher and its debounce timer."""
        super().__init__(parent)
        self._watcher = QFileSystemWatcher(self)
        self._roots: dict[Path, set[str]] = {}       # root -> watched paths (as strings)
        self._dirty: set[Path] = set()
        self._timer = QTimer(self, singleShot=True, interval=DEBOUNCE_MS)
        self._timer.timeout.connect(self._flush)
        self._watcher.directoryChanged.connect(self._on_changed)
        self._watcher.fileChanged.connect(self._on_file_changed)

    # --- keeping watches in step with scans --------------------------------
    def track(self, scanned: ScannedDir) -> None:
        """Watch exactly the folders and files found in `scanned` (adding and removing as needed)."""
        wanted = {str(p) for p in _paths_of(scanned)}
        current = self._roots.get(scanned.path, set())
        if current - wanted:
            self._watcher.removePaths(sorted(current - wanted))
        if wanted - current:
            self._watcher.addPaths(sorted(wanted - current))
        self._roots[scanned.path] = wanted

    def forget(self, root: Path) -> None:
        """Stop watching everything under `root`."""
        paths = self._roots.pop(root, set())
        if paths:
            self._watcher.removePaths(sorted(paths))

    def watch_file(self, path: Path | None) -> None:
        """Watch one loose file (the opened one); None stops watching the previous one."""
        previous = self._roots.pop(_LOOSE, set())
        if previous:
            self._watcher.removePaths(sorted(previous))
        if path is not None:
            self._watcher.addPath(str(path))
            self._roots[_LOOSE] = {str(path)}

    # --- events -------------------------------------------------------------
    def _on_changed(self, changed: str) -> None:
        root = self._root_for(Path(changed))
        if root is not None:
            self._dirty.add(root)
            self._timer.start()

    def _on_file_changed(self, changed: str) -> None:
        self.file_changed.emit(Path(changed))
        if str(changed) in self._roots.get(_LOOSE, set()):
            if not Path(changed).exists():
                return
            self._watcher.addPath(changed)   # editors that replace the file drop the watch: re-add it
            self.loose_file_changed.emit(Path(changed))
            return
        self._on_changed(changed)

    def _flush(self) -> None:
        dirty, self._dirty = self._dirty, set()
        for root in dirty:
            self.root_changed.emit(root)

    def _root_for(self, path: Path) -> Path | None:
        for root, watched in self._roots.items():
            if str(path) in watched:
                return root
        return None


def _paths_of(scanned: ScannedDir) -> list[Path]:
    dirs, files = [], []
    _collect(scanned, dirs, files)
    return dirs + files[:MAX_WATCHED_FILES]


def _collect(node: ScannedDir, dirs: list[Path], files: list[Path]) -> None:
    dirs.append(node.path)
    files.extend(f.path for f in node.files)
    for sub in node.dirs:
        _collect(sub, dirs, files)
