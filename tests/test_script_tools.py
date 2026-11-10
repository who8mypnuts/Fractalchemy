"""The script features around the Script Editor: the console, pinned templates in the main window, the explorer grid,
animating a parameter, and running a script on many fractals."""

import threading

import pytest

from fractalchemy import config
from fractalchemy.fractal.formats import flame_names, load_flames
from fractalchemy.machines import LiveState, OffspringState
from fractalchemy.scripting.codegen import flame_differences
from fractalchemy.scripting.runner import run_script
from tests.conftest import open_flame_and_wait, spin, wait_until

LIVE = ("# @name Live turn\n"
        "angle = param('Angle', 30, min=-180, max=180)\n"
        "for t in transforms:\n"
        "    t.rotate(angle)\n")


@pytest.fixture
def win(main_window_factory, samples, monkeypatch):
    monkeypatch.setattr(config, "SCRIPT_LIVE_DEBOUNCE_MS", 20)
    window = main_window_factory()
    open_flame_and_wait(window, samples / "sample flames" / "candy.flame", 2)
    return window


def finish(editor, timeout=20000):
    wait_until(lambda: not editor.running, timeout)


def run_live(win, code=LIVE):
    editor = win.script_editor
    editor.editor.set_text(code)
    editor.run()
    finish(editor)
    return editor


# --- the console ----------------------------------------------------------------------------------------------------------
def test_the_console_echoes_carries_variables_and_makes_one_step_per_changing_line(win):
    editor = win.script_editor
    doc = win.document
    editor.run_console("len(transforms)")
    finish(editor)
    assert "6" in editor.output.toPlainText().split(">>> len(transforms)")[-1] and not doc.can_undo
    editor.run_console("z = 1.5")
    finish(editor)
    editor.run_console("camera.zoom = z")
    finish(editor)
    assert doc.flame.camera.zoom == 1.5 and doc.undo_label == "Console: camera.zoom = z" and len(doc._undo) == 1
    editor.run_console("print(1 / 0)")
    finish(editor)
    assert "ZeroDivisionError" in editor.output.toPlainText()
    assert editor.console.line.history[-3:] == ["z = 1.5", "camera.zoom = z", "print(1 / 0)"]
    editor.console.line._walk(-1)
    assert editor.console.line.text() == "print(1 / 0)"


# --- pinned templates ---------------------------------------------------------------------------------------------------------
def test_pinned_templates_run_from_the_main_window_without_touching_the_editor(win):
    editor = win.script_editor
    editor.editor.set_text("print('mine')\n")
    template = next(t for t in editor.all_templates() if t.name == "Warm / cool shift")
    editor.drawer.templates.select(template.id)
    editor.drawer.templates.pin_button.click()
    assert editor.pins.is_pinned(template) and "★" in " ".join(editor.drawer.templates.visible_names())
    win.scripts.menu.rebuild()
    pinned = next(a for a in win.scripts.menu.actions() if a.text() == "Warm / cool shift")
    before = win.document.flame.copy()
    pinned.trigger()
    finish(editor)
    assert editor.editor.text() == "print('mine')\n" and win.document.undo_label == "Script: Warm / cool shift"
    assert win.document.flame.palette != before.palette and "(from the Scripts menu)" in editor.output.toPlainText()
    assert not editor.drawer.parameters.banner.isVisible()
    editor.drawer.parameters.rows["Hue"].float_row.spin.setValue(-40)
    wait_until(lambda: editor.live.state == LiveState.READY and not editor.running)
    assert editor.pins.pins[0].values == {"Hue": -40}
    win.scripts.menu.rebuild()
    assert next(a for a in win.scripts.menu.actions() if a.text() == "Adjust Parameters…").isEnabled()


# --- the explorer grid ------------------------------------------------------------------------------------------------------
def test_the_explore_tab_varies_the_live_script_and_adopting_keeps_one_undo_step(win):
    window = win.mutation_window
    window.show()
    window.show_exploring()
    window.regenerate()
    assert window.state == OffspringState.NEEDS_SCRIPT
    editor = run_live(win)
    steps = len(win.document._undo)
    editor.explore_requested.emit()
    wait_until(lambda: window.state == OffspringState.READY and window.variants, 30000)
    cell = next(c for c in window.offspring)
    variant = window.variants[cell].variant
    assert window.adopt(cell)
    wait_until(lambda: editor.live.state == LiveState.READY and not editor.running)
    assert editor.live.values["Angle"] == variant.values["Angle"] and len(win.document._undo) == steps
    expected = run_script(LIVE, editor.live.session.snapshot, None, threading.Event(), seed=variant.seed,
                          parameters=variant.values).flame
    assert flame_differences(win.document.flame, expected) == []
    window.close()


