"""Script parameters: what `param(…)` declares, how stored values are coerced, which scripts may re-run live, and
rewriting a script's defaults.

A script declares a tunable input with `param('Angle', 30, min=-180, max=180)`; the Script Editor shows one control per
declaration (the *Parameters* tab) and re-runs the script when a control moves. This module is the Qt-free half:

* `ParamSpec` and `make_spec(...)` — the declaration, its kind inferred from the default (`bool`, `int`, `float`,
  `choice`, `text`) with every misuse reported as a `ScriptError`.
* `coerce(spec, value)` — a stored value fitted to the declaration (wrong type → default, numbers clamped, ints
  rounded, unknown choices → default), so values kept for an older version of a script never break the new one.
* `live_blockers(code)` — reasons a script must not re-run on every control change that can be seen without running
  it (imports beyond the harmless ones, `open()`, `exec()` …). The API's own side effects are refused at run time
  instead (`api.LiveRefused`), because they are usually conditional.
* `bake_defaults(code, values)` — the script with the given values written in as the new defaults (only the literal
  default of each `param()` call is replaced, so formatting and comments survive).
"""

from __future__ import annotations

import ast
import math
from dataclasses import dataclass, field
from typing import Any

KINDS = ("float", "int", "bool", "choice", "text")
SAFE_MODULES = frozenset({"math", "cmath", "colorsys", "random", "itertools", "functools", "statistics", "operator", "string", "re",
                          "fractions", "decimal", "collections"})
UNSAFE_CALLS = frozenset({"open", "exec", "eval", "compile", "__import__", "input", "breakpoint"})


class ParameterError(ValueError):
    """A `param()` call that cannot be turned into a control (raised as a ScriptError by the API)."""


@dataclass(frozen=True)
class ParamSpec:
    """One declared parameter.

    Attributes:
        name: The label shown, and the key of the value.
        kind: `float`, `int`, `bool`, `choice` or `text`.
        default: The value used when none is set.
        minimum, maximum: Bounds of a number (both given → a slider; otherwise a spin box).
        step: The increment of the spin box / slider.
        choices: The options of a `choice`.
        decimals: Decimals shown for a float.
        help: Tooltip text.
        line: The declaring line of the script (None when unknown).
    """
    name: str
    kind: str
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    choices: tuple = ()
    decimals: int = 2
    help: str = ""
    line: int | None = field(default=None, compare=False)

    @property
    def bounded(self) -> bool:
        return self.minimum is not None and self.maximum is not None

    def same_control(self, other: "ParamSpec") -> bool:
        """True when `other` would be shown with the same control (the line may differ)."""
        return self == other


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _decimals_for(step: float | None, minimum: float | None, maximum: float | None) -> int:
    if step:
        text = f"{abs(float(step)):.10f}".rstrip("0")
        return max(0, min(6, len(text.split(".")[1]) if "." in text else 0))
    if minimum is not None and maximum is not None:
        return 2 if abs(maximum - minimum) >= 1 else 3
    return 3


def make_spec(name, default, minimum=None, maximum=None, step=None, choices=None, decimals=None, help="", line=None) -> ParamSpec:
    """A `ParamSpec` from the arguments of a `param()` call (raises `ParameterError` on misuse)."""
    if not isinstance(name, str) or not name.strip():
        raise ParameterError("param() needs a name: param('Angle', 30)")
    name = name.strip()
    help = str(help or "")
    if choices is not None:
        options = tuple(choices)
        if not options:
            raise ParameterError(f"param '{name}': choices must not be empty")
        if not all(isinstance(c, str) or _is_number(c) for c in options):
            raise ParameterError(f"param '{name}': choices must be strings or numbers")
        if default not in options:
            raise ParameterError(f"param '{name}': the default {default!r} is not one of the choices")
        if minimum is not None or maximum is not None:
            raise ParameterError(f"param '{name}': a choice has no min / max")
        return ParamSpec(name, "choice", default, choices=options, help=help, line=line)
    if isinstance(default, bool):
        if minimum is not None or maximum is not None or step is not None:
            raise ParameterError(f"param '{name}': a check box (True / False) has no min / max / step")
        return ParamSpec(name, "bool", default, help=help, line=line)
    if isinstance(default, str):
        if minimum is not None or maximum is not None or step is not None:
            raise ParameterError(f"param '{name}': text has no min / max / step (use choices=[…] for a list)")
        return ParamSpec(name, "text", default, help=help, line=line)
    if not _is_number(default):
        raise ParameterError(f"param '{name}': the default must be a number, True / False, text or one of choices=[…], "
                             f"not {type(default).__name__}")
    for label, bound in (("min", minimum), ("max", maximum), ("step", step)):
        if bound is not None and (not _is_number(bound) or not math.isfinite(bound)):
            raise ParameterError(f"param '{name}': {label} must be a number")
    if minimum is not None and maximum is not None and minimum > maximum:
        raise ParameterError(f"param '{name}': min ({minimum}) is greater than max ({maximum})")
    if step is not None and step <= 0:
        raise ParameterError(f"param '{name}': step must be positive")
    if not math.isfinite(default):
        raise ParameterError(f"param '{name}': the default must be a finite number")
    if (minimum is not None and default < minimum) or (maximum is not None and default > maximum):
        raise ParameterError(f"param '{name}': the default {default} is outside min / max")
    integer = isinstance(default, int) and all(b is None or float(b).is_integer() for b in (minimum, maximum, step))
    if integer:
        return ParamSpec(name, "int", int(default), None if minimum is None else int(minimum), None if maximum is None else int(maximum),
                         int(step) if step else 1, decimals=0, help=help, line=line)
    places = int(decimals) if decimals is not None else _decimals_for(step, minimum, maximum)
    return ParamSpec(name, "float", float(default), None if minimum is None else float(minimum),
                     None if maximum is None else float(maximum), None if step is None else float(step),
                     decimals=max(0, min(8, places)), help=help, line=line)


