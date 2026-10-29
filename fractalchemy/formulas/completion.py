"""Completion and quick reference for the formula dialect, Qt-free.

    complete(text, position, explicit)   →  a `Completion` (the same shape the Script Editor's completion uses,
                                            so the one popup widget serves both editors)
    CATALOGUE                            →  every documented name, by group, for the reference panel

The candidates are the names the compiler knows (`lang/builtins.py`: the math functions, the constants, the
point state) plus the plugin API, the C keywords, and what the text itself declares: its variables (`VAR_…`),
struct members and local variables.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from ..scripting.completion import Completion, Item
from .authoring import declared_variables
from .lang import builtins as B

WORD = re.compile(r"[A-Za-z_]\w*")
AUTO_TRIGGER_LETTERS = 2

STATE_DOCS = {
    "FTx": "Input point x (after the transform's affine). pre_ formulas rewrite it.",
    "FTy": "Input point y.",
    "FTz": "Input point depth.",
    "FPx": "Output x: add the formula's contribution (post_ formulas rewrite it).",
    "FPy": "Output y.",
    "FPz": "Output depth (write it for a 3D formula).",
    "TC": "The point colour, 0..1. Writing it makes a direct-colour formula.",
    "VVAR": "The formula's weight on the transform.",
}
API_DOCS = {
    "APO_PLUGIN": ('APO_PLUGIN("name");', "Declares the formula's name. pre_ / post_ prefixes choose when it runs."),
    "APO_VARIABLES": ("APO_VARIABLES( VAR_REAL(name, default), … );", "Declares the user-editable variables (each also a struct member)."),
    "APO_NOVARIABLES": ("APO_NOVARIABLES;", "A formula without variables."),
    "VAR": ("VAR(name)", "A variable's value, or a derived struct member set in PluginVarPrepare."),
    "TM": ("TM(a)", "An affine coefficient of the transform: a, b, c, d, e or f."),
    "VAR_REAL": ("VAR_REAL(name, default)", "A real variable."),
    "VAR_INTEGER": ("VAR_INTEGER(name, default)", "An integer variable."),
    "VAR_REAL_RANGE": ("VAR_REAL_RANGE(name, min, max, default)", "A real variable with bounds."),
    "VAR_INTEGER_RANGE": ("VAR_INTEGER_RANGE(name, min, max, default)", "An integer variable with bounds."),
    "VAR_INTEGER_NONZERO": ("VAR_INTEGER_NONZERO(name, default)", "An integer variable that must not be 0."),
    "VAR_REAL_NONZERO": ("VAR_REAL_NONZERO(name, default)", "A real variable that must not be 0."),
    "VAR_REAL_CYCLE": ("VAR_REAL_CYCLE(name, min, max, default)", "A real variable that wraps around its bounds."),
    "VAR_BOOL": ("VAR_BOOL(name, default)", "A yes / no variable (0 or 1)."),
    "PluginVarPrepare": ("int PluginVarPrepare(Variation* vp)", "Runs once per transform: derive constants from the variables. Return TRUE."),
    "PluginVarCalc": ("int PluginVarCalc(Variation* vp)", "Runs once per point: read FTx / FTy, write FPx / FPy. Return TRUE."),
    "fsincos": ("fsincos(a, &s, &c)", "sin and cos of an angle at once (the SDK helper)."),
    "sinhcosh": ("sinhcosh(x, &sh, &ch)", "sinh and cosh at once."),
    "random01": ("random01()", "A uniform random number in [0, 1). Using it marks the formula as random."),
    "rand": ("rand()", "A random integer (C semantics, RAND_MAX 32767)."),
    "sqr": ("sqr(x)", "x squared."),
}
FUNCTION_DOCS = {
    "atan2": "Angle of (y, x): atan2(FTy, FTx) is the input point's polar angle.",
    "hypot": "sqrt(x² + y²) without overflow.",
    "fmod": "C remainder (the sign follows the dividend).",
    "fabs": "Absolute value.",
    "pow": "x to the power y.",
    "copysign": "x with the sign of y.",
    "lgamma": "log of the gamma function.", "tgamma": "The gamma function.", "erf": "The error function.",
}
KEYWORDS = ("if", "else", "for", "while", "do", "switch", "case", "default", "break", "continue", "return", "typedef", "struct",
            "static", "const", "double", "int", "bool", "void")


@dataclass(frozen=True)
class Reference:
    """One documented name of the dialect."""
    name: str
    group: str          # point state | plugin API | function | constant | keyword
    sig: str
    desc: str


def _function_sig(name: str) -> str:
    counts, _kind = B.MATH_FUNCTIONS[name]
    args = ", ".join("xyz"[i] if i < 3 else f"a{i}" for i in range(max(counts)))
    return f"{name}({args})"


def build_catalogue() -> list[Reference]:
    """Every documented name: the point state, the plugin API, the math functions, the constants, the keywords."""
    out = [Reference(n, "point state", n, d) for n, d in STATE_DOCS.items()]
    out += [Reference(n, "plugin API", sig, d) for n, (sig, d) in API_DOCS.items()]
    for name in sorted(B.MATH_FUNCTIONS):
        if name in API_DOCS or name in ("srand", "time"):
            continue
        counts, kind = B.MATH_FUNCTIONS[name]
        desc = FUNCTION_DOCS.get(name, f"math.h {name}" + (" (complex values too)" if name in B.COMPLEX_FUNCTIONS else ""))
        out.append(Reference(name, "function", _function_sig(name), desc + f" → {kind}" if kind in ("float", "int", "bool") else desc))
    for name, (value, kind) in B.CONSTANTS.items():
        if name in ("true", "false", "NULL"):
            continue
        shown = f"{value:.10g}" if isinstance(value, float) else str(value)
        out.append(Reference(name, "constant", name, f"= {shown}"))
    out += [Reference(k, "keyword", k, "C keyword") for k in KEYWORDS]
    return out


CATALOGUE: list[Reference] = build_catalogue()
_BY_NAME = {r.name: r for r in CATALOGUE}
_KIND_OF_GROUP = {"point state": "variable", "plugin API": "function", "function": "function", "constant": "constant", "keyword": "keyword"}


def reference(name: str) -> Reference | None:
    """The documentation of `name`, if it is a name of the dialect."""
    return _BY_NAME.get(name)


def _local_names(text: str) -> list[str]:
    """Identifiers the text declares itself: variables, struct members, locals (`double a, b`)."""
    names: list[str] = []
    for name in declared_variables(text):
        if name not in names:
            names.append(name)
    struct = re.search(r"typedef\s+struct\s*\{(.*?)\}", text, re.S)
    if struct:
        for line in struct.group(1).split(";"):
            for name in WORD.findall(line.split("//")[0]):
                if name not in ("double", "int", "bool") and name not in names:
                    names.append(name)
    for m in re.finditer(r"\b(?:double|int|bool)\s+([^;=(){}]*)", text):
        for name in WORD.findall(m.group(1)):
            if name not in names and name not in ("double", "int", "bool"):
                names.append(name)
    return names


def _in_string_or_comment(text: str, position: int) -> bool:
    """True when `position` is inside a string literal, a `//` comment or a `/* */` comment."""
    before = text[:position]
    if "/*" in before and before.rfind("/*") > before.rfind("*/"):
        return True
    line = before[before.rfind("\n") + 1:]
    if "//" in line:
        return True
    return line.count('"') % 2 == 1


def complete(text: str, position: int, explicit: bool = False) -> Completion:
    """Candidates for the word ending at `position` (an empty list inside strings and comments, or — unless `explicit` —
    with fewer than `AUTO_TRIGGER_LETTERS` letters typed)."""
    before = text[:position]
    m = re.search(r"[A-Za-z_]\w*$", before)
    prefix = m.group(0) if m else ""
    start = position - len(prefix)
    if _in_string_or_comment(text, position) or (not explicit and len(prefix) < AUTO_TRIGGER_LETTERS):
        return Completion([], prefix, start)
    declared = declared_variables(text)
    items: list[Item] = []
    seen: set[str] = set()
    low = prefix.lower()

    def add(name: str, kind: str, desc: str = "", sig: str = "", type_: str = "") -> None:
        if name in seen or (low and not name.lower().startswith(low)):
            return
        seen.add(name)
        items.append(Item(name, kind, type_, desc, sig))

    for name in declared:
        add(name, "variable", "a variable of this formula — use VAR(name)", "", "variable")
    for name in _local_names(text):
        if name not in declared:
            add(name, "variable", "declared in this file", "", "local")
    for ref in CATALOGUE:
        add(ref.name, _KIND_OF_GROUP[ref.group], ref.desc, ref.sig if ref.group in ("plugin API", "function") else "", ref.group)
    if not explicit and len(items) == 1 and items[0].name == prefix:
        items = []
    return Completion(items, prefix, start)


__all__ = ["complete", "Reference", "CATALOGUE", "reference", "build_catalogue", "STATE_DOCS", "API_DOCS", "AUTO_TRIGGER_LETTERS"]
