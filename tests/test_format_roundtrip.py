"""Every fractal format round-trips what it can hold: mutated, bred and synthetic flames are written and read back and
compared with `flames_equivalent`, with the documented per-format equivalences (below) — so silent data loss in a
writer or a reader fails here."""

import math
import random

import pytest

from fractalchemy.fractal import breeding as B
from fractalchemy.fractal import mutation as M
from fractalchemy.fractal.formats import fa, flame_xml, chaos_world, chaos_writer, load_flame
from fractalchemy.fractal.formats.clipboard import flame_to_text, text_to_flames
from fractalchemy.fractal.scene import XForm, identity_affine
from fractalchemy.scripting.codegen import flame_differences

SOURCES = (("candy.flame", 2), ("flamepack1.flame", 5), ("satania_spikobius.chaos", 0))
SEEDS = range(12)


def _corpus(samples):
    bases = [load_flame(samples / "sample flames" / name, index) for name, index in SOURCES]
    flames = list(bases)
    for base in bases:
        flames += [M.mutate(base, random.Random(seed), M.MutationOptions()).flame for seed in SEEDS]
    for mode in ("alternate", "interpolate", "union", "mixed"):
        flames += [child.flame for child in B.children(bases[0], bases[1], 2, seed=3, options=B.BreedOptions(mode=mode))]
    synthetic = bases[0].copy()
    synthetic.name = 'odd <&"\'> näme'
    synthetic.xforms[0].pre = (1.1, 0.1, 0.0, 0.9, 0.2, -0.1)
    synthetic.xforms[1].post = (0.9, 0.0, 0.1, 1.0, 0.0, 0.3)
    synthetic.xforms[0].opacity, synthetic.xforms[0].var_color, synthetic.xforms[0].name = 0.0, 0.5, "centre <1>"
    synthetic.xforms[1].chaos = [0.0, 1.0, 0.5] + [1.0] * (len(synthetic.xforms) - 3)
    synthetic.xforms[2].weight = 1e-9
    synthetic.xforms[3].coefs = (1e6, 0.0, 0.0, -2.5e-7, 3.0, -4.0)
    for channel, mid in (("overall", 0.7), ("red", 0.4), ("green", 0.6), ("blue", 0.55)):
        synthetic.coloring.curves.set_points(channel, [(0, 0), (0.5, mid), (1, 1)])
    synthetic.camera.pitch, synthetic.camera.yaw, synthetic.camera.pitch_y = 0.3, math.radians(20), 0.1
    synthetic.camera.perspective, synthetic.camera.zpos, synthetic.camera.dof = 0.2, -0.5, 0.05
    synthetic.final = XForm(color_speed=0.0, coefs=(0.9, 0.0, 0.0, 0.9, 0.0, 0.0), variations={"julian": 0.5},
                            params={"julian_power": 3.0, "julian_dist": -1.0})
    flames.append(synthetic)
    return flames


def _fold_for_chaos(flame):
    """What a Chaotica world can hold of `flame` (documented losses of the `.chaos` writer):

    * the pre affine is folded into the affine before the variations (`combined_coefs`);
    * `zoom` is folded into `scale`;
    * the final transform becomes the camera's viewing transform: its colour, speed and opacity are not kept;
    * no filter radius, no contrast, no alpha curve, no 3D camera, no oversample, no direct-colour blend (`var_color`).
    """
    out = flame.copy()
    for x in out.xforms + ([out.final] if out.final else []):
        x.coefs, x.pre, x.var_color = x.combined_coefs(), identity_affine(), 1.0
    out.camera.scale, out.camera.zoom = out.camera.scale * 2 ** out.camera.zoom, 0.0
    out.camera.pitch = out.camera.yaw = out.camera.pitch_y = out.camera.perspective = out.camera.zpos = out.camera.dof = 0.0
    if out.final is not None:
        out.final.color, out.final.color_speed, out.final.opacity, out.final.var_color = 0.0, 0.5, 1.0, 1.0
    out.filter_radius, out.oversample, out.coloring.contrast = 0.2, 1, 1.0
    out.coloring.curves.reset("alpha")
    return out


