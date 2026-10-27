"""Completion and context help for the Script Editor (Qt-free).

`complete(code, pos)` lists what can be typed at `pos`: members of the object before the dot (resolved
through `docs.TYPES`, following method return types), the API globals and Python keywords, keyword
arguments of the call the cursor is in, or — inside a string argument such as `set_variation('…')` or a
subscript like `variations['…']` — the valid option names. Local variables are inferred from simple
assignments (`t = add_transform()`), `for` loops over typed sequences and `for_each_transform` callbacks.

`context(code, pos)` describes the same situation for the dynamic documentation panel.
"""

from __future__ import annotations

import keyword
import re
from dataclasses import dataclass, field

from . import docs as D

IDENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
KEYWORDS = tuple(keyword.kwlist) + ("True", "False", "None")
BUILTINS = ("abs", "all", "any", "bool", "dict", "enumerate", "float", "int", "len", "list", "max", "min", "range", "reversed", "round",
            "sorted", "str", "sum", "tuple", "zip", "isinstance", "map", "filter", "set", "type", "repr", "divmod", "pow")
LIST_MEMBERS = {"append": "method", "extend": "method", "insert": "method", "pop": "method", "remove": "method", "index": "method",
                "count": "method", "sort": "method", "reverse": "method", "copy": "method", "clear": "method"}
DICT_MEMBERS = {"keys": "method", "values": "method", "items": "method", "get": "method", "pop": "method", "setdefault": "method",
                "update": "method", "clear": "method", "copy": "method"}
STR_MEMBERS = {"lower": "method", "upper": "method", "strip": "method", "split": "method", "replace": "method", "startswith": "method",
               "endswith": "method", "join": "method", "format": "method", "find": "method", "title": "method"}


@dataclass
class Item:
    """One completion candidate."""
    name: str
    kind: str                 # function | method | property | object | constant | keyword | variable | option | argument | module | class
    type: str = ""
    desc: str = ""
    sig: str = ""
    detail: str = ""
    entry: D.Entry | None = None
    insert: str = ""          # text to insert instead of `name` (keyword arguments get `=`)

    @property
    def text(self) -> str:
        return self.insert or self.name


@dataclass
class Completion:
    """The result of `complete()`."""
    items: list[Item]
    prefix: str
    start: int               # offset of the prefix in the code
    in_string: bool = False
    type: str = ""


@dataclass
class Part:
    name: str = ""
    call: bool = False
    index: bool = False


@dataclass
class ScanState:
    in_string: str | None = None   # the quote that opened it ('...', "...", ''' / """)
    in_comment: bool = False
    string_start: int = -1


@dataclass
class Local:
    """A name defined by the script itself."""
    type: str = ""
    kind: str = "variable"
    desc: str = ""
    sig: str = ""


@dataclass
class Context:
    """What the cursor is on, for the dynamic help panel."""
    kind: str                                  # call | members | symbol | subscript | prefix | comment | string | none
    entry: D.Entry | None = None
    name: str = ""                             # the symbol's name (`rotate`, `add_transform`) or owner type for members
    owner: str = ""                            # type that owns the member / call
    arg_index: int = 0
    param: D.Param | None = None
    options: list[D.Option] = field(default_factory=list)
    members: list[Item] = field(default_factory=list)
    prefix: str = ""
    typed: str = ""                            # text typed so far inside a string / subscript
    items: list[Item] = field(default_factory=list)
    locals: dict[str, Local] = field(default_factory=dict)
    keywords: list[D.Param] = field(default_factory=list)


