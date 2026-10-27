"""Recursive-descent parser for the formula language (a C subset) → `nodes.Module`."""

from __future__ import annotations

from .lexer import Token, tokenize
from .nodes import (
    BOOL, COMPLEX, FLOAT, INT, VOID, AddressOf, Assign, Binary, Block, Break, Call, Case, Cast, Continue, Decl, Declarator,
    Expr, ExprStmt, For, FuncDef, If, IncDec, Index, Module, Name, Num, Param, Return, Stmt, Str, StructField, Switch,
    Ternary, Unary, While,
)

TYPE_WORDS = {
    "double": FLOAT, "float": FLOAT, "int": INT, "long": INT, "short": INT, "unsigned": INT, "signed": INT,
    "char": INT, "bool": BOOL, "_Bool": BOOL, "void": VOID, "size_t": INT, "BOOL": INT, "DWORD": INT, "uint": INT,
}
QUALIFIERS = {"const", "static", "inline", "extern", "volatile", "register", "__inline", "__inline__", "restrict",
              "__restrict", "DLLIMPORT", "DLLEXPORT", "APIENTRY", "WINAPI", "__cdecl", "__stdcall", "__fastcall"}
ASSIGN_OPS = {"=", "+=", "-=", "*=", "/=", "%=", "&=", "|=", "^=", "<<=", ">>="}
BINARY_PRECEDENCE = [
    {"||"}, {"&&"}, {"|"}, {"^"}, {"&"}, {"==", "!="}, {"<", ">", "<=", ">="}, {"<<", ">>"}, {"+", "-"}, {"*", "/", "%"},
]


class ParseError(ValueError):
    """The source is not in the supported C subset."""


