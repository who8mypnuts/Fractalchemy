"""Selected-node panel, colour picker, and single-node operations."""

import random

import pytest
from PySide6.QtCore import QPointF

from fractalchemy.model import Gradient
from fractalchemy.model.node_ops import MIN_NODES, inserted_after, perturbed_color, position_after, random_color, without
from fractalchemy.ui.gradient_library_window import GradientLibraryWindow

RGB3 = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]


# --- model ----------------------------------------------------------------------
def test_position_after_is_midpoint_or_toward_end():
    g = Gradient.from_colors("g", RGB3)
    assert position_after(g, 0) == 0.25 and position_after(g, 1) == 0.75
    assert position_after(g, 2) == 0.75  # last node already at 1.0: slot before it
    assert position_after(Gradient("g", [g.stops[0].copy()]), 0) == 0.5


def test_inserted_after_returns_new_index():
    g = Gradient.from_colors("g", RGB3)
    stops, index = inserted_after(g, 1, (1, 2, 3))
    assert index == 2 and stops[2].color == (1, 2, 3) and stops[2].position == 0.75 and len(stops) == 4


def test_without_keeps_minimum():
    g = Gradient.from_colors("g", RGB3)
    assert [s.color for s in without(g, 1)] == [(0, 0, 0), (255, 255, 255)]
    with pytest.raises(ValueError):
        without(Gradient.from_colors("g", RGB3[:MIN_NODES]), 0)


def test_random_and_perturbed_colours_are_valid_and_different():
    rng = random.Random(4)
    assert all(0 <= c <= 255 for c in random_color(rng))
    nudged = perturbed_color((120, 160, 220), rng)
    assert nudged != (120, 160, 220) and all(0 <= c <= 255 for c in nudged)


# --- panel ----------------------------------------------------------------------
@pytest.fixture
def window(qapp):
    win = GradientLibraryWindow()
    win.document.replace(Gradient.from_colors("g", RGB3))
    win.show()
    yield win
    win.close()


def test_panel_is_greyed_without_selection_and_follows_it(window):
    panel = window.nodePanel
    assert not panel.isEnabled()
    window.document.select(1)
    assert panel.isEnabled() and panel.number.value() == 2 and panel.number.maximum() == 3
    assert panel.swatch.text() == "#FF0000" and panel.position.value() == 200 and panel.position_slider.value() == 200
    window.document.select(-1)
    assert not panel.isEnabled()


def test_typing_a_node_number_selects_it(window):
    window.document.select(0)
    window.nodePanel.number.setValue(3)
    assert window.document.selected_index == 2 and window.nodePanel.swatch.text() == "#FFFFFF"


def test_position_spin_and_slider_move_the_node(window):
    doc, panel = window.document, window.nodePanel
    doc.select(1)
    panel.position.setValue(100)
    assert round(doc.gradient.stops[1].position * 399) == 100 and panel.position_slider.value() == 100
    panel.position_slider.setValue(380)  # past the white node at 399? no — but past nothing yet
    assert doc.selected_index == 1 and round(doc.gradient.stops[1].position * 399) == 380
    panel.position_slider.setValue(399)  # ties with the last node: stable order keeps red before white
    panel.position.setValue(0)           # crosses the black node at 0 → red becomes node 1? tie keeps black first
    assert doc.gradient.stops[doc.selected_index].color == (255, 0, 0)
    assert panel.number.value() == doc.selected_index + 1
    assert doc.modified


def test_position_drag_across_a_neighbour_keeps_following_the_node(window):
    doc, panel = window.document, window.nodePanel
    doc.replace(Gradient.from_colors("g", [(0, 0, 0), (255, 0, 0), (0, 255, 0), (255, 255, 255)]))
    doc.select(1)  # red at 133
    panel.position_slider.setValue(300)  # jumps over green at 266
    assert doc.selected_index == 2 and doc.gradient.stops[2].color == (255, 0, 0)
    assert panel.number.value() == 3 and panel.position.value() == 300
    assert round(doc.gradient.stops[1].position * 399) == 266  # green untouched


def test_add_add_random_randomize_delete(window):
    doc, panel = window.document, window.nodePanel
    doc.select(0)
    panel.add_button.click()
    assert len(doc.gradient) == 4 and doc.selected_index == 1
    assert doc.gradient.stops[1].color == (0, 0, 0) and doc.gradient.stops[1].position == 0.25
    panel.add_random_button.click()
    assert len(doc.gradient) == 5 and doc.selected_index == 2 and doc.gradient.stops[2].color != (0, 0, 0)
    before = doc.gradient.stops[2].color
    panel.randomize_button.click()
    assert doc.gradient.stops[2].color != before and len(doc.gradient) == 5
    panel.delete_button.click()
    assert len(doc.gradient) == 4 and doc.selected_index == 2
    for _ in range(5):
        panel.delete_button.click()
    assert len(doc.gradient) == MIN_NODES and not panel.delete_button.isEnabled()


