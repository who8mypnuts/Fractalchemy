"""One open fragment: its source text, its parameters with an undo history, the last build and the camera.

The editor owns the text (with its own undo stack) and mirrors it here; `build()` preprocesses the text, bakes the
locked parameters in, translates the GLSL and announces the result — compiling happens on the render thread when
the render driver submits the request, and the driver reports back through `set_build_facts()` / `set_build_error()`.
Parameter edits never recompile unless a lock (or a locked value) changed: `needs_build` then lights the Build button,
as in FragM. Every value / lock / camera edit goes through this object, lands in the history (drags coalesce by
`merge_key`) and is announced by a signal the panel, the viewport and the driver listen to.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from ...fragments.animation import AnimationSettings, camera_path, frame_values, keyframe_blend
from ...fragments.grading import Grading
from ...fragments.camera import Camera2D, Camera3D
from ...fragments.document_format import FragmentMetadata
from ...fragments.easing import EasingSetting, parse_all, with_setting, without_slider
from ...fragments.files import FileManager
from ...fragments.glsl_compat import CompatError, CompatOptions, ModernSource, modernise
from ...fragments.gl.job import BuildFacts, FragRequest
from ...fragments.parameters import LockType, locked_substitution
from ...fragments.preprocessor import Preprocessor
from ...fragments.source import CRITICAL, FragmentSource, Message
from ...fragments.state import ParameterState
from ...fragments.textures import texture_specs

UNDO_LIMIT = 200
RE_BARE_UNIFORM = re.compile(r"^\s*uniform\s+(\S+)\s+(\S+)\s*;\s*$")


class BuildOptions:
    """The preferences a build depends on.

    Attributes:
        move_main: Rename the fragment's `main` and call it from a trailing one.
        use_defines: Locked parameters become `#define`s (else `const`).
        compat: The compatibility layer's options (mode and the context's abilities).
        include_paths: Extra include folders (the bundled one is always searched last).
    """

    def __init__(self, move_main: bool = True, use_defines: bool = True, compat: CompatOptions | None = None,
                 include_paths: list[Path] | None = None):
        self.move_main = move_main
        self.use_defines = use_defines
        self.compat = compat or CompatOptions()
        self.include_paths = include_paths or []


class FragDocument(QObject):
    """An open fragment (see the module docstring).

    Signals:
        text_changed(): The source text changed (the editor typed, a preset was inserted, a bound was edited).
        needs_build_changed(bool): Whether the shown program is stale.
        built(object): A `FragmentSource` was produced (the request is ready for the driver).
        build_failed(list): Preprocessing failed or the driver rejected the program: `Message`s / `Diagnostic`s.
        grading_changed(): The display colour grading changed (only the display pass needs to re-run).
        facts_changed(object): `BuildFacts` arrived from the first rendered pass.
        parameters_changed(list, bool, bool): (names, recompile needed, buffer-shader-only change).
        parameters_replaced(): Many values changed at once (preset, reset, undo): the panel refreshes everything.
        camera_changed(bool): The camera parameters changed (True while a drag is in progress).
        path_changed(object): The file (`Path` or None).
        modified_changed(bool): The dirty flag.
        undo_changed(bool, bool): (can undo, can redo).
        message(object): A `Message` for the log.
        easing_changed(): The easing curves changed (added, replaced, removed, or loaded from a preset).
    """
    text_changed = Signal()
    needs_build_changed = Signal(bool)
    built = Signal(object)
    build_failed = Signal(list)
    grading_changed = Signal()
    facts_changed = Signal(object)
    parameters_changed = Signal(list, bool, bool)
    parameters_replaced = Signal()
    camera_changed = Signal(bool)
    path_changed = Signal(object)
    modified_changed = Signal(bool)
    undo_changed = Signal(bool, bool)
    message = Signal(object)
    easing_changed = Signal()

    def __init__(self, text: str = "", path: Path | None = None, parent: QObject | None = None,
                 metadata: FragmentMetadata | None = None):
        super().__init__(parent)
        self._text = text
        self.path = path
        self.metadata = metadata if metadata is not None else FragmentMetadata()   # the .fafrag block (render / animation / library)
        self._modified = False
        self._needs_build = True
        self.build_failed_last = False           # the last build attempt was rejected (preprocessor, translator or driver)
        self.source: FragmentSource | None = None
        self.modern: ModernSource | None = None
        self.buffer_modern: ModernSource | None = None
        self.facts: BuildFacts | None = None
        self.state = ParameterState()
        self.current_preset = ""
        self.step_size: float | None = None          # the camera step, kept per document (None: the camera's default)
        self.easing: list[EasingSetting] = []        # the active easing curves (FragM's `curveSettings`)
        self._include_paths: list[Path] = []
        self.animation = AnimationSettings.from_dict(self.metadata.animation)
        self.grading = Grading.from_dict(self.metadata.grading)
        self.debug_view = ""                      # "" or "depth" (not saved)
        self._undo: list[ParameterState] = []
        self._redo: list[ParameterState] = []
        self._last_merge_key: object = None
        self._default_applied = False

    # --- text and file ------------------------------------------------------------------------------------------------
    @property
    def text(self) -> str:
        return self._text

    def set_text(self, text: str, from_editor: bool = True) -> None:
        """The editor's text changed (marks the document modified and stale)."""
        if text == self._text:
            return
        self._text = text
        self._set_modified(True)
        self.set_needs_build(True)
        if not from_editor:
            self.text_changed.emit()

    @property
    def name(self) -> str:
        return self.path.stem if self.path else "Unnamed"

    @property
    def modified(self) -> bool:
        return self._modified

    def _set_modified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    def mark_modified(self) -> None:
        """Flag unsaved edits (a recovered session's text that never reached its file)."""
        self._set_modified(True)

    def mark_saved(self, path: Path) -> None:
        if path != self.path:
            self.path = path
            self.path_changed.emit(path)
        self._set_modified(False)

    @property
    def needs_build(self) -> bool:
        return self._needs_build

    def set_needs_build(self, needed: bool) -> None:
        if needed != self._needs_build:
            self._needs_build = needed
            self.needs_build_changed.emit(needed)

    # --- building -----------------------------------------------------------------------------------------------------
    def build(self, options: BuildOptions) -> bool:
        """Preprocess + substitute locks + translate; True when a request can now be rendered."""
        self._include_paths = list(options.include_paths)
        files = FileManager(options.include_paths, self.path)
        source = Preprocessor(files, options.move_main).parse(self._text, self.path)
        for msg in source.messages:
            self.message.emit(msg)
        if any(m.level == CRITICAL for m in source.messages) and not source.fragment:
            self._fail([m for m in source.messages if m.level == CRITICAL])
            return False
        self.source = source
        self.state = self.state.rebuilt(source.all_params)
        self._apply_default_preset()
        self._substitute_locks(source, options.use_defines)
        try:
            self.modern = modernise(source, options.compat)
            self.buffer_modern = modernise(source.buffer_shader, options.compat) if source.buffer_shader else None
        except CompatError as exc:
            self._fail([Message(CRITICAL, str(exc), self.path)])
            return False
        self.facts = None
        self.build_failed_last = False
        self.set_needs_build(False)
        self.built.emit(source)
        return True

    def _fail(self, diagnostics: list) -> None:
        self.build_failed_last = True
        self.set_needs_build(True)
        self.build_failed.emit(list(diagnostics))
        self.needs_build_changed.emit(True)      # the label shows *Build failed* even when it was already stale

    def _apply_default_preset(self) -> None:
        """FragM applies the `Default` preset when a fragment is first built."""
        if self._default_applied or self.source is None or "Default" not in self.source.presets:
            return
        self._default_applied = True
        result = self.state.apply_settings(self.source.presets["Default"])
        self.current_preset = "Default"
        for warning in result.warnings:
            self.message.emit(Message("warning", warning, self.path))

    def _substitute_locks(self, source: FragmentSource, use_defines: bool) -> None:
        """FragM's `substituteLockedVariables`: the bare `uniform` of every locked parameter becomes its value."""
        locked = {n: self.state.params[n] for n in self.state.locked_names()}
        if not locked:
            return
        self.message.emit(Message("info", f"{len(locked)} locked variables: {','.join(locked)}"))
        for target in (source, source.buffer_shader):
            if target is None:
                continue
            for i, line in enumerate(target.fragment):
                match = RE_BARE_UNIFORM.match(line)
                if match and match.group(2) in locked:
                    replacement = locked_substitution(locked[match.group(2)], self.state.values[match.group(2)], use_defines)
                    if replacement is not None:
                        target.fragment[i] = replacement

    def request(self) -> FragRequest | None:
        """The render payload for the current values (None before a successful build)."""
        if self.source is None or self.modern is None:
            return None
        return FragRequest(self.modern, self.buffer_modern, dict(self.state.values), self.source.buffer, self.source.clear_on_change,
                           self.source.subframes_between_redraws, self.source.depth_to_alpha,
                           dict(self.source.texture_params.get("backbuffer", {})),
                           texture_specs(self.source, self.state, FileManager(self._include_paths, self.path)),
                           None if self.grading.is_identity else self.grading, self.debug_view)

    def set_debug_view(self, view: str) -> None:
        """*Debug view*: what the display pass shows ("" picture, "depth" the depth buffer)."""
        if view != self.debug_view:
            self.debug_view = view
            self.grading_changed.emit()           # only the display pass needs to re-run

    def set_tab_metadata(self, key: str, value) -> None:
        """One entry of the metadata's `tabs` section (camera bookmarks, the current preset …)."""
        if self.metadata.tabs.get(key) != value:
            self.metadata.tabs[key] = value
            self._set_modified(True)

    def set_grading(self, grading: Grading) -> None:
        """The display colour grading (kept in the metadata; only the display pass re-runs)."""
        if grading != self.grading:
            self.grading = grading
            self.metadata.grading = {} if grading.is_identity else grading.to_dict()
            self._set_modified(True)
            self.grading_changed.emit()

    def set_build_facts(self, facts: BuildFacts) -> None:
        """The driver rendered the first pass: the program's active / unused uniforms are known."""
        self.facts = facts
        self.facts_changed.emit(facts)

    def set_build_error(self, diagnostics: list) -> None:
        """The driver rejected the program."""
        self._fail(diagnostics)

    @property
    def camera_kind(self) -> str:
        return self.source.camera_kind if self.source is not None else "2D"

    # --- history -------------------------------------------------------------------------------------------------------
    def _record(self, merge_key: object = None) -> None:
        if merge_key is not None and merge_key == self._last_merge_key and self._undo:
            return
        self._undo.append(self.state.copy())
        del self._undo[:-UNDO_LIMIT]
        self._redo.clear()
        self._last_merge_key = merge_key
        self.undo_changed.emit(True, False)

    def end_merge(self) -> None:
        """The next edit starts a new undo step (a drag ended)."""
        self._last_merge_key = None

    @property
    def can_undo(self) -> bool:
        return bool(self._undo)

    @property
    def can_redo(self) -> bool:
        return bool(self._redo)

    def undo(self) -> None:
        if self._undo:
            self._redo.append(self.state.copy())
            self._restore(self._undo.pop())

    def redo(self) -> None:
        if self._redo:
            self._undo.append(self.state.copy())
            self._restore(self._redo.pop())

    def _restore(self, state: ParameterState) -> None:
        previous = self.state
        self.state = state
        self._last_merge_key = None
        self._set_modified(True)
        self.undo_changed.emit(self.can_undo, self.can_redo)
        changed = previous.diff(state)
        recompile = any(previous.locks.get(n) != state.locks.get(n) or (state.is_locked(n) and previous.values.get(n) != state.values.get(n))
                        for n in changed)
        self.parameters_replaced.emit()
        self._announce(changed, recompile)

    # --- parameter edits ------------------------------------------------------------------------------------------------
    def set_value(self, name: str, value: Any, merge_key: object = None) -> None:
        """One parameter from a widget (clamped); a drag passes a `merge_key` so it is one undo step."""
        if name not in self.state:
            return
        self._record(merge_key)
        changed, _clamped = self.state.set(name, value)
        if changed:
            self._set_modified(True)
            self._announce([name], self.state.is_locked(name))

    def set_values(self, values: dict[str, Any], merge_key: object = None, interactive: bool = False) -> None:
        """Several parameters at once (the camera): one undo step, one announcement."""
        names = [n for n in values if n in self.state]
        if not names:
            return
        self._record(merge_key)
        changed = [n for n in names if self.state.set(n, values[n])[0]]
        if changed:
            self._set_modified(True)
            recompile = any(self.state.is_locked(n) for n in changed)
            self._announce(changed, recompile, interactive=interactive)

    def set_lock(self, name: str, lock: LockType) -> None:
        if name not in self.state:
            return
        self._record()
        if self.state.set_lock(name, lock):
            self._set_modified(True)
            self._announce([name], recompile=True)

    def set_group_lock(self, group: str, lock: LockType) -> None:
        """Lock / unlock every lockable parameter of a group (FragM's *Lock group* / *Unlock group*)."""
        names = [n for n in self.state.names_in_group(group) if self.state.params[n].lock in (LockType.NOT_LOCKED, LockType.LOCKED)]
        self._record()
        changed = [n for n in names if self.state.set_lock(n, lock)]
        if changed:
            self._set_modified(True)
            self._announce(changed, recompile=True)

    def reset(self, names: list[str] | None = None) -> None:
        """Back to the annotation defaults (`F1` for all, *Reset group* for some)."""
        self._record()
        changed = self.state.reset(names)
        if changed:
            self._set_modified(True)
            self.parameters_replaced.emit()
            self._announce(changed, any(self.state.is_locked(n) for n in changed))

    def apply_settings(self, text: str, label: str = "settings") -> list[str]:
        """Settings text (a preset, the clipboard, a `.fragparams` file); returns the warnings."""
        self._record()
        result = self.state.apply_settings(text)
        for warning in result.warnings:
            self.message.emit(Message("warning", warning, self.path))
        if result.changed:
            self._set_modified(True)
            self.parameters_replaced.emit()
            self._announce(result.changed, result.recompile)
        if result.easing:
            for curve in parse_all(result.easing):
                self.easing = with_setting(self.easing, curve)
            self.easing_changed.emit()
        return result.warnings

    def apply_preset(self, name: str) -> bool:
        """FragM's `setPreset`; False when there is no such preset."""
        if self.source is None or name not in self.source.presets:
            return False
        self.current_preset = name
        self.apply_settings(self.source.presets[name], name)
        return True

    def _announce(self, names: list[str], recompile: bool, interactive: bool = False) -> None:
        if recompile:
            self.set_needs_build(True)
        buffer_only = self._buffer_only(names)
        camera = set(names) & {"Eye", "Target", "Up", "FOV", "Center", "Zoom", "log_Zoom"}
        self.parameters_changed.emit(list(names), recompile, buffer_only)
        if camera:
            self.camera_changed.emit(interactive)

    def _buffer_only(self, names: list[str]) -> bool:
        """True when every changed parameter is used by the buffer shader alone (FragM's `bufferShaderOnly`)."""
        if self.facts is None or not self.facts.buffer_active or not names:
            return False
        return all(n in self.facts.buffer_active and n not in self.facts.active for n in names)

    # --- cameras ------------------------------------------------------------------------------------------------------
    def camera3d(self) -> Camera3D:
        v = self.state.values
        return Camera3D(tuple(v.get("Eye", (0, 0, -10))), tuple(v.get("Target", (0, 0, 0))), tuple(v.get("Up", (0, 1, 0))),
                        float(v.get("FOV", 0.4)))

    def camera2d(self) -> Camera2D:
        v = self.state.values
        zoom_name = "Zoom" if "Zoom" in self.state else "log_Zoom"
        return Camera2D(tuple(v.get("Center", (0.0, 0.0))), float(v.get(zoom_name, 1.0)), bool(v.get("EnableTransform", False)),
                        float(v.get("RotateAngle", 0.0)), float(v.get("StretchAngle", 0.0)), float(v.get("StretchAmount", 0.0)))

    def set_camera3d(self, camera: Camera3D, merge_key: object = "camera", interactive: bool = False) -> None:
        values = {"Eye": camera.eye, "Target": camera.target, "Up": camera.up}
        if "FOV" in self.state and camera.fov != self.state.get("FOV"):
            values["FOV"] = camera.fov
        if self.source is not None and self.source.auto_focus and self.state.get("AutoFocus") and "FocalPlane" in self.state:
            eye, target = camera.eye, camera.target
            values["FocalPlane"] = sum((a - b) ** 2 for a, b in zip(eye, target)) ** 0.5
        self.set_values(values, merge_key, interactive)

    def set_camera2d(self, camera: Camera2D, merge_key: object = "camera", interactive: bool = False) -> None:
        zoom_name = "Zoom" if "Zoom" in self.state else "log_Zoom"
        self.set_values({"Center": camera.center, zoom_name: camera.zoom}, merge_key, interactive)

    # --- animation ------------------------------------------------------------------------------------------------------
    def set_animation(self, settings: AnimationSettings) -> None:
        """The clock (kept in the `.fafrag` metadata)."""
        if settings != self.animation:
            self.animation = settings
            self.metadata.animation = settings.to_dict()
            self._set_modified(True)

    def camera_path(self):
        """The keyframe path at the current length (None before a build)."""
        return camera_path(self.source.presets, self.animation) if self.source is not None else None

    def set_easing(self, curve: EasingSetting) -> None:
        """Add or replace the curve of one slider component (F7)."""
        self.easing = with_setting(self.easing, curve)
        self._set_modified(True)
        self.easing_changed.emit()

    def remove_easing(self, slider: str) -> None:
        if any(c.slider == slider for c in self.easing):
            self.easing = without_slider(self.easing, slider)
            self._set_modified(True)
            self.easing_changed.emit()

    def clear_animation(self) -> None:
        """FragM's *Clear animation actions*: drop every easing curve."""
        if self.easing:
            self.easing = []
            self.easing_changed.emit()

    def easing_lines(self) -> list[str]:
        return [c.format() for c in self.easing]

    def apply_frame(self, frame: int) -> list[str]:
        """Set the camera and the eased parameters for `frame` — outside the undo history; returns what changed."""
        if self.source is None:
            return []
        blend = keyframe_blend(self.source.presets, self.state, self.animation)
        values = frame_values(frame, self.state, self.camera_path(), self.easing, self.source.auto_focus, blend)
        changed = [n for n, v in values.items() if self.state.set(n, v)[0]]
        if changed:
            self._announce(changed, recompile=False, interactive=False)
        return changed

    def has_camera(self) -> bool:
        """Whether the fragment declares the uniforms the camera control needs."""
        wanted = ("Eye", "Target", "Up") if self.camera_kind == "3D" else ("Center",)
        return all(n in self.state for n in wanted) and (self.camera_kind == "3D" or "Zoom" in self.state or "log_Zoom" in self.state)


__all__ = ["FragDocument", "BuildOptions"]
