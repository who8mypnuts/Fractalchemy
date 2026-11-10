# Plan — Sixteen improvements (S1–S16)

Status: **implemented** (round 13). E1–E15 answered (§2: all as recommended; E7 = option A after the explanation in §15.1; the `.chaos` curve rules of §16 added). This plan carries out the sixteen suggestions of
`plans/live-parameters-and-recording-plan.md` §11. That plan (called **Plan A** below) is approved with all nine of its
recommendations (D1–D9). Several items here build on it, and §19 gives one roadmap for both. The decisions this plan
needs are in §2, each with a recommendation. The checkboxes in §20 are ticked as work lands.

| # | Item | Section | Builds on |
|---|---|---|---|
| S1 | Parameter explorer grid | §3 | Plan A phases 1–2 |
| S2 | Run a script on many fractals | §4 | Plan A phase 1 (restricted mode), phase 2 (current values) |
| S3 | "Record changes" (relative) mode | §5 | Plan A phases 4–5 |
| S4 | Animate a parameter | §6 | Plan A phases 1–2 |
| S5 | Script console | §7 | Plan A phase 0 |
| S6 | Pin templates to the main window | §8 | Plan A phases 1–2 |
| S7 | Open Recent | §9 | — |
| S8 | Crash recovery (plus a shelf of discarded edits) | §10 | Plan A phase 0 (`edited`) |
| S9 | Undo History panel | §11 | §17 (history semantics, shared with S15) |
| S10 | Before / after compare | §12 | — |
| S11 | Command palette | §13 | best done last (it lists every action) |
| S12 | Random Batch symmetry | §14 | shares `add_symmetry` with Plan A's symmetry template |
| S13 | Instant tone-mapping | §15 | — |
| S14 | Format round-trip fuzzing | §16 | Plan A phase 0 (`flames_equivalent`) |
| S15 | Round-12 leftovers (old test file, file actions) | §17 | — |
| S16 | Transform Editor polish (parameter ranges, grips) | §18 | — |

The rules are those of Plan A §0: Qt-free cores under `widgets/` and `ui/`; windows only coordinate; `FractalDocument` owns
every edit; explicit state machines for lifecycles with more than two states; tunables in `config.py`; theme roles only;
docstrings everywhere; README *Layout* and TASK_STATE kept current. No `pitch_y` editing UI and no viewer *Detail* come
back.

---

## 1. Findings from the investigation (each checked in the code or by running it)

**F1. Unsaved fractal edits are discarded silently.**
* Choosing another fractal (`open_item` → `open_path` → `document.replace`) and quitting (`MainWindow.closeEvent`) never
  ask about the fractal, and nothing keeps the lost state. `closeEvent` asks about unsaved gradients, renders,
  animations, 3D and Fragments work, but not the fractal itself.
* README's promise, "nothing is written unless you save", holds, but "nothing is lost" does not. This shapes S8.

**F2. Undo history semantics.**
* A no-op edit still creates an undo step and marks the fractal modified. Verified: `set_view(zoom=<same zoom>)` →
  `can_undo` True, `modified` True.
