# TASK_STATE — Fractalchemy review & hardening pass

Branch: `master` (uncommitted working tree on top of `c366985 baseline`). **Do not commit.**

## How to resume
```bash
cd /workspace/Fractalchemy
pip install -r requirements.txt            # PySide6, Pillow, pillow-heif, pillow-jxl-plugin (+ pytest, pyflakes for dev)
QT_QPA_PLATFORM=offscreen python3 -m pytest -q   # conftest sets offscreen automatically
python3 -m pyflakes fractalchemy tests main.py
```

## Last successful commands
- `python3 -m pytest -q` → **119 passed** (run twice, stable)
- `python3 -m pyflakes fractalchemy tests main.py` → clean
- `python3 -m compileall -q fractalchemy main.py tests` → ok
- docstring audit (`/tmp/doccheck.py`, AST scan of public defs) → 0 / 314 missing
- offscreen UI smoke test (library + browser + node picker + whole-gradient panel) → renders, status bar correct

## Known failures
- none. (Timing-sensitive library tests use `wait_until`; if a CI box is very slow, raise `timeout_ms` in `tests/conftest.py`.)

## Rubric score (evidence in the cycle sections below)
| Cycle | Architecture /40 | DRY /30 | Docs /20 | Tests /10 | Total | Label vs previous |
|---|---|---|---|---|---|---|
| 0 (baseline) | 30 | 22 | 10 | 8 | 70 | — |
| 1 | 33 | 27 | 10 | 8.5 | 78.5 | improved |
| 2 | 35 | 27.5 | 18 | 8.5 | 89.0 | improved |
| 3 | 35 | 27.5 | 18 | 9.5 | 90.0 | improved |
| 4 | 36 | 28 | 18.5 | 9.5 | **92.0** | improved |

Exit gates: total ≥ 90 ✔ · every dimension ≥ 85 % (36/40=90 %, 28/30=93 %, 18.5/20=92.5 %, 9.5/10=95 %) ✔ · zero critical failures ✔ · compiles & tests pass ✔

## Findings log
(see "Cycle N" sections appended below)

## Cycle 1 — findings (critic pass on the uncommitted tree)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 1 | DRY | High | model, widgets | RGB↔HSL conversion implemented 3× (`adjust.shift_hsl`, `operations._hsl_rgb`, `color_dialog._to_hsl/_to_rgb`) | features added incrementally | single `rgb_to_hsl` / `hsl_to_rgb` in `model/color.py` |
| 2 | DRY | High | formats | UGR stop/title parsing duplicated in `ugr.py` (`_ENTRY`, `_TITLE`, pack/unpack) vs `ufparams.py`, and again in `clipboard.py` | `ufparams` was added later for `.ufr` | `ugr.py` parses via `ufparams`; exposes `parse_gradient_text` used by clipboard; pack/unpack re-exported |
| 3 | DRY | Med | formats | `_xml_attr` (flame) = `_xml` (chaos); `ufr._newline` duplicates `TextFile` newline detection | per-module helpers | shared `textfile.xml_attr`, `textfile.detect_newline` |
| 4 | DRY | Low | widgets | luminance formula repeated in `qt_colors.contrasting_pen_color` | copy of `color.luminance` | reuse `model.color.luminance` |
| 5 | Architect | Med | formats/flame | `_append_text` writes a brand-new file twice with an awkward branch | grown by patching | build in memory, write once |
| 6 | Architect | Med | formats/chaos | `save` and `rename` duplicate IFS span discovery | copy-paste | `_palette_spans(doc)` helper |
| 7 | Architect | Low | ui/document, library/model | function-local imports with no cycle to justify them | caution | top-level imports |
| 8 | Architect | Low | formats/clipboard, imaging/plugins | `__all__` used to silence unused imports | lint appeasement | delete the unused imports |
| 9 | Defensive | High | ui/file_actions | `_loaded` indexes `gradients[-1]` on an empty list → IndexError inside a Qt slot (flame file with no palettes) | flame loader may return `[]` | worker raises `FormatError`; handled by the existing error path |
| 10 | Defensive | Med | library/scanner | symlinked directory cycles recurse forever | `iterdir` follows symlinks | skip directory symlinks |
| 11 | Defensive | Low | ui/file_actions | `_run_write` infers the written path with `next(isinstance(Path))` | convenience | explicit `path` argument |
| 12 | Architect | Low | formats/ufr | `_Ufr.encode()` mutates the header as a side effect | in-place `pack_into` | encode against a copy |
| 13 | Comments | High | all | 251/309 public defs lack Google-style docstrings | speed of iteration | systematic pass in Cycle 2 after structure settles |
| 14 | Defensive | Med | tests | no tests for background-task error path / thread affinity, empty flame file, symlink loop | — | add focused tests |

