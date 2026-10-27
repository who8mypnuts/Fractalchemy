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
* Menu bar: *File* (Open Fractal…, Save `Ctrl+S`, Save As… `Ctrl+Shift+S`, Exit), *Edit* (Undo `Ctrl+Z`, Redo `Ctrl+Y`,
  Copy `Ctrl+C`, Copy As ▸ Apophysis / Chaotica Parameters, Paste `Ctrl+V`, Edit Fractal Library…), *View* (Show/Hide
  Fractal Library `Ctrl+L`, Refresh `F5`, Thumbnails, Show/Hide Settings Panel, Zoom to Fit / 100%, Toolbar, Status Bar),
  *Windows* (Gradient Library `F6`, Render Image… `Ctrl+R`), *Help*.
* Toolbar: Open · Save · Save As · Undo · Redo · Copy · Paste · Gradient Library · Render Image (hover for tooltips).
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
* **Copy** puts the parameters (transforms, camera, colouring *and* gradient) on the clipboard as Fractalchemy
  text; *Copy As* gives Apophysis `<flame>` XML or a Chaotica world instead. **Paste** accepts any of the three.
* **Fractal Library** (left pane, collapsible via the divider arrow or `Ctrl+L`): folders of `.flame`
  (Apophysis / flam3, legacy files included), `.chaos` (Chaotica) and `.fa` (Fractalchemy) files, each file
  expanding into its flames. Search box, collapse-all, and two view buttons: **list** or **thumbnails**
  (rendered on demand by the preview engine, at low priority so the viewport always comes first).
  Folders are watched, and the right-click menu / drag-and-drop file operations are the same as in the
  Gradient Library. It has its own folder list (*Edit ▸ Edit Fractal Library…*, or **+** / ✎ in the pane).
* **Viewport** (the centre): click a flame and it renders progressively in passes. The flame is framed as an
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
  tabs of options — today *Render* with **Passes** and **Quality** (samples per pixel) for the preview; both
  re-render immediately and persist between runs.
* **Status bar** across the bottom: the loaded fractal (name, transform count, size, file, ignored
  variations), render facts (engine, render size, samples, samples/second — the full GPU name is in the
  tooltip), **Pass n of N**, and a progress bar.
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
* Both use Apophysis's log-density tone mapping (brightness, gamma, gamma threshold, vibrancy, background)
  and the flam3 variation definitions. ~50 variations are implemented, each written once for numpy *and*
  GLSL and tested to agree; unknown ones (plugins not ported yet) are listed in the status bar and ignored.
  3D variations render as their 2D projection.
* Tunables in `config.py`: `PREVIEW_PASSES` / `PREVIEW_QUALITY` (defaults for the settings panel),
  `INTERACTIVE_SCALE`, thumbnail size / quality.

### Render Image window (the final renderer)
*Windows ▸ Render Image…* (`Ctrl+R`) or the toolbar button opens a non-modal tool window; a render runs on its
own thread with a snapshot of the flame, so you can open and edit another fractal while it works. Closing the
window hides it — the render carries on; quitting asks first.

* **Size** — the first preset is the viewer's current image size; then common screen and print sizes, or type
  any width × height (no upper limit beyond memory and disk). The **link** button keeps the aspect ratio: with it
  on, typing one dimension updates the other; off, they are independent. **⇄** swaps them.
* **Quality** — the Apophysis render options: **Density** (samples per pixel; 100 … 16 000 presets or any value),
  **Oversample** (1–8 buckets per pixel per axis), **Filter** + **Radius**. The filter is the anti-aliasing
  choice: Gaussian (Apophysis), Box, Triangle, Mitchell-Netravali, Catmull-Rom, B-spline, Lanczos 2 / 3,
  Blackman-Harris. **Denoiser**: *Density estimation* (flam3's adaptive blur, with max / min radius and curve),
  or an image-space pass after rendering — *Guided filter* and *Bilateral* (built in), *Non-local means*
  (with `opencv-python-headless`), *Intel Open Image Denoise* (with the `oidn` package) — each with a strength.
  **Engine**: automatic, GPU (OpenGL, single precision, fast) or CPU (one worker process per core, float64,
  exact at deep zooms). **Memory limit**: the histogram budget; larger images are rendered in tiles
  (Apophysis's "slices": every tile runs the full chaos game, so the plan line tells you the cost).
* **Output** — file and format: PNG (8 / 16-bit), JPEG, TIFF (8 / 16-bit), WebP, BMP, AVIF, HEIF, JPEG XL
  (the last three when their encoders are installed), SVG (the render embedded as PNG). Options greyed out when
  the format cannot use them: bit depth, quality / lossless, **transparent background**. *Save parameters*
  writes a `.flame` beside the image; *Embed parameters* stores them in the file (PNG text chunk, JPEG comment,
  TIFF description, EXIF comment elsewhere); *Save incomplete renders* keeps what was done when you stop.
* **Progress** — a live preview that fills in tile by tile, a progress bar, elapsed and **remaining** time
  (from the measured sample rate), speed and tile counter. Before you start, the window estimates the time from
  the preview engine's or the last render's measured speed. **Pause / Resume** and **Stop** (which still saves if
  *Save incomplete renders* is on); afterwards the result line links to the file and its folder.
* Settings persist between runs; the destination defaults to the last folder and the flame's name.

| Fractal format | Read | Entries | Rename | Add / remove / replace entry | Write whole file |
|---|---|---|---|---|---|
| `.flame` (Apophysis / flam3) | ✓ | many | ✓ | ✓ (in-place text edits; unknown data survives) | ✓ |
| `.fa` (Fractalchemy, JSON) | ✓ | many | ✓ | ✓ | ✓ |
| `.chaos` (Chaotica) | ✓ | many | ✓ | – | ✓ |

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
                        formats/ (registry + .flame XML, .chaos reader/writer, .fa, clipboard text)
  render/               RenderSettings / RenderStats, CompiledFlame, tone map (numpy + GLSL), cpu_engine, codegen +
                        gpu_engine (moderngl), RenderService (worker thread, priorities, cancellation);
                        the final renderer: final_settings (options, tile plan), filters (reconstruction filters,
                        density estimation), denoise, samplers (+ cpu_workers: shared-memory worker processes),
                        final_engine (tiles → filter → tone map → denoise), output (formats, 16-bit PNG / TIFF,
                        SVG, metadata), final_service (FinalRenderJob thread)
  model/                Qt-free data: colours, stops, Gradient, simplification, adjustments, node operations
  formats/              one module per file type + registry; textfile.py / ufparams.py do in-place text edits
  library/              generic library: Catalog (gradient / fractal file knowledge), roots (QSettings), scanner,
                        model/filter/tree, controller, menus, dialog, panel
  imaging/              decoders/plugins, SVG rasteriser, palette extraction, colour ordering
  widgets/              GradientStrip, NodeBar, GradientEditor, position mapping, run-time painted icons
  ui/                   .ui loader, background tasks, MainWindow, FractalDocument (undo history), FractalViewport +
                        ViewGeometry (image framing, view vs. camera pan/zoom), ViewerBar, SettingsPanel,
                        FractalLibraryPanel, ThumbnailProvider, RenderStatus, GradientLink, LibraryHost (shared
                        library-pane wiring), FileActionsBase + the fractal / gradient file actions,
                        GradientDocument, GradientLibraryWindow, RenderWindow (+ render_size_panel,
                        render_quality_panel, render_output_panel, render_progress)
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
