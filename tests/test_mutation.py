"""Mutation and breeding (Qt-free): determinism, what each operator may touch, parameter rules, stability, crossovers."""

import random

import pytest

from fractalchemy.fractal import breeding as B
from fractalchemy.fractal import mutation as M
from fractalchemy.fractal import variations as V
from fractalchemy.fractal.formats import load_flame
from fractalchemy.fractal.scene import Flame, XForm

FAST = M.MutationOptions(check=False)


@pytest.fixture(scope="module")
def candy(samples) -> Flame:
    return load_flame(samples / "sample flames" / "candy.flame", 0)


@pytest.fixture(scope="module")
def stuff(samples) -> Flame:
    return load_flame(samples / "sample flames" / "stuff.flame", 1)


def sierpinski() -> Flame:
    flame = Flame("sierpinski", [XForm(weight=1.0, color=c, coefs=(0.5, 0, 0, 0.5, e, f))
                                 for c, (e, f) in zip((0.0, 0.5, 1.0), ((0, 0), (0.5, 0), (0, 0.5)))])
    flame.camera.scale, flame.camera.center = 300.0, (0.5, 0.5)
    return flame


def only(kind: str, **kwargs) -> M.MutationOptions:
    return M.MutationOptions(kinds=frozenset({kind}), check=False, **kwargs)


# --- mutation --------------------------------------------------------------------------------------------------------
def test_the_same_seed_gives_the_same_mutants_and_a_different_one_differs(candy):
    first = [m.flame.to_dict() for m in M.mutants(candy, 4, 11, FAST)]
    again = [m.flame.to_dict() for m in M.mutants(candy, 4, 11, FAST)]
    other = [m.flame.to_dict() for m in M.mutants(candy, 4, 12, FAST)]
    assert first == again and first != other
    names = [m.flame.name for m in M.mutants(candy, 3, 1, FAST)]
    assert names == [f"{candy.name} · m{i}" for i in (1, 2, 3)]


def test_strength_zero_or_no_kinds_leave_the_parent_alone(candy):
    for options in (M.MutationOptions(strength=0.0, check=False), M.MutationOptions(kinds=frozenset(), check=False)):
        offspring = M.mutate(candy, random.Random(3), options)
        assert offspring.flame.to_dict() == candy.to_dict() and offspring.notes == []


def test_each_operator_changes_only_what_it_owns(candy):
    rng = random.Random(5)
    gradient = M.mutate(candy, rng, only(M.GRADIENT, strength=0.8)).flame
    assert gradient.palette != candy.palette and [x.coefs for x in gradient.xforms] == [x.coefs for x in candy.xforms]
    affine = M.mutate(candy, rng, only(M.AFFINE, strength=0.8)).flame
    assert affine.palette == candy.palette and [x.coefs for x in affine.xforms] != [x.coefs for x in candy.xforms]
    assert [x.variations for x in affine.xforms] == [x.variations for x in candy.xforms]
    weights = M.mutate(candy, rng, only(M.WEIGHTS)).flame
    assert sum(x.weight for x in weights.xforms) == pytest.approx(sum(x.weight for x in candy.xforms))
    assert all(x.weight > 0 for x in weights.xforms) and weights.palette == candy.palette
    colors = M.mutate(candy, rng, only(M.COLORS, strength=1.0)).flame
    assert all(0.0 <= x.color <= 1.0 and 0.0 <= x.color_speed <= 1.0 for x in colors.xforms)
    for kind in M.ORDER:                                     # every mutant keeps the parent's camera
        assert M.mutate(candy, random.Random(9), only(kind, strength=0.9)).flame.camera == candy.camera


def test_every_operator_runs_on_many_seeds_and_flames(candy):
    """Each operator has several branches picked at random; drive them all (an unexercised branch hid a bug once)."""
    for flame in (candy, sierpinski()):
        for kind in M.ORDER:
            for seed in range(12):
                child = M.mutate(flame, random.Random(seed), only(kind, strength=0.2 + (seed % 5) * 0.2)).flame
                assert child.xforms and len(child.palette) == len(flame.palette)


def test_variation_swaps_prefer_the_trend_and_bring_its_defaults():
    parent = sierpinski()
    seen = 0
    for seed in range(12):
        child = M.mutate(parent, random.Random(seed), only(M.VARIATIONS, trend="julian")).flame
        if any("julian" in x.variations for x in child.xforms):
            seen += 1
            x = next(x for x in child.xforms if "julian" in x.variations)
            assert {"julian_power", "julian_dist"} <= set(x.params)
    assert seen >= 4


def test_structure_respects_same_number_of_transforms_and_keeps_xaos_consistent(candy):
    kept = M.mutate(candy, random.Random(2), only(M.STRUCTURE, keep_count=True)).flame
    assert len(kept.xforms) == len(candy.xforms)
    for seed in range(8):
        child = M.mutate(candy, random.Random(seed), only(M.STRUCTURE, strength=1.0)).flame
        assert len(child.xforms) != len(candy.xforms)
        assert all(x.chaos is None or len(x.chaos) == len(child.xforms) for x in child.xforms)
    for seed in range(6):                                   # xaos and drift keep the rows consistent too
        for kind in (M.XAOS, M.DRIFT):
            child = M.mutate(candy, random.Random(seed), only(kind, strength=0.9)).flame
            assert all(x.chaos is None or len(x.chaos) == len(child.xforms) for x in child.xforms)


