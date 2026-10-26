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


def test_move_stop_is_clamped_between_neighbours():
    g = Gradient.from_colors("g", [(0, 0, 0), (9, 9, 9), (255, 255, 255)])
    assert g.move_stop(1, 0.0) == 0.0
    assert g.move_stop(1, 5.0) == 1.0
    assert g.move_stop(0, 0.9) == 0.9  # neighbour now sits at 1.0
    assert g.move_stop(2, 0.0) == g.stops[1].position


def test_sample_matches_count():
    g = Gradient.from_colors("g", [(0, 0, 0), (255, 255, 255)])
    assert len(g.sample(256)) == 256
    assert g.sample(3) == [(0, 0, 0), (128, 128, 128), (255, 255, 255)]


def test_simplify_drops_collinear_stops_only():
    dense = Gradient.from_colors("g", [(0, 0, 0), (50, 50, 50), (100, 100, 100), (255, 0, 0)]).stops
    kept = simplify(dense, tolerance=2)
    assert [s.color for s in kept] == [(0, 0, 0), (100, 100, 100), (255, 0, 0)]
    assert len(simplify(dense, tolerance=0)) == 4
