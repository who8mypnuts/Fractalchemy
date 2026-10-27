# TASK_STATE — formulas / plugin system (Apophysis plugins incorporated)

Branch: `master`, uncommitted working tree on top of `13a9126 baseline`.

## How to resume
```bash
cd /workspace/Fractalchemy
pip install -r requirements.txt                    # + pytest, pyflakes for development; py7zr for the import tool (7z packs)
python3 -m pytest -q                               # ~4 min: every formula is checked on numpy *and* GLSL (llvmpipe)
python3 -m pyflakes fractalchemy tests main.py tools
python3 main.py                                    # Help ▸ Formulas… lists what loaded (and what failed, why)
```

## What was done (this task)
The plugins under `samples/aposource/` (Apophysis 7X sources + ~540 distinct plugin DLLs, mostly 32-bit) are now
formulas of Fractalchemy. Design and reference: **docs/formulas.md** (read it first).

1. **Formula language + compiler** (`fractalchemy/formulas/lang/`): Apophysis plugin C dialect → typed AST →
   vectorised numpy (masked control flow, per-point loops, 32-bit ints, C semantics) **and** GLSL. Supports
   helpers (inlined for numpy, real functions for GLSL), pointer out-params, arrays, switch, complex numbers,
   nested GNU-C functions (closures), `#include "sibling.h"`, stateful plugins (private orbit re-run
   `ORBIT_STEPS` times), prepare-filled tables (through the parameter texture), constant tables.
2. **Engine**: points carry z; Apophysis transform order (pre_ → normal → post_), `var_color` direct colour,
   3D camera (`render/projection.py`, numpy + GLSL), `Camera.pitch/yaw/perspective/zpos/dof`, `XForm.var_color`,
   `.flame` read/write of `cam_*` / `var_color`, `.fa` carries them. GPU state = (x, y, z, c) + xform + seed.
   Service falls back to the CPU engine for a flame whose GLSL the driver rejects.
3. **Registry** (`fractal/variations.py`): `Variation` gained kind / z / dc / style / prepare / param_info /
   origin / tables; full parameter names; lazy-loading registry (`formulas.load_all()` on first use);
   `parameter_owner()` lets the flame reader classify parameters whose names differ from the variation's.
4. **Library** (`fractalchemy/formulas/library/`, 566 formulas, each file carries provenance + licence header):
   `apophysis7x/` (Apophysis 7X sources), `plugins/` (community sources), `ports/` (hand ports: falloff2/3
   families, pre_xfalloff2, octapol, randCubes, crackle + shared `noiseb.h` / `voronoi.h`), `reconstructed/`
   (229 DLL-only plugins recovered with `tools/apo_decompile.py`), plus native `builtin/flam3.py`
   (classics + Apophysis XForm.pas built-ins incl. real z handling) and `apophysis_depth.py` (the built-ins'
   `FPz += vvar*FTz` rule). Hand-written from Pascal: julia3D, julia3Dz, curl3D, waves2 (3D).
5. **Tools**: `tools/import_apo_plugins.py` (scan sources/archives → assemble → patch → compile → verify →
   write; `PATCHES` dict for broken sources), `tools/apo_decompile.py` (symbolic x87/SSE2 executor:
   layout discovery from Init functions, VarInfo table, imports/thunks, jump tables, path pruning, random01
   and x87 exp/log idioms, function-pointer members, VarInfo tables filled by static constructors (2018
   SDK builds), affine `TM(a..f)` members of the Aposhack-pack SDK layout, `--batch`/`--refresh`),
   `tools/pemeta.py`.
6. **UI**: *Help ▸ Formulas…* (`ui/formula_browser.py`): searchable catalogue grouped by origin, parameter
   details, load errors, user folder path (`select(name)` jumps to one). Status bar still lists ignored unknown
   variations. **Info tab** (`ui/info_panel.py`, first tab of the settings panel, before *Render*): property
   tree of the loaded fractal — file/entry/format, size + camera (3D rows), transforms (weight share, colour,
   variations + parameters, affine/post/xaos), distinct formulas with facts (double-click → formula browser),
   colouring + palette strip, last render stats. Fed by `MainWindow` from the document's signals and
   `viewport.render_progress`; the chosen tab persists (`panel/tab`).
7. **Tests**: `test_formula_lang.py` (compiler features), `test_formulas_loader.py` (user folders, override,
   cache, errors), `test_variations.py` now runs every registered formula through both engines (one of twelve
   points may differ: float32 discontinuities), engine 3D/DC/pre-post tests, flame 3D attribute round trip,
   formula browser test, `test_info_panel.py` (6). **1345 passed** at the last full run.

Also fixed: the `.flame` reader treated `modulus` / `modulus_x` / `modulus_y` as transform attributes (a
baseline assumption); they are the `modulus` plugin, which is now in the library — flames using it rendered
black before.

## Known gaps / next steps
* Not available (see `tools/apo_decompile.py --batch` report): DLL-only plugins with loops (tile, tile_hyp,
  tile_plane, hy2, disc2square, fibonacci_blur, bubbleT3D, pre/post_hexcrop, jac_cn/dn/sn/elk, swirl3sin,
  tailblur), prepare-filled array
  members read by index (rod, spherigon, tri_boarders2, hexaplay3D, hexnix3D), `dc_image` (needs image I/O),
  Knot/Nabla (generated megasources), gamma (lgamma in GLSL), mandel2/pRose3D (path explosion), some 64-bit-only
  DLLs (LazySensen, invpolar: RIP-relative SSE code not finished), chunk/pre_chunk (2-of-12 boundary points).
  The decompiler would need structured loop reconstruction for the first group.
* CPU speed of a few compiled formulas is low (crackle ~20 µs/point, eMod ~3 µs/point): both branches of every
  divergent `if` are evaluated; the GPU path is fine.
* The editor that lets users pick formulas and edit parameters is the next feature; `Variation.param_info`
  (type, default, min/max, cyclic, non-zero) is ready for it, and `FormulaBrowser` shows the catalogue.
* `samples/aposource/` is still the raw input (not scanned by the tests); it can be dropped once no longer wanted.

## Previous task log
The review-and-hardening history of the gradient editor / viewer (cycles 0–4, rename, viewer controls) is in git
history (`git show 13a9126:TASK_STATE.md`).
