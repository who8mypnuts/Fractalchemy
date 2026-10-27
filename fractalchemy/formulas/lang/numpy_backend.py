"""numpy backend: turns an analysed formula into vectorised Python.

Every point of a batch is one lane of the numpy arrays. Control flow that depends on the
point (`if (FTx > 0)`) is vectorised with masks: both branches run, and assignments inside
them become `where(mask, new, old)`. Control flow that depends only on per-transform
constants stays real Python, and such values stay scalars (see `semantic._Uniformity`).
Loops whose condition varies per point iterate while any lane is active; `break`,
`continue` and early `return` remove lanes from the active mask.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np

from . import runtime as _rt
from .builtins import OUT_FUNCTIONS
from .nodes import (
    BOOL, COMPLEX, FLOAT, INT, AddressOf, Assign, Binary, Block, Break, Call, Cast, Continue, Decl, Expr, ExprStmt, For, If,
    IncDec, Index, Name, Num, Return, Stmt, Switch, Ternary, Unary, While,
)
from .semantic import FunctionInfo, InlineBody, PluginSpec, SemanticError, _lvalue_name

STATE = ("FTx", "FTy", "FTz", "FPx", "FPy", "FPz", "TC")
AFFINE = ("TM_a", "TM_b", "TM_c", "TM_d", "TM_e", "TM_f")


class BackendError(SemanticError):
    """The formula uses something the numpy backend cannot vectorise."""


@dataclass
class _Loop:
    brk: str
    cnt: str
    uniform: bool


@dataclass
class _Ctx:
    """Emission context: the active mask and the jump bookkeeping in scope."""
    mask: str | None
    ret: str | None                      # variable collecting lanes that returned (None = real `return`)
    loops: list[_Loop] = field(default_factory=list)
    inline: list[str] = field(default_factory=list)   # `ret` vars of enclosing InlineBody blocks


class NumpyEmitter:
    """Emits one function (calc or prepare) as Python source."""

    def __init__(self, spec: PluginSpec, info: FunctionInfo, scalar: bool):
        self.spec = spec
        self.info = info
        self.scalar = scalar
        self.lines: list[str] = []
        self.counter = 0
        self.indent = 1

    # --- helpers ----------------------------------------------------------------------------
    def fresh(self, base: str) -> str:
        self.counter += 1
        return f"_{base}{self.counter}"

    def out(self, line: str) -> None:
        self.lines.append("    " * self.indent + line)

    def name(self, n: str) -> str:
        sym = self.info.symbols.get(n)
        if sym is None:
            return "L_" + n
        if sym.kind in ("state", "weight", "affine"):
            return n
        if sym.kind in ("param", "derived", "scratch"):
            return "V_" + n
        if sym.kind == "const":
            if isinstance(sym.value, (list, tuple)):
                return "G_" + n
            return _literal(sym.value)
        return "L_" + n

    # --- function -----------------------------------------------------------------------------
    def function(self, fname: str, outputs: list[str]) -> str:
        fn = self.info.node
        self.out = lambda line: self.lines.append("    " * self.indent + line)   # noqa: E731
        self.lines.append(f"def {fname}(FTx, FTy, FTz, FPx, FPy, FPz, TC, VVAR, TM_a, TM_b, TM_c, TM_d, TM_e, TM_f, _P, _rng):")
        if self.scalar:
            self.out("_n = None")
            self.out("def _rnd(): return _rng.random()")
            self.out("def _rand(): return int(_rng.integers(0, 32768))")
        else:
            self.out("_n = np.shape(FTx)[0]")
            self.out("def _rnd(): return _rng.random(_n)")
            self.out("def _rand(): return _rng.integers(0, 32768, _n)")
        # per-transform constants become numpy scalars: x / 0 then yields inf like C, not ZeroDivisionError
        self.out("VVAR = np.float64(VVAR)")
        self.out("TM_a, TM_b, TM_c, TM_d, TM_e, TM_f = (np.float64(v) for v in (TM_a, TM_b, TM_c, TM_d, TM_e, TM_f))")
        for sym in self.info.symbols.values():
            conv = "np.float64" if sym.type == FLOAT else "int" if sym.type == INT else "bool"
            if sym.kind == "param":
                self.out(f"V_{sym.name} = {conv}(_P[{sym.name!r}])")
            elif sym.kind == "derived" and sym.dims:
                if self.scalar:   # prepare fills it
                    self.out(f"V_{sym.name} = {_zeros(sym.dims, sym.type)}")
                else:
                    dtype = "np.int32" if sym.type == INT else "np.float64"
                    size = 1
                    for d in sym.dims:
                        size *= d
                    self.out(f"V_{sym.name} = np.asarray(_P.get({sym.name!r}, [0] * {size}), dtype={dtype}).reshape({tuple(sym.dims)})")
            elif sym.kind == "derived":
                self.out(f"V_{sym.name} = {conv}(_P.get({sym.name!r}, {_zero(sym.type)}))")
            elif sym.kind == "scratch":
                if sym.dims:
                    size = 1
                    for d in sym.dims:
                        size *= d
                    self.out(f"V_{sym.name} = _rt.nested([{conv}(v) for v in _P.get({sym.name!r}, [0] * {size})], {tuple(sym.dims)})")
                else:
                    self.out(f"V_{sym.name} = {conv}(_P.get({sym.name!r}, {_zero(sym.type)}))")
            elif sym.kind == "const" and isinstance(sym.value, (list, tuple)):
                self.out(f"G_{sym.name} = _G[{sym.name!r}]")
        for sym in self.info.symbols.values():
            if sym.kind in ("local",) and not sym.dims:
                self.out(f"L_{sym.name} = {_zero(sym.type)}")
        self.out("_ret = np.False_")
        ctx = _Ctx(mask=None, ret="_ret")
        self.block(fn.body.body, ctx)
        self.out("return " + ", ".join(outputs))
        return "\n".join(self.lines)

    # --- statements ---------------------------------------------------------------------------
    def block(self, stmts: list[Stmt], ctx: _Ctx) -> set[str]:
        """Emit statements under `ctx`; returns the kinds of divergent jumps that may have happened."""
        jumps: set[str] = set()
        for s in stmts:
            j = self.stmt(s, ctx)
            if j:
                jumps |= j
                self.refresh(ctx, j)
        return jumps

    def refresh(self, ctx: _Ctx, jumps: set[str]) -> None:
        """Exclude lanes that jumped from the block's mask."""
        terms = []
        if "ret" in jumps and ctx.ret:
            terms.append(f"~{ctx.ret}")
        if "inline" in jumps and ctx.inline:
            terms.append(f"~{ctx.inline[-1]}")
        if ("brk" in jumps or "cnt" in jumps) and ctx.loops and not ctx.loops[-1].uniform:
            if "brk" in jumps:
                terms.append(f"~{ctx.loops[-1].brk}")
            if "cnt" in jumps:
                terms.append(f"~{ctx.loops[-1].cnt}")
        if not terms:
            return
        new = self.fresh("m")   # a fresh variable: the parent context keeps its own mask untouched
        if ctx.mask is None:
            self.out(f"{new} = {' & '.join(terms)}")
        else:
            self.out(f"{new} = {ctx.mask} & {' & '.join(terms)}")
        ctx.mask = new

    def stmt(self, s: Stmt, ctx: _Ctx) -> set[str]:
        if isinstance(s, Block):
            return self.block(s.body, _Ctx(ctx.mask, ctx.ret, ctx.loops, ctx.inline))
        if isinstance(s, InlineBody):
            ret = self.fresh("ib")
            self.out(f"{ret} = np.False_")
            inner = _Ctx(ctx.mask, ctx.ret, ctx.loops, ctx.inline + [ret])
            jumps = self.block(s.body.body, inner)
            return jumps - {"inline"}
        if isinstance(s, Decl):
            for d in s.declarators:
                target = self.name(d.name)
                if d.dims:
                    self.out(f"{target} = {self.array_init(d.init, d.dims, s.type)}")
                elif d.init is not None:
                    self.out(f"{target} = {self.coerce(d.init, s.type)}")
            return set()
        if isinstance(s, ExprStmt):
            self.expr_stmt(s.expr, ctx)
            return set()
        if isinstance(s, If):
            return self.if_(s, ctx)
        if isinstance(s, While):
            return self.loop(s, ctx)
        if isinstance(s, For):
            return self.loop(s, ctx)
        if isinstance(s, Switch):
            return self.stmt(_lower_switch(s), ctx)
        if isinstance(s, Return):
            return self.return_(s, ctx)
        if isinstance(s, Break):
            if not ctx.loops:
                raise BackendError("break outside a loop")
            if ctx.loops[-1].uniform and ctx.mask is None:
                self.out("break")
                return set()
            self.out(f"{ctx.loops[-1].brk} = {ctx.loops[-1].brk} | {ctx.mask if ctx.mask else 'np.True_'}")
            return {"brk"}
        if isinstance(s, Continue):
            if not ctx.loops:
                raise BackendError("continue outside a loop")
            if ctx.loops[-1].uniform and ctx.mask is None:
                self.out("continue")
                return set()
            self.out(f"{ctx.loops[-1].cnt} = {ctx.loops[-1].cnt} | {ctx.mask if ctx.mask else 'np.True_'}")
            return {"cnt"}
        raise BackendError(f"unsupported statement {type(s).__name__}")

    def return_(self, s: Return, ctx: _Ctx) -> set[str]:
        if ctx.inline:
            self.out(f"{ctx.inline[-1]} = {ctx.inline[-1]} | {ctx.mask if ctx.mask else 'np.True_'}")
            return {"inline"}
        if ctx.mask is None and not ctx.loops:
            self.out("return " + ", ".join(self._outputs))
            return set()
        if ctx.mask is None and all(lp.uniform for lp in ctx.loops):
            self.out("return " + ", ".join(self._outputs))
            return set()
        self.out(f"{ctx.ret} = {ctx.ret} | {ctx.mask if ctx.mask else 'np.True_'}")
        return {"ret"}

    def if_(self, s: If, ctx: _Ctx) -> set[str]:
        cond = self.bool_expr(s.cond)
        if s.cond.uniform and getattr(s, "uniform_ctx", True):
            self.out(f"if {cond}:")
            self.indent += 1
            jumps = self.block(_stmts(s.then), _Ctx(ctx.mask, ctx.ret, ctx.loops, ctx.inline))
            if not _stmts(s.then):
                self.out("pass")
            self.indent -= 1
            if s.other is not None:
                self.out("else:")
                self.indent += 1
                jumps |= self.block(_stmts(s.other), _Ctx(ctx.mask, ctx.ret, ctx.loops, ctx.inline))
                if not _stmts(s.other):
                    self.out("pass")
                self.indent -= 1
            return jumps
        c = self.fresh("c")
        self.out(f"{c} = _rt.mask({cond})")
        m = self.fresh("m")
        self.out(f"{m} = {c}" if ctx.mask is None else f"{m} = {ctx.mask} & {c}")
        jumps = self.block(_stmts(s.then), _Ctx(m, ctx.ret, ctx.loops, ctx.inline))
        if s.other is not None:
            self.out(f"{m} = ~{c}" if ctx.mask is None else f"{m} = {ctx.mask} & ~{c}")
            jumps |= self.block(_stmts(s.other), _Ctx(m, ctx.ret, ctx.loops, ctx.inline))
        return jumps

    def loop(self, s: While | For, ctx: _Ctx) -> set[str]:
        uniform = getattr(s, "uniform_ctx", True) and (s.cond is None or s.cond.uniform) and ctx.mask is None \
            and not _divergent_jumps(s.body)
        if isinstance(s, For) and s.init is not None:
            self.stmt(s.init, ctx)
        if uniform:
            return self.uniform_loop(s, ctx)
        brk, cnt, m = self.fresh("brk"), self.fresh("cnt"), self.fresh("m")
        it = self.fresh("it")
        self.out(f"{brk} = np.False_")
        base = ctx.mask if ctx.mask else "np.True_"
        if isinstance(s, While) and s.do_while:
            self.out(f"{m} = {base}")
        elif s.cond is None:
            self.out(f"{m} = {base}")
        else:
            self.out(f"{m} = {base} & _rt.mask({self.bool_expr(s.cond)})" if ctx.mask else f"{m} = _rt.mask({self.bool_expr(s.cond)})")
        self.out(f"{it} = 0")
        self.out(f"while _rt.any_({m}):")
        self.indent += 1
        self.out(f"{it} += 1")
        self.out(f"if {it} > _rt.LOOP_LIMIT: break")
        self.out(f"{cnt} = np.False_")
        inner = _Ctx(m, ctx.ret, ctx.loops + [_Loop(brk, cnt, False)], ctx.inline)
        jumps = self.block(_stmts(s.body), inner)
        exclude = f"~{brk}"
        if "ret" in jumps and ctx.ret:
            exclude += f" & ~{ctx.ret}"
        self.out(f"{m} = {m} & {exclude}")
        if isinstance(s, For) and s.step is not None:
            self.block(_stmts(s.step), _Ctx(m, ctx.ret, ctx.loops, ctx.inline))
        if s.cond is not None:
            self.out(f"{m} = {m} & _rt.mask({self.bool_expr(s.cond)})")
        self.indent -= 1
        return jumps - {"brk", "cnt"}

    def uniform_loop(self, s: While | For, ctx: _Ctx) -> set[str]:
        inner = _Ctx(None, ctx.ret, ctx.loops + [_Loop("", "", True)], ctx.inline)
        if isinstance(s, For):
            first = self.fresh("first")
            self.out(f"{first} = True")
            self.out("while True:")
            self.indent += 1
            if s.step is not None:
                self.out(f"if not {first}:")
                self.indent += 1
                self.block(_stmts(s.step), inner)
                self.indent -= 1
            self.out(f"{first} = False")
            if s.cond is not None:
                self.out(f"if not ({self.bool_expr(s.cond)}): break")
            jumps = self.block(_stmts(s.body), inner)
            if not _stmts(s.body):
                self.out("pass")
            self.indent -= 1
            return jumps
        if s.do_while:
            self.out("while True:")
            self.indent += 1
            jumps = self.block(_stmts(s.body), inner)
            self.out(f"if not ({self.bool_expr(s.cond)}): break")
            self.indent -= 1
            return jumps
        self.out(f"while {self.bool_expr(s.cond)}:")
        self.indent += 1
        jumps = self.block(_stmts(s.body), inner)
        if not _stmts(s.body):
            self.out("pass")
        self.indent -= 1
        return jumps

    # --- expression statements --------------------------------------------------------------
    def expr_stmt(self, e: Expr, ctx: _Ctx) -> None:
        if isinstance(e, Assign):
            self.assign(e, ctx)
        elif isinstance(e, IncDec):
            delta = "+ 1" if e.op == "++" else "- 1"
            self.store(e.target, f"({self.expr(e.target)} {delta})", ctx, e.target.type)
        elif isinstance(e, Call) and e.func in OUT_FUNCTIONS:
            n_in, names = OUT_FUNCTIONS[e.func]
            arg = self.expr(e.args[0])
            tmp = self.fresh("t")
            self.out(f"{tmp} = {arg}")
            for fn, target in zip(names, e.args[n_in:]):
                t = target.operand if isinstance(target, AddressOf) else target
                self.store(t, f"np.{fn}({tmp})", ctx, FLOAT)
        elif isinstance(e, Call) and e.func in ("srand", "time", "Randomize"):
            pass
        elif isinstance(e, Num):
            pass   # an inlined void call leaves a placeholder literal behind
        else:
            self.out(f"_ = {self.expr(e)}")

    def assign(self, e: Assign, ctx: _Ctx) -> None:
        if e.op == "=":
            value = self.coerce(e.value, e.target.type)
        else:
            op = e.op[:-1]
            value = self.binary_source(op, self.expr(e.target), e.target.type, self.expr(e.value), e.value.type)
            value = self.coerce_source(value, _binary_type(op, e.target.type, e.value.type), e.target.type)
        self.store(e.target, value, ctx, e.target.type)

    def store(self, target: Expr, value: str, ctx: _Ctx, typ: str) -> None:
        """Masked or plain assignment to a name or array element."""
        mask = ctx.mask
        sym = self.info.symbols.get(_lvalue_name(target))
        if mask is not None and sym is not None and sym.uniform:
            raise BackendError(f"internal: uniform variable {sym.name} assigned under a mask")
        if isinstance(target, Index):
            base, indices = _flatten_index(target)
            base_src = self.expr(base)
            if all(i.uniform for i in indices):
                ref = base_src + "".join(f"[{self.int_index(i)}]" for i in indices)
                self.out(f"{ref} = {value}" if mask is None else f"{ref} = _rt.where({mask}, {value}, {ref})")
                return
            k = next(j for j, i in enumerate(indices) if not i.uniform)
            if not all(i.uniform for i in indices[k + 1:]):
                raise BackendError("only one per-point subscript is supported on local arrays")
            if k == len(indices) - 1:
                prefix = base_src + "".join(f"[{self.int_index(i)}]" for i in indices[:k])
                self.out(f"_rt.scatter({prefix}, {self.expr(indices[k])}, {value}, {mask if mask else 'None'})")
                return
            dims = sym.dims if sym is not None else []
            prefix = base_src + "".join(f"[{self.int_index(i)}]" for i in indices[:k])
            rest = "".join(f"[{self.int_index(i)}]" for i in indices[k + 1:])
            idx = self.fresh("idx")
            self.out(f"{idx} = {self.expr(indices[k])}")
            for j in range(dims[k]):
                m = f"({idx} == {j})" if mask is None else f"({mask} & ({idx} == {j}))"
                self.out(f"{prefix}[{j}]{rest} = _rt.where({m}, {value}, {prefix}[{j}]{rest})")
            return
        ref = self.expr(target) if not isinstance(target, Call) else self.name(target.args[0].id)
        self.out(f"{ref} = {value}" if mask is None else f"{ref} = _rt.where({mask}, {value}, {ref})")

    def int_index(self, e: Expr) -> str:
        src = self.expr(e)
        return src if isinstance(e, Num) else f"int({src})"

    # --- expressions --------------------------------------------------------------------------
    def coerce(self, e: Expr, to: str) -> str:
        return self.coerce_source(self.expr(e), e.type, to)

    def coerce_source(self, src: str, frm: str, to: str) -> str:
        if frm == to:
            return src
        if to == INT:
            return f"_rt.to_int({src})"
        if to == FLOAT:
            return f"_rt.to_float({src})"
        if to == BOOL:
            return f"_rt.to_bool({src})"
        if to == COMPLEX:
            return f"_rt.to_complex({src})"
        return src

    def bool_expr(self, e: Expr) -> str:
        src = self.expr(e)
        return src if e.type == BOOL else f"({src} != 0)"

    def expr(self, e: Expr) -> str:
        if isinstance(e, Num):
            return _literal(e.value if e.is_int else float(e.value))
        if isinstance(e, Name):
            return self.name(e.id)
        if isinstance(e, Unary):
            x = self.expr(e.operand)
            if e.op == "!":
                return f"np.logical_not({self.bool_expr(e.operand)})"
            if e.op == "~":
                return f"(~{self.coerce_source(x, e.operand.type, INT)})"
            if e.op == "-":
                return f"(-{self.coerce_source(x, e.operand.type, INT) if e.operand.type == BOOL else x})"
            return x
        if isinstance(e, Cast):
            return self.coerce(e.operand, e.to)
        if isinstance(e, AddressOf):
            return self.expr(e.operand)
        if isinstance(e, Binary):
            return self.binary_source(e.op, self.expr(e.left), e.left.type, self.expr(e.right), e.right.type,
                                      left_expr=e.left, right_expr=e.right)
        if isinstance(e, Ternary):
            c = self.bool_expr(e.cond)
            t = _join_type(e.then.type, e.other.type)
            a, b = self.coerce(e.then, t), self.coerce(e.other, t)
            if e.cond.uniform:
                return f"({a} if {c} else {b})"
            return f"_rt.where({c}, {a}, {b})"
        if isinstance(e, Assign):
            raise BackendError("assignment inside an expression is not supported; split it into statements")
        if isinstance(e, IncDec):
            raise BackendError("++/-- inside an expression is not supported; split it into statements")
        if isinstance(e, Index):
            base, indices = _flatten_index(e)
            base_src = self.expr(base)
            sym = self.info.symbols.get(_lvalue_name(base)) if isinstance(base, (Name, Call)) else None
            if sym is not None and (sym.kind == "const" or (sym.kind == "derived" and not self.scalar)):
                return base_src + "[" + ", ".join(self.coerce(i, INT) for i in indices) + "]"   # a numpy array
            if all(i.uniform for i in indices):
                return base_src + "".join(f"[{self.int_index(i)}]" for i in indices)
            k = next(j for j, i in enumerate(indices) if not i.uniform)
            if not all(i.uniform for i in indices[k + 1:]):
                raise BackendError("only one per-point subscript is supported on local arrays")
            dims = sym.dims if sym is not None else []
            if len(dims) <= k:
                raise BackendError("array shape unknown for per-point indexing")
            prefix = base_src + "".join(f"[{self.int_index(i)}]" for i in indices[:k])
            rest = "".join(f"[{self.int_index(i)}]" for i in indices[k + 1:])
            rows = f"[{prefix}[_j]{rest} for _j in range({dims[k]})]"
            return f"_rt.gather({rows}, {self.expr(indices[k])})"
        if isinstance(e, Call):
            return self.call(e)
        raise BackendError(f"unsupported expression {type(e).__name__}")

    def binary_source(self, op: str, a: str, at: str, b: str, bt: str, left_expr=None, right_expr=None) -> str:
        if op in ("&&", "||"):
            a = a if at == BOOL else f"({a} != 0)"
            b = b if bt == BOOL else f"({b} != 0)"
            return f"({a} {'&' if op == '&&' else '|'} {b})"
        if op in ("<", ">", "<=", ">=", "==", "!="):
            return f"({a} {op} {b})"
        if op == "/":
            if at in (INT, BOOL) and bt in (INT, BOOL):
                return f"_rt.idiv({a}, {b})"
            return f"np.divide({a}, {b})"   # x / 0 gives inf (C behaviour) even for Python scalars
        if op == "%":
            if at in (INT, BOOL) and bt in (INT, BOOL):
                return f"_rt.imod({a}, {b})"
            return f"_rt.fmod({a}, {b})"
        if op in ("&", "|", "^", "<<", ">>"):
            a = a if at == INT else f"_rt.to_int({a})"
            b = b if bt == INT else f"_rt.to_int({b})"
            return f"_rt.i32({a} {op} {b})" if op == "<<" else f"({a} {op} {b})"
        if at == BOOL:
            a = f"_rt.to_int({a})"
        if bt == BOOL:
            b = f"_rt.to_int({b})"
        if at in (INT, BOOL) and bt in (INT, BOOL) and op in ("+", "-", "*"):
            return f"_rt.i32({a} {op} {b})"   # C int arithmetic wraps at 32 bits
        return f"({a} {op} {b})"

    def call(self, e: Call) -> str:
        if e.func == "VAR":
            return self.name(e.args[0].id)
        if e.func == "TM":
            return "TM_" + e.args[0].id
        if e.func == "random01":
            return "_rnd()"
        if e.func == "rand":
            return "_rand()"
        if e.func == "Complex":
            if len(e.args) == 1:
                return f"_rt.to_complex({self.expr(e.args[0])})"
            return f"_rt.complex({self.expr(e.args[0])}, {self.expr(e.args[1])})"
        if e.func in ("creal", "cimag", "norm", "arg", "conj") or (e.func == "abs" and e.args and e.args[0].type == COMPLEX):
            fn = {"creal": "np.real", "cimag": "np.imag", "norm": "_rt.cnorm", "arg": "np.angle", "conj": "np.conj", "abs": "np.abs"}[e.func]
            return f"{fn}({self.expr(e.args[0])})"
        if e.func in ("abs", "fabs", "labs", "llabs"):
            return f"np.abs({self.expr(e.args[0])})"
        if e.func in ("min", "max", "fmin", "fmax"):
            fn = "np.minimum" if e.func in ("min", "fmin") else "np.maximum"
            return f"{fn}({self.expr(e.args[0])}, {self.expr(e.args[1])})"
        if e.func == "atan" and len(e.args) == 2:
            return f"np.arctan2({self.expr(e.args[0])}, {self.expr(e.args[1])})"
        if e.func in _rt.FUNCS:
            return f"_F[{e.func!r}]({', '.join(self.expr(a) for a in e.args)})"
        raise BackendError(f"unknown function {e.func}()")

    def array_init(self, init, dims: list[int], typ: str) -> str:
        if init is None:
            return _zeros(dims, typ)
        if not isinstance(init, list):
            raise BackendError("array needs a brace initialiser")
        if len(dims) == 1:
            items = [self.coerce(i, typ) for i in init] + [_zero(typ)] * (dims[0] - len(init))
            return "[" + ", ".join(items) + "]"
        items = [self.array_init(i, dims[1:], typ) for i in init]
        items += [_zeros(dims[1:], typ)] * (dims[0] - len(items))
        return "[" + ", ".join(items) + "]"


