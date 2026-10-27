"""Scene model and the fractal file formats (.flame, .chaos, .fa)."""

import math
import shutil

import pytest

from fractalchemy.fractal import Camera, Flame, XForm
from fractalchemy.fractal.formats import (
    DEFAULT_SAVE_FORMAT, FORMATS, UnsupportedFractalFormat, fa, flame_names, fractal_format_for, is_fractal_file,
    load_flame, load_flames, open_dialog_filter,
)
from fractalchemy.fractal.formats.flame_xml import flame_to_xml, flames_to_xml, parse_text
from fractalchemy.library.catalog import FRACTAL_CATALOG
from fractalchemy.library.scanner import scan_directory

FLAMES = "sample flames"


# --- scene ------------------------------------------------------------------
def test_camera_pixel_transform_round_trips_and_respects_y_down():
    camera = Camera(center=(0.5, -0.25), scale=100, zoom=1, rotate=30, width=400, height=300)
    for px, py in ((0, 0), (200, 150), (399, 299), (123.4, 56.7)):
        x, y = camera.unproject(px, py, 400, 300)
        a, b, c, d, e, f = camera.pixel_transform(400, 300)
        assert math.isclose(a * x + c * y + e, px, abs_tol=1e-9) and math.isclose(b * x + d * y + f, py, abs_tol=1e-9)
    flat = Camera(center=(0, 0), scale=100, width=400, height=300)
    assert flat.unproject(200, 150, 400, 300) == pytest.approx((0.0, 0.0))
    assert flat.unproject(200, 250, 400, 300)[1] > 0   # lower on screen = larger y (flam3 convention)
    assert flat.pixels_per_unit(800, 600) == 200 and flat.pixels_per_unit(800, 150) == 50  # fits the smaller ratio


def test_flame_dict_round_trip_and_copy_independence():
    flame = Flame("t", [XForm(variations={"spherical": 1.0}, params={}, chaos=[1, 2]), XForm()], XForm(color_speed=0.2))
    flame.camera.zoom = 1.5
    clone = Flame.from_dict(flame.to_dict())
    assert clone.to_dict() == flame.to_dict()
    copy = flame.copy()
    copy.xforms[0].variations["linear"] = 1.0
    copy.camera.zoom = 0
    assert "linear" not in flame.xforms[0].variations and flame.camera.zoom == 1.5
    assert XForm.speed_from_symmetry(1.0) == 0.0 and XForm(color_speed=0.5).symmetry == 0.0


# --- .flame -----------------------------------------------------------------
def test_every_sample_flame_loads(samples):
    expected = {"candy.flame": 5, "bel2.flame": 6, "stuff.flame": 24, "69e8n5w1.flame": 1}
    for name, count in expected.items():
        flames = load_flames(samples / FLAMES / name)
        assert len(flames) == count and flame_names(samples / FLAMES / name) == [f.name for f in flames]
        for flame in flames:
            assert flame.renderable() and len(flame.palette) == 256


def test_apophysis_attributes_are_interpreted(samples):
    candy = load_flame(samples / FLAMES / "candy.flame", 0)
    assert candy.camera == Camera((0.0, 0.0), 960.0, -0.544, 0.0, 3840, 2160)
    assert candy.coloring.brightness == 4 and candy.coloring.gamma == 4 and candy.coloring.gamma_threshold == 0.04
    first = candy.xforms[0]
    assert first.variations == {"linear": 1.0} and first.coefs == (1, 0, 0, 1, -1, 0) and first.chaos == [1, 5, 1, 0, 0]
    assert first.color_speed == 0.0  # symmetry="1"
    rotated = load_flame(samples / FLAMES / "candy.flame", 2)
    assert rotated.final is not None and "lazysusan" in rotated.final.variations
    assert rotated.final.params["lazysusan_spin"] == pytest.approx(1.570796)
    power = [f for f in load_flames(samples / FLAMES / "bel2.flame") if f.name == "power source"][0]
    assert power.camera.rotate == -30 and "crackle" in power.xforms[0].variations and not power.unsupported


def test_flame_xml_writer_round_trips_everything_we_model(samples):
    for path in (samples / FLAMES).glob("*.flame"):
        for flame in load_flames(path):
            again = parse_text(flame_to_xml(flame))[0]
            a, b = flame.to_dict(), again.to_dict()
            a.pop("unsupported"), b.pop("unsupported")   # unknown variations are not carried through the model
            assert a == b, (path.name, flame.name)
    doc = flames_to_xml(load_flames(samples / FLAMES / "candy.flame")[:2], "two")
    assert [f.name for f in parse_text(doc)] == ["original", "outlined"]