### Cycle 1 — result
- Fixed: #1–#12, #14 (tests added: `tests/test_background.py`, empty-flame load, symlink loop). #13 deferred to Cycle 2.
- Regression check vs baseline: **improved** — all 106 prior tests still pass + 4 new (110). One regression caught and fixed during
  the cycle: eager colour parsing in `ugr.parse_blocks` slowed `names()`/span lookup (made lazy via `ParsedBlock.gradient()`).
- Commands: `python3 -m pytest -q` → 110 passed; `python3 -m pyflakes fractalchemy tests main.py` → clean.
- Score: Architecture 33/40 · DRY 27/30 · Docs 10/20 · Tests 8.5/10 → **78.5** (below exit; docs dimension below gate)

## Cycle 2 — findings & result
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 15 | Comments | High | all | 239 public defs undocumented | — | Google-style docstrings on all 313 public defs (Args/Returns/Raises/Signals/Attributes where non-trivial); verified by `/tmp/doccheck.py` → 0 missing |
| 16 | Comments | Med | model, ui, widgets | inline field/signal comments duplicating the new docstrings | docstrings added after the fact | removed; signals only described inline got `Signals:` sections instead |
| 17 | Architect | Med | ui/file_actions | 240 lines mixing dialogs, state and Qt-free worker functions | grown over several features | workers moved to `ui/file_workers.py` (73 lines); `file_actions.py` now 199 |
| 18 | Architect | Low | widgets/node_panel | panel computed the colour dialog's screen position | convenience | `ColorPickerDialog.show_beside(anchor)` owns placement |
- Regression check vs Cycle 1: **improved** — 110 passed, pyflakes clean, behaviour unchanged (pure refactors + docs).
- Score: Architecture 35/40 · DRY 27.5/30 · Docs 18/20 · Tests 8.5/10 → **89.0** (all dimension gates met; total 1 point under exit)

## Cycle 3 — findings & result (Defensive Tester focus)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 19 | Defensive | High | ui/file_actions | `confirm_discard` proceeded (edits lost) when the user chose Save but cancelled the save-file dialog | save methods returned nothing | save methods return whether a write started; `confirm_discard` returns that; test added |
| 20 | Defensive | Low | library/operations | error text "New Image files cannot be created here" unclear | wording | "Gradients cannot be saved as new Image files" |
| 21 | Defensive | Med | tests | no coverage of: missing/unsupported file open, cancelled prompts, library op failure signal, `unique_path`, roots rejecting files, drop refusal | — | `tests/test_failure_paths.py` (9 tests) |
- Manual wiring check: `btnSave`, `actionSave`, `actionSaveAsNewEntry`, `actionSaveAsNewFile` all drive the right flow with the new `bool` returns (PySide drops the `checked` argument).
- Regression check vs Cycle 2: **improved** — 119 passed, pyflakes clean; prior behaviour unchanged except the intended abort on cancelled save.
- Score: Architecture 35/40 · DRY 27.5/30 · Docs 18/20 · Tests 9.5/10 → **90.0**


## Cycle 4 — findings & result (final Architect / DRY sweep)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 22 | DRY | Low | widgets | `blockSignals(True) … setValue … blockSignals(False)` repeated 5× | per-widget copies | `widgets/silent.py: set_value_silently()` (QSignalBlocker; applies range first so clamping can't emit) |
| 23 | Architect | Low | widgets/color_dialog | `_build` (34 lines) mixed field configuration with layout | growth | `_configure_fields()` split out |
| 24 | Defensive | Low | widgets/node_panel | during the #22 refactor `setRange` briefly moved outside the signal block (clamping would re-enter `select`) | refactor slip caught in review | range passed into `set_value_silently` |
- Regression check vs Cycle 3: **improved** — 119 passed ×2, pyflakes clean, compileall ok, UI smoke test ok.
- Remaining, deliberately not changed (out of scope / would expand dependencies): undo/redo stack; `QFileSystemWatcher` per-file cap is a heuristic; `.ufr` header layout is reverse-engineered (documented in `formats/ufr.py`).

## Review-loop summary
Four complete build → critique → diagnose → fix cycles were run. Systemic issues (duplicated colour/UGR parsing,
crash on empty flame files, destructive Save-As semantics already fixed earlier, lost edits on cancelled save) were
fixed before polish (docstrings, comment pruning, layout-method splits). No code was committed.

