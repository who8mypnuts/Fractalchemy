"""The gradient editor's gestures: double-click to add a node, Delete / Backspace, ← / → nudges, Enter for the colour
picker, and the right-click menus — all going through the shared `NodeCommands`."""

import pytest
from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtTest import QTest

from fractalchemy import config
from fractalchemy.model import ColorStop, Gradient
from fractalchemy.model.node_ops import inserted_at, nudged_position, to_units
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow

COLORS = [(0, 0, 0), (255, 0, 0), (0, 0, 255), (255, 255, 255)]


def max_difference(a: Gradient, b: Gradient, samples: int = 400) -> int:
    return max(abs(x - y) for p, q in zip(a.sample(samples), b.sample(samples)) for x, y in zip(p, q))


# --- model ----------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("position", [0.0, 0.05, 0.3, 0.62, 0.95, 1.0])
def test_inserting_at_a_position_leaves_the_gradient_looking_the_same(position):
    gradient = Gradient("g", [ColorStop(0.1, (255, 0, 0)), ColorStop(0.5, (0, 0, 255)), ColorStop(0.8, (0, 255, 0))])
    stops, index = inserted_at(gradient, position)
    assert len(stops) == 4 and stops[index].position == position
    assert stops[index].color == gradient.color_at(position)
    assert max_difference(gradient, Gradient("g", stops)) <= 1          # the wrap-around region included


def test_nudges_move_in_index_units_and_clamp():
    assert to_units(0.5) == 200 and nudged_position(0.5, 1) == 201 / config.UGR_MAX_INDEX
    assert nudged_position(0.5, -10) == 190 / config.UGR_MAX_INDEX
    assert nudged_position(0.001, -3) == 0.0 and nudged_position(0.999, 10) == 1.0


# --- the window -----------------------------------------------------------------------------------------------------
@pytest.fixture
def window(qapp):
    win = GradientLibraryWindow()
    win.resize(900, 320)
    win.document.replace(Gradient.from_colors("g", COLORS))
    win.show()
    yield win
    win.node_commands.picker.hide()
    win.document.modified = False
    win.close()


def x_of(window, position: float) -> float:
    return window.gradientEditor.nodes.mapper().to_x(position)


def test_double_clicking_the_strip_adds_a_node_in_the_colour_already_there(window):
    strip, document = window.gradientEditor.strip, window.document
    before = document.gradient.copy()
    QTest.mouseDClick(strip, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(x_of(window, 0.5)), 20))
    assert len(document.gradient) == 5 and document.selected_index == 2
    assert abs(document.gradient.stops[2].position - 0.5) < 0.01
    assert max_difference(before, document.gradient) <= 1 and document.modified
    assert "Added node 3" in window.statusBar().currentMessage()


def test_double_clicking_an_empty_spot_on_the_node_bar_adds_one_but_a_node_is_only_selected(window):
    nodes, document = window.gradientEditor.nodes, window.document
    y = round(nodes.node_center(0).y())
    QTest.mouseDClick(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(x_of(window, 0.2)), y))
    assert len(document.gradient) == 5 and document.selected_index == 1
    QTest.mouseDClick(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, nodes.node_center(3).toPoint())
    assert len(document.gradient) == 5 and document.selected_index == 3        # on a node: selected, nothing stacked
    QTest.mouseDClick(window.gradientEditor.strip, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier,
                      QPoint(round(nodes.node_center(4).x()), 20))
    assert len(document.gradient) == 5 and document.selected_index == 4        # the strip above a node: the same


def test_delete_and_backspace_remove_the_selected_node_but_never_below_two(window):
    nodes, document = window.gradientEditor.nodes, window.document
    document.select(1)
    QTest.keyClick(nodes, Qt.Key.Key_Delete)
    assert [s.color for s in document.gradient.stops] == [(0, 0, 0), (0, 0, 255), (255, 255, 255)]
    QTest.keyClick(nodes, Qt.Key.Key_Backspace)
    assert len(document.gradient) == 2 and document.selected_index == 1
    QTest.keyClick(nodes, Qt.Key.Key_Delete)
    assert len(document.gradient) == 2 and "at least 2 nodes" in window.statusBar().currentMessage()


