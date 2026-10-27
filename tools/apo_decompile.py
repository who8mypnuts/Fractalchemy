"""Recover the formula of an Apophysis plugin DLL that has no source.

Symbolically executes `PluginVarPrepare` and `PluginVarCalc` of a 32-bit (x87) or 64-bit
(SSE2) plugin DLL and prints equivalent C in the plugin dialect the formula compiler
accepts. Parameter names, types and defaults come from the DLL's `VarInfo` table; the
struct layout (where the point pointers and the variables live) is read from
`PluginVarInit3D` / `PluginVarResetVariable`, so every SDK generation is handled.

Usage:
    python tools/apo_decompile.py plugin.dll [more.dll ...] [--out DIR] [--asm]

Only straight-line and branching code is supported (no loops); a plugin with a loop is
reported so it can be ported by hand from the listing (`--asm` prints it).
Every result must still be reviewed: the output is mechanical and keeps the compiled
code's structure (temporaries, inlined helpers, `sqrt`/`atan2` fallbacks removed).
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import struct
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pemeta import PE, extract  # noqa: E402

MAX_PATHS = 4000
MAX_STEPS = 20000


class Unsupported(Exception):
    pass


# --- expressions ---------------------------------------------------------------------------------
class E:
    """A symbolic value: ('num', v) | ('sym', name) | (op, *args) | ('call', name, *args)."""
    __slots__ = ("kind", "args", "_hash", "is_int")

    def __init__(self, kind: str, *args, is_int: bool = False):
        self.kind = kind
        self.args = args
        self.is_int = is_int
        self._hash = hash((kind, args, is_int))

    def __hash__(self):
        return self._hash

    def __eq__(self, other):
        return isinstance(other, E) and self.kind == other.kind and self.args == other.args and self.is_int == other.is_int

    def __repr__(self):
        return f"E({self.kind}, {self.args})"


def num(v, is_int=False) -> E:
    return E("num", v, is_int=is_int)


def sym(name: str, is_int=False) -> E:
    return E("sym", name, is_int=is_int)


def is_num(e: E, v=None) -> bool:
    return e.kind == "num" and (v is None or e.args[0] == v)


def binop(op: str, a: E, b: E) -> E:
    """Build with light constant folding / simplification."""
    if is_num(a) and is_num(b):
        x, y = a.args[0], b.args[0]
        both_int = a.is_int and b.is_int
        try:
            if op == "+":
                return num(x + y, both_int)
            if op == "-":
                return num(x - y, both_int)
            if op == "*":
                return num(x * y, both_int)
            if op == "/" and y != 0:
                return num(int(x / y) if both_int else x / y, both_int)
        except Exception:  # noqa: BLE001
            pass
    if op == "*" and (is_num(a, 1.0) or is_num(a, 1)):
        return b
    if op == "*" and (is_num(b, 1.0) or is_num(b, 1)):
        return a
    if op == "+" and is_num(a, 0.0):
        return b
    if op == "+" and is_num(b, 0.0):
        return a
    if op == "-" and is_num(b, 0.0):
        return a
    if op == "-" and is_num(a, 0.0):
        return neg(b)
    if op == "-" and a == b:
        return num(0.0)
    if op == "*" and (is_num(a, -1.0)):
        return neg(b)
    if op == "*" and (is_num(b, -1.0)):
        return neg(a)
    if op == "+" and b.kind == "neg":
        return binop("-", a, b.args[0])
    if op == "-" and b.kind == "neg":
        return binop("+", a, b.args[0])
    if op in ("+", "-") and is_num(b) and a.kind == "+" and is_num(a.args[1]):
        return binop("+", a.args[0], num(a.args[1].args[0] + (b.args[0] if op == "+" else -b.args[0]), a.args[1].is_int and b.is_int))
    if op == "*" and b.kind == "num" and a.kind != "num":
        a, b = b, a   # constants first: 2.0 * x
    if op == "+" and a.kind == "num" and b.kind != "num":
        a, b = b, a
    return E(op, a, b, is_int=a.is_int and b.is_int and op in ("+", "-", "*", "/", "%", "&", "|", "^", "<<", ">>"))


def neg(x: E) -> E:
    if x.kind == "neg":
        return x.args[0]
    if is_num(x):
        return num(-x.args[0], x.is_int)
    return E("neg", x, is_int=x.is_int)


def call(name: str, *args: E, is_int=False) -> E:
    if name == "sqrt" and len(args) == 1 and args[0].kind == "*" and args[0].args[0] == args[0].args[1]:
        return call("fabs", args[0].args[0])
    return E("call", name, *args, is_int=is_int)


PREC = {"||": 1, "&&": 2, "|": 3, "^": 4, "&": 5, "==": 6, "!=": 6, "<": 7, ">": 7, "<=": 7, ">=": 7,
        "<<": 8, ">>": 8, "+": 9, "-": 9, "*": 10, "/": 10, "%": 10, "neg": 11, "not": 11, "cast": 12}


def fmt_num(v) -> str:
    if isinstance(v, int):
        return str(v)
    if v != v:
        return "(0.0/0.0)"
    if v in (float("inf"), float("-inf")):
        return "INFINITY" if v > 0 else "-INFINITY"
    if v == int(v) and abs(v) < 1e15:
        return f"{int(v)}.0"
    text = repr(v)
    for name, c in (("M_PI", math.pi), ("M_2PI", 2 * math.pi), ("M_PI_2", math.pi / 2), ("M_PI_4", math.pi / 4),
                    ("M_1_PI", 1 / math.pi), ("M_2_PI", 2 / math.pi), ("M_SQRT2", math.sqrt(2)), ("M_SQRT1_2", math.sqrt(0.5)),
                    ("M_E", math.e), ("M_LN2", math.log(2)), ("M_LN10", math.log(10))):
        if abs(v - c) < 1e-12:
            return name
        if abs(v + c) < 1e-12:
            return "-" + name
    return text


class Printer:
    """C text for expressions, hoisting repeated subexpressions into temporaries."""

    def __init__(self):
        self.temps: dict[E, str] = {}
        self.lines: list[str] = []
        self.counter = 0

    def hoist(self, roots: list[E]) -> None:
        counts: dict[E, int] = {}

        def visit(e: E):
            if e.kind in ("num", "sym"):
                return
            counts[e] = counts.get(e, 0) + 1
            if counts[e] == 1:
                for a in e.args:
                    if isinstance(a, E):
                        visit(a)
        for r in roots:
            visit(r)

        def emit(e: E):
            if e.kind in ("num", "sym") or e in self.temps:
                return
            for a in e.args:
                if isinstance(a, E):
                    emit(a)
            if counts.get(e, 0) > 1 and e.kind not in ("cast", "not", "==", "!=", "<", ">", "<=", ">=", "&&", "||", "cond"):
                self.counter += 1
                name = f"t{self.counter}"
                self.lines.append(f"{'int' if e.is_int else 'double'} {name} = {self.text(e, hoisted=False)};")
                self.temps[e] = name
        for r in roots:
            emit(r)

    def text(self, e: E, parent_prec: int = 0, hoisted: bool = True) -> str:
        if hoisted and e in self.temps:
            return self.temps[e]
        k = e.kind
        if k == "num":
            return fmt_num(e.args[0])
        if k == "sym":
            if e.args[0].startswith("?stack"):
                return "0.0 /* uninitialised local */"
            return e.args[0]
        if k == "funcptr":
            return "0 /* function pointer */"
        if k == "call":
            if e.args[0] in ("rand", "random01"):
                return e.args[0] + "()"
            if e.args[0] == "TABLE":
                return f"TABLE_{e.args[1].args[0]:x}[{self.text(e.args[2])}]"
            return f"{e.args[0]}({', '.join(self.text(a) for a in e.args[1:])})"
        if k == "neg":
            inner = self.text(e.args[0], 11)
            return "-(" + inner + ")" if inner.startswith("-") else "-" + inner
        if k == "not":
            return "!" + self.text(e.args[0], 11)
        if k == "cast":
            return f"({e.args[0]})" + self.text(e.args[1], 12)
        if k == "cond":
            s = f"{self.text(e.args[0], 1)} ? {self.text(e.args[1])} : {self.text(e.args[2])}"
            return f"({s})"
        if len(e.args) == 1:
            return f"{k}({self.text(e.args[0])})"
        p = PREC.get(k, 9)
        s = f"{self.text(e.args[0], p)} {k} {self.text(e.args[1], p + 1)}"
        return f"({s})" if p < parent_prec or (p == parent_prec and k in ("-", "/")) else s


# --- disassembly ----------------------------------------------------------------------------------
@dataclass
class Instr:
    addr: int
    mnem: str
    ops: list[str]
    text: str
    next: int = 0


LABELS: dict[int, str] = {}


def disassemble(path: Path, is64: bool) -> dict[int, Instr]:
    out = subprocess.run(["objdump", "-d", "-M", "intel", "--no-show-raw-insn", str(path)], capture_output=True, text=True, check=True).stdout
    instrs: dict[int, Instr] = {}
    prev: Instr | None = None
    LABELS.clear()
    for line in out.splitlines():
        lm = re.match(r"^([0-9a-f]+) <([^>]+)>:$", line)
        if lm:
            LABELS[int(lm.group(1), 16)] = lm.group(2).lstrip("_")
            continue
        m = re.match(r"\s*([0-9a-f]+):\s+(\S+)\s*(.*)$", line)
        if not m:
            continue
        addr = int(m.group(1), 16)
        mnem = m.group(2)
        rest = m.group(3).strip()
        rest = re.sub(r"\s*<[^>]*>$", "", rest)
        rest = re.sub(r"\s*#.*$", "", rest)
        ops = [o.strip() for o in _split_ops(rest)] if rest else []
        if (mnem.startswith("j") or mnem == "call") and ops and re.fullmatch(r"[0-9a-f]+", ops[0]):
            ops[0] = "0x" + ops[0]   # objdump omits the 0x prefix when it can print a symbol
        ins = Instr(addr, mnem, ops, line.strip())
        if prev is not None:
            prev.next = addr
        instrs[addr] = ins
        prev = ins
    return instrs


def _split_ops(text: str) -> list[str]:
    parts, depth, cur = [], 0, []
    for ch in text:
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append("".join(cur))
            cur = []
        else:
            cur.append(ch)
    if cur:
        parts.append("".join(cur))
    return parts


MEM_RE = re.compile(r"^(?:(?P<size>QWORD|DWORD|WORD|BYTE|TBYTE|XMMWORD) PTR )?(?:(?P<seg>[cdefgs]s):)?\[(?P<inner>[^\]]*)\]$")
ABS_RE = re.compile(r"^(?:(?P<size>QWORD|DWORD|WORD|BYTE|TBYTE|XMMWORD) PTR )?[cdefgs]s:(?P<addr>0x[0-9a-f]+)$|^(?P<size2>QWORD|DWORD|WORD|BYTE|TBYTE|XMMWORD) PTR (?P<addr2>0x[0-9a-f]+)$")


@dataclass
class Mem:
    size: int           # bytes
    base: str | None
    index: str | None
    scale: int
    disp: int
    absolute: bool = False


def _static_addr(mem: Mem | None, ins: Instr) -> int | None:
    """Address of an absolute (`ds:0x...`) or rip-relative operand, else None."""
    if mem is None:
        return None
    if mem.absolute:
        return mem.disp
    if mem.base == "rip" and mem.index is None:
        return ins.next + mem.disp
    return None


def parse_mem(op: str) -> Mem | None:
    m = MEM_RE.match(op)
    if m:
        size = {"QWORD": 8, "DWORD": 4, "WORD": 2, "BYTE": 1, "TBYTE": 10, "XMMWORD": 16, None: 0}[m.group("size")]
        inner = m.group("inner")
        base = index = None
        scale, disp = 1, 0
        for term in re.split(r"(?=[+-])", inner.replace(" ", "")):
            if not term:
                continue
            sign = -1 if term.startswith("-") else 1
            term = term.lstrip("+-")
            if "*" in term:
                reg, sc = term.split("*")
                if reg == "eiz" or reg == "riz":
                    continue
                index, scale = reg, int(sc, 0)
            elif term.startswith("0x") or term.isdigit():
                disp += sign * int(term, 0)
            elif term in ("eiz", "riz"):
                pass
            else:
                if base is None:
                    base = term
                else:
                    index, scale = term, 1
        return Mem(size, base, index, scale, disp)
    m = ABS_RE.match(op)
    if m:
        size = {"QWORD": 8, "DWORD": 4, "WORD": 2, "BYTE": 1, "TBYTE": 10, "XMMWORD": 16, None: 0}[m.group("size") or m.group("size2")]
        return Mem(size, None, None, 1, int(m.group("addr") or m.group("addr2"), 16), absolute=True)
    return None


# --- plugin layout ----------------------------------------------------------------------------------
@dataclass
class Layout:
    vvar: int = 0
    pointers: dict[int, str] = field(default_factory=dict)   # struct offset -> FTx/FTy/FTz/FPx/FPy/FPz/TC
    affine: dict[int, str] = field(default_factory=dict)     # struct offset -> a..f
    var_base: int | None = None


def _find_var_base(instrs: dict[int, Instr], start: int, is64: bool) -> int | None:
    addr = start
    steps = 0
    candidates: list[int] = []
    adds: list[int] = []     # `add eax, 0x58` / `lea eax, [eax+0x58]`: vp + var block offset, indexed afterwards
    while addr in instrs and steps < 400:
        ins = instrs[addr]
        steps += 1
        for op in ins.ops:
            m = parse_mem(op)
            if m is not None and m.index is not None and m.scale == 1 and m.disp > 0 and m.size in (4, 8) and ins.mnem in ("mov", "fstp", "fst", "movsd", "fld", "fild", "fistp"):
                candidates.append(m.disp)
        if ins.mnem == "add" and len(ins.ops) == 2 and ins.ops[0] in ("eax", "ecx", "edx", "rax", "rcx", "rdx") and re.fullmatch(r"0x[0-9a-f]+", ins.ops[1]):
            v = int(ins.ops[1], 16)
            if 8 <= v < 0x400 and v % 4 == 0:
                adds.append(v)
        if ins.mnem == "lea" and len(ins.ops) == 2:
            m = parse_mem(ins.ops[1])
            if m is not None and m.index is None and m.base not in (None, "esp", "ebp", "rsp", "rbp") and 8 <= m.disp < 0x400 and m.disp % 4 == 0:
                adds.append(m.disp)
        if ins.mnem == "ret" and steps > 20 and (candidates or adds):
            break
        addr = ins.next
    if candidates:
        return min(candidates)
    if adds:
        return max(sorted(set(adds)), key=lambda v: (adds.count(v), -v))
    return None


# --- imports ------------------------------------------------------------------------------------------
def import_table(pe: PE) -> dict[int, str]:
    """Absolute IAT slot address -> imported function name."""
    d = pe.d
    opt = struct.unpack_from("<I", d, 0x3c)[0] + 24
    dd = opt + (112 if pe.is64 else 96) + 8   # import directory
    rva, size = struct.unpack_from("<II", d, dd)
    out: dict[int, str] = {}
    if not rva:
        return out
    try:
        off = pe.rva2off(rva)
    except ValueError:
        return out
    while True:
        ilt, _, _, name_rva, iat = struct.unpack_from("<IIIII", d, off)
        if not ilt and not iat:
            break
        thunk = pe.rva2off(ilt or iat)
        slot = iat
        while True:
            if pe.is64:
                entry = struct.unpack_from("<Q", d, thunk)[0]
                thunk += 8
            else:
                entry = struct.unpack_from("<I", d, thunk)[0]
                thunk += 4
            if not entry:
                break
            if not (entry >> (63 if pe.is64 else 31)):
                try:
                    fn = pe.cstr(pe.rva2off((entry & 0x7fffffff) + 2))
                except ValueError:
                    fn = f"ord_{entry:x}"
                out[pe.image_base + slot] = fn
            slot += 8 if pe.is64 else 4
        off += 20
    return out


# --- symbolic execution (x86 / x87) ---------------------------------------------------------------------
STACK = "STACK"
MATH1 = {"sin", "cos", "tan", "asin", "acos", "atan", "sinh", "cosh", "tanh", "exp", "log", "log10", "sqrt", "floor",
         "ceil", "fabs", "asinh", "acosh", "atanh", "cbrt", "exp2", "log2", "trunc", "round", "erf", "erfc", "lgamma", "tgamma",
         "expm1", "log1p"}
MATH2 = {"atan2", "pow", "fmod", "hypot", "fmax", "fmin", "copysign"}


@dataclass
class State:
    regs: dict[str, E]
    fpu: list[E]
    stack: dict[int, E]            # byte offset (relative to entry esp) -> value (doubles keyed by low address)
    mem: dict[str, E]              # named memory (FTx, FPx, VAR(x), G_addr, TC)
    cond: E | None
    flags_src: tuple | None        # ('fcmp', a, b) | ('icmp', a, b) | ('test', a, b)
    path: list[tuple[int, bool]]
    stores: list[tuple[str, E]]    # ordered writes to outputs / statics / VAR()
    ret_stack: list[int]
    calls: int = 0
    steps: int = 0
    rand_counter: int = 0
    visited: list = field(default_factory=lambda: [set()])   # per call frame: instruction addresses executed on this path

    def clone(self) -> "State":
        return State(dict(self.regs), list(self.fpu), dict(self.stack), dict(self.mem), self.cond, self.flags_src,
                     list(self.path), list(self.stores), list(self.ret_stack), self.calls, self.steps, self.rand_counter,
                     [set(v) for v in self.visited])


class Decompiler:
    def __init__(self, path: Path):
        self.path = path
        self.pe = PE(path.read_bytes())
        self.is64 = self.pe.is64
        self.meta = extract(path)
        self.exports = self.pe.exports()
        self.instrs = disassemble(path, self.is64)
        self.imports = import_table(self.pe)
        self.discovering = False
        self.layout = Layout()
        self.statics: dict[int, str] = {}
        self.static_types: dict[str, str] = {}
        if not self.meta.get("vars") and self.meta.get("nvars"):
            self.meta["vars"] = self.recover_varinfo()
        self.vars = {v["name"]: v for v in (self.meta.get("vars") or [])}
        self.layout = self.discover_layout()
        self.var_by_offset: dict[int, dict] = {}
        self.int_members: set[str] = set()
        self.fn_pointers: dict[str, list[tuple[list[E], int]]] = {}   # member -> [(prepare conditions, code address)]
        self._resolve_var_offsets()

    def recover_varinfo(self) -> list[dict] | None:
        """Newer SDK builds keep the VarInfo table in .bss and fill it from a static constructor
        (`mov dword [table+k], imm` / `movsd [table+k], xmmN`): replay those stores."""
        from pemeta import find_global_load
        fn = self.exports.get("PluginVarGetVariableNameAt") or self.exports.get("PluginVarResetVariable")
        if fn is None:
            return None
        tables = [va for _, va, _ in find_global_load(self.pe, fn) if self.is_writable(va)]
        if not tables:
            return None
        # one linear pass: constants loaded into xmm registers, then the global stores
        mem: dict[int, tuple[int, int | float]] = {}
        xmm: dict[str, float] = {}
        for a in sorted(self.instrs):
            ins = self.instrs[a]
            m, ops = ins.mnem, ins.ops
            if m == "pxor" and len(ops) == 2 and ops[0] == ops[1] and ops[0].startswith("xmm"):
                xmm[ops[0]] = 0.0
            elif m in ("movsd", "movq") and len(ops) == 2 and ops[0].startswith("xmm"):
                src = _static_addr(parse_mem(ops[1]), ins)
                if src is not None:
                    c = self.read_const(src, 8)
                    if c is not None:
                        xmm[ops[0]] = c.args[0]
                    else:
                        xmm.pop(ops[0], None)
                else:
                    xmm.pop(ops[0], None)
            elif m in ("movsd", "movq", "movlpd") and len(ops) == 2 and ops[1].startswith("xmm"):
                dst = _static_addr(parse_mem(ops[0]), ins)
                if dst is not None and ops[1] in xmm:
                    mem[dst] = (8, xmm[ops[1]])
            elif m == "mov" and len(ops) == 2 and ops[0].startswith(("DWORD PTR", "QWORD PTR")) and re.fullmatch(r"-?0x[0-9a-f]+|-?\d+", ops[1]):
                dst = _static_addr(parse_mem(ops[0]), ins)
                if dst is not None:
                    size = 8 if ops[0].startswith("QWORD") else 4
                    mem[dst] = (size, int(ops[1], 0))
        n = int(self.meta["nvars"])
        psz = 8 if self.is64 else 4

        def u32(addr: int) -> int | None:
            v = mem.get(addr)
            return None if v is None or v[0] != 4 else v[1] & 0xffffffff

        def f64(addr: int) -> float | None:
            v = mem.get(addr)
            if v is not None and v[0] == 8 and isinstance(v[1], float):
                return v[1]
            lo, hi = mem.get(addr), mem.get(addr + 4)
            if lo is not None and hi is not None and lo[0] == 4 and hi[0] == 4:
                return struct.unpack("<d", struct.pack("<II", lo[1] & 0xffffffff, hi[1] & 0xffffffff))[0]
            return 0.0 if lo is None and hi is None else None

        for table in tables:
            out = []
            for i in range(n):
                base = table + 40 * i
                nameptr = mem.get(base)
                if nameptr is None:
                    break
                try:
                    name = self.pe.cstr(self.pe.va2off(nameptr[1]))
                except Exception:  # noqa: BLE001
                    break
                if not re.fullmatch(r"[A-Za-z0-9_]+", name):
                    break
                typ = u32(base + psz) or 0
                if typ >= 2:
                    lo, hi, de = (u32(base + 16) or 0), (u32(base + 24) or 0), (u32(base + 32) or 0)
                    lo, hi, de = (struct.unpack("<i", struct.pack("<I", v))[0] for v in (lo, hi, de))
                else:
                    lo, hi, de = f64(base + 16), f64(base + 24), f64(base + 32)
                    if de is None:
                        break
                    lo, hi = lo or 0.0, hi or 0.0
                voff = u32(base + psz + 4)
                out.append({"name": name, "type": ["REAL", "REAL_CYCLIC", "INTEGER", "INTEGER_NONZERO"][typ] if typ < 4 else "INTEGER",
                            "min": lo, "max": hi, "default": de, "offset": 0 if voff is None else voff})
            if len(out) == n:
                return out
        return None

    # --- struct layout: run the Init functions symbolically and see where the arguments land --------------
    def discover_layout(self) -> Layout:
        lay = Layout()
        order3d = ["FPx", "FPy", "FPz", "FTx", "FTy", "FTz"]
        order2d = ["FPx", "FPy", "FTx", "FTy"]
        orderdc = ["FPx", "FPy", "FPz", "FTx", "FTy", "FTz", "TC"]
        self.discovering = True
        try:
            for fname, order in (("PluginVarInitDC", orderdc), ("PluginVarInit3D", order3d), ("PluginVarInit", order2d)):
                if fname not in self.exports:
                    continue
                try:
                    states = self.run_function(fname, args=[sym(f"ARG{i}") for i in range(1, 22)])
                except Unsupported:
                    continue
                found = False
                for st in states:
                    raw = {int(n[4:]): v for n, v in st.stores if n.startswith("RAW:")}
                    for off, v in raw.items():
                        if v.kind == "sym" and v.args[0].startswith("ARG"):
                            argno = int(v.args[0][3:])
                            if 1 <= argno <= len(order):
                                lay.pointers[off] = order[argno - 1]
                                found = True
                            elif fname == "PluginVarInitDC" and self.is64 and 9 <= argno <= 14:
                                lay.affine[off] = "abcdef"[argno - 9]   # InitDC(vp, 6 pointers, TC, vvar, a..f)
                            elif fname == "PluginVarInitDC" and not self.is64 and argno in (10, 12, 14, 16, 18, 20) and raw.get(lay.vvar) == sym("ARG8"):
                                lay.affine[off] = "abcdef"[(argno - 10) // 2]   # doubles by value take two dword slots (vvar = ARG8/9)
                if found:
                    break
        finally:
            self.discovering = False
        lay.var_base = _find_var_base(self.instrs, self.pe.image_base + self.exports["PluginVarResetVariable"], self.is64) if "PluginVarResetVariable" in self.exports else None
        if lay.var_base is None:
            ptr = 8 if self.is64 else 4
            lay.var_base = (max(lay.pointers) + ptr) if lay.pointers else (0x20 if not self.is64 else 0x40)
        # doubles are 8-byte aligned in the struct on x64 (and on MSVC i386); the var block starts on that boundary
        return lay

    # --- VarInfo offsets: read from the DLL's table -------------------------------------------------------
    def _resolve_var_offsets(self) -> None:
        pe = self.pe
        fn = self.exports.get("PluginVarGetVariableNameAt") or self.exports.get("PluginVarResetVariable")
        if fn is None or not self.vars:
            return
        if all("offset" in v for v in self.vars.values()):   # recovered from a static constructor
            for v in self.vars.values():
                self.var_by_offset[v["offset"]] = v
            return
        from pemeta import find_global_load, plausible_va
        n = len(self.vars)
        for _, va, _ in find_global_load(pe, fn):
            if not plausible_va(pe, va):
                continue
            try:
                names = []
                for i in range(n):
                    off = pe.va2off(va + i * 40)
                    nameptr = pe.ptr(off)
                    voff = pe.i32(off + (12 if pe.is64 else 8))
                    name = pe.cstr(pe.va2off(nameptr))
                    names.append((name, voff))
                if all(nm in self.vars for nm, _ in names):
                    for nm, voff in names:
                        self.var_by_offset[voff] = self.vars[nm]
                    return
            except Exception:  # noqa: BLE001
                continue

    # --- memory naming ----------------------------------------------------------------------------------------
    def struct_field(self, off: int, size: int) -> tuple[str, bool] | None:
        """Name of a `vp` struct field at `off`: ('VVAR'|'PTR:FTx'|'VAR(x)'|'TM(a)', is_int)."""
        lay = self.layout
        if off == lay.vvar and size == 8:
            return ("VVAR", False)
        if off in lay.pointers:
            return ("PTR:" + lay.pointers[off], False)
        if off in lay.affine:
            return ("TM(" + lay.affine[off] + ")", False)
        if lay.var_base is not None and off >= lay.var_base:
            rel = off - lay.var_base
            v = self.var_by_offset.get(rel)
            if v is not None:
                return (f"VAR({v['name']})", str(v["type"]).startswith("INT"))
            # a member that is not a user variable: a derived / scratch member
            return (f"VAR(m_{rel:x})", size == 4)
        return None

    def read_const(self, addr: int, size: int) -> E | None:
        try:
            off = self.pe.va2off(addr)
        except ValueError:
            return None
        if size == 8:
            return num(struct.unpack_from("<d", self.pe.d, off)[0])
        if size == 4:
            return num(struct.unpack_from("<i", self.pe.d, off)[0], is_int=True)
        if size == 10:
            return num(_ld80(self.pe.d[off:off + 10]))
        return None

    def is_code(self, addr: int) -> bool:
        for name, va, vsize, rawptr, rawsize in self.pe.sections:
            if self.pe.image_base + va <= addr < self.pe.image_base + va + max(vsize, rawsize):
                return name == ".text"
        return False

    def is_writable(self, addr: int) -> bool:
        for name, va, vsize, rawptr, rawsize in self.pe.sections:
            if self.pe.image_base + va <= addr < self.pe.image_base + va + max(vsize, rawsize):
                return name in (".data", ".bss")
        return False

    def global_name(self, addr: int, size: int) -> str:
        if addr not in self.statics:
            self.statics[addr] = f"g_{addr:x}"
            self.static_types[self.statics[addr]] = "int" if size == 4 else "double"
        return self.statics[addr]

    # --- execution ---------------------------------------------------------------------------------------------
    def run_function(self, name: str, args: list[E] | None = None) -> list[State]:
        start = self.pe.image_base + self.exports[name]
        init = State({}, [], {}, {}, None, None, [], [], [])
        args = args or []
        if self.is64:
            init.regs["rcx"] = sym("VP")
            init.regs["rsp"] = E("sp", 0)
            for i, r in enumerate(("rdx", "r8", "r9")):
                if i < len(args):
                    init.regs[r] = args[i]
            for i, a in enumerate(args[3:]):
                init.stack[0x28 + 8 * i] = a
        else:
            init.regs["esp"] = E("sp", 0)
            init.stack[4] = sym("VP")       # [esp+4] = first argument
            for i, a in enumerate(args):
                init.stack[8 + 4 * i] = a
        init.regs["ebp" if not self.is64 else "rbp"] = sym("?ebp")
        finished: list[State] = []
        work = [(start, init)]
        while work:
            addr, st = work.pop()
            try:
                result = self.execute(addr, st, work)
            except Unsupported:
                raise
            if result is not None:
                finished.append(result)
            if len(finished) + len(work) > MAX_PATHS:
                raise Unsupported("too many paths")
        return finished

    def execute(self, addr: int, st: State, work: list) -> State | None:
        """Run from `addr` until ret (returns the state) or a conditional branch (pushes both sides)."""
        while True:
            if addr not in self.instrs:
                raise Unsupported(f"no instruction at {addr:x}")
            ins = self.instrs[addr]
            st.steps += 1
            if st.steps > MAX_STEPS:
                raise Unsupported("too many steps (loop?)")
            if ins.mnem.startswith("j") and ins.mnem != "jmp":
                if addr in st.visited[-1]:
                    raise Unsupported(f"loop at {addr:x}")
            st.visited[-1].add(addr)
            m = ins.mnem
            if m == "ret":
                if st.ret_stack:
                    addr = st.ret_stack.pop()
                    self.pop_return(st, ins)
                    if len(st.visited) > 1:
                        st.visited.pop()
                    continue
                return st
            if m.startswith("j") and m != "jmp":
                target = int(ins.ops[0], 16)
                cond = self.branch_condition(m, st)
                if cond.kind == "num":          # statically known (e.g. the fprem completion loop)
                    addr = target if cond.args[0] else ins.next
                    continue
                known = _implied(st, cond)
                if known is True:
                    addr = target
                    continue
                if known is False:
                    addr = ins.next
                    continue
                taken = st.clone()
                taken.path.append((addr, True))
                taken.cond = None
                st.path.append((addr, False))
                self.add_cond(taken, cond)
                self.add_cond(st, E("not", cond))
                work.append((target, taken))
                addr = ins.next
                continue
            if m == "jmp":
                target = ins.ops[0]
                if target.startswith("0x"):
                    t = int(target, 16)
                    if t in st.visited[-1]:
                        raise Unsupported(f"loop at {addr:x}")
                    addr = t
                    continue
                mem = parse_mem(target)
                if mem is not None and mem.absolute and mem.disp in self.imports:
                    # tail jump to an import (thunk) — treat as call + ret
                    self.do_call(self.imports[mem.disp], st)
                    if st.ret_stack:
                        addr = st.ret_stack.pop()
                        self.pop_return(st, ins)
                        continue
                    return st
                reg_value = st.regs.get(target) if mem is None else None
                if mem is not None and not self.is64 or (reg_value is not None and reg_value.kind == "call" and reg_value.args[0] == "TABLE"):
                    table = self.jump_table(mem, st, reg_value)
                    if table is not None:
                        var, entries = table
                        for k, target_addr in entries:
                            case = st.clone()
                            case.path.append((addr, k))
                            self.add_cond(case, E("==", var, num(k, True)))
                            work.append((target_addr, case))
                        return None
                raise Unsupported(f"indirect jump at {addr:x}: {ins.text}")
            if m == "call":
                target = ins.ops[0]
                if target.startswith("0x"):
                    t = int(target, 16)
                    name = self.thunk_name(t)
                    if name is not None:
                        self.do_call(name, st)
                        addr = ins.next
                        continue
                    # internal helper: inline it
                    st.ret_stack.append(ins.next)
                    self.push_return(st)
                    st.visited.append(set())
                    addr = t
                    continue
                mem = parse_mem(target)
                if mem is not None and mem.absolute and mem.disp in self.imports:
                    self.do_call(self.imports[mem.disp], st)
                    addr = ins.next
                    continue
                value = st.regs.get(target) if mem is None else None
                if value is not None and value.kind == "funcptr":
                    t = value.args[0]
                    name = self.thunk_name(t)
                    if name is not None:
                        self.do_call(name, st)
                        addr = ins.next
                        continue
                    st.ret_stack.append(ins.next)
                    self.push_return(st)
                    st.visited.append(set())
                    addr = t
                    continue
                if value is not None and value.kind == "sym" and value.args[0] in self.fn_pointers:
                    for conds, t in self.fn_pointers[value.args[0]]:   # one path per function prepare may have chosen
                        case = st.clone()
                        case.path.append((addr, t))
                        for c in conds:
                            self.add_cond(case, c)
                        case.regs[target] = E("funcptr", t)
                        work.append((addr, case))
                    return None
                raise Unsupported(f"indirect call at {addr:x}: {ins.text}")
            self.step(ins, st)
            addr = ins.next

    def jump_table(self, mem: Mem | None, st: State, loaded: E | None = None):
        """`jmp [base + var*4]` guarded by `cmp var, N`: (var, [(case, target)...]) or None."""
        if loaded is not None:
            a = binop("+", loaded.args[2], loaded.args[1])
        else:
            a = self.addr_of(mem, st)
        var = base = None
        if a.kind == "+" and is_num(a.args[1]):
            base, scaled = a.args[1].args[0], a.args[0]
        elif a.kind == "+" and is_num(a.args[0]):
            base, scaled = a.args[0].args[0], a.args[1]
        else:
            return None
        if scaled.kind == "<<" and is_num(scaled.args[1], 2):
            var = scaled.args[0]
        elif scaled.kind == "*" and is_num(scaled.args[0], 4):
            var = scaled.args[1]
        elif scaled.kind == "*" and is_num(scaled.args[1], 4):
            var = scaled.args[0]
        if var is None:
            return None
        bound = None
        if st.flags_src is not None and st.flags_src[0] == "icmp" and st.flags_src[1] == var and is_num(st.flags_src[2]):
            bound = st.flags_src[2].args[0]
        if bound is None:
            for n, c in reversed(st.stores):
                if n == "__cond__" and c.kind == "not" and c.args[0].kind == ">" and c.args[0].args[0] == var and is_num(c.args[0].args[1]):
                    bound = c.args[0].args[1].args[0]
                    break
        if bound is None or bound > 64:
            return None
        entries = []
        for k in range(bound + 1):
            try:
                target_addr = struct.unpack_from("<I", self.pe.d, self.pe.va2off(base + 4 * k))[0]
            except ValueError:
                return None
            entries.append((k, target_addr))
        return var, entries

    def is_backedge(self, addr: int, target: int, st: State) -> bool:
        return target <= addr and any(t == target or (t > target and t <= addr) for t, _ in st.path) and target < addr

    def add_cond(self, st: State, c: E) -> None:
        st.stores.append(("__cond__", c))

    def thunk_name(self, t: int) -> str | None:
        label = LABELS.get(t)
        if label in MATH1 or label in MATH2 or label in ("rand", "srand", "lround", "lrint", "abs", "labs", "ldexp", "time", "clock"):
            return label   # a statically linked libm routine: treat like an import
        ins = self.instrs.get(t)
        if ins is None:
            return None
        if ins.mnem == "jmp":
            mem = parse_mem(ins.ops[0])
            if mem is not None and mem.absolute and mem.disp in self.imports:
                return self.imports[mem.disp]
        return None

    # --- stack frame helpers (32-bit) -------------------------------------------------------------------------
    def sp_off(self, st: State, reg: str) -> int | None:
        e = st.regs.get(reg)
        if e is not None and e.kind == "sp":
            return e.args[0]
        return None

    def push_return(self, st: State) -> None:
        if self.is64:
            sp = self.sp_off(st, "rsp")
            st.regs["rsp"] = E("sp", sp - 8)
        else:
            sp = self.sp_off(st, "esp")
            st.regs["esp"] = E("sp", sp - 4)
            st.stack[sp - 4] = sym("?retaddr")

    def pop_return(self, st: State, ins: Instr) -> None:
        if self.is64:
            sp = self.sp_off(st, "rsp")
            st.regs["rsp"] = E("sp", sp + 8)
        else:
            sp = self.sp_off(st, "esp")
            extra = int(ins.ops[0], 16) if ins.ops else 0
            st.regs["esp"] = E("sp", sp + 4 + extra)

    # --- operand access ----------------------------------------------------------------------------------------
    def addr_of(self, mem: Mem, st: State) -> E:
        """Symbolic address of a memory operand."""
        if mem.absolute:
            return num(mem.disp, True)
        base = st.regs.get(mem.base) if mem.base else None
        if mem.base and base is None:
            raise Unsupported(f"unknown register {mem.base}")
        if base is not None and base.kind == "sp" and mem.index is None:
            return E("sp", base.args[0] + mem.disp)
        addr = base if base is not None else num(0, True)
        if mem.index:
            idx = st.regs.get(mem.index)
            if idx is None:
                raise Unsupported(f"unknown index register {mem.index}")
            addr = binop("+", addr, binop("*", idx, num(mem.scale, True)))
        if mem.disp:
            addr = binop("+", addr, num(mem.disp, True))
        return addr

    def load_float(self, mem: Mem, st: State) -> E:
        """An FPU load: a 4-byte operand is a float32 (constants), 8 / 10 bytes a double."""
        if mem.size == 4:
            addr = self.addr_of(mem, st)
            kind = self.classify(addr)
            if kind[0] == "abs" and not self.is_writable(kind[1]):
                off = self.pe.va2off(kind[1])
                return num(struct.unpack_from("<f", self.pe.d, off)[0])
            v = self.load_addr(addr, 4, st, False)
            return E("cast", "double", v) if v.is_int else v
        return self.load(mem, st, mem.size)

    def load(self, mem: Mem, st: State, size: int | None = None, as_int: bool = False) -> E:
        size = size or mem.size or (8 if self.is64 else 4)
        addr = self.addr_of(mem, st)
        return self.load_addr(addr, size, st, as_int)

    def load_addr(self, addr: E, size: int, st: State, as_int: bool) -> E:
        kind = self.classify(addr)
        if kind[0] == "stack":
            off = kind[1]
            if off in st.stack:
                v = st.stack[off]
                if size == 8 and v.kind == "lo":
                    whole = _join_halves(v, st.stack.get(off + 4))
                    if whole is not None:
                        return whole      # the two halves of a double pushed separately (maybe with a sign-bit tweak)
                if size == 4 and _is_double_value(v):
                    return E("lo", v)
                return v
            if size == 4 and (off - 4) in st.stack and _is_double_value(st.stack[off - 4]):
                return E("hi", st.stack[off - 4])
            return sym(f"?stack{off:x}", as_int)
        if kind[0] == "struct":
            off = kind[1]
            if self.discovering:
                return sym(f"?field{off:x}", as_int)
            if size == 4:   # a dword read out of a double member: one half of it (copied through integer registers)
                for base, half in ((off, "lo"), (off - 4, "hi")):
                    f8 = self.struct_field(base, 8)
                    if f8 is not None and not f8[1] and (f8[0].startswith("TM(") or f8[0][4:-1] in self.vars):
                        return E(half, st.mem.get(f8[0], sym(f8[0])))
            f = self.struct_field(off, size)
            if f is None:
                raise Unsupported(f"unknown struct field at offset {off:#x}")
            name, is_int = f
            if name.startswith("PTR:"):
                return E("ptr", name[4:])
            if name == "VVAR":
                return sym("VVAR")
            return st.mem.get(name, sym(name, is_int))
        if kind[0] == "deref":
            name = kind[1]
            if name.startswith("?"):
                return num(0, True)
            v = st.mem.get(name, sym(name))
            if size == 4:
                return E("hi" if kind[2] else "lo", v)
            return v
        if kind[0] == "abs":
            a = kind[1]
            if self.is_writable(a):
                name = self.global_name(a, size)
                return st.mem.get(name, sym(name, size == 4))
            c = self.read_const(a, size)
            if c is None:
                raise Unsupported(f"unreadable constant at {a:#x}")
            return c
        if kind[0] == "table":
            base, idx = kind[1], kind[2]
            return E("call", "TABLE", num(base, True), idx, num(size, True))
        raise Unsupported(f"cannot read {addr}")

    def store(self, mem: Mem, value: E, st: State, size: int | None = None) -> None:
        size = size or mem.size or (8 if self.is64 else 4)
        addr = self.addr_of(mem, st)
        kind = self.classify(addr)
        if kind[0] == "deref" and kind[1].startswith("?"):
            return   # writes through an ignored pointer (errno)
        if size == 4 and value.kind == "num" and value.is_int and kind[0] == "deref":
            name = kind[1]
            key = ("imm", name, kind[2])
            st.mem[str(key)] = value
            lo, hi = st.mem.get(str(("imm", name, 0))), st.mem.get(str(("imm", name, 4)))
            if lo is not None and hi is not None:
                d = struct.unpack("<d", struct.pack("<Ii", lo.args[0] & 0xffffffff, hi.args[0]))[0]
                del st.mem[str(("imm", name, 0))]
                del st.mem[str(("imm", name, 4))]
                st.mem[name] = num(d)
                st.stores.append((name, num(d)))
            return
        if size == 4 and value.kind == "num" and value.is_int and kind[0] in ("stack", "struct"):
            # `mov [x], lo32; mov [x+4], hi32` writes a double constant through integer immediates
            # (in either order); doubles sit at 8-byte aligned offsets
            off = kind[1]
            st.mem[str(("imm", kind[0], off))] = value
            lo_off = off if off % 8 == 0 else off - 4
            lo = st.mem.get(str(("imm", kind[0], lo_off)))
            hi = st.mem.get(str(("imm", kind[0], lo_off + 4)))
            if lo is not None and hi is not None and (abs(lo.args[0]) > 65535 or abs(hi.args[0]) > 65535):
                d = struct.unpack("<d", struct.pack("<Ii", lo.args[0] & 0xffffffff, hi.args[0]))[0]
                if d == 0.0 or 1e-300 < abs(d) < 1e300:
                    del st.mem[str(("imm", kind[0], lo_off))]
                    del st.mem[str(("imm", kind[0], lo_off + 4))]
                    if kind[0] == "stack":
                        st.stack.pop(lo_off + 4, None)
                        st.stack[lo_off] = num(d)
                        return
                    f = self.struct_field(lo_off, 8)
                    if f is not None and not f[0].startswith("PTR:") and f[0] != "VVAR":
                        half = self.struct_field(lo_off + 4, 4)
                        drop = {f[0]} | ({half[0]} if half else set())
                        st.stores = [(n, v) for n, v in st.stores if n not in drop]
                        for n in drop:
                            st.mem.pop(n, None)
                        st.mem[f[0]] = num(d)
                        st.stores.append((f[0], num(d)))
                        return
        if kind[0] == "stack":
            off = kind[1]
            if size >= 8:
                st.stack.pop(off + 4, None)      # an 8-byte store also overwrites whatever sat in the upper dword
            elif size == 4:
                prev = st.stack.get(off - 4)
                if prev is not None and _is_double_value(prev):
                    st.stack[off - 4] = E("lo", prev)   # the high half of that double has just been replaced
            st.stack[off] = value
            return
        if kind[0] == "struct":
            if self.discovering:
                st.stores.append((f"RAW:{kind[1]}", value))
                return
            if size == 4 and value.kind in ("lo", "hi"):
                base_off = kind[1] if value.kind == "lo" else kind[1] - 4
                f = self.struct_field(base_off, 8)
                if f is None:
                    raise Unsupported(f"half store to unknown struct field {kind[1]:#x}")
                self.store_half(f[0], 0 if value.kind == "lo" else 4, value, st)
                return
            f = self.struct_field(kind[1], size)
            if f is None:
                raise Unsupported(f"store to unknown struct field {kind[1]:#x}")
            name, is_int = f
            if name.startswith("PTR:") or name == "VVAR":
                return   # Init-style pointer stores: ignore
            if value.kind == "num" and value.is_int and self.is_code(value.args[0]):
                value = E("funcptr", value.args[0])   # a function pointer chosen in prepare (e.g. the wave type)
            st.mem[name] = value
            st.stores.append((name, value))
            return
        if kind[0] == "deref":
            if size == 4:
                self.store_half(kind[1], kind[2], value, st)
                return
            st.mem[kind[1]] = value
            st.stores.append((kind[1], value))
            return
        if kind[0] == "abs":
            name = self.global_name(kind[1], size)
            st.mem[name] = value
            st.stores.append((name, value))
            return
        raise Unsupported(f"cannot write {addr}")

    def store_half(self, name: str, half: int, value: E, st: State) -> None:
        """`mov [p], lo; mov [p+4], hi` copies a double through integer registers."""
        want = "lo" if half == 0 else "hi"
        if value.kind != want:
            raise Unsupported("half-double store of a non-double value")
        whole = value.args[0]
        key = "__half__" + name
        if key in st.mem and st.mem[key] == whole:
            del st.mem[key]
            st.mem[name] = whole
            st.stores.append((name, whole))
        else:
            st.mem[key] = whole

    def classify(self, addr: E) -> tuple:
        if addr.kind == "sp":
            return ("stack", addr.args[0])
        if addr.kind == "+" and addr.args[0].kind == "sp" and is_num(addr.args[1]):
            return ("stack", addr.args[0].args[0] + addr.args[1].args[0])
        if addr.kind == "sym" and addr.args[0] == "VP":
            return ("struct", 0)
        if addr.kind == "+" and addr.args[0].kind == "sym" and addr.args[0].args[0] == "VP" and is_num(addr.args[1]):
            return ("struct", addr.args[1].args[0])
        if addr.kind == "ptr":
            return ("deref", addr.args[0], 0)
        if addr.kind == "+" and addr.args[0].kind == "ptr" and is_num(addr.args[1], 0):
            return ("deref", addr.args[0].args[0], 0)
        if addr.kind == "+" and addr.args[0].kind == "ptr" and is_num(addr.args[1], 4):
            return ("deref", addr.args[0].args[0], 4)
        if addr.kind == "num":
            return ("abs", addr.args[0])
        if addr.kind == "+" and is_num(addr.args[1]) and addr.args[0].kind in ("*", "<<"):
            return ("table", addr.args[1].args[0], addr.args[0])
        if addr.kind == "+" and is_num(addr.args[0]) and addr.args[1].kind in ("*", "<<"):
            return ("table", addr.args[0].args[0], addr.args[1])
        raise Unsupported(f"unclassifiable address {addr}")

    # --- calls --------------------------------------------------------------------------------------------------
    def do_call(self, name: str, st: State) -> None:
        name = name.lstrip("_")
        st.calls += 1
        if self.is64:
            self.do_call64(name, st)
            return
        sp = self.sp_off(st, "esp")

        def darg(i: int) -> E:
            return self.load_addr(E("sp", sp + 8 * i), 8, st, False)

        def iarg(i: int) -> E:
            return self.load_addr(E("sp", sp + 4 * i), 4, st, True)
        if name in MATH1:
            st.fpu.insert(0, call(name, darg(0)))
        elif name in MATH2:
            st.fpu.insert(0, call(name, darg(0), darg(1)))
        elif name in ("rand",):
            st.rand_counter += 1
            st.regs["eax"] = E("call", "rand", num(st.rand_counter, True), is_int=True)
        elif name in ("srand", "time", "clock"):
            st.regs["eax"] = num(0, True)
        elif name in ("lround", "lrint"):
            st.regs["eax"] = E("cast", "int", call("round", darg(0)), is_int=True)
        elif name in ("abs", "labs"):
            st.regs["eax"] = call("abs", iarg(0), is_int=True)
        elif name in ("ldexp",):
            st.fpu.insert(0, call("ldexp", darg(0), iarg(2)))
        elif name in ("modf",):
            raise Unsupported("modf")
        elif name in ("sincos",):
            raise Unsupported("sincos")
        elif name in ("_ftol", "_ftol2", "_ftol2_sse"):
            v = st.fpu.pop(0)
            st.regs["eax"] = E("cast", "int", v, is_int=True)
            st.regs["edx"] = num(0, True)
        elif name in ("__chkstk", "_alloca", "_chkstk", "__main", "__gcc_deregister_frame", "__gcc_register_frame", "_fpreset", "__cpu_features_init", "___chkstk_ms"):
            pass
        elif name == "errno":
            st.regs["eax"] = E("ptr", "?errno")   # libm's domain-error bookkeeping: ignored
        else:
            raise Unsupported(f"unknown import {name}")

    def do_call64(self, name: str, st: State) -> None:
        x = lambda i: st.regs.get(f"xmm{i}", sym(f"?xmm{i}"))  # noqa: E731
        if name in MATH1:
            st.regs["xmm0"] = call(name, x(0))
        elif name in MATH2:
            st.regs["xmm0"] = call(name, x(0), x(1))
        elif name == "rand":
            st.rand_counter += 1
            st.regs["eax"] = E("call", "rand", num(st.rand_counter, True), is_int=True)
            st.regs["rax"] = st.regs["eax"]
        elif name in ("srand", "time", "clock", "__chkstk", "___chkstk_ms", "__main"):
            st.regs["eax"] = num(0, True)
        elif name in ("lround", "lrint"):
            st.regs["eax"] = E("cast", "int", call("round", x(0)), is_int=True)
            st.regs["rax"] = st.regs["eax"]
        else:
            raise Unsupported(f"unknown import {name}")
        for r in ("rcx", "rdx", "r8", "r9", "r10", "r11"):
            st.regs.pop(r, None)

    # --- conditions ----------------------------------------------------------------------------------------------
    def branch_condition(self, jcc: str, st: State) -> E:
        src = st.flags_src
        if src is None:
            raise Unsupported(f"branch {jcc} without a known comparison")
        kind, a, b = src[0], src[1], src[2]
        if kind == "fcmp":   # unsigned-style flags from fucom/fcomi: CF = a < b, ZF = a == b, PF = unordered
            table = {"ja": ">", "jnbe": ">", "jae": ">=", "jnb": ">=", "jnc": ">=", "jb": "<", "jc": "<", "jnae": "<",
                     "jbe": "<=", "jna": "<=", "je": "==", "jz": "==", "jne": "!=", "jnz": "!="}
            if jcc in ("jp", "jpe"):
                return E("call", "isnan", binop("+", a, b))
            if jcc in ("jnp", "jpo"):
                return E("not", E("call", "isnan", binop("+", a, b)))
            if jcc not in table:
                raise Unsupported(f"float branch {jcc}")
            return E(table[jcc], a, b)
        if kind == "icmp" and a.kind == "&" and a.args[0].kind == "fxamw" and is_num(a.args[1], 0x4500) and is_num(b, 0x100):
            test = E("call", "isnan", a.args[0].args[0])   # fxam class test: NaN ⇔ (C3,C2,C0) == (0,0,1)
            if jcc in ("je", "jz"):
                return test
            if jcc in ("jne", "jnz"):
                return E("not", test)
            raise Unsupported(f"fxam branch {jcc}")
        if kind == "fxam":
            raise Unsupported("branch on fxam flags")
        if kind == "fswtest":   # test ah, mask after fnstsw: bit 0 = C0 (a < b), bit 2 = C2 (unordered), bit 6 = C3 (a == b)
            mask = src[3]
            zero = jcc in ("je", "jz")
            if jcc not in ("je", "jz", "jne", "jnz"):
                raise Unsupported(f"fsw branch {jcc}")
            table = {0x45: ">", 0x05: ">=", 0x01: ">=", 0x41: ">", 0x44: "!=", 0x40: "!=", 0x04: "ordered"}
            if mask not in table:
                raise Unsupported(f"fsw mask {mask:#x}")
            op = table[mask]
            if op == "ordered":
                c = E("not", E("call", "isnan", binop("+", a, b)))
            else:
                c = E(op, a, b)
            return c if zero else E("not", c)
        if kind == "fswcmp":   # `and ah, mask; cmp ah, imm` after fnstsw: C0 = bit 0 (a < b), C2 = bit 2 (unordered), C3 = bit 6 (a == b)
            mask, imm = src[3], src[4]
            if jcc not in ("je", "jz", "jne", "jnz"):
                raise Unsupported(f"fsw compare branch {jcc}")
            table = {(0x45, 0x40): "==", (0x45, 0x00): ">", (0x45, 0x01): "<", (0x45, 0x45): "unordered",
                     (0x44, 0x40): "==", (0x44, 0x00): "!=", (0x41, 0x40): "==", (0x41, 0x00): ">", (0x41, 0x01): "<",
                     (0x01, 0x00): ">=", (0x01, 0x01): "<", (0x05, 0x00): ">=", (0x05, 0x01): "<"}
            if (mask, imm) not in table:
                raise Unsupported(f"fsw compare mask {mask:#x} == {imm:#x}")
            op = table[(mask, imm)]
            if op == "unordered":
                c = E("call", "isnan", binop("+", a, b))
            elif op == "==" and a == b:
                c = E("not", E("call", "isnan", a))   # `fucom st(0)`: self-comparison is a NaN test
            else:
                c = E(op, a, b)
            return c if jcc in ("je", "jz") else E("not", c)
        if kind == "fprem":   # partial-remainder loop: the reduction is complete in one symbolic step
            if jcc in ("jp", "jpe"):
                return num(0, True)
            if jcc in ("jnp", "jpo"):
                return num(1, True)
            raise Unsupported(f"fprem branch {jcc}")
        if kind == "icmp":
            table = {"jl": "<", "jnge": "<", "jle": "<=", "jng": "<=", "jg": ">", "jnle": ">", "jge": ">=", "jnl": ">=",
                     "je": "==", "jz": "==", "jne": "!=", "jnz": "!=", "jb": "<", "jc": "<", "jnae": "<", "jbe": "<=",
                     "jna": "<=", "ja": ">", "jnbe": ">", "jae": ">=", "jnb": ">=", "jnc": ">=", "js": "<", "jns": ">="}
            if jcc not in table:
                raise Unsupported(f"int branch {jcc}")
            if jcc in ("js", "jns"):
                return E(table[jcc], binop("-", a, b), num(0, True))
            return E(table[jcc], a, b)
        if kind == "test" and a.kind == "hi" and (a == b or is_num(b, 0x80000000) or is_num(b, -0x80000000)):
            if jcc in ("js", "jne", "jnz"):
                return E("<", a.args[0], num(0.0))
            if jcc in ("jns", "je", "jz"):
                return E(">=", a.args[0], num(0.0))
        if kind == "test":
            v = binop("&", a, b) if a != b else a
            table = {"je": "==", "jz": "==", "jne": "!=", "jnz": "!=", "js": "<", "jns": ">=", "jle": "<=", "jg": ">", "jl": "<", "jge": ">="}
            if jcc not in table:
                raise Unsupported(f"test branch {jcc}")
            return E(table[jcc], v, num(0, True))
        raise Unsupported(f"branch {jcc}")

    # --- one instruction ----------------------------------------------------------------------------------------
    def step(self, ins: Instr, st: State) -> None:
        m = ins.mnem
        ops = ins.ops
        if m in ("nop", "lea" if False else "nop", "endbr32", "endbr64", "fwait", "wait", "fnclex", "fclex", "emms"):
            return
        if m in ("push", "pop") and not self.is64:
            return self.push_pop(ins, st)
        if m == "leave":
            if self.is64:
                st.regs["rsp"] = st.regs.get("rbp", sym("?rbp"))
                st.regs["rbp"] = sym("?rbp")
                return
            st.regs["esp"] = st.regs.get("ebp", sym("?ebp"))
            sp = self.sp_off(st, "esp")
            if sp is not None:
                st.regs["ebp"] = st.stack.get(sp, sym("?ebp"))
                st.regs["esp"] = E("sp", sp + 4)
            return
        if m == "mov" or m == "movzx" or m == "movsx" or m == "movsxd":
            return self.do_mov(ins, st)
        if m == "lea":
            mem = parse_mem(ops[1])
            if mem.base == ops[0] and mem.index is None and mem.disp == 0:
                return   # `lea esi,[esi+0x0]`: alignment padding
            if mem.base and mem.base not in st.regs:
                st.regs[mem.base] = sym(f"?{mem.base}", True)
            st.regs[ops[0]] = self.addr_of(mem, st)
            return
        if m == "xchg":
            a, b = st.regs.get(ops[0]), st.regs.get(ops[1])
            st.regs[ops[0]], st.regs[ops[1]] = b, a
            return
        if m == "and" and ops[0] == "ah" and st.regs.get("eax") is not None and st.regs["eax"].kind == "fsw":
            fsw = st.regs["eax"]   # `and ah, mask` keeps a few condition bits for a following `cmp ah, imm`
            st.regs["eax"] = E("fswand", fsw.args[0], fsw.args[1], num(int(ops[1], 0), True), is_int=True)
            st.flags_src = ("fswtest", fsw.args[0], fsw.args[1], int(ops[1], 0))
            return
        if m in ("add", "sub", "and", "or", "xor", "imul", "shl", "sar", "shr", "sal"):
            return self.do_alu(ins, st)
        if m in ("inc", "dec", "neg", "not"):
            v = self.read_any(ops[0], st, as_int=True)
            r = {"inc": lambda x: binop("+", x, num(1, True)), "dec": lambda x: binop("-", x, num(1, True)),
                 "neg": lambda x: E("neg", x, is_int=True), "not": lambda x: E("~", x, is_int=True)}[m](v)
            self.write_any(ops[0], r, st)
            if m in ("inc", "dec", "neg"):
                st.flags_src = ("icmp", r, num(0, True))
            return
        if m == "cdq":
            st.regs["edx"] = E("cdq", st.regs.get("eax", sym("?eax", True)), is_int=True)
            return
        if m == "cqo":
            st.regs["rdx"] = E("cdq", st.regs.get("rax", sym("?rax", True)), is_int=True)
            return
        if m == "idiv":
            divisor = self.read_any(ops[0], st, as_int=True)
            acc = "rax" if self.is64 else "eax"
            a = st.regs.get(acc, sym("?eax", True))
            st.regs[acc] = E("/", a, divisor, is_int=True)
            st.regs["rdx" if self.is64 else "edx"] = E("%", a, divisor, is_int=True)
            return
        if m in ("cmp",):
            if ops[0] == "ah" and st.regs.get("eax") is not None and st.regs["eax"].kind == "fswand":
                w = st.regs["eax"]
                st.flags_src = ("fswcmp", w.args[0], w.args[1], w.args[2].args[0], int(ops[1], 0))
                return
            a = self.read_any(ops[0], st, as_int=True)
            b = self.read_any(ops[1], st, as_int=True)
            st.flags_src = ("icmp", a, b)
            return
        if m == "test":
            if ops[0] == "ah" and st.regs.get("eax") is not None and st.regs["eax"].kind == "fsw":
                fsw = st.regs["eax"]
                st.flags_src = ("fswtest", fsw.args[0], fsw.args[1], int(ops[1], 0))
                return
            a = self.read_any(ops[0], st, as_int=True)
            b = self.read_any(ops[1], st, as_int=True)
            st.flags_src = ("test", a, b)
            return
        if m.startswith("set"):
            c = self.branch_condition("j" + m[3:], st)
            self.write_any(ops[0], E("cast", "int", c, is_int=True), st)
            return
        if m.startswith("cmov"):
            c = self.branch_condition("j" + m[4:], st)
            v = self.read_any(ops[1], st, as_int=True)
            cur = self.read_any(ops[0], st, as_int=True)
            self.write_any(ops[0], E("cond", c, v, cur, is_int=True), st)
            return
        if m == "sahf":
            return
        if m in ("fnstsw", "fstsw"):
            if st.flags_src is not None and st.flags_src[0] == "fxam":
                st.regs["eax"] = E("fxamw", st.flags_src[1], is_int=True)
                st.regs["rax"] = st.regs["eax"]
            elif st.flags_src is not None and st.flags_src[0] == "fcmp":
                st.regs["eax"] = E("fsw", st.flags_src[1], st.flags_src[2], is_int=True)
            return
        if m in ("fnstcw", "fstcw", "fldcw", "fninit", "finit", "ffree", "ffreep"):
            if m in ("ffree", "ffreep"):
                pass
            return
        if m.startswith("f"):
            return self.do_fpu(ins, st)
        if (m.endswith("sd") or m.endswith("pd") or m in ("movq", "movd", "pxor", "movaps", "movups", "movapd", "cvttsd2si", "cvtsi2sd", "cvtsd2si", "ucomisd", "comisd", "sqrtsd", "andpd", "xorpd", "orpd", "andnpd", "unpcklpd", "movlpd", "movhpd", "shufpd", "cvtss2sd", "cvtsd2ss", "movss", "movdqa", "movdqu", "pshufd", "punpckldq", "cvtdq2pd")):
            return self.do_sse(ins, st)
        if m in ("cwde", "cbw", "cdqe"):
            return
        raise Unsupported(f"instruction {ins.text}")

    def read_any(self, op: str, st: State, as_int: bool = False, size: int | None = None) -> E:
        mem = parse_mem(op)
        if mem is not None:
            return self.load(mem, st, size, as_int)
        if op.startswith("0x") or op.lstrip("-").isdigit():
            v = int(op, 0)
            if v >= 0x80000000 and not self.is64:
                v -= 0x100000000
            return num(v, True)
        if op in ("st", "st(0)"):
            return st.fpu[0]
        r = REG_ALIAS.get(op, op)
        if r in st.regs:
            v = st.regs[r]
            return v
        if op.startswith(("xmm",)):
            return sym(f"?{op}")
        return sym(f"?{r}", as_int)

    def write_any(self, op: str, v: E, st: State, size: int | None = None) -> None:
        mem = parse_mem(op)
        if mem is not None:
            self.store(mem, v, st, size)
            return
        r = REG_ALIAS.get(op, op)
        st.regs[r] = v
        if r in ("eax", "ebx", "ecx", "edx", "esi", "edi") and self.is64:
            st.regs["r" + r[1:]] = v
        if r.startswith("r") and self.is64 and r in ("rax", "rbx", "rcx", "rdx", "rsi", "rdi"):
            st.regs["e" + r[1:]] = v

    def push_pop(self, ins: Instr, st: State) -> None:
        sp = self.sp_off(st, "esp")
        if sp is None:
            raise Unsupported("esp unknown")
        if ins.mnem == "push":
            v = self.read_any(ins.ops[0], st, as_int=True, size=4)
            st.regs["esp"] = E("sp", sp - 4)
            st.stack[sp - 4] = v
        else:
            st.regs[ins.ops[0]] = st.stack.get(sp, sym(f"?stack{sp:x}", True))
            st.regs["esp"] = E("sp", sp + 4)

    def do_mov(self, ins: Instr, st: State) -> None:
        dst, src = ins.ops
        mdst = parse_mem(dst)
        size = mdst.size if mdst else None
        v = self.read_any(src, st, as_int=True, size=size)
        if ins.mnem in ("movsx", "movsxd", "movzx"):
            v = E("cast", "int", v, is_int=True) if v.kind != "num" else v
        if dst in ("esp", "rsp") and src in ("ebp", "rbp"):
            st.regs[dst] = st.regs.get(src, sym("?ebp"))
            return
        if dst in ("ebp", "rbp") and src in ("esp", "rsp"):
            st.regs[dst] = st.regs[src]
            return
        self.write_any(dst, v, st, size)

    def do_alu(self, ins: Instr, st: State) -> None:
        m = ins.mnem
        ops = ins.ops
        if m == "imul" and len(ops) == 3:
            a = self.read_any(ops[1], st, as_int=True)
            b = self.read_any(ops[2], st, as_int=True)
            self.write_any(ops[0], binop("*", a, b), st)
            return
        if m == "imul" and len(ops) == 1:
            a = st.regs.get("eax", sym("?eax", True))
            b = self.read_any(ops[0], st, as_int=True)
            st.regs["eax"] = binop("*", a, b)
            return
        dst, src = ops
        a = self.read_any(dst, st, as_int=True)
        b = self.read_any(src, st, as_int=True)
        if dst in ("esp", "rsp") and a.kind == "sp" and is_num(b):
            delta = b.args[0]
            st.regs[dst] = E("sp", a.args[0] + (delta if m == "add" else -delta))
            return
        if m == "xor" and dst == src:
            r = num(0, True)
        else:
            op = {"add": "+", "sub": "-", "and": "&", "or": "|", "xor": "^", "imul": "*", "shl": "<<", "sal": "<<", "sar": ">>", "shr": ">>"}[m]
            r = binop(op, a, b)
            if m == "shr":
                r = E(">>", a, b, is_int=True)
        self.write_any(dst, r, st)
        if m in ("add", "sub", "and", "or", "xor"):
            st.flags_src = ("icmp", r, num(0, True))

    # --- x87 ------------------------------------------------------------------------------------------------------
    def do_fpu(self, ins: Instr, st: State) -> None:
        m = ins.mnem
        ops = ins.ops
        f = st.fpu

        def sti(op: str) -> int:
            if op == "st":
                return 0
            mm = re.match(r"st\((\d)\)", op)
            if not mm:
                raise Unsupported(f"fpu operand {op}")
            return int(mm.group(1))
        if m == "fld":
            if ops[0].startswith("st"):
                f.insert(0, f[sti(ops[0])])
            else:
                mem = parse_mem(ops[0])
                f.insert(0, self.load_float(mem, st))
            return
        if m in ("fild",):
            mem = parse_mem(ops[0])
            v = self.load(mem, st, mem.size, as_int=True)
            if v.kind == "sym" and v.args[0].startswith("VAR(m_"):
                self.int_members.add(v.args[0][4:-1])
            f.insert(0, E("cast", "double", v))
            return
        if m in ("fst", "fstp"):
            if ops[0].startswith("st"):
                i = sti(ops[0])
                f[i] = f[0]
            else:
                mem = parse_mem(ops[0])
                self.store(mem, f[0], st, mem.size)
            if m == "fstp":
                f.pop(0)
            return
        if m in ("fistp", "fist", "fisttp"):
            mem = parse_mem(ops[0])
            self.store(mem, E("cast", "int", f[0], is_int=True), st, mem.size)
            if m != "fist":
                f.pop(0)
            return
        if m in ("fld1", "fldz", "fldpi", "fldl2e", "fldln2", "fldlg2", "fldl2t"):
            f.insert(0, {"fld1": num(1.0), "fldz": num(0.0), "fldpi": num(math.pi), "fldl2e": num(math.log2(math.e)),
                         "fldln2": num(math.log(2)), "fldlg2": num(math.log10(2)), "fldl2t": num(math.log2(10))}[m])
            return
        if m == "fxch":
            i = sti(ops[0]) if ops else 1
            f[0], f[i] = f[i], f[0]
            return
        if m in ("fchs", "fabs", "fsqrt", "fsin", "fcos", "frndint", "f2xm1", "fptan", "fsincos", "fscale", "fyl2x", "fyl2xp1", "fpatan", "fprem", "fprem1", "ftst", "fxam"):
            if m == "fchs":
                f[0] = neg(f[0])
            elif m == "fabs":
                f[0] = call("fabs", f[0])
            elif m == "fsqrt":
                f[0] = call("sqrt", f[0])
            elif m == "fsin":
                f[0] = call("sin", f[0])
            elif m == "fcos":
                f[0] = call("cos", f[0])
            elif m == "frndint":
                f[0] = call("rint", f[0])
            elif m == "fsincos":
                a = f[0]
                f[0] = call("sin", a)
                f.insert(0, call("cos", a))
            elif m == "fptan":
                a = f[0]
                f[0] = call("tan", a)
                f.insert(0, num(1.0))
            elif m == "fpatan":
                y, x = f[1], f[0]
                f.pop(0)
                f[0] = call("atan2", y, x)
            elif m == "fscale":
                f[0] = binop("*", f[0], call("pow", num(2.0), call("trunc", f[1])))
            elif m == "fyl2x":
                x = f.pop(0)
                f[0] = binop("*", f[0], call("log2", x))
            elif m == "fyl2xp1":
                x = f.pop(0)
                f[0] = binop("*", f[0], call("log2", binop("+", x, num(1.0))))
            elif m == "f2xm1":
                f[0] = binop("-", call("exp2", f[0]), num(1.0))
            elif m in ("fprem", "fprem1"):
                f[0] = call("fmod", f[0], f[1])
                st.flags_src = ("fprem", None, None)
            elif m == "ftst":
                st.flags_src = ("fcmp", f[0], num(0.0))
            elif m == "fxam":
                st.flags_src = ("fxam", f[0], None)
            return
        if m in ("fadd", "fsub", "fmul", "fdiv", "fsubr", "fdivr", "faddp", "fsubp", "fmulp", "fdivp", "fsubrp", "fdivrp",
                 "fiadd", "fisub", "fimul", "fidiv", "fisubr", "fidivr"):
            base = m.rstrip("p")
            rev = base.endswith("r") and base not in ("fsubr", "fdivr") or base in ("fsubr", "fdivr")
            opname = {"fadd": "+", "fsub": "-", "fmul": "*", "fdiv": "/", "fsubr": "-", "fdivr": "/", "fiadd": "+", "fisub": "-", "fimul": "*", "fidiv": "/", "fisubr": "-", "fidivr": "/"}[base]
            rev = base in ("fsubr", "fdivr", "fisubr", "fidivr")
            if ops and not ops[0].startswith("st"):
                mem = parse_mem(ops[0])
                if base.startswith("fi"):
                    other = E("cast", "double", self.load(mem, st, mem.size, as_int=True))
                else:
                    other = self.load_float(mem, st)
                f[0] = binop(opname, other, f[0]) if rev else binop(opname, f[0], other)
                return
            if len(ops) == 2:
                dst, src = sti(ops[0]), sti(ops[1])
            elif len(ops) == 1:
                dst, src = sti(ops[0]), 0
                if not m.endswith("p"):
                    dst, src = 0, sti(ops[0])
            else:
                dst, src = 1, 0   # faddp with no operands = faddp st(1), st
            a, b = f[dst], f[src]
            # objdump's AT&T-vs-Intel quirk: for the "r" forms with st(i), st the operands swap
            if dst != 0 and base in ("fsub", "fdiv") and m.endswith("p") and False:
                pass
            if rev:
                r = binop(opname, b, a)
            else:
                r = binop(opname, a, b)
            f[dst] = r
            if m.endswith("p"):
                f.pop(0)
            return
        if m in ("fcom", "fcomp", "fcompp", "fucom", "fucomp", "fucompp", "fcomi", "fcomip", "fucomi", "fucomip", "ficom", "ficomp"):
            if ops and not ops[-1].startswith("st"):
                mem = parse_mem(ops[-1])
                if m.startswith("fi"):
                    other = E("cast", "double", self.load(mem, st, mem.size, as_int=True))
                else:
                    other = self.load_float(mem, st)
                st.flags_src = ("fcmp", f[0], other)
            else:
                i = sti(ops[-1]) if ops else 1
                st.flags_src = ("fcmp", f[0], f[i])
            pops = 2 if m.endswith("pp") else 1 if m.endswith("p") else 0
            for _ in range(pops):
                f.pop(0)
            return
        if m.startswith("fcmov"):
            cc = m[5:]
            c = self.branch_condition("j" + cc.replace("nbe", "a").replace("nb", "ae"), st) if cc in ("b", "e", "be", "u", "nb", "ne", "nbe", "nu") else None
            if c is None:
                raise Unsupported(m)
            i = sti(ops[1])
            f[0] = E("cond", c, f[i], f[0])
            return
        if m in ("ffree", "ffreep"):
            return
        if m == "fdecstp":
            f.insert(0, sym("?st"))
            return
        if m == "fincstp":
            f.pop(0)
            return
        raise Unsupported(f"fpu instruction {ins.text}")

    # --- SSE2 (x64) -----------------------------------------------------------------------------------------------
    def do_sse(self, ins: Instr, st: State) -> None:
        m = ins.mnem
        ops = ins.ops

        def rd(op: str, as_int=False, size=8) -> E:
            mem = parse_mem(op)
            if mem is not None:
                return self.load(mem, st, mem.size or size, as_int)
            if op.startswith("xmm"):
                return st.regs.get(op, sym("?" + op))
            return self.read_any(op, st, as_int=True)
        if m in ("movsd", "movapd", "movaps", "movups", "movq", "movd", "movdqa", "movdqu", "movlpd", "movss", "cvtss2sd", "cvtsd2ss"):
            dst, src = ops
            v = rd(src)
            mdst = parse_mem(dst)
            if mdst is not None:
                self.store(mdst, v, st, mdst.size or 8)
            else:
                st.regs[dst] = v
            return
        if m in ("addsd", "subsd", "mulsd", "divsd", "addpd", "subpd", "mulpd", "divpd"):
            a, b = rd(ops[0]), rd(ops[1])
            st.regs[ops[0]] = binop({"a": "+", "s": "-", "m": "*", "d": "/"}[m[0]], a, b)
            return
        if m == "sqrtsd":
            st.regs[ops[0]] = call("sqrt", rd(ops[1]))
            return
        if m in ("maxsd", "minsd"):
            a, b = rd(ops[0]), rd(ops[1])
            st.regs[ops[0]] = call("fmax" if m == "maxsd" else "fmin", a, b)
            return
        if m in ("pxor", "xorpd", "xorps"):
            if ops[0] == ops[1]:
                st.regs[ops[0]] = num(0.0)
            else:
                b = rd(ops[1])
                st.regs[ops[0]] = neg(rd(ops[0])) if (is_num(b) and (b.args[0] != b.args[0] or True)) else E("^", rd(ops[0]), b)
            return
        if m in ("andpd", "andps"):
            st.regs[ops[0]] = call("fabs", rd(ops[0]))
            return
        if m in ("andnpd", "orpd", "unpcklpd", "shufpd", "movhpd", "pshufd", "punpckldq"):
            raise Unsupported(f"sse {m}")
        if m == "roundsd":
            mode = int(ops[2], 0) & 3
            fn = {0: "rint", 1: "floor", 2: "ceil", 3: "trunc"}[mode]
            st.regs[ops[0]] = call(fn, rd(ops[1]))
            return
        if m in ("cvttsd2si", "cvtsd2si"):
            v = rd(ops[1])
            st.regs[ops[0]] = E("cast", "int", v if m == "cvttsd2si" else call("rint", v), is_int=True)
            return
        if m in ("cvtsi2sd", "cvtdq2pd"):
            v = rd(ops[1], as_int=True, size=4)
            st.regs[ops[0]] = E("cast", "double", v)
            return
        if m in ("ucomisd", "comisd"):
            st.flags_src = ("fcmp", rd(ops[0]), rd(ops[1]))
            return
        raise Unsupported(f"sse instruction {ins.text}")


REG_ALIAS = {"al": "eax", "ax": "eax", "bl": "ebx", "bx": "ebx", "cl": "ecx", "cx": "ecx", "dl": "edx", "dx": "edx",
             "r8d": "r8", "r9d": "r9", "r10d": "r10", "r11d": "r11", "r12d": "r12", "r13d": "r13", "r14d": "r14", "r15d": "r15"}


NEGATION = {"==": "!=", "!=": "==", "<": ">=", ">=": "<", ">": "<=", "<=": ">"}


def _negate(c: E) -> E:
    if c.kind == "not":
        return c.args[0]
    if c.kind in NEGATION:
        return E(NEGATION[c.kind], c.args[0], c.args[1])
    return E("not", c)


def _implied(st: State, cond: E):
    """True / False if the path conditions already decide `cond` (syntactically), else None."""
    neg = _negate(cond)
    for n, c in st.stores:
        if n != "__cond__":
            continue
        if c == cond:
            return True
        if c == neg or _negate(c) == cond:
            return False
    return None


def _join_halves(lo: E, hi: E | None) -> E | None:
    """lo/hi dword pairs back into a double; sign-bit tricks on the high word are fabs / negation."""
    if hi is None:
        return None
    v = lo.args[0]
    if hi == E("hi", v):
        return v
    if hi.kind in ("&", "^", "|") and hi.args[0] == E("hi", v) and is_num(hi.args[1]):
        mask = hi.args[1].args[0] & 0xffffffff
        if hi.kind == "&" and mask == 0x7fffffff:
            return call("fabs", v)
        if hi.kind == "^" and mask == 0x80000000:
            return neg(v)
        if hi.kind == "|" and mask == 0x80000000:
            return neg(call("fabs", v))
    return None


def _is_pointer(v: E) -> bool:
    if v.kind in ("sp", "ptr"):
        return True
    if v.kind == "sym":
        return v.args[0] == "VP" or v.args[0].startswith(("?", "ARG"))
    if v.kind in ("+", "-"):
        return _is_pointer(v.args[0]) or _is_pointer(v.args[1])
    return False


def _is_double_value(v: E) -> bool:
    """True for values that are (symbolically) doubles rather than pointers / ints."""
    if v.is_int or v.kind in ("lo", "hi", "cdq") or _is_pointer(v):
        return False
    if v.kind == "num":
        return isinstance(v.args[0], float)
    return True


def _ld80(b: bytes) -> float:
    mant = int.from_bytes(b[:8], "little")
    se = int.from_bytes(b[8:10], "little")
    sign = -1.0 if se & 0x8000 else 1.0
    exp = se & 0x7fff
    if exp == 0 and mant == 0:
        return 0.0
    return sign * mant * 2.0 ** (exp - 16383 - 63)


# --- assembling the output ------------------------------------------------------------------------------------
RAND01 = None


LOG2E = 1.4426950408889634


def simplify_random(e: E) -> E:
    """Recognise the SDK's random01() pattern and the x87 inline expansions of exp / log."""
    if e.kind in ("num", "sym"):
        return e
    args = tuple(simplify_random(a) if isinstance(a, E) else a for a in e.args)
    e = E(e.kind, *args, is_int=e.is_int)
    # ((rand ^ (rand << 15)) & 0xfffffff) / 268435455.0   or   * 3.72529e-9
    if e.kind in ("/", "*"):
        for side in (0, 1):
            c = e.args[side]
            if c.kind == "cast" and c.args[0] == "double" and c.args[1].kind == "&" and is_num(c.args[1].args[1], 0xfffffff) and c.args[1].args[0].kind == "^":
                other = e.args[1 - side]
                if is_num(other) and (abs(other.args[0] - 268435455.0) < 1 or abs(other.args[0] - 3.725290312339702e-09) < 1e-15):
                    first = c.args[1].args[0].args[0]   # keeps the call counter: distinct calls stay distinct
                    return E("call", "random01", first.args[1] if first.kind == "call" and len(first.args) > 1 else num(0, True))
    # (int)(a == b) & (int)!isnan(a + b)  →  a == b ;  (int)(cond) != 0  →  cond
    if e.kind == "&" and e.args[0].kind == "cast" and e.args[1].kind == "cast":
        x, y = e.args[0].args[1], e.args[1].args[1]
        if y.kind == "not" and y.args[0].kind == "call" and y.args[0].args[0] == "isnan" and x.kind in ("==", "!=", "<", ">", "<=", ">="):
            return x
    if e.kind in ("!=", "==") and is_num(e.args[1], 0) and e.args[0].kind == "cast" and e.args[0].args[1].kind in ("==", "!=", "<", ">", "<=", ">=", "not", "&&", "||"):
        inner = e.args[0].args[1]
        return inner if e.kind == "!=" else _negate(inner)
    # (a ^ cdq(a)) - cdq(a)  →  abs(a)       (branch-free integer abs)
    if e.kind == "-" and e.args[1].kind == "cdq" and e.args[0].kind == "^" and e.args[0].args[1] == e.args[1] and e.args[0].args[0] == e.args[1].args[0]:
        return E("call", "abs", e.args[1].args[0], is_int=True)
    # (X - 1.0) + 1.0  →  X
    if e.kind == "+" and is_num(e.args[1], 1.0) and e.args[0].kind == "-" and is_num(e.args[0].args[1], 1.0):
        return e.args[0].args[0]
    if e.kind == "+" and is_num(e.args[0], 1.0) and e.args[1].kind == "-" and is_num(e.args[1].args[1], 1.0):
        return e.args[1].args[0]
    # exp2(A - rint(A)) * pow(2.0, trunc(rint(A)))  →  exp2(A)      (x87 f2xm1 / fscale expansion)
    if e.kind == "*":
        a, b = e.args
        for x, y in ((a, b), (b, a)):
            if x.kind == "call" and x.args[0] == "exp2" and y.kind == "call" and y.args[0] == "pow" and is_num(y.args[1], 2.0):
                arg = x.args[1]
                if arg.kind == "-" and arg.args[1].kind == "call" and arg.args[1].args[0] == "rint":
                    return simplify_random(E("call", "exp2", arg.args[0]))
    # exp2(log2e * X)  →  exp(X);   log2(X) * ln2  →  log(X);  log2(X) * log10(2) → log10(X)
    if e.kind == "call" and e.args[0] == "exp2" and e.args[1].kind == "*" and is_num(e.args[1].args[0]) and abs(e.args[1].args[0].args[0] - LOG2E) < 1e-12:
        return E("call", "exp", e.args[1].args[1])
    if e.kind == "*" and is_num(e.args[0]) and e.args[1].kind == "call" and e.args[1].args[0] == "log2":
        c = e.args[0].args[0]
        if abs(c - math.log(2)) < 1e-12:
            return E("call", "log", e.args[1].args[1])
        if abs(c - math.log10(2)) < 1e-12:
            return E("call", "log10", e.args[1].args[1])
        if abs(c - 1.0) < 1e-12:
            return e.args[1]
    return e


