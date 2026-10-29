"""Writing helpers of the Formula Editor, Qt-free: templates, snippets, the variable and rename refactors, test rigs.

Everything here works on the source *text* (the editor owns the widget) or builds plain scene objects:

    new_formula_text("my_fx", "pre")          # a pre_ skeleton named pre_my_fx
    add_variable(text, "power", 2.0)          # struct member + APO_VARIABLES entry added; returns (text, "VAR(my_fx_power)")
    rename_formula(text, "whorl", "whorl_mine")   # APO_PLUGIN and every whorl_… identifier
    test_rig("julia pair")                    # a small flame for trying the formula on
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass
from typing import Callable

from ..fractal.scene import Camera, Flame, XForm
from ..model import Gradient
from .workbench import DEFAULT_NEW_NAME, SCRATCH_NAME, formula_name, formula_xform, safe_file_name

HEADER = '''\
/*
    {name} — a Fractalchemy formula (Apophysis plugin dialect).

    FTx / FTy / FTz   the incoming point (after the transform's affine)
    FPx / FPy / FPz   the result: add your contribution to it
    VVAR              the formula's weight on the transform
    VAR(name)         one of the variables declared below
    TC                the point colour (0..1); writing it makes a direct-colour formula

    A name starting with pre_ rewrites FTx / FTy before the other variations,
    post_ rewrites FPx / FPy after them. See docs/formulas.md for the whole dialect.
*/
'''

VARIABLES_BLOCK = '''\
typedef struct {{
{members}}} Variables;

#include "apoplugin.h"

APO_PLUGIN("{name}");

APO_VARIABLES(
{entries}
);
'''

PREPARE_BLOCK = '''\
// Once per transform: derive constants from the variables (optional).
int PluginVarPrepare(Variation* vp)
{{
{body}    return TRUE;
}}
'''

CALC_BLOCK = '''\
// Once per point.
int PluginVarCalc(Variation* vp)
{{
{body}    return TRUE;
}}
'''


@dataclass(frozen=True)
class Template:
    """One *New formula* starting point."""
    key: str
    title: str
    description: str
    prefix: str                       # pre_ / post_ / "" — prepended to the chosen name
    variables: tuple[tuple[str, float], ...]
    prepare: str
    calc: str


TEMPLATES: tuple[Template, ...] = (
    Template("normal", "Normal (swirl)", "Adds to the accumulator: the usual kind of variation.", "", (("amount", 1.0),), "",
             "    double r2 = FTx * FTx + FTy * FTy;\n    double s, c;\n    fsincos(r2 * VAR({n}_amount), &s, &c);\n\n"
             "    FPx += VVAR * (FTx * c - FTy * s);\n    FPy += VVAR * (FTx * s + FTy * c);\n"),
    Template("pre", "Pre (rewrites the input)", "A pre_ formula changes FTx / FTy before the other variations run.", "pre_",
             (("scale", 0.5),), "",
             "    FTx = FTx * VAR({n}_scale);\n    FTy = FTy * VAR({n}_scale);\n"),
    Template("post", "Post (rewrites the result)", "A post_ formula changes FPx / FPy after the other variations ran.", "post_",
             (("angle", 45.0),), "    VAR({n}_s) = sin(VAR({n}_angle) * M_PI / 180.0);   // derived: a struct member set once per transform\n"
             "    VAR({n}_c) = cos(VAR({n}_angle) * M_PI / 180.0);\n",
             "    double x = FPx, y = FPy;\n    FPx = x * VAR({n}_c) - y * VAR({n}_s);\n    FPy = x * VAR({n}_s) + y * VAR({n}_c);\n"),
    Template("dc", "Direct colour", "Writes TC, the point colour (blended by the transform's var_color).", "", (("speed", 1.0),), "",
             "    double r = sqrt(FTx * FTx + FTy * FTy);\n    FPx += VVAR * FTx;\n    FPy += VVAR * FTy;\n"
             "    TC = fmod(r * VAR({n}_speed), 1.0);\n"),
    Template("3d", "3D (sets the depth)", "Writes FPz as well, so the transform is a real 3D one.", "", (("height", 1.0),), "",
             "    double r2 = FTx * FTx + FTy * FTy;\n    FPx += VVAR * FTx;\n    FPy += VVAR * FTy;\n"
             "    FPz += VVAR * VAR({n}_height) * (1.0 - r2);\n"),
    Template("blur", "Blur (random)", "Uses random01(): a blur, marked random so the engines are not compared point-for-point.", "",
             (("spread", 0.5),), "",
             "    double a = random01() * 2.0 * M_PI;\n    double r = VAR({n}_spread) * (random01() + random01() - 1.0);\n"
             "    double s, c;\n    fsincos(a, &s, &c);\n    FPx += VVAR * (FTx + r * c);\n    FPy += VVAR * (FTy + r * s);\n"),
)
TEMPLATES_BY_KEY = {t.key: t for t in TEMPLATES}


def new_formula_text(name: str = DEFAULT_NEW_NAME, kind: str = "normal") -> str:
    """The boilerplate of a new formula of `kind` (a `TEMPLATES` key) named `name` (made a valid identifier)."""
    template = TEMPLATES_BY_KEY.get(kind, TEMPLATES[0])
    base = safe_file_name(name)
    if template.prefix and not base.startswith(template.prefix):
        base = template.prefix + base
    stem = base[len(template.prefix):] if template.prefix else base
    derived = "".join(f"    double {stem}_{m};\n" for m in ("s", "c")) if "VAR({n}_s)" in template.prepare else ""
    members = "".join(f"    double {stem}_{v};\n" for v, _d in template.variables) + derived
    entries = ",\n".join(f"    VAR_REAL({stem}_{v}, {d:g})" for v, d in template.variables)
    text = HEADER.format(name=base) + "\n" + VARIABLES_BLOCK.format(name=base, members=members, entries=entries) + "\n"
    text += PREPARE_BLOCK.format(body=template.prepare.replace("{n}", stem)) + "\n" + CALC_BLOCK.format(body=template.calc.replace("{n}", stem))
    return text


# --- snippets ---------------------------------------------------------------------------------------------------
@dataclass(frozen=True)
class Snippet:
    """A piece of dialect inserted at the cursor."""
    title: str
    text: str
    description: str = ""


SNIPPETS: tuple[Snippet, ...] = (
    Snippet("Polar coordinates", "double r = sqrt(FTx * FTx + FTy * FTy);\ndouble a = atan2(FTy, FTx);\n", "r and the angle of the input point"),
    Snippet("sin / cos of an angle", "double s, c;\nfsincos(a, &s, &c);\n", "both at once, as the SDK does"),
    Snippet("Add the input (linear)", "FPx += VVAR * FTx;\nFPy += VVAR * FTy;\n", "the identity contribution"),
    Snippet("Random number", "double u = random01();\n", "uniform in [0, 1) — makes the formula a random one"),
    Snippet("Guard a division", "double d = r2 < EPS ? EPS : r2;\n", "avoid dividing by zero at the origin"),
    Snippet("Derived constant (prepare)", "VAR({n}_k) = 1.0 / (VAR({n}_amount) + EPS);   // declare {n}_k in the struct only: computed once per transform\n",
            "a struct member PluginVarPrepare fills"),
    Snippet("Direct colour", "TC = fmod(fabs(r), 1.0);\n", "write the point colour"),
    Snippet("Depth (3D)", "FPz += VVAR * FTz;\n", "pass the depth through"),
    Snippet("Include the noise library", '#include "noiseb.h"\n', "the simplex / Perlin noise helpers next to crackle"),
)


def snippet_text(snippet: Snippet, text: str) -> str:
    """The snippet with `{n}` replaced by the formula's stem (its name without a pre_ / post_ prefix)."""
    return snippet.text.replace("{n}", stem_of(formula_name(text) or DEFAULT_NEW_NAME))


