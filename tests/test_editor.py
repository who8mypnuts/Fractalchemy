"""The Transform Editor: triangle geometry, transform operations, the pre affine, the document's transform edits,
and the editor window driven through its widgets and the mouse."""

import math
from pathlib import Path

import numpy as np
import pytest
from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QGuiApplication, QMouseEvent
from PySide6.QtWidgets import QApplication

from fractalchemy import config
from fractalchemy.fractal import triangles as T
from fractalchemy.fractal import xform_ops
from fractalchemy.fractal.formats import flame_from_text, flame_to_text
from fractalchemy.fractal.formats.chaos_writer import flame_to_ifs
from fractalchemy.fractal.formats.flame_xml import flame_to_xml, parse_text
from fractalchemy.fractal.scene import Flame, XForm, apply_affine, compose_affine, identity_affine
from fractalchemy.render.compiled import CompiledFlame
from fractalchemy.render.cpu_engine import CpuEngine, apply_xform
from fractalchemy.render.gpu_engine import gpu_available
from fractalchemy.render.settings import RenderSettings
from fractalchemy.ui.editor_context import MODE_NORMAL, MODE_POST, MODE_PRE
from fractalchemy.ui.editor_window import parse_triangle_text
from fractalchemy.ui.fractal_document import FractalDocument
from fractalchemy.widgets.triangle_view import MODE_MOVE, MODE_ROTATE, MODE_SCALE, PIVOT_WORLD
from tests.conftest import open_flame_and_wait, spin, wait_for_render, wait_until

SAMPLE = Path(__file__).resolve().parents[1] / "samples" / "sample flames" / "candy.flame"


# --- geometry -------------------------------------------------------------------------------------------------
def test_triangle_and_affine_are_inverse_and_corners_are_unit_vector_images():
    rng = np.random.default_rng(3)
    for _ in range(50):
        coefs = tuple(float(v) for v in rng.uniform(-2, 2, 6))
        triangle = T.affine_to_triangle(coefs)
        assert np.allclose(T.triangle_to_affine(triangle), coefs)
        for corner, unit in zip(triangle, T.REFERENCE):
            fx, fy = apply_affine(coefs, *T.to_fractal(unit))   # the corners are where the affine sends X, O, Y
            assert np.allclose(T.to_editor((fx, fy)), corner)
    assert T.is_reference(T.affine_to_triangle(identity_affine()))
    assert T.triangle_to_affine(T.REFERENCE) == identity_affine()
    assert T.editor_affine((1, 2, 3, 4, 5, 6)) == (1, -2, -3, 4, 5, -6)


def test_triangle_operations_rotate_scale_flip_reset_and_hit_test():
    tri = T.affine_to_triangle((0.5, 0, 0, 0.5, 1.0, 0.0))   # half size at x = 1
    assert np.allclose(T.rotate_about(tri, (0, 0), math.pi / 2)[T.CORNER_O], (0, 1))
    assert np.allclose(T.scale_about(tri, tri[T.CORNER_O], 2.0)[T.CORNER_X], (2.0, 0.0))
    assert np.allclose(T.flip_horizontal(tri)[T.CORNER_O], (-1.0, 0.0)) and np.allclose(T.flip_vertical(tri)[T.CORNER_Y], (1.0, -0.5))
    assert np.allclose(T.translate(tri, 1, 1)[T.CORNER_O], (2, 1))
    assert T.reset_corner(tri, T.CORNER_O) == T.affine_to_triangle((0.5, 0, 0, 0.5, 0, 0))
    assert np.allclose(T.reset_corner(tri, T.CORNER_X)[T.CORNER_X], (2.0, 0.0))
    turned = T.rotate_about(tri, tri[T.CORNER_O], math.radians(80))
    assert np.allclose(T.snap_rotation(turned), T.rotate_about(tri, tri[T.CORNER_O], math.pi / 2))
    assert np.allclose(T.reset_scale(turned)[T.CORNER_X], (1 + math.cos(math.radians(80)), math.sin(math.radians(80))))
    assert np.allclose(T.reset_corner_scale(tri, T.CORNER_Y)[T.CORNER_Y], (1.0, 1.0))
    # O moves the whole triangle when the axes are locked, alone otherwise
    assert T.move_corner(tri, T.CORNER_O, (0, 0), lock_axes=True) == T.affine_to_triangle((0.5, 0, 0, 0.5, 0, 0))
    assert T.move_corner(tri, T.CORNER_O, (0, 0))[T.CORNER_X] == tri[T.CORNER_X]
    assert T.contains(tri, (1.1, 0.1)) and not T.contains(tri, (1.4, 0.4))
    assert T.nearest_corner(tri, (1.48, 0.02), 0.05) == T.CORNER_X and T.nearest_corner(tri, (1.2, 0.2), 0.05) is None
    assert T.nearest_edge(tri, (1.25, 0.01), 0.03) == 0 and T.nearest_edge(tri, (1.25, 0.25), 0.03) == 2
    assert T.bounds([tri]) == (0.0, 0.0, 1.5, 0.5)
    assert math.isclose(T.area(tri), 0.125)
    assert np.allclose(T.local_point(tri, 1, 0), tri[T.CORNER_X]) and np.allclose(T.local_coords(tri, tri[T.CORNER_Y]), (0, 1))


