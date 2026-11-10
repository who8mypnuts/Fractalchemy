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
* Menu bar: *File* (Open Fractal…, **Open Recent ▸**, **Recover ▸**, Save Fractal `Ctrl+S`, Save Fractal As ▸ New Entry /
  New File `Ctrl+Shift+S` / Into Existing File, Exit), *Edit* (Undo `Ctrl+Z`, Redo `Ctrl+Shift+Z` — both named after the
  step, "Undo Gamma" —, Copy Parameters `Ctrl+Shift+C`, **Copy Parameters As ▸** Fractalchemy / Apophysis / Chaotica, Paste
  Parameters `Ctrl+Shift+V`, Edit Fractal Library…), *View* (Show/Hide Fractal Library `Ctrl+L`,
  Refresh `F5`, Thumbnails, Show/Hide Inspector, **Compare with Original**, Zoom to Fit / 100%, Guides, **Theme ▸**, Toolbar,
  Status Bar), *Windows* (Transform Editor `F4`, Gradient Library `F6`, Animation `F9`, Random Batch `F7`, Mutate & Breed
  `Ctrl+M`, Script Editor `F8`, **Scripts ▸**, Formula Editor `F10`, 3D Editor `F11`, Fragments `F12`, Render Image…
  `Ctrl+R`), *Help* (**Command Palette…** `Ctrl+K`, Formulas…, About).
* **Command palette** (`Ctrl+K` in every window): type a few letters of any command — the window's own menus, the main
  window's, *Open Recent*, *Recover*, the themes, "Run template: …" — and press Enter. Matching is fuzzy (letters in
  order, word starts count most); with nothing typed the commands you used last come first; unavailable commands are
  shown dimmed.
* **Nothing unsaved is lost.** A few seconds after edits pause, an unsaved fractal is copied to the recovery folder
  (the per-user cache, never next to your files); if Fractalchemy does not close properly, the next start offers to
  restore it (*Restore* / *Not now* — it stays under *File ▸ Recover* — / *Discard*), modified and still linked to its
  file entry. Showing another fractal never asks, but puts the unsaved edits on the **shelf** (*File ▸ Recover*, the 20
  newest). Quitting with unsaved fractal edits asks *Save / Discard / Cancel*.
* **Open Recent** lists the last ten fractals opened or saved (file and entry); missing files are shown disabled.
* Toolbar: **Open**, **Save**, **Save As ▾** (new entry in this file / new `.flame` or `.fa` file / into another file),
  **Undo**, **Redo**, **Copy Parameters** (the whole fractal, gradient included, as `.fa` text), **Paste Parameters**
  (`.fa`, Apophysis `<flame>` XML or a Chaotica world from the clipboard, undoable), **Transform Editor** (`F4`),
  **Gradient Library**, **Animation** (`F9`), **Random Batch** (`F7`), **Mutate & Breed** (`Ctrl+M`),
  **Script Editor** (`F8`), **Formula Editor** (`F10`), **3D Editor** (`F11`), **Fragments** (`F12`),
  **Render Image** (`Ctrl+R`).
  Nothing is ever written unless you save: edits only change the preview, the title shows `*`, and Save / Save As
  let you keep as many versions as you like.
* **Open Fractal…** shows the file's first flame and lists *all* of the file's flames in a temporary section at the
  top of the Fractal Library, above a separator; opening another file replaces it. The section follows the file:
  rename / delete / duplicate its flames there, or drag them into library files.
* **Undo / Redo** cover every edit to the fractal — camera moves (Ctrl+drag / Ctrl+wheel / double-click) and gradient
  edits made in the Gradient Library; a drag or a slider sweep is one step, and an edit that changes nothing is no step at
  all. The title shows `*` while the fractal differs from what was loaded or saved — undoing back to that state clears
  it. The Inspector's **History** tab lists every step by name and jumps to any of them.