# --- animating a parameter --------------------------------------------------------------------------------------------------
def test_animate_creates_a_keyframe_per_value(win, monkeypatch):
    from fractalchemy.ui.script_animate import AnimateParameterDialog
    code = LIVE.replace("param('Angle', 30,", "param('Angle', 30.0,")
    editor = run_live(win, code)
    dialog = AnimateParameterDialog(editor.live, "Angle", win.animation, editor)
    dialog.start_box.setValue(0)
    dialog.end_box.setValue(90)
    dialog.count_box.setValue(4)
    dialog.target_box.setCurrentIndex(1)                        # a new animation
    monkeypatch.setattr(win.animation, "confirm_discard", lambda: True)
    dialog.create()
    wait_until(lambda: dialog.result_count == 4, 30000)
    keyframes = win.animation.document.animation.keyframes
    assert [k.name for k in keyframes] == ["Angle = 0", "Angle = 30", "Angle = 60", "Angle = 90"]
    expected = run_script(code, editor.live.session.snapshot, None, threading.Event(), seed=editor.live.session.seed,
                          parameters={"Angle": 60.0}).flame
    assert flame_differences(keyframes[2].flame, expected) == []
    ints = AnimateParameterDialog(run_live(win).live, "Angle", win.animation, editor)     # an integer: one keyframe per value
    ints.start_box.setValue(2)
    ints.end_box.setValue(5)
    assert [v for _f, v in ints.plan()] == [2, 3, 4, 5] and not ints.count_box.isEnabled()


# --- many fractals -------------------------------------------------------------------------------------------------------------
def test_run_a_script_on_every_flame_of_a_file(win, samples, tmp_path):
    import shutil
    source = tmp_path / "candy.flame"
    shutil.copy(samples / "sample flames" / "candy.flame", source)
    original = source.read_bytes()
    run_live(win)
    window = win.scripts.batch_window
    win.scripts.show_batch()
    window.source_file.setText(str(source))
    window.source_buttons["file"].setChecked(True)
    output = tmp_path / "results.fa"
    window.output_path.setText(str(output))
    window.names_box.setCurrentText("{name} · {script}")
    assert window.start_button.isEnabled()
    window.start()
    wait_until(lambda: window.last_outcome is not None and window.job is None, 60000)
    outcome = window.last_outcome
    assert outcome.succeeded == 5 and outcome.failed == 0 and not outcome.stopped
    assert flame_names(output)[0] == "original · Live turn" and source.read_bytes() == original
    flames = load_flames(output)
    first = load_flames(source)[0]
    expected = run_script(LIVE, first, None, threading.Event(), parameters={}).flame
    assert flame_differences(flames[0], expected) == []
    window.output_path.setText(str(source))
    assert not window.start_button.isEnabled() and "cannot go into the file" in window.start_button.toolTip()
    window.close()


def test_the_library_menu_offers_run_script_on_selection(main_window_factory, samples):
    from fractalchemy.library.items import Kind
    window = main_window_factory(samples / "sample flames")
    model = window.fractalLibraryPanel.model
    wait_until(lambda: any(i.kind == Kind.FILE for i in model.entries()))
    item = next(i for i in model.entries() if i.kind == Kind.FILE)
    menu = window.fractal_menu.build(item, [item])
    action = next(a for a in menu.actions() if a.text() == "Run Script on Selection…")
    window.fractalLibraryPanel.tree.selected_items = lambda: [item]
    action.trigger()
    batch = window.scripts.batch_window
    assert batch.source_key() == "selection" and batch.sources() == [(item.path, None)]
    batch.close()


def test_random_batch_window_offers_symmetry(win):
    win.show_random_batch_window()
    window = win._random_window
    window.symmetry_box.setCurrentIndex(window.symmetry_box.findData("rotational"))
    window.order_min.setValue(3)
    window.order_max.setValue(5)
    options = window.options()
    assert options.symmetry == "rotational" and options.symmetry_orders == (3, 5) and window.order_min.isEnabled()
    window.symmetry_box.setCurrentIndex(0)
    assert not window.order_min.isEnabled() and window.options().symmetry == "none"
    spin(10)