* Undoing back to the loaded state leaves `modified` True, so the title keeps its `*`.
* The redo stack stores flames without kinds, so a history view could not label redo entries.
* The excluded old test file expects the opposite on all three points ("no change → no new step", "undo to the saved
  state clears modified", "Undo Move camera" action texts). This shapes S9 and S15.

**F3. The `.chaos` writer loses data.** A probe round-tripped 75 mutated flames through each format:
* `.fa`: lossless.
* `.flame`: only the final transform's `weight`, which no engine uses.
* `.chaos`:
  * **The parameters of variations whose parameter prefix is not the variation's name are dropped.** 31 real losses:
    `JuliaRandomN` (`JRN_*`), `depth_sine` (`ds_*`), `randCubes`. The cause is `chaos_writer._transform_body`, which
    keeps only keys starting with `name + "_"`.
  * `filter_radius` and the tone **curves** are not written.
  * Unnamed transforms come back named `Iterator N`.
  * Others are by design: `zoom` folded into `scale`, the pre affine folded into the affine, and xaos `None` written as
    all ones. These render the same. This shapes S14.

**F4. The file actions bypass the document.** `FractalFileActions._run.done` assigns `document.flame.name` and emits
`document.flame_renamed` itself, outside `FractalDocument`, against the "one document owns the edits" rule. It also
duplicates `FileActionsBase`: the write bookkeeping, `_fail`, `_ask_name` and `RECENT_WRITE_SECONDS` all exist twice
(S15).

**F5. Parameter-range rules are implemented once, privately.** `mutation.mutated_parameter` honours
`ParamInfo.min/max/cyclic/nonzero/int`. The Transform Editor and Formula Editor tables do not. The registry has 2679
parameters: 256 ranged, 56 cyclic, 36 non-zero and 296 integer (S16).

**F6. Instant tone-mapping is feasible without touching the samplers.**
* Both preview jobs keep `self.coloring` and tone-map on demand (`image()`).
* `RenderService` already pre-empts a job (pauses it, keeps its histogram, re-queues it).
* A colouring change today supersedes the job and re-renders from zero (S13).

**F7. The excluded `tests/test_fractal_files.py`** (18 tests, run one by one with a 120 s limit each):
* 4 pass unchanged;
* 9 fail on API drift (`undo_stack`, `actionCopy`, `model.opened_file()`, `files.paste()`, `suggested_file_name`);
* 3 expect behaviour the app no longer has (the three points of F2, a prompt when switching with unsaved edits,
  *Copy As* formats);
* 1 uses data that has since become valid (`crackle` is now supported);
* 1 hangs on a modal dialog from the old Save As flow.

Details are in §17.

**F8. Unused shortcuts.** `Ctrl+K` is unused in every window. `\` has no binding in the main window. `Ctrl+Shift+R` is
used only by the Fragments window, and shortcuts are window-local, so Plan A's Record keeps it.

---

## 2. Decisions (answered: all as recommended; E7 = option A)

| # | Question | Recommendation |
|---|---|---|
| E1 | Quitting with unsaved fractal edits: ask? | **Yes**: *"'x' has unsaved changes — Save / Discard / Cancel"*, like the gradient. Quitting is the one moment with no undo. |
| E2 | Switching fractals with unsaved edits: ask? | **No** (today's fast browsing stays). The edits go to the **Unsaved edits shelf** instead (S8b), so they are always recoverable. |
| E3 | Crash recovery at start-up: dialog, or status bar plus a menu (the Fragments convention)? | **A dialog**: *Restore / Not now / Discard*. "Not now" keeps it under *File ▸ Recover*. Lost fractal work deserves an interruption. |
| E4 | The undo history list: where? | **A third Inspector tab, "History"** (after Info / Image, so the saved tab index stays valid). |
| E5 | Undo / Redo action texts: "Undo Gamma"? | **Yes**, from the same labels as the History tab (the old tests expected this). |
| E6 | Before / after: which "before"? | **Hold `\`** for the fractal as loaded or last saved. **Shift+`\`** for the state before the last undo step. *View ▸ Compare* makes it sticky. |
| E7 | Instant tone-mapping: where? | **Option A — the main viewport only.** The Transform Editor / Animation previews (tiny renders, negligible gain) and the Render Image window (a separate "develop after render" feature with memory trade-offs, not planned) are unchanged. See §15.1. |
| E8 | Command palette: shortcut and scope | **`Ctrl+K`** in every window. It lists that window's actions plus global entries (windows, recent files, templates, themes). |
| E9 | Transform Editor parameter ranges: clamp or refuse? | **Clamp silently, with a status-bar note** (*"julian_power is an integer ≥ 1 — set to 1"*). Files, scripts and paste keep whatever value they carry. |
| E10 | Triangle grips: on by default? | **On**, with a *View ▸ Show grips* toggle (persisted). |
| E11 | Random Batch symmetry default | **None** (today's output), with the choice remembered. |
| E12 | Relative recording (S3): default style? | **Absolute stays the default.** *Record ▾* has *Values* / *Changes*. |
| E13 | Pinned templates (S6) that declare parameters: open the editor when run? | **No**: they run with their saved values, and *Adjust parameters…* in the same menu opens the editor's Parameters tab. |
| E14 | Batch apply (S2): output | **Always a new or appended `.fa`** (or `.flame`). The originals are never touched, and names stay unchanged unless a pattern is given. |
| E15 | Old test file (S15): the "prompt when switching" test | **Retire it** (E2 replaces it with the shelf). Port everything else. Restore F2's semantics (§17.2). Add *Copy Parameters As ▸ .flame / .chaos* (small; the old tests describe it). |

---

## 3. S1 — Parameter explorer ("show me eight versions")

**Goal.** A third tab in Mutate & Breed, **Explore script**. The grid shows the live script's result at the current
values in the centre, and eight variations around it. Clicking a cell adopts its values into the Parameters tab, and the
fractal follows (the same undo step as the live session).

**Design.**
* Qt-free `scripting/explore.py`:
  * `vary(specs, values, seed, rng, options) -> list[Variant]`, where `Variant(values, seed, notes)`.
  * Options: `spread` (0–1); `mode` (*around the current values* / *anywhere in range* / *new seeds only*); `locked`
    (names kept fixed); `vary_seed` (bool).
  * Rules:
    * bounded numbers → Gaussian around the current value, with sigma = spread × range / 4, clamped ("anywhere" is
      uniform in range);
    * unbounded → relative ±spread × (|v| + 1);
    * ints are rounded and never stay at the same value when spread > 0;
    * a `bool` flips with probability spread / 2;
    * a `choice` changes with probability spread;
    * `text` never changes.
  * `explore(code, snapshot, specs, values, seed, count, rng_seed, options, stop) -> list[Offspring]` runs `run_script`
    per variant in **restricted mode** (Plan A §4.3, so no side effects). It marks blow-ups with
    `mutation.is_stable(...)` (caption "⚠ blows up", still adoptable). `notes` lists the changed values
    ("Angle 23.5 · Copies 4 · new seed").
* The window: `MutationWindow` gains `EXPLORE_TAB`, with an `ExplorePanel` (spread slider, mode, vary-seed, a check list of
  the script's parameters for locking, and *New variations*).
  * It talks to the Script Editor through a small protocol, **`ScriptExploreSource`** (`available`, `reason`, `code`,
    `snapshot`, `specs`, `values`, `seed`, `adopt(values, seed)`, and the signal `changed`). `LiveParameters` implements
    it, and the main window connects the two, so neither window imports the other.
  * `OFFSPRING` gains **NEEDS_SCRIPT** (`no_script` from any state): *"Run a script with parameters in the Script
    Editor."*
  * Adopting (click or 1–9) calls `adopt(values, seed)`. The Parameters tab takes the values, a live re-run applies
    them (the same token, so one undo step), and the grid regenerates around the new values once the re-run lands.
  * The *Make it the fractal* menu entry stays available. It uses `replace_flame_parameters` (a separate undo step) for
    when the user wants the cell's flame without the live session.
* Also reachable from the Parameters tab: **Explore ▸** opens Mutate & Breed on this tab.

**Edge cases.**
* A script made INERT or DETACHED (Plan A D1) → NEEDS_SCRIPT with the reason.
* A slow script is stopped when the grid regenerates (a generation counter plus a stop event).
* An error in a variant shows the error as that cell's caption.

**Tests** (`test_mutation_window.py`, `test_script_explore.py`):
* `vary` determinism, locking, clamping and the int / bool / choice rules;
* `explore` refuses effects;
* the tab state moves through NEEDS_SCRIPT → GENERATING → READY;
* adopting cell 3 sets the tab's values and the flame equals `run_script(..., parameters=cell.values)`;
* one undo step across adoptions.

**Effort** about 1 day. **Risk** low.

---

## 4. S2 — Run a script on many fractals

**Goal.** Apply the current script (or a template) with chosen parameter values to many flames, and write the results
to a new or appended file. The originals are never modified (E14).

**Sources** (a combo box):
* the Fractal Library selection, via a new *Run Script on Selection…* entry in the library's menu;
* every flame of a chosen file;
* the *Randomly Generated* batch;
* the current fractal only.

**Design.**
* Qt-free `scripting/batch.py`:
  * `BatchSpec(code, name, parameters, seed_policy ("same" | "per flame"), name_pattern ("{name}", "{name} · {script}", …), on_error ("skip" | "stop"))`;
  * `apply_to_flames(spec, flames: Iterable[Flame], control, on_each) -> BatchReport`.
  * Each flame runs in restricted mode with the message *"not available when running on many fractals"*, so prompts,
    `update` and `save_flame` are refused. Each result is checked with `mutation.is_stable`.
* `ui/script_batch_window.py: ScriptBatchWindow(JobWindowBase)`, which gets the `JOB` machine, Start / Pause / Stop,
  the clock and "quit while running" for free.
  * Options panels: *Script* (the editor's script, or a template picker; parameter values from the Parameters tab or
    the defaults); *Source*; *Output* (a file path defaulting to `<source stem>-scripted.fa` next to the source, `.fa`
    or `.flame`; an existing file is appended to); *Names*; *Seeds*; *On error*.
  * Progress panel: count, current flame, a small preview of the last result, and a results list (✔ / ✖ with the error
    line / ⚠ unstable).
  * When finished: *Show the result file* (`fractal_library.show_file(path)`).
* The job thread, `ScriptBatchJob(QThread)`, uses `RenderControl` for pause / cancel between flames, and a stop event
  inside a flame. Results are **appended one by one** (`FractalFormat.append`), so a stopped batch keeps what it made.
  The write is registered with `wrote_recently`, so the library watcher does not reload.
* Entry points: the Script Editor's *Script ▸ Run on Many Fractals…*, the library's *Run Script on Selection…*
  (`LibraryContextMenu` gains a selection-aware extra action), and the command palette.

**Edge cases.**
* `.chaos` sources are readable; a `.chaos` output is not offered (lossy, F3).
* A source file that fails to parse is reported and skipped.
* An empty selection disables Start (`_problems()`, as in the Render Image window).

**Tests.**
* Qt-free: order, seeds, restricted refusal, `on_error`, name patterns.
* Window: a run over a 3-flame file appends 3 entries to a new `.fa`; Stop after the first keeps one; the source file
  bytes are unchanged; the `JOB` machine is driven.

**Effort** about 1 day. **Risk** low.

---

## 5. S3 — "Record changes" (relative recording)

**Goal.** A second recording style that writes *changes* rather than values, so a recording works as a filter on any
flame. For example `camera.zoom += 0.25`, `coloring.gamma += 0.5`, `transforms[0].rotate(15)` and
`gradient.adjust_stops(hue=30)`.

**Design.**
* `flame_diff(before, after, gradient=None, style="absolute" | "relative", hints=None)` (Plan A §7). The relative
  generators, per section:
  * Camera: `camera.pan(dx, dy)`, `camera.zoom += d`, `camera.rotate_by(d)`, and 3D `camera.pitch += d` and so on.
  * Colouring scalars: `+= d`. The background colour and curves stay absolute (a "colour delta" means nothing to users).
  * Affines: with M0 / M1 the 2×2 parts before and after, and R = M1·M0⁻¹:
    * R a rotation → `t.rotate(θ)`;
    * a uniform scale → `t.scale(s)`;
    * rotation × scale → both;
    * otherwise → `t.multiply(a, b, c, d)`.
    * The origin moves by `t.translate(dx, dy)`.
  * Weights and parameters: `+= d`.
  * Structure (add, remove, final) is the same as absolute.
  * Xaos stays absolute (links are on / off facts).
  * The gradient uses **operation hints** (below), and otherwise falls back to absolute.
* **Gradient operation hints.** `GradientDocument.apply_operation(operation, label=None)`. The whole-gradient panel
  passes labels (`reverse`, `invert`, `smooth`, `add-nodes`, `remove-nodes`, `randomize-*`).
  * `set_adjustments` is itself a hint: the `Adjustments` (rotation / hue / saturation / luminance).
  * `GradientLink.apply_gradient` forwards the last hint to `FractalDocument.set_gradient(gradient, hint=…)`. This is a
    new optional argument; the document stores it as `last_edit_hint` and emits nothing new.
  * New API `gradient.adjust_stops(hue, saturation, luminance)` and `gradient.rotate_stops(amount)` work like the
    library: simplify the palette to stops with the library's tolerance, apply `model.adjust.apply_adjustments`, and
    resample. The existing palette-based `gradient.adjust()` stays unchanged.
  * Random operations (*Random gradient*, *Randomize colours*) record absolutely, because a random result cannot be
    replayed as a change.
* **Verify, then fall back** (Plan A §7.5). Each relative statement is executed against `before` and must reproduce
  `after` within tolerance, or that section is recorded absolutely with a comment
  (`# recorded as a value: the change could not be expressed exactly`).
* UI: Plan A's Record action becomes a menu button, **Record ▾ Values / Changes**. The choice is persisted, and the
  status-bar indicator names the style.

**Tests.**
* Per section: relative output text; the invariant `run(diff(before, after)) ≈ after`.
* Applying a relative recording to a *different* flame changes it by the same amounts (zoom +0.25 stays +0.25).
* The affine decomposition for pure rotation, uniform scale, shear and reflection.
* Gradient hints for each library operation (and library-exact `adjust_stops`).
* Fallback when a hint does not reproduce the result.

**Effort** 1.5–2 days. **Risk** medium (the gradient hints touch the Gradient Library, with a small optional argument).

---

## 6. S4 — Animate a parameter

**Goal.** A Parameters-row menu entry, **Animate…**: sweep one parameter from A to B and create Animation keyframes, each
the script's result at that value (same seed, so only that parameter moves).

**Design.**
* `ui/script_animate.py: AnimateParameterDialog`. Fields:
  * *from* and *to* (defaults: the current value and the upper bound);
  * *keyframes* (2–120, default 5);
  * *first frame* (default: the playhead);
  * *spacing* (frames between keyframes, default fps / 2);
  * *easing* (linear / ease in-out over the values);
  * *target*: the current animation, or a new one.
  * A note explains that the Animation window interpolates *between* keyframes, so more keyframes follow a non-linear
    script more faithfully. Int and choice parameters get one keyframe per distinct value.
* The results are computed with `run_in_background` (restricted mode), then added through `AnimationDocument.capture(flame,
  frame, name=f"{param} = {value}")`.
  * The timeline has no undo (a known gap), so when keyframes already exist on the chosen frames the dialog asks
    *"Replace 3 existing keyframes?"*.
  * The Script Editor reaches the Animation window through a provider the main window passes (as for S1).
* The Animation window opens at the first new keyframe.

**Tests.** Values and frames for linear and eased sweeps; int and choice stepping; the flames equal
`run_script(..., parameters={p: v})`; replace-confirmation; a new animation versus the current one.

**Effort** about 0.5 day. **Risk** low.

---

## 7. S5 — Script console

**Goal.** A one-line `>>>` prompt under the output panel. Each line runs against the current fractal, and the fractal
changes as **one undo step per line**, only when something changed.

**Design.**
* `ui/script_console.py: ConsoleLine`, a one-line `CodeEditor` subclass, so syntax colours and `Tab` completion come for
  free.
  * Enter runs the line; Shift+Enter adds a line (small blocks such as `for t in transforms: t.rotate(5)`).
  * ↑ / ↓ walk the history (persisted, last 100, `script/console_history`).
  * Esc clears the line.
* Execution goes through the same runner and `SCRIPT_RUN` machine as Run (a console line is refused while a script
  runs), with the seed and restricted rules of a full run (prompts are allowed: the user is at the keyboard).
  * **Expressions echo**: if the last statement is an expression, it is rewritten to assign `__console_value__`, and
    its `repr` is printed (`>>> transforms[0].weight` prints `0.5`).
  * **Variables persist between lines**: plain values (numbers, strings, tuples, lists and dicts of them) assigned by a
    line are carried into the next line's namespace. API wrapper objects are not, because they are bound to the
    previous run's flame copy.
  * The undo step is labelled *"Console: camera.zoom += 1"* (S9). A line that changes nothing (print, inspection)
    records no step (`flames_equivalent`).
* **Recording**: while Plan A's recorder is on, console lines are inserted into the script *as typed* (they are already
  code). The resulting flame change is not diffed again, because console runs are `script` edits, which the recorder
  skips.