class Parser:
    """Turns tokens into a Module. Use `parse(text)`."""

    def __init__(self, tokens: list[Token], text: str = ""):
        self.tokens = tokens
        self.i = 0
        self.text = text
        self.nested_functions: dict[str, FuncDef] = {}   # GNU C nested functions, hoisted to module level
        self.typedefs: dict[str, str] = {"Variation": INT, "Variables": INT, "VariableInfo": INT, "IntOrDouble": INT,
                                         "VarType": INT}   # SDK types; only ever used for `Variation* vp`

    # --- token helpers -----------------------------------------------------
    @property
    def tok(self) -> Token:
        return self.tokens[self.i]

    def peek(self, offset: int = 1) -> Token:
        j = min(self.i + offset, len(self.tokens) - 1)
        return self.tokens[j]

    def at(self, *values: str) -> bool:
        return self.tok.kind in ("op", "ident") and self.tok.value in values

    def accept(self, value: str) -> bool:
        if self.at(value):
            self.i += 1
            return True
        return False

    def expect(self, value: str) -> Token:
        if not self.at(value):
            self.error(f"expected {value!r}, found {self.tok.value!r}")
        t = self.tok
        self.i += 1
        return t

    def ident(self) -> str:
        if self.tok.kind != "ident":
            self.error(f"expected identifier, found {self.tok.value!r}")
        v = self.tok.value
        self.i += 1
        return v

    def error(self, message: str):
        line = self.text.count("\n", 0, self.tok.pos) + 1 if self.text else "?"
        raise ParseError(f"line {line}: {message}")

    def is_type_start(self, offset: int = 0) -> bool:
        t = self.peek(offset) if offset else self.tok
        return t.kind == "ident" and (t.value in TYPE_WORDS or t.value in QUALIFIERS or t.value in self.typedefs)

    # --- module ---------------------------------------------------------------
    def parse_module(self) -> Module:
        module = Module()
        while self.tok.kind != "eof":
            self.parse_top_level(module)
        for name, fn in self.nested_functions.items():
            module.functions.setdefault(name, fn)
        return module

    def parse_top_level(self, module: Module) -> None:
        if self.accept(";"):
            return
        if self.at("typedef"):
            self.parse_typedef(module)
            return
        if self.at("using"):   # using namespace std;
            self.skip_to(";")
            return
        if self.at("extern") and self.peek().kind == "string":
            self.i += 2
            if self.accept("{"):
                while not self.at("}"):
                    self.parse_top_level(module)
                self.expect("}")
            return
        if self.at("__declspec") or self.at("__attribute__"):
            self.i += 1
            self.skip_parens()
        if self.tok.kind == "ident" and self.tok.value in ("APO_PLUGIN", "APO_VARIABLES") and self.peek().value == "(":
            call = self.parse_postfix()
            self.accept(";")
            module.top_calls.append(call)
            return
        if self.is_type_start():
            static, const, typ = self.parse_type_prefix()
            pointer = False
            while self.accept("*"):
                pointer = True
            name = self.ident()
            if self.at("("):
                params = self.parse_params()
                if self.accept(";"):
                    return  # prototype
                body = self.parse_block()
                if not pointer:
                    module.functions[name] = FuncDef(typ, name, params, body, static)
                return
            decl = self.parse_declarators(typ, name, static, const, pointer)
            module.globals.append(decl)
            return
        self.error(f"unexpected {self.tok.value!r} at top level")

    def skip_to(self, value: str) -> None:
        while not self.at(value) and self.tok.kind != "eof":
            self.i += 1
        self.accept(value)

    def skip_parens(self) -> None:
        if not self.at("("):
            return
        depth = 0
        while self.tok.kind != "eof":
            if self.at("("):
                depth += 1
            elif self.at(")"):
                depth -= 1
                if depth == 0:
                    self.i += 1
                    return
            self.i += 1

    def parse_typedef(self, module: Module) -> None:
        self.expect("typedef")
        if self.accept("struct"):
            if self.tok.kind == "ident" and not self.at("{"):
                self.i += 1
            self.expect("{")
            fields: list[StructField] = []
            while not self.at("}"):
                _, _, typ = self.parse_type_prefix()
                while True:
                    while self.accept("*"):
                        pass
                    name = self.ident()
                    dims = self.parse_dims()
                    fields.append(StructField(typ, name, dims))
                    if not self.accept(","):
                        break
                self.expect(";")
            self.expect("}")
            name = self.ident()
            self.expect(";")
            if name == "Variables":
                module.struct_fields = fields
            self.typedefs[name] = name
            return
        # typedef <type> Name;  (e.g. typedef complex<double> Complex;)
        start = self.i
        self.skip_to(";")
        words = [t.value for t in self.tokens[start:self.i - 1]]
        if words and words[-1].isidentifier():
            base = " ".join(words[:-1])
            if "complex" in base:
                self.typedefs[words[-1]] = COMPLEX     # typedef std::complex<double> Complex;
                return
            self.typedefs[words[-1]] = TYPE_WORDS.get(words[0], FLOAT)

    def parse_type_prefix(self) -> tuple[bool, bool, str]:
        """Qualifiers and base type at the current position → (static, const, type)."""
        static = const = False
        typ = None
        while True:
            if self.tok.kind != "ident":
                break
            v = self.tok.value
            if v in QUALIFIERS:
                static |= v == "static"
                const |= v == "const"
                self.i += 1
                if v == "__declspec" or self.at("("):
                    self.skip_parens()
            elif v in TYPE_WORDS:
                t = TYPE_WORDS[v]
                typ = t if typ is None or typ == INT and t != INT or t == VOID else typ
                if typ == INT and t == FLOAT:
                    typ = FLOAT
                self.i += 1
            elif v in self.typedefs:
                typ = self.typedefs[v]
                self.i += 1
            elif v == "struct":
                self.i += 1
                self.ident()
                typ = INT
            else:
                break
        if typ is None:
            self.error(f"expected a type, found {self.tok.value!r}")
        return static, const, typ

    def parse_params(self) -> list[Param]:
        self.expect("(")
        params: list[Param] = []
        if self.accept(")"):
            return params
        while True:
            if self.at("void") and self.peek().value == ")":
                self.i += 1
                break
            _, _, typ = self.parse_type_prefix()
            pointer = False
            while self.accept("*") or self.accept("&"):
                pointer = True
            name = self.ident() if self.tok.kind == "ident" else ""
            dims = self.parse_dims()
            params.append(Param(typ, name, pointer or bool(dims), dims))
            if not self.accept(","):
                break
        self.expect(")")
        return params

    def parse_dims(self) -> list[int]:
        dims: list[int] = []
        while self.accept("["):
            if self.accept("]"):
                dims.append(0)
                continue
            size = self.parse_expr()
            self.expect("]")
            dims.append(_const_int(size))
        return dims

    def parse_declarators(self, typ: str, first_name: str, static: bool, const: bool, pointer: bool = False) -> Decl:
        declarators: list[Declarator] = []
        name = first_name
        while True:
            dims = self.parse_dims()
            init = None
            if self.accept("="):
                init = self.parse_initializer() if self.at("{") else self.parse_expr()
            elif self.at("("):        # C++ constructor syntax: Complex z(a, b);  double x(1.0);
                self.i += 1
                args: list[Expr] = []
                while not self.at(")"):
                    args.append(self.parse_expr())
                    if not self.accept(","):
                        break
                self.expect(")")
                init = Call("Complex", args) if typ == COMPLEX else (args[0] if len(args) == 1 else None)
            declarators.append(Declarator(name, dims, init, pointer))
            if not self.accept(","):
                break
            pointer = False
            while self.accept("*"):
                pointer = True
            name = self.ident()
        self.expect(";")
        return Decl(typ, declarators, static, const)

    def parse_initializer(self):
        self.expect("{")
        items = []
        while not self.at("}"):
            items.append(self.parse_initializer() if self.at("{") else self.parse_expr())
            if not self.accept(","):
                break
        self.expect("}")
        return items

    # --- statements -------------------------------------------------------------
    def parse_block(self) -> Block:
        self.expect("{")
        body: list[Stmt] = []
        while not self.at("}"):
            if self.tok.kind == "eof":
                self.error("unexpected end of file inside a block")
            body.extend(self.parse_statement())
        self.expect("}")
        return Block(body)

    def parse_statement(self) -> list[Stmt]:
        """One statement; a comma expression or multi-declarator yields several."""
        if self.at("{"):
            return [self.parse_block()]
        if self.accept(";"):
            return []
        if self.at("if"):
            self.i += 1
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            then = self.as_block(self.parse_statement())
            other = self.as_block(self.parse_statement()) if self.accept("else") else None
            return [If(cond, then, other)]
        if self.at("for"):
            self.i += 1
            self.expect("(")
            init = None
            if not self.at(";"):
                if self.is_type_start():
                    static, const, typ = self.parse_type_prefix()
                    init = self.parse_declarators(typ, self.ident(), static, const)
                else:
                    init = Block([ExprStmt(e) for e in self.parse_comma_list()])
                    self.expect(";")
            else:
                self.expect(";")
            cond = None if self.at(";") else self.parse_expr()
            self.expect(";")
            step = None if self.at(")") else Block([ExprStmt(e) for e in self.parse_comma_list()])
            self.expect(")")
            body = self.as_block(self.parse_statement())
            return [For(init, cond, step, body)]
        if self.at("while"):
            self.i += 1
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            return [While(cond, self.as_block(self.parse_statement()))]
        if self.at("do"):
            self.i += 1
            body = self.as_block(self.parse_statement())
            self.expect("while")
            self.expect("(")
            cond = self.parse_expr()
            self.expect(")")
            self.accept(";")
            return [While(cond, body, do_while=True)]
        if self.at("switch"):
            return [self.parse_switch()]
        if self.at("return"):
            self.i += 1
            value = None if self.at(";") else self.parse_expr()
            self.expect(";")
            return [Return(value)]
        if self.at("break"):
            self.i += 1
            self.expect(";")
            return [Break()]
        if self.at("continue"):
            self.i += 1
            self.expect(";")
            return [Continue()]
        if self.at("using"):
            self.skip_to(";")
            return []
        if self.at("goto") or (self.tok.kind == "ident" and self.peek().value == ":" and self.peek(2).value != ":"):
            self.error("goto / labels are not supported")
        if self.is_type_start():
            static, const, typ = self.parse_type_prefix()
            pointer = False
            while self.accept("*"):
                pointer = True
            name = self.ident()
            if self.at("(") and (self.is_type_start(1) or (self.peek().value == ")" and self.peek(2).value == "{")):
                # nested function definition (GNU C): hoisted, it may only use globals and parameters
                params = self.parse_params()
                body = self.parse_block()
                self.nested_functions[name] = FuncDef(typ, name, params, body, static, closure=True)
                return []
            return [self.parse_declarators(typ, name, static, const, pointer)]
        exprs = self.parse_comma_list()
        self.expect(";")
        return [ExprStmt(e) for e in exprs]

    def as_block(self, stmts: list[Stmt]) -> Block:
        return stmts[0] if len(stmts) == 1 and isinstance(stmts[0], Block) else Block(stmts)

    def parse_switch(self) -> Switch:
        self.expect("switch")
        self.expect("(")
        subject = self.parse_expr()
        self.expect(")")
        self.expect("{")
        cases: list[Case] = []
        while not self.at("}"):
            values: list[Expr] | None = []
            while self.at("case") or self.at("default"):
                if self.accept("default"):
                    values = None
                else:
                    self.i += 1
                    v = self.parse_expr()
                    if values is not None:
                        values.append(v)
                self.expect(":")
            if values == [] :
                self.error("expected 'case' or 'default'")
            body: list[Stmt] = []
            while not (self.at("case") or self.at("default") or self.at("}")):
                body.extend(self.parse_statement())
            cases.append(Case(values, body))
        self.expect("}")
        return Switch(subject, cases)

    # --- expressions ------------------------------------------------------------
    def parse_comma_list(self) -> list[Expr]:
        exprs = [self.parse_expr()]
        while self.accept(","):
            exprs.append(self.parse_expr())
        return exprs

    def parse_expr(self) -> Expr:
        """Assignment expression (right associative)."""
        left = self.parse_ternary()
        if self.tok.kind == "op" and self.tok.value in ASSIGN_OPS:
            op = self.tok.value
            self.i += 1
            right = self.parse_expr()
            if not _is_lvalue(left):
                self.error("assignment to something that is not a variable or array element")
            return Assign(left, op, right)
        return left

    def parse_ternary(self) -> Expr:
        cond = self.parse_binary(0)
        if self.accept("?"):
            then = self.parse_expr()
            self.expect(":")
            other = self.parse_expr()
            return Ternary(cond, then, other)
        return cond

    def parse_binary(self, level: int) -> Expr:
        if level >= len(BINARY_PRECEDENCE):
            return self.parse_unary()
        left = self.parse_binary(level + 1)
        while self.tok.kind == "op" and self.tok.value in BINARY_PRECEDENCE[level]:
            op = self.tok.value
            self.i += 1
            right = self.parse_binary(level + 1)
            left = Binary(op, left, right)
        return left

    def parse_unary(self) -> Expr:
        t = self.tok
        if t.kind == "op" and t.value in ("-", "+", "!", "~"):
            self.i += 1
            operand = self.parse_unary()
            if t.value == "-" and isinstance(operand, Num):
                return Num(-operand.value, operand.is_int)
            if t.value == "+":
                return operand
            return Unary(t.value, operand)
        if t.kind == "op" and t.value in ("++", "--"):
            self.i += 1
            return IncDec(self.parse_unary(), t.value, prefix=True)
        if t.kind == "op" and t.value == "&":
            self.i += 1
            return AddressOf(self.parse_unary())
        if t.kind == "op" and t.value == "*":
            self.i += 1
            return self.parse_unary()   # *ptr : pointer parameters are treated as plain references
        if t.value == "(" and self.is_type_start(1):
            j = self.i + 1
            while self.tokens[j].kind == "ident" and (self.tokens[j].value in TYPE_WORDS or self.tokens[j].value in QUALIFIERS or self.tokens[j].value in self.typedefs):
                j += 1
            while self.tokens[j].value == "*":
                j += 1
            if self.tokens[j].value == ")":
                self.i += 1
                _, _, typ = self.parse_type_prefix()
                while self.accept("*"):
                    pass
                self.expect(")")
                return Cast(typ, self.parse_unary())
        if t.kind == "ident" and t.value == "sizeof":
            self.error("sizeof is not supported")
        if t.kind == "ident" and t.value in TYPE_WORDS and self.peek().value == "(":   # C++ function-style cast
            self.i += 1
            self.expect("(")
            operand = self.parse_expr()
            self.expect(")")
            return Cast(TYPE_WORDS[t.value], operand)
        return self.parse_postfix()

    def parse_postfix(self) -> Expr:
        expr = self.parse_primary()
        while True:
            if self.at("("):
                if not isinstance(expr, Name):
                    self.error("calling something that is not a function name")
                self.i += 1
                args: list[Expr] = []
                while not self.at(")"):
                    args.append(self.parse_expr())
                    if not self.accept(","):
                        break
                self.expect(")")
                if expr.id == "VAR" and len(args) == 1 and isinstance(args[0], Binary):
                    # VAR(x * y) — the SDK macro `vp->var.x` only wraps the leftmost name
                    node = args[0]
                    while isinstance(node.left, Binary):
                        node = node.left
                    if isinstance(node.left, Name):
                        node.left = Call("VAR", [node.left])
                        expr = args[0]
                        continue
                if expr.id == "VAR" and len(args) == 1 and isinstance(args[0], Index):
                    indices = []
                    node = args[0]
                    while isinstance(node, Index):
                        indices.append(node.index)
                        node = node.base
                    expr = Call("VAR", [node])
                    for idx in reversed(indices):
                        expr = Index(expr, idx)
                else:
                    expr = Call(expr.id, args)
            elif self.at("["):
                self.i += 1
                index = self.parse_expr()
                self.expect("]")
                expr = Index(expr, index)
            elif self.at("++") or self.at("--"):
                op = self.tok.value
                self.i += 1
                expr = IncDec(expr, op, prefix=False)
            elif self.at("->") or self.at("."):
                self.i += 1
                member = self.ident()
                expr = self.member(expr, member)
            else:
                return expr

    def member(self, base: Expr, member: str) -> Expr:
        """`vp->var.x`, `vp->vvar`, `vp->a` … → the equivalent macro forms."""
        if isinstance(base, Name) and base.id == "vp":
            if member == "var":
                return Name("vp.var")
            if member == "vvar":
                return Name("VVAR")
            if member in ("a", "b", "c", "d", "e", "f"):
                return Call("TM", [Name(member)])
            if member == "pColor":
                return Name("TC")
            if member in ("pFTx", "pFTy", "pFTz", "pFPx", "pFPy", "pFPz"):
                return Name(member[1:])
        if isinstance(base, Name) and base.id == "vp.var":
            return Call("VAR", [Name(member)])
        if member in ("real", "imag"):
            if self.at("(") and self.peek().value == ")":
                self.i += 2
            return Call("c" + member, [base])
        self.error(f"unsupported member access .{member}")

    def parse_primary(self) -> Expr:
        t = self.tok
        if t.kind == "number":
            self.i += 1
            return _number(t.value)
        if t.kind == "string":
            self.i += 1
            return Str(t.value[1:-1])
        if t.kind == "char":
            self.i += 1
            return Num(ord(t.value[1:-1].encode().decode("unicode_escape")), True)
        if t.kind == "ident":
            self.i += 1
            return Name(t.value)
        if self.accept("("):
            expr = self.parse_expr()
            self.expect(")")
            return expr
        self.error(f"unexpected {t.value!r} in expression")


