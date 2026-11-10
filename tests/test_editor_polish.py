"""Transform Editor polish: parameter ranges enforced in the tables (one rule set with the mutation engine) and the
rotate / scale grips around the selected triangle."""

import math

import pytest
from PySide6.QtCore import QPointF, Qt

from fractalchemy.fractal import variations as V
from fractalchemy.fractal.triangle_drag import MODE_ROTATE, DragSteps, begin_triangle_drag, drag
from fractalchemy.widgets.triangle_view import GRIP_ROTATE, GRIP_SCALE, TriangleEntry, TriangleView
from fractalchemy.widgets.value_table import ValueRow, ValueTable
from tests.conftest import mouse_drag


def _key(predicate):
    """A declared parameter whose ParamInfo satisfies `predicate`."""
    for var in V.REGISTRY.values():
        for key, info in var.param_info.items():
            if predicate(info):
                return key, info
    pytest.skip("no such parameter")


def test_constrain_param_rules():
    key, info = _key(lambda i: i.min is not None and i.max is not None and not i.cyclic and i.type == "float")
    assert V.constrain_param(key, info.max + 10)[0] == info.max and "stays within" in V.constrain_param(key, info.max + 10)[1]
    assert V.constrain_param(key, (info.min + info.max) / 2) == ((info.min + info.max) / 2, "")
    cyclic, cinfo = _key(lambda i: i.cyclic and i.min is not None and i.max is not None)
    span = cinfo.max - cinfo.min
    assert V.constrain_param(cyclic, cinfo.min + span * 1.25)[0] == pytest.approx(cinfo.min + span * 0.25)
    integer, iinfo = _key(lambda i: i.type == "int" and not i.nonzero and (i.max is None or i.max >= 3) and (i.min is None or i.min <= 2))
    assert V.constrain_param(integer, 2.4)[0] == 2.0 and "whole number" in V.constrain_param(integer, 2.4)[1]
    nonzero, _ = _key(lambda i: i.nonzero and i.type == "float" and (i.min is None or i.min < 0 < (i.max or 1)))
    assert V.constrain_param(nonzero, 0.0, previous=0.7)[0] == 0.7
    assert V.constrain_param("not_a_parameter_anywhere", 123.0) == (123.0, "")


def test_the_value_table_clamps_typed_and_dragged_values_with_a_note(qapp):
    key, info = _key(lambda i: i.min is not None and i.max is not None and not i.cyclic and i.type == "float")
    table = ValueTable()
    table.set_rows([ValueRow(key, info.min, constrain=lambda value, previous: V.constrain_param(key, value, previous))])
    edits, notes = [], []
    table.value_edited.connect(lambda name, value: edits.append(value))
    table.note.connect(notes.append)
    table.item(0, 1).setText(str(info.max + 100))
    assert edits[-1] == info.max and notes and key in notes[-1] and table.item(0, 1).text() != str(info.max + 100)


def test_the_variables_tab_rows_carry_the_rules(samples):
    from fractalchemy.fractal.formats import load_flame
    from fractalchemy.ui.editor_value_tabs import param_rows
    flame = load_flame(samples / "sample flames" / "candy.flame", 2)
    rows = param_rows(flame.xforms[0], show_all=True)
    declared = [r for r in rows if V.param_info(r.name) is not None]
    assert declared and all(r.constrain is not None for r in declared)


def _view(qapp):
    view = TriangleView()
    view.resize(400, 300)
    triangle = ((1.0, 0.0), (0.0, 0.0), (0.0, 1.0))
    view.set_entries([TriangleEntry(0, triangle, color=Qt.GlobalColor.red)], 0)
    view.set_view((0.3, 0.3), 100.0)
    view.show()
    return view, triangle


def test_grips_sit_around_the_selected_triangle_and_are_hit_first(qapp):
    view, _triangle = _view(qapp)
    grips = view.grips()
    assert len(grips[GRIP_ROTATE]) == 1 and len(grips[GRIP_SCALE]) == 4
    assert view.hit_at(view.to_editor(grips[GRIP_ROTATE][0])).grip == GRIP_ROTATE
    assert view.hit_at(view.to_editor(grips[GRIP_SCALE][2])).grip == GRIP_SCALE
    view.show_grips = False
    assert view.grips() == {} and view.hit_at(view.to_editor(grips[GRIP_ROTATE][0])) is None


def test_dragging_the_rotate_grip_turns_the_triangle_about_the_pivot(qapp):
    view, triangle = _view(qapp)
    moved = []
    view.triangle_dragged.connect(lambda key, new: moved.append(new))
    start = view.grips()[GRIP_ROTATE][0]
    pivot = view.pivot_of(0)
    centre = view.to_screen(pivot)
    radius = math.hypot(start.x() - centre.x(), start.y() - centre.y())
    end = QPointF(centre.x() + radius, centre.y())                 # a quarter turn clockwise on screen
    mouse_drag(view, start, end, steps=4)
    expected, _ = drag(begin_triangle_drag(MODE_ROTATE, view.to_editor(start), pivot, triangle), view.to_editor(end), False,
                       DragSteps(), True)
    assert moved and all(a == pytest.approx(b, abs=1e-6) for pa, pb in zip(moved[-1], expected) for a, b in zip(pa, pb))


def test_double_clicking_a_grip_resets(qapp):
    from PySide6.QtCore import QEvent
    from PySide6.QtGui import QMouseEvent
    from PySide6.QtWidgets import QApplication
    view, _triangle = _view(qapp)
    commands = []
    view.triangle_command.connect(lambda key, name: commands.append(name))
    for kind in (GRIP_ROTATE, GRIP_SCALE):
        pos = view.grips()[kind][0]
        QApplication.sendEvent(view, QMouseEvent(QEvent.Type.MouseButtonDblClick, pos, view.mapToGlobal(pos.toPoint()),
                                                 Qt.MouseButton.LeftButton, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier))
    assert commands == ["reset-rotation", "reset-scale"]
