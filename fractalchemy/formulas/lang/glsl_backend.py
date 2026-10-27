"""GLSL backend: emits the analysed formula as a GLSL function body (plus helper functions).

The emitted code follows the preview engine's conventions (see `render/codegen.py`):
`t` / `tz` hold the input point, `v` / `vz` the accumulator, `col` the colour, `w` the
weight, `c00..c21` the affine coefficients, `s` the RNG state, and parameters appear as
`P_<name>` placeholders that the code generator binds to parameter-texture reads.
Helper functions and lookup tables are prefixed with `@`, which the code generator
replaces by a per-instance prefix so several transforms can use the same formula.
"""

from __future__ import annotations

from .builtins import OUT_FUNCTIONS
from .nodes import (
    BOOL, COMPLEX, FLOAT, INT, VOID, AddressOf, Assign, Binary, Block, Break, Call, Cast, Continue, Decl, Expr, ExprStmt, For,
    If, IncDec, Index, Name, Num, Return, Stmt, Switch, Ternary, Unary, While,
)
from .numpy_backend import BackendError, _flatten_index, _join_type, _lower_switch, _stmts
from .semantic import FunctionInfo, InlineBody, PluginSpec, _lvalue_name

STATE_GLSL = {"FTx": "t.x", "FTy": "t.y", "FTz": "tz", "FPx": "v.x", "FPy": "v.y", "FPz": "vz", "TC": "col"}
AFFINE_GLSL = {"TM_a": "c00", "TM_b": "c01", "TM_c": "c10", "TM_d": "c11", "TM_e": "c20", "TM_f": "c21"}
GLSL_TYPE = {FLOAT: "float", INT: "int", BOOL: "bool", VOID: "void", COMPLEX: "vec2"}
FLOAT_MAX = 3.4028234663852886e38

