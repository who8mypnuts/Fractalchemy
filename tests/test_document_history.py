"""FractalDocument's announcements and undo history: `edited(kind)` once per change, no-op edits record nothing,
`modified` follows the saved position, labelled steps, `history()` / `jump_to()`, and the file actions on top."""

import math
import time

import pytest

from fractalchemy.fractal.formats import load_flame
from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.model import Gradient
from fractalchemy.ui import fractal_document as FD
from fractalchemy.ui.fractal_document import FractalDocument
from fractalchemy.ui.undo_labels import GENERIC_LABEL, is_specific, undo_label
from tests.conftest import wait_until


@pytest.fixture
def doc(qapp, samples):
    d = FractalDocument()
    path = samples / "sample flames" / "candy.flame"
    d.replace(load_flame(path, 2), path, 2)
    return d


def _spy(doc):
    """Every signal the document emits, in order, as (name, args)."""
    log = []
    for name in ("flame_replaced", "camera_changed", "palette_changed", "coloring_changed", "flame_restored", "xform_changed",
                 "transforms_changed", "edited"):
        getattr(doc, name).connect(lambda *args, n=name: log.append((n, args)))
    return log


MUTATORS = [
    # (call, expected kind, the specific signal that must come first)
    (lambda d: d.set_view(zoom=d.flame.camera.zoom + 1), "view", "camera_changed"),
    (lambda d: d.pan(0.1, 0.0), "view", "camera_changed"),
    (lambda d: d.pan_units(0.1, 0.0), "view", "camera_changed"),
    (lambda d: d.set_camera_3d(pitch=0.4), "camera3d", "camera_changed"),
    (lambda d: d.set_coloring(gamma=d.flame.coloring.gamma + 1), "coloring:gamma", "coloring_changed"),
    (lambda d: d.set_curve("red", [(0, 0), (0.5, 0.7), (1, 1)]), "curve:red", "coloring_changed"),
    (lambda d: d.set_gradient(Gradient.from_colors("g", [(1, 2, 3), (200, 100, 50)])), "palette", "palette_changed"),
    (lambda d: d.set_affine(0, "coefs", (0.5, 0.1, 0.0, 0.5, 0.2, 0.0)), "affine:coefs:0", "xform_changed"),
    (lambda d: d.set_affine(0, "pre", (1.1, 0.0, 0.0, 1.0, 0.0, 0.0)), "affine:pre:0", "xform_changed"),
    (lambda d: d.set_xform_fields(0, weight=0.77), "fields:weight:0", "xform_changed"),
    (lambda d: d.set_variation(0, "julian", 0.3), "variation:julian:0", "xform_changed"),
    (lambda d: d.clear_variations(1), "clear-variations:1", "xform_changed"),
    (lambda d: d.set_param(0, "julian_power", 5.0), "param:julian_power:0", "xform_changed"),
    (lambda d: d.set_chaos(0, 1, 0.0), "chaos:0:1", "xform_changed"),
    (lambda d: d.set_all_chaos(0, 0.0), "chaos-all:0", "xform_changed"),
    (lambda d: d.add_xform(), "add-xform", "transforms_changed"),
    (lambda d: d.duplicate_xform(0), "duplicate-xform", "transforms_changed"),
    (lambda d: d.add_linked_xform(0), "link-xform", "transforms_changed"),
    (lambda d: d.delete_xform(0), "delete-xform", "transforms_changed"),
    (lambda d: d.set_final_enabled(d.flame.final is None), "final-xform", "transforms_changed"),
    (lambda d: d.replace_flame_parameters(_zoomed(d.flame), "mutate"), "mutate", "flame_restored"),
    (lambda d: d.paste(_zoomed(d.flame)), "paste", "flame_restored"),
    (lambda d: d.apply_script(_zoomed(d.flame), object()), "script", "flame_restored"),
]


def _zoomed(flame: Flame) -> Flame:
    other = flame.copy()
    other.camera.zoom += 0.5
    return other


@pytest.mark.parametrize("call, kind, signal", MUTATORS, ids=[m[1] for m in MUTATORS])
def test_every_change_is_announced_once_after_its_own_signal_with_a_labelled_kind(doc, call, kind, signal):
    log = _spy(doc)
    call(doc)
    edited = [args[0] for name, args in log if name == "edited"]
    assert edited == [kind] and doc.last_edit_kind == kind
    names = [name for name, _args in log]
    assert signal in names and names.index(signal) < names.index("edited")
    assert is_specific(kind) and undo_label(kind) != GENERIC_LABEL and doc.undo_label == undo_label(kind)
    assert doc.modified and doc.can_undo