* **Before / after**: hold `\` to see the fractal as it was loaded (or last saved), `Shift+\` as it was before the last
  edit; *View ▸ Compare with Original* keeps the comparison on. The other picture is rendered once with the same view
  and kept, so pressing again is instant.
* **Save** writes the flame back into its own entry (`.fa`, `.flame`); for a Chaotica world or a flame without a file
  it becomes *New File…*. **Save As ▸** (File menu and the toolbar button) has the same three flavours as the
  Gradient Library, so one `.fa` (or `.flame`) file can collect many fractals: *Add to This File as New Fractal…*
  (`Ctrl+Shift+A`, appends under a name you choose), *New File…* (`Ctrl+Shift+S`, `.fa` by default, also `.flame` /
  `.chaos`; an existing multi-fractal file is added to, never wiped), *Add to Another File…* (append to any `.fa` /
  `.flame`). Afterwards the document points at the saved entry, so the next Save is in place. Saving a flame that
  uses variations we can't render yet back into its `.flame` warns first, because those variations would be dropped.
* **Copy Parameters** puts the parameters (transforms, camera, colouring *and* gradient) on the clipboard as
  Fractalchemy text (*Copy Parameters As ▸* Apophysis `<flame>` XML or a Chaotica world); **Paste Parameters** accepts
  any of the three.
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
* **Inspector** (right, collapsible via its divider arrow or *View ▸ Show/Hide Inspector* `Ctrl+Shift+L`):
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
    Apophysis 7X `curves` are read, ours are saved as `fa_curves`). Colouring and curve edits change the picture at once:
    the render's histogram is kept and only tone-mapped again, at the quality already reached (refining carries on).
  * *History* — every undo step of the fractal by name ("Gamma", "Triangle 3", "Script: Random rotate", "Adopt
    mutant"), the loaded state at the top, the current one in bold, undone steps dimmed, the saved state marked 💾. Click
    one to go back (or forward) to it; right-click to compare it with the current picture or copy its parameters.
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
  with the Gradient Library maximised. The library also **follows the fractal**: after undo / redo, Paste
  Parameters, a script, or adopting a mutant or child, it shows the fractal's new gradient at once. Neither
  switching fractals nor following asks about unsaved gradient edits: they were already applied to the fractal
  and live in its undo history.

### Themes
*View ▸ Theme* recolours the whole application at once, every window included, and remembers the choice:

* **System** (the default) keeps the platform's own look. Its editor colours still adapt: on a dark desktop the code
  editors, the formula lists and the painted icons take readable dark-theme colours.
* **Nord** and six variations: *Nord*, *Nord Deep* (darker Polar Night), *Nord Frost* (deep-blue accent),
  *Nord Aurora* (warm accents), *Nord High Contrast*, and two light ones, *Nord Snow Storm* and *Nord Light Frost*.
* **Dark**: Fractalchemy Dark, Dracula, Monokai, One Dark, Tokyo Night (+ Storm), Catppuccin Mocha / Macchiato / Frappé,
  Gruvbox Dark, Solarized Dark, Ayu Mirage, Everforest Dark, Kanagawa, Rosé Pine, Material Palenight, Night Owl,
  Oceanic Next, Tomorrow Night, GitHub Dark, Darcula, Iceberg, High Contrast Dark.
* **Light**: Fractalchemy Light, Solarized Light, Gruvbox Light, Catppuccin Latte, One Light, Rosé Pine Dawn,
  GitHub Light, Paper (high contrast).

Each theme is built from its published palette, and **readability is a rule, checked for every theme by the
test-suite**: text, syntax colours, hints, formula-origin tints, selections and glyphs all meet WCAG AA contrast
(4.5:1 for text, 3:1 for comments and hints). Where a published colour falls short (many themes' own comment greys do)
it is nudged just far enough. The code editors (Script, Formula, Fragments), the completion popups, the help drawers,
the Transform Editor's lists, the log and the toolbar icons all follow the theme live. The drawing areas (the
Transform Editor's canvas, the previews, the timeline, the Mutate & Breed grid) stay dark on every theme, tinted by
it, because the classic transform colours need a dark ground. Rendered fractals, gradients and swatches are never
themed. The Fragments window can pin a theme to its editors (*Edit ▸ Editor theme*); it follows the application by
default.

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
  [docs/formulas.md](docs/formulas.md). Some 850 are bundled: the flam3 classics and Apophysis 7X built-ins,
  every Apophysis plugin whose source was available, plugins that only existed as (mostly 32-bit) DLLs,
  reconstructed from their machine code, and 280-odd variations translated from JWildfire
  (`tools/import_jwf_variations.py`; the report in [docs/jwildfire_import.md](docs/jwildfire_import.md) lists
  what could not be translated and why). Each is defined once and compiled for *both* engines from the
  Apophysis plugin C dialect (or written natively in Python + GLSL), and the test-suite checks that numpy
  and GLSL agree on every one. Your own formulas go into the per-user formulas folder (*Help ▸ Formulas…*
  shows it, together with everything loaded and why anything failed to load) — the **Formula Editor** (`F10`)
  writes them there and shows them working while you type. Formulas a flame uses that are not available are
  listed in the status bar and ignored.
* Tunables in `config.py`: `PREVIEW_PASSES` / `PREVIEW_QUALITY` (defaults for the Inspector's Image tab),
  `INTERACTIVE_SCALE`, thumbnail size / quality.

| Fractal format | Read | Entries | Rename | Add / remove / replace |
|---|---|---|---|---|
| `.flame` (Apophysis / flam3) | ✓ | many | ✓ | ✓ (in-place text edits; unknown data survives) |
| `.fa` (Fractalchemy, JSON) | ✓ | many | ✓ | ✓ |
| `.chaos` (Chaotica) | ✓ (tone curves included) | many | ✓ | add only (a new `<IFS>`; entries are never rewritten, so Chaotica-only data survives) |
| `.faanim` (Fractalchemy animation, JSON) | ✓ (Animation window) | one animation | – | ✓ |

Writing a flame into a Chaotica world keeps what Chaotica can hold: the pre affine is folded into the affine, `zoom`
into the scale, and the final transform becomes the camera's viewing transform; the filter radius, contrast, the alpha
curve, the 3D camera and direct colour (`var_color`) have no Chaotica equivalent. Tone curves are read and written as
Chaotica's `overall` / red / green / blue curves. `tests/test_format_roundtrip.py` checks every format against these rules.

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
  variations in the corner; the status bar shows the cursor position, the zoom and what a drag did. **Grips** around the
  selected triangle (*View ▸ Show grips*, on by default): drag the round one above it to rotate, a square one at its
  corners to scale — about the pivot, Shift snapping — and double-click one to reset the rotation / scale.
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
  dragged, double-click resets the default, *Show all variables* lists every parameter of every formula. Values stay
  within what the formula declares — its range (a cyclic one wraps), whole numbers for integers, never 0 where 0 is not
  allowed — and the status bar says when a typed or dragged value was adjusted (files, scripts and paste keep any value).
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
range persist; a formula you add later starts out checked. **Symmetry** adds flam3's symmetry transforms to every
fractal: none (the default), flam3's own random pick, a left–right mirror, N-fold rotation or both, with an order
range.

### Mutate & Breed window
*Windows ▸ Mutate & Breed…* (`Ctrl+M`, the double helix on the toolbar) explores relatives of the fractal shown in the
main window, as Apophysis's *Mutate* does. It is a 3 × 3 grid: the current fractal in the centre, eight offspring around
it, each rendered small (at thumbnail priority, so the viewport always comes first) with a caption saying what changed
and a tooltip listing every change.

* **Mutate**: eight mutants. **Strength** (a little … wildly); **what may change**: triangles, variations (swap, add,
  drop), variation weights, parameters (declared ranges respected, integer parameters stay integers), transform weights,
  colours, the **gradient** (hue, rotation, saturation / luminance, a new harmony), xaos, adding / removing transforms,
  the final transform, and Apophysis's classic **drift** towards a random flame. A **trend** variation is preferred by
  swaps and additions; *Same number of transforms* and *Keep symmetry* (transforms with colour speed 0 are left alone)
  are Apophysis's switches. Mutants keep the parent's camera.
* **Breed**: eight children of the current fractal (parent **A**) and a second parent **B**. B can be the fractal
  shown now (*Use current fractal*, then show another one as A), a file (*Open…*), a Fractal Library row dropped on
  its slot or chosen with the row's *Breed with Current Fractal*, or any cell (*Use as parent B*). **Combine**: *alternate* (each transform from one parent or the other),
  *interpolate* (every number blended, 25–75 %), *union* (all the transforms of both, weighted 30–70 %) or *mixed*.
  The **gradient** comes from A, B, a blend or either; the **camera** and colouring from A, B, or re-framed on the child.
* **Explore script**: eight variations of the Script Editor's live script (a script whose `param()` controls are live):
  its parameters nudged around the current values (or drawn anywhere in their ranges, or only new random numbers), each
  run on the fractal as it was before the script. **Spread**, **where**, *new random numbers too* and which parameters may
  change are the options. Clicking a cell hands its values to the Parameters tab — the fractal follows, still the
  script's one undo step; *Make it the fractal* in the cell's menu adopts the flame as a separate step instead. The
  Parameters tab's *Explore…* opens this tab.
* Offspring that blow up or collapse are rolled again. **Click a cell** (or press its number, 1–9) to make it the
  fractal: **one undoable edit** that keeps the file link and the name (Ctrl+Z in either window goes back, Save
  overwrites the entry), and the grid regenerates around it. The Gradient Library shows the new gradient straight away,
  without asking about unsaved gradient edits. A cell's right-click menu can also *Open as new unsaved fractal*, *Use as
  parent B* or *Copy parameters*. **New offspring** (`Space` in the grid, or `F5`) rolls again.
* The window follows the main window: choosing another fractal regenerates at once, edits regenerate once they pause,
  and a hidden window only catches up when it is shown again. The options, the tab and the layout persist.

### Script Editor window
*Windows ▸ Script Editor* (`F8`, the script-sheet button on the toolbar) opens a tool window for **scripting the
fractal in Python** — the Apophysis script editor, but with Python and everything Fractalchemy can edit: transforms
(affines, weights, colours, the active transform), variations and their parameters (every loaded formula, plugins
included), the gradient and palette, the chaos / xaos matrix, the camera (2D and 3D), the tone mapping, plus
prompts, random numbers and live previews. Closing the window hides it; the script, the drawer state and the
window layout are remembered between runs. See [docs/scripting.md](docs/scripting.md) for the full reference.

* **Toolbar**: New / Open / Save / Save As (`.py` files) · **Run** (`Ctrl+Enter`) / **Stop** (`Shift+Esc`) · **Record ▾**
  (`Ctrl+Shift+R`) ·
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
  whether it prompts or animates, its parameters, and the last run (time, result, transforms before → after).
  **Parameters** — one control per `param()` declaration of the last run (below). **Templates** — 36
  built-in templates by category (*Random rotate all transforms*, *Normalize weights*, *Add random transform*,
  *Julia mutation*, *Make rotational symmetry*, *Spiral*, *Tile the plane*, *Gnarl*, gradient, xaos and camera
  helpers, *Random flame explorer*, *Flame report*, *Build a flame from scratch*, …) plus *My templates*: save the
  current script as one, overwrite, rename, delete; load, insert at the cursor, or load-and-run. User templates are
  plain `.py` files in the per-user scripts folder (*Open folder*), so they can be shared. **Pin** a template (★) and it
  appears in the main window's **Scripts ▾** menu: one click runs it on the fractal with its saved parameter values,
  without opening the editor (*Adjust Parameters…* opens its Parameters tab).
* **Live parameters**: a script declares tunable inputs instead of asking for them —
  `angle = param('Angle', 30, min=-180, max=180)` (a slider), `param('Copies', 3, min=1, max=12)` (an integer slider),
  `param('Keep colours', True)` (a check box), `param('Palette', 'Fire', choices=list_gradient_presets())` (a dropdown),
  `param('File', '')` (text). After a run the Parameters tab shows the controls; moving one runs the script again from
  the fractal as it was before the run, with the same random numbers (*New seed* rolls new ones; *Keep seed on Run* makes
  Run repeat them), and the fractal follows live while the whole session stays **one undo step**. Changing the fractal
  in any other way ends the session (the values stay; Run applies them again). Scripts with side effects — questions,
  messages, `update()` / `sleep()`, writing files, imports beyond `math` / `colorsys` / `random` … — are not re-run live:
  their controls set the values the next Run uses. *Set as defaults in script* writes the values into the `param()`
  calls; *Save as Template* offers to. Right-click a control for *Reset to default*, *Animate…* (Animation keyframes of
  the result while that parameter sweeps) and *Go to declaration*. The values you change are remembered with the draft.
  Twelve built-in templates declare parameters (*Random rotate*, *Warm / cool shift*, *Make rotational symmetry*,
  *Julia mutation*, *Live kaleidoscope*, …).
* **Record** writes the code for what you do anywhere else: every edit — camera drags and zooms, the Image tab, the 3D
  camera, colouring and curves, the Gradient Library, the Transform Editor, Paste Parameters, adopting a mutant — appends
  the statements that reproduce it at the cursor (`camera.zoom = 1.25`, `coloring.gamma = 3.5`,
  `gradient.set_stops([...])`, `transforms[1].coefs = (…)`). A drag or a slider sweep is one statement; Undo in the main
  window removes the statement it had just written (Redo puts it back); each statement is one step of the editor's own
  undo; the editor never takes the focus. *Record ▾ Changes* writes changes instead of values (`camera.zoom += 0.25`,
  `transforms[0].rotate(15)`, `gradient.adjust_stops(hue=30)`) so the recording works as a filter on any fractal. Every
  statement is checked by running it, so a recording always reproduces the edits. Recording stops when a script runs;
  the main window's status bar shows **● Recording script** meanwhile (click it to stop).
* **Console** (the `>>>` line under the output): type a line and press Enter — an expression shows its value, variables
  carry over to the next line, a line that changes the fractal is one undo step ("Console: camera.zoom += 1"); ↑ / ↓ walk
  the history. While recording, console lines go into the script as typed.
* **Run on Many Fractals** (*Script* menu, the main window's *Scripts ▾*, the Fractal Library's *Run Script on
  Selection…*): the script (or any template) applied to the library selection, every fractal of a file, the Randomly
  Generated batch or the current fractal, the results added to a `.fa` / `.flame` / `.chaos` file — never over the
  fractals it reads. Names (`{name} · {script}`), random numbers (the same for all, or new for each) and what to do when
  one fails are options; Pause and Stop work as in the render windows, and a stopped batch keeps what it made.
* **Running**: a script runs on a worker thread against a copy of the fractal; `print()` streams into the output
  panel, `param()` declares a control (above), `input_text()` / `input_number()` / `confirm()` pop up dialogs,
  `message()` shows a box, `update()` pushes
  the current state into the main window and re-renders (with `sleep()` that makes animation previews), `progress()`
  feeds the status bar, `stop()` ends the script keeping its changes. When it finishes the fractal takes the result
  as **one undo step**; an error leaves the fractal untouched (intermediate updates are rolled back). **Stop** ends
  any script — `while True:` loops, sleeps and open prompts included.
* **The API** (Python, no imports needed): `flame`; `transforms` / `transform` (the active one) with `a`–`f`,
  `coefs`, `post`, `weight`, `color`, `color_speed`, `opacity`, `variations[…]`, `params[…]`, `xaos`, and
  `pre`, `rotate()`, `scale()`, `translate()`, `rotate_around()`, `multiply()`, `flip_*()`, `set_variation()`, …;
  `add_transform()`, `add_random_transform()`, `remove_transform()`, `copy_transform()`, `set_active_transform()`,
  `set_final_transform()`, `normalize_weights()`, `add_symmetry()`, …; `camera` (`x`, `y`, `scale`, `zoom`, `rotate`, size,
  the 3D
  camera, `fit()`, `zoom_by()`, `pan()`); `gradient` (`colors`, `stops`, `set_stops()`, `random()`, `preset()`, the
  Gradient Library's node operations and sliders — `adjust_stops()` exactly as it applies them —, `load()` from any
  gradient file); `xaos` (`set()`, `matrix`, `chain()`, `isolate()`, `from_function()`, `randomize()`); `coloring` (with
  `curve()` / `set_curve()`); `param()`; `new_flame()`, `random_flame()`, `load_flame()`,
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

### 3D Editor window
*Windows ▸ 3D Editor* (`F11`, the cube on the toolbar) renders the fractal as a **lit solid** — the point cloud
treated as a surface, in the manner of JWildfire's solid rendering — with materials per transform, distant lights
with shadows, ambient occlusion and fog, and a camera to orbit it. A tool window like the others: closing it
hides it; the layout and the scene being edited are remembered between runs. It changes nothing the other
windows show: it **pulls** a copy of the main window's fractal (**Use main fractal**, `Ctrl+U` — also done by
itself the first time the window opens with a fractal in the main window) and can **push** one back (**Send
to main window**, `Ctrl+Shift+U`, the 3D camera set here going with it). **Follow** keeps the scene in step with
the main window as the fractal is edited there, re-pulling a moment after the edits pause (the camera orbited
here is kept). The plan behind it, and the phases still to come (meshing and export, Holon IFS, HDRI
environments), is `docs/3d-editor-plan.md`.

* **The viewport** renders progressively through the shared render service — the GPU solid renderer
  (`render/gpu_solid.py`: G-buffer, shadow maps and shading as OpenGL passes) when there is one, the numpy one
  (`solid/`) otherwise; both give the same picture. **Left-drag orbits** (the flame's pitch and yaw),
  **right-drag pans**, the **wheel zooms**, `Ctrl`+wheel changes the perspective, **double-click** (or **Reset
  view**, `Home`) goes back to the camera the fractal arrived with. While dragging, the view renders at half
  size and one pass; the full render follows when the mouse rests. Every move is an undo step (a drag is one),
  written to the flame's own 3D camera fields, so a flame sent back to the main window looks the same there.
  The **Points** toggle shows the palette-coloured point cloud unlit — a quick look at the shape.
* **Render**: *Solid* / *Points* display, the viewport's **preview quality** (Draft / Normal / Fine: samples and
  supersampling), the **density threshold** (a pixel needs this many samples to count as surface — the thin haze
  a flame's blur variations scatter about lands in pixels with one or two hits, a surface collects many, so 3
  removes the dust), normal **smoothing**, **ambient occlusion** (radius, intensity, samples, falloff) and
  **fog** (start / end as fractions of the depth range, colour). **Camera**: pitch / yaw / tilt in degrees,
  perspective, distance, zoom, as numbers. **Materials**: one per transform (the final transform takes the last)
  — colour from the palette or a fixed one, diffuse, ambient, specular and shininess, highlight colour, light
  wrap, *Copy to all transforms*. **Lights**: up to eight — **distant** lights placed relative to the camera
  (altitude above the view plane, azimuth around it, so they turn with the view) with a **shadow** each (a shadow
  map rendered from the light; darkness and softness), or **point** lights placed in the fractal's space (x, y, z,
  a falloff radius — inverse-square, no shadows), colour and intensity. **Environment**: the background colour
  (also the ambient light's colour) and whether it shows (off: transparent renders), ambient strength, exposure.
  The flame's **tone curves** (overall and per channel) apply to solid renders too, so they match the 2D view.
* **Scenes**: the flame, materials, lights, environment and renderer settings together are a *scene*, saved as a
  **`.fa3d`** file (JSON; the flame inside is the `.fa` format's) with **New / Open / Save / Save as** on the
  toolbar (`Ctrl+N` / `Ctrl+O` / `Ctrl+S` / `Ctrl+Shift+S`). The window asks before discarding unsaved changes;
  the title shows the file and a • when modified.
* **Render…** (`Ctrl+R`) opens the **Render 3D Image** window: the Render Image window's size and output panels
  (every format, bit depth, transparency, embedded parameters, *Save parameters* writes the `.flame` and the
  `.fa3d` beside the image) with its own quality — samples per pixel, passes, supersampling, AO samples — and the
  same Start / Pause / Stop life cycle on a worker thread with its own engine (the GPU when available), a live
  preview and a link to the file when done.
* **Mesh**: turns the fractal into a printable object. *Generate mesh* captures orbit points (100 k – 8 M), builds a
  voxel **density grid** (16 – 512 voxels along the longest side) and extracts the **isosurface** at a threshold you
  set on a log-**histogram** of the density (drag the marker: what is denser becomes solid; Gaussian smoothing,
  dilate / erode and vertex colours from the palette are the other knobs). The surface is *naive surface nets*
  — no marching-cubes tables, no ambiguous cases (diagonal voxel patterns are resolved first), watertight by
  construction. Two meshes come out: the **full** one (every triangle) and the **clean** one at a repair level —
  *simple* (weld, drop debris, consistent outward orientation), *aggressive* (largest piece, fill holes,
  Taubin smoothing, decimation to a target face count by quadric edge collapse — the built-in batched collapser,
  or `fast-simplification` when installed) or *remesh* (the voxel occupancy closed and cavity-filled, the last
  resort). Each carries a **print report**: pieces, open and non-manifold edges, orientation, watertight, volume,
  area, size, a thin-wall estimate, a sampled **self-intersection** count (nearby triangle pairs tested
  edge-against-triangle), and a recommendation. The capture is cached, so changing the threshold or the
  clean-up and regenerating takes a moment. *Show* switches the viewport between the solid render and either
  mesh — drawn with the same lights and materials (points sampled on the faces, smooth-shaded), so the mesh lands
  over the render it came from.
* **Instances** (the *Holon IFS*, in the manner of Xenodream): meshes placed at the points of a fractal's orbit, each
  turned and scaled by the orbit's accumulated **frame** — the product of the transforms' local Jacobians along
  the way (exact for affine transforms, sensible for `spherical`, `julia3D` and the rest; or *scale only* to keep
  them upright). **Assets** are primitives (sphere, cube, torus, tetrahedron, icosahedron, cylinder, with a detail
  level; `dla` grows a coral by diffusion-limited aggregation — an asset generator: grow once, instance many
  times), imported meshes (OBJ / STL / PLY / glTF / USD) or the Mesh tab's clean mesh saved as a PLY. An
  **instancer** picks an asset and a fractal — the scene's, or an **own 3D IFS** edited in a table, one row per
  transform as a 3D affine map (position, rotation, scale, weight, colour; *Add* / *Remove* / *Starter IFS* / *Send
  to main window* — it is a normal flame underneath: `linear3D` + `zscale` + `ztranslate` + `post_rotate_x/y`) —
  in **chaos** mode (N orbit samples, frames over the last *depth* transforms, so the sizes are those of depth-*n*
  holons) or **tree** mode (every composition of the transforms to *depth*, every level or the deepest only —
  deterministic and gap-free), with a base size, a size falloff, a minimum size, a cap, a colour (the orbit's
  palette colour, the asset's own colours or a fixed one) and a material. The instances are drawn and rendered
  with the fractal — same G-buffer, lights, shadows and ambient occlusion, on both engines — or alone (*Show the
  fractal itself* off).
  **Use as formula** turns an asset into a variation, `mesh_<name>`: its points lie on the mesh's surface (the
  triangles and an area table ride in the parameter texture, so it runs on both engines), usable in *any* flame
  from the Transform Editor — a transform that *is* a smiley face. The source is saved to your formulas folder.
* **Environment**: a background colour with ambient light, or an **HDRI** — `.hdr` (Radiance RGBE), `.exr`
  (scanline half / float, none / ZIP / ZIPS) or any LDR image — as **image-based lighting**: diffuse from the
  map's SH9 irradiance, reflections from prefiltered copies by material shininess, on both engines identically;
  rotation, light strength, and the map as the (optionally blurred) background or the colour instead. **Extract
  key lights** turns the map's brightest regions into distant lights (the first with shadows) — HDRI lighting
  with real shadows, without path tracing. A thumbnail shows the map.
* **3D formulas**: twelve JWildfire signed-distance solids are in the formula library — `box3D`, `rbox3D`,
  `ellipsoid3D`, `cylinder3D`, `torus3D`, `cappedtorus3D`, `capsule3D`, `cone3D`, `octahedron3D`, `pyramid3D`,
  `hexprism3D`, `rhombus3D` — volumes meant to be lit, and natural building blocks for 3D IFS; `affine3D` /
  `pre_affine3D` / `post_affine3D` (a full 3D affine map: translate, scale, rotate, shear — the transform of a 3D
  IFS); and the 3D crops `post_mandelbulb3d_crop`, `post_mandelbox3d_crop`, `post_aexion_crop` (Mandelbulb /
  Mandelbox / Aexion shells as solids).
* **Export**: the clean or the full mesh as **OBJ** (+ MTL), binary **STL**, binary **PLY**, **glTF** (GLB),
  **OpenUSD** (`.usda` always; `.usdc` / `.usdz` through `usd-core`), with **vertex colours**, or **UVs + a baked
  texture** (box / spherical / cylindrical projection, or an `xatlas` atlas when installed), or geometry only;
  in flame units or scaled to a size in **millimetres** (USD carries `metersPerUnit`); plus a **Blender scene
  script** (`name_blender.py`: `blender --python` imports the asset, builds the material from the colours or the
  texture, places the lights as Suns turned as in the editor, the camera as the flame's, the world colour) and a
  Markdown **report** beside the files. Every writer has a reader (`solid.io.read_mesh`) and the tests round-trip
  them all. **Instanced scenes** export either *instanced* — USD `PointInstancer` (positions, orientations,
  scales, one prototype per instancer), glTF `EXT_mesh_gpu_instancing`, and a Blender script that places the
  instances with a Geometry Nodes *Instance on Points* modifier from a JSON of positions / rotations / scales
  (formats that cannot carry instances get the baked mesh) — or *baked* into one mesh in any format.

### Fragments window
*Windows ▸ Fragments* (`F12`, the code sheet with a shard on the toolbar) is **Fragmentarium** inside Fractalchemy:
fractals written as GLSL fragment shaders — Mandelbulbs, Mandelboxes, kaleidoscopic IFS, escape-time sets, feedback
systems — edited, tweaked and rendered on the GPU. It reads Fragmentarium / FragM `.frag` files unchanged (their
directives, `#include`s, annotated uniforms and `#preset`s), ships FragM's example library and include files
(*Library ▸ Examples*, 232 fragments in 18 categories), and saves `.fafrag` / `.frag`. A tool window like the others:
closing hides it; layout, options and tabs are remembered. See [docs/fragments.md](docs/fragments.md) for the guide
and the language reference; the plan is `plans/fragments-plan.md`.

