"""Preset blocks as text: building them, naming keyframes, finding and replacing them in fragment source.

A preset is FragM's parameter store inside the fragment:

    #preset Default
    FOV = 0.4
    Eye = 5.58,4.88,-6.71
    #endpreset

`KeyFrame.nnnn` presets hold the camera only and become the control points of the camera path; `Range…` presets
hold easing-curve settings only. These helpers are pure text so the document (which edits the editor's text) and
the tests can share them.
"""

from __future__ import annotations

import re

KEYFRAME_PREFIX = "KeyFrame."
RANGE_PREFIX = "Range"
RE_PRESET_START = re.compile(r"^\s*#preset\s+(.*?)\s*$", re.IGNORECASE | re.MULTILINE)
RE_PRESET_END = re.compile(r"^\s*#endpreset\s*$", re.IGNORECASE | re.MULTILINE)


def is_keyframe(name: str) -> bool:
    return name.lower().startswith(KEYFRAME_PREFIX.lower())


def is_range(name: str) -> bool:
    return name.lower().startswith(RANGE_PREFIX.lower())


def keyframe_index(name: str) -> int:
    """The number of `KeyFrame.0012` (0 when unreadable) — the sort key of the camera path."""
    try:
        return int(name.split(".", 1)[1])
    except (IndexError, ValueError):
        return 0


def keyframe_name(index: int) -> str:
    """`KeyFrame.0001` for 1 (FragM pads to four digits)."""
    return f"{KEYFRAME_PREFIX}{index:04d}"


def next_keyframe_name(existing: list[str]) -> str:
    """The name after the highest existing keyframe (FragM: count + 1)."""
    return keyframe_name(len([n for n in existing if is_keyframe(n)]) + 1)


def preset_block(name: str, body: str) -> str:
    """The text FragM inserts: a blank line, the block, a blank line."""
    return f"\n#preset {name}\n{body.rstrip()}\n#endpreset\n"


def find_preset(text: str, name: str) -> tuple[int, int] | None:
    """`(start, end)` character offsets of the whole `#preset name … #endpreset` block in `text`, or None."""
    for match in RE_PRESET_START.finditer(text):
        if match.group(1).strip().lower() != name.lower():
            continue
        end = RE_PRESET_END.search(text, match.end())
        return match.start(), (end.end() if end else len(text))
    return None


def replace_preset(text: str, name: str, body: str) -> str:
    """`text` with the named preset's body replaced (the block is appended when there is none)."""
    span = find_preset(text, name)
    block = preset_block(name, body).strip("\n")
    if span is None:
        return text.rstrip("\n") + "\n" + preset_block(name, body)
    return text[:span[0]] + block + text[span[1]:]


def remove_preset(text: str, name: str) -> str:
    span = find_preset(text, name)
    if span is None:
        return text
    return (text[:span[0]].rstrip("\n") + "\n" + text[span[1]:].lstrip("\n")).rstrip("\n") + "\n"


def preset_names(text: str) -> list[str]:
    """Every preset name in `text`, in order of appearance."""
    return [m.group(1).strip() for m in RE_PRESET_START.finditer(text)]


def selected_preset_name(selection: str) -> str | None:
    """The preset name when the editor's selection holds a whole block (FragM's F8-on-selection rule)."""
    match = RE_PRESET_START.search(selection)
    if match and RE_PRESET_END.search(selection, match.end()):
        return match.group(1).strip()
    return None


__all__ = ["is_keyframe", "is_range", "keyframe_index", "keyframe_name", "next_keyframe_name", "preset_block", "find_preset",
           "replace_preset", "remove_preset", "preset_names", "selected_preset_name", "KEYFRAME_PREFIX", "RANGE_PREFIX"]