def render_paths(dec: Decompiler, states: list[State], outputs_prefix: str) -> list[str]:
    """Nested if/else text for the finished paths; shared subexpressions become temporaries at the top."""
    if not states:
        return ["    /* no path */"]
    pr = Printer()
    roots: list[E] = []
    for s in states:
        for n, v in s.stores:
            roots.append(simplify_random(v))
    pr.hoist(roots)

    def outcome(s: State):
        final: dict[str, E] = {}
        for n, v in s.stores:
            if n != "__cond__":
                final[n] = simplify_random(v)
        return tuple(final.items())

    def conds(s: State) -> list[E]:
        return [simplify_random(v) for n, v in s.stores if n == "__cond__"]

    def emit(sts: list[State], depth: int, lines: list[str]) -> None:
        ind = "    " * depth
        if len({tuple(sorted(outcome(s))) for s in sts}) == 1:
            sts = sts[:1]
        if len(sts) == 1:
            for n, v in outcome(sts[0]):
                if n.startswith("PTR:"):
                    n = n[4:]
                lines.append(f"{ind}{n} = {pr.text(v)};")
            return
        i = 0
        while True:
            addrs = {s.path[i][0] if i < len(s.path) else None for s in sts}
            if len(addrs) != 1 or None in addrs:
                break
            takens = {s.path[i][1] for s in sts}
            if len(takens) >= 2:
                break
            i += 1
        if None in addrs or len(addrs) != 1:
            for s in sts:   # paths diverge irregularly: spell out each full condition
                lines.append(ind + "if (" + " && ".join(pr.text(c) for c in conds(s)) + ") {")
                emit([s], depth + 1, lines)
                lines.append(ind + "}")
            return
        values = sorted({s.path[i][1] for s in sts}, key=lambda v: (v is not True, v is not False, v))
        if values not in ([True, False], [False, True]):
            first = True
            for val in values:   # a switch: one group per case value
                group = [s for s in sts if s.path[i][1] == val]
                cs = conds(group[0])
                ctext = pr.text(cs[i]) if i < len(cs) else "/*?*/"
                lines.append(f"{ind}{'if' if first else '} else if'} ({ctext}) {{")
                emit(group, depth + 1, lines)
                first = False
            lines.append(f"{ind}}}")
            return
        taken = [s for s in sts if s.path[i][1]]
        not_taken = [s for s in sts if not s.path[i][1]]
        cs = conds(taken[0])
        ctext = pr.text(cs[i]) if i < len(cs) else "/*?*/"
        lines.append(f"{ind}if ({ctext}) {{")
        emit(taken, depth + 1, lines)
        lines.append(f"{ind}}} else {{")
        emit(not_taken, depth + 1, lines)
        lines.append(f"{ind}}}")
    lines: list[str] = ["    " + line for line in pr.lines]
    emit(states, 1, lines)
    return lines


