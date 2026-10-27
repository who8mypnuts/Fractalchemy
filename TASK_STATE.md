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
   `viewport.render_progress`; the chosen tab persists (`panel/tab`). **Image tab** (`ui/image_panel.py`,
   was *Render*): Preview (passes/quality), Camera (zoom `FloatRow` slider+spin around the centre, pan
   arrows via `FractalDocument.pan` in screen axes, centre x/y, rotation), 3D camera (pitch/yaw in degrees,
   perspective, zpos, dof → `Camera` fields, real 3D in both engines), Colouring (brightness, gamma,
   threshold, vibrancy, background `ColorButton` + live `ColorPickerDialog`); per-group ↻ revert to the
   loaded values (`document.original`). `FractalDocument` gained `coloring_changed`, `modified_changed`,
   `set_camera_3d`, `set_coloring`, `pan`, `revert_*`, `mark_saved`; *File ▸ Save Fractal* (`Ctrl+S`) writes
   the flame back with `fractal_format_for(path).replace` (own writes are ignored by the file watcher).
   `FractalViewport.render_camera()` now carries the 3D fields (3D flames rendered flat in the viewport before).
   `samples/sample flames/flamepack1.flame` (27 flames incl. the 3D "3d musk sphere") added; all supported.
7. **Tests**: `test_formula_lang.py` (compiler features), `test_formulas_loader.py` (user folders, override,
   cache, errors), `test_variations.py` now runs every registered formula through both engines (one of twelve
   points may differ: float32 discontinuities), engine 3D/DC/pre-post tests, flame 3D attribute round trip,
   formula browser test, `test_info_panel.py` (6), `test_image_panel.py` (8: document setters, pan geometry,
   FloatRow, panel ↔ document, save round trip, preview options, undo/paste, curves, file flows, opened-file area), `test_random_batch.py` (6). **1376 passed** at the
   last full run.

Also fixed: the `.flame` reader treated `modulus` / `modulus_x` / `modulus_y` as transform attributes (a
baseline assumption); they are the `modulus` plugin, which is now in the library — flames using it rendered
black before.

8. **Preview quality** (no denoising): histogram = supersampled buckets + gutter (`RenderSettings.bucket_size`,
   `render/filtering.py` = Apophysis `CreateFilter`), tone map in two stages (per-bucket log scale →
   kernel gather → gamma; `SCALE_GLSL` + `TONEMAP_GLSL`, numpy `tonemap(hist, params, os, radius, size)`);
   continuous refinement (`refine_to`, doubling passes, `RenderStats.samples_target/refining/quality`),
   `RenderService` pauses/resumes pre-empted jobs (`_paused`, `PRIORITY_REFINE`); Apophysis zoom rule
   (`for_zoom`, `density_scale`); `within_bucket_limit` memory guard; Image tab ▸ Preview has Oversample /
   Filter / Keep refining (persisted: `preview/oversample|filter|refine_to`); status bar shows `q`.
   `Flame.oversample/filter_radius` round-trip the file's own hints. Tests run with `PREVIEW_REFINE_TO = 0`
   (conftest) so GUI renders finish quickly; `test_render.py` covers refinement + yielding.

9. **Image tab round 2**: `Camera.pitch_y` (tilt about the vertical axis; full 3×3 matrix in `projection.py`
   numpy + GLSL; `cam_pitch_y` in .flame, `pitch_y` in .fa); contrast control; "Coloring"; pan arrows move
   0.1 / Shift 1 / Ctrl 0.01 fractal units (`FractalDocument.pan_units`, `ImagePanel.pan_step`); tone curves
   (`fractal/curves.py` model + monotone cubic, `widgets/curve_editor.py`, tonemap LUTs numpy + GLSL,
   `fa_curves` attribute, Apophysis `curves` import); undo/redo (`FractalDocument._record` with 1 s
   coalescing, `flame_restored`, `undo_changed`); Save / Save As ▾ (`ui/fractal_file_actions.py`: replace /
   append / new file / into file, background writes, `file_written`), Copy / Paste Parameters
   (`formats.flame_to_text/flame_from_text`: .fa JSON, `<flame>` XML, Chaotica world); viewer-bar **Detail**
   (`FractalViewport.render_scale`); progress bar in permille (int32 overflow at zoom); GPU shader build
   failures dump sources + log to `cache_dir()/glsl-failures` (`ShaderBuildError`).

10. **Toolbar icons** (`widgets/icons.py: action_icon`: theme icons when the platform has them, painted
    look-alikes otherwise; Save As shares the save icon + menu arrow) and the **opened-file area**: `Kind.SEPARATOR`,
    `LibraryItem.temporary` (part of the model key), `LibraryModel.set_open_file/open_file`, tree delegate paints
    the line, `LibraryWatcher.watch_file` + `loose_file_changed`, `LibraryController.show_file/rescan_open_file`
    (`rescan_containing` covers it), `MainWindow.open_file_path`; Save As into a file outside the library shows it there.