# --- transform operations ------------------------------------------------------------------------------------
def test_xform_ops_keep_xaos_rows_consistent_when_adding_duplicating_linking_and_deleting():
    flame = Flame(xforms=[XForm(chaos=[1, 0, 1]), XForm(), XForm(chaos=[0, 1, 1])])
    assert xform_ops.add_xform(flame) == 3
    assert flame.xforms[0].chaos == [1, 0, 1, 1] and flame.xforms[1].chaos is None and flame.xforms[3].variations == {"linear": 1.0}
    assert xform_ops.duplicate_xform(flame, 0) == 4
    assert flame.xforms[0].chaos == [1, 0, 1, 1, 1] and flame.xforms[4].chaos == [1, 0, 1, 1, 1]
    assert flame.xforms[2].chaos == [0, 1, 1, 1, 0]            # the copy inherits the links *to* the original
    new = xform_ops.add_linked_xform(flame, 1)
    assert new == 5 and flame.xforms[1].chaos == [0, 0, 0, 0, 0, 1] and flame.xforms[1].opacity == 0.0
    assert flame.xforms[5].chaos == [1, 1, 1, 1, 1, 0] and flame.xforms[5].color_speed == 0.0
    assert all(x.chaos[5] == 0 for i, x in enumerate(flame.xforms) if i != 1)
    assert xform_ops.delete_xform(flame, 0) == 0 and len(flame.xforms) == 5
    assert flame.xforms[0].chaos == [0, 0, 0, 0, 1]                # was xform 1: its row lost column 0
    assert xform_ops.delete_xform(Flame(xforms=[XForm()]), 0) == 0   # the last transform stays
    xform_ops.set_final_enabled(flame, True)
    assert flame.final is not None and flame.final.color_speed == 0.0
    xform_ops.set_final_enabled(flame, False)
    assert flame.final is None
    xform_ops.area_weights(Flame(xforms=[XForm(coefs=(1, 0, 0, 1, 0, 0)), XForm(coefs=(0.5, 0, 0, 0.5, 0, 0))]))


# --- the pre affine ---------------------------------------------------------------------------------------------
def pre_flame() -> Flame:
    flame = Flame("pre", [XForm(coefs=(0.5, 0, 0, 0.5, 0, 0), color=0.0, variations={"linear": 0.6, "spherical": 0.4}),
                          XForm(coefs=(0.5, 0.1, -0.1, 0.5, 0.5, 0), color=0.5), XForm(coefs=(0.5, 0, 0, 0.5, 0, 0.5), color=1.0)])
    flame.xforms[1].pre = (0.8, 0.2, -0.3, 0.9, 0.1, -0.2)
    flame.camera.center, flame.camera.scale = (0.5, 0.5), 60
    flame.camera.width, flame.camera.height = 96, 64
    flame.coloring.brightness = 8
    return flame


def test_pre_affine_round_trips_through_fa_flame_xml_and_the_clipboard_and_chaotica_folds_it():
    flame = pre_flame()
    assert flame.xforms[1].has_pre() and not flame.xforms[0].has_pre()
    assert Flame.from_dict(flame.to_dict()).xforms[1].pre == flame.xforms[1].pre
    assert "pre" not in flame.to_dict()["xforms"][0]                       # identity pre affines are not written
    xml = flame_to_xml(flame)
    assert 'pre_affine="0.8 0.2 -0.3 0.9 0.1 -0.2"' in xml and xml.count("pre_affine") == 1
    back = parse_text(xml)[0]
    assert back.xforms[1].pre == flame.xforms[1].pre and not back.unsupported and back.xforms[1].variations == {"linear": 1.0}
    assert flame_from_text(flame_to_text(flame)).xforms[1].pre == flame.xforms[1].pre
    ifs = flame_to_ifs(flame)
    a, b, c, d, e, f = flame.xforms[1].combined_coefs()
    assert f'<real name="x_axis_length">{math.hypot(a, b)!r}</real>' in ifs and "pre_affine" not in ifs   # Chaotica gets the composed affine
    assert np.allclose(flame.xforms[1].combined_coefs(), compose_affine(flame.xforms[1].coefs, flame.xforms[1].pre))