# =====================================================================================================
# scanning
# =====================================================================================================
def scan_state(code: str, pos: int) -> ScanState:
    """Whether `pos` is inside a string or a comment (handles triple quotes and escapes)."""
    i, n = 0, min(pos, len(code))
    state = ScanState()
    while i < n:
        ch = code[i]
        if state.in_comment:
            if ch == "\n":
                state.in_comment = False
            i += 1
            continue
        if state.in_string:
            q = state.in_string
            if ch == "\\":
                i += 2
                continue
            if code.startswith(q, i):
                state.in_string = None
                i += len(q)
                continue
            if ch == "\n" and len(q) == 1:
                state.in_string = None   # an unterminated single-line string ends with the line
            i += 1
            continue
        if ch == "#":
            state.in_comment = True
        elif ch in "\"'":
            q = code[i:i + 3] if code.startswith(ch * 3, i) else ch
            state.in_string = q
            state.string_start = i + len(q)
            i += len(q)
            continue
        i += 1
    return state


def _skip_back_ws(code: str, i: int) -> int:
    while i >= 0 and code[i] in " \t":
        i -= 1
    return i


def _skip_back_balanced(code: str, i: int, close: str, open_: str) -> int:
    """From `code[i] == close`, return the index before the matching `open_` (strings skipped roughly)."""
    depth = 0
    while i >= 0:
        ch = code[i]
        if ch == close:
            depth += 1
        elif ch == open_:
            depth -= 1
            if depth == 0:
                return i - 1
        i -= 1
    return -1


def chain_before(code: str, pos: int) -> tuple[list[Part], str, int]:
    """The attribute chain ending at `pos`: `flame.xforms[0].na` → ([flame, xforms, [], ], 'na', start)."""
    i = pos - 1
    while i >= 0 and (code[i].isalnum() or code[i] == "_"):
        i -= 1
    prefix = code[i + 1:pos]
    start = i + 1
    parts: list[Part] = []
    i = _skip_back_ws(code, i)
    if i < 0 or code[i] != ".":
        return parts, prefix, start
    i -= 1
    while i >= 0:
        i = _skip_back_ws(code, i)
        if i < 0:
            break
        call = False
        if code[i] == "]":
            i = _skip_back_balanced(code, i, "]", "[")
            parts.insert(0, Part(index=True))
            continue
        if code[i] == ")":
            i = _skip_back_balanced(code, i, ")", "(")
            call = True
            i = _skip_back_ws(code, i)
        k = i
        while k >= 0 and (code[k].isalnum() or code[k] == "_"):
            k -= 1
        name = code[k + 1:i + 1]
        if not name:
            if call:
                parts.insert(0, Part(call=True))   # a parenthesised expression: type unknown
            break
        parts.insert(0, Part(name, call))
        i = _skip_back_ws(code, k)
        if i >= 0 and code[i] == ".":
            i -= 1
            continue
        break
    return parts, prefix, start


def expr_parts(expr: str) -> list[Part]:
    """A whole expression (`gradient.stops.copy()`) as chain parts."""
    expr = expr.strip().rstrip(";")
    if expr.endswith(")") or expr.endswith("]"):
        parts, _prefix, _start = chain_before(expr + ".", len(expr) + 1)
        return parts
    parts, prefix, _start = chain_before(expr, len(expr))
    if prefix:
        parts.append(Part(prefix))
    return parts


def enclosing(code: str, pos: int) -> tuple[str, int, int] | None:
    """The innermost unclosed bracket before `pos`: (bracket, its index, argument index by commas)."""
    depth = 0
    commas = 0
    i = pos - 1
    st = scan_state(code, pos)
    if st.in_string:
        i = st.string_start - len(st.in_string) - 1   # skip the string we are in
    while i >= 0:
        ch = code[i]
        if ch in "\"'":
            j = i - 1   # skip a string backwards (single-line only)
            while j >= 0 and code[j] != ch and code[j] != "\n":
                j -= 1
            i = j - 1
            continue
        if ch in ")]}":
            depth += 1
        elif ch in "([{":
            if depth == 0:
                return ch, i, commas
            depth -= 1
        elif ch == "," and depth == 0:
            commas += 1
        elif ch == "\n" and depth == 0 and _line_ends_statement(code, i):
            return None
        i -= 1
    return None


