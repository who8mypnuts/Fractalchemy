# Formulas: the variation / plugin system

Every fractal is built from *formulas* — flam3 calls them variations, Apophysis calls the
community-written ones plugins. Fractalchemy keeps all of them in `fractalchemy/formulas/`,
outside the engine code, and runs each one on **both** engines from a single definition:

```
fractalchemy/formulas/
    builtin/        native Python formulas: a numpy function + a GLSL snippet per entry
        flam3.py    the flam3 classics and the Apophysis 7X built-ins from XForm.pas
    library/        the formula library, in the Apophysis plugin C dialect, one file per formula
        apophysis7x/    sources shipped with Apophysis 7X (src/Plugin and the apophysis-plugins SDK repo)
        plugins/        community plugins whose source was available
        ports/          hand-ported sources (structs written out, noise libraries shared as .h files)
        reconstructed/  plugins that only existed as DLLs, recovered from the machine code
        jwildfire/      variations translated from JWildfire's Java sources (tools/import_jwf_variations.py)
    lang/           the compiler for the dialect (preprocess → parse → analyse → numpy + GLSL)
    loader.py       discovery, caching, user folders
    apophysis_depth.py   Apophysis's depth rule for its built-ins
    workbench.py    the Formula Editor's helpers: the scratch registry slot, sources, the read-only policy
    authoring.py    templates, snippets, the variable / rename refactors, test rigs, gradient presets
    completion.py   the dialect's names (for the editor's completion and the reference panel)
    verify.py       one variation on both engines: the point probe and the numpy-vs-GLSL check (the test-suite's too)
tools/
    import_apo_plugins.py   bulk-imports plugin sources into the library (with verification)
    apo_decompile.py        reconstructs a formula from a plugin DLL (no source needed)
    import_jwf_variations.py + jwf_translate.py   translate JWildfire `*Func.java` variations (with verification)
```

At start-up `formulas.load_all()` fills the registry (`fractal.variations.REGISTRY`):
the Python builtins first, then every `.c` file under `library/`, then the user folders.
Compiled artefacts are cached on disk (`loader.cache_file()`), so a warm start takes well
under a second for the ~570 bundled formulas; a cold compile takes a few seconds.

## Why a compiler instead of DLLs

Apophysis plugins are Windows DLLs (mostly 32-bit, some 64-bit). Fractalchemy does not load
DLLs at all: the plugin *source* is compiled into a float64 numpy function for the CPU
engine and into GLSL for the GPU preview, so a plugin works on every platform and both
engines agree on it (`tests/test_variations.py` checks every formula on both). The 32-bit /
64-bit question therefore disappears — a formula in the library renders on a 64-bit
machine regardless of which DLL flavours its author ever built. For plugins that only ever
existed as 32-bit DLLs with no source, `tools/apo_decompile.py` recovers the formula from
the machine code (see below).

## The formula dialect

A formula file is an Apophysis plugin source. Existing plugin sources can be dropped into a
formula folder unchanged in most cases:

```c
typedef struct {
    double whorl_inside;
    double whorl_outside;
} Variables;

#include "apoplugin.h"          // implied: dropped by the preprocessor

APO_PLUGIN("whorl");
APO_VARIABLES(
    VAR_REAL(whorl_inside, 1.0),
    VAR_REAL(whorl_outside, 1.0)
);

int PluginVarPrepare(Variation* vp)   // once per transform: derive constants from parameters
{
    return TRUE;
}

int PluginVarCalc(Variation* vp)      // once per point
{
    double a, r, sina, cosa;
    r = sqrt(FTx * FTx + FTy * FTy);
    if (r < VVAR) a = atan2(FTy, FTx) + VAR(whorl_inside) / (VVAR - r);
    else          a = atan2(FTy, FTx) + VAR(whorl_outside) / (VVAR - r);
    fsincos(a, &sina, &cosa);
    FPx += VVAR * r * cosa;
    FPy += VVAR * r * sina;
    return TRUE;
}
```

### What is available

