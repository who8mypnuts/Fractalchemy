"""The Fragments window's sessions: *Save session* / *Open session*, the autosave and crash recovery.

A helper of `FragmentsWindow` (it holds the window as `w`). `capture` turns the tabs into a `fragments.session.Session`
(the unsaved text of modified tabs included, the settings text of every tab), `restore` opens them again — files
from disk, unsaved ones from the stored text, each with its settings applied. The autosave timer writes the session
to the cache folder every `autosave_minutes`; a clean shutdown removes it, so when one is found at start-up the
window offers to recover it (the tabs restored from the settings come first, recovered ones are added).
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QFileDialog, QMessageBox

from ...formulas.loader import cache_dir
from ...fragments.session import SESSION_SUFFIX, AutosaveStore, Session, SessionTab

if TYPE_CHECKING:
    from .window import FragmentsWindow

SESSION_FILTER = f"Fragment sessions (*{SESSION_SUFFIX});;All files (*)"
FOLDER_KEY = "fragments/session_folder"


class SessionActions:
    """Sessions and the autosave (see the module docstring)."""

    def __init__(self, window: "FragmentsWindow", store: AutosaveStore | None = None):
        self.w = window
        self.autosave = store if store is not None else AutosaveStore(cache_dir() / "fragments")
        self._timer = QTimer(window)
        self._timer.timeout.connect(self.autosave_now)
        self.set_interval(window.prefs.autosave_minutes)

    # --- capture / restore ----------------------------------------------------------------------------------------------
    def capture(self) -> Session:
        """The open tabs as a session."""
        tabs = []
        for tab in self.w.tabs.tabs:
            document = tab.document
            settings = document.state.to_text() if document.source is not None else ""
            tabs.append(SessionTab(str(document.path) if document.path else None, document.text if document.modified or document.path is None else None,
                                   settings, document.current_preset, document.modified))
        return Session(tabs, max(0, self.w.tabs.bar.currentIndex()))

    def restore(self, session: Session) -> int:
        """Open the session's tabs; returns how many were opened."""
        opened = 0
        for entry in session.tabs:
            path = Path(entry.path) if entry.path else None
            if entry.text is not None:
                document = self.w.tabs.open_text(entry.text, path if path and path.is_file() else None)
                if entry.modified:
                    document.mark_modified()
            elif path is not None and path.is_file():
                document = self.w.files.open_path(path)
                if document is None:
                    continue
            else:
                continue
            if entry.settings:
                self._apply_when_built(document, entry.settings)
            opened += 1
        if 0 <= session.current < self.w.tabs.bar.count():
            self.w.tabs.bar.setCurrentIndex(session.current)
        return opened

    def _apply_when_built(self, document, settings: str) -> None:
        if document.source is not None:
            document.apply_settings(settings, label="session")
            return

        def once(_source) -> None:
            document.built.disconnect(once)
            document.apply_settings(settings, label="session")
        document.built.connect(once)

    # --- menu actions -------------------------------------------------------------------------------------------------------
    def save_session(self) -> bool:
        folder = Path(str(self.w._settings.value(FOLDER_KEY, str(Path.home()))))
        chosen, _filter = QFileDialog.getSaveFileName(self.w, "Save session", str(folder / f"session{SESSION_SUFFIX}"), SESSION_FILTER)
        if not chosen:
            return False
        try:
            path = self.capture().write(Path(chosen))
        except OSError as exc:
            QMessageBox.warning(self.w, "Fragments", f"Cannot write the session:\n{exc}")
            return False
        self.w._settings.setValue(FOLDER_KEY, str(path.parent))
        self.w.message(f"Session saved as {path.name}")
        return True

    def open_session(self, path: Path | None = None) -> bool:
        if path is None:
            folder = Path(str(self.w._settings.value(FOLDER_KEY, str(Path.home()))))
            chosen, _filter = QFileDialog.getOpenFileName(self.w, "Open session", str(folder), SESSION_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
        try:
            session = Session.read(path)
        except (OSError, ValueError) as exc:
            QMessageBox.warning(self.w, "Fragments", f"Cannot read {path.name}:\n{exc}")
            return False
        count = self.restore(session)
        self.w.message(f"Session {path.name}: {count} tabs opened")
        return count > 0

    # --- autosave / recovery ---------------------------------------------------------------------------------------------------
    def set_interval(self, minutes: int) -> None:
        if minutes > 0:
            self._timer.start(int(minutes) * 60 * 1000)
        else:
            self._timer.stop()

    def autosave_now(self) -> None:
        """Write the autosave (nothing when no tab is open — then a stale file is removed)."""
        session = self.capture()
        if session.empty:
            self.autosave.clear()
        else:
            self.autosave.write(session)

    def clean_shutdown(self) -> None:
        self.autosave.clear()

    def pending_recovery(self) -> Session | None:
        """The autosave left by a run that did not end cleanly, if any."""
        session = self.autosave.read()
        return session if session is not None and not session.empty else None

    def announce_recovery(self) -> bool:
        """At start-up: say (log + status bar, no dialog) that an autosave is waiting; *File ▸ Recover last session* restores it."""
        session = self.pending_recovery()
        if session is None:
            return False
        self.w.log.add("warning", f"The last Fragments session did not end cleanly — File ▸ Recover last session brings back {session.describe()}")
        self.w.message("A session autosave is waiting: File ▸ Recover last session")
        return True

    def recover(self) -> bool:
        """*Recover last session*: restore the autosave's tabs (asks first) and forget it."""
        session = self.pending_recovery()
        if session is None:
            self.w.message("No session to recover")
            return False
        answer = QMessageBox.question(self.w, "Recover the last session?", f"{session.describe()}\n\nRecover its tabs?",
                                      QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if answer != QMessageBox.StandardButton.Yes:
            return False
        self.autosave.clear()
        count = self.restore(session)
        self.w.message(f"Recovered {count} tabs")
        return count > 0


__all__ = ["SessionActions", "SESSION_FILTER"]
