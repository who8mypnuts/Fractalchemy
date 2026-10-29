# TASK_STATE — Fractalchemy (editor, animation, review cycles)

Branch: `master`, uncommitted working tree on top of `13a9126 baseline`.

## How to resume
```bash
cd /workspace/Fractalchemy
pip install -r requirements.txt                    # + pytest, pyflakes for development; py7zr for the import tool (7z packs)
python3 -m pytest -q --ignore=tests/test_variations.py   # ~8 min (GUI tests on the CPU engine; set QT_QPA_PLATFORM=offscreen)
python3 -m pytest -q tests/test_variations.py      # ~2 min: every formula on numpy *and* GLSL (llvmpipe)
python3 -m pyflakes fractalchemy tests main.py tools
python3 main.py
```
Nothing is committed: the working tree holds the editor / animation work on top of `3fbbded baseline`.

## Review loop (the clean-architecture / DRY / comments / tests pass over the uncommitted changes)
Rubric: architecture 40 (gate 34), DRY 30 (gate 25.5), comments 20 (gate 17), tests 10 (gate 8.5); exit ≥ 90.

### Cycle 1 — findings and repairs
| # | Critic | Severity | Subsystem | Finding / root cause | Correction |
|---|---|---|---|---|---|
| A1 | Architect | high | ui/editor_window | 917-line window mixing construction, 30 actions, triangle operations, a 25-branch command dispatcher | split: `editor_actions.py` (actions / toolbar / menus), `editor_operations.py` (`TransformOperations`: every triangle / transform edit, command table), window = coordination only (≈520 lines) |
| A2 | Architect | high | ui/animation_render_window | 707 lines, four classes | panels → `animation_render_panels.py`; window ≈ 230 lines |
| A4 | Architect + DRY | high | ui/render_window, ui/animation_render_window | identical job life cycle (start / pause / stop / clock / thread end / confirm_quit / closeEvent / layout) written twice | `ui/job_window.py: JobWindowBase`; both windows subclass it |
| A5 | DRY | medium | ui/animation_render_panels | progress panel re-implemented | `AnimationProgressPanel(RenderProgressPanel)` (caption label exposed, `file_link` helper) |
| A3 | Architect | medium | ui/editor_panels | reusable widget buried in the tabs module; widgets importing from ui | `widgets/palette_slider.py`; `palette_pixmap` moved to `widgets/images.py` (no ui → widgets → ui cycle) |
| A9 | Architect | low | ui/editor_preview | "EditorPreview" also serves the Animation window | renamed `ui/live_preview.py: LivePreview` |
| D1 | DRY | medium | ui/render_output_panel, animation panels | `_row` layout helper copied; format / depth combo code copied | `widgets/layouts.py: row`; `fill_format_combo / fill_depth_combo / sync_format_controls` in render_output_panel used by both |
| D2 | DRY | medium | editor / animation windows | two `_action` factories and four separator-loop menu builders | `widgets/actions.py: make_action, populate` |
| D3 | DRY | medium | tests | synthetic mouse helpers copied into two test modules | `conftest.mouse_press / mouse_move / mouse_release / mouse_drag` |
| D6 | DRY | low | editor operations | Shift / Ctrl step scaling written three times | `modifier_factor(coarse, fine)` |
| A6 | DRY | low | ui/editor_window | private `_blocked` class duplicating `widgets.silent.blocked` | removed |
| T1 | Tester | high | widgets/value_table, editor clipboard | `float("nan")` / `inf` accepted as weights / coordinates | non-finite input rejected (test) |
| T2 | Tester | medium | animation/format, model | undecodable file raised `UnicodeDecodeError` past the window; malformed keyframe entries crashed `from_dict` | caught as `AnimationParseError`; non-dict entries skipped, duplicate frames de-duplicated |
| T5 | Tester | medium | ui/live_preview | a `flame_provider` that raises killed the slot | caught and logged; preview clears (test) |
| T6 | Tester | low | ui/animation_document | `set_settings` accepted fps 0 / unknown modes | clamped / rejected |
| T4 | Tester | medium | widgets/timeline | zoom-out floor was a constant, not the fit (a long animation could shrink below fit; short ones could not reach it) | zooming out below fit snaps to fit (test) |
| C1 | Comments | medium | several | public methods without docstrings (`ValueTable` accessors, `LivePreview` state, window option setters) | added |

