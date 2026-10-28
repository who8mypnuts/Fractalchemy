"""Write docs/scripting.md from the scripting documentation database (the same data the Script Editor shows).

    python tools/scripting_reference.py
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fractalchemy.scripting import docs as D  # noqa: E402
from fractalchemy.scripting.templates import builtin_templates  # noqa: E402


def entry_md(name: str, entry: D.Entry) -> str:
    sig = entry.signature(name)
    line = f"* `{sig}`" + (f" → `{entry.returns}`" if entry.returns else "") + (" *(read-only)*" if entry.readonly else "")
    if entry.desc:
        line += f" — {entry.desc}"
    out = [line]
    for p in entry.params:
        if p.desc or p.options:
            options = ""
            if p.options == D.VARIATIONS:
                options = " (any loaded formula name)"
            elif p.options == D.PARAMS:
                options = " (any variation parameter name)"
            elif isinstance(p.options, tuple):
                options = " (" + " / ".join(p.options) + ")"
            elif p.options == D.CURVE_CHANNELS:
                options = " (overall / red / green / blue / alpha)"
            out.append(f"  * `{p.label}` `{p.type}`: {p.desc}{options}")
    if entry.example:
        out.append("  ```python\n  " + entry.example.replace("\n", "\n  ") + "\n  ```")
    return "\n".join(out)


def main() -> None:
    lines = [D.GUIDE.strip(), "", "## Reference", "",
             "Everything below is a global name in a script. Types (`Transform`, `Camera`, …) are described after the functions.", ""]
    for title, names in D.CATEGORIES:
        lines += [f"### {title}", ""]
        for name in names:
            lines.append(entry_md(name, D.GLOBALS[name]))
        lines.append("")
    lines += ["## Types", ""]
    for type_name, doc in D.TYPES.items():
        if doc.builtin:
            continue
        lines += [f"### {type_name}", "", doc.desc, ""]
        if doc.dynamic:
            lines += ["Any loaded formula name is a valid key (`t.variations['julian'] = 1`).", ""]
        for name, entry in doc.members.items():
            lines.append(entry_md(name, entry))
        lines.append("")
    lines += ["## Built-in templates", ""]
    for t in builtin_templates():
        lines.append(f"* **{t.name}** ({t.category}) — {t.description}")
    target = Path(__file__).resolve().parents[1] / "docs" / "scripting.md"
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {target}")


if __name__ == "__main__":
    main()
