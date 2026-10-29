"""The Script Editor's drawer (the right-hand pane): four tabs.

* **Context** — dynamic documentation for what the cursor is on: the members of the object being typed, or
  the signature of the call the cursor is inside with the current argument highlighted and, when that
  argument takes one of a known set of values (variation names, parameter names, curve channels), the list
  of values. Click a name to insert it.
* **Reference** — the scripting guide, the full API reference (searchable) and the catalogue of variations.
* **Info** — facts about the script: name, file, metadata, size, the API it uses, the last run.
* **Templates** — built-in templates by category plus *My templates*; load, insert, run, save, rename, delete.

The tabs are views: the window feeds them (`show_context`, `show_info`, `set_templates`) and acts on their
signals.
"""

from __future__ import annotations

from html import escape
from pathlib import Path

from PySide6.QtCore import Qt, QTimer, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QHBoxLayout, QLineEdit, QPushButton, QTabWidget, QTextBrowser, QToolButton, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget,
)

from ..fractal import variations as V
from ..scripting import completion as C
from ..scripting import docs as D
from ..scripting.templates import Template
from .formula_browser import KIND_LABELS, origin_group

TEMPLATE_ROLE = Qt.ItemDataRole.UserRole
STYLE = """
<style>
body { font-size: 10pt; }
h2 { font-size: 12pt; color: #0d47a1; margin: 6px 0 4px 0; }
h3 { font-size: 10.5pt; margin: 10px 0 3px 0; }
.sig { font-family: monospace; background: #f1f3f6; padding: 4px 6px; border: 1px solid #d8dce2; }
.cur { background: #ffe59a; font-weight: bold; }
table { border-collapse: collapse; }
td, th { padding: 2px 6px; vertical-align: top; border-bottom: 1px solid #e4e6ea; }
th { text-align: left; color: #777; font-weight: normal; font-size: 8.5pt; }
td.n { font-family: monospace; }
td.t { color: #777; font-family: monospace; font-size: 9pt; }
tr.hl td { background: #eef3ff; }
tr.dim td { color: #aaa; }
.hint { color: #777; font-style: italic; }
.badge { color: #555; background: #eee; font-size: 8pt; padding: 0 4px; }
pre { background: #f4f4f4; padding: 4px 6px; border: 1px solid #e0e0e0; }
code { font-family: monospace; color: #7a4a00; }
a { color: #1565c0; text-decoration: none; }
</style>
"""


def _html(body: str) -> str:
    return STYLE + "<body>" + body + "</body>"


def entry_html(name: str, entry: D.Entry, arg_index: int | None = None, param_name: str | None = None, link: bool = False) -> str:
    """The documentation of one entry: signature (current argument highlighted), description, arguments, example.

    With `link` the signature is a clickable `insert:` link (the Reference tab)."""
    if entry.kind in ("function", "method") and entry.params and not entry.sig:
        labels = []
        for i, p in enumerate(entry.params):
            current = (param_name is not None and p.name == param_name) or (param_name is None and arg_index is not None and i == min(arg_index, len(entry.params) - 1))
            labels.append(f"<span class='cur'>{escape(p.label)}</span>" if current else escape(p.label))
        sig = f"{escape(name)}({', '.join(labels)})"
    else:
        sig = escape(entry.signature(name))
    if entry.returns and entry.returns != "":
        sig += f" <span style='color: #777'>→ {escape(entry.returns)}</span>"
    badges = ""
    if entry.readonly:
        badges += " <span class='badge'>read-only</span>"
    if entry.compat:
        badges += " <span class='badge'>Apophysis alias</span>"
    if link:
        sig = f"<a href='insert:{escape(name)}:{entry.kind}'>{sig}</a>"
    html = f"<div class='sig'>{sig}{badges}</div>"
    if entry.desc:
        html += f"<p>{escape(entry.desc)}</p>"
    if entry.params:
        html += "<table width='100%'><tr><th width='24%'>argument</th><th width='18%'>type</th><th width='58%'>description</th></tr>"
        for i, p in enumerate(entry.params):
            current = (param_name is not None and p.name == param_name) or (param_name is None and arg_index is not None and i == min(arg_index, len(entry.params) - 1))
            html += (f"<tr class='{'hl' if current else ''}'><td class='n'>{escape(p.label)}</td><td class='t'>{escape(p.type)}</td>"
                     f"<td>{escape(p.desc)}{' <span class=hint>(choose from the list below)</span>' if p.options and current else ''}</td></tr>")
        html += "</table>"
    if entry.example:
        html += f"<pre>{escape(entry.example)}</pre>"
    return html