## Rename & window split (HueClid → Fractalchemy)
- Package `hueclid/` → `fractalchemy/`; `config.APP_NAME = "Fractalchemy"`, `LEGACY_APP_NAME = "HueClid"`;
  `settings.migrate_legacy_settings()` copies the saved library folders over on first run (tested).
- `ui/main_window.py` is now the shell (File / Edit / View / **Windows** / **Help**, toolbar, status bar,
  placeholder centre). The old main window became `ui/gradient_library_window.py: GradientLibraryWindow`
  (`ui/gradient_library_window.ui`), a child tool window with its own File / Edit / View menus so its
  shortcuts keep working; closing it hides it. Opened via *Windows ▸ Gradient Library* (`F6`) or the
  toolbar button (tooltip "Gradient Library"; icon painted at run time in `widgets/icons.py`).
- Main window `closeEvent` now runs `confirm_discard()` (previously unsaved edits were lost silently on quit).
- Tests: editor tests target `GradientLibraryWindow`; `tests/test_main_window.py` covers the shell;
  `conftest.sample_files()` / `copy_samples()` skip `samples/aposource/` (the Apophysis reference source,
  which had broken `test_every_sample_loads` and the library scan tests).
- `python -m pytest -q` → 132 passed; pyflakes clean.

## Fractal viewer, dual-engine rendering, Fractal Library
- `fractalchemy/fractal/`: shared scene (`Flame`/`XForm`/`Camera`/`Coloring`), `variations.py` (≈50 variations, each
  with numpy + GLSL; aliases for 3D names; z-only variations are no-ops), `formats/` (.flame read/write, .chaos read,
  .fa JSON read/write + entry ops, registry).
- `fractalchemy/render/`: `RenderSettings`/`RenderStats`, `CompiledFlame`, `tonemap.py` (Apophysis ImageMaker maths,
  numpy + GLSL), `cpu_engine.py` (numpy, thread pool), `codegen.py` + `gpu_engine.py` (moderngl: TF iterate → additive
  point plot → GPU tone map), `service.py` (QThread, priority queue, supersede/cancel, pre-emption of thumbnails).
- Library generalised with `library/catalog.py` (`GRADIENT_CATALOG`, `FRACTAL_CATALOG`); `Kind.GRADIENT` → `Kind.ENTRY`;
  model gained lazy thumbnails; payload tagged per library.
- Main window: `FractalLibraryPanel` (search, collapse, list/thumbnail buttons) | `FractalViewport` (wheel zoom about
  cursor, drag pan, half-res while interacting, full-res after settle, generation keys) ; status bar via `RenderStatus`
  (fractal facts · engine/samples/rate · Pass n of N · progress). Edit menu → "Edit Fractal Library…".
- Tests: `test_variations.py` (numpy ≡ GLSL), `test_fractal_formats.py`, `test_render.py` (tone map numpy ≡ GLSL, engines,
  service), main-window tests for library/viewport/status/thumbnails. GL tests skip when no context is available.
- `python -m pytest -q` → 263 passed; pyflakes clean. Mesa/llvmpipe provides GL in the sandbox (slow but exact).
- Known gaps: Chaotica brightness scale is a heuristic (`BRIGHTNESS_SCALE`); Chaotica xaos direction assumed
  (column = "weights into iterator"); plugin variations not ported (collideoscope, crackle, bwraps7, …) are ignored;
  3D camera (pitch/yaw/perspective) ignored; no density-estimation filtering in the preview.

## Gradient Library ⇄ viewport link
- `ui/gradient_link.py: GradientLink` — fractal chosen → gradient editor shows the same (path, index) entry
  (`files.open_path`) or a loose copy (`files.show_gradient`); gradient edits / other gradient chosen →
  `FractalDocument.set_gradient` → `palette_changed` → viewport interactive re-render. Own-entry loads don't push back.
- `formats/fa_palette.py`: `.fa` as a gradient format (same indices as the fractal side), registered in the gradient registry.
- `widgets/fractal_preview.py`: mirror of the viewport image, placed right of the gradient strip (`fractalPreview` in the .ui).
- Status-bar labels no longer force a minimum window width (engine name → tooltip); main splitter gives resizes to the viewport.
- `FileActions._run_write` records the write before starting it (watcher event vs. completion callback race).
- Tests: `tests/test_gradient_link.py` (10). Suite: 273 passed, pyflakes clean.

