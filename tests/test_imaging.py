from hueclid.imaging import extract_palette, order_colors
from hueclid.imaging.ordering import by_path
from hueclid.model.color import luminance


def test_extract_palette_respects_count(samples):
    palette = extract_palette(samples / "sample images" / "idaho-002.jpeg", 8, 128)
    assert 1 < len(palette) <= 8
    assert palette == sorted(palette, key=lambda item: item[1], reverse=True)


def test_path_ordering_starts_dark_and_is_a_permutation():
    colors = [(255, 255, 255), (0, 0, 0), (128, 0, 0), (130, 2, 2)]
    ordered = by_path(colors)
    assert ordered[0] == min(colors, key=luminance)
    assert sorted(ordered) == sorted(colors)
    assert ordered[1:3] in ([(128, 0, 0), (130, 2, 2)], [(130, 2, 2), (128, 0, 0)])


def test_unknown_strategy_raises():
    try:
        order_colors([((0, 0, 0), 1)], "nope")
    except ValueError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ValueError")
