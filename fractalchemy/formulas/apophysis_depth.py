"""Apophysis 7X's depth rule for its built-in variations.

Apophysis ships many community plugins as built-ins (`src/Variations/*.pas`). Those Pascal
versions add `vvar · FTz` to the depth (or scale it, for `pre_` / `post_` ones), which the
original 2D plugin sources never did. Flames made in Apophysis expect the built-in behaviour,
so the loader marks these names `z = pass` after the library is loaded.
"""

from __future__ import annotations

from dataclasses import replace

from ..fractal import variations as V

# names whose Apophysis built-in has `FPz := FPz + vvar * FTz` (or the pre/post equivalent)
APOPHYSIS_Z_PASS = frozenset({
    "blur_zoom", "blur_pixelize", "blur_circle", "polar2", "scry", "escher", "log", "separation", "loonie", "foci",
    "auger", "bwraps", "cross", "lazysusan", "ngon", "wedge", "splits", "rectangles", "fan2", "rings2", "pdj",
    "elliptic", "mobius", "bipolar", "curl", "julian", "juliascope", "hemisphere", "radial_blur", "crop",
    "pre_disc", "pre_sinusoidal", "pre_spherical", "pre_bwraps", "post_bwraps",
})


def apply_depth_rules() -> list[str]:
    """Mark the registered Apophysis built-ins that pass the depth through; returns the names changed."""
    changed = []
    for name in APOPHYSIS_Z_PASS:
        var = dict.get(V.REGISTRY, name)
        if var is not None and var.z == V.Z_NONE:
            V.register(replace(var, z=V.Z_PASS))
            changed.append(name)
    return changed
