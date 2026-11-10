"""Everything the main window does with scripts, in one helper (`MainWindow.scripts`):

* the Script Editor window, created on first use and linked to the viewport, the Animation window (*Animate…* in its
  Parameters tab) and the Mutate & Breed window (its *Explore script* tab draws on the live parameters);
* the **Scripts ▾** menu — a toolbar button and *Windows ▸ Scripts* (`script_menu.ScriptsMenu`): pinned templates;
* *Run a Script on Many Fractals* (`ScriptBatchWindow`), also offered by the Fractal Library's *Run Script on
  Selection…*;
* the status-bar **● Recording script** indicator while the Script Editor records (click it to stop).

The main window keeps only the wiring; windows are created lazily, so an unused feature costs nothing at start-up.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QObject
from PySide6.QtWidgets import QToolButton

from ..widgets.icons import script_icon
from ..widgets.theming import set_themed_style
from ..widgets.windows import bring_to_front
from .script_menu import ScriptsMenu

if TYPE_CHECKING:
    from .main_window import MainWindow

RECORDING_TEXT = "● Recording script"


class ScriptTools(QObject):
    """The main window's script features (see the module docstring)."""

    def __init__(self, window: "MainWindow"):
        super().__init__(window)
        self.w = window
        self._editor = None
        self._batch = None
        self.menu = ScriptsMenu(lambda: self.editor, self.show_batch, window)
        self.menu.setIcon(script_icon())
        window.menuWindows.insertMenu(window.actionFormulaEditor, self.menu)
        self.button = QToolButton(window)
        self.button.setIcon(script_icon())
        self.button.setText("Scripts")
        self.button.setToolTip("Scripts: run a pinned script template on the fractal")
        self.button.setMenu(self.menu)
        self.button.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        window.toolBar.insertWidget(window.actionFormulaEditor, self.button)
        self.recording = QToolButton(window)
        self.recording.setText(RECORDING_TEXT)
        self.recording.setToolTip("The Script Editor is recording your edits as code — click to stop")
        self.recording.setAutoRaise(True)
        set_themed_style(self.recording, "QToolButton {{ color: {error}; font-weight: bold; }}")
        self.recording.hide()
        self.recording.clicked.connect(lambda: self._editor is not None and self._editor.set_recording(False))
        window.statusBar().addPermanentWidget(self.recording)

    # --- the Script Editor ---------------------------------------------------------------------------------------------
    @property
    def editor(self):
        """The Script Editor (created on first use; hidden rather than destroyed when closed)."""
        if self._editor is None:
            from .script_editor_window import ScriptEditorWindow
            w = self.w
            editor = ScriptEditorWindow(w.document, w, w._settings, gradient_hint=lambda: w.gradient_library.document.gradient)
            editor.bind_viewport(w.viewport)
            editor.animation_provider = lambda: w.animation
            editor.explore_requested.connect(self.explore)
            editor.batch_requested.connect(self.show_batch)
            editor.recording_changed.connect(self._show_recording)
            self._editor = editor
            if w._mutation is not None:
                w._mutation.set_script_source(editor.live)
        return self._editor

    @property
    def created(self) -> bool:
        return self._editor is not None

    def link_mutation_window(self, window) -> None:
        """A Mutate & Breed window was created: its Explore tab draws on the Script Editor (once that exists)."""
        if self._editor is not None:
            window.set_script_source(self._editor.live)

    def explore(self) -> None:
        """The Parameters tab's *Explore…*: the Mutate & Breed window on its Explore script tab."""
        window = self.w.mutation_window
        window.set_script_source(self.editor.live)
        window.show_exploring()
        window.bring_to_front()

    def _show_recording(self, recording: bool) -> None:
        self.recording.setVisible(recording)

    # --- many fractals ------------------------------------------------------------------------------------------------------
    @property
    def batch_window(self):
        if self._batch is None:
            from .script_batch_window import ScriptBatchWindow
            w = self.w
            self._batch = ScriptBatchWindow(lambda: self.editor, w.fractalLibraryPanel.tree.selected_items, lambda: list(w._batch),
                                            lambda: w.document.flame, w, w._settings, note_write=w.files.note_write,
                                            show_file=w.fractal_library.show_file)
        return self._batch

    def show_batch(self, prefer: str | None = None) -> None:
        """Open (or raise) *Run a Script on Many Fractals* (`prefer`: the source to select)."""
        window = self.batch_window
        window.refresh_sources(prefer)
        bring_to_front(window)


__all__ = ["ScriptTools", "RECORDING_TEXT"]