* Completion context: the console's completion sees the console's persisted variable names plus the API.

**Tests.** An echoed expression; an assignment that persists; one undo step per changing line and none for `print`; an
error shows its message without a line jump; history ↑ / ↓; recorded lines while recording.

**Effort** about 0.5 day. **Risk** low.

---

## 8. S6 — Pin templates to the main window

**Goal.** A **Scripts ▾** toolbar button and *Windows ▸ Scripts* menu in the main window, listing pinned templates. One
click runs a template on the fractal with its saved parameter values, without opening the editor (E13).

**Design.**
* The Templates tab gains *Pin to main window* / *Unpin* (context menu and a ★ column). The pins persist in QSettings
  `scripts/pinned`: a list of `{id, name, values}` (ids as in `Template.id`). Built-in templates are pinned by name.
* `ScriptEditorWindow.run_code(code, name, parameters, origin)` is a new public path that runs code **without loading it
  into the editor**. The output panel notes *"▶ Running Warm / cool shift (from the Scripts menu)"*. The live session
  remembers its origin, so no "changed since it ran" banner appears. Plan A's `run()` becomes `run_code(editor text, …)`.
* `ui/script_menu.py: ScriptsMenu(QMenu)`, which the main window creates. It offers the pinned entries (each with its
  last values), *Adjust parameters…* for the last-run pinned template (opens the Script Editor on its Parameters tab),
  *Manage…* (opens the Templates tab) and *Run on Many Fractals…* (S2).
