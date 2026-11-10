"""Running scripts many times (Qt-free): explorer variations, parameter sweeps, batches over many flames, symmetry."""

import random
import threading

import pytest

from fractalchemy.fractal.formats import load_flame
from fractalchemy.fractal.random_flame import RandomOptions, random_batch
from fractalchemy.fractal.scene import Flame, XForm
from fractalchemy.fractal.symmetry import add_symmetry, random_symmetry, symmetry_order
from fractalchemy.scripting.batch import SEED_SAME, BatchSpec, apply_to_flames, result_name
from fractalchemy.scripting.codegen import flame_differences
from fractalchemy.scripting.explore import ExploreOptions, explore, sweep, vary
from fractalchemy.scripting.parameters import make_spec
from fractalchemy.scripting.runner import run_script

SPECS = [make_spec("Angle", 30, -180, 180), make_spec("Amount", 0.5, 0.0, 1.0), make_spec("Keep", True),
         make_spec("Palette", "Fire", choices=["Fire", "Ocean", "Forest"]), make_spec("Label", "x")]
VALUES = {"Angle": 30, "Amount": 0.5, "Keep": True, "Palette": "Fire", "Label": "x"}
CODE = ("angle = param('Angle', 30, min=-180, max=180)\namount = param('Amount', 0.5, min=0.0, max=1.0)\n"
        "for t in transforms:\n    t.rotate(angle + random() * amount)\n")


# --- the explorer ---------------------------------------------------------------------------------------------------------
def test_variations_stay_in_range_respect_locks_and_repeat():
    a = vary(SPECS, VALUES, 7, 8, random.Random(3), ExploreOptions(0.5, locked=frozenset({"Amount"})))
    b = vary(SPECS, VALUES, 7, 8, random.Random(3), ExploreOptions(0.5, locked=frozenset({"Amount"})))
    assert [v.values for v in a] == [v.values for v in b]
    for variant in a:
        assert -180 <= variant.values["Angle"] <= 180 and isinstance(variant.values["Angle"], int)
        assert variant.values["Amount"] == 0.5 and variant.values["Label"] == "x" and variant.seed == 7
        assert variant.values["Angle"] != 30                          # integers always move
    seeds = vary(SPECS, VALUES, 7, 4, random.Random(1), ExploreOptions(mode="seeds"))
    assert all(v.values == VALUES and v.seed != 7 and v.notes == ["new seed"] for v in seeds)
    anywhere = vary(SPECS, VALUES, 7, 30, random.Random(2), ExploreOptions(mode="anywhere"))
    assert len({v.values["Palette"] for v in anywhere}) > 1


def test_explore_runs_each_variation_restricted(samples):
    flame = load_flame(samples / "sample flames" / "candy.flame", 2)
    results = explore(CODE, flame, SPECS[:2], {"Angle": 30, "Amount": 0.5}, 7, 4, 11)
    assert len(results) == 4 and all(r.flame is not None and not r.error for r in results)
    first = results[0]
    expected = run_script(CODE, flame, None, threading.Event(), seed=first.variant.seed, parameters=first.variant.values).flame
    assert flame_differences(first.flame, expected) == []
    refused = explore(CODE + "save_flame('/tmp/never.flame')\n", flame, SPECS[:2], {"Angle": 30, "Amount": 0.5}, 7, 2, 11)
    assert all(r.flame is None and "writes files" in r.error for r in refused)


def test_sweeps():
    number = make_spec("A", 0.0, 0.0, 10.0)
    assert sweep(number, 0.0, 10.0, 5) == [0.0, 2.5, 5.0, 7.5, 10.0]
    eased = sweep(number, 0.0, 10.0, 5, "in-out")
    assert eased[0] == 0.0 and eased[-1] == 10.0 and eased[1] < 2.5
    assert sweep(make_spec("N", 2, 1, 12), 2, 5, 99) == [2, 3, 4, 5] and sweep(make_spec("N", 2, 1, 12), 5, 3, 2) == [5, 4, 3]
    assert sweep(SPECS[3], "Fire", "Forest", 2) == ["Fire", "Ocean", "Forest"]


def test_keyframe_plans():
    from fractalchemy.ui.script_animate import keyframe_plan
    plan = keyframe_plan(make_spec("A", 0.0, 0.0, 1.0), 0.0, 1.0, 3, 10, 12, "linear")
    assert plan == [(10, 0.0), (22, 0.5), (34, 1.0)]


