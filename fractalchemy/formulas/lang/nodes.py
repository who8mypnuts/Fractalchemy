"""AST node types for the formula language.

Expressions carry a `type` slot ("float", "int", "bool" or an array type) filled in by the
semantic pass; backends rely on it to insert conversions.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FLOAT, INT, BOOL, VOID, COMPLEX = "float", "int", "bool", "void", "complex"


@dataclass
class Node:
    pass


def clone(node):
    """A deep copy of an AST fragment (much faster than `copy.deepcopy` on these small dataclasses)."""
    if isinstance(node, list):
        return [clone(item) for item in node]
    if not hasattr(node, "__dataclass_fields__"):
        return node
    out = object.__new__(type(node))
    for name in node.__dict__:
        value = node.__dict__[name]
        if isinstance(value, (list, Node, Declarator, Case, Param, StructField)):
            value = clone(value)
        out.__dict__[name] = value
    return out


# --- expressions -------------------------------------------------------------
@dataclass
class Expr(Node):
    type: str = field(default=FLOAT, init=False, repr=False)
    uniform: bool = field(default=False, init=False, repr=False)   # depends on per-xform constants only


@dataclass
class Num(Expr):
    value: float | int
    is_int: bool


@dataclass
class Name(Expr):
    id: str


@dataclass
class Str(Expr):
    value: str


@dataclass
class Call(Expr):
    func: str
    args: list[Expr]


@dataclass
class Unary(Expr):
    op: str        # - + ! ~
    operand: Expr


@dataclass
class Cast(Expr):
    to: str        # float | int | bool
    operand: Expr


@dataclass
class Binary(Expr):
    op: str
    left: Expr
    right: Expr


@dataclass
class Ternary(Expr):
    cond: Expr
    then: Expr
    other: Expr


@dataclass
class Assign(Expr):
    target: Expr   # Name | Index
    op: str        # = += -= *= /= %= &= |= ^= <<= >>=
    value: Expr


@dataclass
class IncDec(Expr):
    target: Expr
    op: str        # ++ --
    prefix: bool


@dataclass
class Index(Expr):
    base: Expr
    index: Expr


@dataclass
class AddressOf(Expr):
    operand: Expr


# --- statements ---------------------------------------------------------------
@dataclass
class Stmt(Node):
    pass


@dataclass
class Declarator:
    name: str
    dims: list[int]
    init: Expr | list | None     # scalar initialiser, nested lists for arrays, or None
    pointer: bool = False        # `double* p = vp->pFPx;` — an alias of another variable


@dataclass
class Decl(Stmt):
    type: str
    declarators: list[Declarator]
    static: bool = False
    const: bool = False


@dataclass
class ExprStmt(Stmt):
    expr: Expr


@dataclass
class If(Stmt):
    cond: Expr
    then: Stmt
    other: Stmt | None


@dataclass
class For(Stmt):
    init: Stmt | None
    cond: Expr | None
    step: Expr | None
    body: Stmt


@dataclass
class While(Stmt):
    cond: Expr
    body: Stmt
    do_while: bool = False


@dataclass
class Case:
    values: list[Expr] | None    # None = default
    body: list[Stmt]


@dataclass
class Switch(Stmt):
    subject: Expr
    cases: list[Case]


@dataclass
class Return(Stmt):
    value: Expr | None


@dataclass
class Break(Stmt):
    pass


@dataclass
class Continue(Stmt):
    pass


@dataclass
class Block(Stmt):
    body: list[Stmt]


@dataclass
class Param:
    type: str
    name: str
    pointer: bool = False
    dims: list[int] = field(default_factory=list)


@dataclass
class FuncDef(Node):
    ret_type: str
    name: str
    params: list[Param]
    body: Block
    static: bool = False
    closure: bool = False      # defined inside another function (GNU C): sees that function's locals


@dataclass
class StructField:
    type: str
    name: str
    dims: list[int]


@dataclass
class Module(Node):
    """A whole formula source file."""
    plugin_name: str | None = None
    struct_fields: list[StructField] = field(default_factory=list)
    variables: list[Any] = field(default_factory=list)       # VariableDecl (see semantic)
    globals: list[Decl] = field(default_factory=list)
    functions: dict[str, FuncDef] = field(default_factory=dict)
    top_calls: list[Call] = field(default_factory=list)      # APO_PLUGIN / APO_VARIABLES
