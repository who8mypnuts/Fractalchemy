"""Writers for the report: Markdown and HTML for people, `key<TAB>value` text for pipelines.

Text format: one record per line, keys dotted and lower-case with no spaces (`render.samples`,
`transforms.2.weight`, `timing.tiles.1.samples`), values in machine form, `#` for comments. So
`grep '^timing\\.' render.txt | cut -f2` or `awk -F'\\t' '$1=="render.samples"'` just work.
"""

from __future__ import annotations

import html

from .model import Report, Table, machine_text


def to_text(report: Report) -> str:
    """Pipeline-friendly `key<TAB>value` lines (see the module docstring)."""
    lines = [f"# {report.title}", f"# generated\t{machine_text(report.generated)}",
             "# format: one record per line, key<TAB>value; keys are dotted, values machine-readable"]
    for sec in report.sections:
        lines.append(f"# {sec.title}")
        for item in sec.items:
            lines.append(f"{sec.key}.{item.key}\t{_escape_text(machine_text(item.value))}")
        for table in sec.tables:
            lines.extend(_table_records(sec.key, table))
        for n, note in enumerate(sec.notes, start=1):
            lines.append(f"{sec.key}.{n}\t{_escape_text(note)}")
    return "\n".join(lines) + "\n"


def _table_records(section_key: str, table: Table) -> list[str]:
    prefix = f"{section_key}.{table.key}" if table.key else section_key
    lines = [f"{prefix}.count\t{len(table.rows)}"]
    for n, row in enumerate(table.rows, start=1):
        row_id = _key_safe(machine_text(table.cell(row, table.id_key).value)) if table.id_key else str(n)
        for key, _label in table.columns:
            if key != table.id_key:
                lines.append(f"{prefix}.{row_id}.{key}\t{_escape_text(machine_text(table.cell(row, key).value))}")
    return lines


def _key_safe(text: str) -> str:
    """A row id usable inside a dotted key: no whitespace, dots or tabs."""
    return "".join("_" if ch.isspace() or ch in ".\t" else ch for ch in text) or "_"


def _escape_text(value: str) -> str:
    return value.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n")


def to_markdown(report: Report) -> str:
    """A readable Markdown document."""
    out = [f"# {report.title}", "", f"_Generated {report.generated.strftime('%Y-%m-%d %H:%M:%S %Z')}_", ""]
    for sec in report.sections:
        out += [f"## {sec.title}", ""]
        if sec.items:
            out += ["| Field | Value |", "|---|---|"]
            out += [f"| {_md(item.label)} | {_md(item.text)} |" for item in sec.items]
            out.append("")
        for table in sec.tables:
            out += [f"### {table.title}", "",
                    "| " + " | ".join(_md(label) for _key, label in table.columns) + " |",
                    "|" + "---|" * len(table.columns)]
            out += ["| " + " | ".join(_md(table.cell(row, key).display) for key, _label in table.columns) + " |"
                    for row in table.rows]
            out.append("")
        if sec.notes:
            out += [f"- {_md(note)}" for note in sec.notes] + [""]
    return "\n".join(out)


def _md(text: str) -> str:
    return text.replace("|", "\\|").replace("\n", " ")


_HTML_STYLE = """
body { font: 14px/1.45 system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif; color: #222; background: #fafafa;
       max-width: 1100px; margin: 2em auto; padding: 0 1em; }
h1 { font-size: 1.6em; border-bottom: 2px solid #ddd; padding-bottom: .3em; }
h2 { font-size: 1.2em; margin-top: 2em; color: #333; }
h3 { font-size: 1em; color: #555; }
table { border-collapse: collapse; margin: .5em 0 1em; background: #fff; font-size: 13px; }
th, td { border: 1px solid #ddd; padding: .3em .6em; text-align: left; vertical-align: top; }
th { background: #f0f0f0; font-weight: 600; }
tr:nth-child(even) td { background: #f7f7f7; }
.fields td:first-child { color: #555; white-space: nowrap; }
.generated { color: #777; font-style: italic; }
"""


def to_html(report: Report) -> str:
    """A standalone HTML page."""
    e = html.escape
    out = ["<!DOCTYPE html>", "<html lang=\"en\"><head><meta charset=\"utf-8\">", f"<title>{e(report.title)}</title>",
           f"<style>{_HTML_STYLE}</style></head><body>", f"<h1>{e(report.title)}</h1>",
           f"<p class=\"generated\">Generated {e(report.generated.strftime('%Y-%m-%d %H:%M:%S %Z'))}</p>"]
    for sec in report.sections:
        out.append(f"<h2 id=\"{e(sec.key)}\">{e(sec.title)}</h2>")
        if sec.items:
            rows = "".join(f"<tr><td>{e(item.label)}</td><td>{e(item.text)}</td></tr>" for item in sec.items)
            out.append(f"<table class=\"fields\"><tbody>{rows}</tbody></table>")
        for table in sec.tables:
            head = "".join(f"<th>{e(label)}</th>" for _key, label in table.columns)
            body = "".join("<tr>" + "".join(f"<td>{e(table.cell(row, key).display)}</td>" for key, _label in table.columns) + "</tr>"
                           for row in table.rows)
            out.append(f"<h3>{e(table.title)}</h3><table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>")
        if sec.notes:
            out.append("<ul>" + "".join(f"<li>{e(note)}</li>" for note in sec.notes) + "</ul>")
    out.append("</body></html>")
    return "\n".join(out) + "\n"


WRITERS = {"md": to_markdown, "txt": to_text, "html": to_html}


def render_report(report: Report, fmt: str) -> str:
    """The report as text in format `fmt` ("md" / "txt" / "html"; unknown → Markdown)."""
    return WRITERS.get(fmt, to_markdown)(report)


__all__ = ["to_text", "to_markdown", "to_html", "render_report", "WRITERS"]
