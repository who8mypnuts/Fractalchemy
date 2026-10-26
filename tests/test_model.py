from hueclid.model import ColorStop, Gradient, simplify


def test_from_colors_spaces_evenly():
    g = Gradient.from_colors("g", [(0, 0, 0), (255, 255, 255), (255, 0, 0)])
    assert [round(s.position, 3) for s in g.stops] == [0.0, 0.5, 1.0]


def test_color_at_interpolates_and_clamps():
    g = Gradient("g", [ColorStop(0.25, (0, 0, 0)), ColorStop(0.75, (200, 100, 0))])
    assert g.color_at(0.0) == (0, 0, 0)
    assert g.color_at(0.5) == (100, 50, 0)
    assert g.color_at(1.0) == (200, 100, 0)


def test_stops_are_kept_sorted():
    g = Gradient("g", [ColorStop(0.9, (1, 1, 1)), ColorStop(0.1, (2, 2, 2))])
    assert [s.position for s in g.stops] == [0.1, 0.9]


def test_move_stop_clamps_to_unit_range():
    g = Gradient.from_colors("g", [(0, 0, 0), (9, 9, 9), (255, 255, 255)])
    grey = g.stops[1]
    g.move_stop(1, -3.0)
    assert grey.position == 0.0 and g.index_of(grey) == 1  # tie with the black stop keeps prior order
    g.move_stop(g.index_of(grey), 5.0)
    assert grey.position == 1.0
    assert [s.position for s in g.stops] == sorted(s.position for s in g.stops)


def test_move_stop_can_pass_other_stops_and_leaves_them_untouched():
    colors = [(0, 0, 0), (10, 10, 10), (20, 20, 20), (30, 30, 30), (40, 40, 40)]
    g = Gradient.from_colors("g", colors)
    before = [s.position for s in g.stops]
    new_index = g.move_stop(1, 0.9)  # jump over stops 2 and 3
    assert new_index == 3
    assert g.stops[3].color == (10, 10, 10) and g.stops[3].position == 0.9
    others = [s for s in g.stops if s.color != (10, 10, 10)]
    assert [s.position for s in others] == [before[i] for i in (0, 2, 3, 4)]
    assert [s.color for s in g.stops] == [(0, 0, 0), (20, 20, 20), (30, 30, 30), (10, 10, 10), (40, 40, 40)]


def test_sample_matches_count():
    g = Gradient.from_colors("g", [(0, 0, 0), (255, 255, 255)])
    assert len(g.sample(256)) == 256
    assert g.sample(3) == [(0, 0, 0), (128, 128, 128), (255, 255, 255)]


def test_simplify_drops_collinear_stops_only():
    dense = Gradient.from_colors("g", [(0, 0, 0), (50, 50, 50), (100, 100, 100), (255, 0, 0)]).stops
    kept = simplify(dense, tolerance=2)
    assert [s.color for s in kept] == [(0, 0, 0), (100, 100, 100), (255, 0, 0)]
    assert len(simplify(dense, tolerance=0)) == 4