def test_pre_affine_renders_exactly_like_the_composed_affine_on_the_cpu():
    flame = pre_flame()
    folded = flame.copy()
    folded.xforms[1].coefs = folded.xforms[1].combined_coefs()
    folded.xforms[1].pre = identity_affine()
    a, b = CompiledFlame.build(flame), CompiledFlame.build(folded)
    assert a.xforms[1].has_pre and not b.xforms[1].has_pre
    rng = np.random.default_rng(1)
    x, y = rng.uniform(-1, 1, 500), rng.uniform(-1, 1, 500)
    z, c = np.zeros(500), np.zeros(500)
    out_a = apply_xform(a.xforms[1], x, y, z, c, np.random.default_rng(2))
    out_b = apply_xform(b.xforms[1], x, y, z, c, np.random.default_rng(2))
    assert all(np.allclose(u, v) for u, v in zip(out_a, out_b))
    settings = RenderSettings(96, 64, passes=1, quality=30, points=4096, fuse=10)
    img_a = CpuEngine(threads=2).start(flame, settings).run_pass()
    img_b = CpuEngine(threads=2).start(folded, settings).run_pass()
    assert np.array_equal(img_a, img_b)


@pytest.mark.skipif(not gpu_available()[0], reason=f"no OpenGL: {gpu_available()[1]}")
def test_pre_affine_renders_exactly_like_the_composed_affine_on_the_gpu():
    from fractalchemy.render.gpu_engine import GpuEngine
    flame = pre_flame()
    folded = flame.copy()
    folded.xforms[1].coefs = folded.xforms[1].combined_coefs()
    folded.xforms[1].pre = identity_affine()
    engine = GpuEngine()
    settings = RenderSettings(96, 64, passes=1, quality=30, points=4096, fuse=10)
    try:
        img_a = engine.start(flame, settings).run_pass()
        img_b = engine.start(folded, settings).run_pass()
    finally:
        engine.close()
    assert np.array_equal(img_a, img_b) and img_a[..., :3].max() > 0


def test_identity_final_with_a_pre_affine_is_not_skipped():
    flame = pre_flame()
    flame.final = XForm(color_speed=0.0)
    assert CompiledFlame.build(flame).final is None
    flame.final.pre = (2, 0, 0, 2, 0, 0)
    assert CompiledFlame.build(flame).final is not None


# --- document edits ----------------------------------------------------------------------------------------------
def test_document_transform_edits_are_undoable_and_announced(qapp):
    doc = FractalDocument()
    doc.replace(pre_flame())
    changed, structure = [], []
    doc.xform_changed.connect(lambda index, what: changed.append((index, what)))
    doc.transforms_changed.connect(lambda: structure.append(True))
    assert doc.set_affine(1, "post", (1, 0, 0, 1, 0.5, 0)) and doc.flame.xforms[1].post == (1, 0, 0, 1, 0.5, 0) and changed == [(1, "affine")]
    with pytest.raises(ValueError):
        doc.set_affine(1, "nope", identity_affine())
    assert doc.set_variation(0, "julian", 0.7) and doc.flame.xforms[0].variations["julian"] == 0.7
    assert doc.set_param(0, "julian_power", 5) and doc.flame.xforms[0].params["julian_power"] == 5.0
    assert doc.set_variation(0, "julian", 0.0) and "julian" not in doc.flame.xforms[0].variations and "julian_power" in doc.flame.xforms[0].params
    assert doc.set_xform_fields(2, name="leaf", weight=0.25, color=0.3) and doc.flame.xforms[2].name == "leaf"
    with pytest.raises(ValueError):
        doc.set_xform_fields(2, bogus=1)
    assert doc.set_chaos(0, 2, 0.0) and doc.flame.xforms[0].chaos == [1.0, 1.0, 0.0]
    assert doc.set_chaos(0, 2, 1.0) and doc.flame.xforms[0].chaos is None
    assert doc.set_all_chaos(1, 0.0) and doc.flame.xforms[1].chaos == [0.0, 0.0, 0.0]
    assert doc.xform(None) is None and doc.xform(7) is None and not doc.set_variation(None, "linear", 1.0)
    doc.set_final_enabled(True)
    assert doc.flame.final is not None and structure == [True] and doc.set_affine(None, "pre", (2, 0, 0, 2, 0, 0))
    assert doc.add_xform() == 3 and doc.duplicate_xform(3) == 4 and doc.add_linked_xform(0) == 5 and doc.delete_xform(5) == 4
    assert len(structure) == 5 and len(doc.flame.xforms) == 5 and doc.modified
    steps = 0
    while doc.undo():
        steps += 1
    assert steps >= 12 and doc.flame.xforms[1].post == identity_affine() and doc.flame.final is None and len(doc.flame.xforms) == 3
    assert doc.redo() and doc.can_undo