def test_arrows_nudge_by_one_index_unit_and_shift_by_ten_following_the_node(window):
    nodes, document, panel = window.gradientEditor.nodes, window.document, window.nodePanel
    document.select(1)
    start = to_units(document.gradient.stops[1].position)                      # 133
    QTest.keyClick(nodes, Qt.Key.Key_Right)
    assert to_units(document.gradient.stops[1].position) == start + 1 == panel.position.value()
    QTest.keyClick(nodes, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    assert to_units(document.gradient.stops[1].position) == start + 1 - config.NODE_NUDGE_COARSE
    for _ in range(16):                                                         # across node 0 at 0: the selection follows
        QTest.keyClick(nodes, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    assert document.gradient.stops[document.selected_index].color == (255, 0, 0)
    assert document.gradient.stops[document.selected_index].position == 0.0    # clamped at the start


def test_enter_opens_the_colour_picker_on_the_selected_node(window):
    nodes, document = window.gradientEditor.nodes, window.document
    document.select(2)
    QTest.keyClick(nodes, Qt.Key.Key_Return)
    picker = window.node_commands.picker
    assert picker.isVisible() and picker.color() == (0, 0, 255) and window.nodePanel.picker is picker
    picker.red.setValue(40)
    assert document.gradient.stops[2].color == (40, 0, 255)


def test_keys_do_nothing_without_a_selection(window):
    QTest.keyClick(window.gradientEditor.nodes, Qt.Key.Key_Delete)
    assert len(window.document.gradient) == 4


def texts(menu) -> list[str]:
    return [a.text().split("\t")[0] for a in menu.actions() if not a.isSeparator()]


def test_right_clicking_a_node_offers_the_node_panels_operations(window):
    nodes, document, commands = window.gradientEditor.nodes, window.document, window.node_commands
    menu = nodes.build_menu(nodes.node_at(nodes.node_center(2)), nodes.node_center(2).x())
    assert document.selected_index == 2
    assert texts(menu) == ["Add node", "Add random node", "Randomize node", "Pick colour…", "Delete node"]
    assert [a for a in menu.actions() if not a.isSeparator()] == [a for a in commands.actions if a is not None]
    commands.delete_action.trigger()
    assert len(document.gradient) == 3
    document.remove_stop(0)
    menu = nodes.build_menu(0, nodes.node_center(0).x())
    assert not menu.actions()[-1].isEnabled()                                   # Delete: disabled at two nodes
    commands.add_action.trigger()
    assert len(document.gradient) == 3


def test_right_clicking_empty_space_offers_add_node_here(window):
    nodes, document = window.gradientEditor.nodes, window.document
    menu = nodes.build_menu(-1, x_of(window, 0.8))
    assert texts(menu) == ["Add node here"]
    menu.actions()[0].trigger()
    assert len(document.gradient) == 5 and abs(document.gradient.stops[document.selected_index].position - 0.8) < 0.01


def test_right_clicks_on_the_bar_and_the_strip_reach_the_menu(window, monkeypatch):
    from PySide6.QtGui import QContextMenuEvent
    nodes, strip = window.gradientEditor.nodes, window.gradientEditor.strip
    calls = []
    monkeypatch.setattr(nodes, "show_menu", lambda index, x, pos: calls.append((index, round(x))))

    def right_click(widget, pos: QPointF) -> None:
        widget.contextMenuEvent(QContextMenuEvent(QContextMenuEvent.Reason.Mouse, pos.toPoint(), pos.toPoint()))

    right_click(nodes, nodes.node_center(1))
    right_click(nodes, QPointF(x_of(window, 0.8), nodes.node_center(0).y()))
    right_click(strip, QPointF(nodes.node_center(3).x(), 20))
    right_click(strip, QPointF(x_of(window, 0.1), 20))
    assert [c[0] for c in calls] == [1, -1, 3, -1]


def test_panel_buttons_use_the_same_commands(window):
    document = window.document
    document.select(1)
    window.nodePanel.add_button.click()
    assert len(document.gradient) == 5 and document.gradient.stops[2].color == (255, 0, 0)
    assert window.nodePanel.commands is window.node_commands

