# Fractalchemy
A fractal flame viewer and gradient editor growing into a full fractal editor. Today it browses libraries of
Apophysis / Chaotica / Fractalchemy fractals, renders them progressively in a GPU-accelerated viewport (with a
multithreaded CPU fallback), and edits, saves and converts gradients for a variety of fractal programs.

## Running

```bash
pip install -r requirements.txt
python main.py
```

Tests (headless, uses Qt's offscreen platform):

```bash
python -m pytest
```

## What it does today

### Main window
* Menu bar: *File* (Open Fractal…, Save Fractal `Ctrl+S`, Save Fractal As ▸ New Entry / New File `Ctrl+Shift+S` /
  Into Existing File, Exit), *Edit* (Undo `Ctrl+Z`, Redo `Ctrl+Shift+Z`, Copy Parameters `Ctrl+Shift+C`, Paste
  Parameters `Ctrl+Shift+V`, Edit Fractal Library…), *View* (Show/Hide Fractal Library `Ctrl+L`,
  Refresh `F5`, Thumbnails, Show/Hide Settings Panel, Zoom to Fit / 100%, Toolbar, Status Bar),
  *Windows* (Transform Editor `F4`, Gradient Library `F6`, Animation `F9`, Random Batch `F7`, Script Editor `F8`,
  Formula Editor `F10`, Render Image… `Ctrl+R`), *Help* (Formulas…, About).
* Toolbar: **Open**, **Save**, **Save As ▾** (new entry in this file / new `.flame` or `.fa` file / into another file),
  **Undo**, **Redo**, **Copy Parameters** (the whole fractal, gradient included, as `.fa` text), **Paste Parameters**
  (`.fa`, Apophysis `<flame>` XML or a Chaotica world from the clipboard, undoable), **Transform Editor** (`F4`),
  **Gradient Library**, **Animation** (`F9`), **Random Batch** (`F7`), **Script Editor** (`F8`), **Formula Editor**
  (`F10`), **Render Image** (`Ctrl+R`).
  Nothing is ever written unless you save: edits only change the preview, the title shows `*`, and Save / Save As
  let you keep as many versions as you like.
* **Open Fractal…** shows the file's first flame and lists *all* of the file's flames in a temporary section at the
  top of the Fractal Library, above a separator; opening another file replaces it. The section follows the file:
  rename / delete / duplicate its flames there, or drag them into library files.
* **Undo / Redo** cover every edit to the fractal — camera moves (Ctrl+drag / Ctrl+wheel / double-click) and gradient
  edits made in the Gradient Library; a drag or a slider sweep is one step. The title shows `*` while unsaved.
* **Save** writes the flame back into its own entry (`.fa`, `.flame`); for a Chaotica world or a flame without a file
  it becomes *New File…*. **Save As ▸** (File menu and the toolbar button) has the same three flavours as the
  Gradient Library, so one `.fa` (or `.flame`) file can collect many fractals: *Add to This File as New Fractal…*
  (`Ctrl+Shift+A`, appends under a name you choose), *New File…* (`Ctrl+Shift+S`, `.fa` by default, also `.flame` /
  `.chaos`; an existing multi-fractal file is added to, never wiped), *Add to Another File…* (append to any `.fa` /
  `.flame`). Afterwards the document points at the saved entry, so the next Save is in place. Saving a flame that
  uses variations we can't render yet back into its `.flame` warns first, because those variations would be dropped.
* **Copy Parameters** puts the parameters (transforms, camera, colouring *and* gradient) on the clipboard as
  Fractalchemy text; **Paste Parameters** accepts `.fa`, Apophysis `<flame>` XML or a Chaotica world.
* **Fractal Library** (left pane, collapsible via the divider arrow or `Ctrl+L`): folders of `.flame`
  (Apophysis / flam3, legacy files included), `.chaos` (Chaotica) and `.fa` (Fractalchemy) files, each file
  expanding into its flames. A file opened with **Open Fractal** sits in a temporary area at the top, above a
  separator line, browsable like the rest; opening another file replaces it, and saving into it (or into a new
  file outside the library) updates the area just like the library folders update. Search box, collapse-all, and two view buttons: **list** or **thumbnails**
  (rendered on demand by the preview engine, at low priority so the viewport always comes first).
  Folders are watched, and the right-click menu / drag-and-drop file operations are the same as in the
  Gradient Library. It has its own folder list (*Edit ▸ Edit Fractal Library…*, or **+** / ✎ in the pane).
* **Viewport** (the centre): click a flame and it renders progressively in passes. The flame is framed as an
  *image* of the chosen **Image size** (dropdown under the viewer, far right: the flame's own size, common
  screen and print sizes, or Custom… with width × height). Changing it only changes the image's aspect and
  framing inside the viewer — never the window. **Guides** (button under the viewer, *View ▸ Show Guides*
  `Ctrl+G`) overlays composition lines on the whole image like Apophysis's guidelines — the rule of thirds,
  the golden ratio (38.2 % / 61.8 %) and the centre lines, each switchable from the button's menu; the choice persists.
  * **Look around without changing the fractal**: left-drag pans, the wheel zooms about the cursor, and the
    **Zoom** box (bottom left) lists Fit / 25–200 % or takes any typed value up to 300 %; zooming out stops once
    the whole image is visible (*View ▸ Zoom to Fit* `Ctrl+0`, *Zoom 100%* `Ctrl+1`). Only the visible part of
    the image is rendered, at screen density, so zooming in genuinely shows more detail at no extra cost.
  * **Re-compose the fractal**: hold **Ctrl** — drag moves the camera, the wheel zooms it (about the cursor),
    double-click re-centres. These change the flame's `center` / `zoom`.
  * While you interact the render runs at half resolution; a quarter second after you stop it re-renders at
    full resolution. Meanwhile the previous picture is simply repositioned under the new view (never stretched),
    and a newer view always cancels the older render, so a stale image never overwrites the current one.
* **Settings panel** (right, collapsible via its divider arrow or *View ▸ Show/Hide Settings Panel* `Ctrl+Shift+L`):
  * *Info* — what the loaded fractal is made of: file / entry / format, size and camera (incl. the 3D camera),
    every transform with its weight share, colour, variations and their parameters, affine / post / xaos, the
    distinct **formulas** it uses (use count, pre/normal/post, 3D, direct colour, random, origin — double-click
    one to open it in the formula browser; unavailable ones are flagged), the colouring and palette strip, and
    the facts of the last preview render.
  * *Image* — everything that shapes the picture, each group with a ↻ *Revert* (back to the file's values):
    **Preview** (passes and quality — samples per pixel — then *Keep refining to* a quality cap while
    nothing changes, each extra pass doubling the samples; **Oversample** and **Filter** are Apophysis's
    supersampling and Gaussian filter radius, 2 / 0.5 = plain 2×2 anti-aliasing; all persist between runs);
    **Camera** (zoom slider + box, Apophysis log2 zoom around the image centre; pan arrows moving the view
    by 0.1 fractal units along the screen axes — **Shift** 1.0, **Ctrl** 0.01 — rotation respected; centre x / y
    and rotation boxes); **3D camera** (**pitch** tilts about the horizontal axis, **yaw** spins the plane, plus
    perspective, z position, depth blur — Apophysis's `cam_*` attributes, so a
    2D flame becomes a tilted plane and variations with depth — `julia3D`, `curl3D`, `ztranslate`, `zcone`,
    `blur3D`, `zblur`, `zscale`, `pre_`/`post_rotate_x/y`, `linear3D`, … — show real 3D); **Coloring** (brightness, gamma, gamma threshold, vibrancy,
    contrast, background colour via the live picker); **Curves** (Chaotica-style tone curves — overall, R, G, B
    and alpha/coverage — click to add points, drag, right-click to remove, *Reset* per channel and *Reset all*;
    Apophysis 7X `curves` are read, ours are saved as `fa_curves`).
  Every change re-renders and is undoable; nothing is written until you save. The tab you were on persists.
* **Status bar** across the bottom: the loaded fractal (name, transform count, size, file, ignored
  variations), render facts (engine, render size, samples, samples/second — the full GPU name is in the
  tooltip), **Pass n of N** → **Refining · q 64** → **q 500 ✓** (samples per pixel), and a progress bar.
  Zoomed-in views get Apophysis's `4^zoom` extra samples so they stay as clean as the whole picture.
* *Windows ▸ Gradient Library* (`F6`) or the toolbar button opens the **Gradient Library** window —
  the gradient editor described below. It is a tool window that stays above the main window; closing it
  only hides it, so the gradient you are editing (and any unsaved edits) stay put until you reopen it.
  Quitting the application asks about unsaved edits first.
* **The two are linked.** Choosing a fractal loads its gradient into the Gradient Library — the same entry
  of the same file, so *Save* writes the colours back into that flame. Every gradient edit (nodes, sliders,
  node operations, or picking another gradient in the library) recolours the fractal and re-renders the
  viewport. A small preview beside the gradient strip mirrors the viewport, so the effect is visible even
  with the Gradient Library maximised. Switching fractals with unsaved gradient edits asks first.

### Rendering
Two engines share one scene model (`fractalchemy/fractal`), so what you see in the viewport is a faithful
preview of what the final renderer will produce — see [docs/rendering.md](docs/rendering.md) for the design.

* **Preview engine** — moderngl / OpenGL 3.3: points are iterated in a vertex shader (transform feedback),
  plotted with additive blending into a float histogram and tone-mapped on the GPU. Each flame gets its own
  generated GLSL; numbers live in a parameter texture so parameter edits won't recompile.
* **CPU engine** — the same chaos game vectorised in numpy across all cores (float64). Used automatically
  when no OpenGL context can be created; it is also the seed of the precision/final renderer.
* Both use Apophysis's log-density tone mapping (brightness, gamma, gamma threshold, vibrancy, background),
  Apophysis's transform semantics (`pre_` / `post_` variation order, `var_color` direct colour, depth `z`)
  and its 3D camera (`cam_pitch`, `cam_yaw`, `cam_perspective` / `cam_dist`, `cam_zpos`, `cam_dof`).
* **Formulas** (variations / plugins) live in `fractalchemy/formulas/` — see
  [docs/formulas.md](docs/formulas.md). Some 820 are bundled: the flam3 classics and Apophysis 7X built-ins,
  every Apophysis plugin whose source was available, plugins that only existed as (mostly 32-bit) DLLs,
  reconstructed from their machine code, and 250-odd variations translated from JWildfire
  (`tools/import_jwf_variations.py`; the report in [docs/jwildfire_import.md](docs/jwildfire_import.md) lists
  what could not be translated and why). Each is defined once and compiled for *both* engines from the
  Apophysis plugin C dialect (or written natively in Python + GLSL), and the test-suite checks that numpy
  and GLSL agree on every one. Your own formulas go into the per-user formulas folder (*Help ▸ Formulas…*
  shows it, together with everything loaded and why anything failed to load) — the **Formula Editor** (`F10`)
  writes them there and shows them working while you type. Formulas a flame uses that are not available are
  listed in the status bar and ignored.
* Tunables in `config.py`: `PREVIEW_PASSES` / `PREVIEW_QUALITY` (defaults for the settings panel),
  `INTERACTIVE_SCALE`, thumbnail size / quality.

| Fractal format | Read | Entries | Rename | Add / remove / replace |
|---|---|---|---|---|
| `.flame` (Apophysis / flam3) | ✓ | many | ✓ | ✓ (in-place text edits; unknown data survives) |
| `.fa` (Fractalchemy, JSON) | ✓ | many | ✓ | ✓ |
| `.chaos` (Chaotica) | ✓ | many | ✓ | – |
| `.faanim` (Fractalchemy animation, JSON) | ✓ (Animation window) | one animation | – | ✓ |

### Transform Editor window
*Windows ▸ Transform Editor* (`F4`, the triangle on the toolbar) is Apophysis's editor, rebuilt: it edits the fractal
shown in the main window, every change is undoable from either window (`Ctrl+Z`), and closing it only hides it.

* **Three affines per transform.** The buttons at the top — **Pre-Affine**, **Normal** (default, shown in the
  highlight colour) and **Post-Affine** — choose which triangle of each transform the canvas shows and edits.
  *Normal* is Apophysis's triangle (the affine before the variations); *Post-Affine* is Apophysis's post-transform
  (applied after the variations); *Pre-Affine* is new: a third affine applied to the incoming point *before* the
  normal triangle, so it acts in the transform's own frame (moving it slides the input along the triangle's axes,
  rotating it turns the input about O in local units). The order is *pre affine → normal → variations → post affine*.
  While editing a pre or post affine the normal triangles stay visible, dotted. The three are saved with the
  fractal (`pre_affine="…"` / `post="…"` in `.flame`, `pre` / `post` in `.fa`; Apophysis ignores the pre affine,
  Chaotica files get it folded into the affine they have), and all three work on the **final transform** too.
* **The canvas** works like Apophysis's: each transform is a coloured triangle with corners **X**, **O**, **Y**
  (the final transform white; *View ▸ Use transform colors* takes the palette colour instead). Drag a corner to
  move it (**O** drags the whole triangle while the axes are locked); drag inside a triangle to move it, or — in
  the **Rotate** / **Scale** modes, or holding **Alt** / **Ctrl** — to turn or scale it about the pivot; drag an
  axis edge to rotate and the hypotenuse to scale; **Shift** snaps to the angle / step in the Triangle tab.
  The pivot is the triangle's O (*local*) or the world origin (*world*, the target button / `Space`), or any
  point typed into the Triangle tab. Right-drag pans, the wheel zooms, double-click on empty space fits
  everything (`Ctrl+0`), double-click a corner or a triangle resets its position / rotation / scale, `Esc`
  cancels a drag. Arrow keys nudge by the move step (Shift ×10, Ctrl ÷10), `Alt+←/→` and `PgUp/PgDn` rotate,
  `Alt+↑/↓` and `Home/End` scale, `Insert` duplicates, `Delete` deletes, `M` / `R` / `S` pick the move / rotate /
  scale mode, `A` toggles select mode, `T` steps through pre / normal / post. Hovering a triangle lists its
  variations in the corner; the status bar shows the cursor position, the zoom and what a drag did.
* **Toolbar**: new flame (one linear transform, camera reset; palette and colouring kept), add / duplicate /
  delete / link transforms (a *linked* transform takes over the selected transform's xaos links, as in
  Apophysis), undo / redo, copy / paste triangle coordinates, the select / move / rotate / scale modes, world
  pivot, rotate 90°, flip, **variation preview** (`V`: a grid of points sent through the selected transform is
  drawn on the canvas in its colour, so what its variations and parameters do is visible on the triangles —
  range, depth and density are the sliders on the Colors tab, as in Apophysis), the final transform on / off,
  fit. The context menu (right-click) has the same, and *View ▸ Reload formulas* re-reads the formula folders.
* **Transform header**: the transform list (coloured), a **name** — a label to keep track of what each
  transform does, saved in the file and shown in the list, on the canvas and in the Info tab — and the weight.
* **Tabs** (Apophysis's): **Variations** — every loaded formula (the flam3 classics, the Apophysis 7X built-ins,
  the bundled plugins and your own formulas; *View ▸ Reload formulas* picks up files added since start-up) with
  its weight; used ones in bold, a search box, *Hide unused*, *Clear*; a third column tags `pre` / `post`
  formulas, **3D** ones (they set the depth — `julia3D`, `ztranslate`, `zscale`, `curl3D`, `blur3D`, …), direct
  colour and random ones. Type a weight, drag a name sideways (Shift coarse, Ctrl / Alt fine) or double-click it
  for 0 ↔ 1. **Variables** — the parameters of the active variations (the z / 3D ones included), typed or
  dragged, double-click resets the default, *Show all variables* lists every parameter of every formula.
  **Xaos** — the outgoing (*to*) or incoming (*from*) weights, *Clear all* / *Set all*. **Triangle** — corner
  coordinates, rotate / move / scale buttons with their amounts, the pivot, axis lock, extended edit and *auto
  weights from triangle area*. **Transform** — the X / Y / O vectors of all three affines, rectangular or polar,
  with reset buttons, and *Auto-calculate pre_zscale* (keeps `pre_zscale = √|det|`, Apophysis's 3D helper).
  **Colors** — the transform colour on the palette strip, colour speed (flam3's, with Apophysis's `symmetry`
  shown beside it), opacity, direct colour (`var_color`), *solo*, and the variation preview's range / depth /
  density.
* **Previews**: the editor's own preview (right-click for the quality: *Low* 2 samples per pixel, *Medium* 5
  and *High* 15, the latter two anti-aliased like the main viewport, High in two passes) follows every drag;
  the **main viewport** waits until the edits pause — a second after the last change (`EDIT_RENDER_DELAY_MS`)
  it re-renders at full quality, so dragging never keeps the GPU / CPU churning.

### Animation window
*Windows ▸ Animation* (`F9`, the film strip on the toolbar) turns fractals into keyframes on a timeline.

* **Keyframes.** *Capture keyframe* (`K`) pins whatever the main window shows at the playhead's frame — so the
  workflow is: show or adjust a fractal (main window, Transform Editor, Gradient Library), capture, move the
  playhead, change it, capture again. Capturing on a frame that has a keyframe replaces it; *Update keyframe*
  replaces the selected one with the main window's fractal; *Delete* removes it. Clicking a keyframe (in the list
  or on the timeline) does what choosing another fractal does: the main window shows it, ready to be changed
  and captured again. Keyframes can be dragged along the timeline, moved with the *Frame* box and labelled.
