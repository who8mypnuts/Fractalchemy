# Plan — Live script parameters, and recording actions as a script

Status: **implemented** (round 13). All nine recommendations in §2 were accepted. The suggestions of §11 are planned in `plans/improvements-s1-s16-plan.md`, which also gives the combined roadmap (§19 there). This is the working plan: it is refined as the questions in §2 are answered,
then followed phase by phase, with the checkboxes in §12 ticked as work lands. §11 lists further suggestions for the
user to accept or decline; none of them is in scope until accepted.

Scope, as requested:

1. **Live parameters.** A script declares tunable inputs with `param(…)`. The Script Editor's drawer gains a fifth tab,
   **Parameters**, with one control per declaration. Moving a control re-runs the script from the pre-run snapshot after a
   short debounce, so the fractal follows the control live while the whole session stays **one undo step**. `param()`
   returns the default when nothing is set, so scripts behave the same headless and in tests.
2. **Record actions as a script.** A **Record** toggle on the Script Editor's toolbar. While it is on, every edit made
   in the application (viewport camera, Image tab, 3D camera, colouring, curves, Gradient Library, Paste Parameters, …)
   appends the API statements that reproduce it, at the cursor. A slider drag becomes one statement. Recording stops
   when the user presses Run, and a recording can be saved as a template like any script.

---

## 0. Rules this plan follows

These are the conventions of the previous plan (`plans/mutate-breed-themes-plan.md` §0), plus what round 12 added:

* **Layering.** Qt-free cores (`scripting/`, `fractal/`, `model/`, `machines/`) sit under `widgets/` and `ui/`. The diff
  generator, the parameter model and the live-effects rules are Qt-free and tested headlessly.
* **Windows coordinate and nothing more.** `ui/script_editor_window.py` is already **800 lines**, well above the ~500-line
  convention. New behaviour goes into helper modules (`script_live.py`, `script_recorder.py`,
  `script_parameters_tab.py`). Phase 0 also moves the actions and the output panel out of the window (§3.6), so the
  window shrinks even though it gains features.
* **One document owns the edits.** `FractalDocument` remains the only thing that changes the main flame. Live re-runs
  go through `apply_script`. The recorder only *listens* and never edits the flame.
* **Explicit state machines** (`fractalchemy/machines/`). Any new lifecycle with more than two states gets a spec in
  `machines/specs.py`. Button states and labels are derived from the machine. The tests run in strict mode, and
  `docs/state-machines.md` is regenerated with `tools/state_machines.py`.
* **Tunables in `config.py`. Persistence in QSettings** under the existing `script/…` namespace.
* **Deterministic randomness.** Live re-runs reuse the seed of the run that declared the parameters.
* **Themes.** New widgets use theme roles (`set_themed_style`, `colored_html`, `current_theme()[role]`) and stay within
  the WCAG-checked roles (`text`, `dim_text`, `success`, `warning`, `error`, `error_soft`). No new hard-coded colours.
* **Standing removals stay removed.** No `pitch_y` editing UI and no viewer *Detail* (Full / ½ / ¼) is introduced.
  The model still carries `camera.pitch_y` (decision Q2 of the last plan). The diff generator treats it like any other
  camera field, so it appears in a recording only if something actually changed it.
* **Docstrings on every public name.** The README *Layout* lists every new module. `docs/scripting.md` is regenerated
  from `scripting/docs.py` with `tools/scripting_reference.py`. TASK_STATE gets a Round 13 entry.
* **Review rubric** as before (architecture 40 / DRY 30 / comments 20 / tests 10, exit ≥ 90, no gate below 85 %).

Baseline for this plan: `728bcd8`. Full suite **703 passed, 1 skipped** (strict machines), `test_variations` 1707 passed,
pyflakes clean, `tools/state_machines.py --check` passes. Every phase is compared against this.

---

## 1. Findings that shape the plan

### 1.1 How the proposal's names map onto the code as it is

The feature descriptions name a few classes that do not exist under those names. This is what they correspond to, so
that the plan builds on the real structure:

| The proposal says | What the code has | Consequence for the plan |
|---|---|---|
| `InteractionCommands` gains `param()` | There is no such class. Every script global is a method of **`ScriptContext`** (`scripting/api.py`), listed in `FUNCTION_NAMES` and documented in `docs.GLOBALS`. | `param()` becomes a `ScriptContext` method, is added to `FUNCTION_NAMES`, and gets a `docs.GLOBALS` entry plus a new *Parameters* category. |
| `ScriptState` gets `parameters` / `declarations` | `ScriptState` is the **state enum of the `SCRIPT_RUN` machine** (idle / running / waiting / stopping). Per-run data lives in `ScriptContext` (during the run) and `ScriptResult` (after it). | The declarations are collected in `ScriptContext` and returned in new `ScriptResult` fields. `ScriptState` gains two states (§5.2). |
| `ScriptSession.run()` / `rerun()`, `ScriptSession._snapshot` | There is no session class. `ScriptEditorWindow` holds `_snapshot`, `_run` (the undo-coalescing token) and `_run_updated`, and calls `ScriptRunner.run(code, flame)`. | A new `LiveParameters` helper (`ui/script_live.py`) owns the live session. The window keeps one shared "start a run" path for full runs and re-runs (§5). |
| `apply_script(flame, run)` coalesces by run token | ✔ Exactly so (`FractalDocument._script_run`). | Re-runs reuse the token of the declaring run, so the whole session is one undo step. A latent edge is fixed in §3.4. |
| `list_gradient_presets()` | Not in the scripting API. The only presets are the six in `formulas/authoring.GRADIENT_PRESETS` (Fire, Ocean, Forest, Candy, Greyscale, Yellow · cyan · magenta). There is no "Aurora". | Optional small addition: `list_gradient_presets()` and `gradient.preset(name)` (§4.5). `choices=` accepts any list either way. |
| Parameters tab "like ImagePanel's groups (FloatRow already exists)" | ✔ `widgets/float_row.FloatRow` (label + slider + spin box, `value_changed`, silent `set_value`). | Used for float and int rows. Its slider's `sliderReleased` gives the end of a drag. |
| The document "keeps the flame before and after each edit" | Only partly. `_record(kind)` stores the **before** state of each *undo step*, and coalesced edits share one step. The after state is simply the current flame. Nothing stores a per-edit pair. | The recorder keeps its own baseline copy (the proposal already says `previous = flame.copy()`). |
| `_record(kind)` names the kind | ✔ In the `view`, `camera3d`, `coloring:gamma`, `curve:red`, `palette`, `paste`, `script`, `affine:coefs:2`, `fields:weight:0`, … forms. It is **private and never emitted**, and `_restructure` / `paste` / `apply_script` reset `_last_edit` straight after recording. | A new public signal `edited(str kind)` is emitted once after every change (§3.3). The recorder and the live session both use it. |
| "Transforms have no UI yet, so transform edits can only come from scripts" | Out of date. The **Transform Editor** (`F4`) and the Formula Editor both edit transforms through `FractalDocument` (`set_affine`, `set_xform_fields`, `set_variation`, `set_param`, `set_chaos`, `add_xform`, `delete_xform`, `set_final_enabled`, `area_weights`, `replace_flame_parameters`), announced by `xform_changed` / `transforms_changed`. | Transform edits are recordable now and are in scope (§7). |
| `CodeEditor.insert_snippet` for recorded lines | ✔ It exists, but it calls `setFocus()` and re-indents to the cursor's line. | The recorder needs an insertion that does **not** take the focus (the user is dragging in another window). It uses its own `QTextCursor` (§8.3). |

### 1.2 Defects found while reading, which these features would hit

1. **Flame → Script drops the pre-affine and the tone curves** (verified). I built a flame with a non-identity
   `pre` affine and a custom overall curve, ran `flame_to_script` and executed the result: the rebuilt flame has an
   identity `pre` and default curves. The scripting API has no way to set either (`Transform` has `coefs` and `post`
   but no `pre`; `coloring` has `reset_curves()` but no setter). The existing test does not catch this because it only
   compares names, counts, palettes, coefficients and weights. The recorder needs both (the Transform Editor edits
   pre-affines, and the Image tab edits curves), so this is fixed first (§3.1–3.2).