* The values saved with a pin are updated whenever that template's Parameters tab values change while it is the live
  session's origin.

**Tests.** Pin / unpin persistence; running from the menu leaves the editor's text untouched and creates one undo step;
saved values are used; a missing template (a deleted user file) shows disabled with a tooltip.

**Effort** about 0.5 day. **Risk** low.

---

## 9. S7 — Open Recent

**Design.**
* `ui/recent_files.py: RecentFiles(QObject)`: a most-recently-used list of `(path, index, name, time)`, 10 entries, in
  QSettings `recent/fractals`. Entries are updated on every successful load (`MainWindow._loaded`) and save (the new
  entry signal from §17.3).
* *File ▸ Open Recent ▸*: "name — file.flame (#3)". Missing files are shown disabled, with "(missing)". There are
  *Clear list* and, via the palette, "Open recent: …".
* Opening a recent entry shows the file in the library's temporary area and loads that entry (`open_file_path` plus the
  index).

**Tests.** The order (move to front, deduplication by path and index), the cap, persistence, and missing files.

**Effort** about 2–3 hours. **Risk** none.

---

## 10. S8 — Crash recovery, and the Unsaved edits shelf (S8b)

**S8, crash recovery.**
* A Qt-free store `fractalchemy/autosave.py`, generalised from `fragments/session.AutosaveStore`, so both windows share
  one implementation (DRY). The Fragments window is switched to it with no behaviour change.
  * `RecoveryStore(folder)` with `write(name, text, meta)`, `pending()` and `clear(name)`.
  * Files live under the config or cache folder (`cache_dir() / "recovery"`), never next to user files.
  * Each running instance holds a `QLockFile` (`recovery/<instance>.lock`). Entries of instances whose lock is stale
    are the recoverable ones. This is safe with two instances open, and Qt detects stale locks on every platform.
* `ui/recovery.py: RecoveryKeeper(document)`:
  * `document.edited` restarts a timer (`config.RECOVERY_DELAY_MS = 3000`).
  * When the fractal is modified, it writes the `.fa` text and `meta.json` (source path and index, name, time, the last
    few undo labels).
  * It clears the entry when the fractal is saved or replaced unmodified, and on clean exit.
