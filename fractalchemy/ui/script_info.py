"""The facts the Script Editor's *Info* tab shows: the script (name, file, metadata, size, what it does and uses), its
last run, and the fractal in the main window."""

from __future__ import annotations

import re
from html import escape
from typing import TYPE_CHECKING

from ..scripting import docs as D
from ..scripting import templates as T
from ..widgets.theming import colored_html

if TYPE_CHECKING:
    from .script_editor_window import ScriptEditorWindow


def _tags(names: list[str]) -> str:
    return " ".join(f"<code>{escape(n)}</code>" for n in names) or "—"


def parameters_note(window: "ScriptEditorWindow") -> str:
    """", 3 parameters (live)" — or why they are not live — for the Interaction row."""
    live = getattr(window, "live", None)
    if live is None or not live.specs:
        return ""
    n = len(live.specs)
    how = "live" if live.live else (live.reason or "not live")
    return f", {n} parameter{'s' if n != 1 else ''} ({how})"


def info_facts(w: "ScriptEditorWindow") -> list[tuple[str, list[tuple[str, str]]]]:
    """(section, [(label, HTML value)]) for the Info tab."""
    code = w.editor.text()
    meta = T.parse_metadata(code)
    lines = code.split("\n")
    code_lines = [line for line in lines if line.strip() and not line.lstrip().startswith("#")]
    used = [n for n in D.GLOBALS if re.search(rf"(?<![\w.]){re.escape(n)}\b", code)]
    functions = re.findall(r"^\s*def\s+(\w+)", code, re.MULTILINE)
    prompts = bool(re.search(r"\b(input_text|input_number|confirm)\s*\(", code))
    updates = bool(re.search(r"\b(update|UpdateFlame)\s*\(", code))
    template = next((t for t in w.all_templates() if t.id == w.template_id), None) if w.template_id else None
    script_rows = [
        ("Name", escape(meta.get("name") or w.script_name)),
        ("File", escape(str(w.script_path)) if w.script_path else "<i>not saved to a file</i>"),
        ("Status", "Modified (unsaved changes)" if w.editor.document().isModified() else "Saved"),
    ]
    for key in ("author", "version"):
        if meta.get(key):
            script_rows.append((key.capitalize(), escape(meta[key])))
    script_rows += [
        ("Description", escape(meta.get("description", "")) or "—"),
        ("Size", f"{len(lines)} lines, {len(code_lines)} code lines, {len(code)} characters"),
        ("Interaction", ("asks questions" if prompts else "no prompts") + (", updates the preview while running" if updates else "")
         + parameters_note(w)),
        ("Functions", _tags(functions)), ("API used", _tags(used)),
    ]
    if template is not None:
        script_rows.append(("From template", escape(template.name) + (" (built-in)" if template.builtin else " (yours)")))
    run_rows: list[tuple[str, str]] = []
    info = w.last_run_info
    if w.running:
        run_rows.append(("Result", colored_html("running…", "warning")))
    elif info:
        outcome = info.get("outcome", "")
        run_rows += [("Started", info.get("started", "")), ("Duration", f"{info.get('seconds', 0):.2f} s"),
                     ("Result", colored_html(escape(outcome), "success" if info.get("ok") else "error")),
                     ("Transforms", f"{info.get('before', '?')} → {info.get('after', '?')}"), ("Output", f"{info.get('lines', 0)} lines")]
    else:
        run_rows.append(("Result", "not run yet"))
    flame = w.document.flame
    flame_rows = [("Flame", escape(flame.name) if flame else "<i>none loaded</i>")]
    if flame is not None:
        flame_rows += [("Transforms", f"{len(flame.xforms)}" + (" + final" if flame.final else "")),
                       ("Size", f"{flame.camera.width} × {flame.camera.height}"),
                       ("Source", escape(w.document.source_path.name) if w.document.source_path else "not from a file")]
    return [("Script", script_rows), ("Last run", run_rows), ("Fractal in the main window", flame_rows)]


__all__ = ["info_facts", "parameters_note"]
