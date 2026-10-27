"""Semantic analysis: plugin specification, scoping, typing, uniformity and helper inlining.

The parser gives a `Module`; this module turns it into a `PluginSpec` whose functions are
typed, alpha-renamed (every local has a unique name, so backends need no scope handling),
and annotated with the facts the backends need:

* which names are parameters (`VAR(x)` declared in `APO_VARIABLES`), *derived* values
  (set in `PluginVarPrepare`, constant per transform) or scratch members;
* the type (float / int / bool) of every expression;
* for the numpy backend, whether an expression is *uniform* — the same for every point
  of a batch — so it can stay a Python scalar while everything else becomes an array.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from .builtins import (AFFINE_NAMES, COMPLEX_FUNCTIONS, CONSTANTS, FLOAT_SUFFIX_ALIASES, MATH_FUNCTIONS,
                       OUT_FUNCTIONS, STATE_NAMES, VARIABLE_MACROS)
from .nodes import (
    BOOL, COMPLEX, FLOAT, INT, VOID, AddressOf, Assign, Binary, Block, Break, Call, Case, Cast, Continue, Decl, Declarator, Expr,
    ExprStmt, For, FuncDef, If, IncDec, Index, Module, Name, Num, Return, Stmt, Str, Switch, Ternary, Unary, While, clone,
)


class SemanticError(ValueError):
    """The source is valid C but outside what the formula compiler supports."""


@dataclass
class VariableDecl:
    """One user-facing parameter (`VAR_REAL(name, default)` and friends)."""
    name: str
    type: str
    default: float
    min: float | None = None
    max: float | None = None
    cyclic: bool = False
    nonzero: bool = False


@dataclass
class Symbol:
    """A named value inside a function after renaming."""
    name: str
    type: str
    dims: list[int] = field(default_factory=list)
    kind: str = "local"         # local | param | derived | scratch | state | affine | weight | const | helper_param
    uniform: bool = True
    value: Any = None           # constant value for kind == "const"


@dataclass
class FunctionInfo:
    """A typed, renamed function ready for the backends."""
    node: FuncDef
    symbols: dict[str, Symbol]
    uses_random: bool = False
    touches: set[str] = field(default_factory=set)   # state names read or written
    writes: set[str] = field(default_factory=set)
    calls: set[str] = field(default_factory=set)      # helper functions called (transitively)
    needs: set[str] = field(default_factory=set)      # context a helper must be handed: state | weight | affine | random

    def uses_context(self) -> set[str]:
        """Context items used directly (not via callees)."""
        out = set()
        if self.touches:
            out.add("state")
        if any(sym.kind == "weight" for sym in self.symbols.values()):
            out.add("weight")
        if any(sym.kind == "affine" for sym in self.symbols.values()):
            out.add("affine")
        if self.uses_random:
            out.add("random")
        return out


@dataclass
class PluginSpec:
    """Everything known about one formula after analysis."""
    name: str
    variables: list[VariableDecl]
    calc: FunctionInfo
    calc_inlined: FunctionInfo                 # helpers inlined, for the numpy backend
    prepare: FunctionInfo | None
    prepare_inlined: FunctionInfo | None
    helpers: dict[str, FunctionInfo]           # in dependency order
    derived: list[str]                         # names computed by prepare, constant per transform
    derived_types: dict[str, str]
    derived_dims: dict[str, list[int]]         # the ones that are lookup tables
    scratch: list[str]                         # struct members used as per-call temporaries
    const_globals: list[tuple[str, str, list[int], Any]]   # (name, type, dims, value) lookup tables
    warnings: list[str]

    @property
    def kind(self) -> str:
        if self.name.startswith("pre_"):
            return "pre"
        if self.name.startswith("post_") or self.name == "flatten":
            return "post"
        return "normal"

    @property
    def writes_z(self) -> bool:
        return bool({"FPz", "FTz"} & self.calc.writes)

    @property
    def writes_color(self) -> bool:
        return "TC" in self.calc.writes

    @property
    def uses_affine(self) -> bool:
        return any(s.kind == "affine" for s in self.calc.symbols.values())

    @property
    def uses_random(self) -> bool:
        return self.calc.uses_random


# --- constant evaluation ---------------------------------------------------------------
def const_eval(expr: Expr, env: dict[str, Any] | None = None):
    """Evaluate a constant expression (numbers, constants, arithmetic, casts, simple calls)."""
    env = env or {}
    if isinstance(expr, Num):
        return expr.value
    if isinstance(expr, Name):
        if expr.id in env:
            return env[expr.id]
        if expr.id in CONSTANTS:
            return CONSTANTS[expr.id][0]
        raise SemanticError(f"{expr.id!r} is not a constant")
    if isinstance(expr, Unary):
        v = const_eval(expr.operand, env)
        return {"-": lambda x: -x, "+": lambda x: x, "!": lambda x: int(not x), "~": lambda x: ~int(x)}[expr.op](v)
    if isinstance(expr, Cast):
        v = const_eval(expr.operand, env)
        return int(v) if expr.to == INT else float(v) if expr.to == FLOAT else bool(v)
    if isinstance(expr, Binary):
        a, b = const_eval(expr.left, env), const_eval(expr.right, env)
        both_int = isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) and not isinstance(b, bool)
        ops = {
            "+": lambda: a + b, "-": lambda: a - b, "*": lambda: a * b,
            "/": lambda: (int(a / b) if both_int else a / b), "%": lambda: math.fmod(a, b),
            "<": lambda: int(a < b), ">": lambda: int(a > b), "<=": lambda: int(a <= b), ">=": lambda: int(a >= b),
            "==": lambda: int(a == b), "!=": lambda: int(a != b), "&&": lambda: int(bool(a) and bool(b)),
            "||": lambda: int(bool(a) or bool(b)), "&": lambda: int(a) & int(b), "|": lambda: int(a) | int(b),
            "^": lambda: int(a) ^ int(b), "<<": lambda: int(a) << int(b), ">>": lambda: int(a) >> int(b),
        }
        return ops[expr.op]()
    if isinstance(expr, Ternary):
        return const_eval(expr.then, env) if const_eval(expr.cond, env) else const_eval(expr.other, env)
    if isinstance(expr, Call) and expr.func in ("sqrt", "sin", "cos", "tan", "atan", "exp", "log", "pow", "fabs", "floor", "atan2", "sqr", "ceil", "abs"):
        args = [const_eval(a, env) for a in expr.args]
        fn = {"sqr": lambda x: x * x, "fabs": abs, "abs": abs}.get(expr.func) or getattr(math, expr.func)
        return fn(*args)
    raise SemanticError("expression is not constant")


# --- renaming / scoping ----------------------------------------------------------------
class _Scope:
    def __init__(self, parent: "_Scope | None" = None):
        self.parent = parent
        self.names: dict[str, str] = {}

    def lookup(self, name: str) -> str | None:
        s: _Scope | None = self
        while s is not None:
            if name in s.names:
                return s.names[name]
            s = s.parent
        return None


class _Warnings(list):
    """A list that ignores duplicates."""

    def append(self, item):
        if item not in self:
            super().append(item)


class Analyzer:
    """Runs the whole analysis for one module."""

    def __init__(self, module: Module):
        self.module = module
        self.warnings: list[str] = _Warnings()
        self.variables: dict[str, VariableDecl] = {}
        self.struct: dict[str, tuple[str, list[int]]] = {}
        self.statics: dict[str, tuple[str, list[int]]] = {}
        self.static_inits: dict[str, Any] = {}
        self.const_globals: dict[str, tuple[str, list[int], Any]] = {}
        self.derived: dict[str, str] = {}
        self.scratch: dict[str, str] = {}
        self.scratch_dims: dict[str, list[int]] = {}
        self.derived_dims: dict[str, list[int]] = {}
        self.local_tables: dict[str, tuple[str, list[int], Any]] = {}   # constant arrays declared inside functions
        self.calc_scratch: set[str] = set()          # derived values a calc also modifies
        self.orbit_statics: dict[str, tuple[str, Any]] = {}
        self.helper_defs: dict[str, FuncDef] = {}
        self.reserved: set[str] = set(CONSTANTS) | set(STATE_NAMES) | {"VVAR"}

    # --- entry point -------------------------------------------------------------------
    def run(self) -> PluginSpec:
        name = self._plugin_name()
        self._collect_variables()
        self._collect_struct()
        self._collect_globals()
        self.reserved |= set(self.variables) | set(self.struct) | set(self.statics) | set(self.const_globals)
        funcs = dict(self.module.functions)
        calc_def = funcs.pop("PluginVarCalc", None)
        prepare_def = funcs.pop("PluginVarPrepare", None)
        if calc_def is None:
            raise SemanticError("no PluginVarCalc function")
        self.helper_defs = funcs
        self._classify_members(calc_def, prepare_def)
        if self.orbit_statics:
            calc_def = _orbit_wrap(calc_def, self.orbit_statics)
            self.warnings.append("stateful plugin: its private orbit is re-run %d steps per point" % ORBIT_STEPS)
        closures = any(f.closure for f in funcs.values())
        lower = Inliner(funcs, inline_helpers=closures)   # closures see the caller's locals: inline them everywhere
        helpers = {n: self.analyze_function(lower.inline(f), is_helper=True) for n, f in funcs.items() if not f.closure}
        calc = self.analyze_function(lower.inline(calc_def))
        prepare = self.analyze_function(lower.inline(prepare_def), is_prepare=True) if prepare_def else None
        for info in list(helpers.values()) + [calc] + ([prepare] if prepare else []):
            _close_calls(info, helpers)
        calc_inl = self.analyze_function(Inliner(funcs).inline(calc_def), inlined=True)
        prepare_inl = self.analyze_function(Inliner(funcs).inline(prepare_def), is_prepare=True, inlined=True) if prepare_def else None
        helpers_ordered = _order_helpers(helpers)
        return PluginSpec(
            name=name, variables=list(self.variables.values()), calc=calc, calc_inlined=calc_inl,
            prepare=prepare, prepare_inlined=prepare_inl, helpers=helpers_ordered,
            derived=sorted(self.derived), derived_types=dict(self.derived), derived_dims=dict(self.derived_dims),
            scratch=sorted(self.scratch),
            const_globals=[(n, t, d, v) for n, (t, d, v) in list(self.const_globals.items()) + list(self.local_tables.items())],
            warnings=self.warnings,
        )

    # --- module level ------------------------------------------------------------------
    def _plugin_name(self) -> str:
        for call in self.module.top_calls:
            if call.func == "APO_PLUGIN":
                if len(call.args) == 1 and isinstance(call.args[0], Str):
                    return call.args[0].value
                raise SemanticError("APO_PLUGIN needs a string literal name")
        raise SemanticError("no APO_PLUGIN(\"name\") declaration")

    def _collect_variables(self) -> None:
        for call in self.module.top_calls:
            if call.func != "APO_VARIABLES":
                continue
            for arg in call.args:
                if not isinstance(arg, Call) or arg.func not in VARIABLE_MACROS:
                    raise SemanticError("APO_VARIABLES entries must be VAR_REAL / VAR_INTEGER / … macros")
                if not arg.args or not isinstance(arg.args[0], Name):
                    raise SemanticError(f"{arg.func}: first argument must be the variable name")
                vname = arg.args[0].id
                values = [const_eval(a) for a in arg.args[1:]]
                is_int = "INTEGER" in arg.func or arg.func == "VAR_BOOL"
                if arg.func in ("VAR_REAL_RANGE", "VAR_INTEGER_RANGE", "VAR_REAL_CYCLE"):
                    lo, hi, default = values
                else:
                    (default,) = values
                    lo = hi = None
                var = VariableDecl(vname, INT if is_int else FLOAT, int(default) if is_int else float(default),
                                   lo, hi, cyclic=arg.func == "VAR_REAL_CYCLE", nonzero=arg.func.endswith("_NONZERO"))
                self.variables[vname] = var

    def _collect_struct(self) -> None:
        for f in self.module.struct_fields:
            self.struct[f.name] = (f.type, f.dims)
            if f.name in self.variables and f.type != self.variables[f.name].type:
                self.variables[f.name].type = f.type if f.type in (FLOAT, INT) else self.variables[f.name].type

    def _collect_globals(self) -> None:
        for decl in self.module.globals:
            for d in decl.declarators:
                env = {n: v for n, (_, _, v) in self.const_globals.items()}
                if decl.const and d.init is not None:
                    self.const_globals[d.name] = (decl.type, d.dims, _eval_init(d.init, d.dims, env))
                    continue
                self.statics[d.name] = (decl.type, d.dims)
                if d.init is not None:
                    try:
                        self.static_inits[d.name] = _eval_init(d.init, d.dims, env)
                    except SemanticError as exc:
                        raise SemanticError(f"initialiser of global {d.name} must be constant") from exc

    def _classify_members(self, calc: FuncDef, prepare: FuncDef | None) -> None:
        """Struct members / statics: parameters, derived (set by prepare) or scratch."""
        prep_writes = _assigned_vars(prepare.body) if prepare else set()
        calc_writes = _assigned_vars(calc.body)
        for helper in self.helper_defs.values():
            calc_writes |= _assigned_vars(helper.body)
        for n, (t, dims) in list(self.statics.items()):
            if n in calc_writes:
                if dims:
                    raise SemanticError(f"static array {n} is modified while iterating (port by hand)")
                # a private orbit: the plugin keeps its own point between calls (see `_orbit_wrap`)
                self.orbit_statics[n] = (t, self.static_inits.get(n, 0))
                self.scratch[n] = t
                del self.statics[n]
                continue
            if n not in prep_writes and n in self.static_inits:   # initialised, never changed: a constant
                self.const_globals[n] = (t, dims, self.static_inits[n])
                del self.statics[n]
        for n, (t, dims) in list(self.struct.items()) + list(self.statics.items()):
            if n in self.variables:
                if n in prep_writes:
                    self.warnings.append(f"prepare modifies parameter {n}; treated as derived")
                    self.derived[n] = t
                continue
            if n in prep_writes:
                if dims:
                    self.derived_dims[n] = list(dims)   # a lookup table filled once per transform
                self.derived[n] = t
                if n in calc_writes:                    # prepared, then changed while iterating: per-call scratch
                    self.calc_scratch.add(n)
                    if dims:
                        self.scratch_dims[n] = list(dims)
            else:
                self.scratch[n] = t
                if dims:
                    self.scratch_dims[n] = list(dims)

    # --- functions ------------------------------------------------------------------------
    def analyze_function(self, fn: FuncDef, is_helper: bool = False, is_prepare: bool = False, inlined: bool = False) -> FunctionInfo:
        """Type and annotate `fn` in place (callers pass a fresh copy from `Inliner.inline`)."""
        info = FunctionInfo(fn, {})
        typer = _Typer(self, info, is_helper, is_prepare)
        typer.function(fn)
        if inlined or not is_helper:
            _Uniformity(info, is_prepare).run(fn)
        return info


ORBIT_STEPS = 12


def _orbit_wrap(calc: FuncDef, statics: dict[str, tuple[str, Any]]) -> FuncDef:
    """Emulate a plugin that carries its own point in static variables between calls.

    Each call of the original advances a private orbit by one step; our engines have no
    per-point memory for it, so every call restarts the orbit from the initial values and
    runs `ORBIT_STEPS` steps, keeping only the last step's output — a sample of the same
    attractor. Early returns end a step (`continue`); every step starts from the accumulator
    as it was before the call, so only the last step's output remains.
    """
    calc = clone(calc)
    body = _ReturnToContinue().block(calc.body)
    k = "orbit_k_"
    saved = [(f"orbit_{n}_", n) for n in ("FPx", "FPy", "FPz", "TC")]
    restore = [ExprStmt(Assign(Name(n), "=", Name(tmp))) for tmp, n in saved]
    loop_body = Block(restore + body.body)
    init = [Decl(t, [Declarator(n, [], Num(v, t == INT))]) for n, (t, v) in statics.items()]
    init += [Decl(FLOAT, [Declarator(tmp, [], Name(n))]) for tmp, n in saved]
    loop = For(Decl(INT, [Declarator(k, [], Num(0, True))]), Binary("<", Name(k), Num(ORBIT_STEPS, True)),
               Block([ExprStmt(IncDec(Name(k), "++", False))]), loop_body)
    calc.body = Block(init + [loop, Return(Name("TRUE"))])
    return calc


class _ReturnToContinue:
    """`return` → `continue` (inside the orbit loop; nested loops keep their own breaks)."""

    def block(self, block: Block) -> Block:
        return Block([self.stmt(s) for s in block.body])

    def stmt(self, s: Stmt) -> Stmt:
        if isinstance(s, Return):
            return Continue()
        if isinstance(s, Block):
            return self.block(s)
        if isinstance(s, If):
            return If(s.cond, self.block(_as_block(s.then)), self.block(_as_block(s.other)) if s.other else None)
        if isinstance(s, (While, For)):
            if _contains_return(s.body):
                raise SemanticError("a stateful plugin returning from inside a loop is not supported (port by hand)")
        if isinstance(s, Switch):
            for c in s.cases:
                c.body = [self.stmt(st) for st in c.body]
        return s


def _contains_return(node) -> bool:
    if isinstance(node, Return):
        return True
    return any(_contains_return(c) for c in _children(node))


def _never_written_arrays(block: Block) -> set[str]:
    """Names of array locals that are only ever read (candidates for constant tables)."""
    declared: set[str] = set()
    written: set[str] = set()

    def visit(node):
        if isinstance(node, Decl):
            for d in node.declarators:
                if d.dims:
                    declared.add(d.name)
        elif isinstance(node, (Assign, IncDec)):
            try:
                written.add(_lvalue_name(node.target))
            except SemanticError:
                pass
        elif isinstance(node, Call):
            if node.func in OUT_FUNCTIONS:
                for a in node.args[1:]:
                    written.add(_lvalue_name(a.operand if isinstance(a, AddressOf) else a))
            else:   # any array handed to another function may be written there
                for a in node.args:
                    if isinstance(a, (Name, AddressOf)):
                        written.add(a.id if isinstance(a, Name) else _lvalue_name(a.operand))
                    if isinstance(a, Index):
                        written.add(_lvalue_name(a))
        for c in _children(node):
            visit(c)
    visit(block)
    return declared - written


def _assigned_vars(block: Block) -> set[str]:
    out: set[str] = set()

    def visit(node):
        if isinstance(node, Assign):
            out.add(_lvalue_name(node.target))
        elif isinstance(node, IncDec):
            out.add(_lvalue_name(node.target))
        elif isinstance(node, Call) and node.func in OUT_FUNCTIONS:
            for a in node.args[1:]:
                out.add(_lvalue_name(a.operand if isinstance(a, AddressOf) else a))
        for child in _children(node):
            visit(child)
    visit(block)
    return out


def _lvalue_name(expr: Expr) -> str:
    if isinstance(expr, Name):
        return expr.id
    if isinstance(expr, Index):
        return _lvalue_name(expr.base)
    if isinstance(expr, Call) and expr.func == "VAR":
        return expr.args[0].id
    if isinstance(expr, AddressOf):
        return _lvalue_name(expr.operand)
    raise SemanticError("invalid assignment target")


def _children(node):
    if isinstance(node, list):
        yield from node
        return
    if not hasattr(node, "__dataclass_fields__"):
        return
    for f in node.__dataclass_fields__:
        if f in ("type", "uniform"):
            continue
        v = getattr(node, f)
        if isinstance(v, list):
            for item in v:
                if hasattr(item, "__dataclass_fields__") or isinstance(item, list):
                    yield item
        elif hasattr(v, "__dataclass_fields__"):
            yield v


def _eval_init(init, dims: list[int], env: dict[str, Any]):
    if isinstance(init, list):
        if not dims:
            raise SemanticError("brace initialiser for a scalar")
        values = [_eval_init(item, dims[1:], env) for item in init]
        size = dims[0] or len(values)
        if len(dims) == 1:
            values = values + [0] * (size - len(values))
        return values
    if dims:
        raise SemanticError("array needs a brace initialiser")
    return const_eval(init, env)


# --- typing ------------------------------------------------------------------------------
class _Typer:
    """Resolves names, renames locals uniquely, assigns expression types, records accesses."""

    def __init__(self, an: Analyzer, info: FunctionInfo, is_helper: bool, is_prepare: bool):
        self.an = an
        self.info = info
        self.is_helper = is_helper
        self.is_prepare = is_prepare
        self.scope = _Scope()
        self.counter: dict[str, int] = {}
        self.loop_depth = 0
        self.aliases: dict[str, Expr] = {}   # pointer locals standing for an array row
        self.pointer_locals: set[str] = set()

    def unique(self, name: str) -> str:
        """A function-wide unique name for a local (never one of the module-level names)."""
        n = self.counter.get(name, 0)
        self.counter[name] = n + 1
        candidate = name if n == 0 else f"{name}_{n + 1}"
        while candidate in self.an.reserved:
            candidate += "_l"
        return candidate

    def declare(self, name: str, typ: str, dims: list[int], kind: str = "local") -> Symbol:
        uname = self.unique(name)
        self.scope.names[name] = uname
        sym = Symbol(uname, typ, list(dims), kind)
        self.info.symbols[uname] = sym
        return sym

    def function(self, fn: FuncDef) -> None:
        self.never_written = _never_written_arrays(fn.body)
        for p in fn.params:
            if p.name == "vp":
                continue
            sym = self.declare(p.name, p.type, p.dims, "helper_param")
            sym.uniform = False
            p.name = sym.name
        self.block(fn.body, new_scope=False)

    def block(self, block: Block, new_scope: bool = True) -> None:
        if new_scope:
            self.scope = _Scope(self.scope)
        for stmt in block.body:
            self.stmt(stmt)
        if new_scope:
            self.scope = self.scope.parent

    def stmt(self, s: Stmt) -> None:
        if isinstance(s, Block):
            self.block(s)
        elif isinstance(s, InlineBody):
            self.block(s.body)
        elif isinstance(s, Decl):
            keep = []
            for d in s.declarators:
                if d.pointer:
                    if d.init is None:      # `double* U;` — bound later by `U = row;`
                        self.pointer_locals.add(d.name)
                        continue
                    target = d.init.operand if isinstance(d.init, AddressOf) else d.init
                    if isinstance(target, Name):
                        self.expr(target)
                        self.scope.names[d.name] = target.id   # alias: every use reads/writes the target
                        continue
                    if isinstance(target, Index):              # double* U = table[k];  →  U[i] reads table[k][i]
                        self.expr(target)
                        self.aliases[d.name] = target
                        continue
                    raise SemanticError(f"pointer variable {d.name} must alias a variable or an array row")
                if d.dims and isinstance(d.init, list) and d.name in self.never_written:
                    try:   # a lookup table written inside the function: make it a constant table
                        value = _eval_init(d.init, d.dims, {n: v for n, (_, _, v) in self.an.const_globals.items()})
                    except SemanticError:
                        value = None
                    if value is not None:
                        uname = self.unique(d.name)
                        self.scope.names[d.name] = uname
                        sym = Symbol(uname, s.type, list(d.dims), "const")
                        sym.value = value
                        self.info.symbols[uname] = sym
                        self.an.local_tables[uname] = (s.type, list(d.dims), value)
                        continue
                if d.init is not None:
                    if isinstance(d.init, list):
                        self._init_list(d.init)
                    else:
                        self.expr(d.init)
                sym = self.declare(d.name, s.type, d.dims)
                d.name = sym.name
                keep.append(d)
                if s.static:
                    self.an.warnings.append(f"static local {d.name} treated as an ordinary local")
            s.declarators = keep
        elif isinstance(s, ExprStmt):
            e = s.expr
            if isinstance(e, Assign) and e.op == "=" and isinstance(e.target, Name) and e.target.id in self.pointer_locals \
                    and self.scope.lookup(e.target.id) is None:
                target = e.value.operand if isinstance(e.value, AddressOf) else e.value
                if isinstance(target, Name):
                    self.expr(target)
                    self.aliases.pop(e.target.id, None)
                    self.scope.names[e.target.id] = target.id
                elif isinstance(target, Index):
                    self.expr(target)
                    self.aliases[e.target.id] = target
                else:
                    raise SemanticError(f"pointer {e.target.id} must be assigned a variable or an array row")
                s.expr = Num(0, True)   # the binding itself generates no code
                return
            self.expr(s.expr)
        elif isinstance(s, If):
            self.cond(s.cond)
            self.stmt(s.then)
            if s.other:
                self.stmt(s.other)
        elif isinstance(s, For):
            self.scope = _Scope(self.scope)
            if isinstance(s.init, Block):
                self.block(s.init, new_scope=False)   # the loop variable belongs to the loop's scope
            elif s.init:
                self.stmt(s.init)
            if s.cond:
                self.cond(s.cond)
            if s.step:
                self.stmt(s.step)
            self.loop_depth += 1
            self.stmt(s.body)
            self.loop_depth -= 1
            self.scope = self.scope.parent
        elif isinstance(s, While):
            self.cond(s.cond)
            self.loop_depth += 1
            self.stmt(s.body)
            self.loop_depth -= 1
        elif isinstance(s, Switch):
            self.expr(s.subject)
            for c in s.cases:
                for v in c.values or []:
                    self.expr(v)
                self.scope = _Scope(self.scope)
                for st in c.body:
                    self.stmt(st)
                self.scope = self.scope.parent
        elif isinstance(s, Return):
            if s.value is not None:
                self.expr(s.value)
        elif isinstance(s, (Break, Continue)):
            pass
        else:
            raise SemanticError(f"unsupported statement {type(s).__name__}")

    def _init_list(self, items) -> None:
        for it in items:
            if isinstance(it, list):
                self._init_list(it)
            else:
                self.expr(it)

    def cond(self, e: Expr) -> None:
        self.expr(e)

    # --- expressions -------------------------------------------------------------------
    def expr(self, e: Expr) -> str:
        t = self._expr(e)
        e.type = t
        return t

    def _expr(self, e: Expr) -> str:
        if isinstance(e, Num):
            return INT if e.is_int else FLOAT
        if isinstance(e, Str):
            raise SemanticError("string values are not supported")
        if isinstance(e, Name):
            return self.name(e)
        if isinstance(e, Unary):
            t = self.expr(e.operand)
            if e.op == "!":
                return BOOL
            if e.op == "~":
                return INT
            return t if t in (FLOAT, COMPLEX) else INT
        if isinstance(e, Cast):
            self.expr(e.operand)
            return e.to
        if isinstance(e, AddressOf):
            return self.expr(e.operand)
        if isinstance(e, Binary):
            lt, rt = self.expr(e.left), self.expr(e.right)
            if COMPLEX in (lt, rt):
                if e.op in ("+", "-", "*", "/"):
                    return COMPLEX
                if e.op in ("==", "!="):
                    return BOOL
                raise SemanticError(f"operator {e.op} is not defined for complex values")
            if e.op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
                return BOOL
            if e.op in ("&", "|", "^", "<<", ">>", "%") and lt != FLOAT and rt != FLOAT:
                return INT
            if e.op == "%":
                return FLOAT
            return FLOAT if FLOAT in (lt, rt) else INT
        if isinstance(e, Ternary):
            self.expr(e.cond)
            a, b = self.expr(e.then), self.expr(e.other)
            return COMPLEX if COMPLEX in (a, b) else FLOAT if FLOAT in (a, b) else INT if INT in (a, b) else BOOL
        if isinstance(e, Assign):
            tt = self.expr(e.target)
            self.expr(e.value)
            self._record_write(e.target)
            return tt
        if isinstance(e, IncDec):
            tt = self.expr(e.target)
            self._record_write(e.target)
            return tt
        if isinstance(e, Index):
            if isinstance(e.base, Name) and e.base.id in self.aliases and self.scope.lookup(e.base.id) is None:
                e.base = clone(self.aliases[e.base.id])   # already typed/renamed expression
                it = self.expr(e.index)
                if it == FLOAT:
                    raise SemanticError("array index must be an integer")
                return e.base.type
            bt = self.expr(e.base)
            it = self.expr(e.index)
            if it == FLOAT:
                raise SemanticError("array index must be an integer")
            return bt
        if isinstance(e, Call):
            return self.call(e)
        raise SemanticError(f"unsupported expression {type(e).__name__}")

    def name(self, e: Name) -> str:
        local = self.scope.lookup(e.id)
        if local is not None:
            e.id = local
            return self.info.symbols[local].type
        if e.id in STATE_NAMES:
            self.info.touches.add(e.id)
            self._sym(e.id, FLOAT, "state", uniform=False)
            return FLOAT
        if e.id == "VVAR":
            self._sym("VVAR", FLOAT, "weight")
            return FLOAT
        if e.id in self.an.variables:          # bare parameter name (some sources omit VAR())
            return self._param(e.id)
        if e.id in self.an.const_globals:
            t, dims, value = self.an.const_globals[e.id]
            s = self._sym(e.id, t, "const")
            s.dims, s.value = list(dims), value
            return t
        if e.id in self.an.derived:
            self._sym(e.id, self.an.derived[e.id], "scratch" if (e.id in self.an.calc_scratch and not self.is_prepare) else "derived")
            return self.an.derived[e.id]
        if e.id in self.an.scratch:
            self._sym(e.id, self.an.scratch[e.id], "scratch")
            return self.an.scratch[e.id]
        if e.id in CONSTANTS:
            s = self._sym(e.id, CONSTANTS[e.id][1], "const")
            s.value = CONSTANTS[e.id][0]
            return s.type
        raise SemanticError(f"unknown name {e.id!r}")

    def _param(self, vname: str) -> str:
        var = self.an.variables[vname]
        if vname in self.an.derived:
            self._sym(vname, var.type, "scratch" if (vname in self.an.calc_scratch and not self.is_prepare) else "derived")
        else:
            self._sym(vname, var.type, "param")
        return var.type

    def _sym(self, name: str, typ: str, kind: str, uniform: bool = True) -> Symbol:
        s = self.info.symbols.get(name)
        if s is None:
            dims = self.an.scratch_dims.get(name, []) if kind == "scratch" else self.an.derived_dims.get(name, []) if kind == "derived" else []
            s = Symbol(name, typ, list(dims), kind, uniform)
            self.info.symbols[name] = s
        return s

    def _record_write(self, target: Expr) -> None:
        base = target
        while isinstance(base, Index):
            base = base.base
        if isinstance(base, Name) and base.id in STATE_NAMES:
            self.info.writes.add(base.id)
        if isinstance(base, Call) and base.func == "VAR":
            vname = base.args[0].id
            if vname in self.an.variables and vname not in self.an.derived and not self.is_prepare:
                self.an.warnings.append(f"calc modifies parameter {vname}; treated as scratch")
                self.an.scratch[vname] = self.an.variables[vname].type
                self.info.symbols[vname].kind = "scratch"

    def call(self, e: Call) -> str:
        if e.func in FLOAT_SUFFIX_ALIASES:
            e.func = FLOAT_SUFFIX_ALIASES[e.func]
        if e.func == "VAR":
            if len(e.args) != 1 or not isinstance(e.args[0], Name):
                raise SemanticError("VAR() takes one variable name")
            vname = e.args[0].id
            if vname in self.an.variables:
                return self._param(vname)
            if vname in self.an.derived:
                self._sym(vname, self.an.derived[vname], "scratch" if (vname in self.an.calc_scratch and not self.is_prepare) else "derived")
                return self.an.derived[vname]
            if vname in self.an.scratch:
                self._sym(vname, self.an.scratch[vname], "scratch")
                return self.an.scratch[vname]
            raise SemanticError(f"VAR({vname}): not a declared variable or struct member")
        if e.func == "TM":
            if len(e.args) != 1 or not isinstance(e.args[0], Name) or e.args[0].id not in AFFINE_NAMES:
                raise SemanticError("TM() takes one of a..f")
            self._sym("TM_" + e.args[0].id, FLOAT, "affine")
            return FLOAT
        if e.func in OUT_FUNCTIONS:
            n_in, _ = OUT_FUNCTIONS[e.func]
            if len(e.args) != n_in + 2:
                raise SemanticError(f"{e.func} takes {n_in + 2} arguments")
            for a in e.args[:n_in]:
                self.expr(a)
            for a in e.args[n_in:]:
                target = a.operand if isinstance(a, AddressOf) else a
                self.expr(target)
                self._record_write(target)
            return VOID
        if e.func in self.an.helper_defs:
            fn = self.an.helper_defs[e.func]
            e.args = [a for a, p in zip(e.args, fn.params) if p.name != "vp"] if len(e.args) == len(fn.params) else e.args
            if len(e.args) != len([p for p in fn.params if p.name != "vp"]):
                raise SemanticError(f"{e.func}() called with the wrong number of arguments")
            for a, p in zip(e.args, [p for p in fn.params if p.name != "vp"]):
                target = a.operand if isinstance(a, AddressOf) else a
                self.expr(target)
                if p.pointer:
                    self._record_write(target)
            self.info.calls.add(e.func)
            return fn.ret_type
        if e.func in ("random01", "rand"):
            self.info.uses_random = True
            if e.args:
                raise SemanticError(f"{e.func}() takes no arguments")
            return MATH_FUNCTIONS[e.func][1]
        if e.func == "Complex":
            if len(e.args) not in (1, 2):
                raise SemanticError("Complex() takes one or two arguments")
            for a in e.args:
                self.expr(a)
            return COMPLEX
        if e.func in ("creal", "cimag", "norm", "arg") and len(e.args) == 1:
            if self.expr(e.args[0]) != COMPLEX:
                raise SemanticError(f"{e.func}() needs a complex argument")
            return FLOAT
        if e.func in MATH_FUNCTIONS:
            counts, ret = MATH_FUNCTIONS[e.func]
            if len(e.args) not in counts:
                raise SemanticError(f"{e.func}() takes {counts} arguments")
            types = [self.expr(a) for a in e.args]
            if e.func == "abs" and types[0] == COMPLEX:
                return FLOAT
            if COMPLEX in types:
                if e.func in COMPLEX_FUNCTIONS:
                    return COMPLEX
                raise SemanticError(f"{e.func}() is not defined for complex values")
            if ret == "same":
                return types[0] if types[0] != BOOL else INT
            if ret == "join":
                return FLOAT if FLOAT in types else INT
            return ret
        if e.func in ("srand", "time", "Randomize"):
            return INT
        raise SemanticError(f"unknown function {e.func}()")


def _close_calls(info: FunctionInfo, helpers: dict[str, FunctionInfo]) -> None:
    """Transitive closure of helper calls; propagates random use and context needs."""
    seen: set[str] = set()
    todo = list(info.calls)
    info.needs |= info.uses_context()
    while todo:
        n = todo.pop()
        if n in seen or n not in helpers:
            continue
        seen.add(n)
        info.uses_random |= helpers[n].uses_random
        info.needs |= helpers[n].uses_context()
        info.touches |= helpers[n].touches
        info.writes |= helpers[n].writes
        todo.extend(helpers[n].calls)
    info.calls = seen


def _order_helpers(helpers: dict[str, FunctionInfo]) -> dict[str, FunctionInfo]:
    ordered: dict[str, FunctionInfo] = {}

    def visit(n: str, stack: tuple[str, ...] = ()):
        if n in ordered:
            return
        if n in stack:
            raise SemanticError("recursive helper functions are not supported")
        for m in sorted(helpers[n].calls):
            if m in helpers:
                visit(m, stack + (n,))
        ordered[n] = helpers[n]
    for n in helpers:
        visit(n)
    return ordered


# --- helper inlining (numpy backend) -----------------------------------------------------
class Inliner:
    """Lowers a function for a backend: hoists assignments nested in expressions and, with
    `inline_helpers`, replaces calls to helper functions by their bodies (arguments bound to
    fresh locals)."""

    def __init__(self, helpers: dict[str, FuncDef], inline_helpers: bool = True):
        self.helpers = helpers
        self.inline_helpers = inline_helpers
        self.counter = 0
        self.depth = 0
        self.post: list[Stmt] = []

    def inline(self, fn: FuncDef) -> FuncDef:
        fn = clone(fn)
        fn.body = self.block(fn.body)
        return fn

    def block(self, block: Block) -> Block:
        out: list[Stmt] = []
        for s in block.body:
            out.extend(self.stmt(s))
        return Block(out)

    def stmt(self, s: Stmt) -> list[Stmt]:
        pre: list[Stmt] = []
        self.post: list[Stmt] = []
        if isinstance(s, Block):
            return [self.block(s)]
        if isinstance(s, InlineBody):
            s.body = self.block(s.body)
            return [s]
        if isinstance(s, Decl):
            for d in s.declarators:
                if d.init is not None and not isinstance(d.init, list):
                    d.init = self.expr(d.init, pre)
            return pre + [s] + self.post
        if isinstance(s, ExprStmt):
            if isinstance(s.expr, (Assign, IncDec)):
                s.expr = self.expr(s.expr, pre, top=True)
            else:
                s.expr = self.expr(s.expr, pre)
            return pre + [s] + self.post
        if isinstance(s, If):
            s.cond = self.expr(s.cond, pre)
            s.then = self.block(_as_block(s.then))
            s.other = self.block(_as_block(s.other)) if s.other else None
            return pre + [s]
        if isinstance(s, While):
            cond_pre: list[Stmt] = []
            cond = self.expr(s.cond, cond_pre)
            body = self.block(_as_block(s.body))
            if cond_pre:
                # while (f(x)) body  →  while (1) { pre; if (!cond) break; body }
                # do body while (f(x))  →  while (1) { body; pre; if (!cond) break; }
                s.cond = Num(1, True)
                test = cond_pre + [If(Unary("!", cond), Block([Break()]), None)]
                s.body = Block(body.body + test if s.do_while else test + body.body)
                s.do_while = False
            else:
                s.cond, s.body = cond, body
            return pre + [s]
        if isinstance(s, For):
            init = self.stmt(s.init) if s.init else []
            cond_pre: list[Stmt] = []
            cond = self.expr(s.cond, cond_pre) if s.cond else None
            step_pre: list[Stmt] = []
            step = Block(sum((self.stmt(x) for x in s.step.body), [])) if s.step else None
            if cond_pre or step_pre:
                raise SemanticError("helper calls in for-loop control are not supported")
            s.init = Block(init) if init else None
            s.cond, s.step = cond, step
            s.body = self.block(_as_block(s.body))
            return pre + [s]
        if isinstance(s, Switch):
            s.subject = self.expr(s.subject, pre)
            for c in s.cases:
                c.body = self.block(Block(c.body)).body
            return pre + [s]
        if isinstance(s, Return):
            if s.value is not None:
                s.value = self.expr(s.value, pre)
            return pre + [s]
        return [s]

    def expr(self, e: Expr, pre: list[Stmt], top: bool = False) -> Expr:
        if isinstance(e, Call) and e.func == "modf" and len(e.args) == 2:
            # frac = modf(x, &ip)  →  tmp = x; ip = trunc(tmp); frac = tmp - trunc(tmp)
            self.counter += 1
            tmp = f"modf{self.counter}_"
            pre.append(Decl(FLOAT, [Declarator(tmp, [], self.expr(e.args[0], pre))]))
            target = e.args[1].operand if isinstance(e.args[1], AddressOf) else e.args[1]
            pre.append(ExprStmt(Assign(target, "=", Call("trunc", [Name(tmp)]))))
            return Binary("-", Name(tmp), Call("trunc", [Name(tmp)]))
        if isinstance(e, Call):
            if e.func in OUT_FUNCTIONS or e.func in ("VAR", "TM"):
                if e.func in OUT_FUNCTIONS:
                    e.args = [self.expr(a, pre) if not isinstance(a, AddressOf) else a for a in e.args]
                return e
            e.args = [self.expr(a, pre) for a in e.args]
            if e.func in self.helpers:
                fn = self.helpers[e.func]
                if len(e.args) == len(fn.params):
                    e.args = [a for a, p in zip(e.args, fn.params) if p.name != "vp"]
                if self.inline_helpers:
                    return self.inline_call(e, pre)
                self.copy_rows(e, fn, pre)
            return e
        if isinstance(e, Assign):
            e.value = self.expr(e.value, pre)
            e.target = self.expr(e.target, pre)
            if top:
                return e
            pre.append(ExprStmt(e))               # a = b = c  →  b = c; a = b
            return clone(e.target)
        if isinstance(e, IncDec):
            e.target = self.expr(e.target, pre)
            if top:
                return e
            if e.prefix:
                pre.append(ExprStmt(e))
                return clone(e.target)
            self.counter += 1
            tmp = f"pf{self.counter}_"
            pre.append(Decl(FLOAT, [Declarator(tmp, [], clone(e.target))]))
            pre.append(ExprStmt(e))
            return Name(tmp)
        for f in ("operand", "left", "right", "cond", "then", "other", "base", "index"):
            if hasattr(e, f) and isinstance(getattr(e, f), Expr):
                setattr(e, f, self.expr(getattr(e, f), pre))
        return e

    def copy_rows(self, call: Call, fn: FuncDef, pre: list[Stmt]) -> None:
        """A row of a larger array passed to an array parameter (`f(P[i])`) goes through a temporary
        array: copied in before the call and back afterwards (GLSL cannot pass sub-arrays)."""
        params = [p for p in fn.params if p.name != "vp"]
        for k, (arg, p) in enumerate(zip(call.args, params)):
            if not p.dims or not isinstance(arg, Index):
                continue
            size = 1
            for d in p.dims:
                size *= d
            self.counter += 1
            tmp = f"row{self.counter}_"
            pre.append(Decl(p.type, [Declarator(tmp, [size], None)]))
            for i in range(size):
                pre.append(ExprStmt(Assign(Index(Name(tmp), Num(i, True)), "=", Index(clone(arg), Num(i, True)))))
                self.post.append(ExprStmt(Assign(Index(clone(arg), Num(i, True)), "=", Index(Name(tmp), Num(i, True)))))
            call.args[k] = Name(tmp)

    def inline_call(self, call: Call, pre: list[Stmt]) -> Expr:
        fn = self.helpers[call.func]
        self.depth += 1
        if self.depth > 16:
            raise SemanticError("helper inlining too deep (recursion?)")
        self.counter += 1
        tag = f"h{self.counter}_"
        body = clone(fn.body)
        params = [p for p in fn.params if p.name != "vp"]
        rename: dict[str, Expr] = {}
        setup: list[Stmt] = []
        for p, arg in zip(params, call.args):
            if p.pointer:
                target = arg.operand if isinstance(arg, AddressOf) else arg
                rename[p.name] = target                 # alias: the helper writes straight into the caller's variable
            else:
                setup.append(Decl(p.type, [Declarator(tag + p.name, [], arg)]))
                rename[p.name] = Name(tag + p.name)
        ret_name = tag + "ret"
        has_value = fn.ret_type != VOID
        _Renamer(tag, rename).block(body)
        body = _ReturnRewriter(ret_name if has_value else None).block(body)
        block = Block(setup + ([Decl(fn.ret_type, [Declarator(ret_name, [], None)])] if has_value else []) + [InlineBody(body)])
        pre.extend(self.block(block).body)
        self.depth -= 1
        return Name(ret_name) if has_value else Num(0, True)


@dataclass
class InlineBody(Stmt):
    """A helper body inlined into its caller: `Return` inside means 'leave this block'."""
    body: Block


class _Renamer:
    """Renames locals of an inlined helper and substitutes parameter references."""

    def __init__(self, tag: str, mapping: dict[str, Expr]):
        self.tag = tag
        self.mapping = dict(mapping)

    def block(self, block: Block) -> None:
        for s in block.body:
            self.stmt(s)

    def stmt(self, s: Stmt) -> None:
        if isinstance(s, Decl):
            for d in s.declarators:
                if d.init is not None:
                    d.init = self.init(d.init)
                new = self.tag + d.name
                self.mapping[d.name] = Name(new)
                d.name = new
        elif isinstance(s, Block):
            self.block(s)
        elif isinstance(s, InlineBody):
            self.block(s.body)
        else:
            for f in s.__dataclass_fields__:
                v = getattr(s, f)
                if isinstance(v, Expr):
                    setattr(s, f, self.expr(v))
                elif isinstance(v, Stmt):
                    self.stmt(v)
                elif isinstance(v, list):
                    for item in v:
                        if isinstance(item, Stmt):
                            self.stmt(item)
                        elif isinstance(item, Case):
                            item.values = [self.expr(x) for x in item.values] if item.values else None
                            for st in item.body:
                                self.stmt(st)

    def init(self, init):
        if isinstance(init, list):
            return [self.init(i) for i in init]
        return self.expr(init)

    def expr(self, e: Expr) -> Expr:
        if isinstance(e, Name):
            return clone(self.mapping[e.id]) if e.id in self.mapping else e
        if isinstance(e, Call):
            if e.func in ("VAR", "TM"):
                return e
            e.args = [self.expr(a) for a in e.args]
            return e
        for f in ("operand", "left", "right", "cond", "then", "other", "value", "base", "index", "target"):
            if hasattr(e, f) and isinstance(getattr(e, f), Expr):
                setattr(e, f, self.expr(getattr(e, f)))
        return e


class _ReturnRewriter:
    """`return x;` → `ret = x; return;` so the inliner can treat it as a block exit."""

    def __init__(self, ret_name: str | None):
        self.ret_name = ret_name

    def block(self, block: Block) -> Block:
        out: list[Stmt] = []
        for s in block.body:
            out.extend(self.stmt(s))
        return Block(out)

    def stmt(self, s: Stmt) -> list[Stmt]:
        if isinstance(s, Return):
            if s.value is not None and self.ret_name:
                return [ExprStmt(Assign(Name(self.ret_name), "=", s.value)), Return(None)]
            return [Return(None)]
        if isinstance(s, Block):
            return [self.block(s)]
        if isinstance(s, If):
            s.then = self.block(_as_block(s.then))
            s.other = self.block(_as_block(s.other)) if s.other else None
        elif isinstance(s, (While, For)):
            s.body = self.block(_as_block(s.body))
        elif isinstance(s, Switch):
            for c in s.cases:
                c.body = self.block(Block(c.body)).body
        return [s]


def _as_block(s: Stmt | None) -> Block:
    return s if isinstance(s, Block) else Block([] if s is None else [s])


# --- uniformity (numpy backend) ------------------------------------------------------------
class _Uniformity:
    """Flow-insensitive analysis: a variable is uniform if every assignment to it is uniform and
    happens under uniform control flow. Iterates to a fixed point, then marks every expression."""

    def __init__(self, info: FunctionInfo, is_prepare: bool):
        self.info = info
        self.is_prepare = is_prepare
        self.nonuniform: set[str] = {n for n, s in info.symbols.items() if s.kind in ("state", "helper_param")}
        self.changed = True

    def run(self, fn: FuncDef) -> None:
        while self.changed:
            self.changed = False
            self.block(fn.body, uniform_ctx=True)
        for s in self.info.symbols.values():
            s.uniform = s.name not in self.nonuniform
        self.block(fn.body, uniform_ctx=True)   # final pass marks expressions with the settled flags

    def mark(self, name: str) -> None:
        if name not in self.nonuniform:
            self.nonuniform.add(name)
            self.changed = True

    def block(self, block: Block, uniform_ctx: bool, in_inline: bool = False) -> None:
        ctx = uniform_ctx
        for s in block.body:
            self.stmt(s, ctx)
            if ctx and _escaping_jump(s, self, in_inline):
                ctx = False   # lanes that returned / broke out are masked from here on
        block.uniform_exit = ctx   # noqa: attribute used by the backend

    def stmt(self, s: Stmt, ctx: bool) -> None:
        if isinstance(s, Block):
            self.block(s, ctx)
        elif isinstance(s, InlineBody):
            self.block(s.body, ctx, in_inline=True)
        elif isinstance(s, Decl):
            for d in s.declarators:
                if d.init is not None:
                    u = self.init(d.init)
                    if not u:
                        self.mark(d.name)
                elif not ctx:
                    pass   # declared inside divergent control flow: assignments decide
        elif isinstance(s, ExprStmt):
            self.expr(s.expr, ctx)
        elif isinstance(s, If):
            u = self.expr(s.cond, ctx) and ctx
            self.stmt(s.then, u)
            if s.other:
                self.stmt(s.other, u)
        elif isinstance(s, While):
            u = self.expr(s.cond, ctx) and ctx and not _has_divergent_jump(s.body, self)
            self.stmt(s.body, u)
            self.expr(s.cond, ctx)
        elif isinstance(s, For):
            if s.init:
                self.stmt(s.init, ctx)
            u = ctx and (s.cond is None or self.expr(s.cond, ctx)) and not _has_divergent_jump(s.body, self)
            self.stmt(s.body, u)
            if s.step:
                self.stmt(s.step, u)
            if s.cond:
                self.expr(s.cond, ctx)
        elif isinstance(s, Switch):
            u = self.expr(s.subject, ctx) and ctx
            for c in s.cases:
                for v in c.values or []:
                    self.expr(v, ctx)
                for st in c.body:
                    self.stmt(st, u)
        elif isinstance(s, Return):
            if s.value is not None:
                self.expr(s.value, ctx)
        s.uniform_ctx = ctx   # noqa: attribute used by the backend

    def init(self, init) -> bool:
        if isinstance(init, list):
            return all(self.init(i) for i in init)
        return self.expr(init, True)

    def expr(self, e: Expr, ctx: bool) -> bool:
        u = self._expr(e, ctx)
        e.uniform = u
        return u

    def _expr(self, e: Expr, ctx: bool) -> bool:
        if isinstance(e, (Num, Str)):
            return True
        if isinstance(e, Name):
            return e.id not in self.nonuniform
        if isinstance(e, (Unary, Cast, AddressOf)):
            return self.expr(e.operand, ctx)
        if isinstance(e, Binary):
            a = self.expr(e.left, ctx)
            b = self.expr(e.right, ctx)
            return a and b
        if isinstance(e, Ternary):
            c = self.expr(e.cond, ctx)
            a = self.expr(e.then, ctx)
            b = self.expr(e.other, ctx)
            return c and a and b
        if isinstance(e, Assign):
            v = self.expr(e.value, ctx)
            t = self.expr(e.target, ctx)
            name = _lvalue_name(e.target)
            if not (v and ctx and (t or e.op == "=" and not isinstance(e.target, Index))):
                self.mark(name)
            return name not in self.nonuniform
        if isinstance(e, IncDec):
            t = self.expr(e.target, ctx)
            name = _lvalue_name(e.target)
            if not (ctx and t):
                self.mark(name)
            return name not in self.nonuniform
        if isinstance(e, Index):
            b = self.expr(e.base, ctx)
            i = self.expr(e.index, ctx)
            return b and i
        if isinstance(e, Call):
            if e.func in ("random01", "rand"):
                return self.is_prepare
            if e.func in ("VAR", "TM"):
                return True
            if e.func in OUT_FUNCTIONS:
                n_in = OUT_FUNCTIONS[e.func][0]
                u = all(self.expr(a, ctx) for a in e.args[:n_in])
                for a in e.args[n_in:]:
                    target = a.operand if isinstance(a, AddressOf) else a
                    t = self.expr(target, ctx)
                    if not (u and ctx and t):
                        self.mark(_lvalue_name(target))
                return True
            return all([self.expr(a, ctx) for a in e.args])
        raise SemanticError(f"unsupported expression {type(e).__name__}")


def _has_divergent_jump(body: Block, an: _Uniformity) -> bool:
    """True if a break/continue/return inside `body` sits under a non-uniform condition
    (returns inside an inlined helper body only affect that body and are not counted)."""
    return _jump_search(body, an, True, any_return=False)


def _escaping_jump(stmt: Stmt, an: _Uniformity, in_inline: bool) -> bool:
    """True if `stmt` may leave some lanes behind for the statements that follow it: a jump under a
    non-uniform condition, or — inside an inlined helper body — any return, which masks the rest
    of that body. Jumps inside nested inlined bodies never escape them."""
    return _jump_search(stmt, an, True, any_return=in_inline)


def _jump_search(node, an: _Uniformity, ctx: bool, any_return: bool, in_loop: bool = False) -> bool:
    def visit(node, ctx: bool, in_loop: bool) -> bool:
        if isinstance(node, Return):
            return (not ctx) or any_return
        if isinstance(node, (Break, Continue)):
            return (not ctx) and not in_loop
        if isinstance(node, If):
            u = ctx and an.expr(node.cond, ctx)
            return visit(node.then, u, in_loop) or (node.other is not None and visit(node.other, u, in_loop))
        if isinstance(node, (While, For)):
            u = ctx and (node.cond is None or an.expr(node.cond, ctx))
            return visit(node.body, u, True)
        if isinstance(node, Switch):
            u = ctx and an.expr(node.subject, ctx)
            return any(visit(st, u, in_loop) for c in node.cases for st in c.body)
        if isinstance(node, Block):
            return any(visit(s, ctx, in_loop) for s in node.body)
        if isinstance(node, InlineBody):
            return False   # its returns end the inlined body only
        return False
    return visit(node, ctx, in_loop)


def analyze(module: Module) -> PluginSpec:
    """Run the semantic pass on a parsed module."""
    return Analyzer(module).run()