def members_table(items: list[C.Item], prefix: str = "", owner: str = "") -> str:
    """A table of members / names; `prefix` highlights the matching rows; names link to `insert:`."""
    p = prefix.lower()
    rows = []
    for item in items:
        matches = not p or item.name.lower().startswith(p)
        cls = "hl" if p and matches else ("dim" if p else "")
        label = item.name + "()" if item.kind in ("function", "method") else item.name
        type_text = item.type or ""
        rows.append(f"<tr class='{cls}'><td class='n'><a href='insert:{escape(item.name)}:{item.kind}' title='Insert'>{escape(label)}</a></td>"
                    f"<td class='t'>{escape(type_text)}</td><td>{escape(item.desc)}</td></tr>")
    head = f"{escape(owner)} member" if owner else "name"
    return (f"<table width='100%'><tr><th width='36%'>{head}</th><th width='16%'>type</th><th width='48%'>description</th></tr>"
            f"{''.join(rows)}</table>")


def options_list(options: list[D.Option], source_name: str) -> str:
    rows = "".join(f"<tr><td class='n'><a href='option:{escape(o.name)}'>{escape(o.name)}</a></td><td>{escape(o.desc)}"
                   f"{(' <span class=t>[' + escape(o.detail) + ']</span>') if o.detail else ''}</td></tr>" for o in options)
    return (f"<p class='hint'>{len(options)} {source_name}{'s' if len(options) != 1 else ''} — click one to insert it:</p>"
            f"<table width='100%'>{rows}</table>")


def guide_html(markdown: str) -> str:
    """A small markdown subset (headings to ###, paragraphs, bullets, fenced code, `code`, **bold**, *italic*) as HTML."""
    import re
    out, para, in_code, in_list = [], [], False, False

    def inline(text: str) -> str:
        text = escape(text)
        text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
        text = re.sub(r"\*\*([^*]+)\*\*", r"<b>\1</b>", text)
        return re.sub(r"(?<![*\w])\*([^*]+)\*", r"<i>\1</i>", text)

    def flush() -> None:
        if para:
            out.append("<p>" + " ".join(para) + "</p>")
            para.clear()

    for line in markdown.split("\n"):
        if line.startswith("```"):
            flush()
            if in_list:
                out.append("</ul>")
                in_list = False
            in_code = not in_code
            out.append("<pre>" if in_code else "</pre>")
            continue
        if in_code:
            out.append(escape(line))
            continue
        if line.startswith("* "):
            flush()
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + inline(line[2:]) + "</li>")
            continue
        if in_list and not line.startswith("  "):
            out.append("</ul>")
            in_list = False
        elif in_list:
            out[-1] = out[-1][:-5] + " " + inline(line.strip()) + "</li>"
            continue
        if line.startswith("# "):
            flush()
            out.append(f"<h1>{inline(line[2:])}</h1>")
        elif line.startswith("## "):
            flush()
            out.append(f"<h2>{inline(line[3:])}</h2>")
        elif line.startswith("### "):
            flush()
            out.append(f"<h3>{inline(line[4:])}</h3>")
        elif line.strip():
            para.append(inline(line))
        else:
            flush()
    flush()
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


# =====================================================================================================
# tabs
# =====================================================================================================
class _Browser(QTextBrowser):
    """A QTextBrowser that reports link clicks instead of navigating."""
    link_clicked = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setOpenLinks(False)
        self.setOpenExternalLinks(False)
        self.anchorClicked.connect(lambda url: self.link_clicked.emit(url.toString()))