def decompile(path: Path, show_asm: bool = False) -> str:
    dec = Decompiler(path)
    meta = dec.meta
    name = meta.get("name") or path.stem
    out = [f"// Reconstructed from {path.name} ({'x64' if dec.is64 else 'x86'}) by tools/apo_decompile.py — review before use.",
           f"// layout: vvar@{dec.layout.vvar} pointers={dec.layout.pointers} var_base={dec.layout.var_base}", ""]
    out.append("typedef struct {")
    for v in meta.get("vars") or []:
        out.append(f"    {'int' if str(v['type']).startswith('INT') else 'double'} {v['name']};")
    out.append("    /*MEMBERS*/")
    out.append("} Variables;")
    out.append('#include "apoplugin.h"')
    out.append(f'APO_PLUGIN("{name}");')
    out.append("APO_VARIABLES(")
    items = []
    for v in meta.get("vars") or []:
        t = str(v["type"])
        d = v["default"]
        if t == "REAL":
            items.append(f"    VAR_REAL({v['name']}, {fmt_num(float(d))})")
        elif t == "REAL_CYCLIC":
            items.append(f"    VAR_REAL_CYCLE({v['name']}, {fmt_num(float(v['min']))}, {fmt_num(float(v['max']))}, {fmt_num(float(d))})")
        elif t == "INTEGER_NONZERO":
            items.append(f"    VAR_INTEGER_NONZERO({v['name']}, {int(d)})")
        else:
            items.append(f"    VAR_INTEGER({v['name']}, {int(d)})")
    out.append(",\n".join(items))
    out.append(");")
    for fname in ("PluginVarPrepare", "PluginVarCalc"):
        out.append("")
        out.append(f"int {fname}(Variation* vp)")
        out.append("{")
        if fname not in dec.exports:
            out.append("    return TRUE;")
            out.append("}")
            continue
        try:
            states = dec.run_function(fname)
            if fname == "PluginVarPrepare":
                found: dict[str, dict[int, list[set]]] = {}
                for st_ in states:
                    conds = [v for n, v in st_.stores if n == "__cond__"]
                    final: dict[str, E] = {}
                    for n, v in st_.stores:
                        if v.kind == "funcptr":
                            final[n] = v
                    for n, v in final.items():
                        found.setdefault(n, {}).setdefault(v.args[0], []).append(set(conds))
                for n, by_addr in found.items():   # the conditions all paths to one pointer share
                    dec.fn_pointers[n] = [(sorted(set.intersection(*sets), key=repr), a) for a, sets in by_addr.items()]
                # the pointer members themselves are not part of the formula
                for st_ in states:
                    st_.stores = [(n, v) for n, v in st_.stores if v.kind != "funcptr"]
            body = render_paths(dec, states, "")
            out.extend(body)
        except Unsupported as exc:
            out.append(f"    /* UNSUPPORTED: {exc} */")
            if show_asm:
                out.extend("    // " + dec.instrs[a].text for a in sorted(dec.instrs) if dec.pe.image_base + dec.exports[fname] <= a < dec.pe.image_base + dec.exports[fname] + 600)
        out.append("    return TRUE;")
        out.append("}")
    text = "\n".join(out)
    members = sorted(set(re.findall(r"VAR\((m_[0-9a-f]+)\)", text)))
    decl = "".join(f"    {'int' if m in dec.int_members else 'double'} {m};\n" for m in members).rstrip("\n")
    text = text.replace("    /*MEMBERS*/", decl if members else "")
    # statics
    if dec.statics:
        decls = "\n".join(f"static {dec.static_types[n]} {n};" for n in dec.statics.values())
        text = text.replace('#include "apoplugin.h"', '#include "apoplugin.h"\n' + decls)
    return text


