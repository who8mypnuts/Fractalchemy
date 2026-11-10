"""Symmetry transforms: flam3's `flam3_add_symmetry`, as the Random Batch, the scripting API (`add_symmetry`) and the
*Make rotational symmetry* template use it.

`add_symmetry(flame, order)` adds plain linear transforms that make the attractor symmetric:

* `order ≤ −1` — a bilateral mirror (x → −x) first, then, for |order| ≥ 2, the rotations too (*dihedral* symmetry);
* `order ≥ 2` — |order| − 1 copies rotated by 360°·k / |order| (*rotational* symmetry);
* `order` 0 or 1 adds nothing.

Every added transform has weight 1, colour speed 0 (Apophysis's `symmetry = 1`, so it keeps the colour of the point it
moves) and colours spread over 0..1, as flam3 does. `random_symmetry(rng)` draws an order from flam3's distribution
(mostly small orders, mirrors as often as not).
"""

from __future__ import annotations

import math
import random

from .scene import Flame, XForm

SYMMETRY_KINDS = ("none", "random", "bilateral", "rotational", "dihedral")
FLAM3_DISTRIBUTION = (-4, -3, -2, -2, -2, -1, -1, -1, 2, 2, 2, 3, 3, 4, 4)


def _linear(coefs, color: float) -> XForm:
    return XForm(weight=1.0, color=color, color_speed=0.0, coefs=coefs, variations={"linear": 1.0})


def _append(flame: Flame, xform: XForm) -> None:
    """Append `xform`, giving every existing xaos row a column for it (1 = normal)."""
    for x in flame.xforms:
        if x.chaos is not None:
            x.chaos.append(1.0)
    flame.xforms.append(xform)


def add_symmetry(flame: Flame, order: int) -> int:
    """Add the symmetry transforms for `order` (see the module docstring); returns how many were added."""
    order = int(order)
    added = 0
    if order <= -1:
        _append(flame, _linear((-1.0, 0.0, 0.0, 1.0, 0.0, 0.0), 1.0))
        added += 1
    n = abs(order)
    for k in range(1, n):
        angle = 2.0 * math.pi * k / n
        c, s = round(math.cos(angle), 6), round(math.sin(angle), 6)
        color = 0.0 if n < 3 else (k - 1.0) / (n - 2.0)
        _append(flame, _linear((c, s, -s, c, 0.0, 0.0), color))
        added += 1
    return added


def random_symmetry(rng: random.Random) -> int:
    """An order drawn as flam3 draws it: usually from `FLAM3_DISTRIBUTION`, sometimes from a wider range."""
    if rng.random() < 0.5:
        return rng.choice(FLAM3_DISTRIBUTION)
    if rng.randrange(32):
        return rng.randrange(13) - 6
    return rng.randrange(51) - 25


def symmetry_order(kind: str, rng: random.Random, orders: tuple[int, int] = (2, 6)) -> int:
    """The order for a Random Batch choice (`SYMMETRY_KINDS`); `orders` is the range for rotational / dihedral."""
    lo, hi = sorted((max(2, int(orders[0])), max(2, int(orders[1]))))
    if kind == "random":
        return random_symmetry(rng)
    if kind == "bilateral":
        return -1
    if kind == "rotational":
        return rng.randint(lo, hi)
    if kind == "dihedral":
        return -rng.randint(lo, hi)
    return 0


__all__ = ["add_symmetry", "random_symmetry", "symmetry_order", "SYMMETRY_KINDS", "FLAM3_DISTRIBUTION"]
