"""Mutation: random relatives of a flame, for the Mutate & Breed window (Apophysis's *Mutate*, with more ways to vary). Pure
Python + numpy, no Qt.

A mutant is the parent with one to three **operators** applied, each scaled by a *strength* (0 = unchanged, 1 = wild):

    affine              turn / scale / move / shear a few triangles (sometimes their post affine)
    variations          swap a variation for another from the pool (or the *trend*), sometimes add or drop one
    variation_weights   re-weigh the variations of a transform
    parameters          nudge variation parameters (bounded ones stay in range, integer ones stay integers)
    weights             redistribute the transforms' weights
    colors              move the transforms' colours and colour speeds
    gradient            shift the palette's hue, rotate it, or recolour it from a harmony — the one that changes the gradient
    xaos                re-weigh (or cut) links between transforms
    structure           add a random transform or remove one
    final               perturb the final transform (or, rarely, add one)
    drift               Apophysis's classic: blend the parent towards a freshly generated random flame

Options (`MutationOptions`): the strength, which operators may run, a **trend** variation that swaps and additions
prefer, the **pool** of variations to draw from, *same number of transforms* (no structure changes, drift stays within
the parent's transforms) and *keep symmetry* (transforms with colour speed 0, Apophysis's `symmetry = 1`, are left
alone).

Mutants keep the parent's camera, so they can be compared with it and with each other. `mutants()` makes a batch and
rolls a mutant again while its system blows up or collapses (the Random Batch's sanity test, `attractor_bounds`),
or while its extent differs from the parent's by more than `SCALE_LIMIT`. Everything takes an injected `random.Random`:
the same seed gives the same mutants.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, replace
from typing import Callable

from .. import config
from ..model.adjust import ROTATION_RANGE, Adjustments, apply_adjustments
from ..model.operations import randomize_colors
from . import variations as V
from .blend import align_flames, blend_flames
from .random_flame import RandomOptions, attractor_bounds, random_flame, random_xform
from .scene import Affine, Flame, XForm, identity_affine
from .xform_ops import MAX_XFORMS, add_xform, chaos_row, delete_xform

AFFINE, VARIATIONS, VARIATION_WEIGHTS, PARAMETERS = "affine", "variations", "variation_weights", "parameters"
WEIGHTS, COLORS, GRADIENT, XAOS, STRUCTURE, FINAL, DRIFT = "weights", "colors", "gradient", "xaos", "structure", "final", "drift"
KIND_LABELS = {
    AFFINE: "Triangles", VARIATIONS: "Variations", VARIATION_WEIGHTS: "Variation weights", PARAMETERS: "Parameters",
    WEIGHTS: "Transform weights", COLORS: "Colours", GRADIENT: "Gradient", XAOS: "Xaos", STRUCTURE: "Add / remove transforms",
    FINAL: "Final transform", DRIFT: "Drift to a random flame",
}
KIND_TIPS = {
    AFFINE: "Turn, scale, move or shear a few triangles (sometimes their post affine)",
    VARIATIONS: "Swap a variation for another one (the trend, when set, is preferred); sometimes add or drop one",
    VARIATION_WEIGHTS: "Re-weigh the variations of a transform",
    PARAMETERS: "Nudge variation parameters (declared ranges respected, integer parameters stay integers)",
    WEIGHTS: "Redistribute how often each transform is chosen",
    COLORS: "Move the transforms' colours along the gradient, and their colour speeds",
    GRADIENT: "Shift the gradient's hue, rotate it, or recolour it — the gradient editor follows",
    XAOS: "Re-weigh or cut the links between transforms",
    STRUCTURE: "Add a random transform or remove one",
    FINAL: "Perturb the final transform, or rarely add one",
    DRIFT: "Apophysis's classic mutation: blend towards a random flame by the strength",
}
ORDER = (AFFINE, VARIATIONS, VARIATION_WEIGHTS, PARAMETERS, WEIGHTS, COLORS, GRADIENT, XAOS, STRUCTURE, FINAL, DRIFT)
DEFAULT_KINDS = frozenset({AFFINE, VARIATIONS, VARIATION_WEIGHTS, PARAMETERS, WEIGHTS, COLORS, GRADIENT, DRIFT})
DEFAULT_STRENGTH = 0.35
ATTEMPTS = config.MUTATION_ATTEMPTS          # the tunables live in config.py
SCALE_LIMIT = config.MUTATION_SCALE_LIMIT
CHECK_POINTS, CHECK_STEPS = config.MUTATION_CHECK_POINTS, config.MUTATION_CHECK_STEPS
TREND_CHANCE = 0.6           # how often a swap / addition takes the trend variation when one is set


@dataclass(frozen=True)
class MutationOptions:
    """What a mutation may do (see the module docstring)."""
    strength: float = DEFAULT_STRENGTH
    kinds: frozenset = DEFAULT_KINDS
    trend: str | None = None
    pool: tuple[str, ...] = ()
    keep_count: bool = False
    keep_symmetry: bool = True
    check: bool = True

    def variation_pool(self) -> list[str]:
        """The variations swaps and additions draw from: the pool, else every loaded formula (all normal-kind ones)."""
        names = [n for n in self.pool if n in V.REGISTRY] or [n for n in V.catalogue() if V.REGISTRY[n].kind == V.NORMAL]
        return names or ["linear"]


@dataclass
class Offspring:
    """A mutant or a child: the flame and what was done to it (one line per change, for tooltips)."""
    flame: Flame
    notes: list[str] = field(default_factory=list)


Operator = Callable[[Flame, random.Random, float, MutationOptions], "str | None"]


# --- helpers -------------------------------------------------------------------------------------------------------
def _editable(flame: Flame, options: MutationOptions) -> list[int]:
    """Indices of the transforms an operator may change (symmetry transforms excluded when asked)."""
    return [i for i, x in enumerate(flame.xforms) if not (options.keep_symmetry and x.color_speed == 0.0)] or \
        list(range(len(flame.xforms)))


def _some(rng: random.Random, indices: list[int], strength: float) -> list[int]:
    """One transform, more as the strength grows."""
    count = max(1, min(len(indices), 1 + int(rng.random() * strength * 3)))
    return rng.sample(indices, count) if indices else []


def _pick_variation(rng: random.Random, options: MutationOptions) -> str:
    if options.trend and options.trend in V.REGISTRY and rng.random() < TREND_CHANCE:
        return options.trend
    return rng.choice(options.variation_pool())


def perturbed_affine(coefs: Affine, rng: random.Random, strength: float) -> tuple[Affine, str]:
    """`coefs` turned, scaled, moved and (sometimes) sheared by amounts that grow with `strength`; and a description."""
    a, b, c, d, e, f = coefs
    angle = rng.gauss(0.0, math.radians(35.0) * strength)
    scale = math.exp(rng.gauss(0.0, 0.25 * strength))
    ca, sa = math.cos(angle) * scale, math.sin(angle) * scale
    a, b, c, d = ca * a - sa * b, sa * a + ca * b, ca * c - sa * d, sa * c + ca * d       # rotate + scale the X and Y axes
    if rng.random() < 0.3:
        shear = rng.gauss(0.0, 0.15 * strength)
        c, d = c + shear * a, d + shear * b
    e += rng.gauss(0.0, 0.4 * strength)
    f += rng.gauss(0.0, 0.4 * strength)
    return (a, b, c, d, e, f), f"turned {math.degrees(angle):+.0f}°, scaled ×{scale:.2f}"


# --- the operators -------------------------------------------------------------------------------------------------
def _affine(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    notes = []
    for i in _some(rng, _editable(flame, options), strength):
        x = flame.xforms[i]
        x.coefs, what = perturbed_affine(x.coefs, rng, strength)
        if x.has_post() and rng.random() < 0.35:
            x.post, _ = perturbed_affine(x.post, rng, strength * 0.6)
            what += " (post too)"
        notes.append(f"transform {i + 1} {what}")
    return "; ".join(notes) or None


def _variations(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    indices = _editable(flame, options)
    if not indices:
        return None
    i = rng.choice(indices)
    x = flame.xforms[i]
    new = _pick_variation(rng, options)
    roll = rng.random()
    if x.variations and roll < 0.65:                          # swap, keeping the weight
        old = rng.choice(list(x.variations))
        if old == new:
            return None
        x.variations[new] = x.variations.pop(old) + x.variations.get(new, 0.0)
        what = f"{old} → {new}"
    elif roll < 0.9 or len(x.variations) <= 1:               # add
        x.variations[new] = x.variations.get(new, 0.0) + rng.uniform(0.1, 0.5) * (0.5 + strength)
        what = f"+ {new}"
    else:                                                    # drop one
        old = rng.choice(list(x.variations))
        x.variations.pop(old)
        what = f"− {old}"
    for key, value in V.REGISTRY[new].params.items():         # a new variation arrives with its defaults
        x.params.setdefault(key, value)
    return f"transform {i + 1}: {what}"


def _variation_weights(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    changed = []
    for i in _some(rng, _editable(flame, options), strength):
        x = flame.xforms[i]
        for name in list(x.variations):
            weight = x.variations[name] * math.exp(rng.gauss(0.0, 0.5 * strength))
            if rng.random() < 0.05 * strength:
                weight = -weight
            x.variations[name] = weight
        changed.append(str(i + 1))
    return f"variation weights of transform {', '.join(changed)}" if changed else None


def mutated_parameter(key: str, value: float, rng: random.Random, strength: float) -> float:
    """`value` of parameter `key` nudged: bounded parameters stay within their range (cyclic ones wrap), integer parameters
    (declared `VAR_INTEGER`: counts, modes, powers) stay integers and are never pushed to zero, the rest move in proportion
    to their size."""
    owner = V.parameter_owner(key)
    info = V.REGISTRY[owner].param_info.get(key) if owner in V.REGISTRY else None
    lo, hi = (info.min, info.max) if info is not None else (None, None)
    integer = info is not None and info.type == "int"
    if lo is not None and hi is not None and hi > lo:
        new = value + rng.gauss(0.0, 0.25 * strength * (hi - lo))
        new = lo + (new - lo) % (hi - lo) if info.cyclic else min(hi, max(lo, new))
    else:
        new = value + rng.gauss(0.0, strength * (0.5 * abs(value) + 0.5))
        new = max(lo, new) if lo is not None else new
        new = min(hi, new) if hi is not None else new
    if integer:
        new = float(round(new))
        if new == 0.0 and value != 0.0:          # a power or a count is never pushed to zero
            new = math.copysign(1.0, value)
    if info is not None and info.nonzero and new == 0.0:
        new = value
    return new


def _parameters(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    candidates = [(i, key) for i in _editable(flame, options) for name in flame.xforms[i].variations
                  for key in (V.REGISTRY[name].params if name in V.REGISTRY else {})]
    if not candidates:
        return None
    notes = []
    for i, key in rng.sample(candidates, max(1, min(len(candidates), 1 + int(rng.random() * strength * 4)))):
        x = flame.xforms[i]
        default = V.REGISTRY[V.parameter_owner(key)].params.get(key, 0.0) if V.parameter_owner(key) in V.REGISTRY else 0.0
        before = x.params.get(key, default)
        x.params[key] = mutated_parameter(key, before, rng, strength)
        notes.append(f"{key} {before:.3g} → {x.params[key]:.3g}")
    return "; ".join(notes)


def _weights(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    total = sum(x.weight for x in flame.xforms)
    if total <= 0:
        return None
    for x in flame.xforms:
        x.weight = max(1e-3, x.weight * math.exp(rng.gauss(0.0, 0.6 * strength)))
    scale = total / sum(x.weight for x in flame.xforms)
    for x in flame.xforms:
        x.weight *= scale
    return "transform weights redistributed"


def _colors(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    indices = _some(rng, _editable(flame, options), strength)
    for i in indices:
        x = flame.xforms[i]
        x.color = (x.color + rng.gauss(0.0, 0.3 * strength)) % 1.0
        x.color_speed = min(1.0, max(0.0, x.color_speed + rng.gauss(0.0, 0.2 * strength)))
    return f"colours of transform {', '.join(str(i + 1) for i in indices)}" if indices else None


def _gradient(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    gradient = flame.gradient
    roll = rng.random()
    if roll < 0.45:
        hue = round(rng.gauss(0.0, 120.0 * strength))
        adjustments, what = Adjustments(hue=max(-180, min(180, hue))), f"gradient hue {hue:+d}°"
    elif roll < 0.7:
        turn = round(rng.gauss(0.0, 80.0 * strength))                    # 1/400ths of the gradient (a whole turn is 400)
        adjustments, what = Adjustments(rotation=max(-ROTATION_RANGE, min(ROTATION_RANGE, turn))), f"gradient rotated {turn / 4:+.0f} %"
    elif roll < 0.85:
        saturation, luminance = round(rng.gauss(0.0, 40.0 * strength)), round(rng.gauss(0.0, 25.0 * strength))
        adjustments = Adjustments(saturation=max(-100, min(100, saturation)), luminance=max(-100, min(100, luminance)))
        what = f"gradient saturation {saturation:+d} %, luminance {luminance:+d} %"
    else:
        sparse = gradient.copy()
        sparse.stops = sparse.stops[::16]                                # a node every 16 entries recoloured, then re-sampled
        sparse.stops = randomize_colors(sparse, rng)
        flame.set_gradient(sparse)
        return "gradient recoloured from a new harmony"
    flame.set_gradient(apply_adjustments(gradient, adjustments))
    return what


def _xaos(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    n = len(flame.xforms)
    if n < 2:
        return None
    i = rng.choice(_editable(flame, options))
    row = chaos_row(flame.xforms[i], n)
    j = rng.randrange(n)
    if rng.random() < 0.3 * strength and sum(1 for v in row if v > 0) > 1:
        row[j] = 0.0
        what = f"link {i + 1} → {j + 1} cut"
    else:
        row[j] = max(0.0, row[j] * math.exp(rng.gauss(0.0, strength)) + (0.2 if row[j] == 0 else 0.0))
        what = f"link {i + 1} → {j + 1} now {row[j]:.2f}"
    flame.xforms[i].chaos = None if all(v == 1.0 for v in row) else row
    return what


def _structure(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    if options.keep_count:
        return None
    n = len(flame.xforms)
    if n > 2 and rng.random() < 0.4:
        index = rng.choice(_editable(flame, options))
        delete_xform(flame, index)
        return f"transform {index + 1} removed"
    if n >= MAX_XFORMS:
        return None
    xform = random_xform(rng, n, n + 1, options.variation_pool())
    if options.trend and options.trend in V.REGISTRY and rng.random() < TREND_CHANCE:
        xform.variations = {options.trend: 1.0}
        xform.params = dict(V.REGISTRY[options.trend].params)
    xform.weight = sum(x.weight for x in flame.xforms) / max(1, n) * rng.uniform(0.3, 1.0)
    add_xform(flame, xform)
    return f"transform {n + 1} added ({', '.join(xform.variations)})"


def _final(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    if flame.final is not None:
        flame.final.coefs, what = perturbed_affine(flame.final.coefs, rng, strength * 0.5)
        return f"final transform {what}"
    if rng.random() > 0.3 * strength:
        return None
    final = XForm(weight=1.0, color=0.0, color_speed=0.0, coefs=identity_affine(),
                  variations={"linear": 1.0 - 0.3 * strength, _pick_variation(rng, options): 0.3 * strength})
    for name in final.variations:
        final.params.update(V.REGISTRY[name].params if name in V.REGISTRY else {})
    flame.final = final
    return f"final transform added ({', '.join(final.variations)})"


def _drift(flame: Flame, rng: random.Random, strength: float, options: MutationOptions) -> str | None:
    n = len(flame.xforms)
    low, high = (n, n) if options.keep_count else (max(2, n - 1), n + 1)
    target = random_flame(rng, RandomOptions(options.variation_pool(), low, high, flame.camera.width, flame.camera.height))
    if options.trend and options.trend in V.REGISTRY:         # Apophysis: the random flame is made of the trend variation
        for x in target.xforms:
            x.variations = {options.trend: 1.0}
            x.params = dict(V.REGISTRY[options.trend].params)
    t = 0.5 * strength
    blended = blend_flames(align_flames([flame, target]), [1.0 - t, t])
    kept = [i for i, x in enumerate(blended.xforms) if x.weight > 1e-6] or list(range(n))
    flame.xforms = [blended.xforms[i] for i in kept]
    for x in flame.xforms:                                   # xaos rows lose the columns of dropped transforms
        x.chaos = [x.chaos[j] for j in kept] if x.chaos else None
    if flame.final is not None:                              # the parent's final drifts too; one only the target had is not taken
        flame.final = blended.final
    return f"drifted {t * 100:.0f} % towards a random flame"


OPERATORS: dict[str, Operator] = {
    AFFINE: _affine, VARIATIONS: _variations, VARIATION_WEIGHTS: _variation_weights, PARAMETERS: _parameters,
    WEIGHTS: _weights, COLORS: _colors, GRADIENT: _gradient, XAOS: _xaos, STRUCTURE: _structure, FINAL: _final, DRIFT: _drift,
}


# --- mutants --------------------------------------------------------------------------------------------------------
def mutate(parent: Flame, rng: random.Random, options: MutationOptions = MutationOptions()) -> Offspring:
    """One mutant: the parent with one to three of the enabled operators applied (the camera is the parent's)."""
    kinds = [k for k in ORDER if k in options.kinds]
    if not kinds or options.strength <= 0:
        return Offspring(parent.copy(), [])
    child = parent.copy()
    notes: list[str] = []
    for key in rng.sample(kinds, min(len(kinds), rng.choice((1, 1, 2, 2, 3)))):
        note = OPERATORS[key](child, rng, options.strength, options)
        if note:
            notes.append(note)
    child.camera = parent.camera.copy()
    return Offspring(child, notes)


def mutants(parent: Flame, count: int, seed: int | None = None, options: MutationOptions = MutationOptions()) -> list[Offspring]:
    """`count` mutants of `parent` (named `<parent> · m<n>`); each is rolled again while it is unstable (see the module
    docstring), gentler and gentler after half the attempts. The same seed gives the same mutants; each mutant has its
    own sub-seed, so they are independent."""
    rng = random.Random(seed)
    seeds = [rng.getrandbits(32) for _ in range(max(0, count))]
    references = [attractor_extent(parent)] if options.check else []
    out = []
    for i, sub in enumerate(seeds):
        sub_rng = random.Random(sub)

        def attempt(n: int, r=sub_rng) -> Offspring:
            gentle = options if n < ATTEMPTS // 2 else replace(options, strength=options.strength * 0.5 ** (n - ATTEMPTS // 2 + 1))
            return mutate(parent, r, gentle)
        offspring = settle(attempt, options.check, references, Offspring(parent.copy(), ["no stable variation found: a copy"]))
        offspring.flame.name = f"{parent.name} · m{i + 1}"
        out.append(offspring)
    return out


def settle(attempt: Callable[[int], Offspring], check: bool, references: list, fallback: Offspring) -> Offspring:
    """`attempt(n)` for n = 0, 1, … until its result `is_stable` (at most `ATTEMPTS` times); `fallback` when none is.
    Without `check` the first attempt is taken as it is. Shared by mutants and children."""
    if not check:
        return attempt(0)
    for n in range(ATTEMPTS):
        offspring = attempt(n)
        if is_stable(offspring.flame, references):
            return offspring
    return fallback


def attractor_extent(flame: Flame) -> tuple[float, float] | None:
    """(width, height) of the attractor from a short, cheap iteration; None when the system is unstable."""
    bounds = attractor_bounds(flame, CHECK_POINTS, CHECK_STEPS)
    return None if bounds is None else (bounds[1] - bounds[0], bounds[3] - bounds[2])


def is_stable(flame: Flame, references: list) -> bool:
    """Whether `flame` renders something sensible: it is renderable, its system neither blows up nor collapses, and its
    extent is within `SCALE_LIMIT` of one of the `references` (extents; None entries are ignored)."""
    if not flame.renderable():
        return False
    extent = attractor_extent(flame)
    if extent is None:
        return False
    known = [r for r in references if r is not None]
    if not known:
        return True
    return any(all(1.0 / SCALE_LIMIT <= e / max(r, 1e-12) <= SCALE_LIMIT for e, r in zip(extent, ref)) for ref in known)


__all__ = ["MutationOptions", "Offspring", "mutate", "mutants", "settle", "is_stable", "attractor_extent", "perturbed_affine",
           "mutated_parameter", "OPERATORS", "ORDER", "KIND_LABELS", "KIND_TIPS", "DEFAULT_KINDS", "DEFAULT_STRENGTH", "AFFINE",
           "VARIATIONS", "VARIATION_WEIGHTS", "PARAMETERS", "WEIGHTS", "COLORS", "GRADIENT", "XAOS", "STRUCTURE", "FINAL", "DRIFT"]