Tests added: `test_value_table_rejects_non_finite_input_and_supports_name_dragging`, `test_operations_helpers_modifier_factor_auto_zscale_and_clipboard_parsing`, `test_render_job_reports_a_failure_when_nothing_can_be_written`, `test_timeline_hit_testing_zoom_and_ticks`, `test_live_preview_survives_a_failing_flame_provider`.

Regression check (same tests before / after): editor 25 → 27 passed, animation 14 → 17 passed, render window 7 → 7, main window 19 → 19 — **improved**, nothing regressed.
Score after cycle 1 (self-assessed): architecture 33 / 40, DRY 25 / 30, comments 16 / 20, tests 8.5 / 10 = **82.5**.

### Cycle 2 — findings and repairs
| # | Critic | Severity | Subsystem | Finding / root cause | Correction |
|---|---|---|---|---|---|
| A10 | Architect | high | widgets/triangle_view | 830-line widget carrying the drag geometry (rotate / scale / snap maths) inside Qt event handlers — untestable without a widget | `fractal/triangle_drag.py` (pure: `DragState`, `DragSteps`, `begin_*_drag`, `drag`), the view only feeds points (≈700 lines) |
| A11 | Architect | high | ui/editor_panels | 888 lines, six tabs; three list tabs repeating search box + table + count + guard | `ui/editor_value_tabs.py` with a `TableTab` base (`rows()` / `hide_row()` hooks); `editor_panels.py` keeps the geometry / colour tabs (≈530 lines) |
| A12 | Architect | high | ui/animation_window | 658-line window with the settings form, the keyframe list and the playback clock inside | `ui/animation_panels.py` (`AnimationSettingsPanel`, `KeyframePanel`, signal-based), `ui/animation_playback.py` (`Playback`: wall-clock session); window ≈ 380 lines |
| D7 | DRY | medium | ui/editor_panels, editor_window, animation_window | the `_updating = True / try / finally` guard written nine times | `widgets.silent.updating()` context manager |
| D8 | DRY | low | ui/editor_value_tabs | Variations / Variables / Xaos each re-implementing refresh + filter + count | `TableTab.refresh / apply_filter` |
| C2 | Comments | medium | 13 modules | 90 public members without docstrings (properties, accessors, Qt-facing setters) | docstrings added everywhere (AST scan: none missing on public names) |
| T7 | Tester | medium | fractal/triangle_drag | drag maths had only end-to-end coverage through mouse events | `test_drag_maths_move_rotate_scale_and_snapping` (move / rotate / scale, Shift snapping, O with and without axis lock, refused zero scale) |

Regression check: editor 27 → 28 passed, animation 17 → 17, render window 7, main window 19, image panel 20, info panel 6 — **improved**.
Score after cycle 2: architecture 36 / 40, DRY 27 / 30, comments 18 / 20, tests 9 / 10 = **90**.

### Cycle 3 — findings and repairs
| # | Critic | Severity | Subsystem | Finding / root cause | Correction |
|---|---|---|---|---|---|
| A13 | Architect | medium | widgets/icons | the new glyphs were two 120- / 50-line `if / elif` painters inside the icon module; an unknown name silently gave a blank icon | `widgets/glyphs.py`: one small painter per glyph in a `GLYPHS` registry, `glyph_pixmap` raises `KeyError` for unknown names; `icons.editor_icon / animation_icon` are thin wrappers |
| A14 | Architect | medium | animation/render_job | a 40-line frame loop doing sampler set-up, rendering, saving and bookkeeping | `_aim_sampler` + `_render_frame` (one frame each) |
| A15 | Architect | low | ui/editor_panels | `TriangleTab._build` 90 lines with "# rotate row" style markers | `_corners_group / _operations_group / _pivot_group / _options_group` |
| D9 | DRY | low | animation/interpolate | three hand-rolled "union in first-seen order" loops and a nested donor search in `_align_variations` | `_ordered_union`, `_default_parameter`, `_by_distance` reused for xforms |
| D10 | DRY | low | widgets/value_table | modifier → step chain inline, a magic ×100 for integer rows | `drag_step()`, `INTEGER_DRAG_SCALE` |
| C3 | Comments | low | README | layout table named modules that no longer exist (`editor_preview`) | updated for the split modules |
| T8 | Tester | low | widgets/glyphs | glyph painters untested | every registered glyph paints something; unknown names raise (test) |

