"""Keeps the Gradient Library window and the main window's fractal in step.

* **Switching fractals** loads the new fractal's gradient into the Gradient Library: the same file entry when the
  fractal came from a `.flame` / `.chaos` / `.fa` file, so *Save* writes back into that flame, otherwise a loose copy
  of its palette.
* **Following the fractal.** When the fractal's palette changes from outside the Gradient Library, the library shows
  the new gradient at once. That covers undo / redo, Paste Parameters, a script's result, the Transform Editor's
  whole-flame operations, and adopting a mutant or a child in the Mutate & Breed window. If the library was showing
  the fractal's own entry, the entry link is kept; otherwise the followed gradient is a loose copy, so a later *Save*
  can never write the fractal's palette into an unrelated gradient file.
* **Editing the gradient** (dragging nodes, sliders, the node operations, or choosing a different gradient in the
  library) recolours the fractal and re-renders the viewport.
* The viewport's picture is mirrored into the small preview beside the gradient strip.

Neither switching nor following ever asks about unsaved gradient edits. Every edit made in the Gradient Library has
already been applied to the fractal, and lives in the fractal's undo history, so nothing is lost by showing another
gradient. The library still asks when *it* replaces its gradient: its own File ▸ Open, a click in its library, its
browser strip, and quitting.

Change detection: the library's gradient is a *simplified* copy of the 256-entry palette, so comparing samples would
see a difference after every undo. The link therefore remembers the palette it last applied or showed
(`_palette_seen`) and follows only when the fractal's palette differs from that. A camera-only undo leaves the
library, its node selection and its pending slider adjustments untouched.
"""

from __future__ import annotations

from contextlib import contextmanager

from PySide6.QtCore import QObject

from .. import config
from ..fractal.scene import Flame
from ..library.catalog import GRADIENT_CATALOG
from ..model import Gradient, simplify
from .fractal_document import FractalDocument
from .fractal_viewport import FractalViewport
from .gradient_library_window import GradientLibraryWindow


class GradientLink(QObject):
    """Two-way binding between a FractalDocument and the Gradient Library's GradientDocument."""

    def __init__(self, fractal: FractalDocument, gradient_window: GradientLibraryWindow, viewport: FractalViewport,
                 parent: QObject | None = None):
        super().__init__(parent)
        self._fractal = fractal
        self._window = gradient_window
        self._syncing = False
        self._palette_seen: list | None = None      # the fractal palette the library last showed or applied
        fractal.flame_replaced.connect(self.sync_gradient_from_flame)
        fractal.flame_restored.connect(self.follow_flame)
        gradient_window.document.gradient_replaced.connect(self._on_gradient_replaced)
        gradient_window.document.gradient_changed.connect(self.apply_gradient)
        gradient_window.document.stop_changed.connect(self.apply_gradient)
        viewport.image_changed.connect(gradient_window.show_fractal_image)

    # --- fractal → gradient ---------------------------------------------------
    def sync_gradient_from_flame(self) -> None:
        """Show a newly chosen fractal's gradient in the Gradient Library (never asks; see the module docstring)."""
        flame = self._fractal.flame
        if flame is None:
            return
        self._palette_seen = list(flame.palette)
        files, document = self._window.files, self._window.document
        path, index = self._fractal.source_path, self._fractal.source_index
        if path is not None and GRADIENT_CATALOG.matches(path):
            if not (document.is_showing(path, index) and not document.modified):
                files.open_path(path, index)
        else:
            with self._quietly():
                files.show_gradient(self._gradient_of(flame))

    def follow_flame(self) -> None:
        """The fractal's state was restored or replaced in place (undo / redo / paste / script / mutation): show its
        palette if it changed, without asking and without applying it back."""
        flame = self._fractal.flame
        if flame is None or flame.palette == self._palette_seen:
            return
        self._palette_seen = list(flame.palette)
        gradient = self._gradient_of(flame)
        document = self._window.document
        path, index = self._fractal.source_path, self._fractal.source_index
        with self._quietly():
            if path is not None and document.is_showing(path, index):
                document.follow(gradient)                # still the fractal's own entry: Save writes into its flame
            else:
                self._window.files.show_gradient(gradient)

    # --- gradient → fractal ---------------------------------------------------
    def _on_gradient_replaced(self) -> None:
        """A gradient was loaded: apply it unless it *is* the fractal's own entry (already shown)."""
        if self._syncing:
            return
        document = self._window.document
        path = self._fractal.source_path
        if path is not None and document.is_showing(path, self._fractal.source_index):
            return
        self.apply_gradient()

    def apply_gradient(self) -> None:
        """Recolour the fractal from the gradient being edited (re-renders if anything changed)."""
        if self._fractal.flame is None or not self._window.document.gradient.stops:
            return
        self._fractal.set_gradient(self._window.document.gradient, hint=self._window.document.last_hint)
        self._palette_seen = list(self._fractal.flame.palette)

    # --- helpers ----------------------------------------------------------------
    @staticmethod
    def _gradient_of(flame: Flame) -> Gradient:
        """The flame's palette as editable nodes (simplified, as when a file is imported)."""
        return Gradient(flame.name, simplify(flame.gradient.stops, config.IMPORT_SIMPLIFY_TOLERANCE))

    @contextmanager
    def _quietly(self):
        """Show a gradient in the library without applying it back to the fractal."""
        self._syncing = True
        try:
            yield
        finally:
            self._syncing = False