def test_area_weights_undo_redo_and_loading_are_announced_too(doc, samples):
    log = _spy(doc)
    doc.set_xform_fields(0, weight=3.0)
    doc.area_weights()
    doc.undo()
    doc.redo()
    doc.replace(load_flame(samples / "sample flames" / "candy.flame", 0))
    assert [a[0] for n, a in log if n == "edited"] == ["fields:weight:0", "area-weights", "undo", "redo", "load"]


@pytest.mark.parametrize("call", [
    lambda d: d.set_view(zoom=d.flame.camera.zoom),
    lambda d: d.set_view(center=d.flame.camera.center, rotate=d.flame.camera.rotate),
    lambda d: d.set_camera_3d(pitch=d.flame.camera.pitch),
    lambda d: d.set_coloring(gamma=d.flame.coloring.gamma, brightness=d.flame.coloring.brightness),
    lambda d: d.reset_curves(),
    lambda d: d.set_xform_fields(0, weight=d.flame.xforms[0].weight),
    lambda d: d.set_affine(0, "coefs", d.flame.xforms[0].coefs),
    lambda d: d.paste(d.flame.copy()),
    lambda d: d.apply_script(d.flame.copy(), object()),
    lambda d: d.replace_flame_parameters(d.flame.copy()),
    lambda d: d.revert_view(),
])
def test_edits_that_change_nothing_record_and_announce_nothing(doc, call):
    log = _spy(doc)
    call(doc)
    assert log == [] and not doc.can_undo and not doc.modified


def test_modified_follows_the_saved_position(doc):
    changes = []
    doc.modified_changed.connect(changes.append)
    doc.set_coloring(gamma=2.0)
    doc.set_view(zoom=3.0)
    assert doc.modified
    doc.undo()
    doc.undo()
    assert not doc.modified and doc.can_redo                    # back at the loaded state: no `*`
    doc.redo()
    assert doc.modified
    doc.mark_saved()
    assert not doc.modified and doc.saved_position == 1
    doc.redo()
    assert doc.modified
    doc.undo()
    assert not doc.modified                                     # the saved state again
    doc.undo()
    doc.set_coloring(brightness=9.0)                            # branches away: the saved state is gone for good
    assert doc.saved_position is None and doc.modified
    assert changes == [True, False, True, False, True, False, True]


def test_saving_starts_a_new_step_so_undo_returns_to_the_saved_state(doc):
    doc.set_coloring(gamma=2.0)
    doc.mark_saved()
    doc.set_coloring(gamma=2.5)                                 # same kind, within the coalescing window
    assert len(doc._undo) == 2 and doc.modified
    doc.undo()
    assert doc.flame.coloring.gamma == 2.0 and not doc.modified


def test_history_lists_the_steps_with_labels_and_jump_to_restores_once(doc):
    FD.UNDO_COALESCE_SECONDS, saved = 0.0, FD.UNDO_COALESCE_SECONDS
    try:
        doc.set_coloring(gamma=2.0)
        doc.set_view(zoom=1.0)
        doc.set_variation(1, "julian", 0.5)
        doc.undo()
    finally:
        FD.UNDO_COALESCE_SECONDS = saved
    entries = doc.history()
    assert [e.label for e in entries] == ["Opened candy.flame #3", "Gamma", "Camera", "julian on 2"]
    assert [e.position for e in entries] == [0, 1, 2, 3] and doc.history_position == 2
    assert doc.undo_label == "Camera" and doc.redo_label == "julian on 2"
    restored = []
    doc.flame_restored.connect(lambda: restored.append(1))
    assert doc.jump_to(0) and restored == [1] and doc.flame.coloring.gamma != 2.0 and not doc.modified
    assert doc.jump_to(3) and restored == [1, 1] and doc.flame.xforms[1].variations.get("julian") == 0.5
    assert not doc.jump_to(3)                                   # already there
    assert [e.label for e in doc.history()][1:] == ["Gamma", "Camera", "julian on 2"]


def test_a_script_result_after_another_edit_records_its_own_step(doc):
    run = object()
    first = _zoomed(doc.flame)
    doc.apply_script(first, run)                                # an update() of a running script
    doc.set_coloring(gamma=7.0)                                 # the user edits meanwhile
    final = doc.flame.copy()
    final.camera.rotate = 33.0
    doc.apply_script(final, run)                                # the run's result
    assert len(doc._undo) == 3
    doc.undo()
    assert doc.flame.coloring.gamma == 7.0 and doc.flame.camera.rotate != 33.0


