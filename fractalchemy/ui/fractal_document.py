"""The flame currently shown in the main window, plus where it came from, and its undo history.

Every change goes through this object and is announced twice: by a specific signal (`camera_changed`,
`coloring_changed`, `xform_changed`, …) for the widgets that show that part, and then by `edited(kind)` — one
announcement per change, carrying the *kind* of edit — for listeners that care about any change (the Script Editor's
recorder and live parameters, the crash-recovery keeper).

Undo history: each step remembers the flame before the edit, its kind (edits of the same kind in quick succession
coalesce into one step — a slider drag) and a readable label (`undo_labels.undo_label`). Edits that change nothing
record nothing. `modified` is derived from the history: the document remembers the depth at which the flame was
loaded or saved, so undoing back to that state clears the `*` and redoing sets it again. `history()` / `jump_to()` give
the Inspector's *History* tab random access.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

from typing import Callable

from PySide6.QtCore import QObject, Signal

from ..fractal import xform_ops
from ..fractal.scene import Affine, Flame, XForm
from ..model import Gradient
from .undo_labels import undo_label

UNDO_COALESCE_SECONDS = 1.0   # edits of the same kind within this window (slider drags) are one undo step
UNDO_LIMIT = 200


@dataclass
class Step:
    """One undo (or redo) step.

    Attributes:
        kind: The edit's kind (coalescing key; see `undo_labels`).
        label: What the History tab and the Undo / Redo actions call it.
        flame: On the undo stack the state *before* the edit; on the redo stack the state *after* it.
        time: When the edit was made (`time.time()`).
    """
    kind: str
    label: str
    flame: Flame
    time: float


@dataclass(frozen=True)
class HistoryEntry:
    """One row of the History tab: position 0 is the state as loaded, position n the state after step n."""
    label: str
    time: float
    position: int


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
        edited(str): Emitted once after every change of the flame (after the specific signal above), with the kind of
            edit: the undo kinds (`view`, `coloring:gamma`, `palette`, `script`, …), `undo` / `redo`, or `load`.
        about_to_replace(): A different flame is about to be shown while the current one has unsaved edits (the
            crash-recovery keeper puts them on the shelf before they go).
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
    edited = Signal(str)
    about_to_replace = Signal()

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._flame: Flame | None = None
        self._original: Flame | None = None   # as loaded, so adjustments can be reverted
        self._source_path: Path | None = None
        self._source_index = 0
        self._image_size: tuple[int, int] | None = None   # None = the flame's own size
        self._modified = False
        self._undo: list[Step] = []
        self._redo: list[Step] = []
        self._saved_depth: int | None = 0      # undo depth of the loaded / saved state (None: no longer reachable)
        self._origin_label = ""                # what position 0 of the history is ("Opened candy.flame #3")
        self._origin_time = 0.0
        self._last_edit: tuple[str, float] = ("", 0.0)
        self._last_kind = ""
        self._script_run: object = None   # the run whose undo step is already recorded (see apply_script)
        self._live_edit = False
        self._pending_hint: dict | None = None
        self._last_hint: dict | None = None

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
        """True while the flame differs from what was loaded or last saved (undoing back to that state clears it)."""
        return self._modified

    @property
    def last_edit_kind(self) -> str:
        """The kind of the most recent change (as announced by `edited`)."""
        return self._last_kind

    @property
    def live_edit(self) -> bool:
        """True while the signals of an *interactive* script result are being emitted (a live parameter tick): the
        viewport renders those at interactive resolution."""
        return self._live_edit

    def mark_saved(self) -> None:
        """The current state is now what the file holds."""
        if self._flame is not None:
            self._original = self._flame.copy()
        self._saved_depth = len(self._undo)
        self._last_edit = ("", 0.0)          # the next edit starts a new step, so undo can return to this state
        self._refresh_modified()

    def rename(self, name: str) -> None:
        """Give the flame the name it was saved under (not an undoable edit)."""
        if self._flame is not None and self._flame.name != name:
            self._flame.name = name
            self.flame_renamed.emit()

    def _refresh_modified(self) -> None:
        modified = self._flame is not None and self._saved_depth != len(self._undo)
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    def _announce(self, kind: str) -> None:
        self._last_kind = kind
        self._last_hint, self._pending_hint = self._pending_hint, None
        self.edited.emit(kind)

    @property
    def last_edit_hint(self) -> dict | None:
        """What the most recent change was beyond its kind (the Gradient Library's operation or slider values), if known."""
        return self._last_hint

    def _changed(self, kind: str, *signals) -> None:
        """After an edit: update `modified`, emit the specific signals, then `edited(kind)`."""
        self._refresh_modified()
        for signal in signals:
            signal.emit()
        self._announce(kind)

    # --- undo / redo ------------------------------------------------------------------------------------
    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    @property
    def undo_label(self) -> str:
        """The label of the step Undo would take back ("" when there is none)."""
        return self._undo[-1].label if self._undo else ""

    @property
    def redo_label(self) -> str:
        return self._redo[-1].label if self._redo else ""

    def _record(self, kind: str, sticky: bool = False, label: str | None = None) -> None:
        """Remember the state before an edit of `kind` (same-kind edits in quick succession share one step;
        with `sticky` they share one step however far apart they are — a mouse drag with pauses)."""
        if self._flame is None:
            return
        if kind != "script":
            self._script_run = None     # a later result of an earlier run must record its own step
        now = time.monotonic()
        last_kind, last_time = self._last_edit
        self._last_edit = (kind, now)
        if self._undo and last_kind == kind and (sticky or now - last_time < UNDO_COALESCE_SECONDS):
            return
        if self._saved_depth is not None and self._saved_depth > len(self._undo):
            self._saved_depth = None    # the saved state was in the redo tail, which this edit discards
        self._undo.append(Step(kind, label or undo_label(kind), self._flame.copy(), time.time()))
        trimmed = len(self._undo) - UNDO_LIMIT
        if trimmed > 0:
            del self._undo[:trimmed]
            self._origin_label = "Earlier edits"
            if self._saved_depth is not None:
                self._saved_depth = self._saved_depth - trimmed if self._saved_depth >= trimmed else None
        self._redo.clear()
        self.undo_changed.emit(True, False)

    def undo(self) -> bool:
        """Restore the state before the last edit; False if there is nothing to undo."""
        if not self._undo or self._flame is None:
            return False
        self._undo_one()
        self._after_restore("undo")
        return True

    def redo(self) -> bool:
        if not self._redo or self._flame is None:
            return False
        self._redo_one()
        self._after_restore("redo")
        return True

    def _undo_one(self) -> None:
        step = self._undo.pop()
        self._redo.append(Step(step.kind, step.label, self._flame, step.time))
        self._flame = step.flame

    def _redo_one(self) -> None:
        step = self._redo.pop()
        self._undo.append(Step(step.kind, step.label, self._flame, step.time))
        self._flame = step.flame

    def _after_restore(self, kind: str) -> None:
        self._last_edit = ("", 0.0)
        self._script_run = None
        self._refresh_modified()
        self.undo_changed.emit(self.can_undo, self.can_redo)
        self.flame_restored.emit()
        self._announce(kind)

    # --- history ------------------------------------------------------------------------------------------
    @property
    def history_position(self) -> int:
        """Where the current state sits in `history()` (0 = as loaded)."""
        return len(self._undo)

    @property
    def saved_position(self) -> int | None:
        """The history position of the loaded / saved state, or None when it can no longer be reached."""
        return self._saved_depth

    def history(self) -> list[HistoryEntry]:
        """Every state Undo / Redo can reach: the loaded state, the steps done, then the steps undone (oldest first)."""
        if self._flame is None:
            return []
        entries = [HistoryEntry(self._origin_label or "Start", self._origin_time, 0)]
        entries += [HistoryEntry(step.label, step.time, i + 1) for i, step in enumerate(self._undo)]
        done = len(self._undo)
        entries += [HistoryEntry(step.label, step.time, done + i + 1) for i, step in enumerate(reversed(self._redo))]
        return entries

    def state_at(self, position: int) -> Flame | None:
        """The flame at history `position` (a copy; None when there is no such position)."""
        if self._flame is None:
            return None
        done = len(self._undo)
        if position == done:
            return self._flame.copy()
        if 0 <= position < done:
            return self._undo[position].flame.copy()
        k = position - done
        return self._redo[-k].flame.copy() if 1 <= k <= len(self._redo) else None

    def jump_to(self, position: int) -> bool:
        """Undo or redo as many steps as it takes to reach history `position`, announcing the result once."""
        if self._flame is None:
            return False
        position = max(0, min(int(position), len(self._undo) + len(self._redo)))
        here = len(self._undo)
        if position == here:
            return False
        while len(self._undo) > position:
            self._undo_one()
        while len(self._undo) < position:
            self._redo_one()
        self._after_restore("undo" if position < here else "redo")
        return True

    def paste(self, flame: Flame) -> None:
        """Replace the flame's parameters (transforms, camera, coloring, palette) keeping the file link; undoable."""
        if self._flame is None:
            self.replace(flame)
            return
        if flame == self._flame:
            return
        self._record("paste")
        self._last_edit = ("", 0.0)
        self._flame = flame.copy()
        self._changed("paste", self.flame_restored)

    def apply_script(self, flame: Flame, run: object = None, label: str | None = None, interactive: bool = False) -> None:
        """Take over a script's result (transforms, camera, colouring, palette), keeping the file link.

        One undo step per script run: `run` identifies the run, so the intermediate `update()` calls of a
        running script and its final result share the step recorded at its first call (unless another edit came in
        between). `label` names the step ("Script: Random rotate"). `interactive` marks a live parameter tick: the
        viewport renders it at interactive resolution (`live_edit`). Without a flame loaded the result simply becomes
        the document's flame (no file). A result equal to the current flame changes nothing.
        """
        if self._flame is None:
            self.replace(flame)
            self._saved_depth = None
            self._refresh_modified()
            return
        if flame == self._flame:
            return
        if run is None or run is not self._script_run:
            self._record("script", label=label)
            self._last_edit = ("", 0.0)
            self._script_run = run
        self._flame = flame.copy()
        self._live_edit = bool(interactive)
        try:
            self._changed("script", self.flame_restored)
        finally:
            self._live_edit = False

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
        if self._flame is not None and self._modified:
            self.about_to_replace.emit()
        self._flame = flame.copy()
        self._original = flame.copy()
        self._source_path = source_path
        self._source_index = source_index
        self._undo.clear()
        self._redo.clear()
        self._saved_depth = 0
        self._origin_label = f"Opened {source_path.name} #{source_index + 1}" if source_path is not None else f"Showed {flame.name}"
        self._origin_time = time.time()
        self._last_edit = ("", 0.0)
        self._script_run = None
        self._refresh_modified()
        self.undo_changed.emit(False, False)
        self.flame_replaced.emit()
        self._announce("load")

    def restore_unsaved(self, flame: Flame, source_path: Path | None = None, source_index: int = 0, label: str = "") -> None:
        """Show a recovered flame that was never saved (crash recovery, the unsaved-edits shelf): like `replace`, but
        the flame counts as modified, so the title shows `*` and *Save* writes it back to `source_path` / entry."""
        self.replace(flame, source_path, source_index)
        if label:
            self._origin_label = label
        self._saved_depth = None
        self._refresh_modified()

    def set_view(self, center: tuple[float, float] | None = None, zoom: float | None = None, rotate: float | None = None) -> None:
        """Change the camera of the current flame (no-op without a flame)."""
        if self._flame is None:
            return
        camera = self._flame.camera
        new_center = camera.center if center is None else (float(center[0]), float(center[1]))
        new_zoom = camera.zoom if zoom is None else float(zoom)
        new_rotate = camera.rotate if rotate is None else float(rotate)
        if (tuple(new_center), new_zoom, new_rotate) == (tuple(camera.center), camera.zoom, camera.rotate):
            return
        self._record("view")
        camera.center, camera.zoom, camera.rotate = new_center, new_zoom, new_rotate
        self._changed("view", self.camera_changed)

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
        camera = self._flame.camera
        given = {name: float(value) for name, value in (("pitch", pitch), ("yaw", yaw), ("perspective", perspective),
                                                        ("zpos", zpos), ("dof", dof), ("pitch_y", pitch_y)) if value is not None}
        if all(getattr(camera, name) == value for name, value in given.items()):
            return
        self._record("camera3d")
        for name, value in given.items():
            setattr(camera, name, value)
        self._changed("camera3d", self.camera_changed)

    def set_coloring(self, brightness: float | None = None, gamma: float | None = None, gamma_threshold: float | None = None,
                     vibrancy: float | None = None, contrast: float | None = None, background=None, curves=None) -> None:
        """Change the tone mapping (None leaves a value alone). No-op without a flame."""
        if self._flame is None:
            return
        given = [n for n, v in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                                ("vibrancy", vibrancy), ("contrast", contrast), ("background", background), ("curves", curves)) if v is not None]
        coloring = self._flame.coloring
        probe = coloring.copy()
        for name, value in (("brightness", brightness), ("gamma", gamma), ("gamma_threshold", gamma_threshold),
                            ("vibrancy", vibrancy), ("contrast", contrast)):
            if value is not None:
                setattr(probe, name, float(value))
        if background is not None:
            probe.background = tuple(int(c) for c in background)
        if curves is not None:
            probe.curves = curves.copy()
        if probe == coloring:
            return
        kind = "coloring:" + ",".join(given)
        self._record(kind)
        for name in ("brightness", "gamma", "gamma_threshold", "vibrancy", "contrast", "background", "curves"):
            setattr(coloring, name, getattr(probe, name))     # in place: the Coloring object keeps its identity
        self._changed(kind, self.coloring_changed)

    def set_curve(self, channel: str, points) -> None:
        """Replace one tone curve's control points. No-op without a flame."""
        if self._flame is None:
            return
        probe = self._flame.coloring.curves.copy()
        probe.set_points(channel, points)
        if probe == self._flame.coloring.curves:
            return
        self._record("curve:" + channel)
        self._flame.coloring.curves.set_points(channel, points)
        self._changed("curve:" + channel, self.coloring_changed)

    def reset_curves(self, channel: str | None = None) -> None:
        """Put one tone curve (or all of them) back to the identity."""
        if self._flame is None or self._flame.coloring.curves.is_default(channel):
            return
        self._record("curves-reset")
        self._flame.coloring.curves.reset(channel)
        self._changed("curves-reset", self.coloring_changed)

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

    def set_gradient(self, gradient: Gradient, hint: dict | None = None) -> None:
        """Recolour the current flame from a Gradient (no-op without a flame, or if nothing changes). `hint` says what the
        Gradient Library did (`last_edit_hint`: the recorder's relative style uses it)."""
        if self._flame is None:
            return
        palette = list(gradient.sample(len(self._flame.palette) or 256))
        if palette == self._flame.palette:
            return
        self._record("palette")
        self._flame.palette = palette
        self._pending_hint = hint
        self._changed("palette", self.palette_changed)

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
        probe = xform.copy()
        action(probe)
        if probe == xform:
            return True                     # nothing changes: no undo step, no announcement
        self._record(kind, sticky)
        action(xform)
        self._refresh_modified()
        self.xform_changed.emit(index, what)
        self._announce(kind)
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
        self._changed(kind, self.transforms_changed)
        return result

    def add_xform(self, xform: XForm | None = None) -> int | None:
        """Append a new transform (Apophysis's reference triangle, or a prepared one); returns its index."""
        return self._restructure("add-xform", lambda f: xform_ops.add_xform(f, xform))

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
        probe = self._flame.copy()
        xform_ops.area_weights(probe)
        if probe.xforms == self._flame.xforms:
            return
        self._record("area-weights")
        xform_ops.area_weights(self._flame)
        self._refresh_modified()
        for i in range(len(self._flame.xforms)):
            self.xform_changed.emit(i, "fields")
        self._announce("area-weights")

    def replace_flame_parameters(self, flame: Flame, kind: str = "edit") -> None:
        """Replace the whole flame as one undoable edit, keeping the file link (editor operations on everything)."""
        if self._flame is None or flame == self._flame:
            return
        self._record(kind)
        self._last_edit = ("", 0.0)
        self._flame = flame.copy()
        self._changed(kind, self.flame_restored)
