"""Folding `const` initializers that stopped being constant expressions — the `Math.frag` / `sqrt` problem.

`Math.frag` redefines `float sqrt(float)` as a user function (to overload it for doubles). GLSL then no longer
treats `const float phi = (sqrt(5.0) + 1.0) / 2.0;` as a constant expression and every driver rejects the line
(NVIDIA's C1059, Mesa's "initializer of const variable must be a constant expression"). FragM has the same
failure. The compatibility layer evaluates such initializers itself when they are made of nothing but numeric
literals, arithmetic, the standard maths functions and earlier folded constants / numeric `#define`s, and writes
the value back as a literal — the same number the user's wrapper would have produced. Anything else is left
untouched; only `float` / `int` scalars are considered and only when the initializer calls a function (plain
arithmetic is a constant expression already).
"""

from __future__ import annotations

import ast
import math
import re

RE_CONST = re.compile(r"^(\s*const\s+(float|int)\s+([A-Za-z_]\w*)\s*=\s*)(.+?)(\s*;.*)$")
RE_DEFINE = re.compile(r"^\s*#\s*define\s+([A-Za-z_]\w*)\s+([-+]?(?:\d+\.?\d*|\.\d+)(?:[eE][-+]?\d+)?)[fF]?\s*$")
RE_FLOAT_SUFFIX = re.compile(r"(\d\.?\d*(?:[eE][-+]?\d+)?)[fF]\b")
RE_CALL = re.compile(r"[A-Za-z_]\w*\s*\(")

FUNCTIONS = {
    "sqrt": math.sqrt, "sin": math.sin, "cos": math.cos, "tan": math.tan, "asin": math.asin, "acos": math.acos,
    "atan": lambda y, x=None: math.atan(y) if x is None else math.atan2(y, x), "exp": math.exp, "log": math.log,
    "exp2": lambda x: 2.0 ** x, "log2": math.log2, "pow": math.pow, "abs": abs, "floor": math.floor, "ceil": math.ceil,
    "fract": lambda x: x - math.floor(x), "mod": lambda x, y: x - y * math.floor(x / y), "min": min, "max": max,
    "sign": lambda x: (x > 0) - (x < 0), "radians": math.radians, "degrees": math.degrees,
    "inversesqrt": lambda x: 1.0 / math.sqrt(x), "clamp": lambda x, lo, hi: min(max(x, lo), hi),
    "mix": lambda a, b, t: a + (b - a) * t, "step": lambda e, x: 0.0 if x < e else 1.0, "float": float, "int": int,
}
OPERATORS = {ast.Add: lambda a, b: a + b, ast.Sub: lambda a, b: a - b, ast.Mult: lambda a, b: a * b, ast.Div: lambda a, b: a / b}


class NotConstant(ValueError):
    """The expression is not something the folder can evaluate."""


def evaluate(expression: str, known: dict[str, float]) -> float:
    """The value of a GLSL numeric expression over literals, `known` names and `FUNCTIONS`; raises `NotConstant`."""
    text = RE_FLOAT_SUFFIX.sub(r"\1", expression)
    try:
        tree = ast.parse(text, mode="eval")
    except SyntaxError as exc:
        raise NotConstant(str(exc)) from exc
    return _eval(tree.body, known)


def _eval(node, known: dict[str, float]) -> float:
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
        return node.value
    if isinstance(node, ast.Name) and node.id in known:
        return known[node.id]
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
        value = _eval(node.operand, known)
        return -value if isinstance(node.op, ast.USub) else value
    if isinstance(node, ast.BinOp) and type(node.op) in OPERATORS:
        return OPERATORS[type(node.op)](_eval(node.left, known), _eval(node.right, known))
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FUNCTIONS and not node.keywords:
        try:
            return FUNCTIONS[node.func.id](*[_eval(a, known) for a in node.args])
        except (TypeError, ValueError, ZeroDivisionError, OverflowError) as exc:
            raise NotConstant(str(exc)) from exc
    raise NotConstant("not a numeric expression")


def literal(value: float, glsl_type: str) -> str | None:
    """`value` as a GLSL literal of `glsl_type` (None when an int would not be whole or the value is not finite)."""
    if isinstance(value, float) and not math.isfinite(value):
        return None
    if glsl_type == "int":
        return str(int(value)) if float(value).is_integer() else None
    text = f"{float(value):.9g}"
    return text if ("." in text or "e" in text) else text + ".0"


def fold_const_initializers(lines: list[str]) -> tuple[list[str], list[str]]:
    """`(lines, names folded)`: `const float/int` scalar initializers with function calls replaced by their value."""
    known: dict[str, float] = {}
    out: list[str] = []
    folded: list[str] = []
    for line in lines:
        define = RE_DEFINE.match(line)
        if define:
            known[define.group(1)] = float(define.group(2))
        match = RE_CONST.match(line)
        if not match:
            out.append(line)
            continue
        head, glsl_type, name, expression, tail = match.groups()
        replacement = None
        if RE_CALL.search(expression):
            try:
                value = evaluate(expression, known)
                replacement = literal(value, glsl_type)
            except NotConstant:
                replacement = None
        if replacement is None:
            try:
                known[name] = evaluate(expression, known)
            except NotConstant:
                pass
            out.append(line)
            continue
        known[name] = float(replacement)
        folded.append(name)
        out.append(f"{head}{replacement}{tail}  // was: {expression}")
    return out, folded


__all__ = ["fold_const_initializers", "evaluate", "literal", "NotConstant"]
