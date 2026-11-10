"""The Script Editor's live parameters: the Parameters tab, re-runs from the snapshot as one undo step, the session
ending when the fractal changes elsewhere, Run superseding a re-run, side effects keeping a script inert, and baking
values into the code."""

import threading

import pytest

from fractalchemy import config
from fractalchemy.machines import LiveState, ScriptState
from fractalchemy.scripting.runner import run_script
from fractalchemy.scripting.codegen import flame_differences
from tests.conftest import open_flame_and_wait, spin, wait_until

ROTATE = ("# @name Live rotate\n"
          "angle = param('Angle', 30, min=-180, max=180)\n"
          "jitter = param('Jitter', 0.0, min=0, max=1)\n"
          "keep = param('Keep colours', True)\n"
          "for t in transforms:\n"
          "    t.rotate(angle + random(-1, 1) * jitter * 10)\n"
          "    if not keep:\n"
          "        t.color = 0.5\n"
          "print('rotated', angle)\n")


@pytest.fixture
def editor(main_window_factory, samples, monkeypatch):
    monkeypatch.setattr(config, "SCRIPT_LIVE_DEBOUNCE_MS", 20)
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    ed = win.script_editor
    ed.bring_to_front()
    ed.main = win
    yield ed
    ed.live.unload()


def finish(editor, timeout=15000) -> None:
    wait_until(lambda: not editor.running, timeout)


def settle(editor) -> None:
    """Wait until the live session has nothing pending or running."""
    wait_until(lambda: editor.live.state not in (LiveState.PENDING, LiveState.RERUNNING, LiveState.QUEUED) and not editor.running)


def run(editor, code=ROTATE) -> None:
    editor.editor.set_text(code)
    editor.run()
    finish(editor)


def test_a_run_that_declares_parameters_fills_the_tab_and_goes_live(editor):
    run(editor)
    tab = editor.drawer.parameters
    assert list(tab.rows) == ["Angle", "Jitter", "Keep colours"] and editor.live.state == LiveState.READY
    assert editor.drawer.currentWidget() is tab and "Live" in tab.status_text()
    assert tab.rows["Angle"].float_row is not None and tab.rows["Angle"].value() == 30
    assert "3 parameters (live)" in editor.drawer.info.browser.toPlainText()


def test_moving_a_control_re_runs_from_the_snapshot_as_the_same_undo_step(editor):
    before = editor.main.document.flame.copy()
    run(editor)
    steps = len(editor.main.document._undo)
    for angle in (45, 60, 90):
        editor.drawer.parameters.rows["Angle"].float_row.spin.setValue(angle)
        settle(editor)
    session = editor.live.session
    expected = run_script(ROTATE, before, None, threading.Event(), seed=session.seed, parameters={"Angle": 90}).flame
    assert flame_differences(editor.main.document.flame, expected) == []
    assert len(editor.main.document._undo) == steps                  # still the run's one step
    assert "↻ Live: Angle = 90" in editor.output.toPlainText() and "rotated 90" in editor.output.toPlainText()
    editor.main.document.undo()
    assert flame_differences(editor.main.document.flame, before) == [] and editor.live.state == LiveState.DETACHED


def test_changes_during_a_re_run_queue_exactly_one_more_with_the_latest_values(editor, monkeypatch):
    slow = ROTATE.replace("print('rotated', angle)\n", "import time\n") + "x = 0\nfor i in range(300000):\n    x += i\n"
    run(editor, ROTATE.replace("print('rotated', angle)\n", "") + "x = 0\nfor i in range(200000):\n    x += i\n")
    starts = []
    original = editor.start_rerun
    monkeypatch.setattr(editor, "start_rerun", lambda *a: starts.append(a[3]["Angle"]) or original(*a))
    rows = editor.drawer.parameters.rows
    rows["Angle"].float_row.spin.setValue(40)
    wait_until(lambda: editor.live.state == LiveState.RERUNNING)
    for angle in (41, 42, 43):
        rows["Angle"].float_row.spin.setValue(angle)
    assert editor.live.state == LiveState.QUEUED
    settle(editor)
    assert starts == [40, 43] and editor.live.state == LiveState.READY
    assert slow                                                        # (kept for readability of the scenario)


def test_an_edit_elsewhere_detaches_the_session(editor):
    run(editor)
    editor.main.document.set_coloring(gamma=2.0)
    assert editor.live.state == LiveState.DETACHED and "press Run" in editor.drawer.parameters.status_text()
    flame = editor.main.document.flame.copy()
    editor.drawer.parameters.rows["Angle"].float_row.spin.setValue(120)   # only remembered for the next Run
    spin(100)
    assert flame_differences(editor.main.document.flame, flame) == [] and editor.live.values_for_run() == {"Angle": 120}
    editor.run()
    finish(editor)
    assert editor.live.state == LiveState.READY and editor.live.session.code == ROTATE