# Shared helpers, emitted once per shader by the code generator (C semantics on floats/ints).
GLSL_PRELUDE = """
float fmodc(float a, float b) { return a - b * trunc(a / b); }
int imodc(int a, int b) { if (b == 0) return 0; int r = abs(a) - abs(b) * (abs(a) / abs(b)); return a < 0 ? -r : r; }
int idivc(int a, int b) { if (b == 0) return 0; int q = abs(a) / abs(b); return (a < 0) != (b < 0) ? -q : q; }
float powc(float x, float y) {
    if (x > 0.0) return pow(x, y);
    if (x == 0.0) return y == 0.0 ? 1.0 : (y > 0.0 ? 0.0 : 1.0 / 0.0);
    float f = fract(y);
    if (f != 0.0) return 0.0 / 0.0;
    return fmodc(y, 2.0) == 0.0 ? pow(-x, y) : -pow(-x, y);
}
float roundc(float x) { return sign(x) * floor(abs(x) + 0.5); }
float cbrtc(float x) { return sign(x) * pow(abs(x), 1.0 / 3.0); }
float erfc_(float x) {
    float sg = sign(x); float a = abs(x); float tt = 1.0 / (1.0 + 0.3275911 * a);
    float y = 1.0 - (((((1.061405429 * tt - 1.453152027) * tt) + 1.421413741) * tt - 0.284496736) * tt + 0.254829592) * tt * exp(-a * a);
    return sg * y;
}
float sqrc(float x) { return x * x; }
float log10c(float x) { return log(x) * 0.43429448190325176; }
float fmaxc(float a, float b) { return isnan(a) ? b : (isnan(b) ? a : max(a, b)); }
float fminc(float a, float b) { return isnan(a) ? b : (isnan(b) ? a : min(a, b)); }
int randc(inout uint s) { return int(rnd(s) * 32768.0); }
// complex numbers as vec2 (re, im)
vec2 cmul(vec2 a, vec2 b) { return vec2(a.x * b.x - a.y * b.y, a.x * b.y + a.y * b.x); }
vec2 cdiv(vec2 a, vec2 b) { float d = dot(b, b); return vec2(a.x * b.x + a.y * b.y, a.y * b.x - a.x * b.y) / d; }
vec2 cconj(vec2 a) { return vec2(a.x, -a.y); }
float cnorm(vec2 a) { return dot(a, a); }
float carg(vec2 a) { return atan(a.y, a.x); }
vec2 cexp(vec2 z) { float e = exp(z.x); return vec2(e * cos(z.y), e * sin(z.y)); }
vec2 clog(vec2 z) { return vec2(log(length(z)), atan(z.y, z.x)); }
vec2 csqrt(vec2 z) { float r = length(z); float re = sqrt(0.5 * (r + z.x)); float im = sqrt(0.5 * (r - z.x)); return vec2(re, z.y < 0.0 ? -im : im); }
vec2 csin(vec2 z) { return vec2(sin(z.x) * cosh(z.y), cos(z.x) * sinh(z.y)); }
vec2 ccos(vec2 z) { return vec2(cos(z.x) * cosh(z.y), -sin(z.x) * sinh(z.y)); }
vec2 ctan(vec2 z) { return cdiv(csin(z), ccos(z)); }
vec2 csinh(vec2 z) { return vec2(sinh(z.x) * cos(z.y), cosh(z.x) * sin(z.y)); }
vec2 ccosh(vec2 z) { return vec2(cosh(z.x) * cos(z.y), sinh(z.x) * sin(z.y)); }
vec2 ctanh(vec2 z) { return cdiv(csinh(z), ccosh(z)); }
vec2 cpowc(vec2 z, vec2 w) { return z == vec2(0.0) ? vec2(0.0) : cexp(cmul(w, clog(z))); }
vec2 casinh(vec2 z) { return clog(z + csqrt(cmul(z, z) + vec2(1.0, 0.0))); }
vec2 cacosh(vec2 z) { return clog(z + cmul(csqrt(z + vec2(1.0, 0.0)), csqrt(z - vec2(1.0, 0.0)))); }
vec2 catanh(vec2 z) { return 0.5 * (clog(vec2(1.0, 0.0) + z) - clog(vec2(1.0, 0.0) - z)); }
vec2 casin(vec2 z) { vec2 r = casinh(vec2(-z.y, z.x)); return vec2(r.y, -r.x); }
vec2 cacos(vec2 z) { vec2 r = casin(z); return vec2(1.5707963267948966 - r.x, -r.y); }
vec2 catan(vec2 z) { vec2 r = catanh(vec2(-z.y, z.x)); return vec2(r.y, -r.x); }
"""


