"""The Animation window: keyframes of the main window's fractal on a timeline, played back and rendered.

Opened from *Windows ▸ Animation* (`F9`) or the toolbar; a tool window like the others (closing hides it).

* **Capture keyframe** pins whatever the main window shows at the playhead's frame; **Update keyframe**
  replaces the selected keyframe's fractal with it; **Delete keyframe** removes it.
* Clicking a keyframe (in the list or on the timeline) does what choosing another fractal does: the
  main window shows it — so it can be adjusted there, in the Transform Editor or the Gradient Library,
  and captured again.
* The **timeline** scrubs the playhead; the small **preview** shows the interpolated fractal at the
  playhead, and **Play** runs through the animation in it at the animation's frame rate (frames are
  dropped when the engine cannot keep up, so timing stays true).
* **Render Animation…** opens the batch renderer (`AnimationRenderWindow`).
* Files are `.faanim` (JSON); *Open* shows the first keyframe in the main window.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Callable

from PySide6.QtCore import QSettings, QStandardPaths, Qt, QTimer
from PySide6.QtGui import QAction, QCloseEvent, QKeySequence
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDoubleSpinBox, QFileDialog, QFormLayout, QGroupBox, QHBoxLayout, QLabel,
                               QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox, QPushButton, QSpinBox,
                               QStatusBar, QToolBar, QVBoxLayout, QWidget)

from ..animation.format import EXTENSION, FILE_FILTER, AnimationParseError
from ..animation.interpolate import blend_fraction
from ..animation.model import EASINGS, INTERPOLATIONS, MAX_FPS, MAX_FRAMES, Keyframe
from ..fractal.scene import Flame
from ..render.service import RenderService
from ..widgets.icons import action_icon, animation_icon, editor_icon
from ..widgets.silent import blocked, set_value_silently
from ..widgets.timeline import Timeline
from .animation_document import AnimationDocument
from .editor_preview import DEFAULT_QUALITY, EditorPreview, quality_level
from .fractal_document import FractalDocument

WINDOW_TITLE = "Animation"
SETTINGS_GROUP = "animation"
PREVIEW_SIZE = (480, 300)
PLAY_TICK_MS = 15
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
        self.service = service
        self._show_flame = show_flame
        self._settings = settings if settings is not None else QSettings()
        self.document = AnimationDocument(self)
        self.preview = EditorPreview(self, PREVIEW_SIZE, flame_provider=self.document.flame_at, name="animation-preview")
        self.preview.placeholder = "Capture a keyframe to start"
        self.preview.bind(None, service)
        self.timeline = Timeline(self)
        self.render_window = None
        self.rate_hint = None          # set by the main window: the preview engine's measured speed, for estimates
        # controls
        self.name_edit = QLineEdit(self)
        self.fps_box = QSpinBox(self)
        self.frames_box = QSpinBox(self)
        self.duration_box = QDoubleSpinBox(self)
        self.interpolation_box = QComboBox(self)
        self.easing_box = QComboBox(self)
        self.loop_check = QCheckBox("Loop", self)
        self.keyframe_list = QListWidget(self)
        self.key_frame_box = QSpinBox(self)
        self.key_name_edit = QLineEdit(self)
        self.show_button = QPushButton("Show in main window", self)
        self.update_button = QPushButton("Update from main window", self)
        self.frame_box = QSpinBox(self)
        self.time_label = QLabel(self)
        self.blend_label = QLabel(self)
        self.play_button = QPushButton("Play", self)
        self.message = QLabel(self)
        # playback
        self._play_timer = QTimer(self, interval=PLAY_TICK_MS)
        self._play_timer.timeout.connect(self._tick)
        self._play_started = 0.0
        self._play_from = 0
        self._play_session = False     # True from Play until Stop (a pause keeps it: Stop still returns to the start)
        self._updating = False
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
        transport = QHBoxLayout()
        transport.addStretch(1)
        transport.addWidget(QLabel("Frame", self))
        self.frame_box.setRange(0, MAX_FRAMES)
        self.frame_box.setKeyboardTracking(False)
        self.frame_box.setToolTip("The playhead: the frame shown in the preview and where a keyframe is captured")
        transport.addWidget(self.frame_box)
        transport.addWidget(self.time_label)
        transport.addSpacing(12)
        self.play_button.setToolTip("Play the animation in the preview (Space)")
        transport.addWidget(self.play_button)
        transport.addWidget(self.blend_label)
        transport.addStretch(1)
        left.addLayout(transport)
        left.addStretch(1)
        top.addLayout(left, 1)
        top.addWidget(self._side_panel(), 0)
        layout.addLayout(top, 1)
        self.timeline.setToolTip("Click or drag to move the playhead; drag a keyframe to move it in time; "
                                 "double-click a keyframe to show it in the main window; wheel zooms, Shift + wheel scrolls")
        layout.addWidget(self.timeline)
        self.setCentralWidget(central)
        status = QStatusBar(self)
        status.addWidget(self.message, 1)
        self.setStatusBar(status)
        self.resize(1100, 640)

    def _side_panel(self) -> QWidget:
        panel = QWidget(self)
        panel.setFixedWidth(SIDE_WIDTH)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        settings = QGroupBox("Animation", panel)
        form = QFormLayout(settings)
        self.name_edit.setToolTip("The animation's name (the default base name of rendered frames)")
        form.addRow("Name", self.name_edit)
        self.fps_box.setRange(1, MAX_FPS)
        self.fps_box.setKeyboardTracking(False)
        self.fps_box.setToolTip("Frames per second")
        self.frames_box.setRange(1, MAX_FRAMES)
        self.frames_box.setKeyboardTracking(False)
        self.frames_box.setToolTip("Length of the animation in frames (never shorter than the last keyframe)")
        self.duration_box.setRange(0.01, MAX_FRAMES)
        self.duration_box.setDecimals(2)
        self.duration_box.setSuffix(" s")
        self.duration_box.setKeyboardTracking(False)
        self.duration_box.setToolTip("Length in seconds (sets the frame count)")
        row = QHBoxLayout()
        row.addWidget(self.fps_box)
        row.addWidget(QLabel("fps", panel))
        row.addWidget(self.frames_box, 1)
        row.addWidget(QLabel("frames", panel))
        row.addWidget(self.duration_box, 1)
        form.addRow("Length", row)
        for key, label in INTERPOLATIONS:
            self.interpolation_box.addItem(label, key)
        self.interpolation_box.setToolTip("How the frames between keyframes are made")
        form.addRow("Interpolation", self.interpolation_box)
        for key, label in EASINGS:
            self.easing_box.addItem(label, key)
        self.easing_box.setToolTip("Slow down into / out of every keyframe")
        form.addRow("Easing", self.easing_box)
        self.loop_check.setToolTip("After the last keyframe, blend back to the first one at the end of the animation; playback repeats")
        form.addRow("", self.loop_check)
        layout.addWidget(settings)
        keys = QGroupBox("Keyframes", panel)
        keys_layout = QVBoxLayout(keys)
        self.keyframe_list.setToolTip("Click a keyframe to show its fractal in the main window and move the playhead to it")
        keys_layout.addWidget(self.keyframe_list, 1)
        selected = QFormLayout()
        self.key_frame_box.setRange(0, MAX_FRAMES)
        self.key_frame_box.setKeyboardTracking(False)
        self.key_frame_box.setToolTip("Move the selected keyframe to another frame (it stays between its neighbours)")
        selected.addRow("Frame", self.key_frame_box)
        self.key_name_edit.setPlaceholderText("label")
        self.key_name_edit.setToolTip("A label for the keyframe")
        selected.addRow("Name", self.key_name_edit)
        keys_layout.addLayout(selected)
        buttons = QHBoxLayout()
        self.show_button.setToolTip("Load the keyframe's fractal in the main window (like choosing another fractal)")
        self.update_button.setToolTip("Replace the keyframe's fractal with what the main window shows now")
        buttons.addWidget(self.show_button)
        buttons.addWidget(self.update_button)
        keys_layout.addLayout(buttons)
        layout.addWidget(keys, 1)
        return panel

    def _action(self, text: str, icon, slot, shortcut: str | None = None, tip: str = "", checkable: bool = False) -> QAction:
        action = QAction(text, self)
        if isinstance(icon, str):
            action.setIcon(editor_icon(icon))
        elif icon is not None:
            action.setIcon(icon)
        if shortcut:
            action.setShortcut(QKeySequence(shortcut))
        action.setToolTip((tip or text) + (f" ({QKeySequence(shortcut).toString()})" if shortcut else ""))
        action.setStatusTip(tip or text)
        action.setCheckable(checkable)
        action.triggered.connect(slot)
        return action

    def _build_actions(self) -> None:
        self.act_new = self._action("New animation", "anim-new", self.new_animation, "Ctrl+N", "Start an empty animation")
        self.act_open = self._action("Open animation…", self.style().standardIcon(self.style().StandardPixmap.SP_DialogOpenButton),
                                     lambda: self.open_animation(), "Ctrl+O", "Open a .faanim file")
        self.act_save = self._action("Save animation", action_icon("save"), self.save_animation, "Ctrl+S", "Save the animation to its .faanim file")
        self.act_save_as = self._action("Save animation as…", action_icon("save-as"), self.save_animation_as, "Ctrl+Shift+S", "Save the animation to a new .faanim file")
        self.act_capture = self._action("Capture keyframe", "anim-capture", self.capture_keyframe, "K",
                                        "Pin the fractal shown in the main window at the playhead's frame")
        self.act_update = self._action("Update keyframe", "anim-update", self.update_keyframe, None,
                                       "Replace the selected keyframe's fractal with the one in the main window")
        self.act_delete = self._action("Delete keyframe", "anim-delete", self.delete_keyframe, None, "Remove the selected keyframe")
        self.act_first = self._action("Go to start", "anim-first", lambda: self.document.set_frame(0), "Home", "Playhead to the first frame")
        self.act_prev = self._action("Previous keyframe", "anim-prev", self.previous_keyframe, "Ctrl+Left", "Playhead to the previous keyframe")
        self.act_play = self._action("Play", "anim-play", self.toggle_play, "Space", "Play / pause the preview", checkable=True)
        self.act_stop = self._action("Stop", "anim-stop", self.stop, None, "Stop playing and return to where playback started")
        self.act_next = self._action("Next keyframe", "anim-next", self.next_keyframe, "Ctrl+Right", "Playhead to the next keyframe")
        self.act_last = self._action("Go to end", "anim-last", lambda: self.document.set_frame(self.document.animation.last_frame), "End",
                                     "Playhead to the last frame")
        self.act_render = self._action("Render Animation…", "anim-render", self.show_render_window, "Ctrl+R",
                                       "Render every frame to images (and a video with ffmpeg)")
        self.act_fit = self._action("Fit timeline", "fit", self.timeline.fit, "Ctrl+0", "Show the whole animation on the timeline")
        self.act_close = self._action("Close", None, self.close, "Ctrl+W")
        toolbar = QToolBar("Animation", self)
        toolbar.setMovable(False)
        for item in (self.act_new, self.act_open, self.act_save, self.act_save_as, None, self.act_capture, self.act_update,
                     self.act_delete, None, self.act_first, self.act_prev, self.act_play, self.act_stop, self.act_next, self.act_last,
                     None, self.act_render):
            toolbar.addSeparator() if item is None else toolbar.addAction(item)
        self.addToolBar(toolbar)
        self.toolbar = toolbar
        menu_file = self.menuBar().addMenu("File")
        for item in (self.act_new, self.act_open, self.act_save, self.act_save_as, None, self.act_render, None, self.act_close):
            menu_file.addSeparator() if item is None else menu_file.addAction(item)
        menu_keys = self.menuBar().addMenu("Keyframes")
        for item in (self.act_capture, self.act_update, self.act_delete):
            menu_keys.addAction(item)
        menu_play = self.menuBar().addMenu("Playback")
        for item in (self.act_play, self.act_stop, None, self.act_first, self.act_prev, self.act_next, self.act_last, None, self.act_fit):
            menu_play.addSeparator() if item is None else menu_play.addAction(item)

    def _connect(self) -> None:
        doc = self.document
        doc.animation_replaced.connect(self.refresh)
        doc.keyframes_changed.connect(self._refresh_keyframes)
        doc.settings_changed.connect(self._refresh_settings)
        doc.frame_changed.connect(self._on_frame_changed)
        doc.selection_changed.connect(self._on_selection_changed)
        doc.modified_changed.connect(lambda _m: self._refresh_title())
        self.fractal.flame_replaced.connect(self._refresh_capture)
        self.timeline.frame_scrubbed.connect(self._scrub)
        self.timeline.keyframe_clicked.connect(self._keyframe_chosen)
        self.timeline.keyframe_activated.connect(self._keyframe_chosen)
        self.timeline.keyframe_dragged.connect(lambda key, frame: self.document.move_keyframe(key, frame))
        self.timeline.keyframe_dropped.connect(lambda key: self.document.set_frame(key.frame))
        self.timeline.delete_requested.connect(self.delete_keyframe)
        self.keyframe_list.itemClicked.connect(self._list_clicked)
        self.keyframe_list.currentRowChanged.connect(self._list_row_changed)
        self.name_edit.editingFinished.connect(lambda: self._set(name=self.name_edit.text().strip() or "animation"))
        self.fps_box.valueChanged.connect(lambda v: self._set(fps=int(v)))
        self.frames_box.valueChanged.connect(lambda v: self._set(total_frames=int(v)))
        self.duration_box.valueChanged.connect(lambda v: self._set(total_frames=max(1, round(v * self.document.animation.fps))))
        self.interpolation_box.currentIndexChanged.connect(lambda _i: self._set(interpolation=self.interpolation_box.currentData()))
        self.easing_box.currentIndexChanged.connect(lambda _i: self._set(easing=self.easing_box.currentData()))
        self.loop_check.toggled.connect(lambda on: self._set(loop=bool(on)))
        self.key_frame_box.valueChanged.connect(self._key_frame_edited)
        self.key_name_edit.editingFinished.connect(self._key_name_edited)
        self.show_button.clicked.connect(self.show_selected_in_main_window)
        self.update_button.clicked.connect(self.update_keyframe)
        self.frame_box.valueChanged.connect(lambda v: self.document.set_frame(int(v)))
        self.play_button.clicked.connect(self.toggle_play)
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
        self.stop()
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
        if not self.confirm_discard():
            return
        self.stop()
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
        self.stop()
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
        if self.document.path is None:
            return self.save_animation_as()
        return self._write(self.document.path)

    def save_animation_as(self) -> bool:
        from ..animation.render import safe_stem
        start = self.document.path if self.document.path else self._folder() / (safe_stem(self.document.animation.name) + EXTENSION)
        chosen, _ = QFileDialog.getSaveFileName(self, "Save animation", str(start), FILE_FILTER)
        if not chosen:
            return False
        return self._write(Path(chosen))

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
        key, flame = self.document.selected, self.fractal.flame
        if key is None or flame is None:
            self._message("Select a keyframe and show a fractal in the main window first")
            return
        self.document.update_keyframe(key, flame)
        self._message(f"Keyframe at frame {key.frame} updated from the main window")

    def delete_keyframe(self) -> None:
        key = self.document.selected
        if key is not None:
            self.document.remove_keyframe(key)
            self._message(f"Keyframe at frame {key.frame} removed")

    def show_selected_in_main_window(self) -> None:
        key = self.document.selected
        if key is not None:
            self._keyframe_chosen(key)

    def _keyframe_chosen(self, keyframe: Keyframe) -> None:
        """A keyframe was clicked: select it, move the playhead to it, and show its fractal in the main window."""
        self.stop()
        self.document.select(keyframe)
        self.document.set_frame(keyframe.frame)
        self._show_flame(keyframe.flame.copy())
        self._message(f"Showing keyframe at frame {keyframe.frame} in the main window")

    def previous_keyframe(self) -> None:
        key = self.document.animation.previous_keyframe(self.document.frame)
        if key is not None:
            self.document.select(key)
            self.document.set_frame(key.frame)

    def next_keyframe(self) -> None:
        key = self.document.animation.next_keyframe(self.document.frame)
        if key is not None:
            self.document.select(key)
            self.document.set_frame(key.frame)

    # --- playback -------------------------------------------------------------------------------------------
    @property
    def playing(self) -> bool:
        return self._play_timer.isActive()

    def toggle_play(self) -> None:
        if self.playing:
            self.pause()
        else:
            self.play()

    def play(self) -> None:
        if not self.document.animation.keyframes:
            self._message("Nothing to play yet")
            self._sync_play_controls()
            return
        anim = self.document.animation
        if self.document.frame >= anim.last_frame and not anim.loop:
            self.document.set_frame(0)
        if not self._play_session:
            self._play_from = self.document.frame
            self._play_session = True
        self._play_started = time.monotonic() - (self.document.frame - self._play_from) / max(1, anim.fps)
        self._play_timer.start()
        self._sync_play_controls()

    def pause(self) -> None:
        self._play_timer.stop()
        self._sync_play_controls()

    def stop(self) -> None:
        """Stop playing and put the playhead back where playback started."""
        self._play_timer.stop()
        if self._play_session:
            self._play_session = False
            self.document.set_frame(self._play_from)
        self._sync_play_controls()

    def _tick(self) -> None:
        anim = self.document.animation
        elapsed = time.monotonic() - self._play_started
        frame = self._play_from + int(elapsed * anim.fps)
        if frame >= anim.total_frames:
            if anim.loop:
                frame %= anim.total_frames
            else:
                self._play_timer.stop()
                self._play_session = False
                self.document.set_frame(anim.last_frame)
                self._sync_play_controls()
                return
        self.document.set_frame(frame)

    def _sync_play_controls(self) -> None:
        playing = self.playing
        with blocked(self.act_play):
            self.act_play.setChecked(playing)
        self.act_play.setText("Pause" if playing else "Play")
        self.act_play.setIcon(editor_icon("anim-pause" if playing else "anim-play"))
        self.play_button.setText("Pause" if playing else "Play")
        self.act_stop.setEnabled(self._play_session)

    # --- render ---------------------------------------------------------------------------------------------
    def show_render_window(self) -> None:
        """Open the Render Animation window (created on first use)."""
        if self.render_window is None:
            from .animation_render_window import AnimationRenderWindow
            self.render_window = AnimationRenderWindow(self.document, self, self._settings, rate_hint=self.rate_hint)
        self.render_window.bring_to_front()

    # --- document → controls --------------------------------------------------------------------------------
    def refresh(self) -> None:
        self._refresh_settings()
        self._refresh_keyframes()
        self._on_frame_changed(self.document.frame)
        self._on_selection_changed(self.document.selected)
        self._refresh_capture()
        self.preview.request()

    def _refresh_settings(self) -> None:
        anim = self.document.animation
        self._updating = True
        try:
            if self.name_edit.text() != anim.name:
                self.name_edit.setText(anim.name)
            set_value_silently(self.fps_box, anim.fps)
            set_value_silently(self.frames_box, anim.total_frames)
            set_value_silently(self.duration_box, anim.duration)
            with blocked(self.interpolation_box, self.easing_box, self.loop_check):
                self.interpolation_box.setCurrentIndex(max(0, self.interpolation_box.findData(anim.interpolation)))
                self.easing_box.setCurrentIndex(max(0, self.easing_box.findData(anim.easing)))
                self.loop_check.setChecked(anim.loop)
            self.frame_box.setMaximum(anim.last_frame)
        finally:
            self._updating = False
        self._refresh_timeline()
        self._refresh_title()
        self.preview.request()

    def _refresh_keyframes(self) -> None:
        anim = self.document.animation
        with blocked(self.keyframe_list):
            self.keyframe_list.clear()
            for i, key in enumerate(anim.keyframes):
                item = QListWidgetItem(f"{i + 1}.  frame {key.frame}  ({anim.frame_to_seconds(key.frame):.2f} s)  —  {key.label}")
                item.setToolTip(f"{key.label}: {len(key.flame.xforms)} transforms" + (" + final" if key.flame.final else ""))
                self.keyframe_list.addItem(item)
            if self.document.selected in anim.keyframes:
                self.keyframe_list.setCurrentRow(anim.keyframes.index(self.document.selected))
        self._refresh_selected_controls()
        self._refresh_timeline()
        self._refresh_title()
        self.preview.request()
        self._sync_actions()

    def _refresh_timeline(self) -> None:
        anim = self.document.animation
        self.timeline.set_data(anim.total_frames, anim.fps, anim.keyframes, self.document.selected, self.document.frame, anim.loop)

    def _refresh_selected_controls(self) -> None:
        key = self.document.selected
        self._updating = True
        try:
            enabled = key is not None
            for w in (self.key_frame_box, self.key_name_edit, self.show_button, self.update_button):
                w.setEnabled(enabled)
            set_value_silently(self.key_frame_box, key.frame if key else 0)
            if self.key_name_edit.text() != (key.name if key else ""):
                self.key_name_edit.setText(key.name if key else "")
        finally:
            self._updating = False

    def _refresh_capture(self) -> None:
        self.act_capture.setEnabled(self.fractal.flame is not None)
        self.update_button.setEnabled(self.fractal.flame is not None and self.document.selected is not None)
        self.act_update.setEnabled(self.update_button.isEnabled())

    def _refresh_title(self) -> None:
        star = "*" if self.document.modified else ""
        self.setWindowTitle(f"{WINDOW_TITLE} — {self.document.title}{star}")

    def _sync_actions(self) -> None:
        has_keys = bool(self.document.animation.keyframes)
        self.act_delete.setEnabled(self.document.selected is not None)
        self.act_render.setEnabled(has_keys)
        self.act_save.setEnabled(True)
        self._refresh_capture()
        self._sync_play_controls()

    def _on_frame_changed(self, frame: int) -> None:
        anim = self.document.animation
        set_value_silently(self.frame_box, frame)
        self.timeline.set_current_frame(frame)
        self.time_label.setText(f"of {anim.total_frames}  ·  {anim.frame_to_seconds(frame):.2f} s")
        key = anim.keyframe_at(frame)
        if key is not None:
            self.blend_label.setText(f"keyframe {anim.keyframes.index(key) + 1}")
        elif anim.keyframes:
            before, after = anim.segment(frame)
            if before is not None and (after is not None or anim.loop):
                self.blend_label.setText(f"{blend_fraction(anim, frame) * 100:.0f} % from keyframe {anim.keyframes.index(before) + 1}")
            else:
                self.blend_label.setText("holding the " + ("last" if before is not None else "first") + " keyframe")
        else:
            self.blend_label.setText("")
        self.preview.request()
        self._sync_play_controls()

    def _on_selection_changed(self, keyframe) -> None:
        anim = self.document.animation
        with blocked(self.keyframe_list):
            self.keyframe_list.setCurrentRow(anim.keyframes.index(keyframe) if keyframe in anim.keyframes else -1)
        self.timeline.set_selected(keyframe)
        self._refresh_selected_controls()
        self._sync_actions()

    # --- controls → document --------------------------------------------------------------------------------
    def _set(self, **fields) -> None:
        if not self._updating:
            self.document.set_settings(**fields)

    def _scrub(self, frame: int) -> None:
        self._play_timer.stop()
        self._play_session = False
        self.document.set_frame(frame)
        self._sync_play_controls()

    def _list_clicked(self, item: QListWidgetItem) -> None:
        row = self.keyframe_list.row(item)
        keys = self.document.animation.keyframes
        if 0 <= row < len(keys):
            self._keyframe_chosen(keys[row])

    def _list_row_changed(self, row: int) -> None:
        keys = self.document.animation.keyframes
        if 0 <= row < len(keys) and keys[row] is not self.document.selected:
            self.document.select(keys[row])

    def _key_frame_edited(self, value: int) -> None:
        key = self.document.selected
        if key is not None and not self._updating:
            got = self.document.move_keyframe(key, int(value))
            if got != value:
                set_value_silently(self.key_frame_box, got)
            self.document.set_frame(got)

    def _key_name_edited(self) -> None:
        key = self.document.selected
        if key is not None and not self._updating:
            self.document.rename_keyframe(key, self.key_name_edit.text().strip())

    def _message(self, text: str) -> None:
        self.message.setText(text)
        self.statusBar().showMessage(text, 6000)


__all__ = ["AnimationWindow", "WINDOW_TITLE"]