def _stmts(s: Stmt | None) -> list[Stmt]:
    if s is None:
        return []
    return s.body if isinstance(s, Block) else [s]


def _zero(typ: str) -> str:
    return {INT: "0", BOOL: "False", COMPLEX: "0j"}.get(typ, "0.0")


def _zeros(dims: list[int], typ: str) -> str:
    if len(dims) == 1:
        return f"[{_zero(typ)}] * {dims[0]}"
    return f"[{_zeros(dims[1:], typ)} for _ in range({dims[0]})]"


def _literal(v) -> str:
    if isinstance(v, bool):
        return "True" if v else "False"
    if isinstance(v, (int, np.integer)):
        return str(int(v))
    if isinstance(v, str):
        return repr(v)
    f = float(v)
    if f != f:
        return "float('nan')"
    if f in (float("inf"), float("-inf")):
        return f"float('{'inf' if f > 0 else '-inf'}')"
    return repr(f)


def _binary_type(op: str, a: str, b: str) -> str:
    if op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
        return BOOL
    if op in ("&", "|", "^", "<<", ">>"):
        return INT
    return COMPLEX if COMPLEX in (a, b) else FLOAT if FLOAT in (a, b) else INT


def _join_type(a: str, b: str) -> str:
    return COMPLEX if COMPLEX in (a, b) else FLOAT if FLOAT in (a, b) else INT if INT in (a, b) else BOOL