* **Source tabs** (left): a GLSL editor with highlighting (keywords, built-ins, directives, the `slider[…]` /
  `color[…]` / `checkbox[…]` / `menu[…]` / `file[…]` annotations, dimmed presets), line numbers, bracket matching,
  completion, find / replace, *Indent script*, and *Edit ▸ Insert command* (every directive, special uniform, texture
  option and include). **Build** (`F5`) preprocesses, translates and compiles; *Auto-build* rebuilds a second after
  typing stops; *Show preprocessed source* shows the GLSL the driver saw with every line's original `file:line`.
* **Viewport** (middle): progressive subframe accumulation (*Subframe max* on the toolbar; 0 = keep going), at half
  resolution while a button is held. Two 3D navigation styles: **orbit** (the default — left-drag orbits the target,
  middle pans, right / wheel dolly, Shift+left looks around, numpad `1 3 7 9 4 6 8 2 .` views and a turntable) and
  FragM's **fly** (left-drag orients, Shift orbits the origin, Shift+Alt orbits the target, right-drag pans, both
  buttons or the wheel dolly); `W A S D R F` fly, `T G Y H` turn, `Q E` roll, `1 3 2 5` change the step, middle-click
  puts the *Target* on the surface under the cursor; for 2D fragments left-drag pans, right-drag and the wheel zoom,
  `A D W S Q E` pan and zoom. Esc toggles fullscreen. Buffer size: locked to the window, or a custom X × Y with an
  aspect lock. Overlays: a **mini-map** plan of the scene (`Ctrl+M`), **A/B compare** (freeze a reference, drag the
  divider), **Ctrl+drag** a region of interest for the render window, draggable **keyframe handles** on the camera path.