# --- the editor window -------------------------------------------------------------------------------------------
@pytest.fixture
def editor(main_window_factory, monkeypatch):
    monkeypatch.setattr(config, "EDIT_RENDER_DELAY_MS", 300)
    win = main_window_factory(cheap_renders=True)
    win.viewport._edit_timer.setInterval(300)
    open_flame_and_wait(win, SAMPLE, 0)
    win.actionEditor.trigger()
    wait_until(lambda: win.editor.isVisible() and win.editor.view.entries())
    spin(50)
    return win


def press(widget, pos: QPointF, button=Qt.MouseButton.LeftButton, modifiers=Qt.KeyboardModifier.NoModifier):
    QApplication.sendEvent(widget, QMouseEvent(QEvent.Type.MouseButtonPress, pos, widget.mapToGlobal(pos.toPoint()), button, button, modifiers))


def move(widget, pos: QPointF, button=Qt.MouseButton.LeftButton, modifiers=Qt.KeyboardModifier.NoModifier):
    QApplication.sendEvent(widget, QMouseEvent(QEvent.Type.MouseMove, pos, widget.mapToGlobal(pos.toPoint()), Qt.MouseButton.NoButton, button, modifiers))


def release(widget, pos: QPointF, button=Qt.MouseButton.LeftButton, modifiers=Qt.KeyboardModifier.NoModifier):
    QApplication.sendEvent(widget, QMouseEvent(QEvent.Type.MouseButtonRelease, pos, widget.mapToGlobal(pos.toPoint()), button, Qt.MouseButton.NoButton, modifiers))


def drag(widget, start: QPointF, end: QPointF, modifiers=Qt.KeyboardModifier.NoModifier, steps: int = 4):
    press(widget, start, modifiers=modifiers)
    for i in range(1, steps + 1):
        move(widget, start + (end - start) * (i / steps), modifiers=modifiers)
    release(widget, end, modifiers=modifiers)


def test_editor_opens_from_the_main_window_and_follows_the_document(editor):
    win = editor
    ed = win.editor
    assert win.actionEditor in win.toolBar.actions() and win.actionEditor.shortcut().toString() == "F4"
    assert win.actionEditor in win.menuWindows.actions() and not win.actionEditor.icon().isNull()
    assert ed.windowTitle().startswith("Transform Editor — ") and ed.isVisible()
    flame = win.document.flame
    assert ed.context.keys() == list(range(len(flame.xforms))) + ([None] if flame.final else [])
    assert ed.transform_combo.count() == len(ed.context.keys()) and ed.transform_combo.currentIndex() == 0
    assert [e.key for e in ed.view.entries()] == ed.context.keys()
    assert ed.view.triangle(0) == T.affine_to_triangle(flame.xforms[0].coefs)
    assert ed.mode_buttons[MODE_NORMAL].isChecked() and ed.mode == MODE_NORMAL
    assert config.HIGHLIGHT_COLOR.lower() in ed.mode_buttons[MODE_NORMAL].styleSheet().lower()
    wait_until(lambda: ed.preview.stats is not None, 30000)
    ed.transform_combo.setCurrentIndex(1)
    assert ed.context.selected == 1 and ed.view.selected_key == 1
    ed.hide()
    win.actionEditor.trigger()
    assert ed.isVisible()


def test_mode_buttons_choose_which_affine_the_triangles_edit(editor):
    ed, doc = editor.editor, editor.document
    for mode in (MODE_PRE, MODE_POST, MODE_NORMAL):
        ed.mode_buttons[mode].click()
        assert ed.mode == mode and ed.mode_buttons[mode].isChecked()
        assert sum(b.isChecked() for b in ed.mode_buttons.values()) == 1
        entry = ed.view.entry(0)
        assert entry.triangle == T.affine_to_triangle(getattr(doc.flame.xforms[0], mode))
        assert (entry.ghost is None) == (mode == MODE_NORMAL)     # the normal triangle shows dotted behind pre / post
    ed.set_mode(MODE_PRE)
    ed.triangle_tab.move_right.click()
    assert doc.flame.xforms[0].pre == (1, 0, 0, 1, 0.1, 0) and doc.flame.xforms[0].coefs == T.triangle_to_affine(ed.view.entry(0).ghost)
    ed.set_mode(MODE_POST)
    ed.triangle_tab.move_up.click()
    assert doc.flame.xforms[0].post == (1, 0, 0, 1, 0, -0.1)      # editor y up = fractal y down
    assert doc.flame.xforms[0].pre == (1, 0, 0, 1, 0.1, 0)
    assert "pre_affine" in flame_to_xml(doc.flame) and 'post="1 0 0 1 0 -0.1"' in flame_to_xml(doc.flame)


