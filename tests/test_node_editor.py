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