def _flatten_index(e: Index) -> tuple[Expr, list[Expr]]:
    indices: list[Expr] = []
    node: Expr = e
    while isinstance(node, Index):
        indices.append(node.index)
        node = node.base
    return node, list(reversed(indices))


def _divergent_jumps(body: Stmt) -> bool:
    """A jump under a per-point condition that escapes `body` (nested loops keep their own breaks;
    returns inside an inlined helper body end that body only)."""
    def visit(node, ctx: bool, in_loop: bool) -> bool:
        if isinstance(node, Return):
            return not ctx
        if isinstance(node, (Break, Continue)):
            return (not ctx) and not in_loop
        if isinstance(node, If):
            u = ctx and node.cond.uniform
            return visit(node.then, u, in_loop) or (node.other is not None and visit(node.other, u, in_loop))
        if isinstance(node, (While, For)):
            u = ctx and (node.cond is None or node.cond.uniform)
            return visit(node.body, u, True)
        if isinstance(node, Switch):
            u = ctx and node.subject.uniform
            return any(visit(st, u, in_loop) for c in node.cases for st in c.body)
        if isinstance(node, Block):
            return any(visit(s, ctx, in_loop) for s in node.body)
        if isinstance(node, InlineBody):
            return False
        return False
    return visit(body, True, False)