@pytest.fixture(scope="module")
def corpus(samples):
    return _corpus(samples)


def test_fa_documents_are_lossless(corpus, tmp_path):
    path = tmp_path / "all.fa"
    fa.write_file(corpus, path)
    back = fa.parse_file(path)
    assert len(back) == len(corpus)
    for before, after in zip(corpus, back):
        assert flame_differences(after, before, ignore=("unsupported", "source_version")) == [], before.name


def test_flame_files_keep_everything_the_engines_use(corpus):
    text = flame_xml.flames_to_xml(corpus)
    back = flame_xml.parse_text(text)
    for before, after in zip(corpus, back):
        assert flame_differences(after, before, ignore=("unsupported", "source_version")) == [], before.name


def test_chaotica_worlds_keep_what_chaotica_can_hold(corpus):
    for flame in corpus:
        back = chaos_world.parse_text(chaos_writer.flames_to_world([flame]))[0]
        assert flame_differences(back, _fold_for_chaos(flame), tol=1e-6) == [], flame.name


def test_chaotica_worlds_keep_parameters_declared_under_another_prefix():
    x = XForm(variations={"JuliaRandomN": 1.0, "depth_sine": 0.5}, params={"JRN_dist": 2.5, "JRN_power": 4.0, "ds_power": 1.5})
    flame = load_flame_like([x])
    back = chaos_world.parse_text(chaos_writer.flames_to_world([flame]))[0]
    assert back.xforms[0].params["JRN_dist"] == 2.5 and back.xforms[0].params["ds_power"] == 1.5


def load_flame_like(xforms):
    from fractalchemy.fractal.scene import Flame
    return Flame("x", xforms)


def test_chaotica_curves_are_read_from_the_sample_worlds(samples):
    satania = load_flame(samples / "sample flames" / "satania_spikobius.chaos", 0)
    curves = satania.coloring.curves
    assert not curves.is_default("overall") and not curves.is_default("red") and not curves.is_default("blue")
    assert curves.points["overall"][1] == pytest.approx((0.08181818, 0.23181818))
    tram = load_flame(samples / "sample flames" / "tatasz_tram_rails.chaos", 0)
    assert tram.coloring.curves.is_default("overall") and not tram.coloring.curves.is_default("green")
    # unsorted tables (x = 0 1 0.76 0.44 0.22) come back in order
    xs = [x for x, _y in tram.coloring.curves.points["red"]]
    assert xs == sorted(xs) and xs[0] == 0.0 and xs[-1] == 1.0
    assert all(x.name == "" for x in tram.xforms)                  # Chaotica's default "Iterator N" names


def test_clipboard_text_round_trips_in_every_format(corpus):
    for flame in corpus[:6] + corpus[-1:]:
        for fmt in ("fa", "flame"):
            back = text_to_flames(flame_to_text(flame, fmt))[0]
            assert flame_differences(back, flame, ignore=("unsupported", "source_version")) == [], (fmt, flame.name)
        back = text_to_flames(flame_to_text(flame, "chaos"))[0]
        assert flame_differences(back, _fold_for_chaos(flame), tol=1e-6) == [], ("chaos", flame.name)


def test_fa_entry_operations_keep_the_other_entries(corpus, tmp_path):
    path = tmp_path / "many.fa"
    for flame in corpus[:4]:
        fa.append_flame(flame, path)
    fa.replace_flame(corpus[5], path, 1)
    fa.remove_flame(path, 0)
    back = fa.parse_file(path)
    expected = [corpus[5], corpus[2], corpus[3]]
    assert [flame_differences(a, b, ignore=("unsupported", "source_version")) for a, b in zip(back, expected)] == [[], [], []]


def test_chaotica_worlds_take_new_entries(corpus, tmp_path):
    from fractalchemy.fractal.formats import fractal_format_for, flame_names
    path = tmp_path / "world.chaos"
    fmt = fractal_format_for(path)
    assert fmt.can_append and not fmt.can_replace
    assert fmt.append(corpus[0], path) == 0 and fmt.append(corpus[1], path) == 1
    assert flame_names(path) == [corpus[0].name, corpus[1].name]