class GlslEmitter:
    """Emits one function of a formula."""

    def __init__(self, spec: PluginSpec, info: FunctionInfo, is_helper: bool):
        self.spec = spec
        self.info = info
        self.is_helper = is_helper
        self.lines: list[str] = []
        self.indent = 1
        self.counter = 0
        self.inline_depth = 0
        self.array_dims: dict[str, list[int]] = {}

    def out(self, line: str) -> None:
        self.lines.append("    " * self.indent + line)

    def fresh(self) -> str:
        self.counter += 1
        return f"fq_t{self.counter}"

    # --- names ---------------------------------------------------------------------------------
    def name(self, n: str) -> str:
        sym = self.info.symbols.get(n)
        if sym is None:
            return "q_" + n
        if sym.kind == "state":
            return STATE_GLSL[n]
        if sym.kind == "weight":
            return "w"
        if sym.kind == "affine":
            return AFFINE_GLSL[n]
        if sym.kind in ("param", "derived"):
            return f"int(P_{n})" if sym.type == INT else f"(P_{n} != 0.0)" if sym.type == BOOL else "P_" + n
        if sym.kind == "scratch":
            return "q_" + n
        if sym.kind == "const":
            if isinstance(sym.value, (list, tuple)):
                return "@_" + n
            return _literal(sym.value, sym.type)
        return "q_" + n

    # --- function ---------------------------------------------------------------------------------
    def body(self) -> str:
        """The calc body (for wrapping in the variation function)."""
        fn = self.info.node
        for sym in self.info.symbols.values():
            if sym.kind == "scratch":
                init = f"P_{sym.name}" if sym.name in self.spec.derived_types else _zero(sym.type)
                if sym.dims:
                    self.declare(sym.type, sym.name, sym.dims, None)
                    if sym.name in self.spec.derived_dims:   # prepared table copied into the per-call array
                        size = 1
                        for d in sym.dims:
                            size *= d
                        self.out(f"for (int fq_i = 0; fq_i < {size}; fq_i++) q_{sym.name}[fq_i] = {GLSL_TYPE[sym.type]}(PA_{sym.name}(fq_i));")
                    continue
                self.out(f"{GLSL_TYPE[sym.type]} q_{sym.name} = {self.coerce_source(init, FLOAT, sym.type)};")
        self.block(fn.body.body)
        return "\n".join(self.lines)

    def helper(self) -> str:
        fn = self.info.node
        params = []
        for p in fn.params:
            if p.name == "vp":
                continue
            if p.dims:
                size = 1
                for d in p.dims:
                    size *= d
                self.array_dims["q_" + p.name] = list(p.dims)
                params.append(f"inout {GLSL_TYPE[p.type]} q_{p.name}[{size}]")
            else:
                params.append(f"{'inout ' if p.pointer else ''}{GLSL_TYPE[p.type]} q_{p.name}")
        params.extend(_context_params(self.info.needs))
        head = f"{GLSL_TYPE[fn.ret_type]} @_{fn.name}({', '.join(params)}) {{"
        self.block(fn.body.body)
        if fn.ret_type != VOID:
            self.out(f"return {_zero(fn.ret_type)};")
        return head + "\n" + "\n".join(self.lines) + "\n}"

    # --- statements ---------------------------------------------------------------------------------
    def block(self, stmts: list[Stmt]) -> None:
        for s in stmts:
            self.stmt(s)

    def stmt(self, s: Stmt) -> None:
        if isinstance(s, Block):
            self.out("{")
            self.indent += 1
            self.block(s.body)
            self.indent -= 1
            self.out("}")
        elif isinstance(s, InlineBody):
            # an inlined closure: `return` leaves the body, which a do { } while (false) gives us via `break`
            if _return_inside_loop(s.body):
                raise BackendError("a closure returning from inside a loop is not supported")
            self.out("do {")
            self.indent += 1
            self.inline_depth += 1
            self.block(s.body.body)
            self.inline_depth -= 1
            self.indent -= 1
            self.out("} while (false);")
        elif isinstance(s, Decl):
            for d in s.declarators:
                self.declare(s.type, d.name, d.dims, d.init)
        elif isinstance(s, ExprStmt):
            self.expr_stmt(s.expr)
        elif isinstance(s, If):
            self.out(f"if ({self.bool_expr(s.cond)}) {{")
            self.indent += 1
            self.block(_stmts(s.then))
            self.indent -= 1
            if s.other is not None:
                self.out("} else {")
                self.indent += 1
                self.block(_stmts(s.other))
                self.indent -= 1
            self.out("}")
        elif isinstance(s, While):
            if s.do_while:
                self.out("do {")
                self.indent += 1
                self.block(_stmts(s.body))
                self.indent -= 1
                self.out(f"}} while ({self.bool_expr(s.cond)});")
            else:
                self.out(f"while ({self.bool_expr(s.cond)}) {{")
                self.indent += 1
                self.block(_stmts(s.body))
                self.indent -= 1
                self.out("}")
        elif isinstance(s, For):
            self.out("{")
            self.indent += 1
            if isinstance(s.init, Block):
                self.block(s.init.body)
            elif s.init is not None:
                self.stmt(s.init)
            cond = self.bool_expr(s.cond) if s.cond is not None else "true"
            step = ", ".join(self.step_expr(st) for st in _stmts(s.step)) if s.step is not None else ""
            self.out(f"for (; {cond}; {step}) {{")
            self.indent += 1
            self.block(_stmts(s.body))
            self.indent -= 1
            self.out("}")
            self.indent -= 1
            self.out("}")
        elif isinstance(s, Switch):
            self.stmt(_lower_switch(s))
        elif isinstance(s, Return):
            if self.inline_depth:
                self.out("break;")
            elif self.is_helper:
                if s.value is None:
                    self.out("return;")
                else:
                    self.out(f"return {self.coerce(s.value, self.info.node.ret_type)};")
            else:
                self.out("return;")
        elif isinstance(s, Break):
            self.out("break;")
        elif isinstance(s, Continue):
            self.out("continue;")
        else:
            raise BackendError(f"unsupported statement {type(s).__name__}")

    def step_expr(self, st: Stmt) -> str:
        """A for-loop step statement as a GLSL expression (sequence operator joins several)."""
        if not isinstance(st, ExprStmt):
            raise BackendError("for-loop steps must be simple expressions")
        e = st.expr
        if isinstance(e, Assign):
            if e.op == "=":
                return f"{self.lvalue(e.target)} = {self.coerce(e.value, e.target.type)}"
            op = e.op[:-1]
            value = self.binary_source(op, self.expr(e.target), e.target.type, self.expr(e.value), e.value.type)
            vt = _binary_type(op, e.target.type, e.value.type)
            return f"{self.lvalue(e.target)} = {self.coerce_source(value, vt, e.target.type)}"
        if isinstance(e, IncDec):
            return f"{self.lvalue(e.target)}{e.op}"
        return self.expr(e)

    def declare(self, typ: str, name: str, dims: list[int], init) -> None:
        gname = self.name(name)
        if dims:
            size = 1
            for d in dims:
                size *= d
            self.array_dims[gname] = list(dims)
            if init is None:
                self.out(f"{GLSL_TYPE[typ]} {gname}[{size}];")
                self.out(f"for (int fq_i = 0; fq_i < {size}; fq_i++) {gname}[fq_i] = {_zero(typ)};")
            else:
                flat = _flatten_init(init, dims)
                items = [self.coerce(i, typ) if i is not None else _zero(typ) for i in flat]
                self.out(f"{GLSL_TYPE[typ]} {gname}[{size}] = {GLSL_TYPE[typ]}[{size}]({', '.join(items)});")
            return
        if init is None:
            self.out(f"{GLSL_TYPE[typ]} {gname} = {_zero(typ)};")
        else:
            self.out(f"{GLSL_TYPE[typ]} {gname} = {self.coerce(init, typ)};")

    def expr_stmt(self, e: Expr) -> None:
        if isinstance(e, Assign):
            target = self.lvalue(e.target)
            if e.op == "=":
                self.out(f"{target} = {self.coerce(e.value, e.target.type)};")
            else:
                op = e.op[:-1]
                value = self.binary_source(op, self.expr(e.target), e.target.type, self.expr(e.value), e.value.type)
                vt = _binary_type(op, e.target.type, e.value.type)
                self.out(f"{target} = {self.coerce_source(value, vt, e.target.type)};")
        elif isinstance(e, IncDec):
            self.out(f"{self.lvalue(e.target)}{e.op};")
        elif isinstance(e, Call) and e.func in OUT_FUNCTIONS:
            n_in, names = OUT_FUNCTIONS[e.func]
            tmp = self.fresh()
            self.out(f"float {tmp} = {self.coerce(e.args[0], FLOAT)};")
            for fn, target in zip(names, e.args[n_in:]):
                t = target.operand if isinstance(target, AddressOf) else target
                self.out(f"{self.lvalue(t)} = {fn}({tmp});")
        elif isinstance(e, Call) and e.func in ("srand", "time", "Randomize"):
            pass
        else:
            self.out(f"{self.expr(e)};")

    def lvalue(self, target: Expr) -> str:
        if isinstance(target, Call) and target.func == "VAR":
            return self.name(target.args[0].id)
        return self.expr(target)

    # --- expressions ----------------------------------------------------------------------------------
    def coerce(self, e: Expr, to: str) -> str:
        return self.coerce_source(self.expr(e), e.type, to)

    def coerce_source(self, src: str, frm: str, to: str) -> str:
        if frm == to or to == VOID:
            return src
        if to == COMPLEX:
            return f"vec2({self.coerce_source(src, frm, FLOAT)}, 0.0)"
        if frm == COMPLEX:
            raise BackendError("a complex value cannot become a real one implicitly (use real()/imag())")
        if to == INT:
            return f"int({src})"
        if to == FLOAT:
            return f"float({src})"
        if to == BOOL:
            return f"({src} != {_zero(frm)})"
        return src

    def bool_expr(self, e: Expr) -> str:
        return self.coerce(e, BOOL)

    def expr(self, e: Expr) -> str:
        if isinstance(e, Num):
            return _literal(e.value, INT if e.is_int else FLOAT)
        if isinstance(e, Name):
            return self.name(e.id)
        if isinstance(e, Unary):
            if e.op == "!":
                return f"(!{self.bool_expr(e.operand)})"
            if e.op == "~":
                return f"(~{self.coerce(e.operand, INT)})"
            if e.op == "-":
                x = self.coerce(e.operand, INT) if e.operand.type == BOOL else self.expr(e.operand)
                return f"(-{x})"
            return self.expr(e.operand)
        if isinstance(e, Cast):
            return self.coerce(e.operand, e.to)
        if isinstance(e, AddressOf):
            return self.expr(e.operand)
        if isinstance(e, Binary):
            return self.binary_source(e.op, self.expr(e.left), e.left.type, self.expr(e.right), e.right.type)
        if isinstance(e, Ternary):
            t = _join_type(e.then.type, e.other.type)
            return f"({self.bool_expr(e.cond)} ? {self.coerce(e.then, t)} : {self.coerce(e.other, t)})"
        if isinstance(e, (Assign, IncDec)):
            raise BackendError("assignment inside an expression is not supported; split it into statements")
        if isinstance(e, Index):
            base, indices = _flatten_index(e)
            dims = self._dims_of(base)
            bsym = self.info.symbols.get(_lvalue_name(base)) if isinstance(base, (Name, Call)) else None
            if bsym is not None and bsym.kind in ("derived", "const") and bsym.dims:
                # tables live in the parameter texture: big GLSL const arrays compile very slowly
                flat = self._flat_index(indices, bsym.dims)
                read = f"PA_{bsym.name}({flat})"
                return f"int({read})" if bsym.type == INT else read
            base_src = self.expr(base)
            if len(indices) == 1:
                return f"{base_src}[{self.coerce(indices[0], INT)}]"
            if dims is None or len(dims) != len(indices):
                raise BackendError("multi-dimensional array shape unknown")
            flat = None
            stride = 1
            for d, idx in reversed(list(zip(dims, indices))):
                term = self.coerce(idx, INT) if stride == 1 else f"{self.coerce(idx, INT)} * {stride}"
                flat = term if flat is None else f"{flat} + {term}"
                stride *= d
            return f"{base_src}[{flat}]"
        if isinstance(e, Call):
            return self.call(e)
        raise BackendError(f"unsupported expression {type(e).__name__}")

    def _flat_index(self, indices: list[Expr], dims: list[int]) -> str:
        if len(indices) != len(dims):
            raise BackendError("array indexed with the wrong number of subscripts")
        flat = None
        stride = 1
        for d, idx in reversed(list(zip(dims, indices))):
            term = self.coerce(idx, INT) if stride == 1 else f"{self.coerce(idx, INT)} * {stride}"
            flat = term if flat is None else f"{flat} + {term}"
            stride *= d
        return flat

    def _dims_of(self, base: Expr) -> list[int] | None:
        if isinstance(base, Call) and base.func == "VAR":
            sym = self.info.symbols.get(base.args[0].id)
            return list(sym.dims) if sym is not None and sym.dims else None
        if not isinstance(base, Name):
            return None
        sym = self.info.symbols.get(base.id)
        if sym is not None and sym.kind == "const":
            return list(sym.dims)
        if sym is not None and sym.dims:
            return list(sym.dims)
        return self.array_dims.get(self.name(base.id))

    def binary_source(self, op: str, a: str, at: str, b: str, bt: str) -> str:
        if COMPLEX in (at, bt):
            if op in ("==", "!="):
                return f"({self.coerce_source(a, at, COMPLEX)} {op} {self.coerce_source(b, bt, COMPLEX)})"
            if op in ("+", "-"):
                return f"({self.coerce_source(a, at, COMPLEX)} {op} {self.coerce_source(b, bt, COMPLEX)})"
            if op == "*":
                if at == COMPLEX and bt == COMPLEX:
                    return f"cmul({a}, {b})"
                return f"({a} * {self.coerce_source(b, bt, FLOAT) if bt != COMPLEX else b})" if at == COMPLEX else f"({self.coerce_source(a, at, FLOAT)} * {b})"
            if op == "/":
                if bt != COMPLEX:
                    return f"({a} / {self.coerce_source(b, bt, FLOAT)})"
                return f"cdiv({self.coerce_source(a, at, COMPLEX)}, {b})"
            raise BackendError(f"operator {op} on complex values")
        if op in ("&&", "||"):
            return f"({self.coerce_source(a, at, BOOL)} {op} {self.coerce_source(b, bt, BOOL)})"
        if op in ("<", ">", "<=", ">=", "==", "!="):
            t = _join_type(at, bt)
            if t == BOOL:
                t = INT
            return f"({self.coerce_source(a, at, t)} {op} {self.coerce_source(b, bt, t)})"
        if op in ("&", "|", "^", "<<", ">>"):
            return f"({self.coerce_source(a, at, INT)} {op} {self.coerce_source(b, bt, INT)})"
        if at in (INT, BOOL) and bt in (INT, BOOL):
            a, b = self.coerce_source(a, at, INT), self.coerce_source(b, bt, INT)
            if op == "/":
                return f"idivc({a}, {b})"
            if op == "%":
                return f"imodc({a}, {b})"
            return f"({a} {op} {b})"
        a, b = self.coerce_source(a, at, FLOAT), self.coerce_source(b, bt, FLOAT)
        if op == "%":
            return f"fmodc({a}, {b})"
        return f"({a} {op} {b})"

    def call(self, e: Call) -> str:
        if e.func == "VAR":
            return self.name(e.args[0].id)
        if e.func == "TM":
            return AFFINE_GLSL["TM_" + e.args[0].id]
        if e.func == "random01":
            return "rnd(s)"
        if e.func == "rand":
            return "randc(s)"
        if e.func in self.spec.helpers:
            fn = self.spec.helpers[e.func].node
            args = []
            for a, p in zip(e.args, [p for p in fn.params if p.name != "vp"]):
                target = a.operand if isinstance(a, AddressOf) else a
                args.append(self.expr(target) if p.pointer or p.dims else self.coerce(a, p.type))
            args.extend(_context_args(self.spec.helpers[e.func].needs))
            return f"@_{e.func}({', '.join(args)})"
        f = e.func
        if f == "Complex":
            if len(e.args) == 1:
                return self.coerce(e.args[0], COMPLEX)
            return f"vec2({self.coerce(e.args[0], FLOAT)}, {self.coerce(e.args[1], FLOAT)})"
        if e.args and e.args[0].type == COMPLEX:
            z = self.expr(e.args[0])
            table = {"creal": f"{z}.x", "cimag": f"{z}.y", "abs": f"length({z})", "norm": f"cnorm({z})", "arg": f"carg({z})",
                     "conj": f"cconj({z})", "exp": f"cexp({z})", "log": f"clog({z})", "sqrt": f"csqrt({z})", "sin": f"csin({z})",
                     "cos": f"ccos({z})", "tan": f"ctan({z})", "sinh": f"csinh({z})", "cosh": f"ccosh({z})", "tanh": f"ctanh({z})",
                     "asin": f"casin({z})", "acos": f"cacos({z})", "atan": f"catan({z})", "asinh": f"casinh({z})",
                     "acosh": f"cacosh({z})", "atanh": f"catanh({z})"}
            if f == "pow":
                return f"cpowc({z}, {self.coerce(e.args[1], COMPLEX)})"
            if f in table:
                return table[f]
            raise BackendError(f"{f}() is not defined for complex values")
        if f == "pow" and len(e.args) == 2 and e.args[1].type == COMPLEX:
            return f"cpowc({self.coerce(e.args[0], COMPLEX)}, {self.expr(e.args[1])})"
        fargs = [self.coerce(a, FLOAT) for a in e.args]
        if f in ("abs", "fabs", "labs", "llabs"):
            return f"abs({self.expr(e.args[0])})"
        if f in ("min", "max"):
            t = _join_type(e.args[0].type, e.args[1].type)
            return f"{f}({self.coerce(e.args[0], t)}, {self.coerce(e.args[1], t)})"
        if f == "fmin":
            return f"fminc({fargs[0]}, {fargs[1]})"
        if f == "fmax":
            return f"fmaxc({fargs[0]}, {fargs[1]})"
        if f == "atan2" or (f == "atan" and len(e.args) == 2):
            return f"atan({fargs[0]}, {fargs[1]})"
        simple = {"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "asinh", "acosh", "atanh", "exp",
                  "exp2", "log", "log2", "sqrt", "floor", "ceil", "trunc", "isnan", "isinf"}
        if f in simple:
            return f"{f}({fargs[0]})"
        table = {"pow": "powc", "fmod": "fmodc", "round": "roundc", "cbrt": "cbrtc", "erf": "erfc_", "sqr": "sqrc",
                 "log10": "log10c", "sign": "sign", "rint": "roundc", "nearbyint": "roundc"}
        if f in table:
            return f"{table[f]}({', '.join(fargs)})"
        if f == "erfc":
            return f"(1.0 - erfc_({fargs[0]}))"
        if f == "hypot":
            return f"length(vec2({fargs[0]}, {fargs[1]}))"
        if f == "copysign":
            return f"(abs({fargs[0]}) * ({fargs[1]} < 0.0 ? -1.0 : 1.0))"
        if f == "log1p":
            return f"log(1.0 + {fargs[0]})"
        if f == "expm1":
            return f"(exp({fargs[0]}) - 1.0)"
        if f in ("lround", "lrint"):
            return f"int(roundc({fargs[0]}))"
        if f == "ldexp":
            return f"({fargs[0]} * exp2({fargs[1]}))"
        if f == "fdim":
            return f"max({fargs[0]} - {fargs[1]}, 0.0)"
        if f == "fma":
            return f"({fargs[0]} * {fargs[1]} + {fargs[2]})"
        raise BackendError(f"function {f}() is not available in GLSL")


