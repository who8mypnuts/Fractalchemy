"""What the Formula Editor needs from the formula system, Qt-free: the scratch slot, sources and templates.

The editor never edits the registry's real entries while the user types. Whatever it compiles is
registered under one reserved name — `SCRATCH_NAME` — and the editor's own little flame refers to the
formula by that name, so both render engines pick the work in progress up through the ordinary
registry path (`CompiledXForm.build`) without any special casing. Only *Save* registers the formula
under its real name (and writes the file that will be loaded at the next start-up).

    var = compile_formula(text).variation  # FormulaError on a problem
    register_scratch(var)                  # now a transform with {SCRATCH_NAME: 1.0} runs it
    source_of(REGISTRY["whorl"])           # the .c text (or a dialect skeleton for a native built-in)
    bundled_origin("whorl")                # the policy: names of bundled / built-in formulas cannot be saved over

Templates, snippets, the rename refactor and the test rigs are in `authoring.py`.
"""

from __future__ import annotations

import inspect
import re
import textwrap
from dataclasses import replace
from pathlib import Path

from ..fractal import variations as V
from ..fractal.scene import Flame, XForm
from .lang import CompiledFormula, FormulaError, compile_source
from .loader import user_formula_dir

SCRATCH_NAME = f"{V.PRIVATE_PREFIX}formula editor)"   # the registry slot of the formula being edited: not a C identifier, so no
                                                       # real formula can have the name, and the catalogue lists leave it out
ORIGINAL_NAME = f"{V.PRIVATE_PREFIX}formula editor original)"   # the formula the edit started from, for *Compare with original*
DEFAULT_NEW_NAME = "new_formula"
PACKAGE_DIR = Path(__file__).resolve().parents[1]     # everything under here is bundled: read-only for the editor
NATIVE_STUB_NOTE = "a native built-in: port the maths into PluginVarCalc to make it a formula of your own"
_PLUGIN_NAME = re.compile(r'APO_PLUGIN\s*\(\s*"([^"]*)"\s*\)')
_LINE_IN_MESSAGE = re.compile(r"\bline (\d+)\b")
_OFFSET_IN_MESSAGE = re.compile(r"\boffset (\d+)\b")
_SAFE_NAME = re.compile(r"[^A-Za-z0-9_]+")

NATIVE_SKELETON = '''\
/*
    {name} — {note}.

    Native formulas are written in Python (numpy) with a GLSL twin, not in the plugin dialect,
    so there is no .c source to edit. This is a dialect skeleton carrying the native code for
    reference; until you change it the preview shows the real {name}.

{reference}
*/

{variables}APO_PLUGIN("{name}");

{declarations}int PluginVarPrepare(Variation* vp)
{{
    return TRUE;
}}

int PluginVarCalc(Variation* vp)
{{
    // TODO: port the maths from the reference above
    FPx += VVAR * FTx;
    FPy += VVAR * FTy;
    return TRUE;
}}
'''


# --- names and files ---------------------------------------------------------------------------------------
def formula_name(text: str) -> str | None:
    """The name declared by `APO_PLUGIN("…")` in `text`, or None."""
    match = _PLUGIN_NAME.search(text)
    return match.group(1) if match else None


def safe_file_name(name: str) -> str:
    """A file stem for a formula name (anything but letters, digits and underscores becomes `_`)."""
    return _SAFE_NAME.sub("_", name.strip()) or DEFAULT_NEW_NAME


def user_formula_path(name: str) -> Path:
    """Where a formula called `name` lives in the per-user formulas folder."""
    return user_formula_dir() / f"{safe_file_name(name)}.c"


def is_user_file(path: Path | None) -> bool:
    """True when `path` is inside the per-user formulas folder."""
    if path is None:
        return False
    try:
        return path.resolve().is_relative_to(user_formula_dir().resolve())
    except (OSError, ValueError):
        return False


def is_bundled_path(path: Path | None) -> bool:
    """True when `path` lies inside the Fractalchemy package (the bundled library, the built-ins): never a save target."""
    if path is None:
        return False
    try:
        return path.resolve().is_relative_to(PACKAGE_DIR)
    except (OSError, ValueError):
        return False


def bundled_origin(name: str) -> str | None:
    """The policy check of *Save*: the origin of the bundled / built-in formula called `name`, or None when the name is
    free (unknown, private, or a formula of the user's own — those may be overwritten)."""
    var = dict.get(V.REGISTRY, name) if name else None
    if var is None or V.is_private(var.name):
        return None
    path = origin_path(var)
    if path is not None and not is_bundled_path(path):
        return None                      # a user file (their own folder or anywhere outside the package)
    return var.origin or "a native built-in"


def origin_path(var: V.Variation) -> Path | None:
    """The source file of a formula-style variation (None for native ones or when the file is gone)."""
    if var.style != V.FORMULA or not var.origin:
        return None
    path = Path(var.origin)
    return path if path.is_file() else None


def source_of(var: V.Variation) -> str:
    """The editable text for a registered formula: its `.c` source, or a dialect skeleton for a native one."""
    path = origin_path(var)
    if path is not None:
        return path.read_text(encoding="utf-8", errors="replace")
    return native_skeleton(var)


