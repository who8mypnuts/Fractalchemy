"""The animation being edited in the Animation window: the `Animation`, its file, the current frame and selection.

Every change is announced so the timeline, the keyframe list, the preview and the title follow. The
document never touches the main window's fractal itself — the window does that when a keyframe is
chosen — so the rest of the application keeps working exactly as before.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, Signal

from ..animation.format import load_animation, save_animation
from ..animation.model import Animation, Keyframe
from ..fractal.scene import Flame


class AnimationDocument(QObject):
    """Holds the current Animation and where it came from.

    Signals:
        animation_replaced(): A different animation was loaded / created.
        keyframes_changed(): Keyframes were added, removed, moved or replaced.
        settings_changed(): fps / length / interpolation / easing / loop / name changed.
        frame_changed(int): The current frame moved.
        selection_changed(object): The selected keyframe (a Keyframe or None).
        modified_changed(bool): Whether the animation differs from what was loaded / last saved.
    """
    animation_replaced = Signal()
    keyframes_changed = Signal()
    settings_changed = Signal()
    frame_changed = Signal(int)
    selection_changed = Signal(object)
    modified_changed = Signal(bool)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._animation = Animation()
        self._path: Path | None = None
        self._modified = False
        self._frame = 0
        self._selected: Keyframe | None = None

    # --- state ------------------------------------------------------------------------------------------------
    @property
    def animation(self) -> Animation:
        return self._animation

    @property
    def path(self) -> Path | None:
        return self._path

    @property
    def modified(self) -> bool:
        return self._modified

    @property
    def frame(self) -> int:
        return self._frame

    @property
    def selected(self) -> Keyframe | None:
        return self._selected

    @property
    def title(self) -> str:
        return self._path.stem if self._path is not None else self._animation.name

    def _set_modified(self, modified: bool) -> None:
        if modified != self._modified:
            self._modified = modified
            self.modified_changed.emit(modified)

    def _touch(self) -> None:
        self._set_modified(True)

    def mark_saved(self) -> None:
        """Treat the current state as saved (no prompt about unsaved changes)."""
        self._set_modified(False)

    # --- files ------------------------------------------------------------------------------------------------
    def new(self, animation: Animation | None = None) -> None:
        """Start a fresh animation (or show `animation`, unsaved)."""
        self._animation = animation if animation is not None else Animation()
        self._path = None
        self._frame = 0
        self._selected = self._animation.keyframes[0] if self._animation.keyframes else None
        self._set_modified(False)
        self.animation_replaced.emit()
        self.selection_changed.emit(self._selected)
        self.frame_changed.emit(self._frame)

    def load(self, path: Path) -> Animation:
        """Read a `.faanim` file and show it (the first keyframe selected)."""
        animation = load_animation(path)
        self._animation = animation
        self._path = Path(path)
        self._frame = animation.keyframes[0].frame if animation.keyframes else 0
        self._selected = animation.keyframes[0] if animation.keyframes else None
        self._set_modified(False)
        self.animation_replaced.emit()
        self.selection_changed.emit(self._selected)
        self.frame_changed.emit(self._frame)
        return animation

    def save(self, path: Path | None = None) -> Path:
        """Write the animation to `path` (or its own file); returns the path written."""
        target = Path(path) if path is not None else self._path
        if target is None:
            raise ValueError("the animation has no file yet")
        written = save_animation(self._animation, target)
        self._path = written
        self._set_modified(False)
        self.settings_changed.emit()
        return written

    # --- frame / selection ------------------------------------------------------------------------------------
    def set_frame(self, frame: int) -> None:
        frame = max(0, min(self._animation.last_frame, int(frame)))
        if frame != self._frame:
            self._frame = frame
            self.frame_changed.emit(frame)

    def select(self, keyframe: Keyframe | None) -> None:
        if keyframe is not None and keyframe not in self._animation.keyframes:
            keyframe = None
        if keyframe is not self._selected:
            self._selected = keyframe
            self.selection_changed.emit(keyframe)

    # --- keyframes --------------------------------------------------------------------------------------------
    def capture(self, flame: Flame, frame: int | None = None, name: str = "") -> Keyframe:
        """Pin `flame` at `frame` (the current frame by default), replacing a keyframe already there."""
        keyframe = self._animation.set_keyframe(self._frame if frame is None else frame, flame, name or flame.name)
        self._touch()
        self.keyframes_changed.emit()
        self.settings_changed.emit()      # the length may have grown
        self.select(keyframe)
        return keyframe

    def update_keyframe(self, keyframe: Keyframe, flame: Flame) -> None:
        """Replace a keyframe's flame."""
        if keyframe in self._animation.keyframes:
            keyframe.flame = flame.copy()
            self._touch()
            self.keyframes_changed.emit()

    def remove_keyframe(self, keyframe: Keyframe) -> None:
        if keyframe not in self._animation.keyframes:
            return
        index = self._animation.keyframes.index(keyframe)
        self._animation.remove_keyframe(keyframe)
        self._touch()
        self.keyframes_changed.emit()
        keys = self._animation.keyframes
        self.select(keys[min(index, len(keys) - 1)] if keys else None)

    def move_keyframe(self, keyframe: Keyframe, frame: int) -> int:
        """Move a keyframe in time (kept between its neighbours); returns the frame it got."""
        if keyframe not in self._animation.keyframes:
            return keyframe.frame
        got = self._animation.move_keyframe(keyframe, frame)
        self._touch()
        self.keyframes_changed.emit()
        self.settings_changed.emit()
        return got

    def rename_keyframe(self, keyframe: Keyframe, name: str) -> None:
        if keyframe in self._animation.keyframes and keyframe.name != name:
            keyframe.name = name
            self._touch()
            self.keyframes_changed.emit()

    # --- settings ---------------------------------------------------------------------------------------------
    def set_settings(self, **fields) -> None:
        """Change `name`, `fps`, `total_frames`, `interpolation`, `easing`, `loop` (given ones only)."""
        changed = False
        anim = self._animation
        for key, value in fields.items():
            if key == "total_frames":
                before = anim.total_frames
                anim.set_total_frames(int(value))
                changed |= anim.total_frames != before
            elif key in ("name", "fps", "interpolation", "easing", "loop"):
                if getattr(anim, key) != value:
                    setattr(anim, key, value)
                    changed = True
            else:
                raise ValueError(f"unknown animation setting {key!r}")
        if changed:
            self._touch()
            self.settings_changed.emit()
            if self._frame > anim.last_frame:
                self.set_frame(anim.last_frame)

    def set_render_settings(self, data: dict) -> None:
        """Keep the render settings with the animation (saved in the file; does not count as an edit)."""
        if data != self._animation.render:
            self._animation.render = dict(data)

    # --- frames -----------------------------------------------------------------------------------------------
    def flame_at(self, frame: int | None = None) -> Flame | None:
        """The interpolated flame at `frame` (the current frame by default)."""
        return self._animation.flame_at(self._frame if frame is None else frame)


__all__ = ["AnimationDocument"]
