"""Editing a uniform's annotation in the source text — the slider bounds typed in a slider's context menu.

FragM's `comboSliderBoundsChanged` finds the declaration line of the parameter and rewrites the number that is the
lower or upper bound of the edited component; the fragment is rebuilt afterwards so the widget takes the new range.
"""

from __future__ import annotations

import re

from .preprocessor import RE_FLOAT1, RE_FLOAT2, RE_FLOAT3, RE_FLOAT4, RE_FLOATCOLOR, RE_INT

VECTOR_REGEXES = {RE_FLOAT2: 2, RE_FLOAT3: 3, RE_FLOAT4: 4}


def _bound_group(regex: re.Pattern, component: int, which: int) -> int | None:
    """The regex group holding the requested bound (`which`: 1 lower, 2 upper) of 1-based `component`."""
    if regex in VECTOR_REGEXES:
        n = VECTOR_REGEXES[regex]
        if not 1 <= component <= n:
            return None
        return 2 + component if which == 1 else 2 + 2 * n + component
    if regex in (RE_FLOAT1, RE_FLOATCOLOR):
        return 3 if which == 1 else 5
    if regex is RE_INT:
        return 2 if which == 1 else 4
    return None


def rewrite_bound(text: str, name: str, component: int, which: int, value: float) -> str | None:
    """`text` with the bound of `name` replaced, or None when the declaration is not in `text` (it is in an include)."""
    lines = text.split("\n")
    declaration = re.compile(rf"^\s*uniform\s+\S+\s+{re.escape(name)}\s*;")
    for index, line in enumerate(lines):
        if not declaration.match(line):
            continue
        for regex in (RE_FLOAT1, RE_FLOAT2, RE_FLOAT3, RE_FLOAT4, RE_FLOATCOLOR, RE_INT):
            match = regex.match(line)
            if not match:
                continue
            group = _bound_group(regex, component, which)
            if group is None or match.group(group) is None:
                return None
            number = str(int(value)) if regex is RE_INT else f"{value:g}"
            lines[index] = line[:match.start(group)] + match.group(group).replace(match.group(group).strip(), number) + line[match.end(group):]
            return "\n".join(lines)
        return None
    return None


__all__ = ["rewrite_bound"]