def test_interactive_script_results_flag_live_edit_while_they_are_announced(doc):
    seen = []
    doc.flame_restored.connect(lambda: seen.append(doc.live_edit))
    doc.apply_script(_zoomed(doc.flame), object(), interactive=True)
    doc.apply_script(_zoomed(doc.flame), object())
    assert seen == [True, False] and not doc.live_edit


def test_script_steps_carry_their_label(doc):
    doc.apply_script(_zoomed(doc.flame), object(), label=undo_label("script", "Random rotate"))
    assert doc.undo_label == "Script: Random rotate"


def test_rename_and_restore_unsaved(doc, samples):
    renamed = []
    doc.flame_renamed.connect(lambda: renamed.append(doc.flame.name))
    doc.rename("pearl")
    doc.rename("pearl")
    assert renamed == ["pearl"] and not doc.modified and not doc.can_undo
    path = samples / "sample flames" / "candy.flame"
    doc.restore_unsaved(load_flame(path, 0), path, 0, "Recovered candy")
    assert doc.modified and doc.source_path == path and doc.history()[0].label == "Recovered candy"


def test_the_history_is_capped_and_the_saved_position_follows(doc):
    FD.UNDO_COALESCE_SECONDS, saved = 0.0, FD.UNDO_COALESCE_SECONDS
    FD.UNDO_LIMIT, limit = 5, FD.UNDO_LIMIT
    try:
        doc.set_coloring(gamma=1.5)
        doc.mark_saved()                                        # saved at depth 1
        for i in range(6):
            doc.set_view(zoom=float(i + 1))
        assert len(doc._undo) == 5 and doc.saved_position is None and doc.history()[0].label == "Earlier edits"
    finally:
        FD.UNDO_COALESCE_SECONDS, FD.UNDO_LIMIT = saved, limit


def test_every_kind_the_editors_produce_has_a_specific_label():
    kinds = ["view", "camera3d", "coloring:gamma", "coloring:brightness,gamma", "curve:red", "curves-reset", "palette", "paste",
             "script", "affine:post:2", "drag:coefs:1:4", "rotate:coefs:0:7", "move:pre:None:2", "reset-rotation:coefs:1:3",
             "reset-corner:coefs:0:1", "paste:2:12345", "corner:1:0", "vector:post:2:1", "fields:weight:0", "fields:color,weight:None",
             "variation:julian:1", "set-variations:0:julian", "clear-variations:0", "param:julian_power:1", "chaos:0:2",
             "chaos-all:1", "add-xform", "duplicate-xform", "link-xform", "delete-xform", "final-xform", "area-weights", "mutate",
             "breed", "new-flame", "reset-all", "use-current", "rig:Formula alone"]
    for kind in kinds:
        assert is_specific(kind) and undo_label(kind) != GENERIC_LABEL, kind
    assert undo_label("affine:post:2") == "Post-affine 3" and undo_label("rotate:coefs:None:1") == "Rotate triangle final"
    assert undo_label("coloring:brightness,gamma") == "Colouring" and undo_label("chaos:0:2") == "Xaos 1 → 3"
    assert undo_label("somethingnew") == GENERIC_LABEL and undo_label("script", "x") == "Script: x"


# --- the main window: action texts, file actions, the quit prompt ------------------------------------------------------
def test_undo_and_redo_actions_name_their_steps(main_window_factory, samples):
    from tests.conftest import open_flame_and_wait
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    assert win.actionUndo.text() == "Undo" and not win.actionUndo.isEnabled()
    win.document.set_coloring(gamma=2.0)
    assert win.actionUndo.text() == "Undo Gamma" and win.actionUndo.isEnabled()
    win.document.undo()
    assert win.actionRedo.text() == "Redo Gamma" and win.actionUndo.text() == "Undo"
    assert win.editor.actions.undo.text() == "Undo"


def test_saving_moves_the_document_to_the_written_entry_without_touching_its_flame(main_window_factory, samples, tmp_path, monkeypatch):
    import shutil

    from fractalchemy.ui import fractal_file_actions as FA
    from tests.conftest import open_flame_and_wait
    target = tmp_path / "candy.flame"
    shutil.copy(samples / "sample flames" / "candy.flame", target)
    win = main_window_factory()
    open_flame_and_wait(win, target, 2)
    written = []
    win.files.entry_written.connect(lambda path, index: written.append((path, index)))
    win.document.set_coloring(gamma=2.5)
    collection = tmp_path / "collection.fa"
    monkeypatch.setattr(FA.QFileDialog, "getSaveFileName", lambda *a, **k: (str(collection), ""))
    assert win.files.save_as_new_file()
    wait_until(lambda: written)
    assert written == [(collection, 0)] and win.document.source_path == collection and not win.document.modified
    assert win.files.wrote_recently(collection) and load_flame(collection, 0).coloring.gamma == 2.5