def test_dragging_corners_and_triangles_with_the_mouse_edits_the_transform(editor):
    ed, doc = editor.editor, editor.document
    view = ed.view
    view.fit()
    spin(20)
    original = doc.flame.xforms[0].coefs
    tri = view.triangle(0)
    # drag corner X one unit to the right (in editor space) in move mode
    start = view.to_screen(tri[T.CORNER_X])
    end = view.to_screen((tri[T.CORNER_X][0] + 1.0, tri[T.CORNER_X][1]))
    drag(view, start, end)
    moved = doc.flame.xforms[0].coefs
    assert math.isclose(moved[0], original[0] + 1.0, abs_tol=1e-6) and moved[4:] == original[4:] and doc.modified
    assert doc.can_undo and len(doc._undo) == 1                    # the whole drag is one undo step
    # dragging O with the axes locked moves the whole triangle
    tri = view.triangle(0)
    drag(view, view.to_screen(tri[T.CORNER_O]), view.to_screen((tri[T.CORNER_O][0] + 0.5, tri[T.CORNER_O][1] - 0.5)))
    after = doc.flame.xforms[0].coefs
    assert math.isclose(after[4], moved[4] + 0.5, abs_tol=1e-6) and math.isclose(after[5], moved[5] + 0.5, abs_tol=1e-6)
    assert after[:4] == pytest.approx(moved[:4]) and len(doc._undo) == 2
    # dragging inside another triangle selects it and moves it
    doc.undo()
    doc.undo()
    assert doc.flame.xforms[0].coefs == original
    tri1 = view.triangle(1)
    inside = (-0.2, 0.5)                                             # inside triangle 1 only (they share an edge)
    assert T.contains(tri1, inside) and not T.contains(view.triangle(0), inside)
    before = doc.flame.xforms[1].coefs
    drag(view, view.to_screen(inside), view.to_screen((inside[0] + 0.25, inside[1])))
    assert ed.context.selected == 1 and math.isclose(doc.flame.xforms[1].coefs[4], before[4] + 0.25, abs_tol=1e-6)
    # Esc during a drag cancels it
    inside = (-0.2, 0.4)
    assert view.hit_at(inside).key == 1
    press(view, view.to_screen(inside))
    move(view, view.to_screen((inside[0] + 1.0, inside[1])))
    assert view.is_dragging() and doc.flame.xforms[1].coefs[4] != pytest.approx(before[4] + 0.25)
    view.cancel_drag()
    assert not view.is_dragging() and math.isclose(doc.flame.xforms[1].coefs[4], before[4] + 0.25, abs_tol=1e-6)
    assert "X:" in ed.coords_label.text()


def test_rotate_and_scale_modes_and_modifier_overrides(editor):
    ed, doc = editor.editor, editor.document
    view = ed.view
    view.fit()
    spin(20)
    ed.context.select(0)
    ed.act_rotate.setChecked(True)
    assert view.edit_mode == MODE_ROTATE
    tri = view.triangle(0)
    pivot = view.pivot()
    assert pivot == tri[T.CORNER_O]                                  # local pivot = O
    start = (pivot[0] + 0.1, pivot[1] + 0.5)                         # inside this triangle only, off its corners and edges
    assert view.hit_at(start).key == 0 and view.hit_at(start).corner is None and view.hit_at(start).edge is None
    quarter = (pivot[0] - 0.5, pivot[1] + 0.1)                      # the start point turned 90° about O
    drag(view, view.to_screen(start), view.to_screen(quarter))
    turned = T.affine_to_triangle(doc.flame.xforms[0].coefs)
    expected = T.rotate_about(tri, pivot, math.pi / 2)
    assert np.allclose(turned, expected, atol=1e-6)
    doc.undo()
    ed.act_scale.setChecked(True)
    assert view.edit_mode == MODE_SCALE
    drag(view, view.to_screen(start), view.to_screen((pivot[0] + 0.2, pivot[1] + 1.0)))   # twice the distance from O
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.scale_about(tri, pivot, 2.0), atol=1e-6)
    doc.undo()
    ed.act_move.setChecked(True)
    drag(view, view.to_screen(start), view.to_screen(quarter), modifiers=Qt.KeyboardModifier.AltModifier)
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), expected, atol=1e-6)   # Alt rotates whatever the mode
    doc.undo()
    ed.act_pivot.setChecked(True)
    assert view.pivot_mode == PIVOT_WORLD and view.pivot() == (0.0, 0.0)
    ed.act_pivot.setChecked(False)