11. **Random Batch** (`fractal/random_flame.py`: Apophysis `RandomFlame` recipes, `RandomVariation`, area /
    equal weights, blow-up rejection, `frame_camera` from a short CPU iteration, random gradient via `reroll`;
    `ui/random_batch_window.py`: registry list with check boxes, debounced filter, check/uncheck listed, count,
    transform range, background generation, QSettings `random/*`). Generated flames live in memory:
    `LibraryItem.virtual`, `LibraryModel.set_open_file(..., virtual=True)` / `open_file_is_virtual`,
    `LibraryController.show_virtual`, `ThumbnailProvider.set_virtual`, `MainWindow.show_random_batch /
    show_batch_entry` (heading "Randomly Generated" in the temporary area; context menu = Open only; no drag).
    Icons: `action_icon("save-as")` (diskette + pencil), `action_icon("random")` (die).

12. **Transform Editor** (Apophysis's editor; *Windows ▸ Transform Editor*, `F4`, toolbar). Model: `XForm.pre`
    (the third affine, applied before `coefs`; `has_pre`, `combined_coefs`, `compose_affine`; `.flame` attribute
    `pre_affine`, `.fa` key `pre`; Chaotica export folds it), both engines apply it (`CompiledXForm.pre_affine`,
    `cpu_engine.apply_xform`, `codegen._xform_function`, identical output to the composed affine — tested CPU and
    GPU). `fractal/triangles.py` (affine ⇄ X/O/Y triangle in editor space = y up; move / rotate / scale / flip /
    snap / reset ops; hit tests), `fractal/xform_ops.py` (add / duplicate / link / delete with xaos rows kept
    consistent, final on/off, area weights). `FractalDocument`: `xform()`, `edit_xform` (undoable, coalescing,
    `sticky` for drags), `set_affine / set_xform_fields / set_variation / clear_variations / set_param / set_chaos /
    set_all_chaos / add_xform / duplicate_xform / add_linked_xform / delete_xform / set_final_enabled /
    area_weights / replace_flame_parameters`, signals `xform_changed(index | None, what)` and `transforms_changed`.
    UI: `widgets/triangle_view.py` (the canvas: modes, pivot, edges, helpers, keys, context menu),
    `widgets/value_table.py` (name / value table with Apophysis's drag-the-name editing), `ui/editor_context.py`
    (selection + affine mode `pre` / `coefs` / `post`), `ui/editor_panels.py` (Variations / Variables / Xaos /
    Triangle / Transform / Colors tabs), `ui/editor_preview.py` (throttled mini preview at `PRIORITY_EDITOR`),
    `ui/editor_window.py` (toolbar, the three mode buttons styled with `config.HIGHLIGHT_COLOR`, menus, settings).
    The viewport debounces transform edits (`EDIT_RENDER_DELAY_MS`, cancels the running render) and now also
    re-renders on `flame_restored` (undo / redo / paste did not re-render before). `config`: `HIGHLIGHT_COLOR`,
    `EDIT_RENDER_DELAY_MS`, `EDITOR_PREVIEW_*`. Icons: `editor_icon(name)`. Tests: `tests/test_editor.py` (19).
    `tests/conftest.py` skips `samples/apophysis-7x/` (the Apophysis source tree) like `aposource`.

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
* Random Batch has no symmetry options yet (Apophysis: bilateral / rotational); parameters stay at defaults.
* Transform Editor: no variation-preview grid (Apophysis's *Toggle variation preview*) and no rotate / scale
  widget grips around the selected triangle (edges and modifier keys cover it); `ParamInfo.min/max` are shown
  in tooltips but not enforced; the pre affine is an editing convenience (it composes with the normal affine),
  so it adds no new shapes — placing it after the `pre_` variations instead would (one-line change in
  `apply_xform` / `_xform_function`).
* *Save* rewrites the `<flame>` element from the model, so attributes we do not model (`plotmode`, `animate`,
  motion, `estimator_*`) are dropped from that entry; coloring / curve edits re-render instead of
  re-tonemapping the kept histogram (a possible speed-up, now that jobs can be kept alive).
* The user reports rare GPU shader build failures (crackle, edisc) on their driver that fall back to the CPU;
  not reproducible on llvmpipe (40 random crackle/edisc flames compiled) — the diagnostics file is the next step.
* On software OpenGL (llvmpipe, as in the test sandbox) refinement to q 500 takes minutes; on a real GPU
  seconds. The GPU plot pass is one draw of `PREVIEW_POINTS` points per iteration — batching several
  iterations per draw would cut driver overhead further if throughput matters.
* `samples/aposource/` is still the raw input (not scanned by the tests); it can be dropped once no longer wanted.

## Previous task log
The review-and-hardening history of the gradient editor / viewer (cycles 0–4, rename, viewer controls) is in git
history (`git show 13a9126:TASK_STATE.md`).