def _lower_switch(s: Switch) -> Stmt:
    """switch → if / else-if chain (fall-through concatenates the following case bodies)."""
    cases = s.cases
    default_body: list[Stmt] | None = None
    chain: list[tuple[list[Expr], list[Stmt]]] = []
    for i, c in enumerate(cases):
        body: list[Stmt] = []
        for c2 in cases[i:]:
            stripped, broke = _strip_break(c2.body)
            body.extend(stripped)
            if broke:
                break
        if c.values is None:
            default_body = body
        else:
            chain.append((c.values, body))
    result: Stmt | None = Block(default_body) if default_body is not None else None
    for values, body in reversed(chain):
        cond: Expr | None = None
        for v in values:
            test = Binary("==", s.subject, v)
            test.type = BOOL
            test.uniform = s.subject.uniform and v.uniform
            cond = test if cond is None else _or(cond, test)
        node = If(cond, Block(body), result)
        node.uniform_ctx = getattr(s, "uniform_ctx", True)
        result = node
    return result if result is not None else Block([])


def _or(a: Expr, b: Expr) -> Expr:
    e = Binary("||", a, b)
    e.type = BOOL
    e.uniform = a.uniform and b.uniform
    return e


def _strip_break(body: list[Stmt]) -> tuple[list[Stmt], bool]:
    """Remove a trailing `break`; returns (statements, ended with break)."""
    if body and isinstance(body[-1], Break):
        return body[:-1], True
    if body and isinstance(body[-1], Return):
        return body, True
    return body, False