def _line_ends_statement(code: str, newline_index: int) -> bool:
    """A newline ends the statement unless the line continues with a backslash or inside brackets (handled by depth)."""
    return not code[:newline_index].rstrip().endswith("\\")


# =====================================================================================================
# types and locals
# =====================================================================================================
def base_type(name: str) -> str:
    if not name:
        return ""
    return name.split("|")[0].strip()


def type_doc(name: str) -> D.TypeDoc | None:
    t = base_type(name)
    if t in D.TYPES:
        return D.TYPES[t]
    if t.startswith("list["):
        return D.TypeDoc("Python list", {}, element=t[5:-1], builtin=True)
    return None


def _element_type(type_name: str) -> str:
    t = base_type(type_name)
    doc = type_doc(t)
    if doc is not None and doc.element:
        return doc.element
    if t.startswith("list["):
        return t[5:-1]
    if t == "VariationMap":
        return "float"
    return ""


def resolve_chain(parts: list[Part], locals_: dict[str, Local]) -> str:
    """The type name a chain evaluates to ('' when unknown)."""
    if not parts:
        return ""
    first = parts[0]
    if not first.name:
        return ""
    if first.name in D.GLOBALS:
        entry = D.GLOBALS[first.name]
        type_name = entry.returns if first.call else entry.type
    elif first.name in locals_:
        type_name = locals_[first.name].type
    elif first.name in ("enumerate", "list", "sorted", "reversed"):
        type_name = "list"
    else:
        return ""
    for part in parts[1:]:
        if part.index:
            type_name = _element_type(type_name)
            continue
        doc = type_doc(type_name)
        if doc is None or not part.name:
            return ""
        member = doc.members.get(part.name)
        if member is None:
            if doc.dynamic:
                type_name = "float"
                continue
            return ""
        type_name = member.returns if part.call else member.type
    return base_type(type_name)


def resolve_entry(parts: list[Part], locals_: dict[str, Local]) -> tuple[D.Entry | None, str]:
    """(documentation entry, owner type) for the last part of a chain."""
    if not parts:
        return None, ""
    if len(parts) == 1:
        name = parts[0].name
        if name in D.GLOBALS:
            return D.GLOBALS[name], ""
        if name in locals_:
            loc = locals_[name]
            kind = "function" if loc.kind == "function" else "property"
            return D.Entry(kind, type=loc.type, desc=loc.desc, sig=loc.sig), "local"
        return None, ""
    owner = resolve_chain(parts[:-1], locals_)
    name = parts[-1].name
    doc = type_doc(owner)
    if doc is None:
        # receiver unknown: any documented type with a member of this name is a fair guess
        for type_name, candidate in D.TYPES.items():
            if name in candidate.members and not candidate.builtin:
                return candidate.members[name], type_name + "?"
        return None, ""
    if name in doc.members:
        return doc.members[name], owner
    if doc.dynamic:
        for option in D.options(doc.dynamic):
            if option.name == name:
                return D.Entry("property", "float", desc=option.desc or "variation weight"), owner
    return None, owner


