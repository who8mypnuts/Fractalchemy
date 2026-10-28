"""What the Transform Editor's parts share: the document, the selected transform and the affine mode.

The mode is which of a transform's three affines the triangles show and edit — **Pre-Affine**,
**Normal** (Apophysis's triangle) or **Post-Affine** (Apophysis's post-transform) — named by the
`XForm` attribute it edits: `pre`, `coefs`, `post`.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ..fractal.scene import Affine, Flame, XForm
from ..fractal.triangles import Triangle, affine_to_triangle, triangle_to_affine
from .fractal_document import FractalDocument

MODE_PRE, MODE_NORMAL, MODE_POST = "pre", "coefs", "post"
MODES = (MODE_PRE, MODE_NORMAL, MODE_POST)
MODE_LABELS = {MODE_PRE: "Pre-Affine", MODE_NORMAL: "Normal", MODE_POST: "Post-Affine"}
MODE_TIPS = {
    MODE_PRE: "Edit the pre affine: applied to the point first, before the normal triangle (Fractalchemy's addition)",
    MODE_NORMAL: "Edit the normal triangle: the affine applied before the variations (Apophysis's triangle)",
    MODE_POST: "Edit the post affine: applied after the variations (Apophysis's post-transform)",
}
FINAL_KEY = None   # the selection key of the final transform (transforms are keyed by index)


class EditorContext(QObject):
    """Selection and mode of the editor, with the document it edits.

    Signals:
        selection_changed(object): The selected transform changed (index, or None for the final transform).
        mode_changed(str): The affine mode changed (`pre` / `coefs` / `post`).
    """
    selection_changed = Signal(object)
    mode_changed = Signal(str)

    def __init__(self, document: FractalDocument, parent: QObject | None = None):
        super().__init__(parent)
        self.document = document
        self._selected: object = 0
        self._mode = MODE_NORMAL
        self._drag_serial = 0

    # --- flame / selection -----------------------------------------------------------------------------------
    @property
    def flame(self) -> Flame | None:
        """The flame being edited (None when nothing is loaded)."""
        return self.document.flame

    @property
    def selected(self) -> object:
        """Index of the selected transform, or None for the final transform."""
        return self._selected

    def keys(self) -> list[object]:
        """Selection keys in display order: every transform's index, then None if there is a final transform."""
        flame = self.flame
        if flame is None:
            return []
        keys: list[object] = list(range(len(flame.xforms)))
        if flame.final is not None:
            keys.append(FINAL_KEY)
        return keys

    def select(self, key: object) -> None:
        """Select a transform by key (an unknown key selects the first transform)."""
        if key not in self.keys():
            key = self.keys()[0] if self.keys() else 0
        if key != self._selected:
            self._selected = key
            self.selection_changed.emit(key)

    def reset_selection(self) -> None:
        """Back to the first transform without announcing (a new flame was loaded; the window rebuilds anyway)."""
        self._selected = 0

    def ensure_valid_selection(self) -> None:
        """After structural changes: keep the selection if it still exists, else select the last transform."""
        keys = self.keys()
        if self._selected not in keys:
            self._selected = keys[-1] if keys else 0
            self.selection_changed.emit(self._selected)

    def xform(self, key: object = "selected") -> XForm | None:
        """The selected transform (or the one with `key`); None if there is no such transform."""
        return self.document.xform(self._selected if key == "selected" else key)

    @property
    def is_final(self) -> bool:
        """True when the final transform is selected."""
        return self._selected is FINAL_KEY

    # --- mode --------------------------------------------------------------------------------------------------
    @property
    def mode(self) -> str:
        """Which affine is being edited: `pre`, `coefs` or `post`."""
        return self._mode

    def set_mode(self, mode: str) -> None:
        """Switch the affine being edited (announced with `mode_changed`).

        Raises:
            ValueError: For a name that is not one of `MODES`.
        """
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}")
        if mode != self._mode:
            self._mode = mode
            self.mode_changed.emit(mode)

    def affine(self, key: object = "selected", mode: str | None = None) -> Affine | None:
        """The affine the current (or given) mode edits, for the selected (or given) transform."""
        xform = self.xform(key)
        return None if xform is None else tuple(getattr(xform, mode or self._mode))

    def triangle(self, key: object = "selected", mode: str | None = None) -> Triangle | None:
        """The triangle of the affine the mode edits (editor space), or None without a transform."""
        affine = self.affine(key, mode)
        return None if affine is None else affine_to_triangle(affine)

    def set_triangle(self, key: object, triangle: Triangle, kind: str | None = None, mode: str | None = None,
                     sticky: bool = False) -> bool:
        """Store a triangle as the transform's affine for the mode (undoable; `kind` groups the steps of a drag, and
        `sticky` keeps them one undo step however long the drag pauses)."""
        which = mode or self._mode
        return self.document.set_affine(key, which, triangle_to_affine(triangle), kind or f"affine:{which}:{key}", sticky)

    def set_affine(self, key: object, coefs: Affine, kind: str | None = None, mode: str | None = None) -> bool:
        """Store an affine for the mode on a transform (undoable); False if there is no such transform."""
        which = mode or self._mode
        return self.document.set_affine(key, which, coefs, kind or f"affine:{which}:{key}")

    def new_drag_kind(self, key: object) -> str:
        """An undo kind unique to one drag, so every drag is its own undo step."""
        self._drag_serial += 1
        return f"drag:{self._mode}:{key}:{self._drag_serial}"


__all__ = ["EditorContext", "MODE_PRE", "MODE_NORMAL", "MODE_POST", "MODES", "MODE_LABELS", "MODE_TIPS", "FINAL_KEY"]
