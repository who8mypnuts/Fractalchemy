"""Record: edits made in the main window, the Gradient Library and the Transform Editor become code in the Script
Editor — one statement per drag, undo-aware, never stealing the focus — and replaying the recording reproduces them."""

import threading

import pytest

from fractalchemy import config
from fractalchemy.scripting.codegen import flame_differences
from fractalchemy.scripting.runner import run_script
from fractalchemy.ui import fractal_document as FD
from tests.conftest import open_flame_and_wait, spin, wait_until


@pytest.fixture
def rec(main_window_factory, samples, monkeypatch):
    monkeypatch.setattr(config, "SCRIPT_RECORD_REFRESH_MS", 10)
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2, gradient_too=True)
    editor = win.script_editor
    editor.editor.set_text("# recording\n")
    editor.editor.moveCursor(editor.editor.textCursor().MoveOperation.End)
    editor.main = win
    return editor


def code_lines(editor):
    return [line for line in editor.editor.text().split("\n") if line.strip() and not line.startswith("#")]


def settle_recorder():
    spin(60)


def test_record_writes_one_statement_per_drag(rec):
    doc = rec.main.document
    start = doc.flame.copy()
    assert rec.set_recording(True) and rec.actionRecord.isChecked()
    assert rec.main.scripts.recording.isVisibleTo(rec.main)
    for gamma in (2.0, 2.5, 3.0, 3.5):
        doc.set_coloring(gamma=gamma)
    settle_recorder()
    assert code_lines(rec) == ["coloring.gamma = 3.5"]
    doc.set_view(zoom=1.25)
    doc.set_coloring(brightness=9.0)
    doc.set_coloring(gamma=2.0)
    settle_recorder()
    assert code_lines(rec) == ["coloring.gamma = 3.5", "camera.zoom = 1.25", "coloring.brightness = 9.0", "coloring.gamma = 2.0"]
    rec.set_recording(False)
    assert not rec.main.scripts.recording.isVisibleTo(rec.main)
    replayed = run_script(rec.editor.text(), start, None, threading.Event()).flame
    assert flame_differences(replayed, doc.flame) == []


def test_typing_in_the_editor_starts_a_new_statement(rec):
    doc = rec.main.document
    rec.set_recording(True)
    doc.set_coloring(gamma=2.0)
    settle_recorder()
    rec.editor.insertPlainText("\nprint('hi')")
    doc.set_coloring(gamma=2.5)
    settle_recorder()
    assert code_lines(rec) == ["coloring.gamma = 2.0", "print('hi')", "coloring.gamma = 2.5"]
    rec.set_recording(False)


def test_a_camera_drag_is_one_statement(rec):
    from tests.conftest import mouse_drag
    from PySide6.QtCore import QPointF, Qt
    rec.set_recording(True)
    view = rec.main.viewport
    centre = QPointF(view.width() / 2, view.height() / 2)
    mouse_drag(view, centre, centre + QPointF(40, 25), Qt.KeyboardModifier.ControlModifier, steps=6)
    settle_recorder()
    lines = code_lines(rec)
    assert len(lines) == 1 and lines[0].startswith("camera.center = (")
    rec.set_recording(False)


def test_undo_in_the_main_window_removes_the_statement_and_redo_restores_it(rec):
    doc = rec.main.document
    FD.UNDO_COALESCE_SECONDS, saved = 0.0, FD.UNDO_COALESCE_SECONDS
    try:
        rec.set_recording(True)
        doc.set_coloring(gamma=2.0)
        settle_recorder()
        doc.set_view(zoom=1.5)
        settle_recorder()
        assert code_lines(rec) == ["coloring.gamma = 2.0", "camera.zoom = 1.5"]
        doc.undo()
        assert code_lines(rec) == ["coloring.gamma = 2.0"]
        doc.redo()
        assert code_lines(rec) == ["coloring.gamma = 2.0", "camera.zoom = 1.5"]
        doc.undo()
        doc.undo()
        assert code_lines(rec) == []
    finally:
        FD.UNDO_COALESCE_SECONDS = saved
        rec.set_recording(False)


