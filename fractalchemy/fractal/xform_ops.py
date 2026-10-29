"""Structural edits of a flame's transforms, the way Apophysis's editor does them. Pure Python, no Qt.

Adding, duplicating, linking and deleting transforms keep the xaos (chaos) rows of every transform
consistent: a row lists the relative weight of choosing each transform *next*, so it must gain or
lose a column whenever a transform comes or goes. The functions edit the flame in place and return
the index of the transform to select afterwards.
"""

from __future__ import annotations

from .scene import Flame, XForm, identity_affine

DEFAULT_WEIGHT = 0.5
MAX_XFORMS = 100


def new_xform() -> XForm:
    """What Apophysis's *Add transform* makes: the reference triangle, `linear = 1`, weight 0.5."""
    return XForm(weight=DEFAULT_WEIGHT, color=0.0, color_speed=0.5, variations={"linear": 1.0})


def new_final_xform() -> XForm:
    """An identity final transform (colour speed 0 — Apophysis's `symmetry = 1` — so it leaves the colour alone)."""
    return XForm(weight=1.0, color=0.0, color_speed=0.0, variations={"linear": 1.0})


def chaos_row(xform: XForm, count: int) -> list[float]:
    """The xform's xaos row padded (with 1s) or cut to `count` entries."""
    row = list(xform.chaos) if xform.chaos else []
    return (row + [1.0] * count)[:count]


def _tidy_chaos(flame: Flame) -> None:
    """Drop rows that are all ones (the default) and pad the others to the transform count."""
    n = len(flame.xforms)
    for x in flame.xforms:
        if x.chaos is not None:
            row = chaos_row(x, n)
            x.chaos = None if all(v == 1.0 for v in row) else row


def add_xform(flame: Flame, xform: XForm | None = None) -> int:
    """Append a fresh transform (or the given one); returns its index."""
    if len(flame.xforms) >= MAX_XFORMS:
        return len(flame.xforms) - 1
    _insert(flame, xform if xform is not None else new_xform())
    return len(flame.xforms) - 1


def duplicate_xform(flame: Flame, index: int) -> int:
    """Append a copy of transform `index` (xaos links to and from it copied too); returns the copy's index."""
    if len(flame.xforms) >= MAX_XFORMS or not 0 <= index < len(flame.xforms):
        return index
    n = len(flame.xforms)
    copy = flame.xforms[index].copy()
    for x in flame.xforms:   # every row gets a column for the copy, equal to the column of the original
        if x.chaos is not None:
            row = chaos_row(x, n)
            x.chaos = row + [row[index]]
    if copy.chaos is not None:
        row = chaos_row(copy, n)
        copy.chaos = row + [row[index]]
    flame.xforms.append(copy)
    _tidy_chaos(flame)
    return n


def add_linked_xform(flame: Flame, index: int) -> int:
    """Apophysis's *Add linked transform*: a new transform that follows `index` and takes over its outgoing links.

    After this, transform `index` leads only to the new one, the new one leads wherever `index` used to,
    nothing else leads to the new one, and the new one takes `index`'s opacity (which becomes 0).
    Returns the new transform's index.
    """
    if len(flame.xforms) >= MAX_XFORMS or not 0 <= index < len(flame.xforms):
        return index
    n = len(flame.xforms)
    source = flame.xforms[index]
    linked = new_xform()
    linked.color_speed = 0.0          # Apophysis: symmetry 1, so the colour passes straight through
    linked.opacity = source.opacity
    source_row = chaos_row(source, n)
    for x in flame.xforms:
        x.chaos = chaos_row(x, n) + [0.0]
    linked.chaos = source_row + [0.0]
    source.chaos = [0.0] * n + [1.0]
    source.opacity = 0.0
    flame.xforms.append(linked)
    _tidy_chaos(flame)
    return n


def delete_xform(flame: Flame, index: int) -> int:
    """Remove transform `index` (never the last remaining one) and its xaos column; returns the index to select."""
    if len(flame.xforms) <= 1 or not 0 <= index < len(flame.xforms):
        return index
    n = len(flame.xforms)
    del flame.xforms[index]
    for x in flame.xforms:
        if x.chaos is not None:
            row = chaos_row(x, n)
            del row[index]
            x.chaos = row
    _tidy_chaos(flame)
    return min(index, len(flame.xforms) - 1)


def set_final_enabled(flame: Flame, enabled: bool) -> None:
    """Give the flame an identity final transform, or remove the one it has."""
    if enabled and flame.final is None:
        flame.final = new_final_xform()
    elif not enabled:
        flame.final = None


def _insert(flame: Flame, xform: XForm) -> None:
    n = len(flame.xforms)
    for x in flame.xforms:
        if x.chaos is not None:
            x.chaos = chaos_row(x, n) + [1.0]
    flame.xforms.append(xform)
    _tidy_chaos(flame)


def reset_affine(xform: XForm, which: str) -> None:
    """Put one of the transform's affines (`pre`, `coefs`, `post`) back to the identity."""
    setattr(xform, which, identity_affine())


def area_weights(flame: Flame) -> None:
    """Apophysis's *auto weights*: each transform's weight proportional to its triangle's area."""
    from .triangles import affine_to_triangle, area
    areas = [area(affine_to_triangle(x.coefs)) for x in flame.xforms]
    total = sum(areas)
    if total <= 0:
        return
    for x, a in zip(flame.xforms, areas):
        x.weight = a / total


__all__ = ["DEFAULT_WEIGHT", "MAX_XFORMS", "new_xform", "new_final_xform", "chaos_row", "add_xform", "duplicate_xform",
           "add_linked_xform", "delete_xform", "set_final_enabled", "reset_affine", "area_weights"]
