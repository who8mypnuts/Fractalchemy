import pytest

from fractalchemy.formats import FORMATS, format_for, load_gradient, load_gradients, save_gradient
from fractalchemy.formats.ufparams import pack_color, unpack_color
from fractalchemy.model import Gradient
from tests.conftest import sample_files


def test_every_sample_loads(samples):
    files = sample_files(samples)
    assert files
    for path in files:
        gradient = load_gradient(path)
        assert gradient.stops, path
        assert all(0.0 <= s.position <= 1.0 for s in gradient.stops)


def test_multi_gradient_files_expose_all_entries(samples):
    assert len(load_gradients(samples / "sample gradients" / "ag6.ugr", 0)) >= 35
    assert len(load_gradients(samples / "sample flames" / "candy.flame", 0)) == 5
    assert len(load_gradients(samples / "sample flames" / "69e8n5w1.flame", 0)) == 1


def test_ugr_colour_packing_is_rgb_low_byte_first():
    assert unpack_color(1186720) == (160, 27, 18)
    assert pack_color((160, 27, 18)) == 1186720


def test_ugr_round_trip(samples, tmp_path):
    original = load_gradient(samples / "sample gradients" / "saturated rainbox.gradient", simplify_tolerance=0)
    out = tmp_path / "out.ugr"
    save_gradient(original, out)
    reloaded = load_gradient(out, simplify_tolerance=0)
    assert reloaded.name == original.name
    assert [s.color for s in reloaded.stops] == [s.color for s in original.stops]
    assert [round(s.position, 4) for s in reloaded.stops] == [round(s.position, 4) for s in original.stops]


def test_flame_save_updates_first_palette_only(samples, tmp_path):
    src = samples / "sample flames" / "candy.flame"
    target = tmp_path / "candy.flame"
    target.write_bytes(src.read_bytes())
    gradient = Gradient.from_colors("x", [(255, 0, 0), (0, 0, 255)])
    save_gradient(gradient, target)
    all_after = load_gradients(target, 0)
    assert len(all_after) == 5
    assert all_after[0].stops[0].color == (255, 0, 0)
    assert all_after[0].stops[-1].color == (0, 0, 255)
    assert len(all_after[0]) == 256
    assert all_after[1].stops[0].color == load_gradients(src, 0)[1].stops[0].color
    assert b"\r\n" in target.read_bytes()  # source line endings preserved
    assert b"<xform" in target.read_bytes()


def test_flame_save_to_new_file(tmp_path):
    gradient = Gradient.from_colors("fresh", [(1, 2, 3), (4, 5, 6)])
    out = tmp_path / "new.flame"
    save_gradient(gradient, out)
    reloaded = load_gradient(out, simplify_tolerance=0)
    assert reloaded.name == "fresh" and len(reloaded) == 256


def test_images_cannot_be_saved(tmp_path):
    with pytest.raises(Exception):
        save_gradient(Gradient.from_colors("g", [(0, 0, 0)]), tmp_path / "x.png")


def test_unknown_extension_rejected(tmp_path):
    with pytest.raises(Exception):
        format_for(tmp_path / "x.txt")


def test_no_duplicate_extensions_across_formats():
    seen = [ext for fmt in FORMATS for ext in fmt.extensions]
    assert len(seen) == len(set(seen))


def test_flame_without_palettes_is_reported_not_crashed(tmp_path, qapp):
    from fractalchemy.ui.file_workers import load_entries

    path = tmp_path / "bare.flame"
    path.write_text('<flame name="x"><xform weight="1" coefs="1 0 0 1 0 0"/></flame>')
    assert load_gradients(path) == []
    with pytest.raises(Exception, match="no gradients"):
        load_entries(path)


def test_scanner_skips_directory_symlink_loops(tmp_path):
    from fractalchemy.library.catalog import GRADIENT_CATALOG
    from fractalchemy.library.scanner import scan_directory

    (tmp_path / "a").mkdir()
    (tmp_path / "a" / "loop").symlink_to(tmp_path, target_is_directory=True)
    (tmp_path / "a" / "g.ugr").write_text('x {\ngradient:\n title="x" smooth=no\n index=0 color=0\n}\n')
    scanned = scan_directory(tmp_path, GRADIENT_CATALOG)
    assert scanned.file_count() == 1 and [d.path.name for d in scanned.dirs] == ["a"]
    assert scanned.dirs[0].dirs == []