def native_skeleton(var: V.Variation) -> str:
    """A dialect file declaring a native formula's name and variables, with its Python + GLSL as a reference comment."""
    reference = ["    GLSL (t = input point, w = weight, v = accumulator, col = colour):", ""]
    reference += ["        " + line for line in var.glsl.splitlines()] or ["        (none)"]
    try:
        source = inspect.getsource(var.numpy)
    except (OSError, TypeError):
        source = ""
    if source:
        reference += ["", "    numpy:", ""] + ["        " + line for line in textwrap.dedent(source).rstrip().splitlines()]
    reference_text = "\n".join(line.replace("*/", "* /") for line in reference)
    if var.params:
        members = "".join(f"    double {key};\n" for key in var.params)
        variables = f"typedef struct {{\n{members}}} Variables;\n\n"
        entries = ",\n".join(f"    VAR_REAL({key}, {default:g})" for key, default in var.params.items())
        declarations = f"APO_VARIABLES(\n{entries}\n);\n\n"
    else:
        variables, declarations = "", ""
    return NATIVE_SKELETON.format(name=var.name, note=NATIVE_STUB_NOTE, reference=reference_text, variables=variables,
                                  declarations=declarations)


# --- compiling and the scratch slot -------------------------------------------------------------------------
def compile_formula(text: str, include_dir: Path | None = None) -> CompiledFormula:
    """Compile editor text for both engines (`FormulaError` says what is wrong and, when known, on which line)."""
    return compile_source(text, origin="formula editor", include_dir=include_dir)


def as_scratch(var: V.Variation) -> V.Variation:
    """The same formula under the editor's reserved registry name (parameters keep their own full names)."""
    return replace(var, name=SCRATCH_NAME)


def register_scratch(var: V.Variation) -> V.Variation:
    """Put `var` in the scratch slot (re-registering is cheap, so callers may do it before every render)."""
    scratch = var if var.name == SCRATCH_NAME else as_scratch(var)
    if dict.get(V.REGISTRY, SCRATCH_NAME) is not scratch:
        V.register(scratch)
    return scratch


def unregister_scratch() -> None:
    """Empty the scratch slot (the editor window is closing for good)."""
    dict.pop(V.REGISTRY, SCRATCH_NAME, None)


def scratch_variation() -> V.Variation | None:
    """What the scratch slot holds (None when nothing is registered)."""
    return dict.get(V.REGISTRY, SCRATCH_NAME)


def register_original(var: V.Variation | None) -> None:
    """Keep the formula an edit started from in the *original* slot (None empties it), for side-by-side comparison."""
    if var is None:
        dict.pop(V.REGISTRY, ORIGINAL_NAME, None)
    else:
        V.register(replace(var, name=ORIGINAL_NAME))


def original_variation() -> V.Variation | None:
    """What the original slot holds (None when nothing is registered)."""
    return dict.get(V.REGISTRY, ORIGINAL_NAME)


def error_line(message: str, text: str = "") -> int | None:
    """The 1-based line a compiler message points at (`line N` or `offset N`), or None."""
    match = _LINE_IN_MESSAGE.search(message)
    if match:
        return int(match.group(1))
    match = _OFFSET_IN_MESSAGE.search(message)
    if match and text:
        return text.count("\n", 0, min(len(text), int(match.group(1)))) + 1
    return None


def error_text(exc: Exception) -> str:
    """A compiler error without the `formula editor:` origin prefix."""
    text = str(exc)
    return text.split(": ", 1)[1] if text.startswith("formula editor: ") else text


# --- the editor's flame -----------------------------------------------------------------------------------
def formula_xform(name: str = "formula", color: float = 0.0) -> XForm:
    """A transform running the scratch formula alone, on the reference triangle."""
    return XForm(weight=1.0, color=color, color_speed=0.5, variations={SCRATCH_NAME: 1.0}, name=name)


def uses_scratch(xform: XForm) -> bool:
    """True when the transform runs the formula being edited."""
    return SCRATCH_NAME in xform.variations


def prepared_xform(xform: XForm, var: V.Variation | None = None, slot: str = SCRATCH_NAME) -> XForm:
    """A copy of `xform` ready to render: a `pre_` / `post_` formula gets `linear` beside it (alone it would
    leave the accumulator at zero, as in Apophysis), anything else is left as it is. With another `slot` the
    formula transforms run that registry slot instead (the *original* one, for comparison)."""
    var = var if var is not None else dict.get(V.REGISTRY, slot)
    copy = xform.copy()
    if uses_scratch(copy):
        if slot != SCRATCH_NAME:
            copy.variations = {(slot if n == SCRATCH_NAME else n): w for n, w in copy.variations.items()}
        if var is not None and var.kind in (V.PRE, V.POST) and not any(n != slot for n in copy.variations):
            copy.variations["linear"] = 1.0
    return copy


def prepared_flame(flame: Flame, var: V.Variation | None = None, slot: str = SCRATCH_NAME) -> Flame:
    """A copy of the editor's flame with every transform prepared (see `prepared_xform`)."""
    copy = flame.copy()
    copy.xforms = [prepared_xform(x, var, slot) for x in copy.xforms]
    return copy


__all__ = ["SCRATCH_NAME", "ORIGINAL_NAME", "DEFAULT_NEW_NAME", "PACKAGE_DIR", "FormulaError", "CompiledFormula", "formula_name",
           "safe_file_name", "user_formula_path", "is_user_file", "is_bundled_path", "bundled_origin", "origin_path", "source_of",
           "native_skeleton", "compile_formula", "as_scratch", "register_scratch", "unregister_scratch", "scratch_variation",
           "register_original", "original_variation", "error_line", "error_text", "formula_xform", "uses_scratch", "prepared_xform",
           "prepared_flame"]