def emit_module(spec: PluginSpec) -> str:
    """Python source defining `calc` (and `prepare` if the formula has one)."""
    calc = NumpyEmitter(spec, spec.calc_inlined, scalar=False)
    calc._outputs = list(STATE)
    parts = ["import numpy as np", calc.function("calc", list(STATE))]
    if spec.prepare_inlined is not None:
        prep = NumpyEmitter(spec, spec.prepare_inlined, scalar=True)
        outputs = ["{" + ", ".join(f"{n!r}: V_{n}" for n in spec.derived) + "}"]
        prep._outputs = outputs
        parts.append(prep.function("prepare", outputs))
    return "\n\n".join(parts)


def build(spec: PluginSpec):
    """Compile the numpy code; returns (calc, prepare_or_None, source)."""
    source = emit_module(spec)
    namespace = {
        "np": np, "_rt": _rt, "_F": _rt.FUNCS,
        "_G": {n: (np.asarray(v) if d else v) for n, t, d, v in spec.const_globals},
    }
    try:
        exec(compile(source, f"<formula {spec.name}>", "exec"), namespace)   # noqa: S102 - our own generated code
    except SyntaxError as exc:
        raise BackendError(f"generated code failed to compile: {exc}\n{source}") from exc
    return namespace["calc"], namespace.get("prepare"), source