* **Start-up (E3):** once the main window is shown, if any entry is pending, a dialog lists it: *"Fractalchemy did not
  close properly. Restore 'x' (edited 14:03, from candy.flame #3)?"* [Restore] [Not now] [Discard].
  * Restore uses a new `document.restore_unsaved(flame, path, index)`. It is like `replace`, but marks the fractal
    modified, so the title shows `*` and Save writes back into the original entry.
  * "Not now" keeps the entry under *File ▸ Recover ▸*.

**S8b, the Unsaved edits shelf (E2).**
* When `replace` is about to discard a modified fractal, `RecoveryKeeper` first puts it on the shelf:
  `recovery/shelf/<time>-<name>.fa` plus its meta. It keeps 20, first in first out (`config.SHELF_SIZE`).
* *File ▸ Recover ▸* lists the shelf ("x — candy.flame #3, edited 14:03") and *Clear shelf*. Choosing one restores it as
  above.
* The shelf survives restarts and is cleared only by the user or by the cap.

**Quit (E1).** `closeEvent` asks *Save / Discard / Cancel* when the fractal is modified, through
`FileActionsBase.confirm_discard`, which the fractal file actions inherit after §17.3.

**Tests.**
* Store: write, pending, clear, stale-lock detection with two stores, and no pending entry for a live lock.
* Keeper: the debounce writes once per pause, clears on save, and shelves on replace-while-modified.
* Start-up: the dialog offers a stale entry; restore gives `modified` True and the source kept.
* Quit: the prompt appears only when modified.
* Fragments: still recovers its session (existing tests).

**Effort** about 1 day for S8 and 0.5 day for S8b. **Risk** low (separate folder, nothing near user files).

---

## 11. S9 — Undo History (Inspector ▸ History)

**Goal.** See every step as a readable label, and jump to any of them.

**Design.**
* **Labels.** `fractalchemy/ui/undo_labels.py: undo_label(kind, extra="") -> str` is a table keyed by kind prefix:

  | Kind | Label |
  |---|---|
  | `view` | Camera |
  | `camera3d` | 3D camera |
  | `coloring:gamma` | Gamma |
  | `coloring:gamma,brightness` | Colouring |
  | `curve:red` | Red curve |
  | `palette` | Gradient |
  | `affine:coefs:2` | Triangle 3 |
  | `rotate:coefs:2:…` | Rotate triangle 3 |
  | `fields:weight:0` | Weight 1 |
  | `variation:julian:1` | julian on 2 |
  | `param:julian_power:1` | julian_power on 2 |
  | `chaos:0:2` | Xaos 1 → 3 |
  | `add-xform` | Add transform |
  | `paste` | Paste parameters |
  | `mutate` | Adopt mutant |
  | `breed` | Adopt child |
  | `script` | Script: \<name\> |
  | console | Console: \<line\> |

  `apply_script` gains an optional `label`, passed by the Script Editor. A test runs every kind produced by the Plan A
  §3.3 mutator table and asserts each gets a specific label, not the generic fallback.
* **Document API** (with §17.2):
  * `_undo` and `_redo` both hold `Step(kind, label, flame, time)`;
  * `history() -> list[HistoryEntry(label, time, position)]` plus `current_index`;
  * `jump_to(index)` moves steps between the stacks and emits **one** `flame_restored` plus
    `edited("undo" | "redo")`;
  * `undo_label` / `redo_label` feed the action texts (E5).
* `ui/history_panel.py: HistoryPanel` is the Inspector's third tab.
  * A list: the loaded state at the top (*"Opened candy.flame #3"*), the steps below it, the current one bold, the redo
    steps dimmed, and the saved position marked 💾.
  * Clicking a row calls `jump_to`. A right-click offers *Compare with this state* (S10, holding the compare image) and
    *Copy parameters of this state*.
  * Thumbnails are a follow-up (a render of each state at thumbnail priority). They are not in version 1.

**Tests.** Labels for all kinds; `jump_to` forward and back emits one restore; the redo steps keep their labels; the
action texts follow; the panel rows follow undo, redo and new edits; a jump clears the redo tail only when a new edit
follows.

**Effort** about 1 day (with §17.2). **Risk** low (undo internals change, covered by the ported old tests).

---

## 12. S10 — Before / after compare

**Goal.** Judge an edit without undo-look-redo.

**Design.**
* `MainWindow` installs a key filter for `\` press and release (auto-repeat ignored). Holding `\` shows **before**.
  Shift+`\` uses the state before the last undo step. *View ▸ Compare with Original* (checkable) makes it sticky (E6).
* `FractalViewport.set_compare(flame | None)`.
  * On the first request it renders `flame` with the **same view geometry** (its own camera at the current image size;
    `render_camera(flame)` gains an optional flame argument) under a `("compare", generation)` key.
  * It paints that image instead of the current one while compare is on, with a top-left label *"Before — as loaded"*
    or *"Before — last step"* drawn on a translucent theme panel.
  * The compare image is cached while the flame and the view geometry are unchanged, so repeated presses are instant.
* History panel hook (S9): *Compare with this state* passes that step's flame.

**Tests.** Pressing `\` submits one compare render and shows its image; release restores the current image without a
new render; the cache is hit on the second press; sticky mode; Shift uses the undo top.

**Effort** about 0.5 day. **Risk** low. A split-view divider is a possible follow-up and is not in version 1.

---

## 13. S11 — Command palette (`Ctrl+K`)

**Design.**
* Qt-free `fractalchemy/search.py: fuzzy_score(query, text) -> float | None`. Subsequence matching, with bonuses at word
  starts and for consecutive characters, and case-insensitive. The Fractal Library's filter could adopt it later.
* `widgets/command_palette.py: CommandPalette(QDialog)`: a frameless popup near the top centre of the active window,
  with a query line and a result list (icon, title, the menu path dimmed, the shortcut right-aligned).
  * Enter runs; Esc closes; ↑ / ↓ move; disabled commands are shown dimmed and cannot run.
  * The last 5 commands used appear first when the query is empty.
* `ui/commands.py: command_sources(window) -> list[Command(title, path, shortcut, icon, enabled, run)]`:
  * that window's menu bar, walked recursively (submenus included; separators and invisible actions skipped);
  * global entries from the main window: *Windows ▸ …*, *Open recent: …* (S7), *Run template: …* and *Pinned: …*
    (S6), *Theme: …* and *Recover: …* (S8).
* A `Ctrl+K` action is added to the main window and every tool window through one helper, `install_palette(window)`.

**Tests.** Fuzzy ranking (`"undo"` ranks *Edit ▸ Undo* first; `"gl"` finds *Gradient Library*); the palette lists the
Script Editor's actions when opened there; Enter triggers the action; disabled entries do not run; recent-first.

**Effort** about 1 day. **Risk** low.

---

## 14. S12 — Random Batch symmetry

**Design.**
* Qt-free `fractal/symmetry.py: add_symmetry(flame, order, rng=None) -> int`, a port of flam3's
  `flam3_add_symmetry`:
  * order < 0 adds a bilateral mirror transform (linear, `(-1, 0, 0, 1, 0, 0)`);
  * |order| ≥ 2 adds |order| − 1 rotated linear copies at `2πk/n`;
  * each added transform has weight 1, colour speed 0 (Apophysis's *symmetry* 1), linear 1 and colours spread over 0..1;
  * order 0 draws from flam3's distribution (`-4 -3 -2 -2 -2 -1 -1 -1 2 2 2 3 3 4 4`, and sometimes wider).
  * It returns the number of transforms added.
* `RandomOptions` gains `symmetry: str = "none"` (none / random / bilateral / rotational / dihedral) and
  `symmetry_orders: tuple[int, int] = (2, 6)`. `random_flame` applies the symmetry before framing and the stability
  check.
* The Random Batch window gets a *Symmetry* combo and an order range (enabled for rotational / dihedral), persisted
  (E11).
* The scripting API gains `add_symmetry(order)`. Plan A's converted *Make rotational symmetry* template calls it (one
  implementation). Mutate's *Keep symmetry* already leaves colour-speed-0 transforms alone.

**Tests.** Transform counts and affines for orders −1, 2, 3, −4; colour speeds; reproducibility with a seed; the batch
option adds the transforms; the default *none* gives byte-identical batches to today's with the same seed.

**Effort** about 0.5 day. **Risk** low.

---

## 15. S13 — Instant tone-mapping for colouring edits

**Goal.** Brightness, gamma, threshold, vibrancy, contrast, background and curves change the picture at once, instead of
restarting the render.

**Design** (F6):
* **Jobs.** `CpuRenderJob.retone(coloring)` and `GpuRenderJob.retone(coloring)` set `self.coloring`, rebuild the curve
  tables (CPU: `curve_luts`; GPU: release and re-upload `curves_tex`), and return `self.image()`. The histogram is
  untouched. Solid (3D) jobs do not have `retone`.
* **Service.**
  * `RenderService.retone(key, coloring)` (GUI thread) records the latest coloring per key in `self._retones`. It is
    *not* put in the request queue, because `submit` de-duplicates by key and would drop the paused job's re-queued
    request.
  * `_urgent_pending()` counts pending retones, so a running job for that key **yields** through the existing
    pre-emption path (paused and re-queued with its histogram).
  * The worker's `_next()` handles retones first. It finds the job in `_paused` or `_retained`, calls `retone`, and
    emits `pass_done(key, image, stats)` with the same key. Nothing found → `retone_missed(key)`.
  * The job then resumes refining with the new colouring.
* **Retained jobs.** `submit(..., retain=True)` (only the viewport uses it) keeps the *finished* job in `_retained[key]`
  instead of closing it. There is one retained job (`config.RETAINED_JOBS = 1`). Cancelling or superseding drops it;
  the worker does the closing (GL objects belong to its thread).
* **Viewport.** `coloring_changed` → `_retone()` instead of `_render_interactive()`.
  * The retone path is taken when a current key exists and the flame without its colouring equals the flame the job
    was submitted with (`_submitted_signature`, from `to_dict()` without `coloring`). The viewport then calls
    `service.retone(self._current_key, flame.coloring)`.
  * Otherwise, or on `retone_missed`, it falls back to today's interactive render.
  * Palette edits still re-render: the histogram stores colours, so a palette change needs new samples.
* `FractalDocument` is unchanged. Undo of a colouring edit arrives as `flame_restored`. That path compares the
  signature too, and retones when only the colouring differs (a common case: undoing a gamma drag).

### 15.1 Scope (E7 = option A), with the measurements behind it
* A preview render samples (slow: points through the transforms into a histogram), then tone-maps (fast: the
  histogram into a picture). Only the tone-mapping depends on brightness, gamma, threshold, vibrancy, contrast,
  background and curves. The gradient is baked in while sampling.
* Measured on candy #3 at viewport size in the sandbox:
  * software OpenGL: 9 s of sampling to quality 16, and **0.039 s** to tone-map again;
  * CPU engine: 106 s to quality 64, and **0.75 s** to tone-map again.
* **Viewport only:**
  * The Gradient Library's mirror gets it for free.
  * The Transform Editor and Animation previews are tiny renders that redraw in tens of milliseconds anyway.
  * The Mutate grid and the thumbnails regenerate or show files.
  * The 3D Editor and Fragments have other pipelines.
  * The Render Image window (tiled, histograms freed per tile) would need a separate "develop after render" feature
    with memory trade-offs; it is not in this plan.
* **Cost:** one finished viewport job is retained, about 70 MB at typical viewport sizes and up to about 750 MB at the
  bucket limit. It is dropped as soon as anything needs a full re-render.

**Tests.**
* Job level, CPU: after 3 passes, `retone(c2)` equals `tonemap(job.histogram, ToneParams.derive(c2, …))` exactly, and the
  samples are unchanged. GPU (llvmpipe): the same against `image()` after a manual coloring swap, and GPU and CPU agree
  as in `test_render.py`.
* Service: a retone during a running job pre-empts and resumes it (the sample count continues from where it was); on a
  retained job it emits one pass with no new samples; a missing job → `retone_missed`.
* Viewport: `set_coloring(gamma=…)` gives no new `submit` (spied) and a new image within one event-loop turn; a palette
  edit still submits; undoing a gamma change retones.

**Effort** 2–2.5 days. **Risk** medium (render service internals; covered by the existing render and viewport tests).

---

## 16. S14 — Format round-trip fuzzing, and the fixes it finds

**Design.**
* `tests/test_format_roundtrip.py`. The generator combines:
  * `mutation.mutate` with every operator on the three sample flames × 25 seeds;
  * `breeding.breed` in all four modes;
  * synthetic extremes: pre and post affines, curves, a 3D camera with `pitch_y`, xaos with zeros, a final transform,
    opacity 0, `var_color`, names with `<&"'>` and Unicode, tiny and huge numbers, and a non-empty `unsupported`.
* For each format it writes, reads back and compares with `flames_equivalent` (Plan A §3.5), extended with
  **per-format equivalences**, each with a reason in a table in the test:
  * `.chaos`: `None` xaos ≡ all ones; short rows padded; `zoom` folded into `scale`; the pre affine folded (compare
    `combined_coefs()`); the final transform's colour fields ignored.
  * `.flame`: the final `weight` ignored.
* Also: clipboard text in all three formats (`flame_to_text` / `flame_from_text`), and `.fa` append / replace / remove
  on multi-entry files.
* **Fixes from F3** (each with a regression test):
  1. `chaos_writer._transform_body` writes a variation's parameters from the registry (`V.REGISTRY[name].params` keys,
     plus any `parameter_owner(key) == name`), not by prefix.
  2. The reader maps `Iterator N` names back to `""` (the writer's default names), so unnamed transforms stay unnamed.
  3. **Curves — read and write (decided).** Chaotica stores tone curves in `<imaging><curves>`: one `<curve name="…">`
     per channel, holding two `<table>`s, the x values and the y values of its control points (not always sorted).
     The two sample worlds establish the channel names: `satania_spikobius.chaos` has `overall`, `0`, `5`, `10`, and
     `tatasz_tram_rails.chaos` has `0`, `5`, `10`. So `overall` is the master curve and `0` / `5` / `10` are red /
     green / blue.
     * **Reading:** the reader maps these channels onto `Coloring.curves` (points sorted, the identity when a curve is
       absent). Unknown curve names are ignored. Sample `.chaos` files now render with their curves, which is closer to
       Chaotica (a visible change, noted in the README).
     * **Writing:** whenever a flame's curves differ from the identity (in other words, they were loaded or edited),
       the writer emits a `<curves>` block with every non-identity channel it can name (`overall`, `0`, `5`, `10`). The
       alpha curve has no known Chaotica channel, so it is a documented loss.
     * Writers of `.chaos` text today are *Copy Parameters As ▸ .chaos* (E15) and *Save As ▸ New File* with a
       `.chaos` name, which is added with this item. `ChaosFileFormat` gains `append` (a new file, or an `<IFS>`
       inserted before `</world>` of an existing one). It does **not** gain in-place `replace`: regenerating an entry
       from our model would throw away Chaotica-only data (layers, shaders), so *Save* on a flame opened from `.chaos`
       still asks for a file, as today.
     * Housekeeping found on the way: `fractal/formats/registry.py` is an unused duplicate of the package
       `__init__` (nothing imports it); it is deleted.
  4. `filter_radius`: Chaotica has no equivalent (it has `antialiasing_mode` / `image_aa_level`), so this is a
     documented loss in README's format table.

**Effort** about 0.5 day, plus 0.5–0.75 day of fixes. **Risk** low (tests; the fixes touch `.chaos` reading and writing only).

---

## 17. S15 — Round-12 leftovers

### 17.1 The old test file (F7)
Port, then delete `tests/test_fractal_files.py` and the `pytest.ini` ignore. The 18 tests, one by one:

| Test | Disposition |
|---|---|
| clipboard round trip in three formats; chaotica writer round trip; save writes back into its own entry; destroying an edited document is silent | **pass today** → moved as-is into `test_formats.py` / `test_main_window.py` |
| document records edits and merges rapid ones | **port** to `can_undo` / `undo()`; also asserts §17.2's no-op and saved-position rules |
| undo / redo actions follow the document | **port**; asserts E5's "Undo Camera" texts |
| undoing a gradient edit refreshes the gradient editor | **port**. The follow rule (Q1 of the previous plan) makes the library *unmodified* after following, so that assertion is dropped. The refresh is kept. |
| copy / paste and copy-as | **port** to `actionCopyParameters`, plus the new *Copy Parameters As ▸ .flame / .chaos* (E15) |
| save as new file defaults to `.fa` / appends; several fractals collect in one `.fa`; opened file listed above the library; refreshes after entry operations; refresh never raises a dialog | **port** `model.opened_file()` → `model.open_file` |
| save as can write `.flame` and `.chaos` | **port**. The hang was the old modal flow; it uses the current `save_as_new_file` with a patched dialog. |
| saving with unsupported variations warns first | **port** with a genuinely unknown variation name (`crackle` is now supported) |
| new file suggested as fa with a date and counter | **retire**. Today's suggestion (`<name>.fa` next to the source) is deliberate, and the README documents it. |
| paste copes with every kind of bad clipboard text | **port** to `MainWindow.paste_parameters` (no dialog storm, a status message) |
| opening another flame with unsaved edits asks | **retire** (E2); replaced by the S8b shelf tests |

### 17.2 History semantics (restored, shared with S9)
* **No-op edits record nothing.** Each mutator compares before it records. The `_record` call moves after a cheap
  equality check of the touched part (for example `set_view` compares centre, zoom and rotate). Coalescing is
  unchanged.
* **The saved position.** The document remembers the undo depth at load or save (`_saved_depth`, or None once that state
  is unreachable). `modified` becomes `depth != _saved_depth`, so undoing back to the loaded or saved state clears the
  `*`, and redoing sets it again. `modified_changed` is emitted on each flip. This matches the old tests and every
  mainstream editor.
* Redo entries keep their kinds and labels (S9).

### 17.3 `FractalFileActions` on `FileActionsBase` (F4)
* The subclass keeps only the fractal flows (save, the three Save As variants, `_suggested_path`). It uses the base's
  `_run_write`, `_fail`, `_ask_name("fractal", …)`, `wrote_recently` and `RECENT_WRITE_SECONDS`.
* The base's `file_written(Path)` stays (the Gradient Library listens to it). The fractal subclass adds
  `entry_written(object, int)`, which the main window connects to instead.
* Renaming goes through a new `FractalDocument.rename(name)`, which emits `flame_renamed`. The file actions no longer
  touch `document.flame` or emit document signals.
* `confirm_discard` and `_document_name` / `_document_modified` are implemented for the quit prompt (E1).

**Tests.** The ported file above, plus: `rename` emits once; `entry_written` carries path and index; `wrote_recently`
shared; the quit prompt.

**Effort** about 0.75 day. **Risk** low.

---

## 18. S16 — Transform Editor polish

### 18.1 Parameter ranges (E9, F5)
* Qt-free `fractal/variations.py: constrain_param(key, value, previous=None) -> tuple[float, str]` returns the allowed
  value and a note. The rules, extracted from `mutation.mutated_parameter` so there is **one** rule set:
  * clamp to `[min, max]`;
  * cyclic values wrap;
  * integers round;
  * non-zero values never become 0 (they keep `previous`, or become ±the smallest step).

  The mutation engine calls it too (no behaviour change; its tests guard this).
* `ValueRow.constrain: Callable[[float], tuple[float, str]] | None`. `ValueTable` applies it to typed values and to
  every drag step, writes the constrained value back into the cell, and emits the note through a new `note(str)`
  signal. The Transform Editor's status bar shows it.
* `param_rows` passes `constrain` for every declared parameter. Rows for parameters no formula declares stay free.
* The Formula Editor's variables panel uses the same helper.
* Not constrained: `document.set_param` itself, scripts, files, paste and mutation input. Only the UI gestures are
  (E9).

### 18.2 Rotate / scale grips (E10)
* `TriangleView` draws, around the **selected** triangle:
  * a **rotate grip**, a small circle on the line from the pivot through X, at `GRIP_DISTANCE_PX = 28` beyond the
    triangle's extent along that ray;
  * **scale grips**, small squares at the corners of the triangle's screen-space bounding box, with a 6 px margin.
* The grips use the canvas's theme-tinted colours, and are drawn only when *View ▸ Show grips* is on.
* `Hit` gains `grip: str | None`. `_hit` tests the grips first (selected triangle only).
* A press on a grip starts `begin_triangle_drag(MODE_ROTATE | MODE_SCALE, …)`, the existing maths, so Shift snapping,
  the pivot modes and Esc-cancel behave exactly as for the edge gestures.
* Cursors: rotate grip → a rotate cursor (`Qt.CursorShape.SizeAllCursor` fallback); scale → the diagonal resize
  cursors.

**Tests.** `constrain_param` for each rule; a typed out-of-range value is clamped with a note; a drag stops at the
bound; the mutation engine's output for a fixed seed is unchanged; grips are hit-tested only when shown, and only on the
selected triangle; dragging the rotate grip by 90° about the pivot gives the expected triangle (against `drag_triangle`
directly); the toggle persists.

**Effort** about 0.5 day for 18.1 and about 1 day for 18.2. **Risk** low.

---

## 19. One roadmap for Plan A and this plan

The order follows the dependencies, and puts the data-protection work early:

1. **Foundations**: Plan A phase 0 (API `pre` and curves, `edited`, the token fix, codegen, window split) **together
   with** §17.2 (history semantics) and §17.3 (file actions). All three reshape `FractalDocument` and the file
   actions, so they are done once.
2. **Protect the user's work**: S9 (History), S7 (Recent), S8 + S8b (recovery, shelf, quit prompt), S14 (fuzzing +
   `.chaos` fixes), the rest of S15 (the old tests ported, *Copy Parameters As*).