* **Point state**: `FTx FTy FTz` (the input point, after the pre-affine), `FPx FPy FPz` (the
  accumulator — add your contribution), `TC` (the point's colour, 0..1; writing it makes a
  *direct colour* formula, blended by the transform's `var_color`), `VVAR` (the weight),
  `TM(a)`…`TM(f)` (the affine coefficients), `VAR(name)` (a variable). `vp->var.x`,
  `vp->vvar`, `*(vp->pFTx)` spellings work too.
* **Naming rules**: a formula whose name starts with `pre_` rewrites `FTx/FTy/FTz` and runs
  before the others; `post_` formulas rewrite `FPx/FPy/FPz` after them (`flatten` too) —
  exactly Apophysis's ordering. Variables declared with `VAR_REAL`, `VAR_INTEGER`,
  `VAR_REAL_RANGE`, `VAR_INTEGER_RANGE`, `VAR_INTEGER_NONZERO`, `VAR_REAL_CYCLE` carry their
  type, default and range into the editor (`Variation.param_info`). Struct members not
  declared as variables are *derived* values if `PluginVarPrepare` sets them (computed once
  per transform, on the CPU, then handed to both engines) and per-call temporaries otherwise.
* **C**: `double`/`int`/`bool`, arrays (constant sizes), `if`/`for`/`while`/`do`/`switch`,
  early `return`, `break`/`continue`, helper functions (including pointer out-parameters and
  array parameters), `static const` tables, `#define` macros and `#if` conditionals,
  `random01()`, `rand()`, `fsincos`, `sinhcosh`, `sqr`, the `<math.h>` functions, `M_PI` and
  friends, `EPS`, `INT_MAX`, `DBL_MAX`.
* **C++ touches**: `std::complex<double>` (`typedef` it, then `Complex z(FTx, FTy)`, `exp(z)`,
  `z.real()`, `1i` literals …), function-style casts, `inline`.
* **Apophysis idioms**: nested (GNU C) functions, `#include "sibling.h"` for shared helper
  sources next to the formula, stateful plugins that keep their own point in `static`
  variables (their private orbit is re-run a dozen steps per point, which samples the same
  attractor), the `gauss_rnd` rolling buffers, `VAR(x)` on array members.

### What is not

`goto`, structs other than `Variables`, pointers beyond aliases of variables / array rows,
file or image I/O (`dc_image`), recursion. The compiler reports the reason per file; the
loader logs it and carries on.

### How it runs

`lang/` turns the source into a typed AST (`semantic.py`), then:

* `numpy_backend.py` emits a vectorised Python function. Branches that depend on the point
  become masked `where` selections; loops whose condition depends on the point iterate while
  any lane is active; per-transform constants stay scalars. Integers are 32-bit (hashes wrap
  like C), `/` and `%` truncate like C, `x / 0` is ±inf.
* `glsl_backend.py` emits a GLSL function body with the same semantics (`fmodc`, `powc`,
  `idivc` helpers give C behaviour); parameters and tables are read from the parameter
  texture, helper functions become GLSL functions.

The GPU preview is float32, so ill-conditioned steps (`acosh` near 1, `sin(x)*43758` hashes,
points exactly on a discontinuity) can differ from the float64 CPU result; the tests
allow one such point in twelve.

## Adding formulas

* **The Formula Editor** (*Windows ▸ Formula Editor*, `F10`) is the easy way: a code editor with the dialect
  highlighted and completed, compiled for both engines a moment after every change and shown live on a transform
  grid and in a rendered preview; *New formula* offers templates (normal / pre / post / direct colour / 3D /
  blur), the list loads any bundled formula's source as a starting point, the drawer has the guide, the
  generated code and a point probe / numpy-vs-GLSL check, and *Save* writes the `.c` file into the per-user
  folder and registers it at once. While you type, the work in progress lives in a reserved registry slot
  (`workbench.SCRATCH_NAME`) that only the editor's own flame refers to, so no real formula changes under the
  other windows until you save. **Bundled and built-in formulas are read-only**: the editor never saves over
  their names (it renames yours `name_mine` instead) or into the package's folders.
* **Users**: drop `.c` (dialect) or `.py` (native) files into the per-user folder —
  `~/.config/Fractalchemy/formulas` on Linux, `~/Library/Application Support/Fractalchemy/formulas`
  on macOS, `%APPDATA%\Fractalchemy\formulas` on Windows — or into any folder listed in
  `$FRACTALCHEMY_FORMULAS`. A user file overrides a bundled formula of the same name.
  Native Python formulas use the `@variation` decorator (see `builtin/flam3.py`): a numpy
  function returning the weighted `(dx, dy[, dz])` and the equivalent GLSL snippet.
* **Bundled**: `python tools/import_apo_plugins.py --source <folder of plugin sources>`
  assembles, patches (`PATCHES` in the tool), compiles and verifies each source and writes
  the survivors into `library/`. `python tools/apo_decompile.py --batch <folder of DLLs>`
  does the same for DLLs without source.

## Translating JWildfire variations

`tools/import_jwf_variations.py --source ../JWildfire` reads every `*Func.java` under
`src/org/jwildfire/create/tina/variation/`, and `tools/jwf_translate.py` turns the regular shape of a
JWildfire variation class into the dialect: `transform()` → `PluginVarCalc` (`pAffineTP.x` → `FTx`,
`pVarTP.x +=` → `FPx +=`, `pAmount` → `VVAR`, `pContext.random()` → `random01()`, the precalc getters →
their expressions, `MathLib` / `Math` → the math functions), `init()` / `initOnce()` → `PluginVarPrepare`,
parameter fields → `APO_VARIABLES` (prefixed with the formula name, as JWildfire writes them in flames),
other fields → derived struct members, private helper methods → dialect functions, `static final`
constants → `#define`s and constant tables, `sinAndCos` → `fsincos`. The `isPreserveZCoordinate()` blocks are
dropped (plugins leave the depth alone unless they are 3D). Each translation is compiled and checked on
both engines before it is written; names already in the library are never shadowed. The report
(`docs/jwildfire_import.md`) groups what could not be translated by reason — the `vec2` / `vec3` shader
helper classes, the `Complex` class, `Random` objects and state kept between points, resources and
images, code compiled at run time, sub-flames — which is the hand-porting queue.

## Reconstructing plugins from DLLs

`tools/apo_decompile.py` symbolically executes `PluginVarPrepare` / `PluginVarCalc` of a
plugin DLL (x87 for 32-bit builds, SSE2 for 64-bit ones): it reads the variable table the
DLL exports, learns the struct layout from the `PluginVarInit*` functions, follows every
branch (jump tables included, infeasible paths pruned), recognises the SDK's `random01()`
pattern, the x87 expansions of `exp`/`log`, `fmin`/`fmax` NaN checks and sign-bit tricks,
and prints the equivalent dialect source. Loops are not supported (those plugins are listed
by the batch run and ported by hand). Every result is verified by the same numpy-vs-GLSL
test as the rest of the library before it is written.
