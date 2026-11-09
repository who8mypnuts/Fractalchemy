# Plan — Mutate & Breed, program-wide themes, readable editors, and gradient-editor QoL

Status: **implemented** (decisions in §2; progress in §12). This document is the working plan: it is refined as questions are
answered and then followed phase by phase, with the checkboxes in §12 ticked as work lands.

Scope, as requested:

1. **Mutate + Breed** for fractals (new).
2. **Program-wide themes**: Nord plus several Nord variations, and about 30 other themes. Mostly dark, with a few light ones.
3. **Readable editor colours** that **follow the theme**.
4. Rename the main window's right-hand panel to **Inspector**, so it no longer clashes with the *Info* tab inside it.
5. **Gradient editor gestures**: double-click to add a node without changing the gradient; Delete / Backspace;
   ← / → nudge (Shift = 10); Enter opens the colour picker; a right-click menu on a node.
6. **Removals**: `pitch_y` (pseudo-3D tilt) and the main viewer's *Detail* (Full / ½ / ¼), wherever they are still
   present in code or docs.
7. **Gradient-editor behaviour for mutations**: the Gradient Library follows the fractal's new gradient, as it does when
   a new fractal is clicked, but **without** prompting to save an unsaved gradient.

---

## 0. How this codebase is built (the rules this plan follows)