## Viewer controls (resolution, view vs. camera pan/zoom, settings panel, status bar)
- `CollapsibleSplitter` now supports three panes (first and last collapse; `set_last_collapsed`, `last_collapsed_changed`).
- `Camera.at_size(w, h)`; `FractalDocument.image_size` / `set_image_size` / `image_size_changed`.
- `FractalViewport` rewritten: image framing + view zoom/offset (`set_zoom`, `pan_view`, `zoom_to_fit`, `fit_zoom`,
  `min_zoom`, `MAX_ZOOM` 3.0), `render_camera()` renders only the visible region; plain drag/wheel = view,
  Ctrl+drag/wheel = composition (`zoom_camera_at`), double-click recentres.
- `ui/viewer_bar.py` (zoom combo + Fit, image-size combo with presets / Custom), `ui/settings_panel.py` (tabs; Render:
  passes, quality; persisted via `attach_settings(QSettings)`), `RenderSettings.with_effort`.
- `RenderStatus` rebuilt: fixed widths from font metrics + separators → no overlap at any DPI.
- `MainWindow(..., settings=)`; View menu: Show/Hide Settings Panel (Ctrl+Shift+L), Zoom to Fit (Ctrl+0), Zoom 100% (Ctrl+1).
- Tests: `tests/test_viewer_controls.py` (11). Suite: 284 passed, pyflakes clean. Tests must pass `settings=` to
  MainWindow or they write to the real QSettings store.

## Undo/redo, copy/paste, save, opened-file section
- `FractalDocument` now owns a `QUndoStack` of whole-flame snapshots (`edit()`, merge ids for camera / gradient sweeps);
  `modified` = not clean; `mark_saved` → `source_changed`; `flame_edited(str)` after edits/undo/redo.
- `ui/fractal_file_actions.py`: open (announces `file_opened`), save (replace entry; lossy warning for unsupported
  variations; .chaos → Save As), save_as (.fa default, append to existing multi-flame files, whole-file write otherwise),
  copy (fa/flame/chaos), paste (auto-detect), confirm_discard, wrote_recently.
- `fractal/formats/clipboard.py`; Chaotica writer `flame_to_ifs` / `flames_to_world` + `parse_text`; `write_file` on all formats.
- Library: `Kind.SEPARATOR`, `LibraryModel.set_opened_file/clear_opened_file/opened_file/root_rows`, separator delegate
  in `LibraryTree`, `LibraryWatcher.watch_file`, `LibraryController.set_opened_file/refresh_opened_file`.
- `GradientLink` tracks `_synced_palette` (editor ↔ flame) so undo/redo refresh the editor without false prompts.
- `widgets/icons.action_icon()` (theme icon or painted glyph); toolbar: open, save, save-as, undo, redo, copy, paste, gradient.
- Tests: `tests/test_fractal_files.py` (13). Suite: 297 passed, pyflakes clean. Test fixtures must `undo_stack.setClean()`
  before closing windows (closeEvent prompts for unsaved fractal edits).

## Save As submenu (multi-fractal files)
- `FractalFileActions.save_as_new_entry / save_as_new_file / save_as_into_file` (+ `_ask_name`, `_append_to`); `_saved(...,
  renamed=True)` renames the document to the saved entry (`FractalDocument.flame_renamed`).
- `menuSaveAs` in File menu; inserted on the toolbar in code after Save (QUiLoader ignores menus in toolbars), InstantPopup.
- `MainWindow._refresh_save_targets` enables "Add to This File" only for appendable sources. Suite: 298 passed.

## Fixes: default file name, gradient nodes jumping
- `suggested_file_name(folder, suffix)` → `FA-YYMMDD-N` (lowest unused N); used by New File….
- `GradientLink.apply_gradient` guards `set_gradient` with `_syncing`: `flame_edited` fired mid-edit and `_on_flame_edited`
  re-synced (resampled) the editor from the flame, moving every node. Regression test
  `test_dragging_a_node_leaves_the_other_nodes_alone`. Suite: 300 passed.

# Review & hardening pass 2 (this session's branch)
Scope: everything above under "Rename & window split" … "Fixes" (uncommitted). Baseline before cycle 1:
`python -m pytest -q -p no:cacheprovider` → 300 passed; pyflakes clean.