CONTEXT_PARAMS = {
    "state": ("inout vec2 t, inout float tz, inout vec2 v, inout float vz, inout float col", "t, tz, v, vz, col"),
    "weight": ("float w", "w"),
    "affine": ("float c00, float c01, float c10, float c11, float c20, float c21", "c00, c01, c10, c11, c20, c21"),
    "random": ("inout uint s", "s"),
}


def _context_params(needs: set[str]) -> list[str]:
    return [CONTEXT_PARAMS[k][0] for k in ("state", "weight", "affine", "random") if k in needs]


def _context_args(needs: set[str]) -> list[str]:
    return [CONTEXT_PARAMS[k][1] for k in ("state", "weight", "affine", "random") if k in needs]


def _return_inside_loop(body: Block) -> bool:
    def visit(node, in_loop: bool) -> bool:
        if isinstance(node, Return):
            return in_loop
        if isinstance(node, (While, For)):
            return visit(node.body, True)
        if isinstance(node, If):
            return visit(node.then, in_loop) or (node.other is not None and visit(node.other, in_loop))
        if isinstance(node, Block):
            return any(visit(s, in_loop) for s in node.body)
        if isinstance(node, InlineBody):
            return visit(node.body, False)
        if isinstance(node, Switch):
            return any(visit(st, in_loop) for c in node.cases for st in c.body)
        return False
    return visit(body, False)