* **Parameters** (dock): collapsible sections or FragM's tabs per `#group`, a preset combo, sliders + spin boxes
  (9 significant digits, 18 for doubles, logarithmic when asked; arrow keys nudge — Shift ×10, Ctrl ×0.1; MIDI knobs
  and gamepad sticks can drive them through *Windows ▸ Controllers…*), vectors
  (unit directions renormalise), colours with the live colour picker, menus, check boxes, texture files — each with a
  **lock** (the value baked into the shader; faster; *Build needed*). Unused parameters (optimised away by the
  compiler) hide unless locked; pinned ones gather in a **★ Favourites** group. `F1` reset, `F2` / `F3` copy / paste
  the settings text, Shift+`F3` paste the editor's selection, `F4` group → preset, `F8` insert a preset (a
  `KeyFrame.nnnn` for 3D cameras), `F9` select the current preset in the source, `Ctrl+F9` a **preset gallery**
  (every preset rendered small); lock / unlock / reset a whole group. Every edit and every camera move is undoable.
  A **History** dock keeps thumbnails of earlier looks (by hand, automatically, and before every **Mutate** — a random
  nudge of the unlocked parameters by a chosen strength — or *Randomize*); click one to go back.
* **Log** (dock): parse / include / compile messages, clamped preset values, `#info` lines, and compile errors with
  the file and line they belong to — click one to open the file (bundled includes read-only) at that line; the
  editor marks the line. Rejected shaders are also written to `<cache>/Fractalchemy/glsl-failures/`.
