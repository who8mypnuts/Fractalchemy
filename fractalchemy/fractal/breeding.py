"""Breeding: children of two flames, for the Mutate & Breed window. Pure Python + numpy, no Qt.

Three ways to combine parents A and B, after flam3-genome's crossovers and Electric Sheep's breeding:

    alternate     each transform slot comes from A or from B at random (flam3's *cross alternate*); the child has as many
                  transforms as one of its parents, and at least one from each when both can give one
    interpolate   a blend of the two at a random point between 25 % and 75 % (`blend.py`: every number mixed)
    union         every transform of both (flam3's *union*), parent A's share of the weight between 30 and 70 %
    mixed         any of the three, chosen per child

The **gradient** comes from A, from B, a blend of both, or either at random; the **camera** (with the colouring that goes
with it) from A, from B, or re-framed on the child's attractor. Xaos rows are kept consistent with the child's transform
count (a union drops them: the two parents' links do not describe each other's transforms). Children are checked and
rolled again exactly like mutants (`mutation.is_stable` against either parent's extent), and the same seed gives the same
children.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from .blend import align_flames, blend_flames
from .mutation import Offspring, attractor_extent, settle
from .random_flame import frame_camera
from .scene import Flame
from .xform_ops import MAX_XFORMS, chaos_row

ALTERNATE, INTERPOLATE, UNION, MIXED = "alternate", "interpolate", "union", "mixed"
MODES = (MIXED, ALTERNATE, INTERPOLATE, UNION)
MODE_LABELS = {MIXED: "Mixed", ALTERNATE: "Alternate transforms", INTERPOLATE: "Interpolate", UNION: "Union"}
MODE_TIPS = {MIXED: "Any of the three, chosen per child", ALTERNATE: "Each transform comes from one parent or the other",
             INTERPOLATE: "Every number blended between the parents (25–75 %)",
             UNION: "All the transforms of both parents, weighted 30–70 %"}
FROM_A, FROM_B, BLEND, EITHER, REFRAME = "a", "b", "blend", "either", "reframe"
GRADIENT_SOURCES = (FROM_A, FROM_B, BLEND, EITHER)
CAMERA_SOURCES = (FROM_A, FROM_B, REFRAME)
SOURCE_LABELS = {FROM_A: "Parent A", FROM_B: "Parent B", BLEND: "Blend of both", EITHER: "Either, at random", REFRAME: "Re-framed"}
INTERPOLATE_RANGE = (0.25, 0.75)
UNION_SHARE = (0.3, 0.7)


@dataclass(frozen=True)
class BreedOptions:
    """How children are made (see the module docstring)."""
    mode: str = MIXED
    gradient: str = FROM_A
    camera: str = FROM_A
    check: bool = True


def breed(a: Flame, b: Flame, rng: random.Random, options: BreedOptions = BreedOptions()) -> Offspring:
    """One child of `a` and `b`."""
    mode = options.mode if options.mode != MIXED else rng.choice((ALTERNATE, INTERPOLATE, UNION))
    if mode == ALTERNATE:
        child, note = _alternate(a, b, rng)
    elif mode == INTERPOLATE:
        child, note = _interpolate(a, b, rng)
    else:
        child, note = _union(a, b, rng)
    notes = [note, _take_gradient(child, a, b, rng, options.gradient), _take_camera(child, a, b, options.camera)]
    child.name = f"{a.name} × {b.name}"
    return Offspring(child, [n for n in notes if n])


def children(a: Flame, b: Flame, count: int, seed: int | None = None, options: BreedOptions = BreedOptions()) -> list[Offspring]:
    """`count` children (named `<A> × <B> · c<n>`), each rolled again while unstable; the same seed gives the same ones."""
    rng = random.Random(seed)
    seeds = [rng.getrandbits(32) for _ in range(max(0, count))]
    references = [attractor_extent(a), attractor_extent(b)] if options.check else []
    out = []
    for i, sub in enumerate(seeds):
        child_rng = random.Random(sub)
        offspring = settle(lambda _n, r=child_rng: breed(a, b, r, options), options.check, references,
                           Offspring(a.copy(), ["no stable child found: a copy of parent A"]))
        offspring.flame.name = f"{a.name} × {b.name} · c{i + 1}"
        out.append(offspring)
    return out


# --- the three crossovers ------------------------------------------------------------------------------------------
def _alternate(a: Flame, b: Flame, rng: random.Random) -> tuple[Flame, str]:
    count = rng.choice((len(a.xforms), len(b.xforms)))
    sources = [rng.choice([p for p in (a, b) if i < len(p.xforms)] or [a]) for i in range(count)]
    both = [i for i in range(count) if i < len(a.xforms) and i < len(b.xforms)]
    if both and len({id(s) for s in sources}) == 1:          # make sure both parents contribute when they can
        i = rng.choice(both)
        sources[i] = b if sources[i] is a else a
    child = a.copy() if sources.count(a) >= sources.count(b) else b.copy()
    child.xforms = [source.xforms[i].copy() for i, source in enumerate(sources)]
    for x in child.xforms:
        x.chaos = chaos_row(x, count) if x.chaos else None
    if a.final is not None or b.final is not None:
        finals = [p.final for p in (a, b) if p.final is not None]
        child.final = rng.choice(finals).copy()
    taken = "".join("A" if s is a else "B" for s in sources)
    return child, f"alternate: transforms from {taken}"


def _interpolate(a: Flame, b: Flame, rng: random.Random) -> tuple[Flame, str]:
    t = rng.uniform(*INTERPOLATE_RANGE)
    child = blend_flames(align_flames([a, b]), [1.0 - t, t])
    return child, f"interpolated {t * 100:.0f} % of the way from A to B"


def _union(a: Flame, b: Flame, rng: random.Random) -> tuple[Flame, str]:
    share = rng.uniform(*UNION_SHARE)                       # A's share of the weight (flam3 uses ½; varied so children differ)
    child = a.copy()
    xforms = ([x.copy() for x in a.xforms] + [x.copy() for x in b.xforms])[:MAX_XFORMS]
    for parent, part, fraction in ((a, xforms[:len(a.xforms)], share), (b, xforms[len(a.xforms):], 1.0 - share)):
        total = sum(x.weight for x in parent.xforms) or 1.0
        for x in part:
            x.weight = fraction * x.weight / total
    for x in xforms:
        x.chaos = None
    child.xforms = xforms
    final = a.final if a.final is not None else b.final
    child.final = final.copy() if final is not None else None
    return child, f"union: {len(a.xforms)} + {len(b.xforms)} transforms, A {share * 100:.0f} % of the weight (xaos dropped)"


# --- gradient and camera -------------------------------------------------------------------------------------------
def _take_gradient(child: Flame, a: Flame, b: Flame, rng: random.Random, source: str) -> str:
    if source == EITHER:
        source = rng.choice((FROM_A, FROM_B))
    if source == BLEND:
        child.palette = blend_flames(align_flames([a, b]), [0.5, 0.5]).palette
        return "gradient: a blend of both"
    child.palette = list((b if source == FROM_B else a).palette)
    return f"gradient of parent {'B' if source == FROM_B else 'A'}"


def _take_camera(child: Flame, a: Flame, b: Flame, source: str) -> str:
    parent = b if source == FROM_B else a
    child.camera = parent.camera.copy()
    child.coloring = parent.coloring.copy()
    if source == REFRAME and frame_camera(child):
        return "camera re-framed on the child"
    return f"camera of parent {'B' if parent is b else 'A'}"


__all__ = ["BreedOptions", "breed", "children", "MODES", "MODE_LABELS", "MODE_TIPS", "GRADIENT_SOURCES", "CAMERA_SOURCES",
           "SOURCE_LABELS", "ALTERNATE", "INTERPOLATE", "UNION", "MIXED", "FROM_A", "FROM_B", "BLEND", "EITHER", "REFRAME"]