def test_gradient_library_edits_are_recorded_as_its_nodes(rec):
    library = rec.main.gradient_library.document
    rec.set_recording(True)
    library.set_color(0, (250, 10, 10))
    settle_recorder()
    lines = code_lines(rec)
    assert lines[0].startswith("gradient.set_stops(") and "'#fa0a0a'" in rec.editor.text()
    rec.set_recording(False)


def test_transform_editor_edits_and_structure(rec):
    doc = rec.main.document
    start = doc.flame.copy()
    rec.set_recording(True)
    doc.set_affine(1, "coefs", (0.4, 0.1, -0.1, 0.4, 0.3, 0.2), sticky=True)
    doc.set_affine(1, "coefs", (0.5, 0.1, -0.1, 0.5, 0.3, 0.2), sticky=True)
    doc.add_xform()
    doc.delete_xform(0)
    settle_recorder()
    lines = code_lines(rec)
    assert lines[0] == "transforms[1].coefs = (0.5, 0.1, -0.1, 0.5, 0.3, 0.2)"
    assert any("add_transform(" in line for line in lines) and "remove_transform(0)" in lines
    rec.set_recording(False)
    replayed = run_script(rec.editor.text(), start, None, threading.Event()).flame
    assert flame_differences(replayed, doc.flame) == []


def test_running_a_script_stops_recording_and_scripts_are_not_recorded(rec):
    rec.set_recording(True)
    rec.main.document.set_coloring(gamma=2.2)
    settle_recorder()
    rec.run()
    assert not rec.recorder.recording and not rec.actionRecord.isChecked()
    wait_until(lambda: not rec.running)


def test_switching_fractals_leaves_a_comment_and_recording_goes_on(rec, samples):
    rec.set_recording(True)
    open_flame_and_wait(rec.main, samples / "sample flames" / "candy.flame", 0)
    rec.main.document.set_coloring(gamma=2.0)
    settle_recorder()
    assert "# (switched to 'original' — not recorded)" in rec.editor.text() and code_lines(rec) == ["coloring.gamma = 2.0"]
    rec.set_recording(False)


def test_the_editor_keeps_its_focus_and_undoes_one_statement_at_a_time(rec):
    rec.set_recording(True)
    doc = rec.main.document
    doc.set_coloring(gamma=2.0)
    doc.set_coloring(gamma=2.4)
    settle_recorder()
    doc.set_view(zoom=1.0)
    settle_recorder()
    rec.set_recording(False)
    assert code_lines(rec) == ["coloring.gamma = 2.4", "camera.zoom = 1.0"]
    rec.editor.undo()
    assert code_lines(rec) == ["coloring.gamma = 2.4"]
    rec.editor.undo()
    assert code_lines(rec) == []


def test_recording_on_the_untouched_default_script_starts_a_recorded_script(rec):
    from fractalchemy.ui.script_editor_window import DEFAULT_SCRIPT
    rec.load_code(DEFAULT_SCRIPT, "untitled")
    rec.set_recording(True)
    assert rec.editor.text().startswith("# @name Recorded script") and rec.script_name == "Recorded script"
    rec.set_recording(False)


def test_relative_style_and_console_lines(rec):
    doc = rec.main.document
    start = doc.flame.copy()
    rec.set_record_style("relative")
    rec.set_recording(True)
    doc.set_view(zoom=doc.flame.camera.zoom + 0.5)
    settle_recorder()
    rec.console.line.set_text("transforms[0].rotate(10)")
    rec.run_console("transforms[0].rotate(10)")
    wait_until(lambda: not rec.running)
    settle_recorder()
    lines = code_lines(rec)
    assert lines == ["camera.zoom += 0.5", "transforms[0].rotate(10)"]
    rec.set_recording(False)
    rec.set_record_style("absolute")
    replayed = run_script(rec.editor.text(), start, None, threading.Event()).flame
    assert flame_differences(replayed, doc.flame) == []
