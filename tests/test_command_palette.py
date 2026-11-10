"""The command palette (Ctrl+K): fuzzy matching, the commands of each window, running one, and the recent ones first."""

from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from fractalchemy.search import best_matches, fuzzy_score
from fractalchemy.widgets.command_palette import Command, rank
from tests.conftest import open_flame_and_wait, wait_until


def test_fuzzy_matching_prefers_starts_runs_and_short_texts():
    assert fuzzy_score("undo", "Undo Gamma") > fuzzy_score("undo", "Redo the undone") > 0
    assert fuzzy_score("gl", "Gradient Library") is not None and fuzzy_score("zz", "Gradient Library") is None
    assert fuzzy_score("grad lib", "Gradient Library") > fuzzy_score("grad lib", "Gradient from a file in the library")
    texts = ["Save Fractal", "Save Fractal As ▸ As New File…", "Paste Parameters"]
    assert [i for _s, i in best_matches("save", texts)] == [0, 1]
    assert fuzzy_score("", "anything") == 0.0


def test_ranking_puts_the_title_first_and_disabled_commands_last():
    commands = [Command("Undo", "Edit"), Command("Paste Parameters", "Edit", enabled=False), Command("Parameters", "Script Editor"),
                Command("Redo", "Edit")]
    assert [c.title for c in rank(commands, "par")][:2] == ["Parameters", "Paste Parameters"]
    assert [c.title for c in rank(commands, "", recent=["Edit ▸ Redo"])][0] == "Redo"


def test_the_palette_lists_the_main_windows_commands_and_runs_one(main_window_factory, samples):
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    palette = win.palette.open(win)
    keys = [c.key for c in palette.commands]
    assert "Edit ▸ Copy Parameters" in keys and any(k.startswith("View ▸ Theme ▸ ") for k in keys)
    assert any(k.startswith("File ▸ Open Recent ▸ rotated") for k in keys)          # dynamic menus are filled
    assert any(k.startswith("Scripts ▸ Run template: ") for k in keys)
    win.document.set_coloring(gamma=2.0)
    palette = win.palette.open(win)
    palette.query.setText("undo gam")
    assert palette.shown()[0].title == "Undo Gamma"
    palette.run_current()
    assert not win.document.can_undo or win.document.flame.coloring.gamma != 2.0
    assert win.palette.recent()[0] == "Edit ▸ Undo Gamma"
    win.document.set_coloring(gamma=2.0)                           # the same command is offered first again
    assert win.palette.open(win).shown()[0].key == "Edit ▸ Undo Gamma"


def test_ctrl_k_opens_the_palette_in_tool_windows_with_their_own_commands(main_window_factory, samples):
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    editor = win.script_editor
    editor.bring_to_front()
    editor.activateWindow()
    wait_until(lambda: QApplication.activeWindow() is editor)
    event = QKeyEvent(QEvent.Type.ShortcutOverride, Qt.Key.Key_K, Qt.KeyboardModifier.ControlModifier)
    QApplication.sendEvent(editor.editor, event)
    palette = win.palette.palette
    assert palette is not None and palette.parent() is editor
    keys = [c.key for c in palette.commands]
    assert any(k.startswith("Script Editor: Script ▸ Run") for k in keys) and "Edit ▸ Copy Parameters" in keys
    palette.query.setText("record")
    assert "Record" in palette.shown()[0].title
    palette.reject()