def stem_of(name: str) -> str:
    """The formula name without a `pre_` / `post_` prefix — what its variables are prefixed with."""
    for prefix in ("pre_", "post_"):
        if name.startswith(prefix) and len(name) > len(prefix):
            return name[len(prefix):]
    return name


# --- refactors -------------------------------------------------------------------------------------------------
_STRUCT = re.compile(r"typedef\s+struct\s*\{(.*?)\}\s*Variables\s*;", re.S)
_APO_VARIABLES = re.compile(r"APO_VARIABLES\s*\((.*?)\)\s*;", re.S)
_APO_PLUGIN = re.compile(r'(APO_PLUGIN\s*\(\s*")([^"]*)("\s*\))')
_NOVARIABLES = re.compile(r"APO_NOVARIABLES\s*;?\s*\n?")

VARIABLE_MACROS = {"real": "VAR_REAL", "int": "VAR_INTEGER", "real_range": "VAR_REAL_RANGE", "int_range": "VAR_INTEGER_RANGE"}


def declared_variables(text: str) -> list[str]:
    """The variable names the text declares (`VAR_REAL(name, …)` and friends), in order."""
    return re.findall(r"\bVAR_(?:REAL|INTEGER|BOOL)(?:_RANGE|_NONZERO|_CYCLE)?\s*\(\s*([A-Za-z_]\w*)", text)