class ContextTab(QWidget):
    """Dynamic documentation that follows the cursor.

    Signals:
        insert_requested(str, str): (text, kind) — insert a name at the cursor (replacing the typed prefix).
        option_requested(str): Insert an option value (inside the string being typed).
    """
    insert_requested = Signal(str, str)
    option_requested = Signal(str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.browser = _Browser(self)
        self.browser.link_clicked.connect(self._link)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        self.kind = "none"
        self.show_context(C.Context("none"))

    def _link(self, url: str) -> None:
        if url.startswith("insert:"):
            _tag, name, kind = url.split(":", 2)
            self.insert_requested.emit(name, kind)
        elif url.startswith("option:"):
            self.option_requested.emit(url[len("option:"):])

    def show_context(self, cx: C.Context) -> None:
        self.kind = cx.kind
        html = ""
        if cx.kind == "call" and cx.entry is not None:
            owner = f"{cx.owner}." if cx.owner and cx.owner not in ("local",) else ""
            html += f"<h2>{escape(owner + cx.name)}</h2>"
            html += entry_html(cx.name, cx.entry, cx.arg_index, cx.param.name if cx.param else None)
            if cx.param is not None:
                html += f"<h3>Argument {cx.arg_index + 1}: <code>{escape(cx.param.name)}</code> <span class='t'>{escape(cx.param.type)}"
                html += (" (optional)" if cx.param.optional else "") + "</span></h3>"
                if cx.param.desc:
                    html += f"<p>{escape(cx.param.desc)}</p>"
                if cx.options:
                    html += options_list(cx.options, "option")
                elif cx.param.options == D.FLAME_FILES:
                    html += "<p class='hint'>A path to a .flame, .chaos or .fa file (~ is expanded).</p>"
            if cx.keywords:
                html += "<h3>Keyword arguments</h3><p class='hint'>" + ", ".join(
                    f"<a href='insert:{escape(k.name)}=:argument'><code>{escape(k.name)}=</code></a>" for k in cx.keywords) + "</p>"
            if cx.members and cx.prefix:
                html += f"<h3>Members matching “{escape(cx.prefix)}”</h3>" + members_table(cx.members, cx.prefix)
        elif cx.kind == "subscript":
            what = "variation" if cx.name == "variations" else "parameter"
            html += f"<h2>{escape(cx.name)}[…]</h2><p>{'Variation name → weight. Assigning 0 removes the variation; new ones get their parameter defaults.' if cx.name == 'variations' else 'Parameter name → value, keyed as in flame files (julian_power).'}</p>"
            html += options_list(cx.options, what + " name")
        elif cx.kind == "members":
            doc = D.TYPES.get(cx.owner)
            html += f"<h2>{escape(cx.owner)}</h2>" + (f"<p>{escape(doc.desc)}</p>" if doc else "")
            if cx.entry is not None and cx.prefix:
                html += entry_html(cx.prefix, cx.entry)
            html += f"<p class='hint'>Members of <code>{escape(cx.owner)}</code>" + (f" matching “{escape(cx.prefix)}”" if cx.prefix else "") + " — click to insert:</p>"
            html += members_table(cx.members, cx.prefix, cx.owner)
        elif cx.kind == "symbol" and cx.entry is not None:
            badge = escape(cx.entry.kind) + (f" · {escape(cx.owner)}" if cx.owner and cx.owner != "local" else "")
            html += f"<h2>{escape(cx.name)} <span class='badge'>{badge}</span></h2>" + entry_html(cx.name, cx.entry)
            if cx.members:
                type_name = C.base_type(cx.entry.type)
                doc = D.TYPES.get(type_name)
                html += f"<h3>{escape(type_name)} members</h3>" + (f"<p>{escape(doc.desc)}</p>" if doc else "") + members_table(cx.members, "", type_name)
        elif cx.kind == "prefix":
            html += f"<h2>Matching “{escape(cx.prefix)}”</h2><p class='hint'>Press Tab to complete, or click a name to insert it.</p>"
            html += members_table(cx.items, cx.prefix)
        elif cx.kind == "comment":
            html += ("<h2>Comment</h2><p class='hint'>Lines like <code># @name My script</code>, <code># @author …</code> and "
                     "<code># @description …</code> at the top of the script are shown in the Info tab and name the script when "
                     "it is saved as a template.</p>")
        elif cx.kind == "string":
            html += "<h2>String</h2><p class='hint'>Inside a string. Variation and parameter names are offered inside <code>set_variation('…')</code>, <code>variations['…']</code> and <code>params['…']</code>.</p>"
        else:
            html += ("<h2>Context help</h2><p class='hint'>This panel follows the cursor. Type one of the objects below followed by a dot "
                     "(e.g. <code>transform.</code>) to see what it offers, or put the cursor inside a call to see its arguments.</p>")
            objects = [C.Item(n, D.GLOBALS[n].kind, D.GLOBALS[n].type, D.GLOBALS[n].desc) for n in D.CATEGORIES[0][1]]
            html += "<h3>Objects</h3>" + members_table(objects)
            common = ("add_transform", "remove_transform", "set_active_transform", "for_each_transform", "random", "print", "input_number",
                      "confirm", "update", "stop")
            html += "<h3>Often used</h3>" + members_table([C.Item(n, D.GLOBALS[n].kind, D.GLOBALS[n].returns, D.GLOBALS[n].desc,
                                                                     D.GLOBALS[n].signature(n)) for n in common])
        if cx.locals and cx.kind in ("none", "prefix"):
            items = [C.Item(n, loc.kind, loc.type, loc.desc, loc.sig) for n, loc in cx.locals.items()]
            html += "<h3>Defined in this script</h3>" + members_table(items)
        scroll = self.browser.verticalScrollBar().value() if cx.kind == self.kind else 0
        self.browser.setHtml(_html(html))
        self.browser.verticalScrollBar().setValue(scroll)


class ReferenceTab(QWidget):
    """Guide / API reference / variations, with a search box.

    Signals:
        insert_requested(str, str): (text, kind).
    """
    insert_requested = Signal(str, str)

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.guide_button = QPushButton("Scripting guide", self)
        self.api_button = QPushButton("API reference", self)
        self.variations_button = QPushButton("Variations", self)
        for b in (self.guide_button, self.api_button, self.variations_button):
            b.setCheckable(True)
            b.setAutoExclusive(True)
        self.guide_button.setChecked(True)
        self.search = QLineEdit(self, placeholderText="Search the API (e.g. rotate, xaos, gradient)…")
        self.search.setClearButtonEnabled(True)
        self.browser = _Browser(self)
        self.browser.link_clicked.connect(self._link)
        buttons = QHBoxLayout()
        for b in (self.guide_button, self.api_button, self.variations_button):
            buttons.addWidget(b)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(buttons)
        layout.addWidget(self.search)
        layout.addWidget(self.browser)
        self._timer = QTimer(self, singleShot=True, interval=200)
        self._timer.timeout.connect(self.render)
        self.search.textChanged.connect(self._on_search)
        for b in (self.guide_button, self.api_button, self.variations_button):
            b.clicked.connect(self.render)
        self.render()

    @property
    def mode(self) -> str:
        return "guide" if self.guide_button.isChecked() else "api" if self.api_button.isChecked() else "variations"

    def show_mode(self, mode: str) -> None:
        {"guide": self.guide_button, "api": self.api_button, "variations": self.variations_button}[mode].setChecked(True)
        self.render()

    def _on_search(self, text: str) -> None:
        if text and self.guide_button.isChecked():
            self.api_button.setChecked(True)
        self._timer.start()

    def _link(self, url: str) -> None:
        if url.startswith("insert:"):
            _tag, name, kind = url.split(":", 2)
            self.insert_requested.emit(name, kind)
        elif url.startswith("option:"):
            self.insert_requested.emit(f"'{url[len('option:'):]}'", "option")

    def render(self) -> None:
        query = self.search.text().strip().lower()
        if self.mode == "guide":
            self.browser.setHtml(_html(guide_html(D.GUIDE)))
        elif self.mode == "variations":
            self.browser.setHtml(_html(self._variations_html(query)))
        else:
            self.browser.setHtml(_html(self._api_html(query)))

    @staticmethod
    def _api_html(query: str) -> str:
        def matches(name: str, entry: D.Entry) -> bool:
            return not query or query in name.lower() or query in entry.desc.lower() or query in entry.signature(name).lower()

        html = ""
        for title, names in D.CATEGORIES:
            rows = [n for n in names if matches(n, D.GLOBALS[n])]
            if not rows:
                continue
            html += f"<h2>{escape(title)}</h2>"
            for n in rows:
                html += entry_html(n, D.GLOBALS[n], link=True)
        for type_name, doc in D.TYPES.items():
            if doc.builtin:
                continue
            members = [(n, e) for n, e in doc.members.items() if matches(n, e) or (query and query in type_name.lower())]
            if not members:
                continue
            html += f"<h2>{escape(type_name)} <span class='badge'>type</span></h2><p>{escape(doc.desc)}</p>"
            if doc.dynamic:
                html += "<p class='hint'>Any loaded formula name is a valid key — see the Variations list.</p>"
            for n, e in members:
                html += entry_html(n, e, link=True)
        return html or f"<p class='hint'>Nothing matches “{escape(query)}”.</p>"

    @staticmethod
    def _variations_html(query: str) -> str:
        groups: dict[str, list[str]] = {}
        for name in V.catalogue():
            var = V.REGISTRY[name]
            params = " ".join(var.params)
            if query and query not in name.lower() and query not in params.lower() and query not in origin_group(var).lower():
                continue
            groups.setdefault(origin_group(var), []).append(name)
        html = (f"<h2>Variations ({len(V.catalogue())} loaded)</h2><p class='hint'>Use <code>t.set_variation(name, weight)</code> or "
                "<code>t.variations[name] = weight</code>; parameters through <code>t.params[name]</code>. Click a name to insert it.</p>")
        for group, names in groups.items():
            html += f"<h3>{escape(group)} ({len(names)})</h3><table width='100%'><tr><th width='30%'>name</th><th width='50%'>parameters (defaults)</th><th width='20%'>kind</th></tr>"
            for name in names:
                var = V.REGISTRY[name]
                params = ", ".join(f"{k}={v:g}" for k, v in var.params.items())
                bits = [KIND_LABELS.get(var.kind, var.kind)] + (["3D"] if var.z == V.Z_FORMULA else []) + (["direct colour"] if var.dc else [])
                html += f"<tr><td class='n'><a href='option:{escape(name)}'>{escape(name)}</a></td><td class='t'>{escape(params)}</td><td>{escape(', '.join(bits))}</td></tr>"
            html += "</table>"
        return html


class InfoTab(QWidget):
    """Facts about the script and its last run.

    Signals:
        header_requested(): Insert / update the `# @name …` header.
        copy_requested(): Copy the script to the clipboard.
    """
    header_requested = Signal()
    copy_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.browser = QTextBrowser(self)
        self.header_button = QPushButton("Insert metadata header", self)
        self.copy_button = QPushButton("Copy script", self)
        self.header_button.clicked.connect(self.header_requested)
        self.copy_button.clicked.connect(self.copy_requested)
        buttons = QHBoxLayout()
        buttons.addWidget(self.header_button)
        buttons.addWidget(self.copy_button)
        buttons.addStretch(1)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.browser)
        layout.addLayout(buttons)

    def show_info(self, facts: list[tuple[str, list[tuple[str, str]]]]) -> None:
        """`facts` = [(section title, [(label, html value), …]), …]."""
        html = ""
        for title, rows in facts:
            html += f"<h2>{escape(title)}</h2><table width='100%'>"
            for label, value in rows:
                html += f"<tr><th>{escape(label)}</th><td>{value}</td></tr>"
            html += "</table>"
        self.browser.setHtml(_html(html))


