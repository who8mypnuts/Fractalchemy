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