* **Timeline.** A ruler of frames and seconds with the keyframes as diamonds and a playhead: click or drag to
  scrub, wheel to zoom (Shift + wheel scrolls), double-click to fit, ←/→ step (Shift: a second), Home / End.
* **Settings.** Name, frame rate, length (frames or seconds — never shorter than the last keyframe),
  **interpolation** (*Linear*: every number blends straight between neighbouring keyframes; *Smooth*: a
  Catmull-Rom spline through the keyframes, so motion flows through them; *Hold*: a slideshow), **easing**
  (in / out / both) and **loop** (the end blends back to the first keyframe; playback repeats). Between
  keyframes everything is interpolated: affines (all three), weights, colours, variation weights and parameters,
  xaos, the 2D and 3D camera, colouring and the palette. Transforms that exist in one keyframe only fade in or
  out; variations missing on one side ramp from zero keeping the other side's parameters; a final transform
  appears as the identity where a keyframe has none.
* **Preview and playback.** The small preview (right-click for the quality) shows the interpolated fractal at
  the playhead; *Play* (`Space`) runs the animation in it at its frame rate — frames are dropped when the engine
  is slower than real time, so timing stays true — *Stop* returns to where playback started.
* **Files.** Animations are `.faanim` (JSON, every keyframe a complete fractal, plus fps, length, interpolation,
  easing, loop and the last render settings). *Open* shows the first keyframe in the main window and loads the
  rest into the editor.
