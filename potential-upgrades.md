# Potential upgrades

Planning notes. **Status**: §1 (the read-only policy) and §3 (the Formula Editor conveniences) are implemented —
see the *Formula Editor window* section of the README; the one item done differently is "multiple open formulas",
which became a *Recent formulas* list. §2 is superseded by `proposed_variations.md`, written against the JWildfire
sources. Three topics: the Formula Editor's save / overwrite policy,
formulas worth adding to the library (including what could be imported from JWildfire), and quality-of-life
features for the Formula Editor.

---

## 1. Save / overwrite policy: only user formulas may be saved or overwritten

### What the code does today (needs changing)
- **Save with a bundled or built-in name is allowed after a warning.** `FormulaSession.overrides_bundled()` detects
  the clash and `save_formula()` asks *"Your file will take its place whenever Fractalchemy runs. Continue?"* —
  answering Yes writes `~/.config/Fractalchemy/formulas/<name>.c`, and because the loader lets user files override
  bundled ones of the same name, the user's version shadows the bundled formula from the next start-up on.
- **Loading a bundled `.c` from the list** sets `own_file = None`, so Save goes to the user folder (correct), but
  under the *same* name — the shadowing case above.
- **Open… on a file inside the package** (`fractalchemy/formulas/library/...`) gives the session `ORIGIN_FILE`, and
  `own_file` then points *into the package*, so Save would write over the bundled source and Delete could remove
  it. (Only reachable by browsing into the install folder, but it is a hole.)
- Delete is already restricted to the user's own file (`own_file`), and broken text is never registered.

### The intended rule
- Bundled library sources (`fractalchemy/formulas/library/**`), the native built-ins (`formulas/builtin/*.py`) and
  anything else inside the package are **read-only**: they can be loaded into the editor as a starting point, but
  never saved over, shadowed, or deleted.
- A formula can only be **saved** when its `APO_PLUGIN("…")` name is not the name of a bundled / built-in formula
  (a *user* formula of that name is fine: that is overwriting your own file).
- **Save As** must stay outside the package tree (the user's folder or any folder of the user's choosing that is not
  inside `fractalchemy/`); **Delete** only ever removes a user file.

### Plan
1. `workbench.is_bundled_path(path)` — true for anything under the package directory; `own_file` becomes
   `path if path is outside the package and (ORIGIN_FILE or is_user_file)`.
2. `FormulaSession.save()` refuses (raises a `FormulaNameTaken` / returns a reason) when `name` resolves to a
   registered formula whose origin is bundled or built-in; `overrides_bundled()` turns from a warning into a block.
3. The window replaces the Yes / No dialog with a clear message and a one-click fix: **"`whorl` is a bundled formula.
   Save yours as `whorl_mine`?"** — the rename rewrites `APO_PLUGIN("whorl")` (and, optionally, the `whorl_` variable
   prefixes, so the parameters stay conventionally named) and saves. Derived copies get a predictable suffix
   (`_mine`, `_2`, …) chosen with the existing `_unique_name()`.
4. Save As dialog: validate the chosen path (outside the package, `.c`) and explain when it is refused.
5. Decide the **loader** side: today a user file with a bundled name overrides the bundled formula at start-up
   (documented behaviour, useful for people who hand-fix a plugin). Options: keep it (the editor simply never creates
   such files), or flip to *bundled wins, user file reported as a clash* in `LoadReport.errors`. The editor policy
   works either way; flipping it makes the rule airtight for files dropped in by hand.
6. Tests: saving under `whorl` / `julian` is refused; Open… on a library file has no Save target; rename-and-save
   produces `whorl_mine.c` with the renamed plugin name; deleting never touches the package.

---

## 2. Formulas worth adding to the library

566 formulas are loaded today: the flam3 classics, the Apophysis 7X built-ins and essentially every Apophysis plugin
whose source or DLL could be found. The gaps are therefore (a) a handful of classics that slipped through, (b) the
large body of **JWildfire-original** variations that never existed as Apophysis plugins, and (c) a few "engine
feature" variations that need more than the dialect offers.

> Note: this list was written without access to the JWildfire repository (no network in the working environment), from
> knowledge of `src/org/jwildfire/create/tina/variation/`. Names and availability should be verified against the repo
> (`*Func.java`, each with `getName()`, `getParameterNames()`, `transform(...)`, and for many a `getGPUCode()`).

### 2a. Classics / near-classics missing from our set
- `twintrian` (flam3; we have `twintrian2` only), `disc2`, `flower` (we have `flower2` / `flower3D`), `parabola`
  (we have `parabola2`), `lissajous`, `cylinder_apo` / `log_apo` (the Apophysis-flavoured variants JWildfire keeps
  beside the flam3 ones — only worth adding if flames in the wild reference them), `tangent3D`, `pie3D`,
  `square3D`, `blob3D`, `butterfly3D`, `post_zscale` / `post_ztranslate` (we have the pre / plain ones).