def collect_locals(code: str) -> dict[str, Local]:
    """Names the script defines, with inferred types where the right-hand side is recognisable."""
    locals_: dict[str, Local] = {}
    lines = code.split("\n")
    for number, raw in enumerate(lines, 1):
        line = raw.split("#", 1)[0].rstrip()
        stripped = line.strip()
        if not stripped:
            continue
        m = re.match(r"(?:async\s+)?def\s+([A-Za-z_]\w*)\s*\(([^)]*)\)", stripped)
        if m:
            locals_[m.group(1)] = Local("", "function", f"Function defined on line {number}", f"{m.group(1)}({m.group(2).strip()})")
            continue
        m = re.match(r"for\s+([A-Za-z_]\w*)\s*(?:,\s*([A-Za-z_]\w*))?\s+in\s+(.+?):\s*$", stripped)
        if m:
            seq = m.group(3).strip()
            enum = re.match(r"enumerate\((.+)\)$", seq)
            if enum and m.group(2):
                locals_[m.group(1)] = Local("int", "variable", f"Loop index (line {number})")
                locals_[m.group(2)] = Local(_element_type(resolve_chain(expr_parts(enum.group(1)), locals_)), "variable", f"Loop variable (line {number})")
            else:
                locals_[m.group(1)] = Local(_element_type(resolve_chain(expr_parts(seq), locals_)), "variable", f"Loop variable (line {number})")
            continue
        m = re.match(r"([A-Za-z_]\w*)\s*(?::\s*[^=]+)?=\s*(?!=)(.+)$", stripped)
        if m and not stripped.startswith(("if ", "while ", "elif ")):
            name, rhs = m.group(1), m.group(2).strip()
            locals_[name] = Local(_rhs_type(rhs, locals_), "variable", f"Variable assigned on line {number}")
    for m in re.finditer(r"for_each_transform\s*\(\s*lambda\s+([A-Za-z_]\w*)\s*(?:,\s*([A-Za-z_]\w*))?", code):
        locals_[m.group(1)] = Local("Transform", "variable", "Callback argument: the transform")
        if m.group(2):
            locals_[m.group(2)] = Local("int", "variable", "Callback argument: the index")
    for m in re.finditer(r"def\s+\w+\s*\(\s*([A-Za-z_]\w*)\s*(?:,\s*([A-Za-z_]\w*))?[^)]*\)\s*:", code):
        # a function later passed to for_each_transform: its first parameter is a transform
        if re.search(rf"for_each_transform\s*\(\s*{re.escape(_def_name(code, m.start()))}\s*\)", code):
            locals_[m.group(1)] = Local("Transform", "variable", "Function argument: the transform")
            if m.group(2):
                locals_[m.group(2)] = Local("int", "variable", "Function argument: the index")
    return locals_


def _def_name(code: str, start: int) -> str:
    m = re.match(r"def\s+(\w+)", code[start:])
    return m.group(1) if m else ""


def _rhs_type(rhs: str, locals_: dict[str, Local]) -> str:
    if re.match(r"^(['\"]|f['\"])", rhs):
        return "str"
    if re.match(r"^-?\d", rhs):
        return "float"
    if rhs.startswith("["):
        return "list"
    if rhs.startswith("{"):
        return "dict"
    if rhs.startswith("("):
        return "tuple"
    if rhs in ("True", "False"):
        return "bool"
    return resolve_chain(expr_parts(rhs), locals_)


# =====================================================================================================
# items
# =====================================================================================================
def _entry_item(name: str, entry: D.Entry) -> Item:
    return Item(name, entry.kind, entry.type or entry.returns, entry.desc, entry.signature(name), "", entry)


def members_of(type_name: str) -> list[Item]:
    doc = type_doc(type_name)
    if doc is None:
        return []
    items = [_entry_item(name, entry) for name, entry in doc.members.items()]
    if doc.dynamic:
        items += [Item(o.name, "option", "float", o.desc, detail=o.detail) for o in D.options(doc.dynamic)]
    t = base_type(type_name)
    extra = LIST_MEMBERS if t.startswith("list") else DICT_MEMBERS if t in ("dict", "VariationMap") else STR_MEMBERS if t == "str" else {}
    have = {i.name for i in items}
    items += [Item(n, k, "", f"{t}.{n}") for n, k in extra.items() if n not in have]
    return items


def global_items(locals_: dict[str, Local]) -> list[Item]:
    items = [_entry_item(name, entry) for name, entry in D.GLOBALS.items()]
    items += [Item(name, loc.kind, loc.type, loc.desc, loc.sig) for name, loc in locals_.items() if name not in D.GLOBALS]
    items += [Item(k, "keyword", "", "Python keyword") for k in KEYWORDS]
    items += [Item(b, "function", "", f"Python built-in {b}()") for b in BUILTINS]
    return items