def add_variable(text: str, short_name: str, default: float = 1.0, kind: str = "real",
                 bounds: tuple[float, float] | None = None) -> tuple[str, str]:
    """Declare a variable in both places at once: the `Variables` struct and `APO_VARIABLES` (created when missing).

    `short_name` is prefixed with the formula's stem (`power` → `julia_power`); `kind` is `real` / `int`, with
    `bounds` the `_RANGE` forms are used. Returns the new text and the `VAR(...)` expression to insert at the cursor.

    Raises:
        ValueError: When the name is not a C identifier or is declared already.
    """
    short_name = short_name.strip()
    if not re.fullmatch(r"[A-Za-z_]\w*", short_name):
        raise ValueError(f"{short_name!r} is not a valid variable name")
    stem = stem_of(formula_name(text) or DEFAULT_NEW_NAME)
    name = short_name if short_name.startswith(stem + "_") else f"{stem}_{short_name}"
    if name in declared_variables(text):
        raise ValueError(f"{name} is declared already")
    macro = VARIABLE_MACROS["real_range" if bounds and kind == "real" else "int_range" if bounds else kind]
    value = f"{int(default)}" if kind == "int" else f"{default:g}"
    entry = f"    {macro}({name}, " + (f"{bounds[0]:g}, {bounds[1]:g}, {value})" if bounds else f"{value})")   # SDK order: min, max, default
    ctype = "int" if kind == "int" else "double"
    member = f"    {ctype} {name};\n"
    struct = _STRUCT.search(text)
    if struct:
        text = text[:struct.start(1)] + struct.group(1).rstrip() + "\n" + member + text[struct.end(1):]
    else:
        text = f"typedef struct {{\n{member}}} Variables;\n\n" + text
    block = _APO_VARIABLES.search(text)
    if block:
        body = block.group(1).rstrip()
        body = (body + ",\n" if body.strip() else "\n") + entry + "\n"
        text = text[:block.start(1)] + body + text[block.end(1):]
    else:
        text = _NOVARIABLES.sub("", text)
        plugin = _APO_PLUGIN.search(text)
        declaration = f"\nAPO_VARIABLES(\n{entry}\n);\n"
        text = text[:plugin.end()] + ";\n" + declaration + text[plugin.end() + 1:] if plugin and text[plugin.end():plugin.end() + 1] == ";" \
            else text + declaration
    return text, f"VAR({name})"


def rename_formula(text: str, old: str, new: str, variables: bool = True) -> str:
    """Rename the formula: `APO_PLUGIN("old")` becomes `new`, and with `variables` every identifier starting with the
    old stem's prefix (`whorl_inside` → `whorl_mine_inside`) follows, so the parameters stay conventionally named."""
    new = safe_file_name(new)
    if variables:
        old_stem, new_stem = stem_of(old), stem_of(new)
        if old_stem and old_stem != new_stem:
            text = re.sub(rf"\b{re.escape(old_stem)}_(?=\w)", f"{new_stem}_", text)   # (before the name: the new name may extend the old)
    return _APO_PLUGIN.sub(lambda m: f"{m.group(1)}{new}{m.group(3)}", text, count=1)


def derived_name(base: str, taken: set[str], suffix: str = "_mine") -> str:
    """`base_mine`, then `base_mine2`, `base_mine3` … — the first not in `taken`."""
    name, n = f"{base}{suffix}", 1
    while name in taken:
        n += 1
        name = f"{base}{suffix}{n}"
    return name


