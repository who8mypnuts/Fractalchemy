"""Readable names for the main fractal's undo steps ("Gamma", "Triangle 3", "Adopt mutant", …).

`FractalDocument` records every edit under a *kind* — a short machine string that also decides which edits coalesce
into one step (`coloring:gamma`, `affine:coefs:2`, `drag:post:1:17`, `variation:julian:0`, …). `undo_label(kind)` turns
a kind into the text the *History* tab and the *Undo / Redo* action texts show. Qt-free; a table of prefix handlers,
so a new kind of edit needs one entry here (the tests check every kind the document produces has a specific label).
"""

from __future__ import annotations

from typing import Callable

GENERIC_LABEL = "Edit"
AFFINE_NAMES = {"pre": "pre-affine", "coefs": "triangle", "post": "post-affine"}
TRIANGLE_OPS = {"rotate": "Rotate", "move": "Move", "scale": "Scale", "flip": "Flip", "reset": "Reset",
                "reset-rotation": "Reset rotation of", "reset-scale": "Reset scale of", "reset-position": "Reset position of",
                "reset-corner": "Reset corner of", "snap-corner": "Snap corner of", "unit-corner": "Unit corner of",
                "drag": "Drag", "paste": "Paste", "corner": "Corner of", "vector": "Vector of"}
COLORING_NAMES = {"brightness": "Brightness", "gamma": "Gamma", "gamma_threshold": "Gamma threshold", "vibrancy": "Vibrancy",
                  "contrast": "Contrast", "background": "Background", "curves": "Curves"}
SIMPLE = {
    "view": "Camera", "camera3d": "3D camera", "curves-reset": "Reset curves", "palette": "Gradient", "paste": "Paste parameters",
    "script": "Script", "add-xform": "Add transform", "duplicate-xform": "Duplicate transform", "link-xform": "Add linked transform",
    "delete-xform": "Delete transform", "final-xform": "Final transform", "area-weights": "Weights from areas",
    "mutate": "Adopt mutant", "breed": "Adopt child", "explore": "Adopt explored variation", "new-flame": "New flame", "reset-all": "Reset all triangles",
    "use-current": "Use the main window's fractal", "edit": GENERIC_LABEL, "load": "Opened", "console": "Console",
}


def _transform(key: str) -> str:
    """`2` → "3" (1-based), the final transform's key → "final"."""
    try:
        return str(int(key) + 1)
    except (TypeError, ValueError):
        return "final"


def _coloring(rest: list[str]) -> str:
    names = [n for n in ",".join(rest).split(",") if n]
    if len(names) == 1:
        return COLORING_NAMES.get(names[0], names[0].replace("_", " ").capitalize())
    return "Colouring"


def _affine(rest: list[str]) -> str:
    which = rest[0] if rest else "coefs"
    key = rest[1] if len(rest) > 1 else ""
    name = AFFINE_NAMES.get(which, "triangle")
    return f"{name.capitalize()} {_transform(key)}"


def _triangle_op(op: str, rest: list[str]) -> str:
    """Transform Editor operations: `<op>:<mode>:<key>:<serial>` (and `corner:<corner>:<key>`)."""
    if op == "corner":                                # `corner:<corner>:<key>` — a corner typed in the Triangle tab
        return f"Corner of triangle {_transform(rest[1] if len(rest) > 1 else '')}"
    mode = rest[0] if rest else "coefs"
    key = rest[1] if len(rest) > 1 else ""
    if op == "paste":                                 # `paste:<key>:<id>` — a pasted triangle
        return f"Paste triangle {_transform(mode)}"
    return f"{TRIANGLE_OPS[op]} {AFFINE_NAMES.get(mode, 'triangle')} {_transform(key)}"


def _fields(rest: list[str]) -> str:
    names = rest[0].split(",") if rest else []
    key = rest[1] if len(rest) > 1 else ""
    what = names[0].replace("_", " ").capitalize() if len(names) == 1 else "Transform"
    return f"{what} {_transform(key)}"


HANDLERS: dict[str, Callable[[list[str]], str]] = {
    "coloring": _coloring,
    "curve": lambda rest: f"{(rest[0] if rest else 'overall').capitalize()} curve",
    "affine": _affine,
    "fields": _fields,
    "variation": lambda rest: f"{rest[0] if rest else 'Variation'} on {_transform(rest[1] if len(rest) > 1 else '')}",
    "set-variations": lambda rest: f"Variations of {_transform(rest[0] if rest else '')}",
    "clear-variations": lambda rest: f"Clear variations of {_transform(rest[0] if rest else '')}",
    "param": lambda rest: f"{rest[0] if rest else 'Parameter'} on {_transform(rest[1] if len(rest) > 1 else '')}",
    "chaos": lambda rest: f"Xaos {_transform(rest[0] if rest else '')} → {_transform(rest[1] if len(rest) > 1 else '')}",
    "chaos-all": lambda rest: f"All xaos of {_transform(rest[0] if rest else '')}",
    "rig": lambda rest: f"Test rig: {':'.join(rest)}",
    **{op: (lambda rest, o=op: _triangle_op(o, rest)) for op in TRIANGLE_OPS},
}


def undo_label(kind: str, detail: str = "") -> str:
    """The readable name of an edit of `kind`; `detail` (a script's name, a console line) is appended after a colon."""
    head, *rest = (kind or "").split(":")
    if head in SIMPLE and (not rest or head not in HANDLERS):
        label = SIMPLE[head]
    elif head in HANDLERS:
        try:
            label = HANDLERS[head](rest)
        except (IndexError, KeyError):
            label = GENERIC_LABEL
    else:
        label = GENERIC_LABEL
    return f"{label}: {detail}" if detail else label


def show_undo_state(document, undo_action, redo_action) -> None:
    """Enable a window's Undo / Redo actions and name them after the steps they would take ("Undo Gamma")."""
    undo_action.setEnabled(document.can_undo)
    redo_action.setEnabled(document.can_redo)
    undo_action.setText(f"Undo {document.undo_label}" if document.can_undo else "Undo")
    redo_action.setText(f"Redo {document.redo_label}" if document.can_redo else "Redo")


def is_specific(kind: str) -> bool:
    """True when `kind` has a label of its own (tests use it to catch new kinds without one)."""
    head = (kind or "").split(":")[0]
    return head in SIMPLE or head in HANDLERS


__all__ = ["undo_label", "is_specific", "show_undo_state", "GENERIC_LABEL"]