def _is_lvalue(expr: Expr) -> bool:
    """Names, array elements and `VAR(x)` plugin variables can be assigned."""
    if isinstance(expr, Name):
        return True
    if isinstance(expr, Index):
        return _is_lvalue(expr.base)
    return isinstance(expr, Call) and expr.func == "VAR" and len(expr.args) == 1 and isinstance(expr.args[0], Name)


def _number(text: str):
    if text.lower().startswith("0x"):
        return Num(int(text.rstrip("uUlL"), 16), True)
    if text.endswith("i"):   # C++14 imaginary literal: 1i, 2.5i
        return Call("Complex", [Num(0.0, False), Num(float(text[:-1]), False)])
    raw = text.rstrip("fFlLuU")
    if any(ch in raw for ch in ".eE") or text[-1] in "fF":
        return Num(float(raw), False)
    return Num(int(raw), True)


def _const_int(expr: Expr) -> int:
    if isinstance(expr, Num):
        return int(expr.value)
    if isinstance(expr, Binary) and isinstance(expr.left, Num) and isinstance(expr.right, Num):
        return int(eval(f"{expr.left.value}{expr.op}{expr.right.value}"))   # noqa: S307 - two literals
    raise ParseError("array sizes must be constant")


def parse(text: str) -> Module:
    """Parse preprocessed formula source."""
    return Parser(tokenize(text), text).parse_module()
