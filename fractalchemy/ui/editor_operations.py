"""The Transform Editor's operations on transforms: triangle moves, structural edits and the 3D / weight helpers.

Everything here edits the document through the `EditorContext` (undoably) and knows nothing about
the window's widgets except the steps the Triangle tab offers (a `StepSource`). The canvas's
keyboard / double-click commands and the toolbar's buttons all land in `TransformOperations`,
so a nudge by arrow key and a nudge by button are the same code.
"""

from __future__ import annotations

import math
from typing import Callable, Protocol

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from ..fractal import triangles as T
from ..fractal import xform_ops
from ..fractal.scene import Affine, identity_affine
from ..fractal.triangles import CORNER_O, CORNER_X, CORNER_Y, Triangle
from .editor_context import FINAL_KEY, MODE_NORMAL, EditorContext

TRIANGLE_CLIPBOARD_PREFIX = "fractalchemy-triangle"
CORNERS_BY_NAME = {"x": CORNER_X, "o": CORNER_O, "y": CORNER_Y}


class StepSource(Protocol):
    """What the operations read from the Triangle tab: the rotate / move / scale amounts and the auto-weights choice."""

    def rotate_degrees(self) -> float:
        """The rotation step in degrees."""

    def move_amount(self) -> float:
        """The move step in fractal units."""

    def scale_factor(self) -> float:
        """The scale step as a factor (> 1)."""

    def auto_weights_enabled(self) -> bool:
        """Whether weights follow the triangles' areas."""


def modifier_factor(coarse: float, fine: float, modifiers=None) -> float:
    """Apophysis's step modifiers: Shift makes a step `coarse` times bigger, Ctrl `fine` times (a fraction) — else 1."""
    modifiers = QApplication.keyboardModifiers() if modifiers is None else modifiers
    if modifiers & Qt.KeyboardModifier.ControlModifier:
        return fine
    if modifiers & Qt.KeyboardModifier.ShiftModifier:
        return coarse
    return 1.0


def auto_zscale_value(coefs: Affine) -> float:
    """Apophysis's *auto pre_zscale*: √|det| of the affine (signed), 0 when the determinant is exactly 1."""
    a, b, c, d, _e, _f = coefs
    det = a * d - b * c
    return 0.0 if det == 1.0 else math.copysign(math.sqrt(abs(det)), det)


def parse_triangle_text(text: str) -> Affine | None:
    """Six finite numbers (optionally after the `fractalchemy-triangle` prefix) → an affine, else None."""
    parts = text.replace(",", " ").split()
    if parts and parts[0] == TRIANGLE_CLIPBOARD_PREFIX:
        parts = parts[1:]
    if len(parts) != 6:
        return None
    try:
        values = tuple(float(p) for p in parts)
    except ValueError:
        return None
    return values if all(math.isfinite(v) for v in values) else None   # type: ignore[return-value]


def triangle_text(affine: Affine) -> str:
    """The clipboard form of an affine (what `parse_triangle_text` reads back)."""
    return f"{TRIANGLE_CLIPBOARD_PREFIX} " + " ".join(repr(float(v)) for v in affine)