def test_node_edits_commit_pending_whole_gradient_adjustments(window):
    from fractalchemy.model.adjust import Adjustments

    doc = window.document
    doc.set_adjustments(Adjustments(luminance=-100))
    doc.select(1)
    window.nodePanel.add_button.click()
    assert doc.adjustments.is_identity and window.wholeGradientPanel.luminance.value() == 0
    assert all(s.color == (0, 0, 0) for s in doc.gradient.stops)  # darkening was baked in


# --- picker -----------------------------------------------------------------------
def test_picker_updates_gradient_live_and_cancel_reverts(window):
    doc, panel = window.document, window.nodePanel
    doc.select(1)
    panel.open_picker()
    picker = panel.picker
    assert picker.isVisible() and picker.color() == (255, 0, 0)
    picker.lightness.slider.setValue(25)  # darker red, live
    assert doc.gradient.stops[1].color == (128, 0, 0) and doc.modified
    picker.hue.slider.setValue(120)
    assert doc.gradient.stops[1].color == (0, 128, 0)
    picker.red.setValue(10)
    assert doc.gradient.stops[1].color == (10, 128, 0) and picker.hex.text() == "#0A8000"
    picker.hex.setText("#0000FF")
    picker.hex.editingFinished.emit()
    assert doc.gradient.stops[1].color == (0, 0, 255) and picker.hue.value() == 240
    picker.reject()
    assert doc.gradient.stops[1].color == (255, 0, 0) and not picker.isVisible()


def test_picker_wheel_drag_sets_hue_and_saturation(window):
    doc, panel = window.document, window.nodePanel
    doc.select(1)
    panel.open_picker()
    wheel = panel.picker.wheel
    centre = QPointF(wheel.width() / 2, wheel.height() / 2)
    wheel._pick(QPointF(centre.x(), centre.y() - wheel._radius()))  # straight up = 90° hue, full saturation
    assert panel.picker.hue.value() == 90 and panel.picker.saturation.value() == 100
    wheel._pick(centre)
    assert panel.picker.saturation.value() == 0
    assert doc.gradient.stops[1].color[0] == doc.gradient.stops[1].color[1] == doc.gradient.stops[1].color[2]
    panel.picker.accept()
    assert doc.gradient.stops[1].color != (255, 0, 0)


def test_picker_retargets_when_selection_changes(window):
    doc, panel = window.document, window.nodePanel
    doc.select(1)
    panel.open_picker()
    doc.select(2)
    assert panel.picker.color() == (255, 255, 255)
    panel.picker.lightness.slider.setValue(50)
    assert doc.gradient.stops[2].color == (128, 128, 128) and doc.gradient.stops[1].color == (255, 0, 0)
    doc.select(-1)
    assert not panel.picker.isVisible()


# --- gestures: double-click, keys, right-click (the shared NodeCommands) ------------------------------------------
from PySide6.QtCore import QPoint, Qt  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

from fractalchemy.model.node_ops import inserted_at, nudged_position  # noqa: E402


def max_channel_difference(a: Gradient, b: Gradient, samples: int = 400) -> int:
    return max(abs(p - q) for x, y in zip(a.sample(samples), b.sample(samples)) for p, q in zip(x, y))


def test_inserted_at_adds_a_handle_without_changing_the_colours():
    g = Gradient("g", [s for s in Gradient.from_colors("g", RGB3).stops])
    g.stops[0].position, g.stops[-1].position = 0.1, 0.8                 # leave room for the wrap-around span
    for position in (0.3, 0.62, 0.95, 0.02):                             # inside spans and in the wrap region
        stops, index = inserted_at(g, position)
        assert len(stops) == 4 and stops[index].position == position
        assert max_channel_difference(g, Gradient("g", stops)) <= 1


def test_nudged_position_uses_the_index_grid_and_clamps():
    assert nudged_position(200 / 399, 1, 399) == 201 / 399
    assert nudged_position(200 / 399, -10, 399) == 190 / 399
    assert nudged_position(0.0005, -1, 399) == 0.0 and nudged_position(0.999, 10, 399) == 1.0


