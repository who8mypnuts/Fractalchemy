"""The flame currently shown in the main window, plus where it came from."""

from __future__ import annotations

import time
from pathlib import Path

from typing import Callable

from PySide6.QtCore import QObject, Signal

from ..fractal import xform_ops
from ..fractal.scene import Affine, Flame, XForm
from ..model import Gradient

UNDO_COALESCE_SECONDS = 1.0   # edits of the same kind within this window (slider drags) are one undo step
UNDO_LIMIT = 200


class FractalDocument(QObject):
    """Holds the current Flame; every change is announced so the viewport and status bar follow.

    Signals:
        flame_replaced(): A different flame was loaded.
        flame_renamed(): The flame took the name it was saved under.
        camera_changed(): The view (center / zoom / rotation / 3D camera) of the current flame changed.
        palette_changed(): The flame's colours changed (e.g. edited in the Gradient Library).
        coloring_changed(): Brightness / gamma / threshold / vibrancy / background changed.
        image_size_changed(): The output resolution chosen for the viewer changed.
        modified_changed(bool): Whether the flame differs from what was loaded / last saved.
        flame_restored(): Undo / redo / paste put a different state in place (anything may have changed).
        undo_changed(bool, bool): (can undo, can redo).
        xform_changed(object, str): One transform's values changed; the arguments are its index (None for the
            final transform) and what changed: `affine`, `variations`, `params`, `fields` (weight / colour / name…),
            `chaos` or `all`.
        transforms_changed(): Transforms were added, removed or reordered, or the final transform was toggled.
    """
    flame_replaced = Signal()
    flame_renamed = Signal()
    camera_changed = Signal()
    palette_changed = Signal()
    coloring_changed = Signal()
    image_size_changed = Signal()
    modified_changed = Signal(bool)
    flame_restored = Signal()
    undo_changed = Signal(bool, bool)
    xform_changed = Signal(object, str)
    transforms_changed = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._flame: Flame | None = None
        self._original: Flame | None = None   # as loaded, so adjustments can be reverted
        self._source_path: Path | None = None
        self._source_index = 0
        self._image_size: tuple[int, int] | None = None   # None = the flame's own size
        self._modified = False
        self._undo: list[tuple[str, Flame]] = []
        self._redo: list[Flame] = []
        self._last_edit: tuple[str, float] = ("", 0.0)

    @property
    def flame(self) -> Flame | None:
        return self._flame

    @property
    def source_path(self) -> Path | None:
        return self._source_path

    @property
    def source_index(self) -> int:
        return self._source_index

    @property
    def image_size(self) -> tuple[int, int]:
        """Output resolution the viewer frames: the chosen one, else the flame's own size."""
        if self._image_size is not None:
            return self._image_size
        if self._flame is not None:
            return (self._flame.camera.width, self._flame.camera.height)
        return (800, 600)

    @property
    def custom_image_size(self) -> tuple[int, int] | None:
        """The explicitly chosen resolution, or None when following the flame."""
        return self._image_size

    def set_image_size(self, size: tuple[int, int] | None) -> None:
        """Choose the output resolution (None = the flame's own size)."""
        size = None if size is None else (max(1, int(size[0])), max(1, int(size[1])))
        if size != self._image_size:
            self._image_size = size
            self.image_size_changed.emit()

    def is_showing(self, path: Path, index: int) -> bool:
        return self._source_path == path and self._source_index == index

    @property
    def modified(self) -> bool:
        """True once the camera / colouring / palette has been edited since loading or saving."""
        return self._modified

    def mark_saved(self) -> None:
        """The current state is now what the file holds."""
        if self._flame is not None:
            self._original = self._flame.copy()
        self._set_modified(False)

    def _set_modified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    # --- undo / redo ------------------------------------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def _record(self, kind: str, sticky: bool = False) -> None:
        """Remember the state before an edit of `kind` (same-kind edits in quick succession share one step;
        with `sticky` they share one step however far apart they are — a mouse drag with pauses)."""
        if self._flame is None:
            return
        now = time.monotonic()
        last_kind, last_time = self._last_edit
        self._last_edit = (kind, now)
        if self._undo and last_kind == kind and (sticky or now - last_time < UNDO_COALESCE_SECONDS):
            return
        self._undo.append((kind, self._flame.copy()))
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self.undo_changed.emit(True, False)

    def undo(self) -> bool:
        """Restore the state before the last edit; False if there is nothing to undo."""
        if not self._undo or self._flame is None:
            return False
        _kind, flame = self._undo.pop()
        self._redo.append(self._flame)
        self._restore(flame)
        return True

    def redo(self) -> bool:
        if not self._redo or self._flame is None:
            return False
        flame = self._redo.pop()
        self._undo.append(("redo", self._flame))
        self._restore(flame)
        return True

    def _restore(self, flame: Flame) -> None:
        self._flame = flame
        self._last_edit = ("", 0.0)
        self._set_modified(True)
        self.undo_changed.emit(self.can_undo, self.can_redo)
        self.flame_restored.emit()

    def paste(self, flame: Flame) -> None:
        """Replace the flame's parameters (transforms, camera, coloring, palette) keeping the file link; undoable."""
        if self._flame is None:
            self.replace(flame)
            return
        self._record("paste")
        self._last_edit = ("", 0.0)
        self._flame = flame.copy()
        self._set_modified(True)
        self.flame_restored.emit()

    def set_source(self, path: Path | None, index: int) -> None:
        """Where the flame now lives (after a save into a file / entry)."""
        self._source_path = path
        self._source_index = index

    @property
    def original(self) -> Flame | None:
        """The flame as it was loaded (before any camera / colouring adjustments)."""
        return self._original

    def replace(self, flame: Flame, source_path: Path | None = None, source_index: int = 0) -> None:
        """Show `flame` (the document keeps its own copy)."""
        self._flame = flame.copy()
        self._original = flame.copy()
        self._source_path = source_path
        self._source_index = source_index
        self._undo.clear()
        self._redo.clear()
        self._last_edit = ("", 0.0)
        self._set_modified(False)
        self.undo_changed.emit(False, False)
        self.flame_replaced.emit()

    def set_view(self, center: tuple[float, float] | None = None, zoom: float | None = None, rotate: float | None = None) -> None:
        """Change the camera of the current flame (no-op without a flame)."""
        if self._flame is None:
            return
        self._record("view")
        camera = self._flame.camera
        if center is not None:
            camera.center = (float(center[0]), float(center[1]))
        if zoom is not None:
            camera.zoom = float(zoom)
        if rotate is not None:
            camera.rotate = float(rotate)
        self._set_modified(True)
        self.camera_changed.emit()

    def pan(self, dx: float, dy: float) -> None:
        """Move the view by a fraction of the image (`dx = 0.1` shows what lies 10% of the width to the right).

        Screen directions: y down, the camera's rotation respected.
        """
        if self._flame is None:
            return
        camera = self._flame.camera
        w, h = camera.width, camera.height
        x0, y0 = camera.unproject(w / 2, h / 2, w, h)
        x1, y1 = camera.unproject(w / 2 + dx * w, h / 2 + dy * h, w, h)
        self.set_view(center=(camera.center[0] + x1 - x0, camera.center[1] + y1 - y0))

    def pan_units(self, dx: float, dy: float) -> None:
        """Move the view by `dx` / `dy` fractal units along the screen axes (y down; rotation respected)."""
        if self._flame is None:
            return
        camera = self._flame.camera
        w, h = camera.width, camera.height
        ppu = camera.pixels_per_unit(w, h)
        x0, y0 = camera.unproject(w / 2, h / 2, w, h)
        x1, y1 = camera.unproject(w / 2 + dx * ppu, h / 2 + dy * ppu, w, h)
        self.set_view(center=(camera.center[0] + x1 - x0, camera.center[1] + y1 - y0))

    def set_camera_3d(self, pitch: float | None = None, yaw: float | None = None, perspective: float | None = None,
                      zpos: float | None = None, dof: float | None = None, pitch_y: float | None = None) -> None:
        """Change the 3D camera (angles in radians; None leaves a value alone). No-op without a flame."""
        if self._flame is None:
            return
        self._record("camera3d")
        camera = self._flame.camera
        for name, value in (("pitch", pitch), ("yaw", yaw), ("perspective", perspective), ("zpos", zpos), ("dof", dof),
                            ("pitch_y", pitch_y)):
            if value is not None:
                setattr(camera, name, float(value))
        self._set_modified(True)
        self.camera_changed.emit()

    def set_coloring(self, brightness: float | None = None, gamma: float | None = None, gamma_threshold: float | None = None,
                     vibrancy: float | None = None, contrast: float | None = None, background=None, curves=None) -> None:
        """Change the tone mapping (None leaves a value alone). No-op without a flame."""
        if self._flame is None:
            return
        given = [n for n, v in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                                ("vibrancy", vibrancy), ("contrast", contrast), ("background", background), ("curves", curves)) if v is not None]
        self._record("coloring:" + ",".join(given))
        coloring = self._flame.coloring
        for name, value in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                            ("vibrancy", vibrancy), ("contrast", contrast)):
            if value is not None:
                setattr(coloring, name, float(value))
        if background is not None:
            coloring.background = tuple(int(c) for c in background)
        if curves is not None:
            coloring.curves = curves.copy()
        self._set_modified(True)
        self.coloring_changed.emit()

    def set_curve(self, channel: str, points) -> None:
        """Replace one tone curve's control points. No-op without a flame."""
        if self._flame is None:
            return
        self._record("curve:" + channel)
        self._flame.coloring.curves.set_points(channel, points)
        self._set_modified(True)
        self.coloring_changed.emit()

    def reset_curves(self, channel: str | None = None) -> None:
        """Put one tone curve (or all of them) back to the identity."""
        if self._flame is None:
            return
        self._record("curves-reset")
        self._flame.coloring.curves.reset(channel)
        self._set_modified(True)
        self.coloring_changed.emit()

    def revert_view(self) -> None:
        """Put the centre / zoom / rotation back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.camera
        self.set_view(center=o.center, zoom=o.zoom, rotate=o.rotate)

    def revert_camera_3d(self) -> None:
        """Put the 3D camera back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.camera
        self.set_camera_3d(o.pitch, o.yaw, o.perspective, o.zpos, o.dof, o.pitch_y)

    def revert_coloring(self) -> None:
        """Put the tone mapping back to the loaded file's values."""
        if self._flame is None or self._original is None:
            return
        o = self._original.coloring
        self.set_coloring(o.brightness, o.gamma, o.gamma_threshold, o.vibrancy, o.contrast, o.background, o.curves)

    def set_gradient(self, gradient: Gradient) -> None:
        """Recolour the current flame from a Gradient (no-op without a flame, or if nothing changes)."""
        if self._flame is None:
            return
        palette = list(gradient.sample(len(self._flame.palette) or 256))
        if palette == self._flame.palette:
            return
        self._record("palette")
        self._flame.palette = palette
        self._set_modified(True)
        self.palette_changed.emit()

    # --- transform editing (the Transform Editor) ----------------------------------------------------------
    def xform(self, index: int | None) -> XForm | None:
        """Transform `index` of the current flame, or the final transform for None; None if there is no such thing."""
        if self._flame is None:
            return None
        if index is None:
            return self._flame.final
        return self._flame.xforms[index] if 0 <= index < len(self._flame.xforms) else None

    def edit_xform(self, index: int | None, kind: str, action: Callable[[XForm], None], what: str = "all",
                   sticky: bool = False) -> bool:
        """Apply `action` to one transform as an undoable edit of `kind` (same-kind edits within a second coalesce,
        so a slider sweep is one undo step; `sticky` ones coalesce regardless of time, so a mouse drag with pauses is
        one step too). `what` is announced with `xform_changed`. Returns False if there is no such transform."""
        xform = self.xform(index)
        if xform is None:
            return False
        self._record(kind, sticky)
        action(xform)
        self._set_modified(True)
        self.xform_changed.emit(index, what)
        return True

    def set_affine(self, index: int | None, which: str, coefs: Affine, kind: str | None = None, sticky: bool = False) -> bool:
        """Replace one of the transform's affines: `which` is `pre`, `coefs` (the normal triangle) or `post`."""
        if which not in ("pre", "coefs", "post"):
            raise ValueError(f"unknown affine {which!r}")
        values = tuple(float(v) for v in coefs)
        return self.edit_xform(index, kind or f"affine:{which}:{index}", lambda x: setattr(x, which, values), "affine", sticky)

    def set_xform_fields(self, index: int | None, **fields) -> bool:
        """Set plain attributes (`weight`, `color`, `color_speed`, `opacity`, `var_color`, `name`)."""
        allowed = {"weight", "color", "color_speed", "opacity", "var_color", "name"}
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unknown transform fields: {sorted(unknown)}")

        def apply(x: XForm) -> None:
            for key, value in fields.items():
                setattr(x, key, str(value) if key == "name" else float(value))
        return self.edit_xform(index, "fields:" + ",".join(sorted(fields)) + f":{index}", apply, "fields")

    def set_variation(self, index: int | None, name: str, weight: float) -> bool:
        """Set a variation's weight (0 removes it; its parameters are kept so they return with it)."""
        def apply(x: XForm) -> None:
            if weight == 0:
                x.variations.pop(name, None)
            else:
                x.variations[name] = float(weight)
        return self.edit_xform(index, f"variation:{name}:{index}", apply, "variations")

    def clear_variations(self, index: int | None) -> bool:
        """Remove every variation of the transform (Apophysis's *Clear*)."""
        return self.edit_xform(index, f"clear-variations:{index}", lambda x: x.variations.clear(), "variations")

    def set_param(self, index: int | None, key: str, value: float) -> bool:
        """Set a variation parameter (full flame-file key such as `julian_power`)."""
        return self.edit_xform(index, f"param:{key}:{index}", lambda x: x.params.__setitem__(key, float(value)), "params")

    def set_chaos(self, index: int, target: int, weight: float) -> bool:
        """Set the xaos weight of going from transform `index` to transform `target`."""
        if self._flame is None or not 0 <= target < len(self._flame.xforms):
            return False
        n = len(self._flame.xforms)

        def apply(x: XForm) -> None:
            row = xform_ops.chaos_row(x, n)
            row[target] = max(0.0, float(weight))
            x.chaos = None if all(v == 1.0 for v in row) else row
        return self.edit_xform(index, f"chaos:{index}:{target}", apply, "chaos")

    def set_all_chaos(self, index: int, weight: float) -> bool:
        """Set every outgoing xaos weight of transform `index` (Apophysis's *Clear all* / *Set all*)."""
        if self._flame is None:
            return False
        n = len(self._flame.xforms)
        value = max(0.0, float(weight))
        return self.edit_xform(index, f"chaos-all:{index}", lambda x: setattr(x, "chaos", None if value == 1.0 else [value] * n), "chaos")

    def _restructure(self, kind: str, action: Callable[[Flame], int | None]) -> int | None:
        """Run a structural edit (transforms added / removed) as its own undo step; returns what the edit returns."""
        if self._flame is None:
            return None
        self._record(kind)
        self._last_edit = ("", 0.0)    # structural edits never coalesce
        result = action(self._flame)
        self._set_modified(True)
        self.transforms_changed.emit()
        return result

    def add_xform(self) -> int | None:
        """Append a new transform; returns its index."""
        return self._restructure("add-xform", xform_ops.add_xform)

    def duplicate_xform(self, index: int) -> int | None:
        """Append a copy of transform `index`; returns the copy's index."""
        return self._restructure("duplicate-xform", lambda f: xform_ops.duplicate_xform(f, index))

    def add_linked_xform(self, index: int) -> int | None:
        """Append a transform linked by xaos to transform `index` (Apophysis's *Add linked*); returns its index."""
        return self._restructure("link-xform", lambda f: xform_ops.add_linked_xform(f, index))

    def delete_xform(self, index: int) -> int | None:
        """Remove a transform (the last one stays); returns the index to select next."""
        if self._flame is None or len(self._flame.xforms) <= 1:
            return None
        return self._restructure("delete-xform", lambda f: xform_ops.delete_xform(f, index))

    def set_final_enabled(self, enabled: bool) -> None:
        """Add an identity final transform or remove the existing one."""
        if self._flame is None or (self._flame.final is not None) == enabled:
            return
        self._restructure("final-xform", lambda f: xform_ops.set_final_enabled(f, enabled))

    def area_weights(self) -> None:
        """Apophysis's auto weights: each transform weighted by its triangle's area."""
        if self._flame is None:
            return
        self._record("area-weights")
        xform_ops.area_weights(self._flame)
        self._set_modified(True)
        for i in range(len(self._flame.xforms)):
            self.xform_changed.emit(i, "fields")

    def replace_flame_parameters(self, flame: Flame, kind: str = "edit") -> None:
        """Replace the whole flame as one undoable edit, keeping the file link (editor operations on everything)."""
        if self._flame is None:
            return
        self._record(kind)
        self._last_edit = ("", 0.0)
        self._flame = flame.copy()
        self._set_modified(True)
        self.flame_restored.emit()