Regression check: editor 28 → 29 passed, animation 17 → 17 — **improved**; full suite rerun below.
Score after cycle 3: architecture 37 / 40, DRY 28 / 30, comments 18 / 20, tests 9 / 10 = **92**.

### Cycle 4 — findings and repairs
| # | Critic | Severity | Subsystem | Finding / root cause | Correction |
|---|---|---|---|---|---|
| A16 | Architect | low | animation/render, animation_render_panels | video formats were positional tuples read by index (`[2]`, `[4]`) | `VideoFormat` dataclass + `video_format(key)` |
| D11 | DRY | low | ui/render_window, ui/animation_render_window | `RateHint` alias defined twice | once, in `render/estimate.py` |
| D12 | DRY | low | widgets/timeline | tick candidates inline; the Shift-scroll amount an opaque expression | `TICK_STEPS`, `LABEL_SPACING_PX`, "a tenth of the view per notch" |
| C4 | Comments | low | ui/editor_actions, animation_window | `lambda` action shorthands carrying `noqa` | small inner `act()` functions |
| C5 | Comments | low | ui/editor_value_tabs, editor_panels, fractal_document | overriding hooks / structural edits without their own docstrings | added |
| T9 | Tester | — | — | no new behaviour this cycle; regression run only | full suite: see below |

Regression check: full suite (without `test_variations`) 344 → 346 passed, 1 skipped; `test_variations` 1135 passed — **improved / unchanged**, nothing regressed.
Final score (self-assessed): architecture 37 / 40 (92 %), DRY 28 / 30 (93 %), comments 18 / 20 (90 %), tests 9 / 10 (90 %) = **92 / 100**; every gate ≥ 85 %, no critical failures, pyflakes clean.

Known residue (not fixed, judged below the bar for this pass): the baseline modules the pass did not touch (`render/compiled.py`, `render/codegen.py`, `ui/fractal_viewport.py`, …) still have undocumented public one-liners; `widgets/triangle_view.py` (≈700 lines) mixes painting and hit-testing and could lose its painters to a helper; `AnimationWindow` and `EditorWindow` each re-implement `bring_to_front` (as the older Gradient Library does).