def test_keep_symmetry_leaves_colour_speed_zero_transforms_alone():
    parent = sierpinski()
    parent.xforms[1].color_speed = 0.0                      # Apophysis's symmetry = 1
    for seed in range(10):
        for kind in (M.AFFINE, M.COLORS, M.VARIATIONS):
            child = M.mutate(parent, random.Random(seed), only(kind, strength=1.0)).flame
            assert child.xforms[1] == parent.xforms[1]


def test_parameters_stay_in_range_and_integers_stay_integers():
    V.REGISTRY.get("linear")                                # load the formulas
    bounded = next((k, i) for n in V.catalogue() for k, i in V.REGISTRY[n].param_info.items()
                   if i.min is not None and i.max is not None and i.max > i.min and i.type == "float" and not i.cyclic)
    integer = next((k, i) for n in V.catalogue() for k, i in V.REGISTRY[n].param_info.items() if i.type == "int")
    rng = random.Random(1)
    key, info = bounded
    assert all(info.min <= M.mutated_parameter(key, (info.min + info.max) / 2, rng, 1.0) <= info.max for _ in range(200))
    key, info = integer
    start = info.default if info.default else 2.0
    values = [M.mutated_parameter(key, start, rng, 1.0) for _ in range(100)]
    assert all(float(v).is_integer() for v in values)
    free = M.mutated_parameter("julian_power", 2.0, random.Random(4), 0.8)
    assert free != 2.0                                      # float parameters move freely


def test_mutants_are_stable_and_rolled_again_when_they_blow_up(candy, monkeypatch):
    for offspring in M.mutants(candy, 4, 7):
        assert M.is_stable(offspring.flame, [M.attractor_extent(candy)])
    calls = []
    real = M.is_stable

    def flaky(flame, references):
        calls.append(1)
        return len(calls) > 2 and real(flame, references)  # the first two rolls "blow up"
    monkeypatch.setattr(M, "is_stable", flaky)
    offspring = M.mutants(candy, 1, 3)[0]
    assert len(calls) == 3 and offspring.notes
    monkeypatch.setattr(M, "is_stable", lambda flame, references: False)
    assert M.mutants(candy, 1, 3)[0].notes == ["no stable variation found: a copy"]


def test_an_exploding_system_is_not_stable():
    flame = sierpinski()
    for x in flame.xforms:
        x.coefs = (3.0, 0.0, 0.0, 3.0, 1.0, 1.0)             # expanding everywhere: it blows up
    assert not M.is_stable(flame, [])


# --- breeding --------------------------------------------------------------------------------------------------------
def test_children_are_deterministic_and_named(candy, stuff):
    first = [c.flame.to_dict() for c in B.children(candy, stuff, 4, 21, B.BreedOptions(check=False))]
    assert first == [c.flame.to_dict() for c in B.children(candy, stuff, 4, 21, B.BreedOptions(check=False))]
    assert B.children(candy, stuff, 2, 1)[1].flame.name == f"{candy.name} × {stuff.name} · c2"


def test_alternate_takes_every_transform_from_a_parent_and_both_contribute(candy, stuff):
    parent_coefs = {x.coefs for x in candy.xforms} | {x.coefs for x in stuff.xforms}
    for seed in range(8):
        child = B.breed(candy, stuff, random.Random(seed), B.BreedOptions(mode=B.ALTERNATE, check=False)).flame
        assert len(child.xforms) in (len(candy.xforms), len(stuff.xforms))
        assert all(x.coefs in parent_coefs for x in child.xforms)
        assert any(x.coefs in {y.coefs for y in candy.xforms} for x in child.xforms)
        assert any(x.coefs in {y.coefs for y in stuff.xforms} for x in child.xforms)
        assert all(x.chaos is None or len(x.chaos) == len(child.xforms) for x in child.xforms)


def test_interpolate_lies_between_the_parents():
    a, b = sierpinski(), sierpinski()
    for x in b.xforms:
        x.coefs = (0.3, 0.0, 0.0, 0.3) + x.coefs[4:]
    child = B.breed(a, b, random.Random(1), B.BreedOptions(mode=B.INTERPOLATE, check=False)).flame
    assert all(0.3 < x.coefs[0] < 0.5 for x in child.xforms)


def test_union_has_every_transform_with_varied_shares(candy, stuff):
    children = [B.breed(candy, stuff, random.Random(s), B.BreedOptions(mode=B.UNION, check=False)).flame for s in range(3)]
    for child in children:
        assert len(child.xforms) == len(candy.xforms) + len(stuff.xforms) and all(x.chaos is None for x in child.xforms)
        assert sum(x.weight for x in child.xforms) == pytest.approx(1.0)
    assert len({round(c.xforms[0].weight, 6) for c in children}) == 3


def test_gradient_and_camera_sources(candy, stuff):
    def child(**options):
        return B.breed(candy, stuff, random.Random(2), B.BreedOptions(mode=B.ALTERNATE, check=False, **options)).flame
    assert child(gradient=B.FROM_A).palette == candy.palette and child(gradient=B.FROM_B).palette == stuff.palette
    blended = child(gradient=B.BLEND).palette
    assert blended not in (candy.palette, stuff.palette)
    assert child(camera=B.FROM_A).camera == candy.camera and child(camera=B.FROM_B).camera == stuff.camera
    assert child(camera=B.FROM_B).coloring == stuff.coloring