2. **3D angles lose precision in Flame → Script.** Angles are printed in degrees with 9 significant digits, so
   `pitch = 0.3 rad` comes back as `0.3000000008`. This is harmless for the picture. The shared number formatting in
   §3.5 fixes it, and the round-trip tests use a stated tolerance.
3. **A stale run token can swallow an undo step.** `FractalDocument._script_run` is only ever set by `apply_script`.
   Suppose another edit happens between a script's intermediate `update()` and its final result (the user drags the
   camera while a `sleep()` loop runs). The final `apply_script` then sees the same token, records nothing, and
   overwrites the camera edit, which has no undo step of its own before the script's state. Live re-runs would make
   this much more likely. Fix: `_record()` clears `_script_run` for any kind other than `script` (§3.4).
4. **A script re-run every 150 ms triggers a full-resolution render.** `apply_script` emits `flame_restored`, and the
   viewport answers that with `_render_full()`, not the interactive half-resolution pass that camera drags get. A live
   tick needs the interactive path (§3.4).
5. **Runs are unseeded.** `ScriptRunner.run` passes no seed, so every run of `random_rotate` draws new angles. Live
   re-runs must reuse one seed, or the fractal would jump on every tick even when the control has not moved.

### 1.3 Facts the design relies on (checked in the code)

* `ScriptContext(flame, host, active, seed)` builds a fresh namespace per run and copies the flame. The runner executes
  on a worker thread with a stop trace. `ScriptResult` carries the flame, `ok`, `stopped`, `output_lines` and the error
  with its line.
* The 12 built-in templates that prompt with `input_number` / `input_text` / `confirm` are: `random_rotate`,
  `gradient_shift`, `symmetry`, `scale_all`, `jitter`, `spiral`, `xaos_random`, `rainbow_gradient`, `camera_3d_tilt`,
  `gradient_from_library`, `save_variants` and `random_explorer`.
* The drawer persists its current tab **by index** (`script/drawer_tab`). Appending the fifth tab keeps every saved index
  valid. Inserting it anywhere else would shift them.
* `FractalDocument` signals are emitted synchronously on the GUI thread, so a re-entrancy guard flag around our own
  `apply_script` call reliably tells our own edits apart from anyone else's.
* `GradientLink.apply_gradient` → `FractalDocument.set_gradient(gradient)` → `palette_changed`. The Gradient Library's
  current `Gradient` (stops) is available as `gradient_library.document.gradient`. The document only stores the
  256-entry palette.
* The Gradient Library's hue / saturation / luminance sliders adjust the **stops** and then resample.
  `gradient.adjust()` in the API adjusts the **256 palette entries**, so the two give slightly different palettes.
  A recorded `gradient.adjust(hue=30)` would therefore *not* reproduce a slider move exactly (this matters in §7.4).
* The image-size dropdown (`set_image_size`) and the preview options (passes, quality, oversample, filter) are viewer
  and application settings, not flame edits. They are not recorded.

---

## 2. Decisions (all accepted as recommended)

| # | Question | Recommendation |
|---|---|---|
| D1 | What happens to a live session when the fractal is changed by something else (an Inspector slider, Undo, another fractal chosen)? | **End it, as Blender's "Adjust Last Operation" panel does.** The controls stay visible with their values but are disabled, with a note: *"The fractal changed after the run — press Run to apply the script again with these values."* Re-running from the old snapshot would silently throw away the user's later edit. Re-running on top of the current flame would apply the script twice. |
| D2 | Run while a session is live: apply again to the current fractal, or re-run from the snapshot? | **Keep Run exactly as it is today.** Run always acts on the fractal as it is now, and it uses the controls' current values. The controls are the way to "re-run from before". |
| D3 | Recorded numbers: readable or bit-exact? | **Readable but faithful.** The shortest form that round-trips to 9 significant digits (`3.5`, not `3.5000000000`). Camera centres get as many decimals as the current zoom needs for sub-pixel accuracy. Every recorded block is verified by executing it (§7.5), so "readable" can never mean "wrong". |
| D4 | Recording gradient edits: absolute (`gradient.set_stops([...])`) or relative (`gradient.adjust(hue=30)`)? | **Absolute in version 1**, with the exactly detectable relative forms `gradient.rotate(n)`, `gradient.reverse()` and `gradient.invert()` (§7.4). A relative "changes" mode is suggestion S3 in §11. |
| D5 | Keep recording while the Script Editor is hidden? | **Yes**, with a red **● Recording** indicator in the main window's status bar (click it to stop). The editor is usually hidden while the user works in the main window. |
| D6 | Convert the prompting built-in templates to `param()`? | **Yes, 10 of the 12** (§6). `random_explorer` stays interactive (it is a Yes / No loop by nature). `save_variants` gets parameters but is never live, because it writes files. |
| D7 | Should parameter values persist across application restarts? | **Yes, with the script draft** (`script/parameters`). They are cleared when another script is loaded. |
| D8 | Julia mutation: turn the random power / distance into parameters? | **Yes**: `Power` 0–12 and `Distance` −3…3, where 0 means random (today's behaviour), so the template still explores by default. |
| D9 | Should a recording started on the untouched default script start a new script? | **Yes**: it becomes `# @name Recorded script` with a header line. Otherwise statements go in at the cursor. |

---

## 3. Phase 0 — Prerequisites (no new features yet; every existing test must still pass)

### 3.1 The pre-affine in the scripting API
* `Transform.pre` → `Affine6` (same pattern as `post`), with a setter. `t.reset_pre()`. `pre` is added to the keyword set
  accepted by `add_transform` / `insert_transform` / `set_final_transform` (`ScriptContext._new_xform`) and to
  `Transform.to_dict()`.
* `docs.py`: a `pre` member on the `Transform` type, and `XFORM_FIELDS` updated. `test_documentation_matches_the_real_api`
  keeps the two honest.

### 3.2 Tone curves in the scripting API
* `coloring.set_curve(channel, points)` (uses `Curves.set_points`, channel options `D.CURVE_CHANNELS`) and
  `coloring.curve(channel)` → the list of points. `reset_curves()` is unchanged.
* Documented in `docs.py`, with the option list for `channel` so completion offers the channel names.

### 3.3 `FractalDocument.edited(str)`: one announcement per change, with its kind
* New signal `edited = Signal(str)`, emitted **last** (after the specific signal) by every method that changes the
  current flame. Kinds are today's `_record` kinds, plus `undo`, `redo` and `load` (for `replace`, which emits
  `flame_replaced`).
* Implementation: a private `_announce(kind)` called at the end of each mutator. **Existing signals, their order and
  their arguments are untouched**; only a new signal is added.
* `last_edit_kind` read-only property (kept in a separate `_last_kind` field, because `_last_edit` is reset for
  coalescing).
* Test: table-driven over every public mutator (`set_view`, `pan`, `pan_units`, `set_camera_3d`, `set_coloring`,
  `set_curve`, `reset_curves`, `revert_*`, `set_gradient`, `set_affine`, `set_xform_fields`, `set_variation`,
  `clear_variations`, `set_param`, `set_chaos`, `set_all_chaos`, `add_xform`, `duplicate_xform`, `add_linked_xform`,
  `delete_xform`, `set_final_enabled`, `area_weights`, `replace_flame_parameters`, `paste`, `apply_script`, `undo`,
  `redo`, `replace`). Each emits `edited` exactly once, with the expected kind, after its specific signal. No-op calls
  (no flame, nothing changed) emit nothing.

### 3.4 Two small document and viewport fixes
* `_record(kind)`: when `kind != "script"`, clear `_script_run`, so a later `apply_script` with an old token records
  its own step (defect 1.2.3). Test: a script's intermediate `update()`, then a camera edit, then the final result gives
  **two** undo steps, and undoing them restores each state in order.