RECONSTRUCTED_HEADER = """/*
    Fractalchemy formula library — reconstructed from the Apophysis plugin DLL
        {dll}   ({arch}, no source available)
    by tools/apo_decompile.py, which symbolically executes the plugin's machine code and
    writes the equivalent formula in the plugin dialect. Parameter names, types and
    defaults come from the DLL's own variable table. Verified: the numpy and GLSL
    translations agree on the test points (tests/test_variations.py).
*/

"""


def batch(source: Path, out: Path, only: set[str], refresh: bool = False) -> int:
    """Decompile every plugin DLL under `source` whose formula is not yet in the registry,
    verify the result with both engines and write the survivors into `out`."""
    import hashlib
    import importlib
    import tempfile
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tests"))
    importlib.import_module("test_variations")   # probes GL before any context is created
    import import_apo_plugins as I
    from fractalchemy.formulas.lang import FormulaError, compile_source
    from fractalchemy.fractal import variations as V
    import moderngl
    ctx = moderngl.create_standalone_context(require=330)
    work = Path(tempfile.mkdtemp(prefix="apo-dll-"))
    I.extract_archives(source, work)
    candidates: dict[str, list[Path]] = {}
    seen_hashes: set[str] = set()
    for root in (source, work):
        for dll in sorted(root.rglob("*.dll")):
            data = dll.read_bytes()
            h = hashlib.md5(data).hexdigest()
            if h in seen_hashes:
                continue
            seen_hashes.add(h)
            try:
                meta = extract(dll)
            except Exception:  # noqa: BLE001
                continue
            name = meta.get("name")
            if not name:
                continue
            existing = V.REGISTRY.get(name)
            if existing is not None and not (refresh and "/reconstructed/" in existing.origin.replace("\\", "/")):
                continue
            candidates.setdefault(name, []).append(dll)
    written, failed = [], []
    for name in sorted(candidates, key=str.lower):
        if only and name not in only:
            continue
        # 32-bit DLLs decompile most reliably (x87); try them first
        dlls = sorted(candidates[name], key=lambda p: (PE(p.read_bytes()).is64, len(str(p))))
        last = "?"
        for dll in dlls:
            try:
                text = decompile(dll)
            except Exception as exc:  # noqa: BLE001
                last = f"{type(exc).__name__}: {exc}"
                continue
            if "UNSUPPORTED" in text:
                last = [ln for ln in text.splitlines() if "UNSUPPORTED" in ln][0].strip()
                continue
            try:
                compiled = compile_source(text, origin=dll.name)
            except FormulaError as exc:
                last = "compile: " + str(exc).split(": ", 1)[-1]
                continue
            ok, why = I.verify(compiled.variation, ctx)
            if not ok:
                last = why
                continue
            arch = "x64" if PE(dll.read_bytes()).is64 else "x86 (32-bit)"
            out.mkdir(parents=True, exist_ok=True)
            (out / f"{name}.c").write_text(RECONSTRUCTED_HEADER.format(dll=dll.name, arch=arch) + text, encoding="utf-8")
            written.append(name)
            break
        else:
            failed.append((name, last))
    shutil.rmtree(work, ignore_errors=True)
    print(f"reconstructed {len(written)}: {', '.join(written)}")
    print(f"\nnot reconstructed {len(failed)}:")
    for name, why in failed:
        print(f"  {name:24s} {why[:150]}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("dlls", nargs="*")
    ap.add_argument("--out", default="")
    ap.add_argument("--asm", action="store_true")
    ap.add_argument("--batch", default="", help="scan this folder for plugin DLLs and reconstruct every missing formula")
    ap.add_argument("--only", default="")
    ap.add_argument("--refresh", action="store_true", help="with --batch: regenerate formulas already reconstructed")
    args = ap.parse_args()
    if args.batch:
        return batch(Path(args.batch), Path(args.out or "fractalchemy/formulas/library/reconstructed"), {n for n in args.only.split(",") if n}, args.refresh)
    for d in args.dlls:
        p = Path(d)
        try:
            text = decompile(p, args.asm)
        except Exception as exc:  # noqa: BLE001
            text = f"// FAILED {p.name}: {type(exc).__name__}: {exc}"
        if args.out:
            Path(args.out).mkdir(parents=True, exist_ok=True)
            (Path(args.out) / (p.stem + ".c")).write_text(text)
            print(p.name, "->", "ok" if "UNSUPPORTED" not in text and "FAILED" not in text else "problem")
        else:
            print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
