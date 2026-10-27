# Fractalchemy
A fractal flame viewer and gradient editor growing into a full fractal editor. Today it browses libraries of
Apophysis / Chaotica / Fractalchemy fractals, renders them progressively in a GPU-accelerated viewport (with a
multithreaded CPU fallback), and edits, saves and converts gradients for a variety of fractal programs.
(Fractalchemy was previously called HueClid; the library folders saved under that name are picked up automatically on first run.)

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
  Parameters `Ctrl+Shift+V`, Edit Fractal Library…), … (Edit Fractal Library…), *View* (Show/Hide Fractal Library `Ctrl+L`,
  Refresh `F5`, Thumbnails, Show/Hide Settings Panel, Zoom to Fit / 100%, Toolbar, Status Bar),
  *Windows* (Gradient Library `F6`), *Help* (Formulas…, About).
* Toolbar: **Open**, **Save**, **Save As ▾** (new entry in this file / new `.flame` or `.fa` file / into another file),
  **Undo**, **Redo**, **Copy Parameters** (the whole fractal, gradient included, as `.fa` text), **Paste Parameters**
  (`.fa`, Apophysis `<flame>` XML or a Chaotica world from the clipboard, undoable), **Gradient Library**.
  Nothing is ever written unless you save: edits only change the preview, the title shows `*`, and Save / Save As
  let you keep as many versions as you like.
* **Fractal Library** (left pane, collapsible via the divider arrow or `Ctrl+L`): folders of `.flame`
  (Apophysis / flam3, legacy files included), `.chaos` (Chaotica) and `.fa` (Fractalchemy) files, each file
  expanding into its flames. Search box, collapse-all, and two view buttons: **list** or **thumbnails**
  (rendered on demand by the preview engine, at low priority so the viewport always comes first).
  Folders are watched, and the right-click menu / drag-and-drop file operations are the same as in the
  Gradient Library. It has its own folder list (*Edit ▸ Edit Fractal Library…*, or **+** / ✎ in the pane).
* **Viewport** (the centre): click a flame and it renders progressively in passes. The **Detail** box under it
  (Full / ½ / ¼) renders the preview at a fraction of the screen resolution — 4× / 16× faster while editing —
  and scales it up; the saved image size is untouched. The flame is framed as an
  *image* of the chosen **Image size** (dropdown under the viewer, far right: the flame's own size, common
  screen and print sizes, or Custom… with width × height). Changing it only changes the image's aspect and
  framing inside the viewer — never the window.
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
    and rotation boxes); **3D camera** (**X pitch** tilts about the horizontal axis, **Y pitch** about the vertical
    one, **yaw** spins the plane, plus perspective, z position, depth blur — Apophysis's `cam_*` attributes, so a
    2D flame becomes a tilted plane and variations with depth — `julia3D`, `curl3D`, `ztranslate`, `zcone`,
    `blur3D`, `zblur`, `zscale`, `pre_`/`post_rotate_x/y`, `linear3D`, … — show real 3D; Y pitch is saved as
    `cam_pitch_y`, which Apophysis ignores); **Coloring** (brightness, gamma, gamma threshold, vibrancy,
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
  [docs/formulas.md](docs/formulas.md). Some 570 are bundled: the flam3 classics and Apophysis 7X built-ins,
  every Apophysis plugin whose source was available, and plugins that only existed as (mostly 32-bit) DLLs,
  reconstructed from their machine code. Each is defined once and compiled for *both* engines from the
  Apophysis plugin C dialect (or written natively in Python + GLSL), and the test-suite checks that numpy
  and GLSL agree on every one. Your own formulas go into the per-user formulas folder (*Help ▸ Formulas…*
  shows it, together with everything loaded and why anything failed to load). Formulas a flame uses that
  are not available are listed in the status bar and ignored.
* Tunables in `config.py`: `PREVIEW_PASSES` / `PREVIEW_QUALITY` (defaults for the settings panel),
  `INTERACTIVE_SCALE`, thumbnail size / quality.

| Fractal format | Read | Entries | Rename | Add / remove / replace |
|---|---|---|---|---|
| `.flame` (Apophysis / flam3) | ✓ | many | ✓ | ✓ (in-place text edits; unknown data survives) |
| `.fa` (Fractalchemy, JSON) | ✓ | many | ✓ | ✓ |
| `.chaos` (Chaotica) | ✓ | many | ✓ | – |

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
fractalchemy/
  config.py             tunables: app name/version, node counts, simplify tolerance, sizes, preview quality
  settings.py           QSettings identity + one-time migration of HueClid settings
  fractal/              the shared scene: Flame / XForm / Camera / Coloring, the variation registry (numpy + GLSL),
                        formats/ (.flame XML, .chaos, .fa)
  formulas/             the formulas: builtin/ (native Python), library/ (the plugin dialect, one file each:
                        apophysis7x / plugins / ports / reconstructed), lang/ (the compiler), loader (user folders,
                        cache), apophysis_depth (the built-ins' depth rule)
  render/               RenderSettings / RenderStats, CompiledFlame, tone map (numpy + GLSL), cpu_engine, codegen +
                        gpu_engine (moderngl), RenderService (worker thread, priorities, cancellation)
  model/                Qt-free data: colours, stops, Gradient, simplification, adjustments, node operations
  formats/              one module per file type + registry; textfile.py / ufparams.py do in-place text edits
  library/              generic library: Catalog (gradient / fractal file knowledge), roots (QSettings), scanner,
                        model/filter/tree, controller, menus, dialog, panel
  imaging/              decoders/plugins, SVG rasteriser, palette extraction, colour ordering
  widgets/              GradientStrip, NodeBar, GradientEditor, position mapping, run-time painted icons
  ui/                   .ui loader, background tasks, MainWindow, FractalDocument, FractalViewport (image framing,
                        view vs. camera pan/zoom), ViewerBar (zoom + image size), SettingsPanel, FractalLibraryPanel,
                        ThumbnailProvider, RenderStatus (status bar), GradientLink, FormulaBrowser, and the gradient side:
                        GradientDocument, file actions, GradientLibraryWindow
tools/                  import_apo_plugins.py (plugin sources → library), apo_decompile.py (plugin DLLs → formulas)
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