* **Render Animation…** (`Ctrl+R` in the Animation window) opens the batch renderer: the Render Image window's
  size and quality panels, then an **output folder** and a base name instead of a file (`name_0001.png`,
  `name_0002.png`, … in any image format with its options), the frame range and step, *skip existing frames*
  (resume a stopped batch), parameters beside or inside each frame, and — when **ffmpeg** is installed —
  *Make a video with ffmpeg* (MP4 H.264 / H.265, WebM VP9, ProRes MOV or an animated GIF with a palette pass;
  CRF quality; the video lands in the same folder, the frames optionally removed afterwards). The command
  line it will run is shown. One engine (GPU context or CPU worker processes) renders every frame; progress
  shows the frame, a preview, elapsed and remaining time; Pause / Stop as for a single image. The settings
  persist and are saved in the `.faanim` file, so a render can be repeated.

### Random Batch window
*Windows ▸ Random Batch…* (`F7`, the die on the toolbar) generates random fractals the way Apophysis's random
batch does: a list of **every loaded variation** — built-ins, bundled plugins and your own formulas — each with
a check box (filter box with debounce, *Check all* / *Uncheck all* acting on what is listed), the number of
fractals to make and the transform range. Each fractal gets 2–5 transforms from Apophysis's affine recipes,
two of the checked variations with complementary weights per transform, area-based or equal weights, a
random gradient, and is framed automatically; systems that blow up are rolled again. The result is **not
saved**: it appears in the library's temporary area under the heading **Randomly Generated** (replacing an
opened file there), browsable with thumbnails like any file. Open one, adjust it, and *Save* / *Save As* put it
in a file of your choosing — the batch stays on show so you can keep the others too. Your checks, count and
range persist; a formula you add later starts out checked.