def rank(items: list[Item], prefix: str) -> list[Item]:
    """Prefix matches first (exact name first, then shorter), then substring matches; compatibility aliases and keywords last."""
    p = prefix.lower()
    if not p:
        return sorted(items, key=lambda i: ((i.entry.compat if i.entry else False), i.kind == "keyword", i.name.lower()))
    matched = [i for i in items if p in i.name.lower()]

    def key(i: Item):
        lower = i.name.lower()
        return (i.name != prefix, not lower.startswith(p), (i.entry.compat if i.entry else False), i.kind == "keyword", len(i.name), lower)

    return sorted(matched, key=key)


def _call_info(code: str, pos: int, locals_: dict[str, Local]) -> tuple[D.Entry | None, str, int, str, list[Part]] | None:
    """The call the cursor is inside: (entry, owner, arg index, callee name, callee chain)."""
    enc = enclosing(code, pos)
    if enc is None or enc[0] != "(":
        return None
    _bracket, open_index, arg_index = enc
    j = _skip_back_ws(code, open_index - 1)
    if j < 0 or not (code[j].isalnum() or code[j] == "_"):
        return None
    parts, prefix, _start = chain_before(code, j + 1)
    if not prefix:
        return None
    chain = parts + [Part(prefix, call=True)]
    entry, owner = resolve_entry(chain, locals_)
    if entry is not None and entry.kind not in ("function", "method", "class"):
        entry = None
    return entry, owner, arg_index, prefix, chain


def _keyword_index(code: str, open_index: int, pos: int) -> str | None:
    """The keyword argument being typed (`weight=`) between the call's `(` and `pos`, if the current arg has one."""
    segment = code[open_index + 1:pos]
    depth = 0
    last = 0
    for i, ch in enumerate(segment):
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif ch == "," and depth == 0:
            last = i + 1
    current = segment[last:]
    m = re.match(r"\s*([A-Za-z_]\w*)\s*=", current)
    return m.group(1) if m else None


def _current_param(entry: D.Entry, code: str, open_index: int, pos: int, arg_index: int) -> D.Param | None:
    if not entry.params:
        return None
    name = _keyword_index(code, open_index, pos)
    if name:
        for p in entry.params:
            if p.name == name:
                return p
        return None
    return entry.params[min(arg_index, len(entry.params) - 1)]


def _subscript_info(code: str, pos: int, locals_: dict[str, Local]) -> str | None:
    """Option source for a string inside `something['…']`: VARIATIONS for a VariationMap, PARAMS for `.params[`."""
    enc = enclosing(code, pos)
    if enc is None or enc[0] != "[":
        return None
    j = _skip_back_ws(code, enc[1] - 1)
    if j < 0:
        return None
    parts, prefix, _start = chain_before(code, j + 1)
    chain = parts + ([Part(prefix)] if prefix else [])
    if not chain:
        return None
    type_name = resolve_chain(chain, locals_)
    if type_name == "VariationMap":
        return D.VARIATIONS
    if chain[-1].name == "params":
        return D.PARAMS
    return None