def test_flame_file_entry_operations(samples, tmp_path):
    path = shutil.copy(samples / FLAMES / "candy.flame", tmp_path / "c.flame")
    fmt = fractal_format_for(path)
    assert fmt.can_append and fmt.can_remove and fmt.can_rename and fmt.multi_entry
    flame = load_flame(path, 2)
    flame.name = "added"
    assert fmt.append(flame, path) == 5 and flame_names(path)[-1] == "added"
    fmt.rename(path, 5, "renamed")
    fmt.remove(path, 0)
    assert flame_names(path) == ["outlined", "rotated", "pearl", "obsession", "renamed"]
    fmt.replace(load_flame(path, 0), path, 4)
    assert flame_names(path)[4] == "outlined"
    other = tmp_path / "o.flame"
    fmt.copy_entry(path, 1, other)
    assert flame_names(other) == ["rotated"]


# --- .chaos -----------------------------------------------------------------
def test_chaotica_worlds_load_with_camera_and_xaos(samples):
    spik = load_flame(samples / FLAMES / "satania_spikobius.chaos")
    assert spik.name == "Spikobius by Satania" and len(spik.xforms) == 7
    assert spik.xforms[0].variations == {"mobius": 1.0} and spik.xforms[0].params["mobius_Im_C"] == -1
    assert spik.camera.width == 1280 and spik.camera.scale == pytest.approx(1266.76, abs=0.01)
    tram = load_flame(samples / FLAMES / "tatasz_tram_rails.chaos")
    assert tram.final is not None and tram.final.variations == {"bipolar": 1.0}
    assert tram.camera.rotate == -197.31 and tram.camera.scale == pytest.approx(960 / 1.25)
    assert tram.xforms[1].chaos == [1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
    assert "collideoscope" in tram.xforms[0].variations and not tram.unsupported   # a plugin the formula library supplies
    assert not fractal_format_for(samples / FLAMES / "tatasz_tram_rails.chaos").can_append


# --- .fa --------------------------------------------------------------------
def test_fa_documents_round_trip_and_support_every_entry_operation(samples, tmp_path):
    flames = load_flames(samples / FLAMES / "candy.flame")
    path = tmp_path / "set.fa"
    fa.write_file(flames[:2], path)
    assert flame_names(path) == ["original", "outlined"]
    assert [f.to_dict() for f in load_flames(path)] == [f.to_dict() for f in flames[:2]]
    fmt = fractal_format_for(path)
    assert fmt is DEFAULT_SAVE_FORMAT and fmt.append(flames[2], path) == 2
    fmt.rename(path, 2, "third")
    fmt.replace(flames[4], path, 0)
    fmt.remove(path, 1)
    assert flame_names(path) == ["obsession", "third"]
    fmt.copy_entry(path, 1, tmp_path / "other.fa")
    assert flame_names(tmp_path / "other.fa") == ["third"]
    (tmp_path / "bad.fa").write_text("{}")
    with pytest.raises(fa.FaParseError):
        load_flames(tmp_path / "bad.fa")


# --- registry / catalog -----------------------------------------------------
def test_registry_dispatches_by_extension():
    assert [f.extensions[0] for f in FORMATS] == [".flame", ".fa", ".chaos"]
    assert is_fractal_file("x.FLAME") and not is_fractal_file("x.ugr")
    with pytest.raises(UnsupportedFractalFormat):
        fractal_format_for("x.ugr")
    assert open_dialog_filter().startswith("All fractals (*.flame *.fa *.chaos)")


def test_fractal_catalog_scans_only_fractal_files(samples):
    scanned = scan_directory(samples / FLAMES, FRACTAL_CATALOG)
    names = {f.path.name for f in scanned.files}
    assert names == {"candy.flame", "bel2.flame", "stuff.flame", "69e8n5w1.flame", "flamepack1.flame", "satania_spikobius.chaos",
                     "tatasz_tram_rails.chaos"}
    candy = next(f for f in scanned.files if f.path.name == "candy.flame")
    assert candy.multi and candy.names[0] == "original"
    gradients = scan_directory(samples / "sample gradients", FRACTAL_CATALOG)
    assert gradients.files == []
    assert FRACTAL_CATALOG.roots_key == "fractal_library/roots" != FRACTAL_CATALOG.key + "x"


# --- 3D camera, direct colour and plugin parameters in flame XML ----------------
def test_flame_xml_reads_and_writes_the_3d_camera_and_plugin_attributes():
    text = """<flame name="deep" size="640 480" center="0 0" scale="200" cam_pitch="0.5" cam_yaw="-0.25" cam_dist="4" cam_zpos="0.1" cam_dof="0.2">
  <xform weight="0.5" color="0" var_color="0.6" collideoscope="1" collideoscope_a="0.3" collideoscope_num="4" coefs="1 0 0 1 0 0"/>
  <xform weight="0.5" color="1" dc_bubble="1" julia3D="0.5" julia3D_power="3" interference2="0.2" intrfr2_a1="2" intrfr2_t1="1" coefs="1 0 0 1 0 0"/>
</flame>"""
    flame = parse_text(text)[0]
    cam = flame.camera
    assert (cam.pitch, cam.yaw, cam.zpos, cam.dof) == (0.5, -0.25, 0.1, 0.2) and cam.perspective == pytest.approx(0.25)
    assert flame.xforms[0].var_color == 0.6 and flame.xforms[0].params["collideoscope_num"] == 4
    assert flame.xforms[1].variations == {"dc_bubble": 1.0, "julia3D": 0.5, "interference2": 0.2}
    assert flame.xforms[1].params["intrfr2_a1"] == 2 and flame.xforms[1].params["intrfr2_t1"] == 1   # parameters named unlike their variation
    assert not flame.unsupported
    again = parse_text(flame_to_xml(flame))[0]
    assert again.camera == cam and again.xforms[0].var_color == 0.6 and again.xforms[1].params == flame.xforms[1].params
    assert 'cam_perspective="0.25"' in flame_to_xml(flame) and "cam_pitch" not in flame_to_xml(Flame("flat", [XForm()]))
    assert Flame.from_dict(flame.to_dict()).camera == cam and Flame.from_dict(flame.to_dict()).xforms[0].var_color == 0.6


def test_modulus_is_a_variation_not_an_xform_attribute(samples):
    """Apophysis has no per-transform `modulus`; it is the modulus plugin (with modulus_x / modulus_y)."""
    text = """<flame name="m" size="600 600" center="0 0" scale="270">
  <xform weight="0.5" color="0" modulus="1" coefs="1 0 0 1 0 0" modulus_x="1" modulus_y="0.5" opacity="0"/>
</flame>"""
    xform = parse_text(text)[0].xforms[0]
    assert xform.variations == {"modulus": 1.0} and xform.params == {"modulus_x": 1.0, "modulus_y": 0.5}
    flame = load_flames(samples / "sample flames" / "69e8n5w1.flame")[0]
    assert all(x.variations == {"modulus": 1.0} for x in flame.xforms) and not flame.unsupported


def test_flame_files_keep_their_oversample_and_filter_hints():
    text = '<flame name="a" size="10 10" supersample="3" filter="0.7"><xform weight="1" coefs="1 0 0 1 0 0"/></flame>'
    flame = parse_text(text)[0]
    assert flame.oversample == 3 and flame.filter_radius == 0.7
    again = parse_text(flame_to_xml(flame))[0]
    assert (again.oversample, again.filter_radius) == (3, 0.7) and 'oversample="3" filter="0.7"' in flame_to_xml(flame)
    assert Flame.from_dict(flame.to_dict()).filter_radius == 0.7 and flame.copy().oversample == 3
    assert parse_text('<flame name="b" size="10 10"><xform weight="1" coefs="1 0 0 1 0 0"/></flame>')[0].oversample == 1


def test_flame_xml_keeps_y_pitch_and_curves():
    from fractalchemy.fractal.curves import Curves
    flame = Flame("c", [XForm()])
    flame.camera.pitch, flame.camera.pitch_y = 0.3, -0.4
    flame.coloring.curves.set_points("blue", [(0, 0), (0.5, 0.25), (1, 1)])
    flame.coloring.curves.set_points("alpha", [(0, 0.1), (1, 1)])
    text = flame_to_xml(flame)
    assert 'cam_pitch_y="-0.4"' in text and "fa_curves=" in text
    again = parse_text(text)[0]
    assert again.camera.pitch_y == -0.4 and again.coloring.curves == flame.coloring.curves
    assert Flame.from_dict(flame.to_dict()).coloring.curves == flame.coloring.curves
    assert Flame.from_dict(flame.to_dict()).camera.pitch_y == -0.4
    flat = flame_to_xml(Flame("f", [XForm()]))
    assert "cam_pitch_y" not in flat and "fa_curves" not in flat
    apo = '<flame name="a" size="8 8" curves="0 0 1 0 0 1 1 1 1 1 1 1 0 0 1 0.2 0.6 1 0.8 0.9 1 1 1 1 0 0 1 0 0 1 1 1 1 1 1 1 0 0 1 0 0 1 1 1 1 1 1 1"><xform weight="1" coefs="1 0 0 1 0 0"/></flame>'
    curves = parse_text(apo)[0].coloring.curves
    assert curves.is_default("overall") and not curves.is_default("red") and curves.evaluate("red", 0.5) > 0.5
    assert Curves.from_apophysis("1 2 3").is_default()