3. **Live parameters**: Plan A phases 1–3, then S5 (console), S6 (pinned), S1 (explorer), S4 (animate), S2 (batch).
4. **Recording**: Plan A phases 4–5, then S3 (relative).
5. **Rendering**: S13 (instant tone-mapping), S10 (before / after).
6. **Polish**: S12 (symmetry), S16 (ranges, grips), then S11 (palette, last, because it indexes every action the
   earlier waves add).
7. **Documentation, review, verification**: README (every new feature and module in *Layout*), `docs/scripting.md` and
   `docs/state-machines.md` regenerated, TASK_STATE Round 13, the rubric review, the full suite plus `test_variations`
   plus pyflakes plus `tools/state_machines.py --check` against the baseline.

Each wave ends green and is committed on its own. Within a wave, each item is its own commit.

**Effort.**
* This plan: ≈ 15 days (S1 1, S2 1, S3 1.75, S4 0.5, S5 0.5, S6 0.5, S7 0.25, S8 1.5, S9 1, S10 0.5, S11 1, S12 0.5,
  S13 2.25, S14 1, S15 0.75, S16 1.5).
* Plan A: ≈ 4.5 days.
* Together: about four working weeks.

### Compatibility guardrails (in addition to Plan A §10)

| Surface | Guarantee | Checked by |
|---|---|---|
| `RenderService.submit` | Unchanged for every existing caller. `retain` and `retone` are opt-in (viewport only). | `test_render`, `test_viewer_controls`, thumbnails, mutation grid tests |
| Undo / modified | Coalescing unchanged. No-op edits no longer record (F2): a fix, with tests. | ported old tests, `test_main_window`, `test_editor` |
| File formats | `.fa` and `.flame` output unchanged. `.chaos` output gains the dropped parameters (a fix). | S14 suite, `test_formats`, `test_fractal_formats` |
| Mutation engine | Identical output for a fixed seed after `constrain_param` is extracted. | `test_mutation` (seeded) |
| Random Batch | Symmetry *none* → identical batches for a fixed seed. | S12 test |
| Fragments autosave | Same behaviour on the shared `RecoveryStore`. | existing Fragments session tests |
| Library context menu | Existing entries and order unchanged. The new entries are appended. | `test_library` |
| Inspector / drawer tabs | New tabs appended. Saved indices stay valid. | existing persistence tests |
| Themes | No new roles. Grips, labels and the palette use existing roles. | `test_themes`, `test_theming` |