# =====================================================================================================
# public API
# =====================================================================================================
def complete(code: str, pos: int, explicit: bool = False) -> Completion:
    """Completion candidates at `pos` (`explicit` = the user asked with Tab / Ctrl+Space, so list everything on an empty prefix)."""
    st = scan_state(code, pos)
    locals_ = collect_locals(code)
    if st.in_comment:
        return Completion([], "", pos)
    if st.in_string:
        typed = code[st.string_start:pos]
        if "\n" in typed:
            return Completion([], "", pos, True)
        source = _subscript_info(code, pos, locals_)
        if source is None:
            info = _call_info(code, pos, locals_)
            if info is not None and info[0] is not None:
                enc = enclosing(code, pos)
                param = _current_param(info[0], code, enc[1], pos, info[2]) if enc else None
                if param is not None and param.options:
                    source = param.options
        if source is None or source == D.FLAME_FILES:
            return Completion([], typed, st.string_start, True)
        items = [Item(o.name, "option", "str", o.desc, detail=o.detail) for o in D.options(source)]
        return Completion(rank(items, typed), typed, st.string_start, True)
    parts, prefix, start = chain_before(code, pos)
    if parts:
        type_name = resolve_chain(parts, locals_)
        return Completion(rank(members_of(type_name), prefix), prefix, start, type=type_name)
    items: list[Item] = []
    info = _call_info(code, pos, locals_)
    if info is not None and info[0] is not None and info[0].params:
        enc = enclosing(code, pos)
        if enc and _keyword_index(code, enc[1], pos) is None:
            items += [Item(p.name, "argument", p.type, p.desc or f"argument of {info[3]}", insert=p.name + "=") for p in info[0].params
                      if p.optional and p.name not in ("values",)]
    if not prefix and not explicit and not items:
        return Completion([], "", pos)
    items += global_items(locals_)
    return Completion(rank(items, prefix), prefix, start)


def context(code: str, pos: int) -> Context:
    """What the cursor is on (for the Context tab)."""
    locals_ = collect_locals(code)
    st = scan_state(code, pos)
    if st.in_comment:
        return Context("comment", locals=locals_)
    # the symbol under / just before the cursor
    end = pos
    while end < len(code) and (code[end].isalnum() or code[end] == "_"):
        end += 1
    parts, prefix, _start = chain_before(code, end)
    owner_type = resolve_chain(parts, locals_) if parts else ""
    symbol_chain = parts + ([Part(prefix, call=code[end:end + 1] == "(")] if prefix else [])
    entry, owner = resolve_entry(symbol_chain, locals_) if symbol_chain and not st.in_string else (None, "")
    if st.in_string:
        typed = code[st.string_start:pos]
        source = _subscript_info(code, pos, locals_)
        if source is not None:
            return Context("subscript", options=[o for o in D.options(source) if typed.lower() in o.name.lower()], typed=typed,
                           name="variations" if source == D.VARIATIONS else "params", locals=locals_)
    info = _call_info(code, pos, locals_)
    if info is not None and info[0] is not None:
        call_entry, call_owner, arg_index, callee, _chain = info
        enc = enclosing(code, pos)
        param = _current_param(call_entry, code, enc[1], pos, arg_index) if enc else None
        opts: list[D.Option] = []
        typed = code[st.string_start:pos] if st.in_string else ""
        if param is not None and param.options:
            opts = [o for o in D.options(param.options) if typed.lower() in o.name.lower()]
        keywords = [p for p in call_entry.params if p.optional]
        return Context("call", call_entry, callee, call_owner, arg_index, param, opts, typed=typed, prefix=prefix, keywords=keywords,
                       members=members_of(owner_type) if owner_type and prefix else [], locals=locals_)
    if st.in_string:
        return Context("string", locals=locals_)
    if parts and type_doc(owner_type) is not None:
        return Context("members", entry, owner_type, owner_type, members=members_of(owner_type), prefix=prefix, locals=locals_)
    if entry is not None:
        return Context("symbol", entry, prefix, owner, members=members_of(base_type(entry.type)) if entry.type else [], locals=locals_)
    if prefix:
        return Context("prefix", prefix=prefix, items=rank(global_items(locals_), prefix)[:40], locals=locals_)
    return Context("none", locals=locals_)


__all__ = ["complete", "context", "Completion", "Context", "Item", "Local", "collect_locals", "resolve_chain", "resolve_entry",
           "chain_before", "expr_parts", "scan_state", "members_of", "global_items", "KEYWORDS"]
