"""`scripting.diff.flame_diff`: the statements the recorder writes reproduce the edit — for every document mutator, for
our own mutation and breeding engines as fuzzers, in both styles — and read the way a person would write them."""

import math
import random
import threading

import pytest

from fractalchemy.fractal import breeding as B
from fractalchemy.fractal import mutation as M
from fractalchemy.fractal.formats import load_flame
from fractalchemy.model import Gradient
from fractalchemy.scripting.codegen import flame_differences
from fractalchemy.scripting.diff import flame_diff
from fractalchemy.scripting.runner import run_script
from fractalchemy.ui.fractal_document import FractalDocument
from tests.test_document_history import MUTATORS


def replay(lines, flame):
    result = run_script("\n".join(lines), flame, None, threading.Event(), seed=0)
    assert result.ok, (result.error, lines)
    return result.flame


@pytest.fixture(scope="module")
def bases(samples):
    return [load_flame(samples / "sample flames" / name, index)
            for name, index in (("candy.flame", 2), ("flamepack1.flame", 5), ("satania_spikobius.chaos", 0))]


@pytest.mark.parametrize("call, kind, _signal", MUTATORS, ids=[m[1] for m in MUTATORS])
def test_every_document_edit_is_reproduced(qapp, samples, call, kind, _signal):
    doc = FractalDocument()
    doc.replace(load_flame(samples / "sample flames" / "candy.flame", 2))
    before = doc.flame.copy()
    call(doc)
    for style in ("absolute", "relative"):
        lines = flame_diff(before, doc.flame, style=style)
        assert lines, kind
        result = replay(lines, before)
        assert flame_differences(result, doc.flame, tol=1e-6) == [] or kind == "view", (kind, style, lines)
        pixel = 1.0 / doc.flame.camera.pixels_per_unit(doc.flame.camera.width, doc.flame.camera.height)
        assert all(abs(a - b) <= pixel for a, b in zip(result.camera.center, doc.flame.camera.center))
        assert not any(line.startswith(("flame.xforms", "flame.camera", "flame.coloring")) for line in lines), (kind, lines)


def test_single_edits_read_like_hand_written_code(bases):
    before = bases[0]
    after = before.copy()
    after.coloring.gamma = 3.5
    after.camera.zoom = 1.25
    assert flame_diff(before, after) == ["camera.zoom = 1.25", "coloring.gamma = 3.5"]
    assert flame_diff(before, after, style="relative") == [f"camera.zoom += {1.25 - before.camera.zoom:.9g}".rstrip("0"),
                                                           f"coloring.gamma += {3.5 - before.coloring.gamma:.9g}"]
    assert flame_diff(before, before.copy()) == []


def test_deep_zooms_keep_the_centre_accurate_to_a_pixel(bases):
    before = bases[0]
    after = before.copy()
    after.camera.zoom = 18.0
    after.camera.center = (0.123456789012345, -0.98765432109876)
    lines = flame_diff(before, after)
    centre = next(line for line in lines if line.startswith("camera.center"))
    x = float(centre.split("(")[1].split(",")[0])
    pixel = 1.0 / after.camera.pixels_per_unit(after.camera.width, after.camera.height)
    assert abs(x - after.camera.center[0]) < pixel / 2


@pytest.mark.parametrize("seed", range(10))
def test_mutants_and_children_are_reproduced_in_both_styles(bases, seed):
    rng = random.Random(seed)
    for base in bases:
        mutant = M.mutate(base, rng, M.MutationOptions()).flame
        for style in ("absolute", "relative"):
            lines = flame_diff(base, mutant, style=style)
            assert flame_differences(replay(lines, base), mutant) == [], (style, lines)
    child = B.breed(bases[0], bases[1], rng, B.BreedOptions()).flame
    assert flame_differences(replay(flame_diff(bases[0], child), bases[0]), child) == []


def test_structure_changes(bases):
    base = bases[0]
    grown = base.copy()
    grown.xforms.append(grown.xforms[0].copy())
    lines = flame_diff(base, grown)
    assert lines[0].startswith(f"t{len(grown.xforms)} = add_transform(")
    shrunk = base.copy()
    del shrunk.xforms[2]
    for x in shrunk.xforms:
        if x.chaos is not None:
            del x.chaos[2]
    assert flame_diff(base, shrunk)[0] == "remove_transform(2)"
    shuffled = base.copy()
    shuffled.xforms.reverse()
    shuffled.xforms.pop()
    lines = flame_diff(base, shuffled)
    assert "clear_transforms()" in lines and flame_differences(replay(lines, base), shuffled) == []