class TemplatesTab(QWidget):
    """Built-in and user templates.

    Signals:
        load_requested(object): Replace the editor's script with the template.
        insert_requested(object): Insert the template's code at the cursor.
        run_requested(object): Load and run.
        save_requested(): Save the current script as a new template.
        overwrite_requested(object): Replace a user template with the current script.
        rename_requested(object): Rename a user template.
        delete_requested(object): Delete a user template.
        refresh_requested(): Re-read the template folders.
    """
    load_requested = Signal(object)
    insert_requested = Signal(object)
    run_requested = Signal(object)
    save_requested = Signal()
    overwrite_requested = Signal(object)
    rename_requested = Signal(object)
    delete_requested = Signal(object)
    refresh_requested = Signal()

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.search = QLineEdit(self, placeholderText="Filter templates…")
        self.search.setClearButtonEnabled(True)
        self.tree = QTreeWidget(self)
        self.tree.setHeaderHidden(True)
        self.tree.setColumnCount(1)
        self.tree.setAlternatingRowColors(True)
        self.description = QTextBrowser(self)
        self.description.setMaximumHeight(90)
        self.load_button = QPushButton("Load", self)
        self.insert_button = QPushButton("Insert", self)
        self.run_button = QPushButton("Load && run", self)
        self.save_button = QPushButton("Save as template…", self)
        self.overwrite_button = QPushButton("Overwrite", self)
        self.rename_button = QPushButton("Rename…", self)
        self.delete_button = QPushButton("Delete", self)
        self.folder_button = QToolButton(self)
        self.folder_button.setText("Open folder")
        self.refresh_button = QToolButton(self)
        self.refresh_button.setText("Refresh")
        self.load_button.setToolTip("Replace the script in the editor with this template")
        self.insert_button.setToolTip("Insert the template's code at the cursor (without its header)")
        self.run_button.setToolTip("Load the template and run it")
        self.save_button.setToolTip("Save the script in the editor as a new template of your own")
        self.overwrite_button.setToolTip("Replace this template of yours with the script in the editor")
        self.folder_button.setToolTip("Open the folder your templates are saved in")
        row1 = QHBoxLayout()
        for b in (self.load_button, self.insert_button, self.run_button):
            row1.addWidget(b)
        row1.addStretch(1)
        row2 = QHBoxLayout()
        for b in (self.save_button, self.overwrite_button):
            row2.addWidget(b)
        row2.addStretch(1)
        row2b = QHBoxLayout()
        for b in (self.rename_button, self.delete_button):
            row2b.addWidget(b)
        row2b.addStretch(1)
        row3 = QHBoxLayout()
        row3.addWidget(self.search, 1)
        row3.addWidget(self.refresh_button)
        row3.addWidget(self.folder_button)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addLayout(row3)
        layout.addWidget(self.tree, 1)
        layout.addWidget(self.description)
        layout.addLayout(row1)
        layout.addLayout(row2)
        layout.addLayout(row2b)
        self._templates: list[Template] = []
        self.folder: Path | None = None
        self.search.textChanged.connect(self._filter)
        self.tree.currentItemChanged.connect(lambda *_: self._selection_changed())
        self.tree.itemDoubleClicked.connect(lambda item, _c: self._emit(self.load_requested))
        self.load_button.clicked.connect(lambda: self._emit(self.load_requested))
        self.insert_button.clicked.connect(lambda: self._emit(self.insert_requested))
        self.run_button.clicked.connect(lambda: self._emit(self.run_requested))
        self.save_button.clicked.connect(self.save_requested)
        self.overwrite_button.clicked.connect(lambda: self._emit(self.overwrite_requested))
        self.rename_button.clicked.connect(lambda: self._emit(self.rename_requested))
        self.delete_button.clicked.connect(lambda: self._emit(self.delete_requested))
        self.refresh_button.clicked.connect(self.refresh_requested)
        self.folder_button.clicked.connect(self._open_folder)
        self._selection_changed()

    def set_templates(self, templates: list[Template], folder: Path | None = None) -> None:
        """(Re)fill the tree; keeps the selection when the same template is still there."""
        selected = self.current()
        self._templates = list(templates)
        self.folder = folder
        self.tree.clear()
        groups: dict[str, QTreeWidgetItem] = {}
        for template in templates:
            group = groups.get(template.category)
            if group is None:
                group = QTreeWidgetItem([template.category])
                group.setFlags(Qt.ItemFlag.ItemIsEnabled)
                font = group.font(0)
                font.setBold(True)
                group.setFont(0, font)
                groups[template.category] = group
                self.tree.addTopLevelItem(group)
            item = QTreeWidgetItem([template.name])
            item.setData(0, TEMPLATE_ROLE, template)
            item.setToolTip(0, template.description or template.name)
            group.addChild(item)
        self.tree.expandAll()
        self._filter(self.search.text())
        if selected is not None:
            self.select(selected.id)
        self._selection_changed()

    def select(self, template_id: str) -> None:
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                item = group.child(j)
                template = item.data(0, TEMPLATE_ROLE)
                if template is not None and template.id == template_id:
                    self.tree.setCurrentItem(item)
                    return

    def current(self) -> Template | None:
        item = self.tree.currentItem()
        return item.data(0, TEMPLATE_ROLE) if item is not None else None

    def visible_names(self) -> list[str]:
        names = []
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            for j in range(group.childCount()):
                if not group.child(j).isHidden():
                    names.append(group.child(j).text(0))
        return names

    def _filter(self, text: str) -> None:
        query = text.strip().lower()
        for i in range(self.tree.topLevelItemCount()):
            group = self.tree.topLevelItem(i)
            visible = 0
            for j in range(group.childCount()):
                item = group.child(j)
                template: Template = item.data(0, TEMPLATE_ROLE)
                show = not query or query in template.name.lower() or query in template.description.lower() or query in template.code.lower()
                item.setHidden(not show)
                visible += show
            group.setHidden(visible == 0)

    def _selection_changed(self) -> None:
        template = self.current()
        has = template is not None
        for b in (self.load_button, self.insert_button, self.run_button):
            b.setEnabled(has)
        own = has and not template.builtin
        for b in (self.overwrite_button, self.rename_button, self.delete_button):
            b.setEnabled(own)
        if template is None:
            self.description.setHtml(_html("<p class='hint'>Pick a template: double-click loads it into the editor.</p>"))
        else:
            where = "built-in" if template.builtin else (str(template.path) if template.path else "")
            self.description.setHtml(_html(f"<b>{escape(template.name)}</b> <span class='badge'>{escape(where)}</span>"
                                           f"<p>{escape(template.description) or '<i>no description</i>'}</p>"))

    def _emit(self, signal: Signal) -> None:
        template = self.current()
        if template is not None:
            signal.emit(template)

    def _open_folder(self) -> None:
        if self.folder is not None:
            self.folder.mkdir(parents=True, exist_ok=True)
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.folder)))


class ScriptDrawer(QTabWidget):
    """The drawer itself: the four tabs in a tab widget."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.context = ContextTab(self)
        self.reference = ReferenceTab(self)
        self.info = InfoTab(self)
        self.templates = TemplatesTab(self)
        self.addTab(self.context, "Context")
        self.addTab(self.reference, "Reference")
        self.addTab(self.info, "Info")
        self.addTab(self.templates, "Templates")
        self.setTabToolTip(0, "Documentation for what the cursor is on — updates as you type")
        self.setTabToolTip(1, "The scripting guide, the full API reference and the variations")
        self.setTabToolTip(2, "About this script: name, file, metadata, the API it uses, the last run")
        self.setTabToolTip(3, "Script templates: built-in ones and your own")
        self.setMinimumWidth(240)

    def show_tab(self, name: str) -> None:
        self.setCurrentIndex({"context": 0, "reference": 1, "info": 2, "templates": 3}[name])


__all__ = ["ScriptDrawer", "ContextTab", "ReferenceTab", "InfoTab", "TemplatesTab", "entry_html", "members_table", "guide_html"]