### Script Editor window
*Windows ▸ Script Editor* (`F8`, the script-sheet button on the toolbar) opens a tool window for **scripting the
fractal in Python** — the Apophysis script editor, but with Python and everything Fractalchemy can edit: transforms
(affines, weights, colours, the active transform), variations and their parameters (every loaded formula, plugins
included), the gradient and palette, the chaos / xaos matrix, the camera (2D and 3D), the tone mapping, plus
prompts, random numbers and live previews. Closing the window hides it; the script, the drawer state and the
window layout are remembered between runs. See [docs/scripting.md](docs/scripting.md) for the full reference.

* **Toolbar**: New / Open / Save / Save As (`.py` files) · **Run** (`Ctrl+Enter`) / **Stop** (`Shift+Esc`) ·
  Undo / Redo · Find & replace (`Ctrl+F` / `Ctrl+H`), toggle comment (`Ctrl+/`), outdent / indent · **Check syntax** ·
  **Flame → Script** (a script that rebuilds the current fractal — the quickest way to start editing one) ·
  **Revert flame** (back to before the last run) · **Save as template** · clear output · show / hide the drawer (`Ctrl+L`).
  The *File*, *Edit*, *Script* and *View* menus hold the same actions plus go-to-line and the drawer's tabs.
* **Editor** (left): Python syntax highlighting with the API's names picked out, line numbers, the current and any
  error line highlighted, **tab completion** with inline documentation — type `transform.`, `gradient.`, a local
  variable or the start of a name and press `Tab` (or `Ctrl+Space`); inside `set_variation('…')`, `variations['…']`
  and `params['…']` the list holds the valid names; inside a call the keyword arguments are offered. Local variables
  are type-inferred (`t = add_transform(); t.` knows `t` is a transform, as do `for t in transforms:` loops and
  `for_each_transform` callbacks). Auto-indent, Backspace un-indents, `Ctrl+D` duplicates, `Ctrl+Shift+K` deletes and
  `Alt+↑/↓` moves lines. The **output panel** beneath it shows `print()` text, results and errors — an error names
  its line and clicking it jumps there.
