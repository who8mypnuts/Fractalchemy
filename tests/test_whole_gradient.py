"""Whole-gradient adjustments (rotate / HSL), node operations, and the panel wiring."""

import random


from hueclid.model import Gradient
from hueclid.model.adjust import Adjustments, apply_adjustments, rotate_stops, shift_hsl
from hueclid.model.operations import (
    MAX_NODES, MIN_NODES, REROLL_NODES, add_nodes, randomize_colors, randomize_positions, remove_nodes, reroll, smooth,
)
from hueclid.model.color import distance
from hueclid.ui.document import GradientDocument
from hueclid.ui.main_window import MainWindow

RGB3 = [(0, 0, 0), (255, 0, 0), (255, 255, 255)]


# --- adjustments --------------------------------------------------------------
def test_shift_hsl_extremes_and_hue_wrap():
    assert shift_hsl((255, 0, 0), 120, 0, 0) == (0, 255, 0)
    assert shift_hsl((255, 0, 0), -240, 0, 0) == (0, 255, 0)
    assert shift_hsl((200, 50, 50), 0, -100, 0)[0] == shift_hsl((200, 50, 50), 0, -100, 0)[1]  # grey
    assert shift_hsl((200, 50, 50), 0, 0, 100) == (255, 255, 255)
    assert shift_hsl((200, 50, 50), 0, 0, -100) == (0, 0, 0)
    assert shift_hsl((200, 50, 50), 0, 0, 0) == (200, 50, 50)


def test_rotation_wraps_nodes_to_the_other_end_and_keeps_seam_order():
    g = Gradient.from_colors("g", RGB3)
    rotated = rotate_stops(g.stops, 0.25)
    assert [(round(s.position, 3), s.color) for s in rotated] == [(0.25, (255, 255, 255)), (0.25, (0, 0, 0)), (0.75, (255, 0, 0))]
    assert rotate_stops(g.stops, -0.25)[-1].color == (0, 0, 0)  # start wrapped to the far end
    assert rotate_stops(g.stops, 0.0) == g.stops


def test_adjustments_are_applied_from_the_base_not_cumulatively():
    g = Gradient.from_colors("g", [(200, 50, 50)])
    once = apply_adjustments(g, Adjustments(saturation=60))
    twice = apply_adjustments(apply_adjustments(g, Adjustments(saturation=30)), Adjustments(saturation=30))
    assert once.stops != twice.stops  # cumulative application would drift...
    assert apply_adjustments(g, Adjustments()).stops == g.stops  # ...and identity is exact


# --- operations -----------------------------------------------------------------
def test_randomize_keeps_colours_but_moves_every_node():
    g = Gradient.from_colors("g", RGB3 * 3)
    out = randomize_positions(g, random.Random(7))
    assert sorted(s.color for s in out) == sorted(s.color for s in g.stops)
    assert [s.position for s in out] == sorted(s.position for s in out)
    assert [s.position for s in out] != [s.position for s in g.stops]


def test_randomize_colors_keeps_positions_and_changes_colours():
    g = Gradient.from_colors("g", RGB3 * 3)
    out = randomize_colors(g, random.Random(11))
    assert [s.position for s in out] == [s.position for s in g.stops]
    assert [s.color for s in out] != [s.color for s in g.stops]
    assert len({s.color for s in out}) > 1
    assert all(0 <= c <= 255 for s in out for c in s.color)


def test_reroll_makes_a_whole_new_gradient():
    g = Gradient.from_colors("g", RGB3)
    out = reroll(g, random.Random(2))
    assert REROLL_NODES[0] <= len(out) <= REROLL_NODES[1]
    assert [s.position for s in out] == sorted(s.position for s in out)
    assert all(0.0 <= s.position <= 1.0 for s in out)
    assert {len(reroll(g, random.Random(seed))) for seed in range(20)} != {len(out)}  # count really varies


def test_add_nodes_adds_a_few_harmonious_colours():
    g = Gradient.from_colors("g", [(200, 40, 40), (220, 120, 40)])
    out = add_nodes(g, random.Random(3))
    assert 4 <= len(out) <= 8
    for stop in out[1:-1]:
        assert distance(stop.color, g.color_at(stop.position)) < 140  # near the local colour, not random
    assert len(add_nodes(Gradient.from_colors("g", [(1, 1, 1)] * MAX_NODES), random.Random(1))) == MAX_NODES


def test_remove_nodes_keeps_at_least_two():
    g = Gradient.from_colors("g", RGB3 * 4)
    out = remove_nodes(g, random.Random(5))
    assert MIN_NODES <= len(out) < len(g.stops)
    assert len(remove_nodes(Gradient.from_colors("g", RGB3[:2]), random.Random(1))) == 2


def test_smooth_reduces_nodes_and_softens_changes(samples):
    from hueclid.formats import load_gradient

    g = load_gradient(samples / "sample flames" / "candy.flame")
    out = Gradient("s", smooth(g))
    assert len(out) < len(g)
    worst_before = max(distance(g.color_at(i / 255), g.color_at((i + 1) / 255)) for i in range(255))
    worst_after = max(distance(out.color_at(i / 255), out.color_at((i + 1) / 255)) for i in range(255))
    assert worst_after < worst_before
    assert distance(out.color_at(0.5), g.color_at(0.5)) < 90  # overall colours preserved


# --- document semantics ---------------------------------------------------------
def test_document_adjust_then_edit_commits_and_resets(qapp):
    doc = GradientDocument()
    doc.replace(Gradient.from_colors("g", RGB3))
    resets = []
    doc.adjustments_reset.connect(lambda: resets.append(True))
    doc.set_adjustments(Adjustments(rotation=100))
    doc.set_adjustments(Adjustments(rotation=0))
    assert doc.gradient.stops == Gradient.from_colors("g", RGB3).stops  # back to base, losslessly
    doc.set_adjustments(Adjustments(luminance=-100))
    assert all(s.color == (0, 0, 0) for s in doc.gradient.stops) and resets == []
    doc.move_stop(1, 0.6)  # a node edit bakes the adjustment in
    assert resets == [True] and doc.adjustments.is_identity
    assert doc.gradient.stops[1].position == 0.6 and doc.gradient.stops[1].color == (0, 0, 0)


def test_panel_drives_document_and_follows_resets(qapp):
    window = MainWindow()
    window.document.replace(Gradient.from_colors("g", RGB3))
    panel = window.wholeGradientPanel
    assert panel.isEnabled()
    panel.position.slider.setValue(100)
    assert panel.position.spin.value() == 100
    assert round(window.document.gradient.stops[-1].position, 3) == 0.75 and window.document.modified
    panel.hue.spin.setValue(120)
    assert panel.hue.slider.value() == 120
    assert (0, 255, 0) in [s.color for s in window.document.gradient.stops]
    assert "3 nodes" in window.lblGradientName.text()

    panel.buttons["Auto increase nodes"].click()
    assert panel.position.value() == 0 and panel.hue.value() == 0  # committed → sliders reset
    assert len(window.document.gradient) > 3 and "nodes" in window.lblGradientName.text()
    panel.buttons["Smooth gradient"].click()
    panel.buttons["Randomize node colors"].click()
    panel.buttons["Reroll gradient"].click()
    panel.buttons["Randomize nodes"].click()
    panel.buttons["Decrease nodes"].click()
    assert len(window.document.gradient) >= MIN_NODES
    window.document.replace(Gradient())
    assert not panel.position.isEnabled() and not panel.buttons["Smooth gradient"].isEnabled()
    window.close()