- `jac_cn`, `jac_dn`, `jac_sn` (Jacobi elliptic family — we only have `jac_asn`), `polylogarithm`, `rhodonea`,
  `vogel`, `spirograph`, `yin_yang`, `waffle`, `onion2`, `intersection`, `ellipse`, `tanh_spiral`, `coth_spiral`,
  `r_circleblur`, `hexnix3D`, `hyperbolic3D`, `quaternion`, `pointsymmetry`, `tile_reverse`.

### 2b. JWildfire-original families (good candidates, all plain maths → straightforward in the dialect)
- **Hex / tiling / Truchet** (Whittaker Courtney et al.): `hexes`, `hex_rand`, `hex_truchet`, `dc_hexes_wf`,
  `truchet_hex_fill` variants, `sphericalN` siblings — we have `Truchet*`, `tile_hlp`, `tile_log`, `hexcrop`;
  the hexagonal family is the obvious hole.
- **Direct-colour / noise**: `dc_perlin`, `dc_crackle_wf`, `dc_hexes_wf`, `dc_ztransl` siblings. Perlin / simplex
  noise needs a shared header like our `noiseb.h` / `voronoi.h` (the crackle port) — one header, several formulas.
- **Escape-time fractals as variations** (`fract_mandelbrot_wf`, `fract_julia_wf`, `fract_dragon_wf`,
  `fract_pearls_wf`, `fract_meteors_wf`, `fract_salamander_wf`, `fract_formula_*_wf`): bounded iteration loops,
  which the compiler supports (per-point `while` with a max count). The `fract_formula_*` ones evaluate a
  user-typed formula string at run time — skip those, or offer fixed presets.