* **Drawer** (right, sliding like the main window's panels): **Context** — dynamic documentation that follows the
  cursor: the members of the object being typed, or the call the cursor is in with its current argument highlighted
  and, for arguments that take a known set of values, that list (e.g. every variation name); click anything to insert
  it. **Reference** — the scripting guide, the searchable API reference and the catalogue of loaded variations.
  **Info** — the script's name, file, `# @name` / `# @author` / `# @description` metadata, size, the API it uses,
  whether it prompts or animates, and the last run (time, result, transforms before → after). **Templates** — 35
  built-in templates by category (*Random rotate all transforms*, *Normalize weights*, *Add random transform*,
  *Julia mutation*, *Make rotational symmetry*, *Spiral*, *Tile the plane*, *Gnarl*, gradient, xaos and camera
  helpers, *Random flame explorer*, *Flame report*, *Build a flame from scratch*, …) plus *My templates*: save the
  current script as one, overwrite, rename, delete; load, insert at the cursor, or load-and-run. User templates are
  plain `.py` files in the per-user scripts folder (*Open folder*), so they can be shared.
* **Running**: a script runs on a worker thread against a copy of the fractal; `print()` streams into the output
  panel, `input_text()` / `input_number()` / `confirm()` pop up dialogs, `message()` shows a box, `update()` pushes
  the current state into the main window and re-renders (with `sleep()` that makes animation previews), `progress()`
  feeds the status bar, `stop()` ends the script keeping its changes. When it finishes the fractal takes the result
  as **one undo step**; an error leaves the fractal untouched (intermediate updates are rolled back). **Stop** ends
  any script — `while True:` loops, sleeps and open prompts included.
* **The API** (Python, no imports needed): `flame`; `transforms` / `transform` (the active one) with `a`–`f`,
  `coefs`, `post`, `weight`, `color`, `color_speed`, `opacity`, `variations[…]`, `params[…]`, `xaos`, and
  `rotate()`, `scale()`, `translate()`, `rotate_around()`, `multiply()`, `flip_*()`, `set_variation()`, …;
  `add_transform()`, `add_random_transform()`, `remove_transform()`, `copy_transform()`, `set_active_transform()`,
  `set_final_transform()`, `normalize_weights()`, …; `camera` (`x`, `y`, `scale`, `zoom`, `rotate`, size, the 3D
  camera, `fit()`, `zoom_by()`, `pan()`); `gradient` (`colors`, `stops`, `set_stops()`, `random()`, the Gradient
  Library's node operations and sliders, `load()` from any gradient file); `xaos` (`set()`, `matrix`, `chain()`,
  `isolate()`, `from_function()`, `randomize()`); `coloring`; `new_flame()`, `random_flame()`, `load_flame()`,
  `save_flame()`, `flame_xml()`, `snapshot()` / `restore()`; random helpers; and Apophysis-style aliases
  (`Transform`, `AddTransform`, `Rotate`, `Scale`, `Translate`, `Multiply`, `RotateFlame`, `UpdateFlame`, `Print`, …).

### Formula Editor window
*Windows ▸ Formula Editor* (`F10`, the *ƒv* sheet on the toolbar) is where formulas (variations / plugins) are written
and tried out **live**: the code compiles by itself a moment after every change, for both engines, and the result is
drawn on a transform grid and rendered in a preview while you type. Closing the window hides it; what you were
writing, the favourites, the recent list and the layout are remembered between runs. The window starts empty.

* **The grid** (top left) is a small Transform Editor canvas with its own little flame: one *formula* transform on
  the reference triangle, running the formula being edited, with the **variation preview** on by default — so the
  formula's effect is drawn as a grid of points sent through the transform (*Variation preview options* in the
  side column, folded away behind a caret: range / depth / density sliders and *Show the input grid*). Its toolbar: **Undo / Redo** (this
  flame's own history), **add a linear transform**, **add a spherical transform**, **add a formula transform**
  (another one running the formula), **Duplicate**, **Delete** the active transform, flip, the variation preview,
  **Compare** (see below), fit, **Test rig ▾** (starter flames: the formula alone, with a linear, two formulas, a
  Julia pair, a Sierpinski set) and a **Transform** dropdown that selects the active transform. Triangles drag as in
  the Transform Editor (corners move, edges rotate / scale, arrows nudge, `V` toggles the preview). The right-click
  menu on a triangle adds **Use the formula on this transform** / **Make it linear** / **Make it spherical**, rotate
  90°, flip horizontally / vertically and reset. *Transform ▸ Use the main window's fractal* copies the fractal
  shown in the main window onto the grid to try the formula on; *Send to the main window* pushes the grid's flame
  out as a new fractal (a saved formula's transforms go with it; an unsaved one's become linear).
* **Preview** (top right): the flame rendered through the shared render service — the GPU when there is one —
  following every change (quality in the View menu or by right-click; the status line says when the GPU rejected
  a shader and the CPU rendered instead). **Compare with the original** (`Ctrl+Shift+O`) shows a second preview
  rendering the formula as it was before the edits, side by side. Beneath them, **Gradient**: a bar showing the
  preview's gradient, a bright three-colour one to begin with, with a **Presets ▾** button (six bright presets and
  *Random*). Clicking the bar opens the **Gradient Library** with that gradient loaded, so the main window's
  fractal takes it too; from then on every gradient edit or choice made there recolours this preview as well —
  one gradient everywhere, for ease. **Variables** lists the active transform's parameters (the formula's own,
  under its name) with **Reset**, **Randomise** and a **Sweep** that animates one variable over its range to show
  what it does; edits are undoable.
* **Formulas**: every loaded formula with tags (`pre` / `post` / `3D` / `DC` / `random`), where it came from and,
  when the file names one, its author. Rows are **colour-coded by origin** — light blue for the built-ins, amber
  for the Apophysis plugin library, green for the JWildfire translations, violet (and bold) for your own — with
  darker text of the same hue; the same tints mark the Transform Editor's Variations list and the formula
  browser. Click a heading to sort; a search box, origin and kind filters, and **favourites** (double-click the
  star, or the context menu; *Favourites* in the origin filter lists them). Clicking one loads its code (a
  bundled `.c` source, or for a native Python built-in a dialect skeleton carrying its numpy and GLSL as a
  reference) and puts the real formula in the previews until the text is changed. **New formula ▾** (`Ctrl+N`,
  also on the *Formula* menu) offers templates — normal (a swirl), normal (linear), pre, post, direct colour,
  3D, blur — each a complete formula with one variable, named so it clashes with nothing. *Formula ▸ Recent
  formulas* reopens what you worked on lately.