def test_triangle_tab_buttons_rotate_move_scale_flip_and_reset(editor):
    ed, doc = editor.editor, editor.document
    ed.context.select(0)
    tri = T.affine_to_triangle(doc.flame.xforms[0].coefs)
    pivot = ed.view.pivot()
    ed.act_rot_ccw.trigger()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.rotate_about(tri, pivot, math.pi / 2))
    ed.act_rot_cw.trigger()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), tri)
    ed.triangle_tab.rotate_step.setCurrentText("30")
    ed.triangle_tab.rotate_left.click()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.rotate_about(tri, pivot, math.radians(30)))
    doc.undo()
    ed.triangle_tab.move_step.setCurrentText("0.25")
    ed.triangle_tab.move_down.click()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.translate(tri, 0, -0.25))
    doc.undo()
    ed.triangle_tab.scale_step.setCurrentText("200")
    ed.triangle_tab.scale_up.click()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.scale_about(tri, pivot, 2.0))
    ed.triangle_tab.scale_down.click()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), tri)
    ed.act_flip_h.trigger()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.flip_horizontal(tri, pivot))
    ed.act_flip_v.trigger()
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.flip_vertical(T.flip_horizontal(tri, pivot), pivot))
    ed.act_reset_triangle.trigger()
    assert doc.flame.xforms[0].coefs == identity_affine()
    # corner boxes edit the triangle directly
    ed.triangle_tab.corner_boxes[T.CORNER_X][0].setValue(2.0)
    assert doc.flame.xforms[0].coefs == (2.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    ed.act_reset_all.trigger()
    assert all(x.coefs == identity_affine() for x in doc.flame.xforms)
    assert doc.undo() and doc.flame.xforms[0].coefs == (2.0, 0.0, 0.0, 1.0, 0.0, 0.0)


def test_variations_variables_xaos_and_colors_tabs_edit_the_document(editor):
    ed, doc = editor.editor, editor.document
    ed.context.select(0)
    xform = doc.flame.xforms[0]
    table = ed.variations_tab.table
    assert len(table.names()) >= 500 and "julia3D" in table.names() and "pre_zscale" in table.names() and "ztranslate" in table.names()
    table.value_edited.emit("julia3D", 0.5)
    assert doc.flame.xforms[0].variations["julia3D"] == 0.5
    assert "julia3D_power" in ed.variables_tab.table.names()         # the 3D variation's parameter appears
    ed.variables_tab.table.value_edited.emit("julia3D_power", 4)
    assert doc.flame.xforms[0].params["julia3D_power"] == 4.0
    ed.variables_tab.table.name_double_clicked.emit("julia3D_power")   # resets the default
    assert doc.flame.xforms[0].params["julia3D_power"] == 2.0
    ed.variables_tab.show_all.setChecked(True)
    assert len(ed.variables_tab.table.names()) > 1000
    ed.variables_tab.show_all.setChecked(False)
    ed.variations_tab.hide_unused.setChecked(True)
    assert "of" in ed.variations_tab.count_label.text() and ed.variations_tab.table.isRowHidden(table.names().index("arch"))
    ed.variations_tab.search.setText("zscale")
    assert not table.isRowHidden(table.names().index("pre_zscale")) or ed.variations_tab.hide_unused.isChecked()
    ed.variations_tab.hide_unused.setChecked(False)
    assert not table.isRowHidden(table.names().index("pre_zscale")) and table.isRowHidden(table.names().index("arch"))
    table.name_double_clicked.emit("julia3D")
    assert "julia3D" not in doc.flame.xforms[0].variations
    ed.variations_tab.clear_button.click()
    assert doc.flame.xforms[0].variations == {}
    doc.undo()
    assert doc.flame.xforms[0].variations
    # xaos
    n = len(doc.flame.xforms)
    ed.xaos_tab.table.value_edited.emit(ed.xaos_tab.table.names()[1], 0.0)
    assert xform_ops.chaos_row(doc.flame.xforms[0], n)[1] == 0.0
    ed.xaos_tab.from_button.setChecked(True)
    ed.xaos_tab.table.name_double_clicked.emit(ed.xaos_tab.table.names()[2])
    assert xform_ops.chaos_row(doc.flame.xforms[2], n)[0] == 0.0
    ed.xaos_tab.set_all.click()
    assert doc.flame.xforms[0].chaos is None
    # colours and the header
    xform = doc.flame.xforms[0]                                      # (undo replaced the flame object)
    ed.colors_tab.color_box.setValue(0.75)
    ed.colors_tab.speed_box.setValue(0.25)
    ed.colors_tab.opacity_box.setValue(0.5)
    assert (xform.color, xform.color_speed, xform.opacity) == (0.75, 0.25, 0.5)
    ed.colors_tab.palette.value_changed.emit(0.1)
    assert xform.color == 0.1
    ed.weight_box.setValue(0.8)
    assert xform.weight == 0.8
    ed.name_edit.setText("my leaf")
    ed.name_edit.editingFinished.emit()
    assert xform.name == "my leaf" and ed.transform_combo.itemText(0) == "1 - my leaf" and 'name="my leaf"' in flame_to_xml(doc.flame)
    ed.colors_tab.solo.setChecked(True)
    assert ed.preview._solo == 0
    ed.colors_tab.solo.setChecked(False)
    assert ed.preview._solo is None


def test_transform_tab_edits_all_three_affines_and_auto_zscale(editor):
    ed, doc = editor.editor, editor.document
    ed.context.select(1)
    tab = ed.transform_tab
    tab.groups[MODE_PRE].boxes[T.CORNER_O][0].setValue(0.5)
    assert doc.flame.xforms[1].pre == (1, 0, 0, 1, 0.5, 0)
    tab.groups[MODE_POST].boxes[T.CORNER_X][1].setValue(0.5)        # X vector (1, 0.5) in editor space → b = -0.5
    assert doc.flame.xforms[1].post == (1, -0.5, 0, 1, 0, 0)
    tab.groups[MODE_PRE].reset_all.click()
    assert doc.flame.xforms[1].pre == identity_affine()
    tab.groups[MODE_POST].buttons[T.CORNER_X].click()
    assert doc.flame.xforms[1].post == identity_affine()
    tab.polar_button.setChecked(True)
    tab.groups[MODE_NORMAL].boxes[T.CORNER_X][1].setValue(90.0)      # X axis straight up, same length
    a, b, c, d, e, f = doc.flame.xforms[1].coefs
    assert abs(a) < 1e-9 and b < 0
    tab.auto_zscale.setChecked(True)
    assert "pre_zscale" not in doc.flame.xforms[1].variations         # determinant 1: no depth scaling needed
    ed.triangle_tab.scale_up.click()
    a, b, c, d, e, f = doc.flame.xforms[1].coefs
    det = a * d - b * c
    assert det != 1 and doc.flame.xforms[1].variations["pre_zscale"] == pytest.approx(math.copysign(math.sqrt(abs(det)), det))
    tab.auto_zscale.setChecked(False)
    ed.triangle_tab.scale_up.click()
    assert doc.flame.xforms[1].variations["pre_zscale"] == pytest.approx(math.copysign(math.sqrt(abs(det)), det))


def test_transforms_can_be_added_duplicated_linked_deleted_and_the_final_toggled(editor):
    ed, doc = editor.editor, editor.document
    n = len(doc.flame.xforms)
    ed.act_add.trigger()
    assert len(doc.flame.xforms) == n + 1 and ed.context.selected == n and ed.transform_combo.count() == n + 1 + (1 if doc.flame.final else 0)
    ed.act_duplicate.trigger()
    assert len(doc.flame.xforms) == n + 2 and doc.flame.xforms[n + 1].coefs == doc.flame.xforms[n].coefs
    ed.act_link.trigger()
    assert len(doc.flame.xforms) == n + 3 and doc.flame.xforms[n + 1].opacity == 0.0 and ed.context.selected == n + 2
    ed.act_delete.trigger()
    assert len(doc.flame.xforms) == n + 2 and ed.context.selected == n + 1
    had_final = doc.flame.final is not None
    ed.act_final.setChecked(not had_final)
    assert (doc.flame.final is not None) == (not had_final)
    if doc.flame.final is None:
        ed.act_final.setChecked(True)
    assert doc.flame.final is not None and ed.context.selected is None and ed.context.is_final
    assert not ed.weight_box.isEnabled() and not ed.act_duplicate.isEnabled() and not ed.act_link.isEnabled()
    ed.set_mode(MODE_PRE)
    ed.triangle_tab.move_left.click()
    assert doc.flame.final.pre == (1, 0, 0, 1, -0.1, 0)             # pre / post affines work on the final transform too
    ed.set_mode(MODE_POST)
    ed.act_rot_cw.trigger()
    assert np.allclose(T.affine_to_triangle(doc.flame.final.post), T.rotate_about(T.REFERENCE, (0, 0), -math.pi / 2))
    ed.act_delete.trigger()                                          # deleting the final transform disables it
    assert doc.flame.final is None and ed.context.selected is not None
    palette = list(doc.flame.palette)
    ed.act_new_flame.trigger()
    assert len(doc.flame.xforms) == 1 and doc.flame.xforms[0].variations == {"linear": 1.0} and doc.flame.final is None
    assert doc.flame.camera.center == (0.0, 0.0) and doc.flame.palette == palette and ed.context.selected == 0
    while doc.undo():
        pass
    assert len(doc.flame.xforms) == n


def test_the_final_transform_can_be_grabbed_with_the_mouse(editor):
    ed, doc = editor.editor, editor.document
    view = ed.view
    ed.act_final.setChecked(True)
    assert doc.flame.final is not None and ed.context.is_final
    ed.act_reset_all.trigger()                                        # every triangle on the reference: the final is topmost
    view.fit()
    spin(20)
    hit = view.hit_at((0.3, 0.3))
    assert hit is not None and hit.key is None and hit.corner is None
    drag(view, view.to_screen((0.3, 0.3)), view.to_screen((0.8, 0.3)))
    assert ed.context.selected is None and doc.flame.final.coefs == pytest.approx((1, 0, 0, 1, 0.5, 0))
    corner = view.hit_at(T.affine_to_triangle(doc.flame.final.coefs)[T.CORNER_Y])
    assert corner is not None and corner.key is None and corner.corner == T.CORNER_Y
    move(view, view.to_screen((0.8, 0.3)), button=Qt.MouseButton.NoButton)
    assert ed.info_label.text().startswith("Transform Final")


def test_main_viewport_waits_for_the_edits_to_pause_before_rerendering(editor):
    win, ed, doc = editor, editor.editor, editor.document
    wait_for_render(win)
    spin(400)                                                         # any settle / resize re-render has fired by now
    generation = win.viewport.generation
    for i in range(5):
        ed.triangle_tab.move_right.click()
        spin(40)
        assert win.viewport.edit_render_pending and win.viewport.generation == generation   # held back while editing
    wait_until(lambda: not win.viewport.edit_render_pending, 3000)
    assert win.viewport.generation == generation + 1                  # one render after the pause
    assert doc.flame.xforms[0].coefs[4] == pytest.approx(ed.view.triangle(0)[T.CORNER_O][0])
    assert ed.preview.generation > 0
    assert "*" in win.windowTitle()


def test_keys_on_the_canvas_nudge_rotate_and_switch_modes(editor):
    from PySide6.QtTest import QTest
    ed, doc = editor.editor, editor.document
    view = ed.view
    view.setFocus()
    ed.context.select(0)
    before = T.affine_to_triangle(doc.flame.xforms[0].coefs)
    QTest.keyClick(view, Qt.Key.Key_Right)
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.translate(before, 0.1, 0))
    QTest.keyClick(view, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.translate(before, -0.9, 0))
    QTest.keyClick(view, Qt.Key.Key_PageUp)
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.rotate_about(T.translate(before, -0.9, 0), view.pivot(), math.radians(15)))
    QTest.keyClick(view, Qt.Key.Key_T)
    assert ed.mode == MODE_POST
    QTest.keyClick(view, Qt.Key.Key_T)
    assert ed.mode == MODE_PRE
    QTest.keyClick(view, Qt.Key.Key_T)
    assert ed.mode == MODE_NORMAL
    QTest.keyClick(view, Qt.Key.Key_R)
    assert view.edit_mode == MODE_ROTATE and ed.act_rotate.isChecked()
    QTest.keyClick(view, Qt.Key.Key_M)
    assert view.edit_mode == MODE_MOVE
    QTest.keyClick(view, Qt.Key.Key_A)
    assert not view.select_mode
    QTest.keyClick(view, Qt.Key.Key_A)
    assert view.select_mode
    QTest.keyClick(view, Qt.Key.Key_Plus)
    assert view.pixels_per_unit > 0


