"""The Fragments window's exploration helper: the History dock, snapshots, *Mutate* and *Randomize* from the strip.

A helper of `FragmentsWindow` (it holds the window as `w`). It keeps one list of snapshots per open document
(image + settings text + label) and shows the current document's in the `HistoryStrip`; restoring applies the
settings through the document (undoable). *Auto* snapshots wait `AUTO_DELAY_MS` after the last parameter change
so the viewport has had a chance to converge a little.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage

from .document import FragDocument
from .history_strip import HistoryStrip
from .parameter_panel import CAMERA_NAMES

if TYPE_CHECKING:
    from .window import FragmentsWindow


class ExploreCoordinator:
    """Snapshots, mutate and randomize for the History dock (see the module docstring)."""

    def __init__(self, window: "FragmentsWindow"):
        self.w = window
        self.strip = HistoryStrip(window)
        self._entries: dict[int, list[tuple[QImage | None, str, str]]] = {}
        self.dock = window.make_dock("History", "fragmentsHistory", self.strip, Qt.DockWidgetArea.BottomDockWidgetArea)
        self.dock.hide()
        self.strip.restore_requested.connect(self.restore)
        self.strip.snapshot_requested.connect(lambda: self.snapshot("snapshot"))
        self.strip.mutate_requested.connect(self.mutate)
        self.strip.randomize_requested.connect(self.randomize)
        self.strip.auto_timer.timeout.connect(self._auto_snapshot)

    # --- documents ------------------------------------------------------------------------------------------------------
    def watch(self, document: FragDocument) -> None:
        """Connect a newly opened document's parameter signals (for *Auto*)."""
        document.parameters_replaced.connect(lambda d=document: self._on_changed(d))
        document.parameters_changed.connect(lambda _n, _r, _b, d=document: self._on_changed(d))

    def forget(self, document: FragDocument) -> None:
        self._entries.pop(id(document), None)

    def show_document(self, document: FragDocument | None) -> None:
        """The current tab changed: the strip shows its snapshots."""
        self.strip.clear()
        if document is None:
            return
        for image, text, label in self._entries.get(id(document), []):
            self.strip.add_entry(image, text, label)

    def _on_changed(self, document: FragDocument) -> None:
        if document is self.w.tabs.document and self.strip.auto.isChecked() and self.dock.isVisible():
            self.strip.auto_timer.start()

    def _auto_snapshot(self) -> None:
        self.snapshot("auto")

    # --- snapshots ----------------------------------------------------------------------------------------------------------
    def snapshot(self, label: str = "") -> bool:
        """Keep the current look (viewport image + settings) for the current document."""
        document = self.w.tabs.document
        if document is None or document.source is None:
            return False
        text = document.state.to_text()
        image = self.w.viewport.image
        entries = self._entries.setdefault(id(document), [])
        caption = f"{len(entries) + 1} · {label}" if label else str(len(entries) + 1)
        if not self.strip.add_entry(image, text, caption):
            return False
        entries.append((image.copy() if image is not None else None, text, caption))
        return True

    def restore(self, text: str) -> None:
        document = self.w.tabs.document
        if document is None:
            return
        warnings = document.apply_settings(text, label="history")
        self.w.message("Restored a snapshot" + (f" ({warnings[0]})" if warnings else ""))

    # --- exploring ----------------------------------------------------------------------------------------------------------
    def mutate(self, strength: float, group_only: bool = False) -> None:
        """F10 / the strip's button: snapshot, then nudge the unlocked parameters by up to `strength` of their ranges."""
        if self.w.tabs.document is None or self.w.tabs.document.source is None:
            return
        self.snapshot("before mutate")
        count = self.w.parameters.mutate(strength, self.w.parameters.current_group() if group_only else None)
        if count == 0:
            self.w.message("Nothing to mutate (locked, or no sliders)")

    def randomize(self, group_only: bool = False) -> None:
        if self.w.tabs.document is None or self.w.tabs.document.source is None:
            return
        self.snapshot("before randomize")
        if group_only:
            self.w.parameters.randomize(group=self.w.parameters.current_group())
        else:
            self.w.parameters.randomize([n for n in self.w.parameters.widgets if n not in CAMERA_NAMES])


__all__ = ["ExploreCoordinator"]
