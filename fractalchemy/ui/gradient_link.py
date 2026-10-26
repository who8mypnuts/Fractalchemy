"""Keeps the Gradient Library window and the main window's fractal in step.

* Choosing a fractal loads its gradient into the Gradient Library (the same file entry
  when the fractal came from a `.flame` / `.chaos` / `.fa` file, so Save writes back
  into that flame; otherwise a loose copy of its palette).
* Editing the gradient — dragging nodes, sliders, the node operations, or choosing a
  different gradient in the library — recolours the fractal and re-renders the viewport.
* The viewport's picture is mirrored into the small preview beside the gradient strip.

Unsaved gradient edits are never thrown away silently: switching fractals asks first.
"""

from __future__ import annotations

from PySide6.QtCore import QObject

from .. import config
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
        self._synced_palette: list | None = None   # the flame palette the editor currently corresponds to
        fractal.flame_replaced.connect(self.sync_gradient_from_flame)
        fractal.flame_edited.connect(self._on_flame_edited)
        fractal.source_changed.connect(self._on_source_changed)
        gradient_window.document.gradient_replaced.connect(self._on_gradient_replaced)
        gradient_window.document.gradient_changed.connect(self.apply_gradient)
        gradient_window.document.stop_changed.connect(self.apply_gradient)
        viewport.image_changed.connect(gradient_window.show_fractal_image)

    # --- fractal → gradient ---------------------------------------------------
    def sync_gradient_from_flame(self) -> None:
        """Show the current fractal's gradient in the Gradient Library (asks about unsaved edits)."""
        flame = self._fractal.flame
        if flame is None:
            return
        files, document = self._window.files, self._window.document
        path, index = self._fractal.source_path, self._fractal.source_index
        self._synced_palette = list(flame.palette)
        if path is not None and GRADIENT_CATALOG.matches(path):
            if document.is_showing(path, index) and not document.modified:
                return
            if files.confirm_discard():
                files.open_path(path, index)
        elif files.confirm_discard():
            self._syncing = True
            try:
                files.show_gradient(Gradient(flame.name, simplify(flame.gradient.stops, config.IMPORT_SIMPLIFY_TOLERANCE)))
            finally:
                self._syncing = False

    def _on_flame_edited(self, _text: str) -> None:
        """After undo / redo the flame's palette may differ from the editor: refresh the editor in place."""
        flame, document = self._fractal.flame, self._window.document
        if flame is None or self._syncing or flame.palette == self._synced_palette:
            return
        self._syncing = True
        try:
            gradient = Gradient(document.gradient.name or flame.name, simplify(flame.gradient.stops, config.IMPORT_SIMPLIFY_TOLERANCE))
            document.replace(gradient, document.source_path, document.source_index)
            document.modified = True
            self._synced_palette = list(flame.palette)
        finally:
            self._syncing = False

    def _on_source_changed(self) -> None:
        """The fractal was saved somewhere: its gradient (already inside it) lives there too now."""
        path, index = self._fractal.source_path, self._fractal.source_index
        if path is None or not GRADIENT_CATALOG.matches(path):
            return
        self._window.document.modified = False
        self._synced_palette = list(self._fractal.flame.palette)
        self._window.files.open_path(path, index)

    # --- gradient → fractal ---------------------------------------------------
    def _on_gradient_replaced(self) -> None:
        """A gradient was loaded: apply it unless it *is* the fractal's own entry (already shown)."""
        if self._syncing:
            return
        document = self._window.document
        path = self._fractal.source_path
        if path is not None and document.is_showing(path, self._fractal.source_index):
            self._synced_palette = list(self._fractal.flame.palette)   # the fractal's own entry: already in step
            return
        self.apply_gradient()

    def apply_gradient(self) -> None:
        """Recolour the fractal from the gradient being edited (re-renders if anything changed)."""
        if self._fractal.flame is None or not self._window.document.gradient.stops:
            return
        # `set_gradient` emits flame_edited before we can note the new palette; guard so the editor's own
        # edit is never mistaken for an undo and "refreshed" (which resampled and moved its nodes)
        self._syncing = True
        try:
            self._fractal.set_gradient(self._window.document.gradient)
        finally:
            self._syncing = False
        self._synced_palette = list(self._fractal.flame.palette)