def test_copy_and_paste_triangle_and_clipboard_parsing(editor):
    ed, doc = editor.editor, editor.document
    ed.context.select(0)
    ed.act_copy.trigger()
    text = QGuiApplication.clipboard().text()
    assert text.startswith("fractalchemy-triangle") and parse_triangle_text(text) == doc.flame.xforms[0].coefs
    ed.context.select(1)
    ed.act_paste.trigger()
    assert doc.flame.xforms[1].coefs == doc.flame.xforms[0].coefs
    assert parse_triangle_text("1 0 0 1 0.5 0.25") == (1, 0, 0, 1, 0.5, 0.25) and parse_triangle_text("nope") is None


def test_editor_context_menu_keys_and_view_commands(editor):
    ed, doc = editor.editor, editor.document
    view = ed.view
    ed.context.select(0)
    # hovering reports the transform's variations in the status bar
    move(view, view.to_screen((-0.9, 0.5)), button=Qt.MouseButton.NoButton)   # inside transform 1's triangle only
    assert ed.info_label.text().startswith("Transform 1: linear 1")
    before = T.affine_to_triangle(doc.flame.xforms[0].coefs)
    view.triangle_command.emit(0, "move-up")
    assert np.allclose(T.affine_to_triangle(doc.flame.xforms[0].coefs), T.translate(before, 0, 0.1))
    view.triangle_command.emit(0, "reset-position")
    assert doc.flame.xforms[0].coefs[4:] == (0.0, 0.0)
    view.triangle_command.emit(0, "duplicate")
    assert ed.context.selected == len(doc.flame.xforms) - 1
    view.triangle_command.emit(ed.context.selected, "delete")
    view.triangle_command.emit(0, "toggle-pivot")
    assert ed.act_pivot.isChecked()
    zoom = view.pixels_per_unit
    view.zoom_by(2.0)
    assert view.pixels_per_unit == pytest.approx(zoom * 2)
    view.fit()
    x0, y0, x1, y1 = T.bounds([e.triangle for e in view.entries()] + [t for e in view.entries() for _l, t in e.ghosts])
    assert view.center == pytest.approx(((x0 + x1) / 2, (y0 + y1) / 2))