### Last successful commands
```
python3 -m pyflakes fractalchemy tests main.py tools          # clean
python3 -m pytest -q --ignore=tests/test_variations.py          # 346 passed, 1 skipped
python3 -m pytest -q tests/test_variations.py                    # 1135 passed
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
   (since removed — the Guides button took its place, see 13); progress bar in permille (int32 overflow at zoom); GPU shader build
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

12. **Script Editor** (*Windows ▸ Script Editor*, `F8`, toolbar button; `actionScriptEditor` in `main_window.ui`,
    `MainWindow.script_editor` created lazily and hidden on close). Qt-free engine in `fractalchemy/scripting/`:
    `api.py` (`ScriptContext.namespace()`: `flame`, `transforms` / `transform` (live active-transform view), `camera`,
    `gradient`, `xaos`, `coloring` helpers + functions + Apophysis aliases; `ScriptHost` callbacks for output /
    prompts / `update()`; `ScriptError`, `ScriptStopped(BaseException)`), `runner.py` (`run_script`: compile, exec
    with a `sys.settrace` stop check on script frames only, `ScriptResult` / `ScriptErrorInfo` with the script line),
    `docs.py` (`GLOBALS` / `TYPES` / `CATEGORIES` / `options()` / `GUIDE` — the reference database; the tests check
    it against the real API), `completion.py` (`complete()` / `context()`: chain resolution through the docs,
    locals inferred from assignments / for-loops / `for_each_transform` lambdas, option lists inside strings and
    subscripts, keyword arguments), `generate.py` (`flame_to_script`), `templates.py` (`builtin_templates/*.py` with
    `# @name / @category / @description` headers; user templates as `.py` files in `user_script_dir()/templates`).
    UI: `widgets/code_editor.py` (`CodeEditor`: line numbers, `PythonHighlighter`, `CompletionPopup` = tool-tip
    window + doc box, editing keys), `ui/script_runner.py` (`ScriptRunner`: worker thread, blocking request /
    `reply()` protocol, `stop()`), `ui/script_drawer.py` (`ScriptDrawer` tabs: `ContextTab`, `ReferenceTab`,
    `InfoTab`, `TemplatesTab`), `ui/script_editor_window.py` (`ScriptEditorWindow`: toolbar / menus, `FindBar`,
    `OutputPanel`, run / stop / revert / check / Flame → Script / templates, QSettings `script/*`).
    `CollapsibleSplitter(collapse_last=True)` makes a two-pane splitter collapse its right pane (the drawer).
    `FractalDocument.apply_script(flame, run)`: one undo step per run (intermediate `update()` calls share it).
    Fixes on the way: the viewport now re-renders on `flame_restored` (undo / redo / paste did not re-render
    before), `random_flame.sample_points` imported the renamed `_Worker` (now `PointPopulation`), so
    `frame_camera` — Random Batch framing and `camera.fit()` — works again. `docs/scripting.md` is generated by
    `tools/scripting_reference.py`. Tests: `tests/test_scripting.py` (23).

13. **Viewer bar**: the *Detail* (Full / ½ / ¼) dropdown and `FractalViewport.render_scale` are gone. **Guides**
    (`ViewerBar.guides_button`, a checkable tool button with a menu of `GUIDE_KINDS`: thirds / golden / center;
    `guides_changed(bool, kinds)`, `set_guides`, `guide_kinds()`) overlay composition lines on the whole image:
    `FractalViewport.set_guides` / `guide_lines()` / `_paint_guides` (`GUIDE_FRACTIONS`, a dark halo under each
    line). *View ▸ Show Guides* (`actionShowGuides`, `Ctrl+G`) mirrors the button; QSettings `viewer/guides`,
    `viewer/guide_kinds`.

14. The Image tab's **Y pitch** row is gone (it was Fractalchemy's own `cam_pitch_y`, of little visible use); the
    `Camera.pitch_y` field, its file round-trip and the scripting API's `camera.pitch_y` stay.

15. **Transform Editor** (Apophysis's editor; *Windows ▸ Transform Editor*, `F4`, toolbar). Model: `XForm.pre`
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
    Triangle / Transform / Colors tabs), `ui/live_preview.py` (throttled mini preview at `PRIORITY_EDITOR`),
    `ui/editor_window.py` (toolbar, the three mode buttons styled with `config.HIGHLIGHT_COLOR`, menus, settings).
    The viewport debounces transform edits (`EDIT_RENDER_DELAY_MS`, cancels the running render) and now also
    re-renders on `flame_restored` (undo / redo / paste did not re-render before). `config`: `HIGHLIGHT_COLOR`,
    `EDIT_RENDER_DELAY_MS`, `EDITOR_PREVIEW_*`. Icons: `editor_icon(name)`. Tests: `tests/test_editor.py` (19).
    `tests/conftest.py` skips `samples/apophysis-7x/` (the Apophysis source tree) like `aposource`.
    Round 2: Apophysis's **variation preview** (`render/xform_preview.py`: grid ±range at density·5 per unit
    through `apply_xform` `depth` times; `TriangleView.set_variation_preview` plots the dots through numpy into
    an image; toolbar `act_var_preview` / key `V`; sliders on the Colors tab; QSettings `editor/var_preview*`),
    and the preview **quality levels** as `QualityLevel`s (`ui/live_preview.py`: Low 2 spp, Medium 5 spp +
    oversample 2 / filter 0.5, High 15 spp, 2 passes; `quality_level()` maps names / numbers; the box is 380×240).

16. **Animation** (*Windows ▸ Animation*, `F9`, toolbar). `fractalchemy/animation/`: `model.py` (`Keyframe`,
    `Animation`: fps / total_frames / interpolation linear|smooth|hold / easing / loop / keyframes / render dict;
    set / move / remove keyframes, `flame_at`), `interpolate.py` (`blend_plan` → keyframe weights: linear, uniform
    Catmull-Rom with clamped or looped ends, hold; `align_flames` pads transforms at weight 0, unions variations
    and parameters, final everywhere if anywhere, palettes resampled; `blend_flames` mixes every number, dominant
    keyframe for names / size / curves), `format.py` (`.faanim` JSON: `fractalchemy-animation` v1), `render.py`
    (`AnimationRenderSettings` wrapping `FinalRenderSettings` + folder / base name / range / step / skip existing /
    video options; `ffmpeg_command`, `video_problems`, `ffmpeg_path`), `render_job.py` (`AnimationRenderJob`
    QThread: one sampler reused through `Sampler.set_flame` — new `"flame"` worker command in `cpu_workers`,
    `GpuSampler.set_flame`; `FinalRenderer(sampler=…)` reuses it — frames saved with `output.save_image`, then
    ffmpeg via subprocess; progress / outcome dataclasses). UI: `ui/animation_document.py` (AnimationDocument),
    `widgets/timeline.py` (ruler, diamonds, playhead, scrub / drag / zoom), `ui/animation_window.py` (toolbar,
    preview = `LivePreview` with a `flame_provider`, wall-clock playback with frame dropping, keyframe list,
    settings; clicking a keyframe calls `MainWindow.show_flame`), `ui/animation_render_window.py` (SizePanel +
    QualityPanel reused, `AnimationOutputPanel`, `VideoPanel`, `AnimationProgressPanel`; settings in QSettings
    `animation_render/settings` and in the `.faanim` `render` key). Icons: `animation_icon()`, `editor_icon("anim-*")`.
    `SizePanel.preview_label` lets the first preset read "Keyframe size". Tests: `tests/test_animation.py` (14).

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
* Script Editor: no "record actions as script" yet; `update(wait=True)` waits for the first render pass or 2.5 s.
* Animation: interpolation is by index (transform 1 blends with transform 1); there is no per-keyframe easing, no
  motion blur, and the timeline has no undo. Rotation of affines interpolates the coefficients (flam3's
  linear mode), not angles — a 180° turn passes through a collapsed triangle.
* Transform Editor: no rotate / scale widget grips around the selected triangle (edges and modifier keys cover it);
  `ParamInfo.min/max` are shown in tooltips but not enforced; the pre affine is an editing convenience (it
  composes with the normal affine), so it adds no new shapes — placing it after the `pre_` variations instead
  would (one-line change in `apply_xform` / `_xform_function`).
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


## Formula Editor (added after the review cycles)
*Windows ▸ Formula Editor* (`F10`, toolbar: the *ƒv* sheet). Write a formula in the plugin dialect and see it work live.

* `formulas/workbench.py` (Qt-free): the reserved registry slot `SCRATCH_NAME = "(formula editor)"` — not a C identifier,
  so no real formula can clash and `variations.catalogue()` (new; every listing site uses it) leaves it out —
  `compile_formula`, `register_scratch`, `source_of` (a `.c` file's text, or a dialect skeleton carrying a native
  built-in's numpy + GLSL), `new_formula_text` (the boilerplate), `prepared_xform` (a `pre_` / `post_` formula gets
  `linear` beside it at render time, so the document's flame is never touched), `error_line`.
* `ui/formula_session.py`: `FormulaSession` — the text, name, file and origin of the formula being edited, the debounced
  background compile (`run_in_background`, stale results dropped, last good variation kept in the slot while the text
  is broken), `save()` (the user's folder, registered at once under the real name), `delete()` (file + `load_all(force)`),
  drafts for QSettings.
* `ui/formula_editor_window.py`: its own `FractalDocument` (undo / redo) + `EditorContext` + `TransformOperations`
  (`FixedSteps`, new in `editor_operations`) + `TriangleView` with the variation preview on; `LivePreview` with a
  `flame_provider`; `FormulaCodeEditor`; `FormulaListPanel` (search, *New formula*); `GradientBar` (click → the
  gradient goes to the Gradient Library, which recolours the main fractal too; from then on its edits follow);
  `FormulaVariablesTab` (the scratch slot shown under the formula's name). Actions / toolbars / menus / context menu
  in `ui/formula_editor_actions.py`.
* `widgets/base_code_editor.py`: the language-independent editor (line numbers, error mark, find / replace, line edits)
  split out of `code_editor.py`; `CodeEditor` (Python) and `widgets/formula_code_editor.py` (C dialect highlighting from
  `lang/builtins.py`) subclass it; `FindBar` moved to `widgets/find_bar.py`.
* `LivePreview`: the last pass no longer releases the slot (the following `job_finished` does) — releasing twice let a
  pending change start a render that was then marked as not in flight.
* `FractalDocument.add_xform(xform=None)` / `xform_ops.add_xform(flame, xform=None)` take a prepared transform.
* Tests: `tests/test_formula_editor.py` (9).