@pytest.mark.quit_prompt
def test_quitting_with_unsaved_fractal_edits_asks(main_window_factory, samples, monkeypatch):
    from fractalchemy.ui import file_actions_base
    from tests.conftest import open_flame_and_wait
    win = main_window_factory()
    open_flame_and_wait(win, samples / "sample flames" / "candy.flame", 2)
    asked = []
    monkeypatch.setattr(file_actions_base.QMessageBox, "question",
                        lambda *a, **k: asked.append(a[2]) or file_actions_base.QMessageBox.StandardButton.Cancel)
    assert win.close()                                          # nothing edited: no question
    assert asked == []
    win.show()
    win.document.set_coloring(gamma=2.5)
    assert not win.close() and win.isVisible() and "unsaved changes" in asked[0]
    monkeypatch.setattr(file_actions_base.QMessageBox, "question", lambda *a, **k: file_actions_base.QMessageBox.StandardButton.Discard)
    assert win.close()


def test_flame_to_script_rebuilds_every_field(samples):
    import random
    import threading

    from fractalchemy.fractal import mutation as M
    from fractalchemy.scripting.codegen import flame_differences
    from fractalchemy.scripting.generate import flame_to_script
    from fractalchemy.scripting.runner import run_script
    flames = []
    for name, index in (("candy.flame", 2), ("flamepack1.flame", 5), ("satania_spikobius.chaos", 0)):
        base = load_flame(samples / "sample flames" / name, index)
        flames += [base] + [M.mutate(base, random.Random(seed), M.MutationOptions()).flame for seed in range(4)]
    synthetic = flames[0].copy()
    synthetic.xforms[0].pre = (1.1, 0.1, 0.0, 0.9, 0.2, -0.1)
    synthetic.xforms[1].post = (0.9, 0.0, 0.1, 1.0, 0.0, 0.3)
    synthetic.xforms[0].opacity, synthetic.xforms[0].var_color, synthetic.xforms[0].name = 0.4, 0.5, "centre"
    synthetic.coloring.curves.set_points("overall", [(0, 0), (0.5, 0.7), (1, 1)])
    synthetic.camera.pitch, synthetic.camera.yaw, synthetic.camera.perspective = 0.3, math.radians(20), 0.2
    synthetic.final = XForm(color_speed=0.0, coefs=(0.9, 0.0, 0.0, 0.9, 0.0, 0.0), pre=(1.0, 0.2, 0.0, 1.0, 0.0, 0.0))
    flames.append(synthetic)
    for flame in flames:
        result = run_script(flame_to_script(flame), Flame("empty", []), None, threading.Event())
        assert result.ok, result.error
        assert flame_differences(result.flame, flame) == [], flame.name


def test_codegen_numbers_are_short_but_exact_enough():
    from fractalchemy.scripting.codegen import coord, num
    assert num(3.5) == "3.5" and num(2.0) == "2.0" and num(12) == "12" and num(0.1 + 0.2) == "0.3"
    assert float(num(math.radians(17.3))) == pytest.approx(math.radians(17.3), rel=1e-9)
    assert num(1e-12) == "1e-12" and num(float("inf")) == "float('inf')"
    assert coord(0.123456789, 1e-3) == "0.1235" and coord(0.123456789012, 1e-9) == "0.123456789"


def test_the_api_reads_and_writes_pre_affines_and_curves():
    import threading

    from fractalchemy.scripting.runner import run_script
    code = ("t = add_transform(pre=(1, 0.1, 0, 1, 0, 0))\n"
            "transform.pre.e = 0.25\n"
            "coloring.set_curve('red', [(1, 1), (0, 0), (0.5, 0.6)])\n"
            "print(coloring.curve('red'), transform.pre.coefs)\n")
    result = run_script(code, Flame("x", [XForm()]), None, threading.Event())
    assert result.ok, result.error
    assert result.flame.xforms[1].pre == pytest.approx((1, 0.1, 0, 1, 0.25, 0))
    assert result.flame.coloring.curves.points["red"] == [(0.0, 0.0), (0.5, 0.6), (1.0, 1.0)]
    bad = run_script("coloring.set_curve('purple', [(0, 0), (1, 1)])", Flame("x", [XForm()]), None, threading.Event())
    assert not bad.ok and "curve channel" in bad.error.message


def test_time_of_steps_is_recorded(doc):
    before = time.time()
    doc.set_coloring(gamma=2.0)
    assert doc.history()[1].time >= before
