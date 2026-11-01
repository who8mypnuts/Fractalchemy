"""The Fragments window's animation coordination: the clock's events, the easing dialog, the timeline, the loop and
interpolation options.

A helper of `FragmentsWindow` (it holds the window as `w`) so the window stays a thin coordinator: the time toolbar
reports frames / modes / play state here, the document applies the frame (camera path, easing curves, the *All
parameters* blend), the driver restarts the accumulation, and the timeline window mirrors it all.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtWidgets import QDialog

from ...fragments.animation import curves_past_the_end
from .animation_controls import ANIMATION, PROGRESSIVE
from .document import FragDocument
from .easing_dialog import EasingDialog
from .timeline_window import TimelineWindow

if TYPE_CHECKING:
    from .window import FragmentsWindow


class AnimationCoordinator:
    """What happens when the animation clock, the easing dialog or the timeline act (see the module docstring).

    Args:
        window: The Fragments window.
    """

    def __init__(self, window: "FragmentsWindow"):
        self.w = window
        self._timeline: TimelineWindow | None = None

    def connect(self) -> None:
        """Wire the time toolbar and the viewport's play toggle."""
        anim = self.w.anim
        anim.frame_changed.connect(self._on_frame)
        anim.mode_changed.connect(self._on_mode)
        anim.playing_changed.connect(self._on_playing)
        anim.settings_changed.connect(self._on_animation_settings)
        anim.slider.customContextMenuRequested.connect(lambda _pos: self.show_timeline())
        self.w.viewport.play_toggle_requested.connect(anim.toggle_play)

    def _on_frame(self, frame: int) -> None:
        """The playhead moved: the camera path and the easing curves set their values, `time` follows, the accumulation restarts."""
        document = self.w.tabs.document
        self.w.driver.set_time(self.w.anim.time(), render=False)
        if document is None or document.source is None:
            return
        late = curves_past_the_end(document.easing, document.animation)
        if late and self.w.anim.playing:
            self.w.anim.stop()
            self.w.log.add("warning", f"Easing curve end frame {late[0].end_frame} is greater than the animation's {document.animation.frames} frames: "
                                    f"select {late[0].slider} and press F7, or make the animation longer")
        document.apply_frame(frame)
        self.w.driver.render(clear=True)
        if self._timeline is not None:
            self._timeline.set_frame(frame)

    def _on_mode(self, mode: str) -> None:
        self.w.message("Animation mode: time runs while playing" if mode == ANIMATION else "Progressive mode: one still frame accumulates")
        if mode == PROGRESSIVE:
            self.w.driver.render(clear=True)

    def _on_playing(self, playing: bool) -> None:
        if self.w.anim.mode == PROGRESSIVE:
            if playing:
                self.w.driver.render(clear=False)          # keep accumulating
            else:
                self.w.driver.cancel()

    def _on_animation_settings(self, settings) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.set_animation(settings)
            self.refresh(document)

    def refresh(self, document: FragDocument | None) -> None:
        """Keyframes, curves or the clock changed: the slider ticks, the viewport overlay and the timeline follow."""
        path = document.camera_path() if document is not None and document.source is not None else None
        self.w.anim.set_keyframe_ticks(len(path.keyframes) if path is not None else 0)
        self.w.viewport.set_path(path)
        if self._timeline is not None and document is not None:
            self._timeline.show_animation(path.keyframes if path else [], document.easing, document.animation, self.w.anim.frame, document.current_preset)

    def add_easing_curve(self, slider: str | None = None) -> None:
        """F7: the easing dialog for the last edited slider (or `slider`)."""
        document = self.w.tabs.document
        if document is None or document.source is None:
            return
        dialog = EasingDialog(document.state, document.animation, document.easing, slider or self.w.parameters.last_edited_slider, self.w)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        if dialog.discarded:
            document.remove_easing(dialog.slider)
            self.w.log.add("warning", f"Easing curve of {dialog.slider} removed")
        elif dialog.result_setting is not None:
            document.set_easing(dialog.result_setting)
            self.w.log.add("info", dialog.result_setting.format())
            self.w.log.add("warning", 'Insert a "Range-nnnn-nnnn" preset (F8) to keep this setting in the fragment')
            document.apply_frame(self.w.anim.frame)

    def show_timeline(self) -> None:
        if self._timeline is None:
            self._timeline = TimelineWindow(self.w)
            self._timeline.frame_scrubbed.connect(self.w.anim.set_frame)
            self._timeline.keyframe_chosen.connect(self._on_timeline_keyframe)
            self._timeline.edit_curve.connect(self.add_easing_curve)
            self._timeline.remove_curve.connect(self._remove_curve)
        self.refresh(self.w.tabs.document)
        self._timeline.show()
        self._timeline.raise_()

    def _on_timeline_keyframe(self, name: str) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.apply_preset(name)
            self.w.parameters.rebuild()

    def _remove_curve(self, slider: str) -> None:
        if self.w.tabs.document is not None:
            self.w.tabs.document.remove_easing(slider)

    def clear_animation(self) -> None:
        if self.w.tabs.document is not None:
            self.w.tabs.document.clear_animation()
            self.w.message("Easing curves cleared")

    def set_loop_play(self, on: bool) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.set_animation(document.animation.with_(loop_play=on))
            self.w.anim.apply_settings(document.animation)

    def set_loop_path(self, on: bool) -> None:
        document = self.w.tabs.document
        if document is not None:
            document.set_animation(document.animation.with_(loop_path=on))
            self.refresh(document)
            document.apply_frame(self.w.anim.frame)

    def set_interpolation(self, mode: str) -> None:
        """*Interpolation*: `camera` (FragM) or `all` (every numeric parameter blended between keyframe presets)."""
        document = self.w.tabs.document
        if document is not None and document.animation.interpolation != mode:
            document.set_animation(document.animation.with_(interpolation=mode))
            document.apply_frame(self.w.anim.frame)

    def set_draw_paths(self, on: bool) -> None:
        self.w.prefs.draw_paths = on
        self.w.viewport.draw_paths = on
        self.w.viewport.update()

    def set_save_easing(self, on: bool) -> None:
        self.w.prefs.save_easing = on



__all__ = ["AnimationCoordinator"]