These conventions come from README, TASK_STATE (the review cycles), docs/* and the code itself:

* **Layering.** Qt-free cores (`model/`, `fractal/`, `formats/`, `render/`, `scripting/`, `animation/`, `fragments/`
  core) sit under Qt widgets (`widgets/`) and windows (`ui/`). Widgets must not import from `ui/`: review finding A3
  removed exactly that kind of cycle. (The one existing exception is `ui.document.GradientDocument`, which the
  gradient widgets bind to.)
* **Windows coordinate and nothing more.** Panels, operations and actions go in their own modules, e.g.
  `editor_window` + `editor_actions` + `editor_operations` + `editor_panels`. A window module kept to about 500 lines
  or less.
* **One document owns the edits.** `FractalDocument` is the only thing that changes the main flame. Every change is
  undoable and announced by a signal. Nothing is written to disk until *Save*.
* **DRY helpers already exist and are reused:** `widgets/actions.make_action / populate`, `widgets/layouts.row`,
  `widgets/silent.updating / blocked`, `ui/background.run_in_background`, `FileActionsBase`, `JobWindowBase`,
  `TableTab`, and registries instead of if/elif chains (`glyphs.GLYPHS`).
* **Tunables go in `config.py`.** Persistence uses QSettings with namespaced keys (`preview/…`, `random/…`, `editor/…`).
* **Deterministic randomness.** Every random operation takes an injectable `random.Random` (`model/operations.py`,
  `fractal/random_flame.py`), so tests are deterministic.
* **Docstrings on every public name.** A module docstring explains each module's design. README's *Layout* section
  lists every module. TASK_STATE gets a round entry for each piece of work.
* **Tests.** pytest with Qt offscreen, GUI tests on the CPU engine (`prefer_gpu=False`), helpers in `tests/conftest.py`
  (`wait_until`, `spin`, `main_window_factory`, mouse helpers). `pyflakes` must stay clean (the script templates
  under `scripting/builtin_templates/` are expected to report undefined names).
* **Review rubric** from TASK_STATE: architecture 40, DRY 30, comments 20, tests 10. Exit at ≥ 90 with no gate below
  85 %. The final phase runs this review over the changes.

Baseline (this sandbox, before any change): `pyflakes` clean. Full suite without `test_variations`: **586 passed, 1
skipped** (19 min, Qt offscreen, llvmpipe). An earlier run stopped only on `test_image_formats[.heic]` because
`pillow-heif` was missing from the sandbox; with it installed the suite is fully green. Every phase is compared
against this run.

---

## 1. Findings that shape the plan

Each item below was verified by reading the code and, where noted, by running it.

| # | Finding | Evidence | Consequence for the plan |
|---|---|---|---|
| F1 | **The Gradient Library does not follow undo / redo / paste / script results / `replace_flame_parameters`.** `GradientLink` only listens to `flame_replaced`; these all emit `flame_restored`. | Probe script: after `undo()` the flame's palette[0] = (135,43,21) but the editor's stop 0 is still (200,0,0). After `replace_flame_parameters` with an all-green palette the editor is unchanged. | A mutant or child adopted as an undoable edit would leave a **stale gradient** in the editor, and the next gradient tweak would write the old gradient back over the new one. This is the "looks like a bug" case. Fix in Phase 3, before Mutate & Breed. |
| F2 | **Switching fractals *does* prompt today** when the Gradient Library has unsaved edits (`sync_gradient_from_flame → files.confirm_discard()`). The behaviour is documented in README and gradient_link.py, and asserted by `test_switching_fractals_with_unsaved_gradient_edits_asks_first`. | Probe: switching with an edited gradient produced the dialog *"'original' has unsaved changes."* | The brief says the gradient editor "doesn't do this when we switch to a new fractal". The code disagrees. **Open question Q1.** The mutate/breed path is silent either way. |
| F3 | **`pitch_y` is still live.** The 3D Editor's *Camera* tab has a **Tilt** row bound to `pitch_y`. It also survives in the model (`Camera.pitch_y`, camera matrix), `.flame` (`cam_pitch_y`) and `.fa` I/O, the scripting API (`camera.pitch_y`, docs, Flame→Script), animation blending, the Info tab's camera line, `FractalDocument.set_camera_3d / revert_camera_3d`, the Transform Editor's *New flame* reset, the 3D document / viewport, tests, README ("pitch / yaw / tilt") and docs/scripting.md. | grep: 29 lines in 13 source files + 11 test lines. TASK_STATE item 14 removed only the Image-tab row and deliberately kept everything else. | Phase 1 removes it. How far to go is **Q2**. |
| F4 | **Detail (Full / ½ / ¼) is gone from the code.** Two things remain: a stale line in `docs/rendering.md` (line 137: "**Detail** (viewer bar): `FractalViewport.render_scale` …"), and a guard test (`assert not hasattr(bar, "detail_box")`). | grep | Phase 1 deletes the doc line and keeps the guard test. |
| F5 | **The app has no theming at all.** There is no `setPalette` and no app style; every colour is hard-coded: 126 literals in `ui/`, 148 in `widgets/`, 25 `setStyleSheet` calls. The only themes are the Fragments editor's six (`fragments/editor_themes.py`). | grep; screenshots under a dark palette | The theme system must replace literals with theme roles (Phase 5). |
| F6 | **Editor colours that are hard to read** (screenshots taken with a dark palette, the situation any dark desktop already produces): | | Every item gets a named fix in Phase 5. |
| | a. **Transform Editor ▸ Variations / Variables.** Rows are tinted by formula origin (pale blue / amber / green / violet) but only the *name* column gets a dark text colour. The **Weight and Kind columns keep the palette's light text on the pale tint, so they are unreadable.** Root cause: `ValueTable._refresh_row` applies `row.color` to column 0 only. | `dark_editor.png` | |
| | b. Formula Editor list / formula browser: the pale origin tints glare on dark themes. | `dark_formula.png` | |
| | c. Code editors (Script, Formula, Fragments "Default"): fixed light-scheme syntax colours (`#0d47a1`, `#7b2fa0`, `#1565c0`, …) nearly vanish on a dark base. | `dark_formula.png`, `dark_script.png` | |
| | d. Completion popup: the doc pane has a fixed `#fffdf5` background while the text uses the palette's (light) colour. Script drawer HTML: `.sig` / `pre` light backgrounds and `#0d47a1` headings. | code | |
| | e. Painted toolbar glyphs use a fixed ink (`GLYPH_COLOR = #3b3b3b`), so undo/redo, move/rotate/scale and similar icons disappear on dark toolbars. | `dark_editor.png` toolbar | |
| | f. Fragments log: the *info* level is `QColor(90,90,90)`, dim on dark. Diff / diagnostics colours are fixed too. | `dark_fragments.png` | |
| F7 | `align_flames` / `blend_flames` (generic flame blending) live in `animation/interpolate.py`. Mutation (Apophysis-style "drift towards a random flame") and breeding by interpolation need them. | code | Move them to `fractal/blend.py` and re-export from `animation.interpolate`, so the Qt-free `fractal` layer does not import `animation`. |
| F8 | `fractal/random_flame.frame_camera` contains the "blows up / collapses" test that mutants and children also need. | code | Extract `attractor_bounds(flame)` and share it (DRY). |
| F9 | Node operations (add, add random, randomize, delete, pick colour) live inside `NodePanel`. The requested right-click menu and keys need the same operations. | code | Move them into a shared `NodeCommands` object. The panel, menu and keys all use it (DRY). |
| F10 | Housekeeping found on the way, **not requested** (Q6): `ui/editor_preview.py` is dead **and broken** (`ImportError: _fitted`); `render/report.py` (692 lines) is dead, shadowed by the `render/report/` package; `ui/file_actions.py` duplicates `FileActionsBase`; `bring_to_front` is written out 8 times; `ColorPickerDialog._configure_fields` is an unused duplicate. | import checks, grep | Listed in Phase 9 as optional. Nothing is touched without a yes. |

---

## 2. Decisions (answered)

* **Q1: fractal-switch prompt → no prompt.** Switching fractals no longer asks about unsaved gradient edits; the
  Gradient Library simply shows the new fractal's gradient (as it will for mutate / breed / undo / paste).
  `GradientLink.sync_gradient_from_flame` stops calling `confirm_discard`; the test that asserted the prompt is
  inverted; README / gradient_link docstring updated. The prompt stays where the *Gradient Library itself* replaces
  its gradient (its own File ▸ Open, library clicks, the browser strip) and on quit.
* **Q2: `pitch_y` → do not remove yet; report.** Phase 1 only investigates where `pitch_y` can still be seen and
  edited and reports back; no code change.
* **Q3: default theme → "System".**
* **Q4: clicking a mutant / child → one undoable edit keeping the file link**; *Open as new unsaved fractal* in the
  cell's menu.
* **Q5: canvases → always dark**, theme-tinted.
* **Q6: housekeeping → yes**: delete `ui/editor_preview.py` and `render/report.py`; one shared `bring_to_front`
  helper used by every tool window (the 8 copies migrated).

---

## 3. Phase 1 — Removals (Detail), `pitch_y` report, housekeeping

Done first because it is small, isolated, and makes the later camera / scripting work simpler.

**Detail**
* `docs/rendering.md`: delete the `**Detail** (viewer bar)…` bullet.
* Keep `test_viewer_bar_guides…`'s `assert not hasattr(bar, "detail_box")` as the guard.
* Confirm nothing else remains: `render_scale`, `viewer/detail`, `detail_box` (all already 0 hits).

**`pitch_y`**: per Q2, *investigate and report only* (no code change). Findings go to the progress log (§12). The
removal table is kept below for when a decision is made (deferred; not part of this round):

| File | Change (deferred) |
|---|---|
| `fractal/scene.py` | drop `Camera.pitch_y` (field, docstring, `is_3d`, the tilt block in `matrix()`, the positional argument in `at_size`). `to_dict` stops writing it; `from_dict` ignores a legacy `"pitch_y"` key. Review every positional `Camera(...)` call (`at_size`, `from_dict`, readers). |
| `fractal/formats/flame_xml.py` | the reader ignores `cam_pitch_y`; the writer stops emitting it |
| `render/projection.py` | module docstring ("pitch / yaw (/ pitch_y)") |
| `animation/interpolate.py` (→ `fractal/blend.py`, Phase 6) | remove from `_blend_camera`'s field list |
| `ui/fractal_document.py` | `set_camera_3d(…, pitch_y)` parameter and `revert_camera_3d` |
| `ui/editor_operations.py` | *New flame* camera reset |
| `ui/three_d/panels.py` | the **Tilt** row; `CameraPanel` docstring "pitch / yaw / tilt" → "pitch / yaw" |
| `ui/three_d/document.py`, `ui/three_d/viewport.py` | `keep_camera` field list, `set_camera` docstring, `reset_view` |
| `ui/info_panel.py` | the `/ y …°` part of the 3D-camera line |
| `scripting/api.py`, `scripting/docs.py`, `scripting/generate.py` | the `camera.pitch_y` property and reset, the reference entries, the Flame→Script line. Regenerate `docs/scripting.md` with `tools/scripting_reference.py`. |
| tests | `test_render.py` (pitch_y projection tests) → a test that `Camera` has no `pitch_y`. `test_fractal_formats.py` round trip → `cam_pitch_y` is neither written nor fatal on read, and `.fa` with `"pitch_y"` loads. New guards: the 3D Editor `CameraPanel` has no `tilt`; the scripting `camera` has no `pitch_y`. |
| docs | README "pitch / yaw / tilt" → "pitch / yaw"; TASK_STATE item 14 annotated "(fully removed in round N)" |

**Housekeeping (Q6, done in this phase because the new window needs the helper)**
* Delete `ui/editor_preview.py` (dead, fails to import) and `render/report.py` (dead, shadowed by `render/report/`).
* `widgets/windows.py: bring_to_front(window)`; the 8 `bring_to_front` methods delegate to it (keeping their own
  extra steps, e.g. the Animation window's preview refresh).

---

## 4. Phase 2 — "Settings panel" → **Inspector**

A mechanical rename that also fixes the user-facing wording.

* `ui/settings_panel.py` → **`ui/inspector_panel.py`**, `SettingsPanel` → **`InspectorPanel`**. Module docstring: "The
  Inspector: the collapsible panel right of the viewport with the *Info* and *Image* tabs". The inner `InfoPanel` /
  `ImagePanel` keep their names; the outer name no longer collides.
* `ui/main_window.ui`:
  * widget `settingsPanel` → `inspectorPanel`; class and header → `InspectorPanel`.
  * `actionToggleSettings` → `actionToggleInspector`, text **"Show/Hide Inspector"** (Ctrl+Shift+L unchanged).
* `ui/main_window.py`: import, `CUSTOM_WIDGETS`, `SETTINGS_PANE_WIDTH` → `INSPECTOR_PANE_WIDTH`, splitter label
  `"inspector"` (so the divider arrow's tooltip reads *Show / Hide inspector*), and the 13 `self.settingsPanel` uses.
* QSettings: the tab key moves from `panel/tab` to `inspector/tab`. The old key is read once as a fallback so users
  keep their tab. `preview/*` keys are unchanged.
* Docstrings: `info_panel.py`, `image_panel.py` ("tab of the settings panel" → "tab of the Inspector"), `scripting/api.py`.
* Tests: `conftest.py` (`win.settingsPanel.set_values`), `test_viewer_controls.py` (menu texts), `test_image_panel.py`,
  `test_info_panel.py`. Test names change `settings_panel` → `inspector`.
* README lines 25, 72, 129 and the Layout section; TASK_STATE.

Acceptance: there is no `SettingsPanel` / `settingsPanel` / "Settings Panel" left (the unrelated
`AnimationSettingsPanel` stays). View menu and splitter tooltip say *Inspector*. The saved tab survives the upgrade.

---

## 5. Phase 3 — The Gradient Library follows the fractal **silently** (the mutation "bug")

This is the foundation Mutate & Breed needs (F1). It also fixes stale gradients after undo / redo / paste / script runs.

**Behaviour.** Whenever the main fractal's palette changes from *outside* the Gradient Library (undo, redo, paste,
a script's result, the Transform Editor's whole-flame operations, **adopting a mutant or child**), the Gradient Library
shows the new gradient at once, the same way it does when a fractal is clicked, **and never asks about unsaved
gradient edits**. Nothing is lost: every gradient edit made in the library was already applied to the fractal and
sits in the fractal's undo history.

**Design** (`ui/gradient_link.py`, `ui/document.py`):
* `GradientLink` connects `FractalDocument.flame_restored` → `follow_flame()`.
* **Change detection without false positives.** The editor's gradient is a *simplified* version of the 256-entry
  palette, so comparing samples would trigger on every undo. Instead the link remembers `_palette_seen`: the palette
  it last applied (`apply_gradient`) or last showed (`sync_gradient_from_flame`, `follow_flame`). `follow_flame` acts
  only when `flame.palette != _palette_seen`. A camera-only undo therefore leaves the editor, its node selection and
  its pending slider adjustments alone.
* **Which source the followed gradient keeps:**
  * If the editor was showing **the fractal's own entry** (`document.is_showing(fractal.source_path, index)`), keep
    that `(path, index)`. The browser strip still lists the file's gradients, and Save still writes into that flame.
    New `GradientDocument.follow(gradient)`: it replaces the stops and name, keeps the source, clears selection and
    adjustments, sets `modified = False` (the *fractal* carries the `*`), and emits `gradient_replaced`.
  * Otherwise (the editor showed some other file's gradient, or a loose one), show it as a loose copy:
    `files.show_gradient(...)`, the same call the fractal-click path uses for loose flames. This prevents a later
    *Save* from writing the fractal's palette into an unrelated `.ugr`.
* Both paths run under `_syncing`, so `_on_gradient_replaced` does not re-apply the simplified gradient back onto
  the fractal. The module docstring gets a new paragraph: *following vs. switching*.
* `sync_gradient_from_flame` (fractal switching) no longer calls `confirm_discard` (Q1).

**Tests** (`tests/test_gradient_link.py`; each patches `QMessageBox.question` to **fail the test if called**):
* Undo and redo of a gradient edit update the editor. No prompt, even with `document.modified` set before the undo.
* `replace_flame_parameters` with a new palette (the mutation path) updates the editor, keeps `(path, index)` when
  the editor showed the fractal's own entry, and leaves `modified` False.
* Paste Parameters and a script that changes `gradient` update the editor.
* A camera-only undo does **not** touch the editor (selection and adjustments kept).
* After following, a node edit applies on top of the **new** palette, not the stale one (the original bug, end to end).
* The editor showing another file's gradient → the follow becomes loose (`source_path is None`).

---

## 6. Phase 4 — Gradient editor gestures (Gradient Library window)

**Shared operations (DRY, F9).** New `widgets/node_commands.py: NodeCommands(QObject)`. It is bound to the
`GradientDocument` and owns:
* The node operations: `add_after()` (same colour, midway to the next node), `add_random()`, `randomize()`, `delete()`
  (refused below `MIN_NODES` with a status message), `nudge(units)`, `add_at(position)`, and `pick_colour(anchor)`.
* One `QAction` per operation, with its shortcut text and enabled state kept in step with the selection.
* The `ColorPickerDialog`, moved out of `NodePanel`. `NodePanel.picker` / `open_picker()` stay as thin delegates so the
  existing tests and callers keep working.
* A `status(str)` signal that goes to the window's status bar.

`NodePanel`'s buttons, the node bar's keys and both context menus all call `NodeCommands`. Each operation exists
exactly once.

**Model** (`model/node_ops.py`, Qt-free, unit-tested):
* `inserted_at(gradient, position) -> (stops, index)`: a stop at `position` coloured `gradient.color_at(position)`.
  Because the new node lies on the existing colour curve, **the gradient looks identical** (within ±1 per channel
  from 8-bit rounding).
* `nudged_position(position, units) -> float`: moves in Ultra Fractal index units (`round(p·399) + units`, clamped
  0…399, divided by 399). This is the same rounding the Position spin box uses, so the two always agree.

**Gestures**

| Gesture | Where | Behaviour |
|---|---|---|
| Double-click | colour strip, or an empty spot on the node bar | add a node at that position in the colour already there; the new node becomes selected. A double-click within the hit radius of an existing node selects that node instead of stacking a duplicate. |
| **Delete / Backspace** | node bar focused (clicking the strip or the bar gives it focus; the strip's focus proxy is the bar) | delete the selected node; at 2 nodes nothing happens and the status bar explains why |
| **← / →** | same | nudge the selected node by 1 UF unit; **Shift** = 10; the selection follows across neighbours (`move_stop` already returns the new index) |
| **Enter / Return** | same | open the colour picker on the selected node |
| Right-click a node | node bar | selects it, then a menu: *Add node* · *Add random node* · *Randomize node* · — · *Pick colour…* (Enter) · — · *Delete node* (Del; disabled at 2 nodes) |
| Right-click empty space *(small proposed extra; easy to drop)* | node bar / strip | *Add node here* (the double-click action) |

Files: `widgets/node_bar.py` (focus policy, `mouseDoubleClickEvent`, `keyPressEvent`, `contextMenuEvent`),
`widgets/gradient_strip.py` (double-click, focus proxy), `widgets/gradient_editor.py` (`bind(document, commands)`),
`widgets/node_panel.py` (uses commands), `ui/gradient_library_window.py` (creates `NodeCommands`, wires status).
`config.py` gains `NODE_NUDGE_COARSE = 10`. The README *Editor* section gets a gestures list.

**Tests** (`tests/test_node_editor.py`, `tests/test_widgets.py`):
* `inserted_at` leaves `sample(400)` unchanged (±1), both inside a span and in the wrap-around region.
* Double-click via synthetic Qt events on the strip and on empty node-bar space adds a selected node; on a node it
  does not add.
* Delete / Backspace delete, and are refused at 2 nodes.
* ← / → / Shift move 1 / 10 units, clamp at 0 and 399, and follow across a neighbour.
* Enter shows the picker on the right colour.
* The context menu lists the five actions with correct enabled states, and its actions are the same `QAction`
  objects `NodeCommands` owns.
* Every gesture recolours the linked fractal, through the existing `GradientLink`.

---

## 7. Phase 5 — Program-wide themes and readable, theme-following editors

Themes come **before** the Mutate & Breed window so the new UI is built theme-aware rather than retrofitted.

### 7.1 Core model (Qt-free): `fractalchemy/themes/`
* `themes/model.py`: the `Theme` dataclass (hex strings), plus colour maths: `mix`, `lighten`, `darken`,
  `relative_luminance`, `contrast_ratio`, and `ensure_contrast(fg, bg, minimum)`. That last function nudges a colour
  toward the theme's foreground until it meets the minimum ratio, so a published palette stays faithful wherever it
  is already readable, and is corrected wherever it is not.
* **Seed → derived.** A catalogue entry gives about 14 *seed* colours: `bg`, `surface`, `base`, `fg`, `dim`, `accent`,
  `red`, `orange`, `yellow`, `green`, `cyan`, `blue`, `purple`, `comment`. Optional overrides cover a theme's iconic
  mappings (e.g. Monokai's pink keywords, Nord's Frost keywords). `derive(seed) -> Theme` fills in every role. This
  keeps the catalogue compact and DRY, and guarantees that no role is ever missing.
* **Roles:**
  * **UI:** window, window_text, base, alt_base, text, dim_text, button, button_text, border, accent, accent_text, link,
    tooltip, tooltip_text, placeholder, disabled_text.
  * **Status:** error / warning / success / info, plus soft backgrounds for each.
  * **Editor chrome:** editor_bg, editor_fg, gutter, gutter_fg, current_line, selection, selection_fg, error_line,
    match, find_match.
  * **Syntax (the union of today's three highlighters):** keyword, type, function, builtin, string, comment, number,
    preprocessor, annotation, preset, special, api, member, state, constant, decorator, definition, meta.
  * **Formula origins:** (background, text) pairs for built-in / apophysis / jwildfire / user, derived from the theme's
    blue / yellow / green / purple over its base. On dark themes that gives dark tints with light text; on light
    themes, pale tints with dark text.
  * **Canvas (Q5):** canvas_bg, canvas_grid, canvas_axis, canvas_text.
  * **Glyphs:** glyph_ink, glyph_accent.
* `themes/catalog.py` (plus `themes/nord.py` for the family): the `THEMES` registry, `theme(name)` (unknown → default),
  `theme_names()`, `families()`, `DEFAULT_THEME = "System"` (Q3).
* **Readability is enforced by tests, not by eye**, at WCAG AA. For every theme:
  * text / base ≥ 4.5:1, dim text ≥ 4.5:1, placeholder / disabled ≥ 3:1;
  * every syntax colour vs editor_bg ≥ 4.5:1 (comment / preset ≥ 3:1);
  * origin text vs origin background ≥ 4.5:1;
  * accent_text vs accent ≥ 4.5:1;
  * selection_fg vs selection ≥ 4.5:1.

  These thresholds are what make "hard to read" impossible to reintroduce.
* **Calibrated against the real palettes** (measured during planning):
  * Body text passes unmodified everywhere. The lowest is Solarized Light at 5.0:1; One Dark, Palenight, Darcula and
    Rosé Pine Dawn sit at 6–7:1. A 7:1 (AAA) rule would have distorted those themes' identity, so AA is used.
  * Several *published* comment greys fail 3:1 and will be lifted slightly by `ensure_contrast`: Nord 2.4, One Dark
    2.3, Tokyo Night 2.8 / Storm 2.4, Solarized Dark 2.8 / Light 2.5, Ayu Mirage 2.7, Palenight 2.8, Oceanic 3.0,
    One Light 2.5, Catppuccin Latte 2.8, Rosé Pine Dawn 2.7. This is exactly the "comments you can't read" problem
    these themes are known for.

### 7.2 Catalogue: 39 entries (28 dark, 10 light, plus "System")

**Nord family (7).** Uses the canonical Nord palette: nord0 `#2E3440`, nord1 `#3B4252`, nord2 `#434C5E`, nord3
`#4C566A`, nord4 `#D8DEE9`, nord5 `#E5E9F0`, nord6 `#ECEFF4`, Frost nord7–10 `#8FBCBB #88C0D0 #81A1C1 #5E81AC`, Aurora
nord11–15 `#BF616A #D08770 #EBCB8B #A3BE8C #B48EAD`.

| Theme | Kind | Ground / text / accent | Character |
|---|---|---|---|
| **Nord** | dark | nord0 / nord4 / nord8 | the reference: Polar Night panels (nord1), Frost keywords (nord9), strings nord14, numbers nord15, comments `#616E88` (Nord's own readable comment grey) |
| **Nord Deep** | dark | `#242933` (base `#1E222A`) / nord4 / nord8 | darker Polar Night for dim rooms |
| **Nord Frost** | dark | nord0 / nord6 / nord10 | cool: deep-blue accent and selection, Frost-heavy syntax |
| **Nord Aurora** | dark | nord0 / nord4 / nord15 | warm: purple accent, Aurora orange/yellow keywords |
| **Nord High Contrast** | dark | `#1E2128` / nord6 / nord8 | accessibility variant: brighter text and comments (`#8A94A8`) |
| **Nord Snow Storm** | light | nord6 (windows nord5) / nord0 / nord10 | the light Nord; Aurora syntax darkened by `ensure_contrast` |
| **Nord Light Frost** | light | `#F8F9FB` / nord1 / nord9 | brighter light variant with Frost accents |

**Others (31).** Each is built from its published palette (bg / fg / accent shown):

| Dark (23) | bg · fg · accent | Light (8) | bg · fg · accent |
|---|---|---|---|
| Fractalchemy Dark | `#202225 · #E3E5E8 · #1E88E5` | Fractalchemy Light | `#F3F4F6 · #1F2328 · #1E88E5` (today's syntax colours) |
| Dracula | `#282A36 · #F8F8F2 · #BD93F9` | Solarized Light | `#FDF6E3 · #586E75 · #268BD2` |
| Monokai | `#272822 · #F8F8F2 · #66D9EF` | Gruvbox Light | `#FBF1C7 · #3C3836 · #076678` |
| One Dark | `#282C34 · #ABB2BF · #61AFEF` | Catppuccin Latte | `#EFF1F5 · #4C4F69 · #1E66F5` |
| Tokyo Night | `#1A1B26 · #C0CAF5 · #7AA2F7` | One Light | `#FAFAFA · #383A42 · #4078F2` |
| Tokyo Night Storm | `#24283B · #C0CAF5 · #7AA2F7` | Rosé Pine Dawn | `#FAF4ED · #575279 · #907AA9` |
| Catppuccin Mocha | `#1E1E2E · #CDD6F4 · #89B4FA` | GitHub Light | `#FFFFFF · #1F2328 · #0969DA` |
| Catppuccin Macchiato | `#24273A · #CAD3F5 · #8AADF4` | Paper (high contrast) | `#FFFFFF · #000000 · #0044CC` |
| Catppuccin Frappé | `#303446 · #C6D0F5 · #8CAAEE` | | |
| Gruvbox Dark | `#282828 · #EBDBB2 · #83A598` | | |
| Solarized Dark | `#002B36 · #93A1A1 · #268BD2` | | |
| Ayu Mirage | `#1F2430 · #CBCCC6 · #FFCC66` | | |
| Everforest Dark | `#2D353B · #D3C6AA · #A7C080` | | |
| Kanagawa | `#1F1F28 · #DCD7BA · #7E9CD8` | | |
| Rosé Pine | `#191724 · #E0DEF4 · #C4A7E7` | | |
| Material Palenight | `#292D3E · #A6ACCD · #82AAFF` | | |
| Night Owl | `#011627 · #D6DEEB · #82AAFF` | | |
| Oceanic Next | `#1B2B34 · #D8DEE9 · #6699CC` | | |
| Tomorrow Night | `#1D1F21 · #C5C8C6 · #81A2BE` | | |
| GitHub Dark | `#0D1117 · #E6EDF3 · #58A6FF` | | |
| Darcula | `#2B2B2B · #A9B7C6 · #4A88C7` | | |
| Iceberg | `#161821 · #C6C8D1 · #84A0C6` | | |
| High Contrast Dark | `#000000 · #FFFFFF · #1AEBFF` | | |

**Plus "System".** It applies no palette and no style, keeping the platform look as today. Its editor, origin, glyph
and canvas roles are derived from the live palette: light or dark, chosen by the base colour's lightness. Fragments'
old *Dark* / *Solarized* / *Monokai* / *Paper* map onto catalogue entries.

### 7.3 Applying a theme (Qt): `widgets/theming.py`
It lives in `widgets/` so that both widgets and windows can use it without a `widgets → ui` import.

* `ThemeManager(QObject)` singleton (`theme_manager()`):
  * `current() -> Theme`, `apply(name)`, and the signal `theme_changed(Theme)`.
  * `color(role) -> QColor`, `css(role) -> str`.
  * Persistence under QSettings `appearance/theme`.
* **A catalogue theme** sets the **Fusion** style (the only Qt style that honours palettes fully on every platform)
  and an app `QPalette` built from the roles, covering all three colour groups (Active / Inactive / Disabled) and
  `PlaceholderText`, `Link`, `ToolTip*` and `Accent`.
* **System** restores the style name and palette captured at start-up. It also listens to
  `QStyleHints.colorSchemeChanged`, so an OS light/dark switch re-derives the editor colours while the app runs.
* `main.py` applies the saved theme **before** `MainWindow` is built. Tests are unaffected unless they opt in.
* **Live switching.** `app.setPalette` already repaints every palette-driven widget. The widgets that *cache* colours
  subscribe to `theme_changed`, through one helper: `on_theme_changed(widget, callback)`, disconnected when the
  widget is destroyed. That covers:
  * syntax highlighters, which rebuild their formats and rehighlight;
  * `ValueTable` / `TableTab` rows, re-tinted by repopulating;
  * the formula list and the formula browser;
  * stylesheet sites;
  * HTML drawers, which re-render their CSS.
* **Icons follow the theme live.** Painted glyphs become a `QIcon` backed by a small `GlyphIconEngine(QIconEngine)`.
  It paints the registered glyph with the *current* theme ink at the requested size; caches per (size, mode, state,
  theme); and builds the disabled look through the style. A theme change therefore only needs a repaint.
  Fallback, if PySide's `QIconEngine` subclassing misbehaves: a registry that re-sets icons on `theme_changed`.
* **UI.** The main window gets *View ▸ Theme ▸* with **System**, a **Nord ▸** submenu (7), **Dark ▸** and **Light ▸**
  submenus. Each is a checkable `QActionGroup`; switching is live and persisted. Because themes are program-wide, one
  menu in the main window is enough.

### 7.4 Editor colours (the "hard to read" fixes), each tied to a finding in §1

| Finding | Fix |
|---|---|
| F6a Transform Editor value columns | **Root-cause fix:** `ValueTable._refresh_row` applies the row's text colour to **every** column (name, value, info). The origin colours come from the theme (`formula_origins.ORIGINS` become theme-derived `origin_colors(theme)`); `MISSING_COLOR` / `UNDECLARED_COLOR` become `theme.error` / `theme.dim_text`. The tabs repopulate on `theme_changed`. |
| F6b origin tints glare | Same theme-derived origin pairs in `formula_list_panel.py`, `formula_browser.py` and the Variations tab (one source) |
| F6c syntax colours | `BaseCodeEditor.apply_theme(theme)` replaces `GlslCodeEditor.set_theme` for **all three** editors (DRY): Base / Text / Highlight palette, gutter, current line, error line, popup. `PythonHighlighter`, `CHighlighter` and `GlslHighlighter` share one `set_colors(theme)` path (a small `ThemedHighlighter` base), and their module-level `COLORS` dicts are removed. `ERROR_LINE_COLOR` / `NUMBER_COLOR` become theme roles. |
| F6d popup / drawer HTML | `completion_popup`: the doc pane uses `palette(tool-tip-base)` / `palette(tool-tip-text)`, the signature colour is `theme.type`, and the badge colours come from syntax roles. `script_drawer.STYLE` becomes `drawer_css(theme)`, re-rendered on theme change. Formula drawer likewise. |
| F6e glyph ink | `icons.GLYPH_COLOR` / `GLYPH_ACCENT` → `theme.glyph_ink` / `theme.accent`, via the icon engine. Glyph *identity* colours (green "run", red "stop", the gradient swatch) stay fixed because they read on both light and dark. |
| F6f Fragments | `fragments/editor_themes.py` becomes a thin adapter over the catalogue. The preference `editor_theme` gains **"Follow application theme"**, which becomes the new default; old values map (Default → Follow; Dark → Fractalchemy Dark; Solarized light/dark → Solarized Light/Dark; Monokai; Paper). *Edit ▸ Editor theme* lists Follow plus every catalogue theme. `LEVEL_COLORS` (log), `editor_tools` error/warning/multi colours and the `diff_dialog` colours become theme roles. |
| Transform Editor chrome | mode buttons: `config.HIGHLIGHT_COLOR` → `theme.accent` / `accent_text`. The canvas constants in `triangle_view.py` (`BACKGROUND`, `GRID_*`, `TEXT_COLOR`, …) read canvas roles at paint time. The transform colours themselves stay (they identify transforms). |
| Literal stylesheets (25 sites) | hints `color: #808080` → `palette(placeholder-text)`. `render_progress` / `three_d` thumbnail `#181818` → canvas role. `ProblemBanner` → warning role pair. The missing-file combo `#ffb3b3` → error-soft role. The build label, `OK_STYLE` / `ERROR_STYLE` → success / error roles. `library/dialog` ✕ → error role. `node_panel` swatch border → border role. `mesh_export_dialog` preview → canvas role. |
| Other painted widgets | `gradient_strip` (border, empty state), `live_preview` / `fractal_preview` letterbox, `thumbnails` placeholder, `fractal_viewport` surround, `timeline`, `curve_editor`, `palette_slider`, `hue_wheel` frame, `info_panel` "missing" red, `three_d/viewport` background: canvas / UI roles read at paint time. **Rendered fractal images, gradients, palette swatches and the logo are never themed.** |

### 7.5 Tests
* `tests/test_themes.py` (Qt-free):
  * ≥ 38 themes; the Nord family has ≥ 6 variations, with exact Nord anchors (nord0 and nord8 present); dark > light;
    names unique; unknown name → default.
  * Every role is present after `derive`, and every contrast rule in §7.1 holds **for every theme**.
* `tests/test_theming.py` (Qt):
  * `apply` sets the app palette (Base / Text / Highlight = roles) and emits `theme_changed`; System restores the
    captured palette; the choice persists.
  * The Script / Formula / GLSL highlighters' keyword format colour changes with the theme.
  * **A `ValueTable` origin row's value and info cells use the row's text colour** (the F6a regression test).
  * A glyph icon's pixmap ink differs between Nord and Nord Snow Storm.
  * The Fragments editor follows the app theme when its preference is Follow, and keeps its own when a theme is
    pinned.
  * The theme menu has every catalogue entry, with the current one checked.
* Existing Fragments theme tests are updated to the adapter (names kept: "Monokai" still works).
* A screenshot smoke script (`tools/theme_snapshots.py`, dev only) renders the main window, Transform Editor, Formula
  Editor, Script Editor, Gradient Library, Fragments and Mutate & Breed in a few themes, for the review in Phase 8.

---

## 8. Phase 6 — Mutate & Breed: the Qt-free core

### 8.1 Shared building blocks
* **`fractal/blend.py`**: `align_flames`, `blend_flames` and their helpers, moved out of `animation/interpolate.py`
  (which re-exports them, so every existing import and animation test keeps working).
* **`random_flame.attractor_bounds(flame, points, steps) -> (x0, x1, y0, y1) | None`**, extracted from
  `frame_camera`, which now uses it. `None` means the system blows up or collapses. Mutants and children use it as
  their sanity check with a **small** sample (`config.MUTATION_CHECK_POINTS/STEPS`), because some compiled formulas
  are slow on the CPU (crackle ≈ 20 µs/point).

### 8.2 `fractal/mutation.py`
* `MutationOptions`:
  * `strength` 0..1;
  * `kinds`: a set of operator keys;
  * `trend`: a variation name or None, Apophysis's "Trend";
  * `pool`: the variation names to draw from (default: every catalogued formula);
  * `keep_count`: Apophysis's "Same # of transforms";
  * `keep_symmetry`: leave symmetry transforms alone, i.e. `color_speed == 0`, Apophysis's `symmetry = 1`.
* **Operators**: a registry `OPERATORS: dict[str, Operator]` (the `GLYPHS` pattern). Each is a small function
  `(flame, rng, strength, options) -> note | None`:

| Key | What it does (scaled by strength) |
|---|---|
| `affine` | rotate / scale (log-normal) / translate / slight shear one or more triangles; sometimes the post affine |
| `variations` | swap one variation for one from the pool (or the trend), keeping its weight; sometimes add or drop one |
| `variation_weights` | jitter variation weights, keeping signs |
| `parameters` | jitter variation parameters, honouring `ParamInfo` (min / max, int, cyclic, nonzero) |
| `weights` | redistribute transform weights (always positive, normalised) |
| `colors` | transform colour / colour speed |
| `gradient` | hue rotate, rotate the palette, recolour from a harmony (`model.operations` / `model.adjust`, reused). **This is the mutation that changes the gradient.** |
| `xaos` | jitter existing xaos rows (rows kept consistent via `xform_ops`) |
| `structure` | add a random transform (reusing `random_flame`'s recipes) or remove one (min 2); off under `keep_count` |
| `final` | perturb the final transform if present (rarely add one) |
| `drift` | Apophysis's classic mutation: blend the parent toward a freshly generated random flame by `strength` (`random_flame` + `blend`) |

* `mutate(parent, rng, options) -> Offspring(flame, notes)`: picks 1–3 operators from the enabled set. **The
  parent's camera is kept**, so mutants are comparable with the parent and with each other. The name is
  `"<parent> · m<n>"`.
* `mutants(parent, count, seed, options) -> list[Offspring]`: each mutant is rolled again (up to
  `config.MUTATION_ATTEMPTS`) until `attractor_bounds` accepts it. If no roll is accepted, the slot gets a lighter
  mutation and a note saying so.

### 8.3 `fractal/breeding.py`
* `BreedOptions`:
  * `mode`:
    * **Alternate**: each transform slot taken from A or B at random (flam3's `cross alternate`);
    * **Interpolate**: aligned blend at `t ∈ [0.25, 0.75]` (`blend.py`);
    * **Union**: every transform of both, weights halved;
    * **Mixed**: a random mode per child.
  * `palette`: from A / from B / blend / either parent at random;
  * `camera`: from A (default) / from B / re-framed (`frame_camera`).
* `breed(a, b, rng, options) -> Offspring` and `children(a, b, count, seed, options)`. Both keep xaos rows
  consistent, drop zero-weight padding, cap at `xform_ops.MAX_XFORMS`, and apply the same sanity check and rerolls as
  mutants. The name is `"<A> × <B> · c<n>"`.

### 8.4 Tests (`tests/test_mutation.py`, Qt-free, seeded)
* **Determinism:** the same seed gives identical `to_dict()`; different seeds differ.
* Strength 0 → identical to the parent.
* **Each operator changes only what it owns:**
  * `gradient` changes the palette only;
  * `affine` touches coefs / post only;
  * `keep_count` keeps the count;
  * `keep_symmetry` never touches `color_speed == 0` transforms.
* Parameters stay within `ParamInfo` bounds and integer parameters stay integers; weights stay > 0; colours stay in
  0..1; xaos row lengths equal the transform count.
* A trend variation appears in a seeded batch.
* Every mutant and child passes `attractor_bounds`.
* **Breeding modes:**
  * alternate: every child transform equals a transform of A or of B;
  * interpolate: the coefficients lie between the parents';
  * union: the count is |A| + |B|, capped;
  * the palette / camera options are honoured.
* The animation tests still pass against the moved `blend.py`.

---

## 9. Phase 7 — Mutate & Breed: the window

*Windows ▸ Mutate & Breed…* (**Ctrl+M**, a new toolbar glyph after Random Batch). It is a tool window like the
others: closing hides it, and its layout and options persist.

### 9.1 Layout and modules
* `ui/mutation_window.py`: `MutationWindow(QMainWindow)`. Coordination only: tabs, the grid, wiring to the main
  document, regeneration, adoption.
* `ui/mutation_panels.py`:
  * `MutatePanel`: strength slider, a checkbox per operator, Trend combo (*Random* + the catalogue), *Same number of
    transforms*, *Keep symmetry*, **Regenerate** (Space).
  * `BreedPanel`: a **Parent B** slot (thumbnail and name; *Use current fractal*; *Open…*; accepts drops of
    Fractal Library rows through the library's existing mime payload), then mode, palette and camera, and
    **Regenerate**.
* `widgets/flame_grid.py`: `FlameGrid`, a reusable 3 × 3 grid of preview cells (image, caption, hover highlight, a
  busy state). It emits `chosen(int)` and `menu_requested(int, QPoint)`, and keys **1–9** choose a cell. Theme-aware
  from the start.
* `ui/grid_renderer.py`: `GridRenderer`. It renders a list of in-memory flames into the grid's cells through the
  shared `RenderService`, at `PRIORITY_THUMBNAIL`, so it yields to the viewport. Keys are
  `("grid", id(window), generation, slot)`, so a regeneration cancels every stale render. Small settings come from
  `config.MUTATION_CELL_SIZE / QUALITY / PASSES`.
* **Mutate tab:** the **centre** cell is the current fractal (the parent) and the **8** around it are mutants
  (Apophysis's layout). **Breed tab:** Parent A (the current fractal) and Parent B at the top, and **8** children in
  the grid.
* **Generation** runs on the thread pool (`run_in_background`), because the sanity checks iterate on the CPU. A
  *generation* counter discards results that arrive late.

### 9.2 Behaviour
* **Choose a cell (click / 1–9)** → `document.replace_flame_parameters(child, "mutate" | "breed")`: **one undo
  step, file link kept** (Q4). The window then regenerates around the new parent, as Apophysis does.
  **The Gradient Library updates to the child's gradient silently** (Phase 3), even if it had unsaved edits, because
  the prompt path is never involved.
* **Cell menu:**
  * *Adopt* (1–9);
  * *Open as new unsaved fractal* (`MainWindow.show_flame`, i.e. the same flow as clicking a new fractal);
  * *Use as Parent B*;
  * *Copy parameters*.
* **Undo / Redo** buttons and Ctrl+Z / Ctrl+Shift+Z act on the main document, exactly as the Transform Editor's do.
* **Following the main window.** A new fractal (`flame_replaced`) regenerates at once if the window is visible;
  otherwise the grid is marked stale and regenerates on show. Other edits regenerate after `EDIT_RENDER_DELAY_MS`
  once they pause. Adoption does not count as an outside edit (a guard flag).
* With no fractal loaded, the grid shows *"Open a fractal to mutate it"*. Breed without a Parent B shows *"Choose a
  second parent"*.
* **Persistence:** QSettings `mutate/*` (tab, strength, kinds, trend, keep flags, breed mode / palette / camera,
  geometry).
* **Main window:** `actionMutate` in `main_window.ui` (Windows menu + toolbar), a lazy `mutation_window` property (the
  `formula_editor` pattern), hide and `save_state` in `closeEvent`. **Optional:** a Fractal Library context-menu
  entry *Breed with current fractal*, which sets Parent B.
* `widgets/glyphs.py`: a `"mutate"` glyph (a flask with branching sparks) registered in `GLYPHS`. It is theme-ink
  aware by construction (Phase 5).

### 9.3 Tests (`tests/test_mutation_window.py`, CPU engine, `main_window_factory`)
* Ctrl+M opens the window. For a loaded fractal, 8 mutant cells plus the parent are produced and rendered.
* Choosing a cell makes the main flame equal to that mutant, in one undo step. Undo restores the parent. The window
  regenerates around the new parent.
* **The user's requirement, as a test:** the gradient editor holds unsaved edits, and `QMessageBox.question` is
  patched to fail if called. Adopting a mutant whose palette differs updates the Gradient Library's stops to the
  mutant's gradient, with **no prompt** and `(path, index)` kept.
* Breed: *Use current fractal* for B, switch the main fractal, regenerate, adopt a child; a library-row drop sets B.
* Options persist across window instances. A new fractal in the main window regenerates the grid.
* The grid's stale renders are cancelled when regenerating, so no late image lands in a new cell.

---

## 10. Phase 8 — Documentation, review and verification

* **README:**
  * *Main window* menus and toolbar: View ▸ Theme, Windows ▸ Mutate & Breed (Ctrl+M);
  * **Inspector** wording;
  * a new **Themes** section;
  * a new **Mutate & Breed window** section;
  * Gradient Library *Editor* gestures;
  * the behaviour "the Gradient Library follows undo / paste / mutations without asking";
  * 3D Editor camera without tilt;
  * the *Layout* section for every new or moved module (`themes/`, `widgets/theming.py`, `widgets/node_commands.py`,
    `widgets/flame_grid.py`, `fractal/blend.py`, `fractal/mutation.py`, `fractal/breeding.py`,
    `ui/inspector_panel.py`, `ui/mutation_window.py`, `ui/mutation_panels.py`, `ui/grid_renderer.py`).
* `docs/rendering.md`: the Detail line is gone and the projection wording updated. `docs/scripting.md` is
  regenerated. `docs/fragments.md`: editor themes follow the application theme ("six colour themes" → the catalogue).
* **TASK_STATE:** a new round entry (what, where, tests, decisions Q1–Q6), and item 14 annotated.
* **Review cycle** against the rubric (architecture / DRY / comments / tests), written into TASK_STATE like cycles 1–4.
* **Verification:**
  * `pyflakes` clean;
  * the full suite without `test_variations`, compared test-for-test with the §12 baseline;
  * `test_variations` (projection changed, Q2);
  * theme screenshots reviewed for readability in Nord, Nord Snow Storm, Dracula, Solarized Light, High Contrast Dark
    and System (light and dark palettes).

## 11. Phase 9 — Housekeeping (approved; done in Phase 1)
* Delete `ui/editor_preview.py` (dead and failing to import) and `render/report.py` (dead, shadowed by `render/report/`).
* `widgets/windows.py: bring_to_front(window)`, used by the new window; migrating the 8 existing copies is optional.
* `ui/file_actions.FileActions` subclasses `FileActionsBase` (it duplicates `confirm_discard` / `_run_write` /
  `wrote_recently`).
* Remove `ColorPickerDialog._configure_fields` (unused duplicate).

---

## 12. Order, rationale, progress

| Phase | Content | Why in this order | Status |
|---|---|---|---|
| 0 | baseline: tests, pyflakes, screenshots | a reference to compare against | ✓ 586 passed / 1 skipped; pyflakes clean; dark + light screenshots taken |
| 1 | Detail docs, `pitch_y` report, housekeeping | small and isolated | ✓ `8d65728` |
| 2 | Inspector rename | mechanical; touches main window files early, before the theme menu lands there | ✓ `fb5aa49` |
| 3 | Gradient Library follows silently (+ no prompt on switching, Q1) | prerequisite for adopting mutants; fixes F1 | ✓ `cc6d103` |
| 4 | gradient editor gestures | same subsystem as Phase 3; independent of themes | ✓ `843fd35` |
| 5 | themes + readable editors | before the new window, so it is built theme-aware | ✓ `f9eae2a` |
| 6 | mutation / breeding core | Qt-free, fully testable before any UI | ✓ `f9eae2a` |
| 7 | Mutate & Breed window | needs Phases 3, 5 and 6 | ✓ `f9eae2a` |
| 8 | docs, review, verification | | ✓ (see the log) |
| 9 | housekeeping | approved (Q6); done in Phase 1 | ✓ |

Each phase ends green (its tests, plus the suites it touches, plus pyflakes) before the next begins. Phases 5–7 were
developed together (the window is built on both) and landed as one commit.

**Risks and how they were handled**
* *Fusion plus palettes change widget metrics slightly.* Themes are applied only in `main.py` / the menu, so tests run
  unthemed unless they opt in; the screenshots (`tools/theme_snapshots.py`) were reviewed.
* *`QIconEngine` subclassing in PySide6.* Verified in a spike and now in use (`icons.PaintedIconEngine`); the engine
  generates the Disabled look itself. The fallback registry was not needed.
* *GPU shader compiles for structurally new mutants.* Grid renders run at thumbnail priority, so the viewport never
  waits.
* *CPU cost of the sanity checks.* A small iteration (`mutation.CHECK_POINTS / CHECK_STEPS`) on the thread pool, with a
  generation guard; eight mutants take about 3 s.
* *Following a palette re-simplifies it into nodes* (≤ `IMPORT_SIMPLIFY_TOLERANCE`), as loading a fractal always did.
* *Hidden windows recolouring on every theme change* (found in review, R1): `on_theme_changed` is lazy for hidden owners.

**Progress log** (oldest first)
* (planning) Code and docs reviewed. Findings F1–F10 verified (probe script + dark-palette screenshots). Plan written.
* **Phase 1 done.** The Detail line is gone from `docs/rendering.md` (no code remained). `ui/editor_preview.py` and
  `render/report.py` are deleted. `widgets/windows.bring_to_front` is used by the 8 tool windows and by the main
  window's formula browser / Random Batch (+ test).
* **`pitch_y` report (Q2).** The feature is **still fully in the program**. The Image tab row was its only control *in
  the main window*, and that row is gone, but `pitch_y` is still:
  * **rendered**: `Camera.matrix()` applies the tilt, and every consumer uses it: the GPU and CPU preview (`projection.py`
    numpy + GLSL), the final renderer, the 3D Editor's solid renderers (`solid/view.py`), the Blender scene export
    camera (`solid/io/blender.py`) and the HDRI key-light placement (`three_d/document.py`);
  * **editable**: the **3D Editor ▸ Camera ▸ Tilt** row (−180…180°, undoable; *Send to main window* carries it to the
    main fractal; *Reset view* restores it), and the **scripting API** (`camera.pitch_y`, in degrees; *Flame → Script*
    writes it);
  * **indirectly changed** by the main window's Image ▸ 3D camera ↻ *Revert* (restores the file's value), the Transform
    Editor's *New flame* (resets it to 0) and animation (interpolates it);
  * **stored**: read and written in `.flame` (`cam_pitch_y`) and `.fa` (`pitch_y`);
  * **shown**: the Info tab's 3D-camera line (`/ y N°`).

  A bundled sample uses it: `samples/sample flames/bel2.flame`, entry 5 "photon flower stan", has
  `cam_pitch_y = −0.885` (−50.7°).
* **Phase 2 done.** `ui/inspector_panel.py: InspectorPanel`, *View ▸ Show/Hide Inspector*, tab key `inspector/tab` with the
  old `panel/tab` read as a fallback (+ test); README. The flaky `test_status_bar_widgets_never_overlap` now waits for the
  layout instead of sleeping 50 ms.
* **Phase 3 done.** `GradientLink.follow_flame` on `flame_restored` with `_palette_seen` change detection;
  `GradientDocument.follow` (keeps the entry); no prompt on fractal switching (Q1). 6 new / rewritten tests in
  `test_gradient_link.py`, each failing if a prompt appears.
* **Phase 4 done.** `model/node_ops.inserted_at / nudged_position`, `widgets/node_commands.NodeCommands` (operations,
  actions, the picker), `NodeBar` double-click / keys / `menu_at`, `GradientStrip` double-click / focus proxy /
  `menu_at`, `NodePanel` as a view over the commands, `config.NODE_NUDGE_COARSE`. The strip and empty-space
  *Add node here* menu was included. 11 new tests in `test_node_editor.py`.
* **Phases 5–7 done.** Themes (`themes/`, `widgets/theming.py`, `theme_menu.py`, `syntax.py`), the readability fixes of
  §7.4, the Fragments editor-theme adapter; `fractal/blend.py`, `mutation.py`, `breeding.py`; `FlameGrid`,
  `GridRenderer`, `mutation_panels.py`, `MutationWindow`, `Ctrl+M`. The catalogue came out at 38 themes + System (28 dark,
  10 light), every one passing every contrast rule.
* **Phase 8.** README (menus, toolbar, *Themes*, *Mutate & Breed window*, gradient gestures, the library following the
  fractal, Inspector, layout), `docs/fragments.md`, `docs/rendering.md`, TASK_STATE round 11 with the review table
  (R1–R3, D1–D3, C1, T1). Verification results are recorded in TASK_STATE.
