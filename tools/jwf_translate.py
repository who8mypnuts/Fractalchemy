"""Translate a JWildfire variation (`*Func.java`) into the Fractalchemy formula dialect.

JWildfire variations are Java classes with a regular shape:

    public class WhorlFunc extends VariationFunc implements SupportsGPU {
      private static final String PARAM_INSIDE = "inside";          // parameter names …
      private static final String[] paramNames = {PARAM_INSIDE, …};
      private double inside = 0.10;                                  // … their fields and defaults
      private double timespi;                                        // derived fields (set in init)
      public void transform(FlameTransformationContext pContext, XForm pXForm, XYZPoint pAffineTP, XYZPoint pVarTP, double pAmount) { … }
      public void init(FlameTransformationContext pContext, Layer pLayer, XForm pXForm, double pAmount) { … }
      public Object[] getParameterValues() { return new Object[]{inside, outside}; }
      public String getName() { return "whorl"; }
    }

`transform()` maps onto `PluginVarCalc` one to one (`pAffineTP.x` → `FTx`, `pVarTP.x +=` → `FPx +=`, `pAmount` →
`VVAR`, fields → `VAR(name_field)`, `pContext.random()` → `random01()`, `MathLib` → the math functions …),
`init()` / `initOnce()` onto `PluginVarPrepare`, private helper methods onto dialect functions. The translation
is token-level (Java's expression syntax *is* C's), so the formula compiler is the judge: what it rejects is
reported and left out. Things no rewrite can cover — images and resources, `Complex` / `vec2` helper classes,
code compiled at run time, sub-flames, state kept between points — are detected up front and refused with a
reason, so the report says why a variation is missing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

TOKEN = re.compile(
    r"(?P<ws>\s+)"
    r"|(?P<comment>//[^\n]*|/\*.*?\*/)"
    r"|(?P<number>0[xX][0-9A-Fa-f]+[lL]?|(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?[fFdDlL]?)"
    r"|(?P<ident>[A-Za-z_$]\w*)"
    r'|(?P<string>"(?:\\.|[^"\\])*")'
    r"|(?P<char>'(?:\\.|[^'\\])')"
    r"|(?P<op>>>>=|<<=|>>=|>>>|\+\+|--|&&|\|\||==|!=|<=|>=|\+=|-=|\*=|/=|%=|&=|\|=|\^=|<<|>>|->|::|[-+*/%=<>!&|^~?:;,.(){}\[\]@])",
    re.S)
API_METHODS = {"getName", "getParameterNames", "getParameterValues", "setParameter", "getVariationTypes", "getGPUCode", "getGPUFunctions",
               "getRessourceNames", "getRessourceValues", "setRessource", "getRessourceType", "getParameterAlternativeNames", "getPriority",
               "makeCopy", "dynamicParameterExpansion", "validate", "randomize", "mutate", "getRandomParamNames", "initOnce", "init",
               "transform", "getParameter", "getParameterDefault", "isEqual", "getParameterMin", "getParameterMax",
               "getVariationTypesAsString", "toString", "hashCode", "equals", "getCurrFlameRenderer", "getAlternativeNames",
               "getGPUVariationFuncName", "getMotionCurveNames"}
PRECALC = {
    "getPrecalcSqrt": "(sqrt(FTx * FTx + FTy * FTy) + EPS)", "getPrecalcSumsq": "(FTx * FTx + FTy * FTy)",
    "getPrecalcAtan": "atan2(FTx, FTy)", "getPrecalcAtanYX": "atan2(FTy, FTx)",
    "getPrecalcSinA": "(FTx / (sqrt(FTx * FTx + FTy * FTy) + EPS))", "getPrecalcCosA": "(FTy / (sqrt(FTx * FTx + FTy * FTy) + EPS))",
}
POINTS = {"pAffineTP": {"x": "FTx", "y": "FTy", "z": "FTz", "color": "TC"}, "pVarTP": {"x": "FPx", "y": "FPy", "z": "FPz", "color": "TC"}}
COEFFS = {"getXYCoeff00": "TM(a)", "getXYCoeff01": "TM(b)", "getXYCoeff10": "TM(c)", "getXYCoeff11": "TM(d)", "getXYCoeff20": "TM(e)",
          "getXYCoeff21": "TM(f)", "getCoeff00": "TM(a)", "getCoeff01": "TM(b)", "getCoeff10": "TM(c)", "getCoeff11": "TM(d)",
          "getCoeff20": "TM(e)", "getCoeff21": "TM(f)"}
CONSTANTS = {"EPSILON": "1.0e-8", "SMALL_EPSILON": "EPS", "M_2PI": "(2.0 * M_PI)", "M_1_2PI": "(0.5 / M_PI)", "C_255": "255.0",
             "Math.PI": "M_PI", "Math.E": "M_E", "Integer.MAX_VALUE": "INT_MAX", "Integer.MIN_VALUE": "INT_MIN",
             "Double.MAX_VALUE": "DBL_MAX", "Double.MIN_VALUE": "DBL_MIN", "Float.MAX_VALUE": "FLT_MAX"}
FUNCTION_RENAMES = {"iabs": "abs", "iMax": "max", "iMin": "min", "Math.abs": "fabs", "Math.signum": "sign", "Math.toRadians": "radians",
                    "Math.toDegrees": "degrees", "Math.hypot": "hypot", "Math.cbrt": "cbrt", "Math.expm1": "expm1", "Math.log1p": "log1p",
                    "toRadians": "radians", "toDegrees": "degrees", "signum": "sign"}
ENGINE_OBJECTS = ("FlameTransformationContext", "XForm", "Layer")
MATH_PREFIXES = ("Math.", "MathLib.", "FastMath.", "StrictMath.")
TYPE_RENAMES = {"boolean": "bool", "float": "double", "long": "int", "short": "int", "byte": "int", "Boolean": "bool", "Double": "double",
                "Integer": "int"}
UNSUPPORTED_WORDS = {"Complex": "complex-number helper class", "vec2": "GLSL vector helper classes", "vec3": "GLSL vector helper classes",
                     "vec4": "GLSL vector helper classes", "mat2": "GLSL matrix helper classes", "mat3": "GLSL matrix helper classes",
                     "String": "strings at run time", "Random": "a Random object (state between points)", "System": "System calls",
                     "RESSOURCE": "resources (images / text / code) at run time", "ressource": "resources at run time",
                     "Flame": "a sub-flame / the flame object", "pLayer": "the layer object", "Layer": "the layer object",
                     "ArrayList": "Java collections", "List": "Java collections", "HashMap": "Java collections", "Map": "Java collections",
                     "Thread": "threads", "Object": "Java objects", "Tools.": "Tools helpers", "Class": "reflection",
                     "BufferedImage": "images", "Pixel": "images", "SimpleImage": "images", "WFImage": "images", "Graphics": "images",
                     "getFlameRenderer": "the renderer", "getCurrentXForm": "the transform object", "pXForm.getXYPostCoeff": "post coefficients",
                     "DC_BaseFunc": "the DC base class", "AbstractFractWFFunc": "the escape-time base class"}
HELPERS = {
    "frac": "double frac(double v) { return v - trunc(v); }",
    "FTOI": "int FTOI(double v) { return v > 0.0 ? (int)(v + 0.5) : (v < 0.0 ? (int)(0.0 - (fabs(v) + 0.5)) : 0); }",
    "radians": "double radians(double d) { return d * M_PI / 180.0; }",
    "degrees": "double degrees(double r) { return r * 180.0 / M_PI; }",
}
BODY_FORBIDDEN = ("new ", "this.", "super.", "throw ", "try ", "catch", "instanceof", "synchronized", "static ", "->")


class Unsupported(Exception):
    """The variation uses something the dialect cannot express; `str(exc)` says what."""


@dataclass
class Member:
    """A field or method of the class at brace depth one."""
    kind: str            # field | method
    type: str
    name: str
    text: str            # the initialiser (fields) or the body without braces (methods)
    params: str = ""     # the method's parameter list
    modifiers: tuple[str, ...] = ()


@dataclass
class Translation:
    """The outcome: the dialect source plus what was learnt."""
    name: str
    source: str
    params: list[tuple[str, float, str]]      # (full name, default, real | int)
    derived: list[str]
    author: str = ""
    types: tuple[str, ...] = ()
    notes: list[str] = field(default_factory=list)


# --- tokenising -----------------------------------------------------------------------------------------------------
def tokens(text: str) -> list[tuple[str, str]]:
    """(kind, value) pairs without whitespace and comments."""
    out = []
    pos = 0
    while pos < len(text):
        m = TOKEN.match(text, pos)
        if not m:
            raise Unsupported(f"cannot tokenise near {text[pos:pos + 20]!r}")
        kind = m.lastgroup
        if kind not in ("ws", "comment"):
            out.append((kind, m.group(0)))
        pos = m.end()
    return out


def strip_comments(text: str) -> str:
    return re.sub(r"//[^\n]*|/\*.*?\*/", lambda m: "\n" * m.group(0).count("\n"), text, flags=re.S)


# --- the class ------------------------------------------------------------------------------------------------------
def class_body(text: str) -> tuple[str, str, str]:
    """(class name, base class, body between the outer braces)."""
    m = re.search(r"public\s+(?:final\s+)?class\s+(\w+)\s+extends\s+([\w.]+)(?:\s+implements\s+[\w., ]+)?\s*\{", text)
    if not m:
        raise Unsupported("no public class extending a variation base class")
    start = m.end()
    depth = 1
    i = start
    while i < len(text) and depth:
        c = text[i]
        if c == "{":
            depth += 1
        elif c == "}":
            depth -= 1
        elif c == '"':
            i = _skip_string(text, i)
        i += 1
    return m.group(1), m.group(2), text[start:i - 1]


def _skip_string(text: str, i: int) -> int:
    j = i + 1
    while j < len(text) and text[j] != '"':
        j += 2 if text[j] == "\\" else 1
    return j


def members(body: str) -> list[Member]:
    """Split the class body into fields and methods (inner classes are refused)."""
    out: list[Member] = []
    i = 0
    n = len(body)
    while i < n:
        c = body[i]
        if c.isspace():
            i += 1
            continue
        if c == "@":                                   # an annotation
            i = re.compile(r"@\w+(\([^)]*\))?").match(body, i).end()
            continue
        if c == "/":
            m = re.compile(r"//[^\n]*|/\*.*?\*/", re.S).match(body, i)
            i = m.end() if m else i + 1
            continue
        # a declaration runs to ';' (field) or to the '{' of a body (method / initialiser / inner class)
        j = i
        depth = 0
        while j < n:
            ch = body[j]
            if ch == '"':
                j = _skip_string(body, j)
            elif ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            elif ch == "=" and depth == 0 and body[j + 1:j + 2] != "=":
                break
            elif ch == ";" and depth == 0:
                break
            elif ch == "{" and depth == 0:
                break
            j += 1
        head = body[i:j].strip()
        if j >= n:
            break
        if body[j] == "=":                             # a field with an initialiser: read to the matching ';'
            k = j + 1
            d = 0
            while k < n:
                ch = body[k]
                if ch == '"':
                    k = _skip_string(body, k)
                elif ch in "({[":
                    d += 1
                elif ch in ")}]":
                    d -= 1
                elif ch == ";" and d == 0:
                    break
                k += 1
            _extend(out, _field(head, body[j + 1:k].strip()))
            i = k + 1
        elif body[j] == ";":
            if head:
                _extend(out, _field(head, ""))
            i = j + 1
        else:                                          # a body
            k = j + 1
            d = 1
            while k < n and d:
                ch = body[k]
                if ch == '"':
                    k = _skip_string(body, k)
                elif ch == "{":
                    d += 1
                elif ch == "}":
                    d -= 1
                k += 1
            inner = body[j + 1:k - 1]
            m = re.match(r"((?:\w+\s+)*)([\w\[\]<>.]+)\s+(\w+)\s*\((.*)\)\s*(?:throws\s+[\w., ]+)?$", head, re.S)
            if m is None:
                if re.search(r"\b(class|interface|enum)\b", head):
                    raise Unsupported("an inner class")
                i = k                                   # a static initialiser block: ignored
                continue
            modifiers = tuple(m.group(1).split())
            out.append(Member("method", m.group(2), m.group(3), inner, m.group(4).strip(), modifiers))
            i = k
    return out


def _extend(out: list[Member], fields) -> None:
    out.extend(fields if isinstance(fields, list) else [fields])


def _field(head: str, init: str) -> Member | list[Member]:
    if "," in head and "(" not in head:                      # `private double a, b, c;`
        first, *rest = [w.strip() for w in head.split(",")]
        base = _field(first, "")
        if not isinstance(base, Member):
            raise Unsupported("a field declaration that cannot be read")
        return [base] + [Member("field", base.type, r, "", modifiers=base.modifiers) for r in rest if r]
    words = head.replace("[]", " [] ").split()
    arrays = words.count("[]")
    words = [w for w in words if w != "[]"]               # `double[] a`, `double a[]` and `double a[][]` alike
    name = words[-1]
    type_ = words[-2] if len(words) >= 2 else "double"
    modifiers = tuple(words[:-2])
    if arrays:
        type_ += "[]" * arrays
    return Member("field", type_, name, init, modifiers=modifiers)


# --- the parameter table --------------------------------------------------------------------------------------------
def parameter_table(ms: list[Member], body: str) -> tuple[list[str], dict[str, str]]:
    """(parameter names in order, parameter name → field name) from `paramNames` and `getParameterValues()`."""
    strings = {m.name: m.text.strip('"') for m in ms if m.kind == "field" and m.type == "String" and m.text.startswith('"')}
    names_member = next((m for m in ms if m.kind == "field" and m.name in ("paramNames", "additionalParamNames") and "{" in m.text), None)
    names: list[str] = []
    if names_member is not None:
        inner = names_member.text[names_member.text.index("{") + 1:names_member.text.rindex("}")]
        for item in inner.split(","):
            item = item.strip()
            if not item:
                continue
            names.append(strings.get(item, item.strip('"')))
    values = next((m for m in ms if m.kind == "method" and m.name == "getParameterValues"), None)
    fields: list[str] = []
    if values is not None:
        m = re.search(r"\{(.*)\}", values.text, re.S)
        if m:
            fields = [f.strip() for f in m.group(1).split(",") if f.strip()]
    mapping: dict[str, str] = {}
    if fields and len(fields) == len(names):
        for name, expr in zip(names, fields):
            fm = re.fullmatch(r"\(?\s*(?:\(\s*\w+\s*\)\s*)?(\w+)\s*\)?", expr)
            if fm is None:
                raise Unsupported(f"parameter {name} is not a plain field ({expr})")
            mapping[name] = fm.group(1)
    else:
        for name in names:
            mapping[name] = name
    return names, mapping


def literal(text: str) -> float | None:
    """A numeric literal / simple constant expression as a number, or None."""
    expr = text.strip().rstrip("fFdDlL") if re.fullmatch(r"[-+]?(?:\d+\.\d*|\.\d+|\d+)(?:[eE][-+]?\d+)?[fFdDlL]?", text.strip()) else text.strip()
    expr = re.sub(r"\b(\d+\.\d*|\.\d+|\d+(?:[eE][-+]?\d+)?)[fFdDlL]\b", r"\1", expr)
    expr = expr.replace("M_PI", "3.141592653589793").replace("Math.PI", "3.141592653589793").replace("M_2PI", "6.283185307179586")
    if expr in ("true", "false"):
        return 1.0 if expr == "true" else 0.0
    if not re.fullmatch(r"[-+*/().\d eE]+", expr):
        return None
    try:
        return float(eval(expr, {"__builtins__": {}}, {}))  # noqa: S307 - digits and operators only
    except Exception:  # noqa: BLE001
        return None


# --- rewriting a body -----------------------------------------------------------------------------------------------
def rewrite(body: str, fields: dict[str, str], helpers: set[str], locals_: set[str] | None = None) -> str:
    """A Java method body as dialect text: the point / context / math rewrites, fields as `VAR(full)`."""
    body = re.sub(r"\bthis\s*\.\s*", "", body)
    for word, why in UNSUPPORTED_WORDS.items():
        if re.search(r"(?<![\w.])" + re.escape(word) + r"(?![\w])", body) if "." not in word else word in body:
            raise Unsupported(why)
    for word in BODY_FORBIDDEN:
        if word == "new ":
            if re.search(r"\bnew\s+(?!double\b|int\b|float\b|long\b|boolean\b|DoubleWrapper\w*\b)", body):
                raise Unsupported("uses 'new' (an object)")
            continue
        if word in body:
            raise Unsupported(f"uses {word.strip()!r}")
    toks = tokens(body)
    out: list[str] = []
    i = 0
    n = len(toks)
    declared_locals: set[str] = set(locals_ or ())

    def peek(k: int) -> tuple[str, str]:
        return toks[i + k] if i + k < n else ("", "")

    while i < n:
        kind, value = toks[i]
        if kind == "string" or kind == "char":
            raise Unsupported("strings at run time")
        if kind == "number":
            value = value.rstrip("fFdDlL") if not value.lower().startswith("0x") else value.rstrip("lL")
            out.append(value)
            i += 1
            continue
        if kind == "op" and value == "@":
            i += 2
            continue
        if kind == "ident":
            nxt = peek(1)
            # point state and context
            if value in POINTS and nxt == ("op", "."):
                member = peek(2)[1]
                if member in PRECALC:
                    out.append(PRECALC[member].replace("FT", "FT" if value == "pAffineTP" else "FP"))
                    i += 5                     # ident . name ( )
                    continue
                if member in POINTS[value]:
                    out.append(POINTS[value][member])
                    i += 3
                    continue
                raise Unsupported(f"point member {member}")
            if value == "pAmount":
                out.append("VVAR")
                i += 1
                continue
            if value in ("pContext", "pXForm", "pLayer", "pVarTP", "pAffineTP") and nxt[1] in (",", ")") and out and out[-1] in ("(", ","):
                if nxt[1] == ",":
                    i += 2                         # the argument and its comma
                else:
                    if out[-1] == ",":
                        out.pop()
                    i += 1
                continue
            if value == "pContext" and nxt == ("op", "."):
                member = peek(2)[1]
                if member == "random" and peek(3) == ("op", "(") and peek(4) == ("op", ")"):
                    out.append("random01()")
                    i += 5
                    continue
                if member == "random" and peek(3) == ("op", "("):
                    out.append("(int)(random01() * ")
                    i += 4
                    continue
                if member == "isPreserveZCoordinate":
                    out.append("FALSE")
                    i += 5
                    continue
                raise Unsupported(f"context call {member}")
            if value == "pXForm" and nxt == ("op", "."):
                member = peek(2)[1]
                if member in COEFFS:
                    out.append(COEFFS[member])
                    i += 5
                    continue
                raise Unsupported(f"transform call {member}")
            if value.startswith("DoubleWrapper"):
                out.append("double")
                i += 1
                if peek(0) == ("op", "(") and peek(1) == ("op", ")"):     # `new DoubleWrapper()` → nothing
                    i += 2
                continue
            if value in ("Tools", "Math", "MathLib", "FastMath", "StrictMath", "Double", "Integer", "Float", "Long") and nxt == ("op", "."):
                qualified = f"{value}.{peek(2)[1]}"
                if peek(2)[1] == "sinAndCos":
                    i += 2                         # handled below, unqualified
                    continue
                if value in ("Double", "Integer", "Float", "Long") and qualified not in CONSTANTS:
                    raise Unsupported(f"{qualified}")
                if qualified in CONSTANTS:
                    out.append(CONSTANTS[qualified])
                    i += 3
                    continue
                if qualified in FUNCTION_RENAMES:
                    fn = FUNCTION_RENAMES[qualified]
                    if fn in HELPERS:
                        helpers.add(fn)
                    out.append(fn)
                    i += 3
                    continue
                if value == "Tools" and peek(2)[1] == "FTOI":
                    helpers.add("FTOI")
                    out.append("FTOI")
                    i += 3
                    continue
                if value == "Tools":
                    raise Unsupported(f"Tools.{peek(2)[1]}")
                out.append(peek(2)[1])             # Math.sin → sin
                i += 3
                continue
            if value in CONSTANTS:
                out.append(CONSTANTS[value])
                i += 1
                continue
            if value in FUNCTION_RENAMES:
                out.append(FUNCTION_RENAMES[value])
                i += 1
                continue
            if value in HELPERS and nxt == ("op", "("):
                helpers.add(value)
                out.append(value)
                i += 1
                continue
            if value == "sinAndCos":                   # sinAndCos(a, s, c) → fsincos(a, &s, &c)
                out.append("fsincos")
                i += 1
                j = i                                  # at the opening parenthesis
                depth = 0
                commas = []
                while j < n:
                    k2, v2 = toks[j]
                    if v2 == "(":
                        depth += 1
                    elif v2 == ")":
                        depth -= 1
                        if depth == 0:
                            break
                    elif v2 == "," and depth == 1:
                        commas.append(j)
                    j += 1
                if len(commas) != 2:
                    raise Unsupported("sinAndCos with an unexpected argument list")
                toks[commas[0] + 1:commas[0] + 1] = [("op", "&")]
                toks[commas[1] + 2:commas[1] + 2] = [("op", "&")]
                n = len(toks)
                continue
            if value in TYPE_RENAMES:
                out.append(TYPE_RENAMES[value])
                i += 1
                continue
            if value == "final":
                i += 1
                continue
            if value == "new":                         # new double[3] → handled by the array rewrite below
                i += 1
                continue
            if value == "value" and out and out[-1] == ".":   # DoubleWrapper.value
                out.pop()
                i += 1
                continue
            if value in fields and nxt != ("op", "(") and value not in declared_locals:
                out.append(f"VAR({fields[value]})")
                i += 1
                continue
            if value in ("double", "int", "bool", "boolean", "float", "long") and peek(1)[0] == "ident":
                declared_locals.add(peek(1)[1])
            out.append(value)
            i += 1
            continue
        out.append(value)
        i += 1
    text = _join(out)
    text = _arrays(text)
    text = re.sub(r"\s*=\s*double\s*;", ";", text)          # `DoubleWrapper s = new DoubleWrapper();` → `double s;`
    text = _drop_dead_branches(text)
    return text


def _drop_dead_branches(text: str) -> str:
    """`if (FALSE) { … }` (the preserve-z blocks) disappear — with their `else` branch promoted — so a 2D variation
    does not end up writing the depth."""
    while True:
        m = re.search(r"if\s*\(\s*FALSE\s*\)\s*", text)
        if not m:
            return text
        j = m.end()
        if text[j:j + 1] == "{":
            depth = 0
            k = j
            while k < len(text):
                if text[k] == "{":
                    depth += 1
                elif text[k] == "}":
                    depth -= 1
                    if depth == 0:
                        break
                k += 1
            end = k + 1
        else:
            end = text.index(";", j) + 1
        rest = text[end:]
        em = re.match(r"\s*else\s*", rest)
        if em:
            rest = rest[em.end():]
            if rest.startswith("{"):                       # the else body stays, unwrapped
                depth, k = 0, 0
                while k < len(rest):
                    if rest[k] == "{":
                        depth += 1
                    elif rest[k] == "}":
                        depth -= 1
                        if depth == 0:
                            break
                    k += 1
                rest = rest[1:k] + rest[k + 1:]
        text = text[:m.start()] + rest


def _join(parts: list[str]) -> str:
    """Tokens back to text with sensible spacing and line breaks after ';', '{' and '}'."""
    out = []
    indent = 1
    at_line_start = True
    for k, p in enumerate(parts):
        if p == "}":
            indent = max(1, indent - 1)
            out.append("\n" + "    " * indent + "}")
            following = parts[k + 1] if k + 1 < len(parts) else ""
            at_line_start = following not in ("else", "while", ";", ",", ")")
            continue
        if at_line_start:
            out.append("\n" + "    " * indent + p)
            at_line_start = False
        elif p in (";", ",", ")", "]", "++", "--") or (out and out[-1].endswith(("(", "[", "!", "~"))):
            out.append(p)
        elif p in ("(", "[") and out and re.search(r"[\w)\]]$", out[-1]):
            out.append(p)
        else:
            out.append(" " + p)
        if p == "{":
            indent += 1
            at_line_start = True
        elif p == ";":
            at_line_start = True
    return "".join(out)


def _arrays(text: str) -> str:
    """Java array syntax → C: `double[] a = new double[3];` → `double a[3];`, `int[] b = {…}` → `int b[] = {…}`."""
    text = re.sub(r"\b(double|int|bool)\s*\[\s*\]\s*\[\s*\]\s*(\w+)\s*=\s*(?:new\s+)?(?:double|int|bool)\s*\[\s*(\w+)\s*\]\s*\[\s*(\w+)\s*\]\s*;",
                  r"\1 \2[\3][\4];", text)
    text = re.sub(r"\b(double|int|bool)\s*\[\s*\]\s*(\w+)\s*=\s*(?:new\s+)?(?:double|int|bool)\s*\[\s*(\w+)\s*\]\s*;", r"\1 \2[\3];", text)
    text = re.sub(r"\b(double|int|bool)\s*\[\s*\]\s*(\w+)\s*=\s*(?:new\s+(?:double|int|bool)\s*\[\s*\]\s*)?\{", r"\1 \2[] = {", text)
    text = re.sub(r"\b(double|int|bool)\s*\[\s*\]\s*(\w+)\s*;", r"\1 \2[1];", text)
    # the C-style spelling `double P[][] = new double[9][2];` (the `new` token is gone already)
    text = re.sub(r"\b(double|int|bool)\s+(\w+)\s*\[\s*\]\s*\[\s*\]\s*=\s*(?:double|int|bool)\s*\[\s*(\w+)\s*\]\s*\[\s*(\w+)\s*\]\s*;",
                  r"\1 \2[\3][\4];", text)
    text = re.sub(r"\b(double|int|bool)\s+(\w+)\s*\[\s*\]\s*=\s*(?:double|int|bool)\s*\[\s*(\w+)\s*\]\s*;", r"\1 \2[\3];", text)
    return text


# --- the whole translation --------------------------------------------------------------------------------------------
def translate(java: str, file_name: str = "") -> Translation:
    """The dialect source for one `*Func.java`; raises `Unsupported` when it cannot be expressed."""
    clean = strip_comments(java)
    author = find_author(java)
    includes = ["#define _x_ 0", "#define _y_ 1", "#define _z_ 2", '#include "../ports/voronoi.h"'] if "VoronoiTools" in java else []
    cls, base, body = class_body(clean)
    if base not in ("VariationFunc", "SimpleVariationFunc"):
        raise Unsupported(f"extends {base} (a specialised base class)")
    ms = members(body)
    name_member = next((m for m in ms if m.kind == "method" and m.name == "getName"), None)
    m = re.search(r'return\s+"([^"]+)"', name_member.text) if name_member else None
    if not m:
        raise Unsupported("no getName()")
    name = m.group(1)
    if not re.fullmatch(r"[A-Za-z_]\w*", name):
        raise Unsupported(f"name {name!r} is not an identifier")
    types = tuple(re.findall(r"VARTYPE_([A-Z_0-9]+)", clean))
    for forbidden, why in (("SUPPORTS_EXTERNAL_SHAPES", "external shapes (images / fonts / flames)"), ("EDIT_FORMULA", "code compiled at run time"),
                           ("PREPOST", "a pre+post variation (JWildfire's prepost concept)")):
        if forbidden in types:
            raise Unsupported(why)
    param_names, mapping = parameter_table(ms, body)
    field_members = {m.name: m for m in ms if m.kind == "field" and "static" not in m.modifiers and m.type != "String"}
    buffers: dict[str, str] = {}                                   # `double[] _r = new double[4]` scratch buffers: locals of the body
    for m in ms:
        if m.kind == "field" and "static" not in m.modifiers and m.type.endswith("[]") and re.fullmatch(r"new\s+\w+\s*((\[\s*\d+\s*\])+)", m.text.strip()):
            dims = re.search(r"new\s+\w+\s*((\[\s*\d+\s*\])+)", m.text.strip()).group(1).replace(" ", "")
            buffers[m.name] = f"{TYPE_RENAMES.get(m.type.rstrip('[]'), m.type.rstrip('[]'))} {m.name}{dims};"
            del field_members[m.name]
    scratch = [m.name for m in field_members.values() if m.type.startswith("DoubleWrapper")]   # sin / cos outputs kept as fields
    for name_ in scratch:
        del field_members[name_]
    for fm in field_members.values():
        if fm.type not in ("double", "int", "float", "long", "boolean", "short", "byte"):
            if fm.type.endswith("[]"):
                raise Unsupported(f"array field {fm.name} (state between points)")
            raise Unsupported(f"field {fm.name} of type {fm.type}")
    full = {fname: f"{name}_{pname}" for pname, fname in mapping.items()}
    for fname in field_members:
        full.setdefault(fname, f"{name}_{fname}")
    transform = next((m for m in ms if m.kind == "method" and m.name == "transform"), None)
    if transform is None:
        raise Unsupported("no transform()")
    inits = [m for m in ms if m.kind == "method" and m.name in ("init", "initOnce") and m.text.strip()]
    assigned_in_transform = set(re.findall(r"(?<![\w.])(\w+)\s*(?:=(?!=)|\+=|-=|\*=|/=|\+\+|--)", transform.text))
    assigned_in_transform |= set(re.findall(r"(?:\+\+|--)\s*(\w+)", transform.text))
    local_names = set(re.findall(r"\b(?:double|int|float|long|boolean)\s+([A-Za-z_]\w*)", transform.text))
    local_names |= set(re.findall(r"\b(?:double|int|float|long|boolean)\s+\w+\s*(?:=[^,;]*)?,\s*([A-Za-z_]\w*)", transform.text))
    assigned_in_transform -= local_names
    state = [f for f in field_members if f in assigned_in_transform and f not in mapping.values()]
    if state:
        raise Unsupported(f"keeps state between points ({', '.join(sorted(state)[:3])})")
    if any(p in assigned_in_transform for p in mapping.values()):
        raise Unsupported("rewrites its parameters while running")
    helpers: set[str] = set()

    def body_of(member: Member) -> str:
        used = [n for n in scratch if re.search(rf"\b{re.escape(n)}\b", member.text)]
        used_buffers = [n for n in buffers if re.search(rf"\b{re.escape(n)}\b", member.text)]
        prefix = "".join(f"\n    double {n};" for n in used) + "".join(f"\n    {buffers[n]}" for n in used_buffers)
        return prefix + rewrite(member.text, full, helpers, set(used) | set(used_buffers))

    calc = body_of(transform)
    prepare = "".join(body_of(m) for m in inits)
    functions = []
    for m in ms:
        if m.kind != "method" or m.name in API_METHODS or m.name in ("transform", "init", "initOnce"):
            continue
        if "static" in m.modifiers and m.type == "void" and not m.params:
            continue
        if any(word in m.params for word in ("String", "Object")):
            raise Unsupported(f"helper {m.name}() takes engine objects")
        if re.search(r"XYZPoint\s+(?!pVarTP\b|pAffineTP\b)", m.params):
            raise Unsupported(f"helper {m.name}() takes a point of its own")
        ret = TYPE_RENAMES.get(m.type, m.type)
        if ret not in ("double", "int", "bool", "void"):
            raise Unsupported(f"helper {m.name}() returns {m.type}")
        params = []
        for p in (m.params.split(",") if m.params.strip() else []):
            words = p.replace("final", "").split()
            if words and (words[0] in ENGINE_OBJECTS or words[0] == "XYZPoint"):
                continue                           # the context / transform / point argument: dropped at the call sites too
            if len(words) != 2 or words[0] not in TYPE_RENAMES and words[0] not in ("double", "int"):
                raise Unsupported(f"helper {m.name}() has a parameter {p.strip()!r}")
            params.append(f"{TYPE_RENAMES.get(words[0], words[0])} {words[1]}")
        body_text = rewrite(m.text, full, helpers, set(w.split()[1] for w in params))
        functions.append(f"{ret} {m.name}({', '.join(params)})\n{{{body_text}\n}}\n")
    constants = []
    for m in ms:
        if m.kind != "field" or "static" not in m.modifiers or not m.text or m.name == "serialVersionUID":
            continue
        base = m.type.rstrip("[]")
        if base not in ("double", "int", "float", "long"):
            continue
        if m.type.endswith("[]"):                                   # a constant table
            init = re.sub(r"^\s*new\s+\w+\s*(\[\s*\w*\s*\])+\s*", "", m.text.strip())
            dims = "[]" * m.type.count("[]")
            value = rewrite(init, {}, helpers).strip()
            constants.append(f"static const {TYPE_RENAMES.get(base, base)} {m.name}{dims} = {value};")
        else:
            value = rewrite(m.text, {}, helpers).strip()
            constants.append(f"#define {m.name} ({value})")
    params_out: list[tuple[str, float, str]] = []
    for pname in param_names:
        fname = mapping[pname]
        fm = field_members.get(fname)
        if fm is None:
            raise Unsupported(f"parameter {pname} has no field")
        default = literal(fm.text) if fm.text else 0.0
        if default is None:
            raise Unsupported(f"default of {pname} is not a constant ({fm.text})")
        params_out.append((full[fname], default, "int" if TYPE_RENAMES.get(fm.type, fm.type) == "int" else "real"))
    derived = [full[f] for f in field_members if f not in mapping.values()]
    source = _emit(name, params_out, derived, field_members, full, includes + constants, [HELPERS[h] for h in sorted(helpers)] + functions,
                   prepare, calc)
    source = _size_array_params(source)
    return Translation(name, source, params_out, derived, author, types)


def _size_array_params(source: str) -> str:
    """GLSL needs sized array parameters: `double V[]` in a helper takes the size of what the callers pass (`P[i]` of a
    `double P[9][2]` → 2, `U` of a `double U[2]` → 2)."""
    declared = {m.group(2): [d for d in re.findall(r"\[\s*(\w+)\s*\]", m.group(3))]
                for m in re.finditer(r"\b(double|int|bool)\s+(\w+)((?:\s*\[\s*\w+\s*\])+)\s*(?:;|=)", source)}
    for m in list(re.finditer(r"\b(double|int|bool|void)\s+(\w+)\s*\(([^)]*)\)", source)):
        fname, params = m.group(2), m.group(3)
        unsized = [(i, pm.group(1), pm.group(2)) for i, pm in enumerate(re.finditer(r"(?:^|,)\s*(\w+)\s+(\w+)\s*\[\s*\]", params)) if pm]
        if not unsized:
            continue
        param_list = [p.strip() for p in params.split(",")]
        positions = [i for i, p in enumerate(param_list) if re.search(r"\[\s*\]\s*$", p)]
        sizes: dict[int, str] = {}
        for call in re.finditer(rf"\b{re.escape(fname)}\s*\(([^;]*?)\)\s*;", source):
            args = [a.strip() for a in call.group(1).split(",")]
            for pos in positions:
                if pos >= len(args) or pos in sizes:
                    continue
                arg = args[pos]
                am = re.fullmatch(r"(\w+)((?:\s*\[[^\]]+\])*)", arg)
                if am and am.group(1) in declared:
                    dims = declared[am.group(1)]
                    used = len(re.findall(r"\[", am.group(2) or ""))
                    if used < len(dims):
                        sizes[pos] = dims[used]
        if len(sizes) != len(positions):
            continue
        new_params = [re.sub(r"\[\s*\]\s*$", f"[{sizes[i]}]", p) if i in sizes else p for i, p in enumerate(param_list)]
        source = source.replace(m.group(0), f"{m.group(1)} {fname}({', '.join(new_params)})", 1)
    return source


def _emit(name, params, derived, field_members, full, constants, functions, prepare, calc) -> str:
    members_text = ""
    for fname, fm in field_members.items():
        ctype = "int" if TYPE_RENAMES.get(fm.type, fm.type) == "int" else "double"
        members_text += f"    {ctype} {full[fname]};\n"
    lines = []
    if members_text:
        lines.append(f"typedef struct {{\n{members_text}}} Variables;\n")
    lines.append('#include "apoplugin.h"\n')
    lines.append(f'APO_PLUGIN("{name}");\n')
    if params:
        entries = ",\n".join(f"    {'VAR_INTEGER' if kind == 'int' else 'VAR_REAL'}({pname}, {default:g})" for pname, default, kind in params)
        lines.append(f"APO_VARIABLES(\n{entries}\n);\n")
    else:
        lines.append("APO_NOVARIABLES;\n")
    lines.extend(constants)
    if constants:
        lines.append("")
    lines.extend(functions)
    lines.append(f"int PluginVarPrepare(Variation* vp)\n{{{prepare}\n    return TRUE;\n}}\n")
    lines.append(f"int PluginVarCalc(Variation* vp)\n{{{calc}\n    return TRUE;\n}}\n")
    return "\n".join(lines)


def find_author(java: str) -> str:
    """The author a variation's comments name (beyond JWildfire's own copyright line)."""
    head = java[:6000].split("getGPUCode")[0]          # (the CUDA translations credit their own author)
    for pattern in (r"(?:Autor|Author|Written by|Created by|Ported (?:to JWildfire )?by|Variation by|Coded by|Based on code by)\s*:?\s+([A-Z][\w.\- ]{2,40}?)(?=[\n,.(]| and | with |$)",
                    r"\*\s+([A-Z][a-z]+ [A-Z][a-z]+(?: [A-Z][a-z]+)?)\s*\n"):
        m = re.search(pattern, head)
        if m:
            name = m.group(1).strip()
            words = name.split()
            if (re.fullmatch(r"[A-Z][a-z]+(?: (?:[A-Z][a-z]+|[A-Z]\.)){1,2}", name) and name not in ("Andreas Maschke", "Free Software")
                    and words[-1] not in ("Function", "Attractor", "Variation", "Shell", "Plugin", "Formula", "Fractal", "Curve", "Set")):
                return name
    return ""


__all__ = ["translate", "Translation", "Unsupported", "find_author", "tokens", "rewrite", "members"]