def _flatten_init(init, dims: list[int]) -> list:
    if len(dims) == 1:
        items = list(init) if isinstance(init, list) else [init]
        return items + [None] * (dims[0] - len(items))
    out = []
    items = list(init) if isinstance(init, list) else []
    for i in range(dims[0]):
        sub = items[i] if i < len(items) else []
        out.extend(_flatten_init(sub, dims[1:]))
    return out


def _zero(typ: str) -> str:
    return {INT: "0", BOOL: "false", COMPLEX: "vec2(0.0)"}.get(typ, "0.0")


def _binary_type(op: str, a: str, b: str) -> str:
    if op in ("<", ">", "<=", ">=", "==", "!=", "&&", "||"):
        return BOOL
    if op in ("&", "|", "^", "<<", ">>"):
        return INT
    return COMPLEX if COMPLEX in (a, b) else FLOAT if FLOAT in (a, b) else INT


def _literal(v, typ: str) -> str:
    if typ == BOOL:
        return "true" if v else "false"
    if typ == INT:
        return str(((int(v) + 0x80000000) & 0xFFFFFFFF) - 0x80000000)   # 32-bit two's complement, as C would store it
    f = float(v)
    if f != f:
        return "(0.0 / 0.0)"
    if f in (float("inf"), float("-inf")):
        return "(1.0 / 0.0)" if f > 0 else "(-1.0 / 0.0)"
    if abs(f) > FLOAT_MAX:
        f = FLOAT_MAX if f > 0 else -FLOAT_MAX
    text = repr(f)
    if "e" in text or "E" in text:
        mant, exp = text.split("e")
        if "." not in mant:
            mant += ".0"
        return f"{mant}e{exp}"
    return text if "." in text else text + ".0"


def _const_table(name: str, typ: str, dims: list[int], value) -> str:
    flat = _flatten_value(value)
    items = ", ".join(_literal(v, typ) for v in flat)
    return f"const {GLSL_TYPE[typ]} @_{name}[{len(flat)}] = {GLSL_TYPE[typ]}[{len(flat)}]({items});"


def _flatten_value(value) -> list:
    if isinstance(value, (list, tuple)):
        out = []
        for v in value:
            out.extend(_flatten_value(v))
        return out
    return [value]


def emit(spec: PluginSpec) -> tuple[str, str]:
    """(declarations, body) — declarations hold lookup tables and helper functions, `@`-prefixed."""
    decls: list[str] = []   # (constant tables are bound through the parameter texture, see Variation.tables)
    for name, info in spec.helpers.items():
        if name in spec.calc.calls:   # helpers only prepare uses never reach the GPU
            decls.append(GlslEmitter(spec, info, is_helper=True).helper())
    body = GlslEmitter(spec, spec.calc, is_helper=False).body()
    return "\n".join(decls), body
