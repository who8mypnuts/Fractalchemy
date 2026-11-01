"""The Camera menu: bookmarks (named camera positions kept in the `.fafrag` metadata) and flight recording.

A **bookmark** is the camera's settings text under a name — `Ctrl+B` adds one, the menu lists them, choosing one
applies it as one undoable step; they live in `metadata.tabs["bookmarks"]` so FragM ignores them. **Record camera
path** samples the camera while you fly (every `RECORD_INTERVAL_MS`, only when it moved) and, when stopped, writes
the samples into the source as `KeyFrame.nnnn` presets — the animation path of a flight without pressing F8 at every
turn. A helper of `FragmentsWindow` (it holds the window as `w`).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QInputDialog, QMenu

from ...fragments import presets

if TYPE_CHECKING:
    from .window import FragmentsWindow

RECORD_INTERVAL_MS = 400
BOOKMARKS_KEY = "bookmarks"


class CameraActions:
    """Bookmarks and flight recording (see the module docstring)."""

    def __init__(self, window: "FragmentsWindow"):
        self.w = window
        self.menu: QMenu | None = None
        self._samples: list[str] = []
        self._timer = QTimer(window, interval=RECORD_INTERVAL_MS)
        self._timer.timeout.connect(self._sample)

    # --- bookmarks -------------------------------------------------------------------------------------------------------
    def bookmarks(self) -> list[dict]:
        document = self.w.tabs.document
        if document is None:
            return []
        stored = document.metadata.tabs.get(BOOKMARKS_KEY, [])
        return [b for b in stored if isinstance(b, dict) and "name" in b and "settings" in b]

    def add_bookmark(self) -> None:
        """`Ctrl+B`: the current camera under a name."""
        document = self.w.tabs.document
        if document is None or document.source is None:
            return
        name, ok = QInputDialog.getText(self.w, "Add camera bookmark", "Name:", text=f"Bookmark {len(self.bookmarks()) + 1}")
        if not ok or not name.strip():
            return
        entries = [b for b in self.bookmarks() if b["name"] != name.strip()]
        entries.append({"name": name.strip(), "settings": document.state.camera_text(document.camera_kind)})
        document.set_tab_metadata(BOOKMARKS_KEY, entries)
        self.refresh_menu()
        self.w.message(f"Bookmark '{name.strip()}' added")

    def go_to(self, name: str) -> None:
        document = self.w.tabs.document
        for bookmark in self.bookmarks():
            if bookmark["name"] == name and document is not None:
                document.apply_settings(bookmark["settings"], label=f"bookmark {name}")
                self.w.message(f"Camera: {name}")
                return

    def remove(self, name: str) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.set_tab_metadata(BOOKMARKS_KEY, [b for b in self.bookmarks() if b["name"] != name])
            self.refresh_menu()

    def refresh_menu(self) -> None:
        """Rebuild the bookmark entries of the Camera menu."""
        if self.menu is None:
            return
        self.menu.clear()
        self.menu.addAction(self.w.actions.add_bookmark)
        entries = self.bookmarks()
        if entries:
            self.menu.addSeparator()
            for bookmark in entries:
                self.menu.addAction(bookmark["name"], lambda n=bookmark["name"]: self.go_to(n))
            remove = self.menu.addMenu("Remove bookmark")
            for bookmark in entries:
                remove.addAction(bookmark["name"], lambda n=bookmark["name"]: self.remove(n))
        self.menu.addSeparator()
        self.menu.addAction(self.w.actions.record_path)

    # --- recording -------------------------------------------------------------------------------------------------------
    @property
    def recording(self) -> bool:
        return self._timer.isActive()

    def set_recording(self, on: bool) -> None:
        """*Record camera path*: sample the camera while flying; off writes the samples as keyframe presets."""
        document = self.w.tabs.document
        if on:
            if document is None or document.source is None or document.camera_kind != "3D":
                self.w.actions.record_path.setChecked(False)
                self.w.message("Recording needs a built 3D fragment")
                return
            self._samples = [document.state.camera_text("3D")]
            self._timer.start()
            self.w.message("Recording the camera path — fly, then turn recording off to write the keyframes")
            return
        self._timer.stop()
        self._write_keyframes()

    def _sample(self) -> None:
        document = self.w.tabs.document
        if document is None:
            self._timer.stop()
            return
        text = document.state.camera_text("3D")
        if text != self._samples[-1]:
            self._samples.append(text)

    def _write_keyframes(self) -> None:
        document = self.w.tabs.document
        samples, self._samples = self._samples, []
        if document is None or document.source is None or len(samples) < 2:
            self.w.message("Nothing recorded (the camera did not move)")
            return
        text = document.text
        existing = list(document.source.presets)
        names = []
        for body in samples:
            name = presets.next_keyframe_name(existing)
            existing.append(name)
            names.append(name)
            text = presets.replace_preset(text, name, body)
        self.w.replace_text(text)
        self.w.build_document(document)
        self.w.message(f"Recorded {len(names)} keyframes ({names[0]} … {names[-1]}); set the animation length and play")


__all__ = ["CameraActions", "RECORD_INTERVAL_MS"]