* **Library** (dock, `Ctrl+L`): the bundled examples and your own folders of `.frag` / `.fafrag` files with search
  (names, `tag:`, `param:`, `include:`, presets, `#info` lines, stars) and an optional thumbnail view in three sizes
  (each fragment rendered once, cached on disk, captioned with the camera kind, preset and parameter counts);
  **favourites, ratings and tags** from a row's menu, a *Show* filter (favourites, recent, rated, 2D / 3D); drag a
  file onto the window to open it. A **Walkthrough** dock lists a fragment's `// STEP n:` comments (the
  *Fractalchemy Tutorials*) and its outline. *File ▸ New from template* starts from FragM's New 2D / New 3D or the other built-in
  starters (kaleidoscopic IFS, Mandelbox, 2D with a map, Shadertoy-style, buffer feedback, fast raytracer), or from
  your own templates.
* **Animation**: FragM's model — the 3D camera follows a Catmull-Rom path through `KeyFrame.nnnn` presets (`F8`
  inserts one; the paths are drawn over the viewport, dashed where the surface hides them), single slider components follow **easing curves** (`F7`: Qt's
  curves with period / amplitude / overshoot, loops, ping-pong, kept in `Range…` presets as FragM's twelve-field
  lines), a **timeline editor** shows both on one ruler, and an *All parameters* interpolation mode blends every
  numeric parameter between the keyframe presets too; a **graph editor** (values against frames, draggable curve
  handles, keyframe tracks) sits beside the timeline. *Progressive* / *Animation* modes, Rewind / Play / Stop
  (`F10` `F11` `F12`, Space), a time slider with keyframe marks, fps and length on the toolbar.