* `apply_script(flame, run, interactive=False)`. With `interactive=True`, the document sets a read-only
  `live_edit` flag while it emits, and `FractalViewport._on_flame_restored` uses `_render_interactive()` (half
  resolution, then full resolution after the existing 250 ms settle) instead of `_render_full()`. The default path is
  byte-for-byte today's.

### 3.5 Shared code generation (`scripting/codegen.py`)
* Moved out of `generate.py` (no behaviour change): `num()`, `affine()`, `mapping()`, `xform_lines()` (the
  `add_transform(...)` / `set_final_transform(...)` block), `palette_lines()`, `stops_call()`. `generate.flame_to_script`
  keeps its signature and output, except for two additions: a non-identity `pre` becomes `tN.pre.coefs = (…)`, and
  non-default curves become `coloring.set_curve('overall', [...])`.
* `num(v)`: the shortest of `repr(v)` and `f"{v:.9g}"` that reads back within 1e-9 relative, with integers kept as
  integers. `coord(v, pixel)`: enough decimals for a quarter of a pixel at the current zoom, at least 4.
* Test `test_flame_to_script_rebuilds_the_flame` is strengthened to compare **every field** with
  `flames_equivalent(a, b, tol)` (new helper in `scripting/codegen.py`). It compares `to_dict()` within tolerance,
  treats a missing parameter as its formula's default, and ignores `name` / `unsupported`. It runs on the three sample
  flames plus a synthesised flame with pre / post affines, curves, a 3D camera, opacity, `var_color`, names, xaos and a
  final transform.

### 3.6 Make room in the window (mechanical moves, no behaviour change)
* `ui/script_editor_actions.py`: the action / menu / toolbar construction (`_build_actions`, about 110 lines),
  following `editor_actions.py`. The window keeps `self.actionRun` etc. as attributes, so tests and the main window
  are unaffected.
* `ui/script_output.py`: `OutputPanel` (re-exported from `script_editor_window` because `__all__` lists it).
* Result: the window goes from 800 lines to about 620, before the new features add their wiring (about 60 lines).

---

## 4. Phase 1 — Live parameters: the Qt-free core (`scripting/`)

### 4.1 `scripting/parameters.py` (new)
```python
@dataclass(frozen=True)
class ParamSpec:
    name: str                      # the label, and the key of the value
    kind: str                      # "float" | "int" | "bool" | "choice" | "text"
    default: Any
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    choices: tuple = ()
    decimals: int = 2
    help: str = ""
    line: int | None = None        # the declaring line (Parameters tab → "Go to declaration"; baking defaults)
```
* **Kind inference** (the call must be unambiguous, or it is a `ScriptError` that names the line):
  * a `bool` default → `bool` (bounds and choices are not allowed);
  * `choices=` given → `choice` (non-empty; the default must be one of them; items are strings or numbers and are
    returned as given);
  * an `int` default with an integer or missing `step` and integer or missing bounds → `int`;
  * a number otherwise → `float`;
  * a `str` default without choices → `text`.
* **Slider or spin box**: a slider appears only when both `min` and `max` are given. An unbounded number gets a spin box.
* `decimals`: from `step` (0.05 → 2) or from the bounds' span (2 for a span ≥ 1, 3 below). It can be overridden with
  `decimals=`.
* `coerce(spec, value) -> value`: a stored value of the wrong type falls back to the default; numbers are clamped into
  `[min, max]`; ints are rounded; an unknown choice falls back to the default. So a value saved for an older version of
  the script can never crash the new one.
* `live_blockers(code) -> list[Blocker]` (static, AST): imports outside a safe list (`math`, `cmath`, `colorsys`,
  `random`, `itertools`, `functools`, `statistics`, `operator`, `string`, `re`, `fractions`, `decimal`, `collections`),
  and calls to `open`, `exec`, `eval`, `compile`, `__import__`, `input` and `breakpoint`, each with its line. The API's
  own side effects are handled at run time instead (§4.3), because they are often conditional (`if export:`).
* `bake_defaults(code, values) -> (new_code, skipped)`: rewrites the default argument of each
  `param('<name>', <default>, …)` call (the second positional argument or `default=`) when it is a literal (a constant,
  a negated constant, or a tuple or list of constants). The rewrite replaces only that literal's source segment (AST
  `col_offset` / `end_col_offset`), so formatting and comments are untouched. Calls with a computed default are
  reported in `skipped`.

### 4.2 `param()` in `ScriptContext`
```python
def param(self, name, default, min=None, max=None, step=None, choices=None, decimals=None, help=""):
    """A tunable input: returns the value set in the Parameters tab (or given to run_script), else `default`."""
```
* The value is `coerce(spec, self.parameters.get(name, default))`. The spec is recorded in `self.declarations` (an
  ordered dict, in first-call order) and the value in `self.values`.
* Calling it again with the same name and the same spec returns the same value (loops and helper functions are fine).
  The same name with a *different* spec is a `ScriptError` naming both lines.
* More than `config.SCRIPT_MAX_PARAMETERS` (40) distinct names is a `ScriptError`, which guards against
  `param(f'x{i}')` in a loop.
* The name must be a non-empty string. `param` is added to `FUNCTION_NAMES`. No Apophysis alias.

### 4.3 Side effects and live mode
* `ScriptContext.effects: set[str]` is filled by the API calls that reach outside the flame: `prompt` (`input_text`,
  `input_number`, `confirm`), `message`, `update`, `sleep`, `write` (`save_flame`) and `read` (`load_flame`,
  `gradient.load`; allowed live).
* `ScriptContext(live=True)`: each of `prompt`, `message`, `update`, `sleep` and `write` raises
  **`LiveRefused(ScriptStopped)`** *before* doing anything, with a reason such as *"save_flame() writes files, so it does
  not run while controls update live"*. It derives from `ScriptStopped` (a `BaseException`), so `except Exception:` in a
  script cannot swallow it. The effect is never performed.

### 4.4 `run_script` and `ScriptResult`
* `run_script(code, flame, host=None, stop_event=None, active=0, seed=None, parameters=None, live=False)`. The new
  keywords come last and have defaults, so every current call is unchanged.
* New `ScriptResult` fields, all defaulted: `declarations: tuple[ParamSpec, ...]`, `values: dict`,
  `effects: frozenset[str]`, `refused: str` (the `LiveRefused` reason) and `seed: int | None`.
* A `LiveRefused` run comes back with `ok=True, stopped=True, refused=<reason>`. The live coordinator never applies its
  flame.