- **Strange attractors as variations** (Jesus Sosa's set): `lorenz`, `rossler`, `clifford`, `ikeda`, `duffing`,
  `hadamard`, `pdj_js`, `popcorn_js`, `sattractor`, `tree_js`, `lsystem3D_js`, plus the big `cut_*` family
  (`cut_bricks`, `cut_circles`, `cut_hex`, `cut_kaleido`, `cut_mandel`, `cut_spiral`, `cut_squares`, `cut_stars`,
  `cut_truchet`, `cut_voronoi`, …). Most are short functions; the "stateful orbit" ones fit the existing
  stateful-plugin mechanism (private orbit re-run `ORBIT_STEPS` times).
- **Curves and shapes**: `chrysanthemum`, `cloverleaf_wf`, `heart_wf`, `epispiral_wf`, `rose_wf`, `devil_warp`,
  `excinis`, `spirograph`, `super_shape` siblings (`super_shape3d` we have), `glynnia3`, `bubbleT3D`,
  `pre_wave3D_wf`, `waves2_wf` / `waves3_wf` / `waves4_wf` (JWildfire's re-parameterised wave variants).
- **GLSL-sourced variations** (`glsl_*`, Sosa): these are *written in GLSL* already, which is unusual — our GPU engine
  could take their bodies almost verbatim, and the numpy side is a mechanical port. Worth a look precisely because
  both engines are first-class here.

### 2c. Variations that need engine features first (decide before importing)
- `subflame_wf` / `pre_subflame_wf` — run another flame as a variation. Would need a "flame-in-variation" engine
  concept; powerful, but a separate project.
- `text_wf`, `svg_wf`, `primitives_wf`, `colormap_wf`, `post_colormap_wf`, `dc_image` — file / font / image I/O at
  render time. Excluded by the dialect on purpose (`docs/formulas.md`); would need a resource mechanism in
  the parameter texture (images as tables) — feasible for small images, but a design decision.
- `dla_wf`, `isosfplot3d_wf`, `custom_wf_*` — precomputed point clouds, formula parsers, scripted variations. Skip.

### 2d. How to import (tooling + licensing)
- **Tool**: a `tools/import_jwf_variations.py` in the spirit of `import_apo_plugins.py` — parse the Java
  `transform()` body and translate the subset that maps 1:1 onto the dialect (`pAffineTP.x/y/z` → `FTx/FTy/FTz`,
  `pVarTP.x += …` → `FPx += …`, `pAmount` → `VVAR`, parameters → `VAR()`, `pContext.random()` → `random01()`,
  `Math.*` / `MathLib.*` → the math functions, `initOnce`/`init` → `PluginVarPrepare`), compile, verify numpy vs GLSL
  with the same harness as `test_variations.py`, and write the survivors into `library/jwildfire/` with provenance
  headers. Variations whose `getGPUCode()` exists give a second reference for verification.
- **Licensing**: JWildfire is LGPL-2.1; many variation files carry the original Apophysis plugin GPL headers and
  named authors. Keep the existing practice — one provenance + licence header per file, authors credited — and
  keep a `library/jwildfire/LICENSE` note. Check per file, since a few JWildfire variations state stricter terms.
- **Naming**: JWildfire names sometimes collide with ours for *different* maths (`heart` vs `Heart`, `rose` vs
  `rose_wf`, the `_apo` variants). Import under JWildfire's exact names so `.flame` files written by JWildfire
  render correctly; where the maths is identical to an existing formula, register an alias instead of a duplicate.
- **Priority order**: 2a classics (small, expected by users) → hex / tiling and direct-colour families → curves →
  attractors / `cut_*` → escape-time fractals → `glsl_*`.

---

## 3. Formula Editor: feature and quality-of-life ideas

### Writing
- **Dialect completion** in the code editor (reuse `CompletionPopup`): `FTx`/`FPx`/`VVAR`/`TC`, `VAR(…)` with the
  declared variables, the math functions and constants from `lang/builtins.py`, the `VAR_REAL…` macros — with the
  one-line docs inline.
- **Insert-variable helper**: one action that adds a variable in all three places at once (struct member,
  `APO_VARIABLES` entry with default / range, and a `VAR(name)` at the cursor).
- **Snippets**: polar coordinates (`r`, `a` with `fsincos`), a `pre_` / `post_` / direct-colour / 3D skeleton, a
  stateful-orbit skeleton, a `PluginVarPrepare` derived-constant block, a `#include` of `noiseb.h` / `voronoi.h`.
- **Template chooser** for *New formula*: normal / pre / post / direct colour / 3D / blur (random) starting points
  rather than the single swirl template.
- **Rename refactor**: rename the formula and all `name_` variable prefixes consistently (the same helper the save
  policy in §1 needs).
- **Reference drawer** like the Script Editor's: the dialect guide (`docs/formulas.md`) searchable in-window, the
  function / constant catalogue, and the loaded formula's own summary (kind, depth rule, DC, parameters).

### Seeing
- **Variation preview controls**: range / density / depth sliders (fixed at 2 / 2 / 1 today), a polar grid option,
  colour the dots by iteration depth, show input grid faintly for before/after reading.
- **Compare with the original** when editing a bundled formula: side-by-side previews (or an A/B toggle) of the
  registered formula and the edited one.
- **Point probe**: type a point (or click the canvas) and see the formula's output for it on both engines — the
  fastest way to debug a sign error.
- **Engine verification button** ("Check numpy vs GLSL"): run the `test_variations` comparison on the current
  formula and report disagreeing points; also surface the *"rendered on the CPU — the GPU rejected the shader"*
  note from the preview's `RenderStats` in the status line instead of silently falling back.
- **Compiler output tab**: the generated numpy and GLSL, plus the compiler's warnings (`spec.warnings`, e.g.
  "stateful plugin", unsupported constructs) — today only the first error is shown.
- **Test rigs**: a dropdown of starter flames for the grid (single transform, two linear + formula, a Julia pair,
  a tiling set) and **Use current fractal** (copy the main window's flame into the grid) / **Send to main
  window** (push the grid's flame out as a new fractal).
- **Parameter tools**: randomise / reset all variables, a sweep (animate one variable over its range) to see how
  a formula behaves, and drag-editing ranges that respect `VAR_REAL_RANGE` min / max.

### Managing
- **Multiple open formulas** (tabs or a recent list), with per-formula drafts.
- **Watch the user folder**: reload a formula when its file changes on disk (the library panels already use a
  watcher), and a **Open folder** button for the user formulas directory.
- **Favourites / tags / authors** in the formula list (origin, author from the header, 3D / DC / random filters
  as checkboxes rather than text search only).
- **Revert to saved** and **Duplicate as new** (with the auto-suffixed name) actions.
- **Export**: copy the source as an Apophysis plugin `.c` with a proper header (for sharing), or as a JWildfire-style
  stub if the import tooling in §2d ever runs the other way.
- **Gradient presets** beside the bar: a few bright 3–5 colour presets and *random*, without opening the library.
- **Window**: remember the selected transform and view zoom between runs, a compact mode that hides the side panel,
  and the preview quality in the View menu (right-click only today).
- **Keyboard**: `F5` / `Ctrl+Enter` compile (exists), `Ctrl+Shift+V` toggle variation preview globally, `Ctrl+E`
  focus the code editor from the canvas and back.