def test_run_during_a_re_run_supersedes_it(editor):
    code = ROTATE + "x = 0\nfor i in range(400000):\n    x += i\n"
    run(editor, code)
    editor.drawer.parameters.rows["Angle"].float_row.spin.setValue(10)
    wait_until(lambda: editor.run_state.state == ScriptState.RERUNNING)
    assert editor.actionRun.isEnabled()
    editor.run()
    assert editor.run_state.state == ScriptState.SUPERSEDED
    finish(editor, 30000)
    assert "▶ Running Live rotate" in editor.output.toPlainText().split("↻")[-1] or editor.output.toPlainText().count("▶ Running") == 2
    assert editor.live.state == LiveState.READY and editor.run_state.state == ScriptState.IDLE


def test_an_error_keeps_the_last_good_fractal_and_recovers(editor):
    code = ROTATE.replace("print('rotated', angle)\n", "print(1 / angle)\n")
    run(editor, code)
    rows = editor.drawer.parameters.rows
    rows["Angle"].float_row.spin.setValue(50)
    settle(editor)
    good = editor.main.document.flame.copy()
    rows["Angle"].float_row.spin.setValue(0)
    settle(editor)
    assert flame_differences(editor.main.document.flame, good) == [] and "ZeroDivisionError" in editor.drawer.parameters.error.text()
    assert editor.live.state == LiveState.READY
    rows["Angle"].float_row.spin.setValue(70)
    settle(editor)
    assert not editor.drawer.parameters.error.isVisible() and flame_differences(editor.main.document.flame, good) != []


def test_side_effects_keep_a_script_inert_and_nothing_is_written(editor, tmp_path):
    out = tmp_path / "out.flame"
    code = (f"save = param('Save', False)\nangle = param('Angle', 10, min=0, max=90)\n"
            f"transforms[0].rotate(angle)\nif save:\n    save_flame(r'{out}')\n")
    run(editor, code)
    assert editor.live.state == LiveState.READY
    editor.drawer.parameters.rows["Save"].editor.setChecked(True)
    settle(editor)
    assert editor.live.state == LiveState.INERT and not out.exists() and "writes files" in editor.drawer.parameters.status_text()
    editor.run()                                                     # Run applies the values, side effects included
    finish(editor)
    assert out.exists() and editor.live.state == LiveState.INERT
    run(editor, "import os\nn = param('N', 2, min=1, max=5)\n")
    assert editor.live.state == LiveState.INERT and "imports os" in editor.drawer.parameters.status_text()


def test_set_as_defaults_rewrites_the_code_and_templates_offer_it(editor, monkeypatch):
    from fractalchemy.ui import script_editor_window as SEW
    run(editor)
    editor.drawer.parameters.rows["Angle"].float_row.spin.setValue(75)
    settle(editor)
    editor.live.bake()
    assert "param('Angle', 75, min=-180, max=180)" in editor.editor.text() and editor.live.values_for_run() == {}
    assert not editor.drawer.parameters.banner.isVisible()            # the session's code follows the baked text
    editor.editor.undo()
    assert "param('Angle', 30," in editor.editor.text()
    asked = []
    monkeypatch.setattr(SEW.QMessageBox, "exec", lambda self: asked.append(self.text()) or 0)
    editor.drawer.parameters.rows["Jitter"].float_row.spin.setValue(0.5)
    settle(editor)
    monkeypatch.setattr(SEW.QInputDialog, "getText", lambda *a, **k: ("", False))
    editor.save_as_template()
    assert asked and "current parameter values" in asked[0]


def test_values_persist_with_the_draft_and_feed_the_next_run(editor):
    run(editor)
    editor.drawer.parameters.rows["Angle"].float_row.spin.setValue(-45)
    settle(editor)
    from fractalchemy.ui.script_live import VALUES_KEY
    assert '"Angle": -45' in editor.settings.value(VALUES_KEY)
    editor.run()
    finish(editor)
    assert "rotated -45" in editor.output.toPlainText()
    editor.load_code("print(1)\n", "other")
    assert editor.live.state == LiveState.OFF and editor.drawer.parameters.rows == {} and editor.live.values_for_run() == {}


def test_scripts_without_parameters_behave_as_before(editor):
    run(editor, "camera.zoom = 1.5\nprint('done')\n")
    assert editor.live.state == LiveState.OFF and editor.drawer.currentWidget() is not editor.drawer.parameters
    assert not editor.drawer.parameters.empty.isHidden() and len(editor.main.document._undo) == 1


def test_a_new_seed_re_runs_and_keep_seed_repeats_runs(editor):
    run(editor)
    editor.drawer.parameters.rows["Jitter"].float_row.spin.setValue(1.0)
    settle(editor)
    first = editor.main.document.flame.copy()
    seed = editor.live.session.seed
    editor.drawer.parameters.reseed_button.click()
    settle(editor)
    assert editor.live.session.seed != seed and flame_differences(editor.main.document.flame, first) != []
    editor.drawer.parameters.keep_seed.setChecked(True)
    kept = editor.live.session.seed
    editor.main.document.undo()
    editor.run()
    finish(editor)
    assert editor.live.session.seed == kept