---

## 20. Progress
- [x] Wave 1 — Foundations (Plan A phase 0 + §17.2 + §17.3)
- [x] Wave 2 — S9 · S7 · S8 / S8b + quit prompt · S14 + `.chaos` fixes · S15 port + *Copy Parameters As*
- [x] Wave 3 — Plan A phases 1–3 · S5 · S6 · S1 · S4 · S2
- [x] Wave 4 — Plan A phases 4–5 · S3
- [x] Wave 5 — S13 · S10
- [x] Wave 6 — S12 · S16 · S11
- [x] Wave 7 — docs, review, full verification

### Log
* *(implemented)* Every wave. Notes beyond the plan:
  * Found on the way and fixed: Ctrl+wheel zoom changed the camera outside the document (Undo restored the centre but
    not the zoom); the lossy-save question for unsupported variations had gone missing (restored, `_confirm_lossy_save`);
    a watcher reload of the shown fractal — and the library's rescan of the opened file — could raise a modal dialog for a
    file caught mid-write (now status messages).
  * The before / after render runs at the editor preview's priority (ahead of the viewport), so a quick look is quick.
  * The command palette is an application-wide `ShortcutOverride` filter (one install covers every window, however late it
    is created); its recent list is keyed by the menu path.
  * `Ctrl+K` also opens from *Help ▸ Command Palette…*.
* *(approved)* E1–E15 answered; E7 = A (viewport only) after §15.1's explanation; `.chaos` curves are read and written (§16 fix 3); implementation starts with Wave 1.
* *(planning)* Investigation: the format probe (75 mutated flames × 3 formats), the old test file run test by test, the
  undo semantics checked in a script, and the render job / service internals read for S13. Findings F1–F8 are in §1;
  the decisions to confirm are E1–E15 in §2.
