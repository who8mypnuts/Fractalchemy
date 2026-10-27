"""A small C preprocessor for formula sources.

Handles what Apophysis plugin sources actually use: comments, line continuations,
object-like and function-like `#define`s, `#undef`, `#if` / `#ifdef` / `#ifndef` /
`#elif` / `#else` / `#endif` with integer constant expressions and `defined()`.
`#include` lines are dropped (formula files are self-contained; the SDK header is
implied), as are `#pragma`, `#error` and `#warning`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .lexer import Token, tokenize

_LINE_CONT = re.compile(r"\\\r?\n")
_BLOCK_COMMENT = re.compile(r"/\*.*?\*/", re.S)
_LINE_COMMENT = re.compile(r"//[^\n]*")
_DIRECTIVE = re.compile(r"^\s*#\s*(\w+)\s*(.*)$")
_IDENT = re.compile(r"[A-Za-z_]\w*")

IGNORED_DIRECTIVES = {"include", "pragma", "error", "warning", "line"}

# Macros the Apophysis SDK header (apoplugin.h) provides.
SDK_MACROS = {
    "MAX(a, b)": "((a) > (b) ? (a) : (b))",
    "MIN(a, b)": "((a) < (b) ? (a) : (b))",
    "DLLIMPORT": "",
    "DLLEXPORT": "",
    "APO_NOVARIABLES": "",
}


class PreprocessError(ValueError):
    """A directive could not be handled."""


class UnterminatedArguments(PreprocessError):
    """A function-like macro call did not close on this line."""


@dataclass
class Macro:
    name: str
    params: list[str] | None     # None for object-like macros
    body: str


def strip_comments(text: str) -> str:
    """Remove `/* */` and `//` comments, keeping newlines so line numbers survive."""
    text = _LINE_CONT.sub("", text)
    text = _BLOCK_COMMENT.sub(lambda m: "\n" * m.group(0).count("\n"), text)
    return _LINE_COMMENT.sub("", text)


def preprocess(text: str, predefined: dict[str, str] | None = None, include_dir=None) -> str:
    """Expand directives and macros in `text`; returns plain C source.

    `#include "file"` is inlined when `file` exists under `include_dir` (shared helper code such
    as a noise library); every other include is dropped — the SDK header is implied.
    """
    macros: dict[str, Macro] = {}
    for definition, body in {**SDK_MACROS, **(predefined or {})}.items():
        macro = parse_define(f"{definition} {body}")
        macros[macro.name] = macro
    out: list[str] = []
    stack: list[tuple[bool, bool, bool]] = []   # (parent active, this branch taken, any branch taken so far)
    active = True
    lines = strip_comments(_inline_includes(text, include_dir, 0)).split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        i += 1
        m = _DIRECTIVE.match(line)
        if not m:
            if not active:
                out.append("")
                continue
            joined = 0
            while True:   # a macro call may span lines: pull the following lines in until its arguments close
                try:
                    out.append(expand(line, macros))
                    break
                except UnterminatedArguments:
                    if i >= len(lines) or _DIRECTIVE.match(lines[i]) or joined > 50:
                        raise PreprocessError("unterminated macro argument list") from None
                    line += " " + lines[i]
                    out.append("")
                    i += 1
                    joined += 1
            continue
        name, rest = m.group(1), m.group(2).strip()
        if name in ("ifdef", "ifndef", "if"):
            if name == "if":
                cond = active and bool(eval_condition(rest, macros))
            else:
                cond = active and ((rest.split()[0] in macros) == (name == "ifdef"))
            stack.append((active, cond, cond))
            active = cond
        elif name == "elif":
            parent, _, taken = stack.pop()
            cond = parent and not taken and bool(eval_condition(rest, macros))
            stack.append((parent, cond, taken or cond))
            active = cond
        elif name == "else":
            parent, _, taken = stack.pop()
            cond = parent and not taken
            stack.append((parent, cond, True))
            active = cond
        elif name == "endif":
            if not stack:
                raise PreprocessError("#endif without #if")
            active = stack.pop()[0]
        elif not active:
            pass
        elif name == "define":
            macro = parse_define(rest)
            macros[macro.name] = macro
        elif name == "undef":
            macros.pop(rest.split()[0] if rest else "", None)
        elif name in IGNORED_DIRECTIVES:
            pass
        else:
            raise PreprocessError(f"unsupported directive #{name}")
        out.append("")
    if stack:
        raise PreprocessError("unterminated #if")
    return "\n".join(out)


_INCLUDE = re.compile(r'^\s*#\s*include\s+"([^"]+)"\s*$', re.M)


def _inline_includes(text: str, include_dir, depth: int) -> str:
    if include_dir is None or depth > 8:
        return text

    def repl(m: re.Match) -> str:
        from pathlib import Path
        target = Path(include_dir) / m.group(1)
        if target.is_file():
            return _inline_includes(target.read_text(encoding="utf-8", errors="replace"), target.parent, depth + 1)
        return ""
    return _INCLUDE.sub(repl, text)


def parse_define(rest: str) -> Macro:
    """`NAME body` or `NAME(a, b) body` → Macro."""
    m = _IDENT.match(rest)
    if not m:
        raise PreprocessError(f"bad #define: {rest!r}")
    name = m.group(0)
    tail = rest[m.end():]
    if tail.startswith("("):
        close = tail.index(")")
        params = [p.strip() for p in tail[1:close].split(",") if p.strip()]
        return Macro(name, params, tail[close + 1:].strip())
    return Macro(name, None, tail.strip())


def expand(line: str, macros: dict[str, Macro], depth: int = 0, disabled: frozenset[str] = frozenset(),
           used: set[str] | None = None) -> str:
    """Macro-expand one line of source (token based, so identifiers inside words are safe).

    A macro is not re-expanded inside its own expansion (C's rule), so `#define vvar vp->vvar` works.
    `used` collects the names of the macros that were expanded.
    """
    if not macros or depth > 64:
        return line
    tokens = tokenize(line, keep_whitespace=True)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        macro = macros.get(tok.value) if tok.kind == "ident" and tok.value not in disabled else None
        if macro is None:
            out.append(tok.value)
            i += 1
            continue
        if used is not None:
            used.add(macro.name)
        if macro.params is None:
            out.append(expand(macro.body, macros, depth + 1, disabled | {macro.name}, used))
            i += 1
            continue
        j = i + 1
        while j < len(tokens) and tokens[j].kind == "ws":
            j += 1
        if j >= len(tokens) or tokens[j].value != "(":
            out.append(tok.value)   # function-like macro name without arguments: leave it
            i += 1
            continue
        args, j = _collect_args(tokens, j)
        # C's rule: arguments are macro-expanded first (so nested calls such as `mind(a, mind(b, c))` work),
        # then substituted, and the result is rescanned with this macro disabled.  Macros already expanded
        # inside the arguments stay disabled during the rescan (C "paints" those tokens blue), so
        # `#define power_inv vp->var.power_inv` is not expanded a second time.
        inner: set[str] = set()
        args = [expand(a, macros, depth + 1, disabled, inner) for a in args]
        if used is not None:
            used |= inner
        out.append(expand(_substitute(macro, args), macros, depth + 1, disabled | {macro.name} | inner, used))
        i = j
    return "".join(out)


def _collect_args(tokens: list[Token], open_index: int) -> tuple[list[str], int]:
    """Split the parenthesised argument list starting at `tokens[open_index]`."""
    depth = 0
    args: list[str] = []
    current: list[str] = []
    i = open_index
    while i < len(tokens):
        t = tokens[i]
        if t.value == "(":
            depth += 1
            if depth > 1:
                current.append(t.value)
        elif t.value == ")":
            depth -= 1
            if depth == 0:
                args.append("".join(current).strip())
                return args, i + 1
            current.append(t.value)
        elif t.value == "," and depth == 1:
            args.append("".join(current).strip())
            current = []
        else:
            current.append(t.value)
        i += 1
    raise UnterminatedArguments("unterminated macro argument list")


def _substitute(macro: Macro, args: list[str]) -> str:
    if len(args) == 1 and args[0] == "" and not macro.params:
        args = []
    if len(args) != len(macro.params or []):
        raise PreprocessError(f"macro {macro.name} expects {len(macro.params or [])} arguments, got {len(args)}")
    mapping = dict(zip(macro.params or [], args))
    tokens = tokenize(macro.body, keep_whitespace=True)
    out: list[str] = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.value == "#" and i + 1 < len(tokens) and tokens[i + 1].kind == "ident" and tokens[i + 1].value in mapping:
            out.append('"' + mapping[tokens[i + 1].value].replace('"', '\\"') + '"')
            i += 2
            continue
        if t.value == "##":
            i += 1
            continue
        if t.kind == "ident" and t.value in mapping:
            out.append("(" + mapping[t.value] + ")" if _needs_parens(mapping[t.value]) else mapping[t.value])
        else:
            out.append(t.value)
        i += 1
    return "".join(out)


def _needs_parens(arg: str) -> bool:
    return bool(re.search(r"[-+*/%<>=!&|^?:]", arg)) and not (arg.startswith("(") and arg.endswith(")"))


def eval_condition(expr: str, macros: dict[str, Macro]) -> int:
    """Evaluate a `#if` constant expression (integers, logic, comparisons, `defined`)."""
    expr = re.sub(r"defined\s*\(\s*(\w+)\s*\)", lambda m: "1" if m.group(1) in macros else "0", expr)
    expr = re.sub(r"defined\s+(\w+)", lambda m: "1" if m.group(1) in macros else "0", expr)
    expr = expand(expr, macros)
    expr = _IDENT.sub(lambda m: m.group(0) if m.group(0) in ("and", "or", "not") else "0", expr)
    expr = expr.replace("&&", " and ").replace("||", " or ").replace("!", " not ").replace(" not =", " !=")
    expr = re.sub(r"\b0x([0-9A-Fa-f]+)", lambda m: str(int(m.group(1), 16)), expr)
    expr = re.sub(r"(\d+)[uUlL]+", r"\1", expr)
    try:
        return int(bool(eval(expr, {"__builtins__": {}}, {})))   # noqa: S307 - constant expression, no names
    except Exception as exc:  # noqa: BLE001
        raise PreprocessError(f"cannot evaluate #if {expr!r}: {exc}") from exc
