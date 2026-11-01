"""The Fragments window's preferences — FragM's *Preferences* dialog as one Qt-free record.

Only options the code actually honours are here (FragM's EXR-tool and shader-assembler paths have no counterpart).
`to_dict` / `from_dict` are the persistence contract: the window stores the dict under `fragments/preferences/`
in `QSettings`, the dialog edits a copy, and `FragmentsWindow.apply_preferences` pushes the values into the parts
that use them (the driver's refresh rate and interactive scale, the file watcher, the log, the editors' font,
the build options, the include paths).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field, fields, replace

from .. import config
from .glsl_compat import MODES

DEFAULT_LOG_NAME = "fragments.log"


@dataclass
class FragPreferences:
    """Every preference (groups as in the dialog).

    Attributes:
        max_recent: Entries in *Recent files*.
        loop_play: New fragments start with *Loop play* on.
        draw_paths: Draw the keyframe camera paths over the viewport.
        traveling_wheel: The 2D wheel zooms towards the pointer (*traveling*) rather than the centre.
        log_max_rows: Rows kept in the Log dock.
        font_size: The editors' font size in points (0 = the system's fixed font size).
        jump_to_error: Move the cursor to the first error line after a failed build.
        autoload: Reload a tab when its file changes on disk and the tab has no unsaved edits.
        autorun: Build a fragment as soon as it is opened.
        auto_build: Rebuild after every edit (after a pause).
        move_main: Rename the fragment's `main` and call it from a trailing one (FragM's *moveMain*).
        use_defines: Locked parameters become `#define`s (else `const`).
        compat_mode: The compatibility layer: `modernise`, `patch` or `off`.
        save_easing: Inserted presets carry the easing-curve settings.
        default_fps: Frames per second for fragments without their own animation settings.
        refresh_ms: The viewport aims for one delivered image per this many milliseconds.
        interactive_scale: Render scale while the camera moves (1 = full size).
        gpu_load: The viewport's GPU duty cycle in percent (100 = render flat out, FragM's behaviour; lower values idle
            between passes so the machine stays responsive and cool).
        pause_when_hidden: Stop accumulating while the window is hidden or minimised; resume on show.
        include_paths: Extra folders searched for `#include` files (the bundled folder is always last).
        log_to_file: Mirror the log to a file.
        log_file: That file ("" = `fragments.log` in the cache folder).
        log_file_max_kb: Rotate the file once it passes this size.
        verbose: Log the parameter values after every build (FragM's `--verbose`).
    """
    max_recent: int = 10
    loop_play: bool = False
    draw_paths: bool = True
    traveling_wheel: bool = False
    log_max_rows: int = 2000
    font_size: int = 0
    jump_to_error: bool = True
    autoload: bool = True
    autorun: bool = True
    auto_build: bool = False
    move_main: bool = True
    use_defines: bool = True
    compat_mode: str = "modernise"
    save_easing: bool = True
    default_fps: int = 25
    refresh_ms: int = config.FRAG_REFRESH_MS
    interactive_scale: float = config.FRAG_INTERACTIVE_SCALE
    gpu_load: int = 100
    pause_when_hidden: bool = True
    include_paths: list[str] = field(default_factory=list)
    log_to_file: bool = False
    log_file: str = ""
    log_file_max_kb: int = 1024
    verbose: bool = False

    def copy(self) -> "FragPreferences":
        return replace(self, include_paths=list(self.include_paths))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict | None) -> "FragPreferences":
        """Preferences from a stored dict; unknown keys are ignored, missing ones keep their defaults, values are coerced."""
        prefs = cls()
        if not data:
            return prefs
        for f in fields(cls):
            if f.name in data:
                setattr(prefs, f.name, _coerce(f.name, getattr(prefs, f.name), data[f.name]))
        return prefs.normalised()

    def normalised(self) -> "FragPreferences":
        """Values clamped to what the code accepts."""
        return replace(self, max_recent=max(1, min(50, int(self.max_recent))), log_max_rows=max(50, int(self.log_max_rows)),
                       font_size=max(0, min(48, int(self.font_size))), compat_mode=self.compat_mode if self.compat_mode in MODES else "modernise",
                       default_fps=max(1, min(240, int(self.default_fps))), refresh_ms=max(5, min(2000, int(self.refresh_ms))),
                       interactive_scale=max(0.1, min(1.0, float(self.interactive_scale))), log_file_max_kb=max(16, int(self.log_file_max_kb)),
                       gpu_load=max(5, min(100, int(self.gpu_load))),
                       include_paths=[str(p) for p in self.include_paths if str(p).strip()])


def _coerce(name: str, default, value):
    if isinstance(default, bool):
        return value in (True, "true", "True", 1, "1")
    if isinstance(default, int):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, float):
        try:
            return float(value)
        except (TypeError, ValueError):
            return default
    if isinstance(default, list):
        if isinstance(value, str):
            return [value] if value else []
        return [str(v) for v in (value or [])]
    return str(value) if value is not None else default


__all__ = ["FragPreferences", "DEFAULT_LOG_NAME"]