* **The code editor**: C syntax highlighting that knows the dialect (the plugin API, `FTx` / `FPy` / `VVAR` / `TC`,
  the math functions and constants, both comment styles), **completion** (Tab / Ctrl+Space, or by itself after
  two letters: the dialect's names with one-line docs, and the file's own variables), line numbers, brace-aware
  indentation, find / replace (`Ctrl+F` / `Ctrl+H`), go to line (`Ctrl+G`), `Ctrl+/` comments, `Ctrl+D` duplicates,
  `Alt+↑/↓` moves lines, its own undo / redo, `Ctrl+E` to switch the keyboard between the code and the grid.
  **Insert variable…** (`Ctrl+Shift+I`) declares a variable in the struct and in `APO_VARIABLES` at once (real or
  integer, optional bounds) and puts `VAR(name)` at the cursor; *Edit ▸ Insert snippet* has the usual idioms
  (polar coordinates, `fsincos`, a random number, a guarded division, a derived constant, direct colour, depth,
  the noise header). The line beneath the editor says what the code compiled to (`✓ name — normal; 2 variables`)
  or what is wrong and on which line (the line is marked too); while the code is broken the previews keep
  showing the last version that compiled. *Compile now* (`Ctrl+Enter`) does not wait for the pause.
* **The drawer** (right edge, `Ctrl+L`, collapsed at first): **Reference** — the dialect guide
  (`docs/formulas.md`), the catalogue of every name the compiler knows (click one to insert it) and a summary of
  the formula being edited; **Compiler** — the numpy and GLSL the last good compile generated, and the compiler's
  remarks; **Probe** — one point through the formula on numpy *and* GLSL (on a context of its own, off the GUI
  thread), and **Check numpy vs GLSL**, the test-suite's comparison on its sample points, for the formula at hand.
* **Files**: **Save** (`Ctrl+S`) writes `name.c` into your formulas folder (*Formula ▸ Open formulas folder* shows
  it) and registers the formula at once, so the Transform Editor's Variations list, the Random Batch and the
  formula browser have it without a restart. **Bundled and built-in formulas are read-only**: a formula carrying
  one of their names cannot be saved over them — Save offers to rename yours (`whorl` → `whorl_mine`, variable
  prefixes included), *Duplicate as my own* does the same on purpose, and *Rename…* changes the name and the
  prefixes by hand. **Save as…** picks a file outside Fractalchemy's own folders, **Open…** loads a `.c` from
  anywhere, **Revert to saved** throws the edits away, **Delete** removes a file of yours (the code stays in the
  editor in case it was a slip), **Copy source** puts the text on the clipboard. The user folder is watched: a
  formula dropped in or changed by another program is loaded (and reloaded into the editor unless it has unsaved
  edits). Nothing is registered under its real name until you save: while you type, the work in progress lives in
  a reserved registry slot that only this window uses.

### Render Image window (the final renderer)
*Windows ▸ Render Image…* (`Ctrl+R`) or the toolbar button opens a non-modal tool window; a render runs on its
own thread with a snapshot of the flame, so you can open and edit another fractal while it works. Closing the
window hides it — the render carries on; quitting asks first.

* **Size** — the first preset is the viewer's current image size; then common screen and print sizes, or type
  any width × height (no upper limit beyond memory and disk). The **link** button keeps the aspect ratio: with it
  on, typing one dimension updates the other; off, they are independent. **⇄** swaps them.
