"""Write the generated half of docs/state-machines.md from the specs in `fractalchemy.machines.specs`.

    python tools/state_machines.py            # rewrite the section between the markers
    python tools/state_machines.py --check    # exit 1 if the document is out of date (the tests do the same)

Only the text between `BEGIN` and `END` is replaced; the rest of the document (the introduction and the inventory of
implicit lifecycles) is written by hand.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from fractalchemy.machines import ALL, MachineSpec  # noqa: E402

DOC = ROOT / "docs" / "state-machines.md"
BEGIN = "<!-- BEGIN GENERATED: tools/state_machines.py -->"
END = "<!-- END GENERATED -->"


def spec_markdown(spec: MachineSpec) -> str:
    """One machine: what it models, its states with their meanings, every transition, and a diagram."""
    lines = [f"### {spec.name}", "", f"*Owner:* `{spec.owner}` · *starts in* `{spec.initial}`", "", spec.doc, "",
             "| State | Meaning | Accepts |", "|---|---|---|"]
    for state in spec.states:
        accepts = ", ".join(f"`{e}` → `{t}`" for (s, e), t in spec.transitions.items() if s == state) or "—"
        lines.append(f"| `{state}` | {spec.meanings.get(state, '')} | {accepts} |")
    lines += ["", "```mermaid", spec.mermaid(), "```", ""]
    return "\n".join(lines)


def generated() -> str:
    """The whole generated section (markers included)."""
    body = "\n".join(spec_markdown(spec) for spec in ALL)
    return f"{BEGIN}\n\n{body}\n{END}"


def updated(text: str) -> str:
    """`text` with its generated section replaced."""
    start, end = text.index(BEGIN), text.index(END) + len(END)
    return text[:start] + generated() + text[end:]


def main(argv: list[str]) -> int:
    text = DOC.read_text(encoding="utf-8")
    new = updated(text)
    if "--check" in argv:
        if new != text:
            print(f"{DOC} is out of date: run python tools/state_machines.py")
            return 1
        return 0
    DOC.write_text(new, encoding="utf-8")
    print(f"wrote {DOC.relative_to(ROOT)} ({len(ALL)} machines)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