def strip_point(window, position: float) -> QPoint:
    strip = window.gradientEditor.strip
    return QPoint(round(strip.mapper().to_x(position)), strip.height() // 2)


def test_double_click_on_the_strip_adds_a_selected_node_in_the_colour_already_there(window):
    before = window.document.gradient.copy()
    QTest.mouseDClick(window.gradientEditor.strip, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, strip_point(window, 0.25))
    doc = window.document
    assert len(doc.gradient) == 4 and doc.selected_index == 1
    assert abs(doc.gradient.stops[1].position - 0.25) < 0.01
    assert max_channel_difference(before, doc.gradient) <= 1 and doc.modified
    assert "Added node 2" in window.statusBar().currentMessage()


def test_double_click_on_empty_node_bar_adds_but_on_a_node_only_selects(window):
    nodes = window.gradientEditor.nodes
    QTest.mouseDClick(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, QPoint(round(nodes.mapper().to_x(0.75)), 8))
    assert len(window.document.gradient) == 4 and window.document.selected_index == 2
    QTest.mouseDClick(nodes, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, nodes.node_center(0).toPoint())
    assert len(window.document.gradient) == 4 and window.document.selected_index == 0
    strip = window.gradientEditor.strip                                   # on the strip, right over a node: selects it
    QTest.mouseDClick(strip, Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier, strip_point(window, 0.5))
    assert len(window.document.gradient) == 4 and window.document.selected_index == 1


def test_delete_and_backspace_remove_the_selected_node_but_never_below_two(window):
    nodes, doc = window.gradientEditor.nodes, window.document
    doc.select(1)
    QTest.keyClick(nodes, Qt.Key.Key_Delete)
    assert len(doc.gradient) == 2 and [s.color for s in doc.gradient.stops] == [(0, 0, 0), (255, 255, 255)]
    doc.select(0)
    QTest.keyClick(nodes, Qt.Key.Key_Backspace)
    assert len(doc.gradient) == MIN_NODES and "at least 2 nodes" in window.statusBar().currentMessage()


def test_arrow_keys_nudge_by_one_index_unit_and_shift_by_ten(window):
    nodes, doc = window.gradientEditor.nodes, window.document
    doc.select(1)                                                         # at 0.5 → index 200 (rounded)
    QTest.keyClick(nodes, Qt.Key.Key_Right)
    assert round(doc.gradient.stops[1].position * 399) == 201 and window.nodePanel.position.value() == 201
    QTest.keyClick(nodes, Qt.Key.Key_Left, Qt.KeyboardModifier.ShiftModifier)
    assert round(doc.gradient.stops[1].position * 399) == 191
    doc.select(2)
    QTest.keyClick(nodes, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)  # already at the end: clamped
    assert doc.gradient.stops[2].position == 1.0
    doc.select(0)
    for _ in range(25):                                                   # past the neighbour at 191: the selection follows
        QTest.keyClick(nodes, Qt.Key.Key_Right, Qt.KeyboardModifier.ShiftModifier)
    assert doc.selected_index == 1 and doc.gradient.stops[1].color == (0, 0, 0)


def test_enter_opens_the_colour_picker_on_the_selected_node(window):
    window.document.select(1)
    QTest.keyClick(window.gradientEditor.nodes, Qt.Key.Key_Return)
    picker = window.nodePanel.picker
    assert picker is window.node_commands.picker and picker.isVisible() and picker.color() == (255, 0, 0)
    picker.reject()


def test_clicking_the_strip_gives_the_node_keys_focus(window):
    strip, nodes = window.gradientEditor.strip, window.gradientEditor.nodes
    assert strip.focusProxy() is nodes and nodes.focusPolicy() == Qt.FocusPolicy.StrongFocus


def test_right_click_on_a_node_offers_the_panel_operations(window):
    nodes, commands = window.gradientEditor.nodes, window.node_commands

    def texts(menu):
        return [a.text() for a in menu.actions() if not a.isSeparator()]
    menu = nodes.menu_at(nodes.node_center(2))
    assert window.document.selected_index == 2
    assert texts(menu) == ["Add node", "Add random node", "Randomize node", "Pick colour…", "Delete node"]
    assert commands.delete_action in menu.actions() and commands.delete_action.shortcut().toString() == "Del"
    commands.delete_action.trigger()
    assert len(window.document.gradient) == 2 and not commands.delete_action.isEnabled()
    here = nodes.menu_at(QPointF(nodes.mapper().to_x(0.3), 8))            # empty space: "Add node here"
    assert texts(here) == ["Add node here"]
    here.actions()[0].trigger()
    assert len(window.document.gradient) == 3 and window.document.selected_index == 1
    assert texts(window.gradientEditor.strip.menu_at(strip_point(window, 0.8).x())) == ["Add node here"]


def test_panel_buttons_and_menu_actions_are_the_same_operations(window):
    doc, commands = window.document, window.node_commands
    doc.select(0)
    commands.add_action.trigger()
    assert len(doc.gradient) == 4 and doc.selected_index == 1
    window.nodePanel.add_button.click()
    assert len(doc.gradient) == 5
    assert window.nodePanel.commands is commands and window.gradientEditor.nodes.commands is commands
