"""A Flame pre-digested for rendering: resolved variations, selection table, palette array.

Both engines start from this so they agree on which variations run with which
parameters, in which order (pre affine → normal affine, then Apophysis's rule: `pre_`
variations first, then the rest, then `post_` ones, then the post affine), how xaos weights turn into selection probabilities, and how the
palette is indexed. Prepared (per-transform constant) values of formula-style
variations are computed here, once, and travel with the parameters.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ..fractal.scene import Affine, Flame, XForm
from ..fractal.variations import NORMAL, POST, PRE, REGISTRY, Variation, normalize, params_for, resolve

PREPARE_SEED = 12345   # prepare-time randomness (e.g. JuliaRandomN) is the same for every render of a flame


@dataclass(frozen=True)
class CompiledVariation:
    """One active variation on an xform, with its full parameter set (prepared values included)."""
    variation: Variation
    weight: float
    params: dict[str, float]


@dataclass(frozen=True)
class CompiledXForm:
    """An xform with variations resolved against the registry and ordered pre → normal → post."""
    coefs: Affine
    post: Affine
    pre_affine: Affine
    color: float
    color_speed: float
    opacity: float
    var_color: float
    pre_blur: float
    variations: tuple[CompiledVariation, ...]
    has_post: bool
    has_pre: bool

    @property
    def pre(self) -> tuple[CompiledVariation, ...]:
        return tuple(v for v in self.variations if v.variation.kind == PRE)

    @property
    def normal(self) -> tuple[CompiledVariation, ...]:
        return tuple(v for v in self.variations if v.variation.kind == NORMAL)

    @property
    def posts(self) -> tuple[CompiledVariation, ...]:
        return tuple(v for v in self.variations if v.variation.kind == POST)

    @property
    def direct_color(self) -> bool:
        return any(v.variation.dc for v in self.variations)

    @classmethod
    def build(cls, xform: XForm) -> "CompiledXForm":
        active = []
        pre_blur = 0.0
        rng = np.random.default_rng(PREPARE_SEED)
        variations, all_params, _unsupported = normalize(xform.variations, xform.params)   # aliases such as linear3D
        for name, weight in variations.items():
            var = resolve(name)
            if var is None or weight == 0:
                continue
            if name == "pre_blur":
                pre_blur = weight
                continue
            params = params_for(name, all_params)
            if var.prepare is not None:
                params.update(var.prepare(params, weight, tuple(xform.coefs), rng))
            params.update(var.tables)
            active.append(CompiledVariation(var, weight, params))
        order = {PRE: 0, NORMAL: 1, POST: 2}
        active.sort(key=lambda cv: order.get(cv.variation.kind, 1))
        return cls(tuple(xform.coefs), tuple(xform.post), tuple(xform.pre), xform.color, min(1.0, max(0.0, xform.color_speed)),
                   min(1.0, max(0.0, xform.opacity)), xform.var_color, pre_blur, tuple(active), xform.has_post(), xform.has_pre())


@dataclass(frozen=True)
class CompiledFlame:
    """Everything an engine needs, independent of output size."""
    xforms: tuple[CompiledXForm, ...]
    final: CompiledXForm | None
    selection: np.ndarray          # (N, N) cumulative probabilities: row = previous xform
    palette: np.ndarray            # (256, 3) float32 in 0..1
    notes: tuple[str, ...]         # remarks for the user (unsupported / approximated variations)

    @property
    def count(self) -> int:
        return len(self.xforms)

    @classmethod
    def build(cls, flame: Flame) -> "CompiledFlame":
        """Compile; raises ValueError for a flame with no usable transform."""
        usable = [x for x in flame.xforms if x.weight > 0]
        if not usable:
            raise ValueError(f"'{flame.name}' has no transform with a positive weight")
        xforms = tuple(CompiledXForm.build(x) for x in usable)
        final = CompiledXForm.build(flame.final) if flame.final is not None else None
        if final is not None and _is_identity(final):
            final = None  # a do-nothing final xform: skip the work
        return cls(xforms, final, selection_table(usable), palette_array(flame), tuple(_notes(flame)))


def _is_identity(xform: CompiledXForm) -> bool:
    """True for `linear=1` with identity affines and no colour blending — what Apophysis writes for an unused final."""
    only_linear = len(xform.variations) == 1 and xform.variations[0].variation.name == "linear" and xform.variations[0].weight == 1.0
    return (only_linear and not xform.pre_blur and not xform.has_post and not xform.has_pre and xform.color_speed == 0.0
            and tuple(xform.coefs) == (1.0, 0.0, 0.0, 1.0, 0.0, 0.0))


def selection_table(xforms: list[XForm]) -> np.ndarray:
    """Cumulative choice probabilities; row `i` applies after xform `i` (xaos), as in flam3."""
    n = len(xforms)
    weights = np.array([x.weight for x in xforms], dtype=np.float64)
    table = np.empty((n, n), dtype=np.float64)
    for i, x in enumerate(xforms):
        chaos = np.ones(n) if x.chaos is None else np.array((list(x.chaos) + [1.0] * n)[:n], dtype=np.float64)
        row = weights * np.clip(chaos, 0.0, None)
        if row.sum() <= 0:
            row = weights.copy()  # a dead-end xaos row: fall back to plain weights
        cum = np.cumsum(row / row.sum())
        cum[-1] = 1.0
        table[i] = cum
    return table


def palette_array(flame: Flame) -> np.ndarray:
    colors = np.array(flame.palette if len(flame.palette) >= 2 else [(0, 0, 0), (255, 255, 255)], dtype=np.float32) / 255.0
    if len(colors) != 256:  # resample to 256 entries so index lookups are uniform
        idx = np.linspace(0, len(colors) - 1, 256)
        colors = np.stack([np.interp(idx, np.arange(len(colors)), colors[:, ch]) for ch in range(3)], axis=1).astype(np.float32)
    return colors


def _notes(flame: Flame) -> list[str]:
    notes = []
    if flame.unsupported:
        notes.append("Unsupported variations ignored: " + ", ".join(flame.unsupported))
    approximated = sorted({REGISTRY[n].note for x in (*flame.xforms, *([flame.final] if flame.final else []))
                           for n in x.variations if n in REGISTRY and REGISTRY[n].note})
    notes.extend(approximated)
    return notes