* **Render…** (`Ctrl+R`): FragM's hi-res / animation render as a job window on its own thread and OpenGL context —
  tiles with padding, subframes per tile, a frame range, every host image format (16-bit PNG / TIFF, OpenEXR half /
  float with the **depth buffer as Z**), parameters embedded under FragM's `frAg` key, `.fragparams` and the fragment
  with its includes saved beside the image (FragM's autosave), ffmpeg video afterwards, pause / stop / save
  incomplete; **stereo** pairs (anaglyph / side by side) and **360°** equirectangular panoramas; a **region** of the
  frame at full resolution. A **render queue** runs several snapshots one after another. *Batch render presets…*
  renders every preset or keyframe of a file; `tools/render_frag.py` does the same from the command line (what `.fqs`
  scripts were for), with `--tile-range` / `--assemble` / `--resume` for renders spread over machines or resumed.
* **Quality of life**: parameter filter box, per-parameter *Reset / Randomize / Copy / Paste / Pin*, *Randomize group*
  (`F6`), next / previous preset, a viewport context menu (copy image, screenshot, bookmark, reset camera, HUD,
  fullscreen, render, mesh), tab menu (close others / all, copy path, show in folder) and middle-click close,
  `Ctrl+E` editor pane toggle, editor font zoom, an accumulation progress bar in the status bar. **Editor**: inline
  diagnostics (wavy underlines, hover messages), hover signatures, Ctrl+click **go to definition** (into the includes
  too), **snippets with tab-stops**, **multi-cursor** editing (`Ctrl+Shift+D` / `L`), *Compare with original…* (a diff
  against the bundled example with *Revert*), **colour themes** (the application's: follow *View ▸ Theme*, or pin one to the fragment editors). **Sessions**: save / open the open tabs with their settings; an autosave
  every few minutes and *Recover last session* after a crash.
* **Tools**: a **Grading** page (exposure, Reinhard / filmic / ACES tone mapping, gamma, contrast, saturation, hue,
  vignette, invert, plus a post stack — bloom, chromatic aberration, grain, `.cube` LUTs — a display-pass stage,
  instant, saved with the fragment, applied to renders); **camera
  bookmarks** and **flight recording** (samples the camera while you fly and writes the keyframe presets);
  *Manual rendering* (FragM's manual mode); **Debug views** — the depth buffer as a picture and a **DE slice** heat
  map with contours for debugging estimators; a **Performance HUD**; **Colours from a gradient** (every colour
  parameter sampled along the Gradient Library's gradient or a file); a **DE Composer** (folds, transforms and a
  primitive as a recipe → a fragment with sliders, Menger / Sierpinski / Mandelbox presets); **Import from
  Shadertoy** (Image and Buffer A, channels to textures / feedback); sparse-block mesh export up to 4096³.
* **Primitives**: `#include "Primitives.frag"` — ~60 signed distance primitives (boxes, tori, cones, prisms,
  polyhedra, gyroids…), the boolean / smooth / repetition / twist operators and the box / sphere / Menger /
  Sierpinski / kaleido folds as plain GLSL; *Insert command* menus, a *Primitives playground* template, a *Primitives*
  example folder (gallery, booleans, Menger from crosses, Mandelbox from folds, domain repetition, gyroid, chain
  maille) and a *Distance Estimator Compendium* folder of parameterised fractal estimators (gaz, kamoshika, yonatan,
  Kali, Nameless, Kleinian, Lewpen, butadiene, Marble Marcher levels, mrange, iq's Apollonian), plus a *Fractalchemy
  Collection* (Nova, Magnet, Phoenix, a gathering Buddhabrot; Amazing Surf, ABoxMod1, FoldingIntPow, Juliabulb,
  Lambdabulb, Jerusalem cube, Mosely snowflake, sphere-inversion IFS, Koch snowflake 2D / prism / 3D tetrahedron,
  Apollonian gasket, Indra's Pearls in 2D and 3D, Kleinian limit sets in 2D and 3D, Dragon curves and a Dragon ribbon) on a `Triplex.frag`
  include, and four *Fractalchemy Tutorials* that explain themselves in `// STEP n:` comments.
* **Textures**: `file[…]` samplers (LDR through Pillow, `.hdr` / `.exr` float with per-channel selection, cube-map strips, integer samplers),
  `#TexParameter` filters / wrapping / anisotropy with mipmaps, a cache keyed by file and modification time.
* **Insert gradient…**: any gradient the host reads (the Gradient Library's current one, `.ugr`, `.map`, palettes,
  images) or a GIMP `.ggr` — with GIMP's exact blend shapes and colour spaces — as a `vec3 gradient(float t)`:
  exact segments, a sampled table or a PNG strip texture, optionally wrapped as the object colour or the sky.
  GIMP gradients open in the Gradient Library too.
* **Export mesh…**: the distance estimator sampled on a voxel grid **on the GPU** (the fragment's own shader with a
  probe `main`, vertex colours from `baseColor`), the host's surface nets, clean-up levels and print report, a
  preview, OBJ / STL / PLY / glTF / USD output, normals from the field's gradient, colours baked to a texture through
  generated UVs, a Blender import script, and *Send to 3D Editor* (a PLY asset on the Instances tab). **Export DE as
  code…** writes the estimator with its values baked in as GLSL, a Shadertoy, a Unity shader or an Unreal include.
* **Preferences…**: recent files, loop play, camera paths, 2D wheel mode, editor font, jump to error, reload on
  change, session autosave, autorun / auto-build, moveMain, `#define` locks, the compatibility layer, easing in presets, frame rate,
  refresh interval, interactive scale, a GPU load limit and pause-when-hidden, the Parameters layout, the navigation
  style, include paths, log to file, verbose. *Build ▸ Test GLSL versions* compiles at
  every version the driver offers; *Clear texture cache*; Help has the guide, the CLI, a welcome note and links.
* **Under the hood**: a second render service thread with its own OpenGL context runs the fragment engine
  (ping-pong accumulation surfaces that survive parameter edits for `DontClearOnChange` fragments, a program cache,
  a buffer-shader display pass, depth reads for the 3D pick, engine chores such as the version test as priority
  jobs); the legacy GLSL 1.10 / 1.20 the fragment world is written in is translated to 3.30 core so it runs on every
  modern context (`fragments/glsl_compat.py`); 225 of the 232 bundled examples compile, the rest fail in FragM too.
  Heavy fragments stay clear of the GPU watchdog: half-size rendering while the camera moves, subframes per image
  adapting to the refresh interval, and automatic **tiling** of a subframe that exceeds the time budget (the status
  bar shows *tiled n×n*).

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
  | `.ggr` (GIMP gradient; blend shapes and HSV segments baked into stops) | one | ✓ | – | ✓ |
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
* **Gestures** (as in Ultra Fractal / Apophysis): **double-click** the strip or an empty spot on the node bar to add a
  node there in the colour already there, which adds a handle without changing the gradient. With the bar focused
  (click the strip or the bar), **Delete / Backspace** remove the selected node, **← / →** nudge it by one index unit
  (0–399; **Shift** = 10) and **Enter** opens the colour picker. **Right-click** a node for *Add node*, *Add random
  node*, *Randomize node*, *Pick colour…* and *Delete node*; right-click empty space for *Add node here*. The panel's
  buttons, the keys and the menus share one implementation (`widgets/node_commands.py`).
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
docs/fragments.md       the Fragments window guide and the .frag language reference
docs/state-machines.md  every explicit state machine (generated from machines/specs.py) and the inventory of the rest
fractalchemy/
  config.py             tunables: app name/version, node counts, simplify tolerance, sizes, preview quality, recovery,
                        the Script Editor's live parameters and recording
  settings.py           QSettings identity
  autosave.py           crash-recovery files (Qt-free): the unsaved fractal of each running instance, the shelf of edits
                        left behind, and the write / read helpers the Fragments session autosave shares
  search.py             fuzzy matching (the command palette)
  machines/             explicit state machines (Qt-free): core (MachineSpec, Machine, strict mode for the tests) and
                        specs (every machine of the application: render jobs, script runs, live parameters, Mutate &
                        Breed offspring, fragment builds, animation playback, the render queue)
  animation/            keyframed animations: model (Animation / Keyframe), interpolate (alignment + blending),
                        format (.faanim), render (AnimationRenderSettings, frame names, the ffmpeg command),
                        render_job (the batch thread: one sampler for every frame, then ffmpeg)
  fractal/              the shared scene: Flame / XForm / Camera / Coloring, the variation registry (numpy + GLSL),
                        formats/ (.flame XML, .chaos, .fa), triangles (affine ⇄ editor triangle geometry),
                        triangle_drag (the mouse-drag maths), xform_ops (add / duplicate / link / delete transforms
                        with consistent xaos), random_flame (the Random Batch recipes, framing, the blow-up test),
                        blend (align + blend flames: animation frames, drift, interpolated children), mutation (the
                        mutation operators and mutants), breeding (alternate / interpolate / union children), symmetry
                        (flam3's symmetry transforms); variations also hold `constrain_param` (a parameter's declared
                        range / integer / non-zero rules, shared by the editors and the mutation engine)
  themes/               Qt-free themes: model (seed colours → every role, WCAG contrast rules enforced), catalog
                        (System + 38 themes), nord (the Nord family)
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
  scene3d/              the 3D Editor's scene (Scene3D: the flame, materials, distant lights, environment, renderer
                        settings) and the .fa3d file
  fragments/            the Fragments window's Qt-free core: preprocessor (FragM's directives and annotations, line map),
                        parameters / state (values, locks, settings text), files (include paths), glsl_compat (legacy GLSL →
                        3.30 core), camera (FragM's 2D / 3D controls as maths), presets, annotations, templates, examples
                        (the bundled library/ — FragM's Include/ and Examples/), document_format (.fafrag metadata,
                        .fragparams, the frAg image key), library_format, spline / easing / animation (the camera path,
                        the easing curves, frame values), render_settings + batch (the hi-res plan, the CLI's work),
                        textures (file[…] decoding, #TexParameter), gradient_glsl (gradients → GLSL), mesh (DE → voxel
                        grid → surface nets → files, dense or sparse blocks), preferences, const_fold, grading (the
                        display colour grading), shadertoy (the importer's converter), composer (the DE recipe → GLSL); gl/ (moderngl): engine + program cache, surfaces
                        (ping-pong accumulation), uniforms, passes, job (the render-service job with the watchdog
                        tiling), tasks (engine chores as jobs), textures (the GL cache), final + final_job (the hi-res
                        renderer and its thread), mesh (the DE probe), diagnostics
  solid/                the solid renderer on the CPU: View (the 3D camera as a view transform), GBuffer + ShadowMap,
                        shading (normals, ambient occlusion, lights, shadows, fog), SolidCpuJob (the engine job);
                        render/gpu_solid.py is the same pipeline as OpenGL passes. Meshing: capture (orbit points),
                        voxelize (density / colour grids, filters, histogram), isosurface (surface nets), mesh (Mesh,
                        weld / components / orient / holes / Taubin / quadric decimation / report, clean levels, remesh),
                        uv (projections, texture bake), mesh_preview (a mesh through the solid shader), holon (frames
                        along the orbit, chaos / tree instancing, primitives, the 3D-affine transform representation,
                        instance point clouds for the renderers, baking), pipeline (the stages and the exports), io/ (OBJ,
                        STL, PLY, glTF + instancing, USD + PointInstancer, Blender scripts, readers), hdri (.hdr / .exr
                        readers, the equirect environment map: SH9 irradiance, prefiltered levels, key lights),
                        mesh_formula (a mesh as a `mesh_…` variation)
  model/                Qt-free data: colours, stops, Gradient, simplification, adjustments, node operations, presets
                        (the named gradients)
  formats/              one module per file type + registry; textfile.py / ufparams.py do in-place text edits
  library/              generic library: Catalog (gradient / fractal file knowledge), roots (QSettings), scanner,
                        model/filter/tree, controller, menus, dialog, panel
  imaging/              decoders/plugins, SVG rasteriser, palette extraction, colour ordering
  widgets/              GradientStrip, NodeBar, NodeCommands (the node operations shared by the panel, keys and menus),
                        GradientEditor, position mapping, run-time painted icons (+ glyphs), windows (bring_to_front),
                        TriangleView (the editor canvas), ValueTable (name / value lists with drag editing),
                        PaletteSlider, Timeline (the animation timeline), actions / layouts / silent helpers,
                        BaseCodeEditor (line numbers, find / replace, line edits, completion with a pluggable
                        completer) → CodeEditor (the script editor: Python highlighting and completer) and
                        FormulaCodeEditor (C dialect highlighting and completer), CompletionPopup, FindBar,
                        GradientBar (the Formula Editor's clickable gradient swatch), CollapsibleSection, logo (the
                        application's mark — docs/logo.md, renders in logo/), theming (ThemeManager: applying a theme,
                        the palette, `on_theme_changed`, themed style sheets), theme_menu (View ▸ Theme), syntax (the
                        theme-coloured highlighter base), FlameGrid (the Mutate & Breed grid), CommandPalette (Ctrl+K)
  scripting/            the scripting engine (Qt-free): api (the objects and functions scripts see), runner (stoppable
                        execution with line-numbered errors), docs (the reference database behind completion and the
                        help tabs), completion (type-aware completion / context help), generate (Flame → Script),
                        codegen (numbers and blocks as code, flame equivalence), parameters (param() declarations,
                        coercion, live blockers, baking defaults), diff (the statements that turn one flame into another:
                        the recorder's code, values or changes, verified), explore (explorer variations, parameter
                        sweeps), batch (one script on many flames), templates (+ builtin_templates/*.py)
  ui/                   .ui loader, background tasks, MainWindow, FractalDocument (undo history), FractalViewport +
                        ViewGeometry (image framing, view vs. camera pan/zoom), ViewerBar (zoom + image size),
                        InspectorPanel (the Info + Image + History tabs; history_panel, undo_labels: the steps' names),
                        FractalLibraryPanel, ThumbnailProvider, RenderStatus (status bar), recent_files (Open Recent),
                        recovery (RecoveryKeeper: crash recovery and the unsaved-edits shelf), commands (the command
                        palette's commands and the Ctrl+K shortcut), script_tools (the main window's script features:
                        the Script Editor, the Scripts menu, the batch window, the recording indicator),
                        GradientLink, FormulaBrowser, LibraryHost (shared library-pane wiring),
                        EditorWindow (+ editor_context, editor_actions, editor_operations, editor_panels and
                        editor_value_tabs: the tabs, live_preview: the mini preview shared with the animation),
                        AnimationWindow (+ animation_document, animation_panels, animation_playback),
                        MutationWindow (+ mutation_panels: the Mutate / Breed / Explore options, grid_renderer: small
                        renders of in-memory flames through the render service),
                        JobWindowBase → RenderWindow and AnimationRenderWindow (+ animation_render_panels),
                        FileActionsBase + the fractal / gradient file actions, GradientDocument,
                        GradientLibraryWindow, RenderWindow (+ render_size_panel, render_quality_panel,
                        render_output_panel, render_progress), ScriptEditorWindow (+ script_drawer: the Context /
                        Reference / Info / Templates / Parameters tabs, script_runner: the worker thread,
                        script_editor_actions, script_output (the output panel and its live section), script_console,
                        script_parameters_tab + script_live (live parameters), script_recorder (Record), script_menu
                        (pinned templates), script_animate (Animate a parameter), script_batch_window (Run on Many
                        Fractals)),
                        FormulaEditorWindow (+ formula_session: the formula being edited and its background
                        compiles, formula_editor_actions, formula_list_panel, formula_editor_panels: preview
                        options / variable tools / presets, formula_drawer: reference / compiler output / probe,
                        formula_origins: the origin classification and row colours shared by every formula list),
                        fragments/ (the Fragments window: FragDocument with its parameter history and builds, TabManager,
                        FragViewport with the cameras, RenderDriver (what to render when), ParameterPanel + widgets,
                        GlslCodeEditor, LogPanel (with log-to-file), BufferSizeBar, actions / file_actions, library_panel
                        (the library dock + thumbnails), animation_controls / easing_dialog / timeline_window,
                        render_window + render_panels / batch_dialog, gradient_dialog, mesh_export_dialog + mesh_job,
                        preferences_dialog, help, grading_panel, camera_actions (bookmarks, flight recording),
                        de_slice_dialog, composer_dialog, shadertoy_dialog),
                        three_d/ (the 3D Editor: Scene3DDocument with its undo history, Viewport3D with the orbit rig
                        and the mesh display, the Render / Camera / Materials / Lights / Environment panels, mesh_panels:
                        the Mesh and Export tabs with the density histogram, instances_panel: assets, instancers and the
                        own-IFS table, jobs: MeshJob / ExportJob / MeshPreviewJob, SolidRenderWindow: the render to file
                        on its own thread)
tools/                  theme_snapshots.py (screenshots of the windows in chosen themes, for review),
                        state_machines.py (docs/state-machines.md from the machine specs; --check for the tests),
                        fragments_snapshot.py (the example fragments' parameter inventory fixture), render_frag.py (the
                        fragment batch renderer / checker),
                        import_apo_plugins.py (plugin sources → library), apo_decompile.py (plugin DLLs → formulas),
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