def test_the_palette_is_written_in_its_most_readable_exact_form(bases):
    base = bases[0]
    rotated = base.copy()
    rotated.palette = base.palette[-37:] + base.palette[:-37]
    assert flame_diff(base, rotated) == ["gradient.rotate(37)"]
    flipped = base.copy()
    flipped.palette = base.palette[::-1]
    assert flame_diff(base, flipped) == ["gradient.reverse()"]
    inverted = base.copy()
    inverted.palette = [(255 - r, 255 - g, 255 - b) for r, g, b in base.palette]
    assert flame_diff(base, inverted) == ["gradient.invert()"]
    library = Gradient.from_colors("g", [(5, 7, 15), (15, 125, 74), (240, 200, 10)])
    recoloured = base.copy()
    recoloured.set_gradient(library)
    lines = flame_diff(base, recoloured, gradient=library)
    assert lines[0].startswith("gradient.set_stops(") and "'#05070f'" in lines[0]
    wrong_hint = Gradient.from_colors("h", [(1, 2, 3), (4, 5, 6)])
    assert flame_differences(replay(flame_diff(base, recoloured, gradient=wrong_hint), base), recoloured) == []
    noise = base.copy()
    rng = random.Random(1)
    noise.palette = [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(256)]
    lines = flame_diff(base, noise)
    assert lines[0] == "gradient.colors = [" and flame_differences(replay(lines, base), noise) == []


def test_values_the_api_would_clamp_fall_back_to_the_raw_model(bases):
    base = bases[0]
    odd = base.copy()
    odd.coloring.vibrancy = 1.5                    # a file may hold it; coloring.vibrancy clamps to 0..1
    odd.xforms[0].color = 1.25
    lines = flame_diff(base, odd)
    assert any(line.startswith("flame.coloring.vibrancy = 1.5") for line in lines)
    assert flame_differences(replay(lines, base), odd) == []


def test_relative_triangle_edits_are_rotations_scalings_and_moves(bases):
    base = bases[0]
    after = run_script("transforms[1].rotate(20)\ntransforms[1].translate(0.1, 0)\ntransforms[2].scale(1.5)\n"
                       "transforms[3].multiply(1, 0.3, 0, 1)", base, None, threading.Event()).flame
    lines = flame_diff(base, after, style="relative")
    assert "transforms[1].rotate(20.0)" in lines and "transforms[1].translate(0.1, 0.0)" in lines and "transforms[2].scale(1.5)" in lines
    assert any(line.startswith("transforms[3].coefs = (") for line in lines)        # a shear stays a value


def test_a_relative_recording_changes_another_fractal_by_the_same_amounts(bases):
    a, b = bases[0], bases[1]
    edited = a.copy()
    edited.camera.zoom += 0.25
    edited.coloring.gamma += 0.5
    edited.camera.rotate += 30
    lines = flame_diff(a, edited, style="relative")
    other = replay(lines, b)
    assert other.camera.zoom == pytest.approx(b.camera.zoom + 0.25)
    assert other.coloring.gamma == pytest.approx(b.coloring.gamma + 0.5)
    assert other.camera.rotate == pytest.approx((b.camera.rotate + 30) % 360)


def test_gradient_library_hints_become_stop_operations(bases):
    from fractalchemy import config
    from fractalchemy.model import simplify
    from fractalchemy.model.adjust import Adjustments, apply_adjustments
    base = bases[0]
    library = Gradient("g", simplify(base.gradient.stops, config.IMPORT_SIMPLIFY_TOLERANCE))
    after = base.copy()
    after.set_gradient(apply_adjustments(library, Adjustments(0, 30, 10, 0)))
    hints = {"adjustments": {"hue": 30, "saturation": 10, "luminance": 0, "rotation": 0}}
    lines = flame_diff(base, after, style="relative", hints=hints)
    assert lines == ["gradient.adjust_stops(hue=30, saturation=10)"]
    assert flame_differences(replay(lines, base), after) == []


def test_unavailable_variations_are_kept(bases):
    base = bases[0]
    after = base.copy()
    after.xforms[0].variations["no_such_formula"] = 1.0
    lines = flame_diff(base, after)
    assert flame_differences(replay(lines, base), after) == []      # kept exactly (through the raw model)


def test_the_3d_camera_is_written_in_degrees(bases):
    base = bases[0]
    after = base.copy()
    after.camera.pitch, after.camera.yaw = math.radians(35), math.radians(-15)
    lines = flame_diff(base, after)
    assert "camera.pitch = 35.0" in lines and "camera.yaw = -15.0" in lines
