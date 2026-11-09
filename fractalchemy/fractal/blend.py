"""Blending flames: make several flames structurally alike, then mix every number with weights. Pure Python + numpy.

Used by the animation (a frame is a weighted blend of its keyframes), by mutation (Apophysis's classic mutation: the
parent drifting towards a random flame) and by breeding (a child *interpolated* between two parents).

1. **Align** the flames so they have the same structure: the same number of transforms (a transform missing from one
   flame is padded with a copy of its neighbour's at weight and opacity 0, so it fades in or out), the same variations
   (missing ones at weight 0) and parameters (missing ones take the nearest flame's value, so a variation that fades in
   keeps its shape), xaos rows of the same length, a final transform everywhere if anywhere, palettes of one size.
2. **Blend** every number with the weights: affines, weights, colours, variation weights, parameters, xaos, camera
   (2D and 3D), colouring, palette entries. Things that cannot be blended (names, image size, tone curves) come from the
   flame with the largest weight.
"""

from __future__ import annotations

import numpy as np

from . import variations as V
from .scene import Affine, Camera, Coloring, Flame, XForm
from .xform_ops import chaos_row, new_final_xform


# --- alignment -------------------------------------------------------------------------------------------------
def align_flames(flames: list[Flame]) -> list[Flame]:
    """Copies of `flames` with identical structure (see the module docstring); the order is kept."""
    flames = [f.copy() for f in flames]
    if not flames:
        return flames
    count = max(len(f.xforms) for f in flames)
    for i in range(count):
        _align_xform_slot(flames, i)
    if any(f.final is not None for f in flames):
        for f in flames:
            if f.final is None:
                f.final = new_final_xform()
        _align_variations([f.final for f in flames])
    for f in flames:
        chaos_any = any(x.chaos is not None for g in flames for x in g.xforms)
        for x in f.xforms:
            x.chaos = chaos_row(x, count) if chaos_any else None
    size = max(len(f.palette) for f in flames)
    for f in flames:
        if len(f.palette) != size:
            f.palette = _resample_palette(f.palette, size)
    return flames


def _align_xform_slot(flames: list[Flame], i: int) -> None:
    """Make sure every flame has a transform at index `i` (padding with a silent copy of the nearest one)."""
    for j, f in enumerate(flames):
        if i < len(f.xforms):
            continue
        donor = next((g.xforms[i] for g in _by_distance(flames, j) if i < len(g.xforms)), None)
        padding = donor.copy() if donor is not None else XForm()
        padding.weight = 0.0
        padding.opacity = 0.0
        padding.chaos = None
        while len(f.xforms) <= i:
            f.xforms.append(padding.copy())
    _align_variations([f.xforms[i] for f in flames])


def _by_distance(items: list, j: int) -> list:
    """The other items ordered by distance (in the list) from index `j` — the nearest flames first."""
    return [items[k] for k in sorted((k for k in range(len(items)) if k != j), key=lambda k: abs(k - j))]


def _ordered_union(groups) -> list[str]:
    """Every name of every group once, in first-seen order."""
    names: list[str] = []
    for group in groups:
        names += [name for name in group if name not in names]
    return names


def _default_parameter(key: str) -> float:
    """The registry default of a parameter (0 when no formula declares it)."""
    owner = V.parameter_owner(key)
    var = V.REGISTRY.get(owner) if owner else None
    return var.params.get(key, 0.0) if var is not None else 0.0


def _align_variations(xforms: list[XForm]) -> None:
    """Give every xform the union of variation names (missing at 0) and parameter keys (missing: the nearest
    flame's value, else the formula's default)."""
    names = _ordered_union(x.variations for x in xforms)
    declared = [V.REGISTRY[n].params for n in names if n in V.REGISTRY]
    keys = _ordered_union([x.params for x in xforms] + declared)
    for j, x in enumerate(xforms):
        x.variations = {name: x.variations.get(name, 0.0) for name in names}
        neighbours = _by_distance(xforms, j)
        x.params = {key: x.params[key] if key in x.params
                    else next((o.params[key] for o in neighbours if key in o.params), _default_parameter(key))
                    for key in keys}


