"""The values of a fragment's parameters — what a preset holds and what the sliders show.

A `ParameterState` is a plain mapping of parameter name → value (plus per-parameter lock and slider types), built
from a `FragmentSource`'s parameter list with the annotation defaults and then changed by presets, settings text,
the sliders and the camera. It is immutable-by-convention: the document copies it into its undo history, so the
methods here return results rather than emitting anything. `apply_settings` is FragM's `VariableEditor::setSettings`
(clamping with a warning, unknown names warned, "requires recompile" when a lock changed); `to_text` is `getSettings`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .parameters import GuiParameter, LockType, SamplerParameter, SliderType, parse_settings, settings_line

CAMERA_3D = ("FOV", "Eye", "Target", "Up")
CAMERA_2D = ("Center", "Zoom")


@dataclass
class ApplyResult:
    """What `apply_settings` did.

    Attributes:
        changed: Names whose value, lock or slider type changed.
        recompile: A lock type changed (the substituted source is stale — FragM's `requiresRecompile`).
        warnings: Clamped values, unknown names, malformed lines.
        easing: Easing-curve lines found in the text (for the animation layer).
    """
    changed: list[str] = field(default_factory=list)
    recompile: bool = False
    warnings: list[str] = field(default_factory=list)
    easing: list[str] = field(default_factory=list)


class ParameterState:
    """Values, locks and slider types of one fragment's parameters (see the module docstring)."""

    def __init__(self, params: list[GuiParameter] | None = None):
        self.params: dict[str, GuiParameter] = {}
        self.values: dict[str, Any] = {}
        self.locks: dict[str, LockType] = {}
        self.sliders: dict[str, SliderType] = {}
        for param in params or []:
            self.add(param)

    # --- construction ---------------------------------------------------------------------------------------------
    def add(self, param: GuiParameter) -> None:
        """Register a parameter at its default (an existing value of the same name is kept)."""
        self.params[param.name] = param
        self.values.setdefault(param.name, param.default)
        self.locks.setdefault(param.name, param.lock)
        self.sliders.setdefault(param.name, param.slider)

    def rebuilt(self, params: list[GuiParameter]) -> "ParameterState":
        """The state for a rebuilt fragment: parameters with the same `unique_name` keep their values, locks and sliders.

        FragM keeps a widget across a rebuild only while its group, name and range are unchanged; a parameter whose
        range changed starts again from its default.
        """
        state = ParameterState()
        old_by_unique = {p.unique_name: p.name for p in self.params.values()}
        for param in params:
            state.params[param.name] = param
            previous = old_by_unique.get(param.unique_name)
            if previous is not None:
                state.values[param.name] = self.values[previous]
                state.locks[param.name] = self.locks[previous]
                state.sliders[param.name] = self.sliders[previous]
            else:
                state.values[param.name] = param.default
                state.locks[param.name] = param.lock
                state.sliders[param.name] = param.slider
        return state

    def copy(self) -> "ParameterState":
        state = ParameterState()
        state.params = dict(self.params)
        state.values = dict(self.values)
        state.locks = dict(self.locks)
        state.sliders = dict(self.sliders)
        return state

    # --- values -------------------------------------------------------------------------------------------------------
    def __contains__(self, name: str) -> bool:
        return name in self.params

    def get(self, name: str, default: Any = None) -> Any:
        return self.values.get(name, default)

    def set(self, name: str, value: Any) -> tuple[bool, bool]:
        """Set `name` (clamped to its range); returns `(changed, clamped)`. Unknown names are ignored (False, False)."""
        param = self.params.get(name)
        if param is None:
            return False, False
        value, clamped = param.clamp(value)
        changed = value != self.values.get(name)
        self.values[name] = value
        return changed, clamped

    def set_lock(self, name: str, lock: LockType) -> bool:
        """Change a lock type; True when it changed (the source must be rebuilt)."""
        if name not in self.params or self.locks.get(name) == lock:
            return False
        self.locks[name] = lock
        return True

    def is_locked(self, name: str) -> bool:
        return self.locks.get(name, LockType.NOT_LOCKED).locked

    def locked_names(self) -> list[str]:
        """Parameters substituted into the source, in declaration order (samplers excluded: they stay uniforms)."""
        return [n for n, p in self.params.items() if self.is_locked(n) and not isinstance(p, SamplerParameter)]

    def reset(self, names: list[str] | None = None) -> list[str]:
        """Back to the annotation defaults (all parameters, or `names`); returns what changed."""
        changed = []
        for name in names if names is not None else list(self.params):
            param = self.params.get(name)
            if param is not None and self.values.get(name) != param.default:
                self.values[name] = param.default
                changed.append(name)
        return changed

    def names_in_group(self, group: str) -> list[str]:
        return [n for n, p in self.params.items() if (p.group or "Default") == group]

    def diff(self, other: "ParameterState") -> list[str]:
        """Names whose value, lock or slider type differs between the two states."""
        names = set(self.params) | set(other.params)
        return sorted(n for n in names if (self.values.get(n), self.locks.get(n), self.sliders.get(n))
                      != (other.values.get(n), other.locks.get(n), other.sliders.get(n)))

    # --- settings text ------------------------------------------------------------------------------------------------
    def to_text(self, provenance: str | None = None, names: list[str] | None = None, extra_lines: list[str] = ()) -> str:
        """FragM's `getSettings`: an optional two-line provenance header, one `name = value…` line per parameter.

        Args:
            provenance: The fragment file name for the `// Generated by:` header (None: no header, as for presets).
            names: A subset (a group); every parameter by default.
            extra_lines: Appended verbatim (easing-curve settings when the preference says so).
        """
        lines = []
        if provenance is not None:
            lines += [f"// Generated by: {provenance}", f"// Created on: {datetime.now().strftime('%a %b %d %H:%M:%S %Y')}"]
        for name in names if names is not None else list(self.params):
            param = self.params[name]
            lines.append(settings_line(param, self.values[name], self.locks[name], self.sliders[name]))
        lines += list(extra_lines)
        return "\n".join(lines)

    def camera_text(self, camera: str) -> str:
        """The camera lines of the settings text (`FOV`, `Eye`, `Target`, `Up` for 3D; `Center`, `Zoom` for 2D)."""
        wanted = CAMERA_3D if camera == "3D" else CAMERA_2D
        return self.to_text(names=[n for n in wanted if n in self.params])

    def apply_settings(self, text: str) -> ApplyResult:
        """FragM's `setSettings`: assign every `name = value` line; clamp with a warning; report unknown names."""
        parsed = parse_settings(text)
        result = ApplyResult(warnings=list(parsed.warnings), easing=list(parsed.easing))
        for line in parsed.lines:
            param = self.params.get(line.name)
            if param is None:
                result.warnings.append(f"Could not find: {line.name}")
                continue
            if line.lock is not None and self.set_lock(line.name, line.lock):
                result.recompile = True
                result.changed.append(line.name)
            if self.sliders.get(line.name) != line.slider:
                self.sliders[line.name] = line.slider
                result.changed.append(line.name)
            try:
                value = param.parse(line.value_text)
            except (ValueError, TypeError):
                result.warnings.append(f"Could not parse the value of {line.name}: {line.value_text}")
                continue
            changed, clamped = self.set(line.name, value)
            if clamped:
                result.warnings.append(f"Value from preset clamped: {line.name} = {line.value_text}")
            if changed:
                result.changed.append(line.name)
                if self.is_locked(line.name):
                    result.recompile = True        # a locked value is part of the source
        result.changed = list(dict.fromkeys(result.changed))
        return result


__all__ = ["ParameterState", "ApplyResult", "CAMERA_2D", "CAMERA_3D"]