# --- batches ----------------------------------------------------------------------------------------------------------------
def test_a_batch_runs_on_every_flame_names_results_and_reports_failures():
    flames = random_batch(4, RandomOptions(variations=["linear", "spherical"]), seed=5)
    flames[2] = Flame("broken", [])
    code = "transforms[0].rotate(param('Angle', 10))\n"
    seen = []
    report = apply_to_flames(BatchSpec(code, "Turn", {"Angle": 45}, 3, name_pattern="{name} · {script}"), flames, on_each=seen.append)
    assert [item.ok for item in report.items] == [True, True, False, True] and report.succeeded == 3 and report.failed == 1
    assert report.items[0].flame.name == f"{flames[0].name} · Turn" and "out of range" in report.items[2].error
    assert seen == report.items
    expected = run_script(code, flames[0], None, threading.Event(), seed=report.items[0].flame and None, parameters={"Angle": 45})
    assert flame_differences(report.items[0].flame, expected.flame) == []
    stopped = apply_to_flames(BatchSpec(code, stop_on_error=True), flames)
    assert stopped.stopped and len(stopped.items) == 3


def test_batches_refuse_side_effects_and_seeds_repeat():
    flames = random_batch(3, RandomOptions(variations=["linear"]), seed=1)
    refused = apply_to_flames(BatchSpec("message('hi')\n"), flames)
    assert all("shows a message" in item.error for item in refused.items)
    jitter = "for t in transforms:\n    t.translate(random(), random())\n"
    same = apply_to_flames(BatchSpec(jitter, seed=9, seed_policy=SEED_SAME), [flames[0], flames[0]])
    assert same.items[0].flame.xforms[0].coefs == same.items[1].flame.xforms[0].coefs
    fresh = apply_to_flames(BatchSpec(jitter, seed=9), [flames[0], flames[0]])
    assert fresh.items[0].flame.xforms[0].coefs != fresh.items[1].flame.xforms[0].coefs
    stop = threading.Event()
    stop.set()
    assert apply_to_flames(BatchSpec(jitter), flames, stop).stopped
    assert result_name("{name} {n}", "a", "s", 3) == "a 3" and result_name("{bad}", "a", "s", 1) == "a"


# --- symmetry -----------------------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("order, added", [(0, 0), (1, 0), (2, 1), (3, 2), (-1, 1), (-4, 4)])
def test_add_symmetry(order, added):
    flame = Flame("x", [XForm(chaos=[1.0, 0.0]), XForm()])
    assert add_symmetry(flame, order) == added and len(flame.xforms) == 2 + added
    extra = flame.xforms[2:]
    assert all(x.color_speed == 0.0 and x.weight == 1.0 and x.variations == {"linear": 1.0} for x in extra)
    assert flame.xforms[0].chaos == [1.0, 0.0] + [1.0] * added
    if order < 0:
        assert extra[0].coefs == (-1.0, 0.0, 0.0, 1.0, 0.0, 0.0)
    if order == 3:
        assert extra[0].coefs[0] == pytest.approx(-0.5) and extra[0].coefs[1] == pytest.approx(0.866025, abs=1e-6)


def test_symmetry_orders_and_the_random_batch_option():
    rng = random.Random(4)
    assert {random_symmetry(rng) for _ in range(200)} >= {-1, 2, 3}
    assert symmetry_order("bilateral", rng) == -1 and 2 <= symmetry_order("rotational", rng, (2, 5)) <= 5
    assert symmetry_order("dihedral", rng, (3, 3)) == -3 and symmetry_order("none", rng) == 0
    plain = random_batch(3, RandomOptions(variations=["linear", "julian"]), seed=12)
    again = random_batch(3, RandomOptions(variations=["linear", "julian"], symmetry="none"), seed=12)
    assert [f.to_dict()["xforms"] for f in plain] == [f.to_dict()["xforms"] for f in again]   # "none" changes nothing
    rotational = random_batch(3, RandomOptions(variations=["linear"], symmetry="rotational", symmetry_orders=(4, 4)), seed=12)
    assert all(sum(1 for x in f.xforms if x.color_speed == 0.0 and x.variations == {"linear": 1.0}) >= 3 for f in rotational)