## Cycle 1 — findings (systemic first)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 1 | Architect | High | ui/fractal_viewport | 378-line widget mixes view geometry maths (zoom/offset/clamping/regions) with rendering + Qt events; the maths is untestable without a window | grew feature by feature | extract `ui/view_geometry.py: ViewGeometry` (pure, QtCore types only), viewport delegates; unit tests on geometry |
| 2 | DRY | High | ui/main_window + ui/gradient_library_window | add-folder prompt, Edit-Library dialog, scanning message, error box, panel wiring duplicated in both windows | second library copied from the first | `ui/library_host.py: LibraryHost` used by both |
| 3 | DRY | Med | fractal/formats/flame_xml + chaos_world | `_g` / `_attr` number & attribute text helpers duplicated | written separately | `fractal/formats/xml_text.py` |
| 4 | DRY | Med | fractal/formats/fa + formats/fa_palette | JSON document open/validate/write/require helpers duplicated (schema knowledge in two places) | avoided a package import cycle | `formats/fa_document.py` (dependency-free) used by both |
| 5 | DRY | Med | ui/fractal_viewport + ui/thumbnails | numpy RGBA → QImage conversion duplicated | — | `widgets/images.py: rgba_to_qimage` |
| 6 | Architect | Med | fractal/formats/__init__ | imports *private* helpers (`_open`, `_append_text`) from the gradient flame module | expedient | public `flame_spans()` / `append_flame_text()` in `formats/flame.py` |
| 7 | Architect | Med | fractal/formats/chaos_world | `flame_to_ifs` is an 80-line string builder | — | split into `_camera_lines` / `_imaging_lines` / `_iterator_lines` |
| 8 | DRY | Low | tests | `gl_context` fixture + context creation duplicated in two test modules and in gpu_engine | — | conftest fixture using `gpu_engine.create_context()` |
| 9 | Defensive | **Critical** | library/controller + ui/*file_actions | a file-watcher event during our own save re-read a half-written file and raised a *modal* warning box from a background path (intermittent suite hang; in the app, a surprise dialog) | failures from unrequested reloads used the same modal reporting as user actions | `_opened_unreadable` keeps the section + status text; `open_path(quiet=True)` for watcher-triggered reloads in both windows; test `test_opened_file_refresh_never_raises_a_dialog` |
| 10 | Defensive | Med | ui/view_geometry | fit zoom exceeded the 300 % cap for images smaller than the widget | cap applied to explicit zoom only | `fit_zoom()` capped at MAX_ZOOM; `min_zoom` removed (identical); geometry tests |

Cycle 1 result: 303 passed (was 300; +3 tests), pyflakes clean. Regression check vs baseline: **improved**
(all prior tests still pass; behaviour unchanged except #9/#10 fixes). main_window.py 304 → 262 lines,
fractal_viewport.py 378 → 300 lines (+ view_geometry.py 130, library_host.py 75).
Score after cycle 1: Architecture 33/40 · DRY 26/30 · Docs 16/20 · Tests 8/10 → **83** (gates: arch, docs, tests not yet met).

## Cycle 2 — findings (Architect / Comments, on the cycle-1 code)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 11 | Comments | Med | all new modules | 50 public methods/properties without docstrings (IDE help blank) | one-liners skipped | docstrings added (AST sweep now reports only nested closures) |
| 12 | Architect | Med | ui/main_window | `_connect_actions` 45 lines mixing icons, file, edit, view wiring and a toolbar hack | accretion | `_connect_file_actions` / `_place_save_as_on_toolbar` / `_connect_edit_actions` / `_connect_view_actions` |
| 13 | Architect | Med | ui/viewer_bar | `_build` 45 lines | — | `_build_zoom_controls` / `_build_resolution_controls` |
| 14 | Architect | Med | ui/fractal_file_actions | `_saved` used a `renamed` flag with an inline dict comparison expression | two flows squeezed into one | `_is_still(snapshot, ignore_name)` extracted, docstring explains the re-pointing rule |
| 15 | Architect | Med | render/service | `_render` 30 lines: setup, loop, requeue, error paths interleaved | — | `_run_passes` + `_requeue` extracted; single `finally` closes the job |
| 16 | Architect | Med | fractal/formats/__init__ | package `__init__` held all format classes (217 lines) | grew from a registry stub | classes + functions in `registry.py`; `__init__` is a façade with `__all__` |
Cycle 2 result: 303 passed, pyflakes clean. Regression vs cycle 1: **improved** (pure refactors + docstrings; no behaviour change).
Score after cycle 2: Architecture 35/40 · DRY 26.5/30 · Docs 18/20 · Tests 8/10 → **87.5** (tests gate 8.5 not met).

## Cycle 3 — findings (Defensive Tester, on the cycle-2 code)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 17 | Defensive | High | fractal/scene | `Camera.unproject` divides by zero for `scale=0` (malformed file → viewport crash on first mouse move) | no floor on pixels-per-unit | `MIN_PIXELS_PER_UNIT` floor in `pixels_per_unit` / `at_size`; test |
| 18 | Defensive | High | fractal/scene | `Flame.from_dict` accepted garbage (`"coefs": "abc"`, chaos strings) and deferred the crash to the render engine | no validation | `_number` / `_affine` validators with clear `ValueError`s; test |
| 19 | Defensive | High | fractal/formats/clipboard + flame_xml | Paste of malformed `<flame>` XML raised `ET.ParseError` (not a ValueError) and `.fa` text with non-dict flames raised `AttributeError` — both escaped to the user as tracebacks | exception families not covered | `parse_text` wraps in `FlameParseError`; clipboard validates the envelope with `is_document` and catches `AttributeError`; test covers 6 bad inputs |
| 20 | Defensive | Med | ui/viewer_bar | garbage typed in the zoom box re-parsed its own text and fell back to *fit* instead of keeping the current zoom | `_current_zoom()` derived from the text being edited | bar remembers the last shown zoom; `_current_zoom` removed; test |
| 21 | Defensive | Low | tests | untested: thumbnail load failure, watcher extra file, `.fa` envelope validation | — | tests added (deterministic: load failure injected) |
Cycle 3 result: 311 passed ×2 (+8 tests), pyflakes clean. Regression vs cycle 2: **improved** (fixes only tighten failure behaviour).
Score after cycle 3: Architecture 35/40 · DRY 26.5/30 · Docs 18/20 · Tests 9/10 → **88.5** (total gate not yet met).

## Cycle 4 — findings (final Architect / DRY sweep, on the cycle-3 code)
| # | Critic | Severity | Subsystem | Criticism | Root cause | Correction |
|---|---|---|---|---|---|---|
| 22 | DRY | High | ui/file_actions + ui/fractal_file_actions | ~70 identical lines: background write bookkeeping, "wrote recently", failure box, unsaved-changes prompt, name prompt, load tickets | second class copied from the first | `ui/file_actions_base.py: FileActionsBase` (template-method contract `save` / `_document_name` / `_document_modified`); both subclasses shrink (237→192, 307→287) |
| 23 | Architect | Med | fractal/formats/chaos_world | reader and writer (330 lines) in one module | writer appended later | `chaos_writer.py` split out; registry/clipboard import it |
| 24 | DRY | Low | render/service | `_snapshot` re-listed every RenderStats field | — | `dataclasses.replace` |
| 25 | DRY | Low | tests | three UI modules built MainWindows and open/wait helpers the same way | — | conftest `main_window_factory`, `open_flame_and_wait`, `wait_for_render` |
Cycle 4 result: 311 passed ×2 (76 s), pyflakes clean, compileall ok. Regression vs cycle 3: **improved** (pure refactors; tests unchanged in intent).

## Final score & evidence
| Dimension | Points | Gate | Score | Evidence |
|---|---|---|---|---|
| Clean architecture | 40 | 34 | 36 | ViewGeometry / LibraryHost / FileActionsBase / chaos_writer / registry extractions; no module > 330 lines except the variation catalogue; wiring methods ≤ 20 lines |
| DRY | 30 | 25.5 | 27 | #2, #3, #4, #5, #8, #22–#25 removed every duplicate found; remaining: thin viewport façade over ViewGeometry (deliberate API) |
| Comments & docs | 20 | 17 | 18 | module docstrings explain *why*; public API docstrings complete (AST sweep: only closures left); no obvious-statement comments |
| Defensive testing | 10 | 8.5 | 9 | 311 tests; failure paths for clipboard, envelope, XML, camera, zoom box, thumbnails, watcher, mid-write refresh; 2 critical dialog-from-background defects found and fixed |
| **Total** | 100 | ≥ 90 | **90** | all gates met; zero critical failures open |

Commands: `python -m pytest -q -p no:cacheprovider` (≈ 80 s; GL tests use Mesa/llvmpipe here and skip without OpenGL);
`python -m pyflakes fractalchemy tests main.py`; `python -m compileall -q fractalchemy main.py tests`. Nothing committed.

## Fix: "Signal source has been deleted" at shutdown
- `FractalDocument` connected a lambda to `QUndoStack.cleanChanged`; the stack emits it while being destroyed, after the
  document's C++ object is gone. Replaced by the bound method `_on_clean_changed` (auto-disconnected on destruction).
  Regression test `test_destroying_an_edited_document_is_silent` (captures stderr; verified to fail against the lambda).
- Rule of thumb recorded for the codebase: never connect a lambda to a signal that can fire during teardown
  (QUndoStack, QAction text/enabled signals); use bound methods. Suite: 312 passed.

# Final rendering engine + Render Image window (this session)
Scope: the full-fledged final renderer and its window, opened from *Windows ▸ Render Image…* (`Ctrl+R`) or the
toolbar button (`render_icon()`: framed picture with a green go-badge; `link_icon()` for the aspect lock).

## What was built
- `render/final_settings.py` — `FinalRenderSettings` (size, density, oversample, filter + radius, denoiser + strength,
  flam3 DE params, engine, workers, memory limit, transparency, depth, output path/format, lossy quality, lossless,
  save/embed parameters, save incomplete), `to_dict`/`from_dict` (persisted as JSON in QSettings), `problems()`,
  `plan_tiles()` (fewest tiles within the memory budget / GPU texture limit, interior edges on pixel boundaries,
  gutter = max filter reach), `describe_plan()`, `physical_memory_bytes()` (sysconf / GlobalMemoryStatusEx).
- `render/filters.py` — 9 reconstruction filters as 1-D profiles (`make_taps` → strided separable `downsample`);
  `DensityEstimation` + `density_estimate` (flam3 scatter semantics via a geometric ladder of kernel levels;
  scipy Gaussian when present, Kutskir box³ fallback); `box_blur` via cumulative sums (edge-clipped windows).
- `render/denoise.py` — registry with availability: none, density (handled by the engine), guided filter (numpy),
  bilateral (numpy), non-local means (cv2, optional), Intel OIDN (optional `oidn` package). Strength 0..100.
- `render/tonemap.py` — split into `log_scale` (per-bucket L and L·mean colour, what flam3 filters) and `finish`
  (gamma / vibrancy / background, or straight-alpha transparent); `tonemap()` unchanged = finish(log_scale()).
- `render/cpu_workers.py` + `render/samplers.py` — `CpuSampler`: one **spawned process per core** writing into a
  shared-memory `(4, rows, cols)` float64 histogram; hits partitioned by row band (radix argsort on uint16 key)
  and added under 64 band locks (plain adds under one lock for histograms ≤ 2 M buckets); cancel/pause flags in a
  `mp.Array`. `GpuSampler`: `GpuPopulation` (extracted from `GpuRenderJob` in `gpu_engine.py`) → RGBA32F texture,
  read back into the float64 master every 3 s / 2^28 samples. `RenderControl` (cancel / pause, paused seconds).
  `create_sampler()` falls back to the CPU with a note when GL fails.
- `render/cpu_engine.py` — `_Worker._select`: xform selection via a 1024-bin lookup table + exact fix-up
  (was O(n·xforms) with an (n, k) temporary); shared by the preview CPU engine and the final workers.
- `render/final_engine.py` — `FinalRenderer.run(progress)`: tiles → batches sized to ~1.5 s → previews (block means
  of the histogram, adaptive interval) → log-scale (row-chunked) → DE → downsample → finish → uint16 image;
  image-space denoise at the end; `FinalProgress` (phase, fraction, elapsed, remaining from measured rate + timed
  filter phases, preview canvas) and `FinalResult`. Cancel with `save_incomplete` finishes the current tile.
- `render/output.py` — `FORMATS` (png, jpeg, tiff, webp, bmp, avif, heif, jxl, svg) with alpha / 16-bit / lossy /
  max side / availability; own 16-bit PNG and deflate TIFF writers (verified bit-exact with OpenCV); SVG with
  embedded PNG; parameters as PNG tEXt / JPEG comment / TIFF description / EXIF user comment; `.flame` sidecar.
- `render/final_service.py` — `FinalRenderJob(QThread)`: progressed (throttled to 4/s, previews always),
  succeeded(FinalOutcome), failed(str); pause / resume / cancel.
- UI: `ui/render_size_panel.py` (presets with "Preview size — W × H" first, link, swap, aspect line),
  `ui/render_quality_panel.py`, `ui/render_output_panel.py` (format ⇄ suffix sync, greyed-out options, Browse),
  `ui/render_progress.py` (scaled preview, bar, elapsed / remaining / speed / tile, result links),
  `ui/render_window.py` (`RenderWindow`: plan + time estimate lines, Start / Pause / Stop / Close, overwrite prompt,
  1 s clock, settings persistence, `confirm_quit`, close = hide). `MainWindow.render_window`, `actionRenderImage`
  in `ui/main_window.ui` (Windows menu + toolbar), `_preview_rate()` feeds the estimate.
- `main.py`: `multiprocessing.freeze_support()`, lazy MainWindow import (spawned workers re-import `__main__`).
- `requirements.txt`: scipy (optional, fallback built in); opencv / oidn noted as optional extras.

## Measurements (4-vCPU sandbox, noisy)
- Preview CPU engine: 0.4–1 M samples/s and *no* thread scaling (tiny per-thread batches). Final CPU sampler:
  ~2.2 M/s per process, 4.4 M/s with 4 processes. Histogram adds: band-partitioned `np.add.at` ≈ 47 ns/sample vs
  400–800 ns unpartitioned on 8 M-bucket buffers (memory-latency bound).
- Final render exposure equals the preview engine's (mean 21.42 vs 21.42 on candy.flame at 640×480, 2 tiles, DE).

## Tests
- `tests/test_final_render.py` (43): filters (normalisation, symmetry, box = block mean, gutter check), DE (energy,
  sparse vs dense), blur fallback, tone-map halves + transparency, denoisers, settings round-trip / validation,
  tile coverage / budgets / GPU limits, every format writes + PNG16 bit-exact + embedded params + size limits,
  engine vs preview exposure + seamless tiles, cancel (keep / discard), RenderControl pauses, GPU ≈ CPU (skips
  without GL), GPU→CPU fallback note, FinalRenderJob success + setup failure.
- `tests/test_render_window.py` (8): size link / swap / presets / preview-size following, output format ⇄ suffix,
  time formatting, Start gating, background render keeps its snapshot while the document changes, pause / stop
  keeps a partial file, persistence, main-window action / toolbar / hide-on-close.
- Fixed stale expectation in `test_fractal_catalog_scans_only_fractal_files` (two `.fa` samples had been added);
  `test_menu_bar_has_windows_and_help_menus` now expects "Render Image…".
- Suite: `python -m pytest -q -p no:cacheprovider` → 363 passed; pyflakes clean.
- Gotcha recorded: `spin()` needs a QApplication (use `time.sleep` in Qt-free tests); `QMessageBox.question`
  in `RenderWindow.start()` blocks offscreen tests → pass `ask_overwrite=False`.

## Known limits / ideas
- GPU is float32 (documented in the engine combo); fp64 GPU not planned. Chaotica's exact AA filter names are
  approximated by the standard kernels. OIDN untested here (no package); wrapped defensively.
- Image memory is `8 B × pixels` (uint16 RGBA) on top of the tile budget; gigapixel renders need the disk.
- Possible next steps: render queue (several jobs), post-process window (re-tone-map a kept histogram),
  EXR / float output, reading `quality` / `oversample` / `filter` attributes from `.flame` files as defaults.

## Follow-ups (same session)
- Link button: bold blue joined chain when linked, faint grey broken chain with a red cut when free; no auto-raise;
  state-describing tooltips. Filter dropdown entries no longer name other programs ("Gaussian", "Mitchell-Netravali").
- **Fractal and Render Details** report: `render/report.py` builds a `Report` (sections of `Item`s with machine value +
  human display, and `Table`s) from flame + settings + `FinalResult`, rendered as Markdown, HTML (standalone, styled)
  or text (`key<TAB>value` per line, dotted lower-case keys, `#` comments; tables as `section.rowid.column`).
  Sections: output, render settings (filter taps / reach, tiles, budget…), timing & statistics (phases, per-tile
  table with hits / hit ratio / lit buckets / densest bucket), system, fractal summary, camera (extent in units),
  colouring, palette stats (dominant hues, luminance, smoothness), transforms table (probability, affines,
  determinant, variations, params, xaos), variations usage table, xaos matrix, notes.
  `FinalResult` gained `tiles: list[TileStats]`, `plan`, `started_at` / `finished_at`, `paused_seconds`,
  `denoise_seconds`. Settings: `save_details` (default off) + `details_format` ("md" / "txt" / "html");
  `FinalRenderJob(..., source=)` writes `<image>.<ext>` after the image and sidecar; `FinalOutcome.report`;
  the result line links to it. OutputPanel: checkbox + format combo (combo enabled only when checked).
- Tests: `test_report_is_complete_in_all_three_formats` (+ job / window coverage); suite 365 passed, pyflakes clean.
