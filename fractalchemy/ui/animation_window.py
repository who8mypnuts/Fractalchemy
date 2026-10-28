"""The Animation window: keyframes of the main window's fractal on a timeline, played back and rendered.

Opened from *Windows ▸ Animation* (`F9`) or the toolbar; a tool window like the others (closing hides it).

* **Capture keyframe** pins whatever the main window shows at the playhead's frame; **Update keyframe**
  replaces the selected keyframe's fractal with it; **Delete keyframe** removes it.
* Clicking a keyframe (in the list or on the timeline) does what choosing another fractal does: the
  main window shows it — so it can be adjusted there, in the Transform Editor or the Gradient Library,
  and captured again.
* The **timeline** scrubs the playhead; the small **preview** shows the interpolated fractal at the
  playhead, and **Play** runs through the animation in it (`Playback`).
* **Render Animation…** opens the batch renderer (`AnimationRenderWindow`).
* Files are `.faanim` (JSON); *Open* shows the first keyframe in the main window.

The settings and keyframe panels are `animation_panels`; the document is `AnimationDocument`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QFileDialog, QHBoxLayout, QLabel, QMainWindow, QMessageBox, QPushButton, QSpinBox, QStatusBar, QToolBar, QVBoxLayout, QWidget

from ..animation.format import EXTENSION, FILE_FILTER, AnimationParseError
from ..animation.interpolate import blend_fraction
from ..animation.model import MAX_FRAMES, Keyframe
from ..animation.render import safe_stem
from ..fractal.scene import Flame
from ..render.service import RenderService
from ..widgets.actions import make_action, populate
from ..widgets.icons import action_icon, animation_icon, editor_icon
from ..widgets.silent import blocked, set_value_silently
from ..widgets.timeline import Timeline
from .animation_document import AnimationDocument
from .animation_panels import AnimationSettingsPanel, KeyframePanel
from .animation_playback import Playback
from .fractal_document import FractalDocument
from .live_preview import DEFAULT_QUALITY, LivePreview, quality_level

WINDOW_TITLE = "Animation"
SETTINGS_GROUP = "animation"
PREVIEW_SIZE = (480, 300)
SIDE_WIDTH = 380


class AnimationWindow(QMainWindow):
    """The Animation window (see the module docstring)."""

    def __init__(self, fractal: FractalDocument, service: RenderService, show_flame: Callable[[Flame], None],
                 parent: QWidget | None = None, settings: QSettings | None = None):
        """Args:
            fractal: The main window's document: what *Capture keyframe* takes.
            service: The shared render service (for the preview).
            show_flame: Shows a flame in the main window (what clicking a keyframe does).
            parent: Owning window; when given this becomes a child top-level window.
            settings: Where window preferences persist.
        """
        super().__init__(parent, Qt.WindowType.Window)
        self.setWindowTitle(WINDOW_TITLE)
        self.setWindowIcon(animation_icon())
        self.fractal = fractal
        self._show_flame = show_flame
        self._settings = settings if settings is not None else QSettings()
        self.document = AnimationDocument(self)
        self.playback = Playback(self.document, self)
        self.preview = LivePreview(self, PREVIEW_SIZE, flame_provider=self.document.flame_at, name="animation-preview")
        self.preview.placeholder = "Capture a keyframe to start"
        self.preview.bind(None, service)
        self.timeline = Timeline(self)
        self.settings_panel = AnimationSettingsPanel(self)
        self.keyframe_panel = KeyframePanel(self)
        self.frame_box = QSpinBox(self)
        self.time_label = QLabel(self)
        self.blend_label = QLabel(self)
        self.play_button = QPushButton("Play", self)
        self.message = QLabel(self)
        self.render_window = None
        self.rate_hint = None          # set by the main window: the preview engine's measured speed, for estimates
        self._build()
        self._build_actions()
        self._connect()
        self._load_settings()
        self.refresh()

    # --- construction ---------------------------------------------------------------------------------------
    def _build(self) -> None:
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(6, 4, 6, 4)
        top = QHBoxLayout()
        left = QVBoxLayout()
        left.addStretch(1)
        preview_row = QHBoxLayout()
        preview_row.addStretch(1)
        preview_row.addWidget(self.preview)
        preview_row.addStretch(1)
        left.addLayout(preview_row)
        left.addLayout(self._transport_row())
        left.addStretch(1)
        top.addLayout(left, 1)
        side = QWidget(self)
        side.setFixedWidth(SIDE_WIDTH)
        side_layout = QVBoxLayout(side)
        side_layout.setContentsMargins(0, 0, 0, 0)
        side_layout.addWidget(self.settings_panel)
        side_layout.addWidget(self.keyframe_panel, 1)
        top.addWidget(side, 0)
        layout.addLayout(top, 1)
        self.timeline.setToolTip("Click or drag to move the playhead; drag a keyframe to move it in time; "
                                 "double-click a keyframe to show it in the main window; wheel zooms, Shift + wheel scrolls")
        layout.addWidget(self.timeline)
        self.setCentralWidget(central)
        status = QStatusBar(self)
        status.addWidget(self.message, 1)
        self.setStatusBar(status)
        self.resize(1100, 640)

    def _transport_row(self) -> QHBoxLayout:
        """The playhead's frame box, the time, Play and the blend read-out under the preview."""
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(QLabel("Frame", self))
        self.frame_box.setRange(0, MAX_FRAMES)
        self.frame_box.setKeyboardTracking(False)
        self.frame_box.setToolTip("The playhead: the frame shown in the preview and where a keyframe is captured")
        row.addWidget(self.frame_box)
        row.addWidget(self.time_label)
        row.addSpacing(12)
        self.play_button.setToolTip("Play the animation in the preview (Space)")
        row.addWidget(self.play_button)
        row.addWidget(self.blend_label)
        row.addStretch(1)
        return row

    def _build_actions(self) -> None:
        doc = self.document

        def act(text, icon, slot, shortcut=None, tip=""):
            return make_action(self, text, icon, slot, shortcut, tip)


        self.act_new = act("New animation", "anim-new", self.new_animation, "Ctrl+N", "Start an empty animation")
        self.act_open = act("Open animation…", self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton),
                            lambda: self.open_animation(), "Ctrl+O", "Open a .faanim file")
        self.act_save = act("Save animation", action_icon("save"), self.save_animation, "Ctrl+S", "Save the animation to its .faanim file")
        self.act_save_as = act("Save animation as…", action_icon("save-as"), self.save_animation_as, "Ctrl+Shift+S",
                               "Save the animation to a new .faanim file")
        self.act_capture = act("Capture keyframe", "anim-capture", self.capture_keyframe, "K",
                               "Pin the fractal shown in the main window at the playhead's frame")
        self.act_update = act("Update keyframe", "anim-update", self.update_keyframe, None,
                              "Replace the selected keyframe's fractal with the one in the main window")
        self.act_delete = act("Delete keyframe", "anim-delete", self.delete_keyframe, None, "Remove the selected keyframe")
        self.act_first = act("Go to start", "anim-first", lambda: doc.set_frame(0), "Home", "Playhead to the first frame")
        self.act_prev = act("Previous keyframe", "anim-prev", self.previous_keyframe, "Ctrl+Left", "Playhead to the previous keyframe")
        self.act_play = act("Play", "anim-play", self.playback.toggle, "Space", "Play / pause the preview")
        self.act_play.setCheckable(True)
        self.act_stop = act("Stop", "anim-stop", self.playback.stop, None, "Stop playing and return to where playback started")
        self.act_next = act("Next keyframe", "anim-next", self.next_keyframe, "Ctrl+Right", "Playhead to the next keyframe")
        self.act_last = act("Go to end", "anim-last", lambda: doc.set_frame(doc.animation.last_frame), "End", "Playhead to the last frame")
        self.act_render = act("Render Animation…", "anim-render", self.show_render_window, "Ctrl+R",
                              "Render every frame to images (and a video with ffmpeg)")
        self.act_fit = act("Fit timeline", "fit", self.timeline.fit, "Ctrl+0", "Show the whole animation on the timeline")
        self.act_close = act("Close", None, self.close, "Ctrl+W")
        self.toolbar = QToolBar("Animation", self)
        self.toolbar.setMovable(False)
        populate(self.toolbar, self.act_new, self.act_open, self.act_save, self.act_save_as, None, self.act_capture, self.act_update,
                 self.act_delete, None, self.act_first, self.act_prev, self.act_play, self.act_stop, self.act_next, self.act_last, None,
                 self.act_render)
        self.addToolBar(self.toolbar)
        populate(self.menuBar().addMenu("File"), self.act_new, self.act_open, self.act_save, self.act_save_as, None, self.act_render, None,
                 self.act_close)
        populate(self.menuBar().addMenu("Keyframes"), self.act_capture, self.act_update, self.act_delete)
        populate(self.menuBar().addMenu("Playback"), self.act_play, self.act_stop, None, self.act_first, self.act_prev, self.act_next,
                 self.act_last, None, self.act_fit)

    def _connect(self) -> None:
        doc, keys = self.document, self.keyframe_panel
        doc.animation_replaced.connect(self.refresh)
        doc.keyframes_changed.connect(self._refresh_keyframes)
        doc.settings_changed.connect(self._refresh_settings)
        doc.frame_changed.connect(self._on_frame_changed)
        doc.selection_changed.connect(self._on_selection_changed)
        doc.modified_changed.connect(lambda _m: self._refresh_title())
        self.fractal.flame_replaced.connect(self._refresh_capture)
        self.playback.state_changed.connect(self._sync_play_controls)
        self.timeline.frame_scrubbed.connect(self._scrub)
        self.timeline.keyframe_clicked.connect(self._keyframe_chosen)
        self.timeline.keyframe_activated.connect(self._keyframe_chosen)
        self.timeline.keyframe_dragged.connect(doc.move_keyframe)
        self.timeline.keyframe_dropped.connect(lambda key: doc.set_frame(key.frame))
        self.timeline.delete_requested.connect(self.delete_keyframe)
        self.settings_panel.edited.connect(lambda fields: doc.set_settings(**fields))
        keys.keyframe_clicked.connect(self._keyframe_chosen)
        keys.keyframe_selected.connect(lambda key: key is doc.selected or doc.select(key))
        keys.frame_edited.connect(self._key_frame_edited)
        keys.name_edited.connect(lambda name: doc.selected is None or doc.rename_keyframe(doc.selected, name))
        keys.show_requested.connect(self.show_selected_in_main_window)
        keys.update_requested.connect(self.update_keyframe)
        self.frame_box.valueChanged.connect(lambda v: doc.set_frame(int(v)))
        self.play_button.clicked.connect(self.playback.toggle)
        self.preview.quality_changed.connect(lambda q: self._settings.setValue(f"{SETTINGS_GROUP}/preview_quality", q))

    def _load_settings(self) -> None:
        s = self._settings
        try:
            self.preview.level = quality_level(s.value(f"{SETTINGS_GROUP}/preview_quality", DEFAULT_QUALITY.name))
            geometry = s.value(f"{SETTINGS_GROUP}/geometry")
            if geometry is not None:
                self.restoreGeometry(geometry)
        except (TypeError, ValueError):
            pass

    # --- window management ----------------------------------------------------------------------------------
    def bring_to_front(self) -> None:
        """Show the window (restoring it if minimised), focus it and refresh the preview."""
        self.setWindowState(self.windowState() & ~Qt.WindowState.WindowMinimized)
        self.show()
        self.raise_()
        self.activateWindow()
        self.preview.request()

    def confirm_discard(self) -> bool:
        """Ask about unsaved changes; True = go ahead."""
        if not self.document.modified:
            return True
        answer = QMessageBox.question(self, WINDOW_TITLE, f"The animation '{self.document.title}' has unsaved changes. Discard them?",
                                      QMessageBox.StandardButton.Discard | QMessageBox.StandardButton.Cancel)
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        self.playback.stop()
        self._settings.setValue(f"{SETTINGS_GROUP}/geometry", self.saveGeometry())
        if self.parent() is not None:
            event.ignore()
            self.hide()
            return
        super().closeEvent(event)

    def showEvent(self, event) -> None:
        super().showEvent(event)
        QTimer.singleShot(0, self.timeline.fit)

    # --- files ----------------------------------------------------------------------------------------------
    def new_animation(self) -> None:
        """Start an empty animation (asking about unsaved changes first)."""
        if not self.confirm_discard():
            return
        self.playback.stop(rewind=False)
        self.document.new()
        self._message("New animation — capture a keyframe from the main window to start")

    def open_animation(self, path: Path | None = None) -> bool:
        """Open a `.faanim` file (asks for one when `path` is None); shows its first keyframe in the main window."""
        if not self.confirm_discard():
            return False
        if path is None:
            start = str(self.document.path.parent if self.document.path else self._folder())
            chosen, _ = QFileDialog.getOpenFileName(self, "Open animation", start, FILE_FILTER)
            if not chosen:
                return False
            path = Path(chosen)
        self.playback.stop(rewind=False)
        try:
            animation = self.document.load(Path(path))
        except AnimationParseError as exc:
            QMessageBox.warning(self, WINDOW_TITLE, str(exc))
            self._message(str(exc))
            return False
        self._settings.setValue(f"{SETTINGS_GROUP}/folder", str(Path(path).parent))
        if animation.keyframes:
            self._show_flame(animation.keyframes[0].flame.copy())
        self._message(f"Opened '{self.document.title}': {len(animation.keyframes)} keyframes, {animation.total_frames} frames at {animation.fps} fps")
        QTimer.singleShot(0, self.timeline.fit)
        return True

    def save_animation(self) -> bool:
        """Save to the animation's own file (asks for one the first time); True when written."""
        if self.document.path is None:
            return self.save_animation_as()
        return self._write(self.document.path)

    def save_animation_as(self) -> bool:
        """Ask for a `.faanim` file and save there; True when written."""
        start = self.document.path if self.document.path else self._folder() / (safe_stem(self.document.animation.name) + EXTENSION)
        chosen, _ = QFileDialog.getSaveFileName(self, "Save animation", str(start), FILE_FILTER)
        return bool(chosen) and self._write(Path(chosen))

    def _write(self, path: Path) -> bool:
        try:
            written = self.document.save(path)
        except OSError as exc:
            QMessageBox.warning(self, WINDOW_TITLE, f"Could not save the animation: {exc}")
            return False
        self._settings.setValue(f"{SETTINGS_GROUP}/folder", str(written.parent))
        self._message(f"Saved {written.name}")
        self._refresh_title()
        return True

    def _folder(self) -> Path:
        stored = self._settings.value(f"{SETTINGS_GROUP}/folder")
        return Path(stored) if stored else Path(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DocumentsLocation) or Path.home())

    # --- keyframes ------------------------------------------------------------------------------------------
    def capture_keyframe(self) -> Keyframe | None:
        """Pin the main window's fractal at the playhead's frame."""
        flame = self.fractal.flame
        if flame is None:
            self._message("Nothing to capture: open a fractal in the main window first")
            return None
        existed = self.document.animation.keyframe_at(self.document.frame) is not None
        keyframe = self.document.capture(flame)
        self._message(f"Keyframe {'replaced' if existed else 'captured'} at frame {keyframe.frame} — move the playhead, "
                      f"change the fractal, and capture the next one")
        return keyframe

    def update_keyframe(self) -> None:
        """Replace the selected keyframe's fractal with the main window's."""
        key, flame = self.document.selected, self.fractal.flame
        if key is None or flame is None:
            self._message("Select a keyframe and show a fractal in the main window first")
            return
        self.document.update_keyframe(key, flame)
        self._message(f"Keyframe at frame {key.frame} updated from the main window")

    def delete_keyframe(self) -> None:
        """Remove the selected keyframe."""
        key = self.document.selected
        if key is not None:
            self.document.remove_keyframe(key)
            self._message(f"Keyframe at frame {key.frame} removed")

    def show_selected_in_main_window(self) -> None:
        """Load the selected keyframe's fractal in the main window."""
        if self.document.selected is not None:
            self._keyframe_chosen(self.document.selected)

    def _keyframe_chosen(self, keyframe: Keyframe) -> None:
        """A keyframe was clicked: select it, move the playhead to it, and show its fractal in the main window."""
        self.playback.stop(rewind=False)
        self.document.select(keyframe)
        self.document.set_frame(keyframe.frame)
        self._show_flame(keyframe.flame.copy())
        self._message(f"Showing keyframe at frame {keyframe.frame} in the main window")

    def _go_to(self, keyframe: Keyframe | None) -> None:
        if keyframe is not None:
            self.document.select(keyframe)
            self.document.set_frame(keyframe.frame)

    def previous_keyframe(self) -> None:
        """Select the keyframe before the playhead and move the playhead to it."""
        self._go_to(self.document.animation.previous_keyframe(self.document.frame))

    def next_keyframe(self) -> None:
        """Select the keyframe after the playhead and move the playhead to it."""
        self._go_to(self.document.animation.next_keyframe(self.document.frame))

    # --- render ---------------------------------------------------------------------------------------------
    def show_render_window(self) -> None:
        """Open the Render Animation window (created on first use)."""
        if self.render_window is None:
            from .animation_render_window import AnimationRenderWindow
            self.render_window = AnimationRenderWindow(self.document, self, self._settings, rate_hint=self.rate_hint)
        self.render_window.bring_to_front()

    # --- document → controls --------------------------------------------------------------------------------
    def refresh(self) -> None:
        """Everything from the document: settings, keyframes, playhead, selection, preview."""
        self._refresh_settings()
        self._refresh_keyframes()
        self._on_frame_changed(self.document.frame)
        self._on_selection_changed(self.document.selected)

    def _refresh_settings(self) -> None:
        anim = self.document.animation
        self.settings_panel.show(anim)
        self.frame_box.setMaximum(anim.last_frame)
        self._refresh_timeline()
        self._refresh_title()
        self.preview.request()

    def _refresh_keyframes(self) -> None:
        self.keyframe_panel.show(self.document.animation, self.document.selected, self.fractal.flame is not None)
        self._refresh_timeline()
        self._refresh_title()
        self._sync_actions()
        self.preview.request()

    def _refresh_timeline(self) -> None:
        anim = self.document.animation
        self.timeline.set_data(anim.total_frames, anim.fps, anim.keyframes, self.document.selected, self.document.frame, anim.loop)

    def _refresh_capture(self) -> None:
        can_capture = self.fractal.flame is not None
        self.act_capture.setEnabled(can_capture)
        self.act_update.setEnabled(can_capture and self.document.selected is not None)
        self.keyframe_panel.show_selected(self.document.selected, can_capture)

    def _refresh_title(self) -> None:
        star = "*" if self.document.modified else ""
        self.setWindowTitle(f"{WINDOW_TITLE} — {self.document.title}{star}")

    def _sync_actions(self) -> None:
        self.act_delete.setEnabled(self.document.selected is not None)
        self.act_render.setEnabled(bool(self.document.animation.keyframes))
        self._refresh_capture()
        self._sync_play_controls()

    def _sync_play_controls(self) -> None:
        playing = self.playback.playing
        with blocked(self.act_play):
            self.act_play.setChecked(playing)
        self.act_play.setText("Pause" if playing else "Play")
        self.act_play.setIcon(editor_icon("anim-pause" if playing else "anim-play"))
        self.play_button.setText("Pause" if playing else "Play")
        self.act_stop.setEnabled(self.playback.in_session)

    def _blend_text(self, frame: int) -> str:
        """What the playhead shows: a keyframe, a blend between two, or a held end."""
        anim = self.document.animation
        key = anim.keyframe_at(frame)
        if key is not None:
            return f"keyframe {anim.keyframes.index(key) + 1}"
        if not anim.keyframes:
            return ""
        before, after = anim.segment(frame)
        if before is not None and (after is not None or anim.loop):
            return f"{blend_fraction(anim, frame) * 100:.0f} % from keyframe {anim.keyframes.index(before) + 1}"
        return "holding the " + ("last" if before is not None else "first") + " keyframe"

    def _on_frame_changed(self, frame: int) -> None:
        anim = self.document.animation
        set_value_silently(self.frame_box, frame)
        self.timeline.set_current_frame(frame)
        self.time_label.setText(f"of {anim.total_frames}  ·  {anim.frame_to_seconds(frame):.2f} s")
        self.blend_label.setText(self._blend_text(frame))
        self.preview.request()
        self._sync_play_controls()

    def _on_selection_changed(self, keyframe) -> None:
        self.keyframe_panel.show_selected(keyframe, self.fractal.flame is not None)
        self.timeline.set_selected(keyframe)
        self._sync_actions()

    # --- controls → document --------------------------------------------------------------------------------
    def _scrub(self, frame: int) -> None:
        self.playback.stop(rewind=False)
        self.document.set_frame(frame)

    def _key_frame_edited(self, value: int) -> None:
        key = self.document.selected
        if key is None:
            return
        got = self.document.move_keyframe(key, value)
        if got != value:
            self.keyframe_panel.set_frame_value(got)
        self.document.set_frame(got)

    def _message(self, text: str) -> None:
        self.message.setText(text)
        self.statusBar().showMessage(text, 6000)


__all__ = ["AnimationWindow", "WINDOW_TITLE"]