class TransformOperations:
    """Edits of the selected transform (or a given one), each one undo step.

    Attributes:
        context: Selection, mode and the document.
        pivot: Returns the pivot point rotations and scalings turn about (the canvas knows it).
        steps: The Triangle tab's amounts.
        auto_zscale_keys: Transforms whose `pre_zscale` follows their triangle (Apophysis's checkbox, per transform).
    """

    def __init__(self, context: EditorContext, pivot: Callable[[], tuple[float, float]], steps: StepSource):
        self.context = context
        self.pivot = pivot
        self.steps = steps
        self.auto_zscale_keys: set[object] = set()
        self._commands: dict[str, Callable[[object], None]] = {
            "reset-rotation": lambda key: self.edit_triangle(T.snap_rotation, "reset-rotation", key),
            "reset-scale": lambda key: self.edit_triangle(T.reset_scale, "reset-scale", key),
            "reset-position": lambda key: self.edit_triangle(lambda t: T.reset_corner(t, CORNER_O), "reset-position", key),
            "move-left": lambda key: self.move(-1, 0, key),
            "move-right": lambda key: self.move(1, 0, key),
            "move-up": lambda key: self.move(0, 1, key),
            "move-down": lambda key: self.move(0, -1, key),
            "rotate-ccw": lambda key: self.rotate(self.rotate_step(), key),
            "rotate-cw": lambda key: self.rotate(-self.rotate_step(), key),
            "scale-up": lambda key: self.scale(True, key),
            "scale-down": lambda key: self.scale(False, key),
        }

    @property
    def document(self):
        """The document the edits go to."""
        return self.context.document

    # --- one triangle ------------------------------------------------------------------------------------------
    def edit_triangle(self, fn: Callable[[Triangle], Triangle], kind: str, key: object = "selected") -> bool:
        """Replace a transform's triangle (the current mode's) by `fn(triangle)` as one undo step; True if it changed."""
        key = self.context.selected if key == "selected" else key
        triangle = self.context.triangle(key)
        if triangle is None:
            return False
        new = fn(triangle)
        if new == triangle:
            return False
        self.context.set_triangle(key, new, kind=f"{kind}:{self.context.mode}:{key}:{id(new)}")
        self.after_affine_edit(key, live=False)
        return True

    def rotate_step(self) -> float:
        """The Triangle tab's angle, ×6 with Shift, ÷6 with Ctrl."""
        return self.steps.rotate_degrees() * modifier_factor(6.0, 1 / 6.0)

    def rotate(self, degrees: float, key: object = "selected") -> None:
        """Rotate about the pivot (counter-clockwise for positive angles)."""
        pivot = self.pivot()
        self.edit_triangle(lambda t: T.rotate_about(t, pivot, math.radians(degrees)), "rotate", key)

    def move(self, dx: int, dy: int, key: object = "selected") -> None:
        """Nudge by the Triangle tab's step (Shift ×10, Ctrl ÷10) in the direction (dx, dy)."""
        step = self.steps.move_amount() * modifier_factor(10.0, 0.1)
        self.edit_triangle(lambda t: T.translate(t, dx * step, dy * step), "move", key)

    def scale(self, up: bool, key: object = "selected") -> None:
        """Grow (or shrink) about the pivot by the Triangle tab's percentage (Shift: squared, Ctrl: square root)."""
        factor = self.steps.scale_factor()
        if not up:
            factor = 1.0 / factor
        factor = factor ** modifier_factor(2.0, 0.5)
        pivot = self.pivot()
        self.edit_triangle(lambda t: T.scale_about(t, pivot, factor), "scale", key)

    def flip(self, horizontal: bool, key: object = "selected") -> None:
        """Mirror about the pivot's vertical (or horizontal) line."""
        pivot = self.pivot()
        self.edit_triangle(lambda t: T.flip_horizontal(t, pivot) if horizontal else T.flip_vertical(t, pivot), "flip", key)

    def reset(self, key: object = "selected") -> None:
        """Back to the reference triangle (the identity affine)."""
        self.edit_triangle(lambda _t: T.REFERENCE, "reset", key)

    def paste_affine(self, affine: Affine, key: object = "selected") -> bool:
        """Put an affine on a transform (this mode) as one undo step."""
        key = self.context.selected if key == "selected" else key
        if not self.context.set_affine(key, affine, kind=f"paste:{key}:{id(affine)}"):
            return False
        self.after_affine_edit(key, live=False)
        return True

    def run_command(self, command: str, key: object = "selected") -> bool:
        """A canvas command (`move-left`, `rotate-cw`, `reset-corner-x`, …); False if unknown."""
        for prefix, fn in (("reset-corner-", T.reset_corner), ("snap-corner-", T.snap_corner_rotation),
                           ("unit-corner-", T.reset_corner_scale)):
            if command.startswith(prefix) and command[len(prefix):] in CORNERS_BY_NAME:
                corner = CORNERS_BY_NAME[command[len(prefix):]]
                self.edit_triangle(lambda t, c=corner, f=fn: f(t, c), prefix.rstrip("-"), key)
                return True
        handler = self._commands.get(command)
        if handler is None:
            return False
        handler(key)
        return True

    # --- side effects of affine edits ---------------------------------------------------------------------------
    def after_affine_edit(self, key: object, live: bool) -> None:
        """Keep `pre_zscale` in step for transforms that asked for it; recompute area weights when a drag ends."""
        if self.context.mode != MODE_NORMAL:
            return
        if key in self.auto_zscale_keys:
            self.apply_auto_zscale(key)
        if not live and self.steps.auto_weights_enabled():
            self.document.area_weights()

    def apply_auto_zscale(self, key: object) -> None:
        """Set the transform's `pre_zscale` from its affine (removing it when not needed)."""
        xform = self.document.xform(key)
        if xform is None:
            return
        value = auto_zscale_value(xform.coefs)
        if xform.variations.get("pre_zscale", 0.0) != value:
            self.document.set_variation(key, "pre_zscale", value)

    def set_auto_zscale(self, key: object, on: bool) -> None:
        """Turn the automatic `pre_zscale` on or off for a transform (applying it at once when on)."""
        if on:
            self.auto_zscale_keys.add(key)
            self.apply_auto_zscale(key)
        else:
            self.auto_zscale_keys.discard(key)

    # --- whole transforms ---------------------------------------------------------------------------------------
    def add(self) -> None:
        """Append a new transform and select it."""
        self._select_result(self.document.add_xform())

    def duplicate(self) -> None:
        """Duplicate the selected transform (not the final one) and select the copy."""
        if not self.context.is_final:
            self._select_result(self.document.duplicate_xform(self.context.selected))

    def add_linked(self) -> None:
        """Add a transform linked by xaos to the selected one and select it."""
        if not self.context.is_final:
            self._select_result(self.document.add_linked_xform(self.context.selected))

    def delete(self) -> None:
        """Remove the selected transform (the final transform is disabled instead)."""
        if self.context.is_final:
            self.document.set_final_enabled(False)
        else:
            self._select_result(self.document.delete_xform(self.context.selected))

    def set_final_enabled(self, on: bool) -> None:
        """Add (and select) or remove the final transform."""
        flame = self.document.flame
        if flame is None or (flame.final is not None) == on:
            return
        self.document.set_final_enabled(on)
        if on:
            self.context.select(FINAL_KEY)

    def _select_result(self, index: int | None) -> None:
        if index is not None:
            self.context.select(index)

    # --- everything at once -------------------------------------------------------------------------------------
    def reset_all(self) -> None:
        """Every transform's triangle of the current mode back to the reference (one undo step)."""
        flame = self.document.flame
        if flame is None:
            return
        new = flame.copy()
        for xform in list(new.xforms) + ([new.final] if new.final else []):
            setattr(xform, self.context.mode, identity_affine())
        self.document.replace_flame_parameters(new, "reset-all")

    def new_flame(self) -> bool:
        """Apophysis's *New flame*: one linear transform, camera reset; palette, colouring and size kept (undoable)."""
        flame = self.document.flame
        if flame is None:
            return False
        new = flame.copy()
        new.xforms = [xform_ops.new_xform()]
        new.final = None
        cam = new.camera
        cam.center, cam.zoom, cam.rotate = (0.0, 0.0), 0.0, 0.0
        cam.scale = cam.width / 4.0          # Apophysis: pixels_per_unit = width / 4
        cam.pitch = cam.yaw = cam.pitch_y = cam.perspective = cam.zpos = cam.dof = 0.0
        self.document.replace_flame_parameters(new, "new-flame")
        self.context.select(0)
        return True


__all__ = ["TransformOperations", "StepSource", "modifier_factor", "auto_zscale_value", "parse_triangle_text", "triangle_text",
           "TRIANGLE_CLIPBOARD_PREFIX"]