* **Quality** — the Apophysis render options: **Density** (samples per pixel; 100 … 16 000 presets or any value),
  **Oversample** (1–8 buckets per pixel per axis), **Filter** + **Radius**. The filter is the anti-aliasing
  choice: Gaussian, Box, Triangle, Mitchell-Netravali, Catmull-Rom, B-spline, Lanczos 2 / 3,
  Blackman-Harris. **Denoiser**: *Density estimation* (flam3's adaptive blur, with max / min radius and curve),
  or an image-space pass after rendering — *Guided filter* and *Bilateral* (built in), *Non-local means*
  (with `opencv-python-headless`), *Intel Open Image Denoise* (with the `oidn` package) — each with a strength.
  **Engine**: automatic, GPU (OpenGL, single precision, fast) or CPU (one worker process per core, float64,
  exact at deep zooms). **Memory limit**: the histogram budget; larger images are rendered in tiles
  (Apophysis's "slices": every tile runs the full chaos game, so the plan line tells you the cost).
* **Output** — file and format: PNG (8 / 16-bit), JPEG, TIFF (8 / 16-bit), WebP, BMP, AVIF, HEIF, JPEG XL
  (the last three when their encoders are installed), **OpenEXR** (16-bit half or 32-bit float, linear light with
  premultiplied alpha, ZIP-compressed; the header carries the flame's name, source, camera, colouring, engine, sample
  count, render time, tile count, the full settings as JSON and the parameters XML, plus `comments` / `capDate` /
  `writer` for other DCCs), SVG (the render embedded as PNG). Options greyed out when the format cannot use them:
  bit depth, quality / lossless, **transparent background**. *Save parameters*
  writes a `.flame` beside the image; *Embed parameters* stores them in the file (PNG text chunk, JPEG comment,
  TIFF description, EXIF comment elsewhere); *Save incomplete renders* keeps what was done when you stop.
  *Save fractal and render details* (off by default) writes a report beside the image — `name.md`, `name.txt`
  or `name.html` — with every render setting, the tile plan, timings per phase and per tile, sample counts,
  speeds, hit ratios and bucket statistics, the system it ran on, and a full breakdown of the fractal:
  camera and colouring, palette statistics (dominant hues, luminance, smoothness), every transform (weights,
  probabilities, affines, determinants, variations, parameters, xaos), and a per-variation usage table.
  The text form is one `key<TAB>value` record per line with dotted lower-case keys and `#` comments, so
  `grep '^timing\.' name.txt | cut -f2` or `awk -F'\t' '$1=="render.samples_per_second"'` work as-is for
  tracking usage over time.
* **Progress** — a live preview that fills in tile by tile, a progress bar, elapsed and **remaining** time
  (from the measured sample rate), speed and tile counter. Before you start, the window estimates the time from
  the preview engine's or the last render's measured speed. **Pause / Resume** and **Stop** (which still saves if
  *Save incomplete renders* is on); afterwards the result line links to the file and its folder.
* Settings persist between runs; the destination defaults to the last folder and the flame's name.

### Gradient Library window
Its own *File* (Open, Save, Save As, Close Window), *Edit* (Edit Library…) and *View* (Show/Hide
Library, Refresh Library) menus, so the shortcuts below work whenever that window is active. The
title shows the gradient's name and a `*` while it has unsaved edits.

#### Library (left pane)
* Add folders with **+** (or *Edit ▸ Edit Library…* / the ✎ button, which lists every folder
  with its path, supported-file count and a ✕ to remove it). Folders persist between runs.
* The tree shows folders, supported files, and — for `.flame` / `.ugr` files holding several
  gradients — each named gradient as a child row. Click any file or gradient row to show it.
* Search box (debounced) matches file names **and** gradient names inside files; the ▲ button collapses the tree.
* Folders are watched (`QFileSystemWatcher`): files added, removed or rewritten by other programs show up
  automatically, and the open file is reloaded if it changes on disk and you have no unsaved edits.
* Right-click: Open, Copy, Paste, Duplicate, Rename, Delete, New Folder, Show in File Manager,
  Refresh, Remove from Library.
* Drag a gradient row onto another `.ugr` / `.flame` file to **move** it there (hold **Ctrl** to copy);
  onto a folder to create a new `.ugr` from it. Drag files between folders to move them.
* The arrow in the middle of the divider (or *View ▸ Show/Hide Library*, `Ctrl+L`) collapses the pane.
* Scanning, loading and every file operation run on a thread pool; the UI never blocks.

#### Editor
* **Whole gradient** box: *Position* rotates the gradient (−200…200 = one full turn in 1/400 steps,
  nodes wrap around the ends); *Hue / Saturation / Luminance* shift every colour. Sliders and spin
  boxes are linked; values are always applied to the gradient as it was when you started adjusting,
  so dragging back and forth is lossless. Any other edit (dragging a node, the buttons, loading)
  bakes the adjustment in and returns the sliders to zero.
* *Randomize nodes* (new positions, colours kept), *Randomize node colors* (positions kept, colours drawn from a
  random harmony — analogous / complementary / triadic / split), *Reroll gradient* (new count, positions and
  colours), *Auto increase nodes* (2–6 harmonising colours), *Decrease nodes* (drops 25–50 %),
  *Smooth gradient* (blurs the colour curve and keeps only the nodes needed to reproduce it).
* *Copy gradient* puts the gradient on the clipboard as UGR text — the format Ultra Fractal's and
  Apophysis's gradient editors paste from. *Paste gradient* accepts the same text back (also a bare run of
  `index=/color=` tokens or a flame `<palette>`), replacing the current entry's nodes but keeping its name.
* **Selected node** box (right of the gradient, greyed out until a node is clicked): type a node number
  to select it; click the colour swatch for a movable, non-modal picker (hue/saturation wheel, H/S/L
  sliders, R/G/B and hex fields, before/after preview) that updates the gradient live — Cancel reverts.
  Position has a slider plus spin box in 0–399 (UF index) units; dragging past neighbours is allowed.
  *Add node* (same colour, midway to the next node), *Add random node*, *Randomize node* (nudges
  hue/saturation/lightness), *Delete node* (never below two nodes).
* Gradients are cyclic, as in Ultra Fractal / Apophysis: beyond the first/last node the colour
  blends across the wrap rather than clamping.
* The strip above the editor shows a thumbnail of **every gradient in the open file**; click one to edit it.
* **Save** (`Ctrl+S`) writes the gradient back into its own slot in the file and refreshes its thumbnail.
* **Save As ▾**: *Add to This File as New Gradient…* (`Ctrl+Shift+A`), *New File…* (`Ctrl+Shift+S`),
  or *Add to Another File…*. Afterwards the editor points at the saved location, so the next Save is in place.
  Flame gradients keep their fractal: a new entry or new file made from a flame clones the source `<flame>`
  (xforms, camera, …) under the new palette. Existing multi-gradient files are never overwritten by
  *New File…* — the gradient is saved into its own slot or appended instead.

* **Open** (`File ▸ Open…`, `Ctrl+O`) any of:

  | Format | Entries per file | Save in place | Add / remove entries | New file |
  |---|---|---|---|---|
  | `.flame` (Apophysis / flam3) | one per `<flame>` | ✓ | ✓ | ✓ |
  | `.ugr` / `.gradient` (Ultra Fractal gradients) | many | ✓ | ✓ | ✓ |
  | `.ufr` (Ultra Fractal fractal) | one per layer | ✓ | – | – |
  | `.map` (Fractint / UF palette) | one | ✓ | – | ✓ |
  | `.chaos` (Chaotica world) | one per IFS | ✓ | – | – |
  | `.fa` (Fractalchemy document) | one per flame | ✓ | ✓ | ✓ |
  | images | one (extracted) | – | – | – |

  `.ufr` files are binary containers (header + parameter text + cached render); only the
  gradient section of a layer is rewritten and the header offsets are adjusted, so the
  cached pixels survive. A no-op save reproduces the file byte-for-byte.
  * images – dominant colours are extracted and ordered into a gradient:
    PNG / APNG (first frame), JPEG, AVIF, HEIC/HEIF, JPEG XL, WebP, GIF, BMP, TIFF,
    and SVG (rasterised via Qt). Transparent pixels are ignored.
* The gradient is painted in the editor with one **node** beneath each colour stop.
  Drag a node anywhere along the bar, including past other nodes; the others stay put.
* **Save** (`Ctrl+S`) writes back to the source file when it is a flame/ugr
  (for a flame, only the first palette block is rewritten; everything else is preserved).
  **Save As…** lets you pick `.flame` or `.ugr`. Image-derived gradients save as `.ugr`.

## Layout

```
main.py                 entry point only
ui/main_window.ui       Qt Designer layout of the main window: fractal library + viewport, menus, toolbar, status bar
ui/gradient_library_window.ui
                        Qt Designer layout of the Gradient Library window (GradientEditor etc. are promoted custom widgets)
docs/rendering.md       the dual-engine rendering design
docs/scripting.md       the scripting guide and API reference (generated by tools/scripting_reference.py)
fractalchemy/
  config.py             tunables: app name/version, node counts, simplify tolerance, sizes, preview quality
  settings.py           QSettings identity
  animation/            keyframed animations: model (Animation / Keyframe), interpolate (alignment + blending),
                        format (.faanim), render (AnimationRenderSettings, frame names, the ffmpeg command),
                        render_job (the batch thread: one sampler for every frame, then ffmpeg)
  fractal/              the shared scene: Flame / XForm / Camera / Coloring, the variation registry (numpy + GLSL),
                        formats/ (.flame XML, .chaos, .fa), triangles (affine ⇄ editor triangle geometry),
                        triangle_drag (the mouse-drag maths), xform_ops (add / duplicate / link / delete transforms
                        with consistent xaos)
  formulas/             the formulas: builtin/ (native Python), library/ (the plugin dialect, one file each:
                        apophysis7x / plugins / ports / reconstructed / jwildfire), lang/ (the compiler), loader (user folders,
                        cache), apophysis_depth (the built-ins' depth rule), workbench (the Formula Editor's scratch
                        slot, sources, the read-only policy), authoring (templates, snippets, the variable and
                        rename refactors, test rigs), completion (the dialect's names for the editor and the
                        reference), verify (one variation on both engines: the probe and the numpy-vs-GLSL check)
  render/               RenderSettings / RenderStats, CompiledFlame, tone map (numpy + GLSL), cpu_engine, codegen +
                        gpu_engine (moderngl), RenderService (worker thread, priorities, cancellation);
                        the final renderer: final_settings (options, tile plan) + memory (RAM / budgets), filters
                        (reconstruction filters, density estimation), denoise, control (cancel / pause), samplers
                        (+ cpu_workers: shared-memory worker processes), final_engine (tiles → filter → tone map →
                        denoise) + preview_canvas, output (formats, metadata) + png_tiff / exr encoders, report/
                        (model, writers, render_facts, fractal_facts: the details file in md / txt / html and the EXR
                        attributes), estimate (time estimate), units (shared formatting), final_service (FinalRenderJob)
  model/                Qt-free data: colours, stops, Gradient, simplification, adjustments, node operations
  formats/              one module per file type + registry; textfile.py / ufparams.py do in-place text edits
  library/              generic library: Catalog (gradient / fractal file knowledge), roots (QSettings), scanner,
                        model/filter/tree, controller, menus, dialog, panel
  imaging/              decoders/plugins, SVG rasteriser, palette extraction, colour ordering
  widgets/              GradientStrip, NodeBar, GradientEditor, position mapping, run-time painted icons (+ glyphs),
                        TriangleView (the editor canvas), ValueTable (name / value lists with drag editing),
                        PaletteSlider, Timeline (the animation timeline), actions / layouts / silent helpers,
                        BaseCodeEditor (line numbers, find / replace, line edits, completion with a pluggable
                        completer) → CodeEditor (the script editor: Python highlighting and completer) and
                        FormulaCodeEditor (C dialect highlighting and completer), CompletionPopup, FindBar,
                        GradientBar (the Formula Editor's clickable gradient swatch), CollapsibleSection, logo (the
                        application's mark — docs/logo.md, renders in logo/)
  scripting/            the scripting engine (Qt-free): api (the objects and functions scripts see), runner (stoppable
                        execution with line-numbered errors), docs (the reference database behind completion and the
                        help tabs), completion (type-aware completion / context help), generate (Flame → Script),
                        templates (+ builtin_templates/*.py)
  ui/                   .ui loader, background tasks, MainWindow, FractalDocument (undo history), FractalViewport +
                        ViewGeometry (image framing, view vs. camera pan/zoom), ViewerBar (zoom + image size),
                        SettingsPanel, FractalLibraryPanel, ThumbnailProvider, RenderStatus (status bar),
                        GradientLink, FormulaBrowser, LibraryHost (shared library-pane wiring),
                        EditorWindow (+ editor_context, editor_actions, editor_operations, editor_panels and
                        editor_value_tabs: the tabs, live_preview: the mini preview shared with the animation),
                        AnimationWindow (+ animation_document, animation_panels, animation_playback),
                        JobWindowBase → RenderWindow and AnimationRenderWindow (+ animation_render_panels),
                        FileActionsBase + the fractal / gradient file actions, GradientDocument,
                        GradientLibraryWindow, RenderWindow (+ render_size_panel, render_quality_panel,
                        render_output_panel, render_progress), ScriptEditorWindow (+ script_drawer: the Context /
                        Reference / Info / Templates tabs, script_runner: the worker thread),
                        FormulaEditorWindow (+ formula_session: the formula being edited and its background
                        compiles, formula_editor_actions, formula_list_panel, formula_editor_panels: preview
                        options / variable tools / presets, formula_drawer: reference / compiler output / probe,
                        formula_origins: the origin classification and row colours shared by every formula list)
tools/                  import_apo_plugins.py (plugin sources → library), apo_decompile.py (plugin DLLs → formulas),
                        import_jwf_variations.py + jwf_translate.py (JWildfire *Func.java → formulas), render_logo.py,
                        scripting_reference.py (docs/scripting.md from the scripting documentation database)
tests/                  pytest suite
samples/                sample flames / gradients / images used by the tests, plus
samples/aposource/      the Apophysis 7x source and plugin code, kept for reference (not scanned by the tests)
```

### Notes for tuning
* Flame and UF palettes contain 256 entries. On import, stops that a straight blend
  between their neighbours would reproduce within `IMPORT_SIMPLIFY_TOLERANCE`
  (per channel, 0–255) are dropped so the node bar stays usable. Set it to `0` to keep every stop.
* `IMAGE_COLOR_COUNT` controls how many nodes an image produces; `IMAGE_ORDERING`
  picks how they are sequenced (`path` = smooth nearest-neighbour walk from the darkest
  colour, or `luminance` / `hue`).
* All loaders already return *every* gradient in a file; only the UI picks the first.
* HEIC and JPEG XL need `pillow-heif` / `pillow-jxl-plugin`; if either is missing those
  extensions simply disappear from the Open dialog, and opening such a file by path
  reports which package to install.