def _resample_palette(palette, size: int) -> list:
    colors = np.array(palette if len(palette) >= 2 else [(0, 0, 0), (255, 255, 255)], dtype=np.float64)
    idx = np.linspace(0, len(colors) - 1, size)
    out = np.stack([np.interp(idx, np.arange(len(colors)), colors[:, ch]) for ch in range(3)], axis=1)
    return [tuple(int(round(v)) for v in rgb) for rgb in out]


# --- blending --------------------------------------------------------------------------------------------------
def blend_flames(flames: list[Flame], weights: list[float]) -> Flame:
    """The weighted blend of *aligned* flames (weights sum to 1); one flame with weight 1 comes back unchanged."""
    if len(flames) == 1:
        return flames[0].copy()
    dominant = flames[max(range(len(flames)), key=lambda i: weights[i])]
    out = dominant.copy()
    out.xforms = [_blend_xforms([f.xforms[i] for f in flames], weights) for i in range(len(dominant.xforms))]
    out.final = _blend_xforms([f.final for f in flames], weights) if dominant.final is not None else None
    out.camera = _blend_camera([f.camera for f in flames], weights, dominant.camera)
    out.coloring = _blend_coloring([f.coloring for f in flames], weights, dominant.coloring)
    palettes = np.array([f.palette for f in flames], dtype=np.float64)
    mixed = np.tensordot(np.array(weights), palettes, axes=1)
    out.palette = [tuple(int(v) for v in rgb) for rgb in np.clip(np.rint(mixed), 0, 255)]
    unsupported = []
    for f in flames:
        unsupported += [u for u in f.unsupported if u not in unsupported]
    out.unsupported = unsupported
    return out


def _mix(values, weights: list[float]) -> float:
    return float(sum(w * float(v) for v, w in zip(values, weights)))


def _mix_affine(affines: list[Affine], weights: list[float]) -> Affine:
    return tuple(_mix([a[k] for a in affines], weights) for k in range(6))   # type: ignore[return-value]


def _blend_xforms(xforms: list[XForm], weights: list[float]) -> XForm:
    dominant = xforms[max(range(len(xforms)), key=lambda i: weights[i])]
    out = dominant.copy()
    out.weight = max(0.0, _mix([x.weight for x in xforms], weights))
    out.color = min(1.0, max(0.0, _mix([x.color for x in xforms], weights)))
    out.color_speed = min(1.0, max(0.0, _mix([x.color_speed for x in xforms], weights)))
    out.opacity = min(1.0, max(0.0, _mix([x.opacity for x in xforms], weights)))
    out.var_color = min(1.0, max(0.0, _mix([x.var_color for x in xforms], weights)))
    out.coefs = _mix_affine([x.coefs for x in xforms], weights)
    out.post = _mix_affine([x.post for x in xforms], weights)
    out.pre = _mix_affine([x.pre for x in xforms], weights)
    out.variations = {name: _mix([x.variations.get(name, 0.0) for x in xforms], weights) for name in dominant.variations}
    out.variations = {name: w for name, w in out.variations.items() if w != 0.0}
    out.params = {key: _mix([x.params.get(key, dominant.params[key]) for x in xforms], weights) for key in dominant.params}
    if dominant.chaos is not None:
        n = len(dominant.chaos)
        out.chaos = [max(0.0, _mix([chaos_row(x, n)[j] for x in xforms], weights)) for j in range(n)]
    return out


def _blend_camera(cameras: list[Camera], weights: list[float], dominant: Camera) -> Camera:
    out = dominant.copy()
    out.center = (_mix([c.center[0] for c in cameras], weights), _mix([c.center[1] for c in cameras], weights))
    out.scale = max(1e-9, _mix([c.scale for c in cameras], weights))
    for name in ("zoom", "rotate", "pitch", "yaw", "perspective", "zpos", "dof", "pitch_y"):
        setattr(out, name, _mix([getattr(c, name) for c in cameras], weights))
    return out


def _blend_coloring(colorings: list[Coloring], weights: list[float], dominant: Coloring) -> Coloring:
    out = dominant.copy()
    for name in ("brightness", "gamma", "gamma_threshold", "vibrancy", "contrast"):
        setattr(out, name, max(0.0, _mix([getattr(c, name) for c in colorings], weights)))
    out.gamma = max(0.01, out.gamma)
    out.background = tuple(int(min(255, max(0, round(_mix([c.background[ch] for c in colorings], weights))))) for ch in range(3))
    return out


__all__ = ["align_flames", "blend_flames"]