# --- test rigs and gradients ------------------------------------------------------------------------------------
RIG_WIDTH, RIG_HEIGHT = 400, 300
TRANSFORM_COLORS = (0.0, 0.5, 1.0, 0.25, 0.75)   # palette positions handed out to transforms in turn


def _flame(xforms: list[XForm], name: str) -> Flame:
    flame = Flame(name, xforms)
    flame.camera = Camera(scale=RIG_WIDTH / 4.0, width=RIG_WIDTH, height=RIG_HEIGHT)
    for i, x in enumerate(flame.xforms):
        x.color = TRANSFORM_COLORS[i % len(TRANSFORM_COLORS)]
    return flame


def _xform(variations: dict[str, float], coefs=(1.0, 0.0, 0.0, 1.0, 0.0, 0.0), name: str = "", weight: float = 1.0) -> XForm:
    return XForm(weight=weight, color_speed=0.5, coefs=tuple(coefs), variations=dict(variations), name=name)


RIGS: dict[str, Callable[[], Flame]] = {
    "Formula alone": lambda: _flame([formula_xform("formula")], "Formula alone"),
    "Formula + linear": lambda: _flame([formula_xform("formula"), _xform({"linear": 1.0}, (0.5, 0.0, 0.0, 0.5, 0.5, 0.0), "linear")],
                                       "Formula + linear"),
    "Two formulas": lambda: _flame([formula_xform("formula"), _xform({SCRATCH_NAME: 1.0}, (0.7, 0.0, 0.0, 0.7, -0.5, 0.3), "formula")],
                                   "Two formulas"),
    "Julia pair": lambda: _flame([formula_xform("formula"), _xform({"julian": 1.0}, (1.0, 0.0, 0.0, 1.0, 0.0, 0.0), "julian", 0.5)],
                                 "Julia pair"),
    "Sierpinski": lambda: _flame([formula_xform("formula"), _xform({"linear": 1.0}, (0.5, 0.0, 0.0, 0.5, 0.5, 0.0), "linear"),
                                  _xform({"linear": 1.0}, (0.5, 0.0, 0.0, 0.5, 0.0, 0.5), "linear"),
                                  _xform({"linear": 1.0}, (0.5, 0.0, 0.0, 0.5, -0.5, 0.0), "linear")], "Sierpinski"),
}


def test_rig(name: str) -> Flame:
    """A starter flame for the grid: one of `RIGS` (the formula alone for an unknown name)."""
    return RIGS.get(name, RIGS["Formula alone"])()


GRADIENT_PRESETS: dict[str, tuple[tuple[int, int, int], ...]] = {
    "Yellow · cyan · magenta": ((255, 210, 48), (41, 217, 255), (255, 63, 181)),
    "Fire": ((255, 240, 120), (255, 120, 20), (140, 10, 60)),
    "Ocean": ((200, 255, 240), (30, 170, 220), (20, 40, 120)),
    "Forest": ((240, 255, 170), (80, 200, 90), (20, 80, 50)),
    "Candy": ((255, 150, 220), (150, 220, 255), (255, 250, 150)),
    "Greyscale": ((255, 255, 255), (128, 128, 128), (20, 20, 20)),
}


def preset_gradient(name: str) -> Gradient:
    """One of `GRADIENT_PRESETS` as a gradient (the first for an unknown name)."""
    colors = GRADIENT_PRESETS.get(name, next(iter(GRADIENT_PRESETS.values())))
    return Gradient.from_colors(name, list(colors))


def random_gradient(rng: random.Random | None = None, count: int = 3) -> Gradient:
    """A bright gradient of `count` saturated colours at evenly spaced, random hues."""
    import colorsys
    rng = rng or random.Random()
    start = rng.random()
    colors = []
    for i in range(count):
        h = (start + i / count + rng.uniform(-0.08, 0.08)) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, rng.uniform(0.6, 0.95), rng.uniform(0.85, 1.0))
        colors.append((int(r * 255), int(g * 255), int(b * 255)))
    return Gradient.from_colors("Random", colors)


__all__ = ["Template", "TEMPLATES", "TEMPLATES_BY_KEY", "new_formula_text", "Snippet", "SNIPPETS", "snippet_text", "stem_of",
           "declared_variables", "add_variable", "rename_formula", "derived_name", "RIGS", "test_rig", "GRADIENT_PRESETS",
           "preset_gradient", "random_gradient"]