### 4.5 Optional, small: gradient presets
`list_gradient_presets()` → the names in `formulas/authoring.GRADIENT_PRESETS`; `gradient.preset(name)` applies one
(`ScriptError` listing the names if unknown). This makes the proposal's `choices=list_gradient_presets()` example work.
*(Moving `GRADIENT_PRESETS` to `model/` so that `scripting` does not import from `formulas.authoring` is the cleaner
home; a one-line re-export keeps the Formula Editor's import working.)*

### 4.6 Documentation database
* `docs.GLOBALS["param"]` with every argument (`min`, `max`, `step`, `choices`, `decimals`, `help` marked optional, so
  completion offers the keywords inside the call) and an example. New category **Parameters** in `CATEGORIES`.
  Entries for `list_gradient_presets` and `gradient.preset` if §4.5 is accepted.
* GUIDE: a new section, *"Parameters: scripts as live tools"*. It covers declaring, the kinds, live re-runs and the
  seed, what turns live updates off and why, *Set as defaults*, and converting an `input_number` script.

### 4.7 Tests (`tests/test_script_parameters.py`, Qt-free)
* Kind inference and validation errors for every rule, with line numbers. Coercion (type mismatch, clamping, int
  rounding, unknown choice). Duplicate declarations. The 40-parameter cap.
* `run_script` without `parameters` returns the defaults; with `parameters` it uses the coerced values.
  `result.declarations` is in order with the right `line`.
* **Determinism**: the same seed and parameters give identical flames; different parameters give different flames, and
  `random()` draws stay the same.
* `live=True` refuses each blocked effect before performing it (`save_flame` writes no file; `message` never reaches
  the host). `except Exception` in the script does not catch `LiveRefused`. `read` is allowed.
* `live_blockers` flags `import os` / `open(` with lines and passes the safe imports.
* `bake_defaults`: positional and keyword defaults, negative numbers, strings with quotes, a tuple default, comments on
  the same line preserved, computed defaults reported as skipped, and the code still compiles afterwards.

---

## 5. Phase 2 — Live parameters: the window

### 5.1 Modules
* `ui/script_parameters_tab.py` → **`ParametersTab(QWidget)`**, a pure view. `set_specs(specs, values)` rebuilds the rows
  only when the list of specs actually changed; a row whose spec is unchanged keeps its widget, so a drag in progress
  is never interrupted. It also has `set_status(state, reason)`, `set_seed(seed)` and `set_code_changed(bool)`.
  Signals: `value_changed(str name, object value, bool final)`, `reset_requested(str | None)`, `bake_requested()`,
  `reseed_requested()`, `keep_seed_toggled(bool)`, `goto_line(int)`, `insert_example()`.
* `ui/script_live.py` → **`LiveParameters`**, a helper of the window (it holds the window as `w`, like
  `ExploreCoordinator`). It owns the `LIVE_PARAMS` machine, the session (frozen code, snapshot, undo token, seed,
  specs, touched values, static blockers, slow flag), the debounce timer and the re-entrancy guard.

### 5.2 The machines
**`SCRIPT_RUN`** gains two states (its existing transitions are unchanged):

| From | Event | To | Meaning |
|---|---|---|---|
| IDLE | `rerun` | **RERUNNING** | a live re-run is on the worker |
| RERUNNING | `finished` | IDLE | |
| RERUNNING | `stop` | STOPPING | Stop was pressed during a slow re-run |
| RERUNNING | `run` | **SUPERSEDED** | Run was pressed during a re-run: the re-run is being stopped, and Run follows it |
| SUPERSEDED | `finished` | IDLE | the window then starts the requested Run at once |
| SUPERSEDED | `stop` | STOPPING | Stop cancels the pending Run too |

`WAITING` cannot follow `RERUNNING`, because `update()` is refused while live.

**`LIVE_PARAMS`** (new, in `machines/specs.py` and `ALL`):

| State | Meaning | UI |
|---|---|---|
| OFF | the last run declared no parameters (or another script was loaded) | empty state with an example |
| READY | controls are live; nothing pending | chip **Live** |
| PENDING | a value changed; the 150 ms debounce is running | **Live** |
| RERUNNING | a re-run is on the worker | **Updating…** (only shown after 300 ms, to avoid flicker) |
| QUEUED | a value changed during a re-run; run again when it ends (latest value wins) | **Updating…** |
| INERT | parameters exist but cannot update live (a blocked effect, a static blocker, or the re-run refused) | the reason in the `warning` role; the controls still set the values for the next Run |
| DETACHED | the fractal was changed elsewhere after the run (D1) | the controls are disabled; *"press Run to apply again with these values"* |

Events: `declared_live`, `declared_inert`, `declared_none` (from any state, after a full run), `changed`, `settle`,
`finished`, `refused` (→ INERT), `detach` (READY, PENDING, RERUNNING or QUEUED → DETACHED) and `unload` (→ OFF). The
machine tests check that every state is reachable and has a way out.

### 5.3 Flow
1. **Run** (full run, unchanged for scripts without `param()`). The window draws a seed (`random.getrandbits(32)`, or
   the kept seed if *Keep seed* is on) and passes `parameters =` the **touched** values only (those the user changed
   from their default). Untouched parameters therefore pick up a default edited in the code. The rest is as today:
   `_snapshot`, the `_run` token, *▶ Running…*.
2. **Result of a full run**: applied as today. If it declared parameters, `LiveParameters.on_run_finished(result)`
   stores the frozen `code`, the `snapshot`, the `token`, the `seed` and the `specs`. It fires `declared_live` (no
   blocked effects and no static blockers), or `declared_inert` with the reason. The tab is filled. The first time a
   script declares parameters, the drawer switches to the Parameters tab.
3. **A control moves**: the value is stored as touched and `changed` fires. The debounce (`config.SCRIPT_LIVE_DEBOUNCE_MS
   = 150`) restarts. A slider release or a committed spin box edit settles at once.
4. **Settle**: `window.start_run(code=session.code, flame=session.snapshot, seed=session.seed, parameters=values,
   live=True, rerun=True)`. `SCRIPT_RUN` fires `rerun`.
5. **Re-run finished**:
   * `ok`, not refused, state not DETACHED: `document.apply_script(result.flame, session.token, interactive=True)`
     inside the guard, and the output's live section is replaced (§5.5). Then `finished`, and if QUEUED, another
     settle.
   * `refused`: nothing is applied, the state becomes INERT with the reason, and the fractal keeps the last good result.
   * **error**: nothing is applied. The fractal keeps the last good result, the error line is marked and shown in the
     live section, and the tab shows *"Angle = 190 → ZeroDivisionError (line 7); the fractal shows the last good
     values"*. The session stays live, so moving the control back recovers.
6. **Any other edit** (`document.edited` outside the guard; kinds `view`, `coloring:*`, `palette`, `undo`, `load`, …)
   fires `detach`. A re-run in flight is stopped and its late result ignored. Values are kept.
7. **Run during a re-run** → SUPERSEDED. The re-run is stopped, and Run starts as soon as its result is discarded.
8. **Loading another script** (New, Open, template, Flame → Script) fires `unload`, and the values are cleared.
9. **Slow scripts**: if a re-run takes longer than `config.SCRIPT_LIVE_SLOW_MS` (1500 ms), the session switches to
   *apply on release*. Drags no longer re-run; releases do, and the chip says so.

### 5.4 Undo, modified state, and other windows (what the user sees elsewhere)
* The first Run records one `script` undo step. Every re-run reuses the token, so **one Ctrl+Z returns to the fractal
  before the run** however many ticks there were, and Ctrl+Shift+Z returns the last tick. Undo detaches the session
  (D1).
* *Revert flame* uses the same `_snapshot`. It detaches the session as well.
* Each applied tick is an ordinary `flame_restored`. The Gradient Library follows the palette **without prompting**
  (the Q1 rule of the last plan is unchanged). The Mutate & Breed window regenerates once the ticks pause, as it does
  after any edit. The Transform Editor and the Inspector refresh. The viewport renders at interactive resolution
  (§3.4).
* While a session is live, the window's `running` is True during re-runs only. `closeEvent` asks *"A script is
  running…"* only in RUNNING / WAITING. A re-run is simply stopped.

### 5.5 The Parameters tab and the output panel
* **Layout, top to bottom**:
  1. a status chip, as in §5.2;
  2. a banner when the editor's text differs from the code that ran: *"The script has changed since it ran: the
     controls drive the version that ran. Run it to pick up your changes."*;
  3. the rows;
  4. a seed row: **Seed 1234567**, a die button (*New seed*, which re-runs) and a **Keep seed on Run** check box;
  5. a footer: **Reset all** and **Set as defaults in script**.
* **Rows**:
  * `float` and `int` use `FloatRow` (with 0 decimals for ints), or a spin box alone when unbounded;
  * `choice` uses a `QComboBox`, `bool` a `QCheckBox`, and `text` a `QLineEdit` that commits on Enter or focus-out.
  * The label's tooltip is `help`.
  * Right-click on a row: *Reset to default*, *Copy value*, *Go to declaration* (jumps to `spec.line`).
  * A touched row's label is shown in the theme's `text` role; untouched rows use `dim_text`. This does not rely on
    colour alone, because touched labels also get a trailing "•".
* **Empty state (OFF)**: *"This script has no parameters. Add* `angle = param('Angle', 30, min=-180, max=180)` *and run it
  — its controls appear here."*, plus an **Insert example** button.
* **Set as defaults in script**: `bake_defaults` is applied to the editor text as one edit block (so it can be undone
  in the editor). Baked values stop being "touched". The session's frozen code is updated to the baked text, so no
  "changed since it ran" banner appears. Skipped (computed) defaults are listed in the status bar.
* **Save as Template** with touched values asks *"Save with the current parameter values as the defaults?"* [Save with
  values] [Save as written] [Cancel].
* **Output during live**: re-runs do not add *▶ Running* / *✔ Finished* notes. `OutputPanel.begin_live_section()` marks
  where the live output starts. After each re-run, `replace_live_section()` swaps that part for the re-run's buffered
  `print` output and one summary line, *"↻ Live: Angle = 20 · Copies = 5 — 14 ms"*. Errors stay clickable. The next
  full Run closes the section.
* **Info tab**: the *Interaction* row adds *"3 parameters (live)"* or *"(not live: saves files)"*.
* **Persistence** (D7): touched values go to `script/parameters` (JSON) with the draft, and are restored with it.

### 5.6 Tests (`tests/test_scripting.py`, window part, CPU engine)
1. Running a `param()` script fills the tab with the right widgets in order and switches the drawer to it (first time
   only).
2. Moving a control gives a result equal to `run_script(code, snapshot, seed=…, parameters={…}).flame`. Ten moves in a
   row add **exactly one** undo step. Undo returns the pre-run fractal and detaches.
3. Latest value wins: several changes during a slow re-run give exactly one further re-run, with the last value.
4. An external edit (`set_coloring`) while live → DETACHED, and a control change no longer alters the flame. An
   external edit *during* a re-run discards its late result.
5. Run during a re-run → SUPERSEDED → the Run happens once, with the current values.
6. An error in a re-run keeps the last good flame and marks the line; moving back recovers.
7. `save_flame` behind a `bool` parameter → INERT on toggle, no file written, and the next Run uses the values.
   `import os` → INERT from the start.
8. *Set as defaults* rewrites the code (editor undo restores it). *Save as Template* with touched values offers to bake.
9. Scripts **without** `param()`: the output notes, undo steps and tab are unchanged (a regression guard that reuses
   `test_running_a_script_edits_the_fractal_as_one_undo_step_and_rerenders`).
10. `test_machines.py` picks up `LIVE_PARAMS` and the new `SCRIPT_RUN` states automatically (completeness, reachability,
    no dead ends, document current).

---

## 6. Phase 3 — Templates and documentation for parameters

Converted templates (each keeps its name, category and description, and still runs headless with the defaults):

| Template | Parameters (default, range) | Live? |
|---|---|---|
| Random rotate all transforms | `Maximum rotation` 360 (0–360) | ✔ (seeded, so the angles hold still while only the maximum changes) |
| Warm / cool shift | `Hue` 20 (−180–180), `Saturation` 10 (−100–100) | ✔ |
| Make rotational symmetry | `Order` 3 (2–12, int) | ✔ |
| Scale all transforms | `Factor` 0.9 (0.1–2) | ✔ |
| Mutate (jitter) coefficients | `Amount` 0.05 (0–0.5) | ✔ |
| Spiral | `Rotation per step` 25 (−90–90) | ✔ |
| Random xaos | `Link probability` 0.6 (0–1) | ✔ |
| Rainbow gradient | `Saturation` 0.8 (0–1) | ✔ |
| 3D tilt | `Pitch` 35 (−90–90), `Yaw` 15 (−180–180), `Perspective` 0.15 (0–1) | ✔ |
| Julia mutation (D8) | `Power` 0 (0–12, int, 0 = random), `Distance` 0 (−3–3, 0 = random) | ✔ |
| Gradient from a file | `File` (text), `Entry` 0 (int) | ✔ (reading is allowed) |
| Save rotated variants to a file | `File` (text), `Variants` 4 (1–50, int) | ✘ INERT (writes files): the form feeds Run |

`random_explorer` keeps `confirm()`. `test_builtin_templates_have_metadata_and_all_run` passes `parameters=` for the two
file templates instead of answering prompts (the answer-by-prompt mapping is kept for `random_explorer`). A new built-in
template, **"Live kaleidoscope"** (Transforms), shows off the feature with order, twist and scale. The README count goes
from 35 to 36.

Documentation: README (Script Editor: the Parameters tab, live re-runs, seeds, what stops live mode), `docs/scripting.md`
regenerated, and the GUIDE section from §4.6.

---

## 7. Phase 4 — The diff generator (`scripting/diff.py`, Qt-free)

### 7.1 Contract
```python
def flame_diff(before: Flame, after: Flame, gradient: Gradient | None = None) -> list[str]:
    """API statements that turn `before` into `after` (empty when nothing differs)."""
```
* The invariant, tested over thousands of pairs:
  `flames_equivalent(run_script("\n".join(flame_diff(b, a)), b).flame, a)`.
* The `kind` argument of the proposal is **not needed for correctness**. The generator compares everything (a flame is
  small: 256 colours, a few transforms), so a mis-named kind can never drop a change. Kinds are used by the recorder
  for coalescing only.
* Not recorded: `name` (a rename is not an edit a template should repeat), `unsupported` and `source_version`.

### 7.2 Sections, in this order (later statements rely on the structure settled by earlier ones)
1. **Structure.** Compare the transform counts and whether a final transform exists:
   * Same count → nothing here.
   * Exactly one transform **appended** (`after[:-1]` ≈ `before`) → the `add_transform(...)` block from
     `codegen.xform_lines`.
   * Exactly one **removed** at `k` → `remove_transform(k)`.
   * The final transform switched on or off → `set_final_transform(...)` block / `remove_final_transform()`.
   * Anything else (reordering, several at once, a paste or an adopted mutant that reshapes everything) →
     `clear_transforms()` plus the full rebuild (the same lines Flame → Script writes), commented
     `# transforms rebuilt (the structure changed)`.
2. **Per transform**, after **simulating** the structure statements on a copy of `before` (so index-based statements are
   computed against what the script will really see, including the API's side effects such as xaos columns appended
   with 1.0):
   * `weight`, `color`, `color_speed`, `opacity`, `var_color`, `name` → `transforms[i].weight = 0.5`;
   * affines → `transforms[i].coefs = (…)`, `.pre.coefs = (…)`, `.post.coefs = (…)`;
   * variations → `transforms[i].variations['julian'] = 1.0`, or `del transforms[i].variations['x']`;
   * parameters → `transforms[i].params['julian_power'] = 3.0`, or `del …`;
   * the final transform uses `final_transform().…`.
   * With three or more statements for one transform it binds `t3 = transforms[2]` first (the same names as Flame →
     Script).
   * A variation that is not loaded here is skipped with a comment (the API would reject its name).
3. **Xaos**: one changed entry → `xaos.set(i, j, w)`; a changed row → `transforms[i].xaos = [...]`; a row back to all
   ones → `transforms[i].xaos = None`.
4. **Camera**:
   * `camera.set_size(w, h)` if the size changed;
   * `camera.center = (x, y)`, with pixel-accurate decimals (D3);
   * `camera.scale`, `camera.zoom`, `camera.rotate`;
   * 3D: `camera.pitch`, `yaw`, `perspective`, `zpos`, `dof` in the API's units (degrees for angles), and `pitch_y`
     only if it changed (see §0).
5. **Colouring**: `coloring.brightness / gamma / gamma_threshold / vibrancy / contrast`, `coloring.background = '#rrggbb'`,
   and per changed curve `coloring.set_curve(channel, [...])` (or `coloring.reset_curves(channel)` when back to the
   identity).
6. **Flame**: `flame.oversample`, `flame.filter_radius` (changed only by paste, adoption or scripts).
7. **Palette**: see §7.4.

### 7.3 Clamps and API semantics (why the equivalence check is tolerant in two places)
* Adding a variation through the API fills its parameter defaults (`_fill_defaults`). The Transform Editor does not.
  `flames_equivalent` treats a missing parameter as its default, so the two are the same fractal.
* The API clamps a few values (`color` and `opacity` to 0..1, `gamma ≥ 0.01`, `vibrancy` to 0..1). A file can hold
  values outside those ranges, and an edit cannot reproduce them exactly. In that case the verification in §7.5 falls
  back to a statement that sets the value through the raw object instead (`flame.coloring.vibrancy = 1.5`), which is
  unclamped. There is a test with an out-of-range source.

### 7.4 The palette ladder (most readable form that is exact)
1. `after.palette` is `before.palette` rotated by *n* → `gradient.rotate(n)`; reversed → `gradient.reverse()`;
   inverted → `gradient.invert()`.
2. A **gradient hint** is given (the Gradient Library's current stops) and `hint.sample(256) == after.palette` →
   `gradient.set_stops([(0.0, '#05070f'), (0.4, '#0f7d4a'), …])`. These are the stops the user actually sees. The
   formatted positions are re-sampled to confirm that the result is exact.
3. The simplified stops (the API's `gradient.stops`) re-sample exactly → `gradient.set_stops([...])`.
4. Otherwise `gradient.colors = [...]`, all 256 entries, 8 per line (exact, and the same layout as Flame → Script).

Relative hue / saturation recording (`gradient.adjust(hue=30)`) is deliberately not generated, because it does not
reproduce the library's stop-based result (§1.3). See suggestion S3.

### 7.5 Generate, verify, fall back
`flame_diff` executes its own output on a copy of `before` (`run_script`, a few milliseconds) and checks
`flames_equivalent` section by section. Any section that does not reproduce `after` is replaced by its exact fallback
(the raw-object assignment, the full transform rebuild, or `gradient.colors`). The fallback is logged at debug level so
tests can assert it is rare. A recording is therefore correct by construction, and "readable" is never at the expense of
"right".

### 7.6 Tests (`tests/test_script_diff.py`, Qt-free)
* **One test per document mutator** (the same table as §3.3): the pair (before, after the mutator) gives the expected
  statement text, and the invariant holds.
* **Fuzzing with our own engines**: 3 sample flames × 40 seeds of `mutation.mutate` (every mutation kind switched on),
  plus `breeding.breed` in all four modes (structural changes). The invariant holds for all of them. The generated
  line count is small for single-kind mutations (for example, one `coloring` change gives one line).
* Palette ladder: rotate, reverse, invert, a hint that matches, a hint that does not, simplified stops, and arbitrary
  colours.
* Numbers: `3.5` stays `3.5`; a deep zoom keeps centre accuracy below a pixel; angles come back within 1e-9 rad.
* Out-of-range source values take the raw fallback and still satisfy the invariant.
* `flame_to_script` and `flame_diff(empty, flame)` agree on the rebuilt flame (shared `codegen`).

---

## 8. Phase 5 — The recorder (`ui/script_recorder.py`)

### 8.1 What is recorded (every path was traced to its `FractalDocument` call)

| User action | Document call → kind | Recorded as (example) |
|---|---|---|
| Viewport Ctrl+drag / Ctrl+wheel / double-click | `set_view` → `view` | `camera.center = (0.1432, -0.0210)` · `camera.zoom = 1.25` |
| Image tab: zoom, centre, rotation, pan arrows, ↻ revert | `set_view` / `pan_units` → `view` | `camera.rotate = 30.0` |
| Image tab: 3D camera | `set_camera_3d` → `camera3d` | `camera.pitch = 35.0` |
| Image tab: colouring, background | `set_coloring` → `coloring:<field>` | `coloring.gamma = 3.5` |
| Image tab: curves, reset | `set_curve` / `reset_curves` → `curve:<ch>` / `curves-reset` | `coloring.set_curve('red', [(0.0, 0.0), (0.5, 0.62), (1.0, 1.0)])` |
| Gradient Library: nodes, sliders, operations, choosing a gradient | `GradientLink.apply_gradient` → `set_gradient` → `palette` | `gradient.set_stops([...])` / `gradient.reverse()` |
| Formula Editor gradient presets | `set_gradient` → `palette` | as above |
| Transform Editor: triangles (pre / normal / post) | `set_affine` → `affine:<which>:<i>` (sticky drags) | `transforms[1].coefs = (…)` |
| Transform Editor: weight, colour, speed, opacity, name | `set_xform_fields` → `fields:…` | `transforms[0].weight = 0.7` |
| Transform Editor: variations, parameters, Clear | `set_variation` / `set_param` / `clear_variations` | `transforms[0].variations['julian'] = 1.0` |
| Transform Editor: xaos, set / clear all | `set_chaos` / `set_all_chaos` | `xaos.set(0, 2, 0.0)` |
| Transform Editor: add / duplicate / linked / delete / final / auto weights / new flame / reset all | `_restructure`, `area_weights`, `replace_flame_parameters` | structure statements (§7.2) |
| Paste Parameters; adopting a mutant or child | `paste` → `paste`; `replace_flame_parameters` → `mutate` / `breed` | the full diff, usually the structural rebuild |
| Undo / Redo in any window | `undo` / `redo` | the diff, or the undo-aware removal (§8.4) |
| Choosing another fractal | `replace` → `load` | a comment: `# (switched to 'name' — not recorded)`; the baseline moves on |
| A script's result (any run, live ticks included) | `apply_script` → `script` | nothing; the baseline moves on |
| Image size dropdown; preview passes / quality / oversample / filter | not flame edits | not recorded |

### 8.2 The recorder object
`ScriptRecorder(document, editor, gradient_hint, parent)`. It is a `QObject`, and `gradient_hint` is a callable that
returns the Gradient Library's current `Gradient` or `None`. The main window passes it when it creates the Script Editor.
* `start()`: the baseline is `document.flame.copy()`. Start is disabled without a flame. D9 applies when the editor
  holds the untouched default script. `stop()` flushes the pending block. `recording` is a property, and
  `recording_changed(bool)` is a signal.
* It listens to `document.edited(kind)` only.
* There is **no state machine**, because this is a two-state toggle. Coalescing is handled by one "open block"
  reference (§8.3). The `docs/state-machines.md` inventory gets a line explaining why.

### 8.3 Blocks, coalescing, and the editor
* A **block** is the text inserted for one run of same-kind edits. It is tracked by a `QTextCursor` selection, which Qt
  keeps up to date as text is inserted elsewhere. Each block keeps its **base** (the flame before the first edit of the
  run).
* On `edited(kind)`:
  1. `script` → the baseline becomes the current flame; the open block is closed.
  2. `load` → the open block is closed; the comment line is inserted; the baseline moves on.
  3. Same kind as the open block, and the block is still valid → the block is marked dirty. A refresh timer
     (`config.SCRIPT_RECORD_REFRESH_MS = 100`) rewrites the block's text as `flame_diff(block.base, now)`. A 60 Hz drag
     therefore rewrites the text at most 10 times a second, and the final text is one statement.
  4. Otherwise → the open block is flushed and closed, and a new block is started with base = baseline.
  5. The baseline becomes a copy of the current flame.
* **Validity**: a block stays open only while the user has not typed in the editor and has not moved the cursor away
  from the block's end. This is watched through `QTextDocument.contentsChange` and `cursorPositionChanged`, with the
  recorder's own edits guarded. This matches the document's coalescing: a drag, or a slider swept back and forth, is one
  step.
* **An empty diff** (the value went back to where it was) removes the block's text.
* **Insertion**:
  * at the cursor, without taking the focus and without re-indenting lines the user wrote;
  * if the cursor's line has text, the block starts on a new line;
  * the block uses the cursor line's indentation, so recording inside a `for` body works;
  * the cursor ends after the block, and `ensureCursorVisible()` keeps it in view.
  * Each block is one editor undo step (`beginEditBlock`). Rewrites use `joinPreviousEditBlock`, so one Ctrl+Z in the
    editor removes the whole recorded statement.
* **Stops recording**: the Record toggle, **Run** (it stops first, as requested), and loading another script (New,
  Open, template, Flame → Script). Closing or hiding the editor does **not** stop it (D5).

### 8.4 Undo-aware blocks
When the main window's Undo (`edited("undo")`) restores exactly the base of the most recent block, and that block is
still intact in the editor, the block is **removed** rather than answered with statements that set the old values
again. It is pushed on a small stack, so Redo re-inserts it. In every other case Undo / Redo are recorded as ordinary
diffs. This keeps "try something, undo it" from leaving noise in the script.

### 8.5 UI
* Script Editor: a checkable **Record** action (`Ctrl+Shift+R`; the Script Editor does not use this shortcut today) on
  the toolbar after Run / Stop, and in the *Script* menu. Its icon is a new painted `record` glyph (a filled circle, in
  the theme's `error` role while recording). The state label reads **● Recording** while it is on.
* Main window (D5): a permanent status-bar button, **● Recording script**, in the `error` role, hidden unless
  recording. Clicking it stops the recording. It connects through `recording_changed`. This is the only change to the
  main window besides passing `gradient_hint`.
* The Info tab says *"recorded from the main window"* for a script whose header came from D9.

### 8.6 Tests (`tests/test_script_recorder.py`, CPU engine, `main_window_factory`)
1. Record, then `set_coloring(gamma=…)` five times in quick succession → exactly one line, `coloring.gamma = <last>`.
2. A simulated Ctrl+drag in the viewport (the `conftest` mouse helpers) → one `camera.center = …` statement.
3. Gamma, then brightness, then gamma again → three blocks. Typing in the editor between two gamma edits → two blocks.
4. A Gradient Library node operation → `gradient.set_stops(...)` equal to the library's stops. Reverse → `gradient.reverse()`.
5. Transform Editor: drag a corner (sticky) → one `coefs` statement; add a transform → an `add_transform` block; delete →
   `remove_transform(k)`.
6. Main window Undo of the last block removes it, and Redo brings it back. Undo of something older is recorded as a diff.
7. A script run while recording → Run stops the recording first; nothing is recorded for the result. Loading a template
   stops recording.
8. Switching fractals inserts the comment and the baseline moves on.
9. **End to end**: record a session of mixed edits, then execute the recorded script on the fractal as it was when
   recording started → `flames_equivalent` to the fractal at the end. This is the feature's promise in one test.
10. The editor keeps the focus it had (the recorder never calls `setFocus`), and editor Ctrl+Z removes one block at a
    time.
11. The status-bar indicator appears and disappears, and clicking it stops the recording.

---

## 9. Phase 6 — Documentation, review, verification
* README:
  * Script Editor section: the Parameters tab, live re-runs, seeds, what turns live off; Record, what is recorded,
    coalescing, undo-aware blocks, the status-bar indicator.
  * *Layout*: `scripting/parameters.py`, `scripting/codegen.py`, `scripting/diff.py`, `ui/script_live.py`,
    `ui/script_parameters_tab.py`, `ui/script_recorder.py`, `ui/script_editor_actions.py`, `ui/script_output.py`.
  * Remove "no record actions as script yet" from TASK_STATE's known gaps.
* `docs/scripting.md` regenerated. The GUIDE gets a *"Recording"* section: what is recorded, absolute values, how to turn
  a recording into a tool by replacing literals with `param()`.
* `docs/state-machines.md` regenerated (`LIVE_PARAMS`, the new `SCRIPT_RUN` states). The inventory gets the recorder's
  line.
* TASK_STATE: a Round 13 entry. This plan: status and the §12 log.
* Review by the rubric. The full suite, `test_variations`, pyflakes and `tools/state_machines.py --check` are compared
  with the baseline.
* **Performance check** (recorded in the log): the time from a live tick to the first viewport frame with the Transform
  Editor and the Inspector open, and the listener cost of one `flame_restored`. If a listener is the bottleneck, it gets
  the same "re-render once edits pause" treatment the viewport already has.

---

## 10. Compatibility guardrails (what must not change)

| Surface | Guarantee | Checked by |
|---|---|---|
| `run_script`, `ScriptRunner.run`, `ScriptResult` | New keywords and fields only, each with a default. Positional calls are unchanged. | existing `test_scripting.py` |
| Scripts without `param()` | Same results, output notes, undo steps and drawer behaviour. Each Run still gets a fresh random seed, as today's `None` does. | §5.6 (9), the existing window tests |
| `FractalDocument` signals | Existing signals keep their emission order and arguments. `edited` is emitted last and is new. | §3.3 table test; `test_gradient_link`, `test_mutation_window`, `test_image_panel`, `test_editor` |
| Undo coalescing | Unchanged, except that a non-script edit now ends a script's token (a fix, §3.4). | new test + the existing undo tests |
| Viewport | `flame_restored` without the live flag still renders at full resolution. | `test_viewer_controls`, `test_main_window` |
| Flame → Script | The same output for flames without pre-affines or curves. Those two are now included. | strengthened round-trip test |
| Drawer | Tabs 0–3 unchanged, and the saved tab index stays valid. `show_tab` accepts `parameters`. | `test_flame_to_script_save_load_and_drawer_state` |
| Templates | All 35 (36) still run headless with their defaults. | `test_builtin_templates_have_metadata_and_all_run` |
| Gradient Library | It never prompts on a live tick or on any recorded edit (the Q1 rule). | `test_gradient_link` + §5.6 (2) |
| Themes | No new roles and no hard-coded colours. The WCAG test is unchanged. | `test_themes`, `test_theming` |
| Removed features | No `pitch_y` editing UI and no viewer *Detail* anywhere. | grep in the review phase |

---

## 11. Suggestions (accepted; planned in `plans/improvements-s1-s16-plan.md`)

Each has *what*, *why*, *how it fits*, *effort* and *risk*. They are grouped by how directly they build on this plan.

### A. Building directly on live parameters and recording

**S1. Parameter explorer: "show me eight versions".** In the Parameters tab, **Explore ▸** opens the Mutate & Breed grid
in a third mode. The centre cell is the current values; the eight cells around it are the script run with the
parameters jittered around them (or fully random within their ranges, or eight new seeds). Clicking a cell adopts its
values into the tab. *Why:* a slider explores one dimension at a time; a grid explores all of them at once, and picking
is faster than tuning. It is the same "pick the one you like" loop that made Mutate popular. *Fits:* `FlameGrid`,
`GridRenderer` and the `OFFSPRING` machine exist; each cell's flame is one `run_script(code, snapshot, seed,
parameters)` on a worker. *Effort:* about 1 day after Phase 2. *Risk:* low. Slow scripts make slow grids, so INERT
scripts are excluded.

**S2. Run a script on many fractals ("batch apply").** Apply the current script (or a template) to every flame of a
library file, the library selection, or the *Randomly Generated* batch. The results are written to a **new** `.fa` /
`.flame` file, never over the originals. *Why:* this is the payoff of recording ("I always do these four things to a
random flame → record once, then run it on the next batch"). Today there is no way to apply a script to more than the
one fractal on screen. *Fits:* a job window on `JobWindowBase` (the `JOB` machine gives Pause / Stop and progress for
free); `run_script` is Qt-free and thread-safe per run; the file writers exist. *Effort:* about 1 day. *Risk:* low. It
never overwrites, and scripts that prompt are refused up front (`effects`).

**S3. "Record changes" mode (relative).** A second recording style that writes `camera.zoom += 0.25`,
`coloring.gamma *= 1.2`, `transforms[0].rotate(15)` and `gradient.adjust(hue=30)` instead of absolute values, so a
recorded tool adapts to the flame it runs on rather than copying values onto it. *Why:* absolute recordings are perfect
for "make this flame like that". Relative ones are what "filters" need. *Fits:* numeric deltas fall straight out of the
diff. Triangle edits can be decomposed into rotate / scale / translate (the Transform Editor's operations are named).
The gradient needs the Gradient Library to name its operations; `GradientDocument.apply_operation` receives lambdas
today, so it would take an added `label` argument. *Effort:* 1.5–2 days. *Risk:* medium. The library's stop-based hue
shift and the API's palette-based one differ (§1.3), so the API would gain a stop-based `gradient.adjust_stops()` to
match it exactly.

**S4. Animate a parameter.** In a Parameters row: *Animate ▸ from … to … over N frames*. It creates Animation-window
keyframes, each the script's result at that value (same seed). *Why:* animation today is capture-by-hand. A parameter
sweep is the most common thing people animate, and it is exactly what parameterised scripts describe. *Fits:*
`AnimationDocument` keyframes are flames; the results come from `run_script`. *Effort:* about 0.5 day. *Risk:* low.

**S5. A script console.** A one-line `>>>` prompt under the output panel. Each line runs against the current fractal as
one undoable step (`camera.zoom += 1`, `print(transforms[0])`), with completion from the existing engine. *Why:* with
the recorder, the API becomes explorable in both directions: do something in the UI and see the code, or type code and
see the fractal. *Fits:* `run_script` + `apply_script` + `CompletionPopup`. *Effort:* about 0.5 day. *Risk:* low.

**S6. Pin templates to the main window.** A **Scripts ▾** toolbar menu listing favourite templates. Choosing one runs it
on the fractal with its saved parameter values, without opening the editor; holding Shift opens it instead. *Why:*
parameterised templates become everyday tools, and tools belong where the work happens. *Fits:* the templates API and
`ScriptRunner`; the favourites live in QSettings. *Effort:* about 0.5 day. *Risk:* low.

### B. Main-window workflow and quality of life

**S7. Open Recent.** *File ▸ Open Recent* (the last 10 files, and the entry index for multi-flame files). There is none
today (checked: the only "recent" in `ui/` is the file watcher's `wrote_recently`). *Effort:* 2–3 hours. *Risk:* none.

**S8. Crash recovery for unsaved fractals.** "Nothing is written unless you save" is a promise about the user's files.
But it also means that a crash loses every unsaved edit. The Fragments window already autosaves sessions for recovery;
the main window does not. The plan is to write the current flame and its undo kind list to a recovery file in the
config folder (never next to the user's files) a few seconds after edits pause, and on the next start to offer
*"Restore the unsaved fractal 'x' from 14:03?"*. *Effort:* 0.5–1 day. *Risk:* low (a separate folder, removed after a
clean exit).

**S9. An Undo History panel.** The document already keeps a kind for every undo step (`view`, `coloring:gamma`,
`palette`, `script`, `mutate`, …). The panel (a dock or an Inspector tab) lists them as readable labels (*"Camera",
"Gamma", "Script: Random rotate", "Adopted mutant"*), and clicking one jumps there (multi-step undo / redo). *Why:*
exploration is non-linear, and single-step Ctrl+Z through 40 slider steps is tedious. *Effort:* 0.5–1 day (about 1.5 with
thumbnails). *Risk:* low. It is a view over `_undo` / `_redo` with a `jump_to(index)` on the document.

**S10. Before / after.** Hold `\` in the viewport to see the fractal as loaded (`document.original`) or as it was before
the current undo step, and release to return (Lightroom's gesture). *Why:* judging an edit needs a comparison, and
today that means undo-look-redo. *Fits:* the viewport renders the other flame into a cached image on the first press.
*Effort:* about 0.5 day. *Risk:* low.

**S11. A command palette (Ctrl+K).** Fuzzy search over every action in every window, plus templates, themes and
recent files. *Why:* there are more than 70 actions in 11 windows, many only in menus. A palette makes all of them one
keystroke away, and it doubles as a discoverability aid (it shows each shortcut). *Fits:* `QAction`s are already
centralised per window (`*_actions.py`). *Effort:* about 1 day. *Risk:* low.

**S12. Random Batch symmetry options** (a known gap in TASK_STATE): Apophysis's bilateral and rotational symmetry for
generated flames. It reuses the symmetry template's construction. *Effort:* about 0.5 day. *Risk:* low.

### C. Rendering and performance

**S13. Instant tone-mapping** (a known gap in TASK_STATE). Colouring and curve edits currently re-render from scratch.
Re-tone-mapping the kept histogram would make the gamma, brightness, vibrancy and curve sliders, and live colour scripts,
effectively instant. *Why:* these are the most-dragged controls in the program, and they are the slowest to respond.
*Fits:* jobs can already be kept alive (round 12 notes). The histogram lives in the engine; both engines need a
"tone-map again with new settings" entry point. *Effort:* 2–3 days. *Risk:* medium (render internals, GPU and CPU paths,
refinement interplay).

### D. Code health and developer experience

**S14. Format round-trip fuzzing.** The same trick as §7.6, pointed at the file formats: mutate flames, then save and
load them as `.fa`, `.flame` and `.chaos` and compare with `flames_equivalent`. *Why:* it would catch silent data loss
in saving (TASK_STATE notes that unmodelled `<flame>` attributes are dropped; the pre-affine and curves problem in §1.2
is the same class of bug). *Effort:* about 0.5 day. *Risk:* none (tests only; failures become findings).

**S15. Finish the round-12 leftovers.** Port or retire `tests/test_fractal_files.py` (excluded by `pytest.ini`; it
targets the old `undo_stack` architecture), and merge `FractalFileActions` into `FileActionsBase` (their `file_written`
signals differ, so this needs an adapter). *Effort:* about 0.5 day. *Risk:* low.

**S16. Transform Editor polish** (known gaps): enforce `ParamInfo.min/max` when typing and dragging parameters (today
they are only in tooltips), and add rotate / scale grips around the selected triangle. *Effort:* about 0.5 day and
about 1 day. *Risk:* low.

**My picks, if only a few:** S2 (it completes the recording story), S1 (the most fun, and cheap after Phase 2), S8 (it
protects users' work), S7 (nearly free), S13 (the biggest speed-up users will feel).

---

## 12. Order, rationale, progress

The order follows the dependencies. Phase 0 fixes the API gaps and adds the document signal that both features need.
Parameters come before recording, because recording reuses the codegen and the `edited` signal, and a recorded script is
turned into a tool with `param()`. Each phase ends with the full suite green and is committed on its own.

- [x] Phase 0 — prerequisites: `pre` and curves in the API; `edited(kind)`; the token fix; the interactive hint;
      `codegen.py`; window split; strengthened round trip (§3)
- [x] Phase 1 — parameters core: `parameters.py`, `param()`, effects / `LiveRefused`, runner fields, docs entries, tests (§4)
- [x] Phase 2 — parameters window: `ParametersTab`, `LiveParameters`, `LIVE_PARAMS`, the new `SCRIPT_RUN` states,
      output live section, persistence, tests (§5)
- [x] Phase 3 — templates converted, the new template, README / GUIDE (§6)
- [x] Phase 4 — `diff.py`: sections, palette ladder, verify-and-fall-back, fuzz tests (§7)
- [x] Phase 5 — `ScriptRecorder`: blocks, coalescing, undo-aware, Record action, status-bar indicator, tests (§8)
- [x] Phase 6 — docs regenerated, TASK_STATE, review, full verification, performance note (§9)

Estimated effort: Phase 0 ≈ 0.5 day, Phases 1–3 ≈ 1.5 days, Phases 4–5 ≈ 2 days, Phase 6 ≈ 0.5 day.

### Log
* *(implemented)* All phases, together with the S1–S16 plan's waves. Deviations, each deliberate:
  * DETACHED / INERT / OFF controls stay **enabled**: moving them stores the value for the next Run (the plan had them
    disabled in DETACHED). The status chip says the session is not live and why.
  * The shared formatting module is `scripting/codegen.py`; the diff takes no `kind` (it compares everything and verifies
    itself), exactly as §7.1 argued; the recorder keeps a per-block *target* flame so a pending rewrite never includes the
    next edit of another kind.
  * Palette positions are written with every digit when nine significant digits would tip a sampled colour by one.
  * Camera centres are verified to half a pixel (the readable `coord` form), every other value to 1e-7.
  * `save_variants` defaults its file to empty (a relative default would have written into the working folder).
* *(approved)* D1–D9 accepted as recommended. §11's suggestions are planned in detail in `plans/improvements-s1-s16-plan.md`. Phase 0 runs together with that plan's §17.2–17.3 (Wave 1 there).
* *(planning)* The code was read against both proposals. The name mapping is in §1.1, the defects found in §1.2, and the
  decisions to confirm in §2.