def coerce(spec: ParamSpec, value) -> Any:
    """`value` fitted to `spec` (wrong type → the default; numbers clamped; ints rounded; unknown choice → default)."""
    if value is None:
        return spec.default
    if spec.kind == "bool":
        return value if isinstance(value, bool) else spec.default
    if spec.kind == "text":
        return value if isinstance(value, str) else spec.default
    if spec.kind == "choice":
        return value if value in spec.choices else spec.default
    if not _is_number(value) or not math.isfinite(value):
        return spec.default
    number = float(value)
    if spec.minimum is not None:
        number = max(spec.minimum, number)
    if spec.maximum is not None:
        number = min(spec.maximum, number)
    return int(round(number)) if spec.kind == "int" else number


# --- what can be seen without running ------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Blocker:
    """A reason a script should not re-run live, with its line."""
    reason: str
    line: int | None = None

    def __str__(self) -> str:
        return self.reason + (f" (line {self.line})" if self.line else "")


def live_blockers(code: str) -> list[Blocker]:
    """Imports beyond `SAFE_MODULES` and calls such as `open()` / `exec()`: things a script could do to the world outside
    the fractal, which must not happen on every control change. A script that does not compile has none (it fails when
    it runs)."""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return []
    found: list[Blocker] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in SAFE_MODULES:
                    found.append(Blocker(f"it imports {alias.name}", node.lineno))
        elif isinstance(node, ast.ImportFrom):
            module = (node.module or "").split(".")[0]
            if node.level or module not in SAFE_MODULES:
                found.append(Blocker(f"it imports from {node.module or '.'}", node.lineno))
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in UNSAFE_CALLS:
            found.append(Blocker(f"it calls {node.func.id}()", node.lineno))
    return found


# --- rewriting defaults -----------------------------------------------------------------------------------------------------
def _literal(node: ast.AST) -> bool:
    if isinstance(node, ast.Constant):
        return True
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)) and isinstance(node.operand, ast.Constant):
        return True
    if isinstance(node, (ast.Tuple, ast.List)):
        return all(_literal(e) for e in node.elts)
    return False


def _offset(lines: list[str], line: int, col: int) -> int:
    """Character offset of (1-based line, UTF-8 byte column) in the text."""
    prefix = sum(len(text) + 1 for text in lines[:line - 1])
    return prefix + len(lines[line - 1].encode("utf-8")[:col].decode("utf-8", errors="ignore"))


def _source(value) -> str:
    if isinstance(value, float):
        from .codegen import num
        return num(value)
    return repr(value)


def bake_defaults(code: str, values: dict[str, Any]) -> tuple[str, list[str]]:
    """`code` with the default of every `param('<name>', <default>, …)` call found in `values` replaced by that value.

    Returns:
        (the new code, the names whose default is an expression and could not be rewritten).
    """
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return code, sorted(values)
    lines = code.split("\n")
    edits: list[tuple[int, int, str]] = []
    skipped: list[str] = []
    for node in ast.walk(tree):
        if not (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "param"):
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant) or node.args[0].value not in values:
            continue
        name = node.args[0].value
        target = node.args[1] if len(node.args) > 1 else next((k.value for k in node.keywords if k.arg == "default"), None)
        if target is None or not _literal(target):
            skipped.append(name)
            continue
        start = _offset(lines, target.lineno, target.col_offset)
        end = _offset(lines, target.end_lineno, target.end_col_offset)
        edits.append((start, end, _source(values[name])))
    for start, end, text in sorted(edits, reverse=True):
        code = code[:start] + text + code[end:]
    return code, sorted(set(skipped))


__all__ = ["ParamSpec", "ParameterError", "Blocker", "make_spec", "coerce", "live_blockers", "bake_defaults", "KINDS", "SAFE_MODULES"]
