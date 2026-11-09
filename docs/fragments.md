# Fragments — Fragmentarium inside Fractalchemy

*Windows ▸ Fragments* (`F12`, the code-sheet-with-a-shard button on the toolbar) opens the Fragments window: a
**Fragmentarium**-style editor and renderer for GLSL *fragments* — fractals written as fragment shaders (Mandelbulbs,
Mandelboxes, kaleidoscopic IFS, escape-time sets, feedback systems). It reads the `.frag` files of Fragmentarium /
FragM unchanged, ships FragM's example library and include files, and renders on the GPU through moderngl.

The plan behind it is `plans/fragments-plan.md`; this document is the user guide and the language reference.

## The window

The **Library** dock and the source tabs on the left, the viewport in the middle, the **Parameters** dock on the
right, the **Log** dock below, the animation toolbars above the viewport. Closing the window hides it; layout,
options (*Edit ▸ Preferences…*) and open tabs are remembered between runs.

* **Toolbar**: New 2D / New 3D fragment, Open, Save, Save as · Undo / Redo (the parameters; the editor has its own
  when it has focus) · **Build** (`F5`; a red *Build needed* appears when the shown program is stale) · **Subframe max**
  (how many subframes accumulate before the viewport rests; 0 = keep going) and *n rendered* · **Buffer size**: X × Y
  with an aspect lock, *Lock to window size* (the buffer follows the viewport) or *Custom size* (the image is
  letterboxed).
* **Quality of life**: a *Filter parameters…* box above the tabs (names first, tooltips as a fallback; the first
  matching tab is selected); a right-click on any parameter row gives *Reset to default*, *Randomize*, *Copy value*,
  *Paste value*; *Parameters ▸ Randomize group* (`F6`, never the camera or locked values), *Next / Previous preset*
  (`Ctrl+PgDown` / `Ctrl+PgUp`); a right-click on the viewport (without dragging) gives *Copy image*
  (`Ctrl+Shift+C`), *Save screenshot*, *Add camera bookmark*, *Reset camera* (`Ctrl+Shift+0`, back to the preset's),
  the HUD, fullscreen, render and mesh export; tabs close on middle-click and have *Close others* / *Close all* /
  *Copy path* / *Show in folder*; `Ctrl+E` hides the editor pane so the viewport takes the width; `Ctrl` + wheel /
  `Ctrl` + `+` `−` `0` zoom the editor font (all tabs, kept in the preferences); the status bar shows the
  accumulation against *Subframe max* as a progress bar; a warning repeated within a few lines is logged once.
* **Log**: the preprocessor's remarks (*Parse*, *Including file*, `#info` lines, clamped preset values, locked
  variables), *Compiled script in N ms*, and compile errors with the **file and line** they belong to — clicking a
  row opens the file (bundled includes open read-only) at that line; the line is marked in the editor too.
* **Library** (dock, `Ctrl+L`): the bundled examples (read-only — *Save* becomes *Save as*) and your own folders
  (*Library ▸ Add folder to library…*) of `.frag` / `.fafrag` files, with a search box on a row of its own, the
  *Show* filter, the thumbnail size and the list / thumbnail buttons on the row below, and an optional thumbnail
  view (*Library ▸ Thumbnails*: each fragment rendered once at a small size and cached; small / medium / large). Double-click opens a
  tab; drag a file onto the window to open it; the host's library features (copy / move / rename, per-folder
  views) apply to your folders. A row's menu adds **Favourite**, a **Rating** (one to five stars) and **Tags…** —
  kept in a small JSON beside the cache, never in the files, so the examples stay pristine — and the **Show** combo
  narrows the tree to favourites, recently opened files, ★★★★ and up, 2D or 3D fragments. The search box matches more
  than names: `tag:ifs`, `param:Power` (or just `Power` — every annotated uniform is indexed), `include:DE-Raytracer`,
  preset and group names, `#info` lines, `★★★`, `fav`, `recent`, `fp64`. In the thumbnail view each row's caption says the
  camera kind, the number of presets and parameters, the stars and the tags. Fragments that use **double precision**
  outright (`double` / `dvec` / `#version 4xx`, in the file or in what it includes — not behind `#if __VERSION__ >= 400`
  guards) carry an `[fp64]` badge in the list, a line in the caption and a tooltip; on a context without fp64 the badge
  reads `fp64 ✗` and the caption warns that the build will fail. *Show ▸ Needs double precision* lists them.
* **Grading** (a page of the Parameters dock): exposure, tone mapping (Reinhard / filmic / ACES), gamma, contrast,
  saturation, hue shift, vignette, invert, and the **post stack** — bloom (a bright pass blurred at half resolution and
  added back: threshold, radius, strength), chromatic aberration (the red and blue channels drift outwards), film grain,
  and a `.cube` colour **LUT** (3D or 1D, Resolve / Photoshop style, with a strength) — applied by the display pass on
  top of the fragment's own buffer shader, so every change shows at once without touching the accumulation; saved in
  the `.fafrag`; applies to hi-res renders. A LUT that cannot be read is noted in the log and skipped.
* **Parameters dock extras**: the groups are collapsible *sections* on one page or FragM's *tabs* (the ⊞ button);
  *Pin to Favourites* on a row's menu moves the parameter into a **★ Favourites** group at the top (the list is saved in
  the `.fafrag`); the arrow keys nudge a focused slider or number by a thousandth of its range — **Shift** makes it ten
  times as much, **Ctrl** a tenth, Page Up / Down a hundredth; *Parameters ▸ Preset gallery…* (`Ctrl+F9`) renders
  every preset small, double-click applies one.
* **Controllers** (*Windows ▸ Controllers…*): a MIDI knob or a gamepad stick bound to a slider component — *Listen*
  to a device (Linux device files: `/dev/input/js*`, `/dev/midi*`, `/dev/snd/midiC*D*`; no library needed), choose a
  slider, press *Learn* and move the control. Knobs and triggers work **absolutely** (their position spans the slider's
  range), sticks **relatively** (the deflection moves the value at a speed, with a dead zone); invert and speed are
  per binding, the bindings are saved in the `.fafrag` (`tabs.controllers`). Each burst of movement is one undo step.
* **Walkthrough** (dock, hidden by default, tabbed with the Library): the current fragment's `// STEP n:` comments as a
  clickable list — the *Fractalchemy Tutorials* examples explain themselves step by step — and below them an outline
  (`#group`s, functions, `#preset`s) that jumps to the line.
* **History** (dock, hidden by default, tabbed with the Log): a strip of thumbnails of earlier looks. *Snapshot*
  (`Ctrl+F6`) keeps the current one, *Auto* takes one a moment after any parameter change, and **Mutate** (`Shift+F6`) nudges
  the fragment's own unlocked parameters (those declared in the tab — the raytracer's and lights' from the includes stay
  put; *current group only* restricts it further, the camera never moves) at random by up to the *strength* (a share of
  each slider's range) after taking a snapshot, so a walk through variations can always go back — click a thumbnail to
  restore those settings (undoable). *Randomize* is the same with whole ranges.
* **Animation toolbars**: *Progressive* (accumulate one still) / *Animation* (advance `time` while playing), Rewind
  `F10`, Play `F11`, Stop `F12`, the time slider with a keyframe mark per `KeyFrame.nnnn` preset, the length in
  seconds and the frame rate. Space in the viewport toggles play.
* **Status bar**: messages, FPS (images per second while accumulating), the buffer size and aspect (and *tiled n×n*
  when the watchdog mitigation kicked in), the engine.

### Workflow

1. *Library ▸ Examples ▸ …* opens one of the bundled fragments (FragM's example folder: 2D Systems, Benesi, Kaleidoscopic
   IFS, Kali's Creations, Knighty Collection, Tutorials, … plus Fractalchemy's *Primitives* and *Distance Estimator
   Compendium* folders) in a tab. It is built and rendered at once (*Autorun*).
   Bundled examples never save over themselves: *Save* becomes *Save as*.
2. The **Parameters** dock shows one tab per `#group`, the **Preset** combo applies a `#preset` block (the `Default`
   preset is applied on load). Sliders re-render as you drag; Ctrl+Z undoes. A parameter the compiler optimised away
   is hidden (unless locked — *Parameters ▸ Hide unused parameters* toggles it).
3. Edit the source; **Build** (`F5`) compiles it (or turn on *Build ▸ Auto-build* to rebuild a second after typing
   stops). While a build fails the previous program keeps rendering.
4. **Lock** a parameter (the padlock) to bake its value into the shader: faster, and the program needs a rebuild.
   `Locked` / `NotLocked` / `NotLockable` / `AlwaysLocked` come from the annotation; a slider's context menu also
   offers *Select source*, *Scientific* / *Standard* notation and editing the *Upper* / *Lower bound* (the annotation
   in the source is rewritten).
5. **Presets**: `F2` copies the settings as text (`name = value` lines), `F3` pastes them, Shift+`F3` applies the
   editor's selection, `F4` makes a preset from the current group, `F8` inserts a preset from the current settings
   (named `KeyFrame.nnnn` by default for 3D fragments — the camera only), `F9` selects the current preset in the source,
   `F1` resets everything.
6. *Build ▸ Show preprocessed source* shows the exact GLSL handed to the driver with the original `file:line` of every
   line; *Edit ▸ Insert command* has every directive, special uniform and texture option, and every include on the
   include path. The completer (`Ctrl+Space`) knows the GLSL built-ins with their signatures, the host's directives
   and annotations, and the fragment's own functions. **In the editor**: a failed build underlines the offending lines
   (wavy, red for errors, amber for warnings) with the message on hover; hovering a name shows its signature (GLSL
   built-ins, the fragment's own functions, uniforms); **Ctrl+click** goes to a name's definition — in the tab, or in
   the files it includes (opened read-only at the line); *Insert command ▸ Code snippets* inserts templates with
   **tab-stops** (`Tab` walks from placeholder to placeholder: a DE skeleton, a colour function, an iteration loop with
   bailout, slider / colour / checkbox uniforms, a box fold, a sphere fold …); **Ctrl+Shift+D** selects the next
   occurrence of the word as one more cursor (Ctrl+Shift+L all of them) so typing, Backspace and Delete edit every
   occurrence at once — a rename in three keystrokes; Esc leaves. *Edit ▸ Compare with original…* shows a unified diff of
   the tab against the bundled example it was saved from (a copy of an example remembers its origin in the `.fafrag`; an
   unsaved tab compares with its file) with *Revert to original*.
7. *File ▸ New from template* starts from one of the built-in templates (FragM's New 2D / New 3D, a kaleidoscopic IFS, a
   Mandelbox, a 2D Julia / Mandelbrot with a map, a Shadertoy-style shader, a buffer-feedback system, the fast
   raytracer) or one of yours (*Save as template…* keeps the current source under
   `~/.config/Fractalchemy/fragments/templates`).

### Camera menu

*Navigation style* chooses between **orbit** (the default: DCC conventions around the *Target* — left-drag orbits,
middle-drag pans, right-drag / wheel dolly, Shift + left looks around, Alt + left orbits the origin) and **fly**
(FragM's controls, below). *View from* has the numpad views — `1` `3` `7` front / right / top (Ctrl: the opposite
side), `9` the other side, `4` `6` `8` `2` orbit 15°, `.` frames the origin (also Alt+1 / 3 / 7 … in the Navigation
toolbar) — and *Turntable* (Alt+T) slowly orbits the target. *Add camera bookmark…* (`Ctrl+B`) keeps the current
camera under a name in the `.fafrag`; the menu lists the bookmarks (one click applies one, undoable) and removes them.
*Record camera path* (`Ctrl+Shift+P`) samples the camera every 0.4 s while you fly and, when turned off, writes the
samples into the source as `KeyFrame.nnnn` presets — the path of a flight without pressing `F8` at every turn. With
*Draw camera paths* on, the keyframes' eye points are **handles**: drag one in the screen plane and its `KeyFrame`
preset is rewritten on release.

### Viewport overlays

*Render ▸ Mini-map* (`Ctrl+M`) draws a plan of the scene in the corner — the origin, the target, the eye with its
view wedge and the keyframe path, seen from above along the camera's up vector (a 2D fragment shows its centre and
zoom; the 2D Julia example has its own map inside the fragment). *Render ▸ Freeze reference (A)* (`Ctrl+Shift+A`)
keeps the current picture and *A/B compare* (`Ctrl+Shift+B`) shows it left of a draggable divider with the live render
on the right — judge a slider change against the look before it. **Ctrl+drag** a rectangle on the viewport to choose a
**region of interest**: the render window opens with that crop of the frame as its *Region* (rendered at full
resolution, the tile taking the region's aspect; *Clear* returns to the whole frame).

### Build menu extras

*Manual rendering* holds every render until *Render now* (`Shift+F5`) or a build (FragM's *Manual* mode; the
change made meanwhile renders when the mode is turned off). *DE Composer…* builds a distance estimator from folds,
transforms and a primitive (below). *Debug view ▸ Depth buffer* shows the depth the raytracer wrote (near bright, far
dark, background black, iso-depth lines); *Debug view ▸ DE slice…* samples the distance estimator on a plane (facing
the camera through *Target*, or XY / XZ / YZ through a centre) as a heat map — inside blue, the surface white,
outside through yellow to red, contour lines every step: a good estimator has evenly spaced contours, one that
overestimates (the "dust" of a noisy render) shows contours bunching towards the surface; *Follow the camera*
re-samples after every move. *Windows ▸ Performance HUD* (`Ctrl+H`) overlays images per second, milliseconds per
subframe against the watchdog budget, subframes, tiling, size and the GPU load limit.

### Mouse and keyboard

| 3D camera, **orbit** style (the default) | |
|---|---|
| Left-drag | orbit around the *Target* |
| Middle-drag · Shift + right-drag | pan in the screen plane |
| Right-drag · Ctrl + middle-drag · wheel | dolly towards the target (Ctrl + wheel: fine) |
| Shift + left-drag | look around (FragM's orient) |
| Alt + left-drag | orbit around the world origin |
| Numpad `1` `3` `7` (Ctrl: opposite) · `9` · `4` `6` `8` `2` · `.` | front / right / top views · the other side · orbit 15° · frame the origin |
| Alt+T | turntable |

| 3D camera, **fly** style (FragM; `#camera 3D`: `Eye`, `Target`, `Up`, `FOV`) | |
|---|---|
| Left-drag | orient (turn the view) |
| Shift + left-drag | rotate around the world origin |
| Shift + Alt + left-drag | rotate around the *Target* |
| Right-drag | translate in the screen plane |
| Left + right drag · wheel | dolly (by step / FOV); Shift + wheel halves / doubles the step |
| Middle click | set *Target* (and *FocalPlane* when *AutoFocus* is on) to the surface under the cursor; Ctrl: `LightPos` |
| Click without drag | the 3D point under the cursor in the status bar |
| `W` `S` · `A` `D` · `R` `F` | forward / back · strafe · down / up |
| `T` `G` · `Y` `H` · `Q` `E` | pitch · yaw · roll |
| `1` `3` `2` `5` | step ×0.5 · ×2 · ×10 · reset |
| Shift + `~` | look at the origin |

| 2D camera (`Center`, `Zoom`) | |
|---|---|
| Left-drag · right-drag | pan · zoom about the press point |
| Wheel | zoom about the cursor (*fixed*; *traveling* moves the centre to the cursor) |
| `A` `D` `W` `S` · `Q` `E` · `1` `3` `2` `X` | pan · zoom · step ×0.5 · ×2 · ×10 · ×0.1 |

The keys (`W A S D R F`, `T G Y H`, `Q E`, the step keys) work in both styles. While a button is held the viewport
renders at half resolution and one subframe at a time; on release the full-size accumulation resumes. Esc toggles
fullscreen (Shift + right-click shows the menus there). Ctrl+drag, the compare divider and the keyframe handles are
described under *Viewport overlays*.

## Animation

A fragment is animated two ways, both FragM's:

* **The camera path.** For a 3D fragment `F8` inserts a `KeyFrame.nnnn` preset holding the camera (`Eye`, `Target`,
  `Up`, `FOV`, and `FocalPlane` when *AutoFocus* is on). The keyframes are spaced evenly over the animation's length
  and the camera follows a Catmull-Rom spline through them (*Animation ▸ Loop camera path* closes it). The paths are
  drawn over the viewport (*Draw camera paths*); with *Hide paths behind the surface* (FragM's spline occlusion) the
  depth buffer is read after every pass and the parts of the path the rendered surface is in front of are dashed and
  faint (the keyframe dots too) — the depth the raytracers write (`1 − 1e-5 / distance`, or `1 / distance` with
  *DepthToAlpha*) is turned back into a distance and compared with the path point's distance from the eye. *Clear
  animation actions* removes the curves, the keyframe presets stay in the source.
* **Easing curves.** `F7` (*Animation ▸ Add easing curve…*) animates the last edited slider component between two
  values over a frame range with one of Qt's easing curves (linear, quad, cubic, sine, elastic, bounce, back … with
  period / amplitude / overshoot, loops and ping-pong). The curves live in `Range…` presets (`F8` with *Presets contain
  easing curves* puts them in ordinary presets too) as FragM's twelve-field lines:
  `Power1:InOutQuad:5:2:8:0:100:0.3:1:1.7:1:0` — name, type, number, start, end, first frame, last frame, period,
  amplitude, overshoot, loops, ping-pong.

*Animation ▸ Interpolation* adds a mode FragM lacks: **All parameters** blends every numeric parameter (floats,
vectors, colours) between consecutive keyframe presets as well — smoothly, with integers, booleans and menus holding
the last keyframe passed; the camera path and the easing curves apply on top. The mode is saved in the `.fafrag`
metadata and ignored by FragM.

*Animation ▸ Timeline editor…* shows the keyframes and the curves on one ruler: click a keyframe to apply it, scrub
the playhead, double-click a curve to edit it. Its **Graph** tab plots values against frames: every easing curve as
a line with its two handles (start frame / value, end frame / value) — drag one and the curve is rewritten — and, for a
chosen parameter, its **keyframe track** (the value in each `KeyFrame` preset, which the *All parameters* interpolation
blends between; vector components as `Name.n`). *Animation* mode plays at the frame rate on a wall clock (a slow
render drops frames rather than slowing down), stops at the end or loops (*Loop play*). The clock (fps, length,
loop flags) is saved in the `.fafrag` metadata.

## Rendering to files

*Render ▸ Render…* (`Ctrl+R`) is FragM's *High Resolution and Animation Render* as a job window: it snapshots the
current tab (program, parameters, presets, curves, clock) and renders on its own thread with its own OpenGL context,
so the editor stays usable; closing the window hides it while the render carries on.

* **Tiles**: the tile size (the buffer size of each tile), tiles per side (`n × n`, up to 32768 pixels a side in
  all), padding (extra view per tile, cropped away when assembling — hides seams from screen-space effects).
* **Quality**: subframes per tile. **Animation**: a frame range at the clock's fps and length (a numbered sequence
  `name.00012.png`), optionally encoded to a video with ffmpeg afterwards (mp4 / HEVC / webm / mov / gif, with a
  quality setting; the frames can be kept).
* **Output**: every image format the host writes (PNG 8 / 16-bit, JPEG, TIFF, WebP, BMP, AVIF / HEIF / JPEG XL when
  their encoders are installed, OpenEXR half / float), *Embed parameters* (the settings text under the `frAg` key
  FragM uses, so either program reads the other's images), *Save parameters* (a `.fragparams` beside the image), *Save
  fragment* (the fragment with its settings into a `<name> Files` folder, FragM's autosave, optionally with the
  includes), *Unique name* (a time stamp), **EXR with depth** (the `DepthToAlpha` option: the depth buffer as the `Z`
  channel), *Save incomplete* (keep what was rendered when stopped). *Preview* shows a still in a dialog instead.
* **View**: **stereo** pairs — two renders with the eye shifted along the camera's right vector by the *separation*
  (a fraction of the eye–target distance; 0.03 feels natural), composited as an **anaglyph** (red from the left eye,
  green and blue from the right, for red / cyan glasses) or **side by side** (left | right, twice as wide, for VR
  viewers and 3D displays) — and the **360° panorama** (the fragment's `EquiRectangular` mode: the whole sphere around
  the eye as a 2:1 image, for VR viewers and sky maps). **Region**: the crop chosen with Ctrl+drag on the viewport.
* The plan line says what will be drawn; the estimate extrapolates from the viewport's measured subframe speed.
* **When a render cannot start** the window says why, in plain sight: a warning banner above the options lists
  every blocker, the status bar repeats the first, the *Start* button's tooltip has them all, and the offending
  controls are framed in red. A tile larger than the GPU limit (4096 pixels a side — the GPU renders one tile at a
  time) is the usual one: the banner's **Fix** button splits the same image into enough tiles (6000 × 6000 becomes
  2 × 2 tiles of 3000 × 3000); other blockers are an image over 32768 a side in a non-EXR format, no output file,
  an empty frame range, a region outside the frame, a tile range that selects nothing.

*Render ▸ Add to render queue* (`Ctrl+Shift+Q`) snapshots the current tab with the render window's settings into the
**Render Queue** window (*Render ▸ Render queue…*), which runs its entries one after another on their own thread —
line up several fragments, presets or sizes and let them render while you work; entries can be removed while they
wait, *Stop* ends the running one and leaves the rest waiting, finished entries report in the log.
*Render ▸ Batch render presets…* renders one image per preset (or per keyframe) of the saved fragment into a folder.
*File ▸ Save screenshot…* writes the viewport's accumulation as an image with the parameters embedded.

### From the command line

`tools/render_frag.py` is what FragM's `.fqs` scripts were for (*Help ▸ Batch rendering from the command line…*):

```
python tools/render_frag.py Mandelbulb.frag --out out/bulb.png --size 1920x1080 --tiles 2 --subframes 200
python tools/render_frag.py Mandelbulb.frag --all-presets --out out/presets/
python tools/render_frag.py Flight.fafrag --frames 0-249 --fps 25 --out out/flight.png --video mp4
python tools/render_frag.py --check "Examples/**/*.frag"
```

`--preset`, `--keyframes`, `--padding`, `--format` (`png16`, `exr`, …), `--depth-alpha`, `--include-path`, `--region
X,Y,W,H` (a crop as fractions), `--stereo anaglyph | sbs` with `--eye-separation`, `--panorama` and `--quiet` complete
the set; the exit code is the number of failures.

**Distributed and resumed renders.** `--tile-range A-B` draws only those tiles (row-major indices of the `n × n`
grid) and keeps each as a `.npz` in `--tile-dir` (default `<out>.tiles`); run the other ranges on other machines (or
later), then `--assemble` joins every tile found in the folder into the image — nothing is written until all the
tiles are there. `--resume` skips tiles already in the folder, so a render interrupted half-way continues where it
stopped:

```
python tools/render_frag.py big.frag --out out/big.png --tiles 4 --tile-range 0-7  --tile-dir out/tiles
python tools/render_frag.py big.frag --out out/big.png --tiles 4 --tile-range 8-15 --tile-dir out/tiles
python tools/render_frag.py big.frag --out out/big.png --tiles 4 --assemble --tile-dir out/tiles
```

### Importing from Shadertoy

*File ▸ Import from Shadertoy…*: paste the *Image* tab (and optionally *Buffer A*), say what each `iChannel` is
(a texture file, Buffer A, the previous frame) and import. Shadertoy's uniforms (`iResolution`, `iTime`, `iFrame`,
`iMouse` as a slider pair, `iDate`, `iChannelResolution`) are declared on top of the host's, `mainImage` is called
from `main`. With a Buffer A the import writes two files next to each other: Buffer A becomes the main program
(its self-reading channel is the `backbuffer`, `DontClearOnChange` keeps the feedback) and Image becomes its
`#buffershader` reading `frontbuffer`. Buffers B–D, cube maps, keyboard, sound and video inputs are not mapped
(the log says what was left out).

## Textures

`uniform sampler2D tex; file[name.png]` binds a texture: the file is looked up beside the fragment, then on the
include paths, then in the bundled `Include` folder (a file dialog in the Parameters dock changes it; the parameter is
always locked). LDR images load through Pillow unconverted, `.hdr` and `.exr` as float; for an EXR the four boxes
beside the file name pick which of the file's channels feed r, g, b and a (`file[sky.exr, R;G;B;A]`; `Z;Z;Z;A` puts a
depth pass in every colour channel; a name the file lacks fills with 0, or 1 for alpha — FragM's rules; every
channel the file declares is offered, `diffuse.R` and the like included), `samplerCube` from a strip of six square faces
(`+x −x +y −y +z −z`), `isampler2D` / `usampler2D` as integer textures. `#TexParameter tex GL_TEXTURE_MIN_FILTER
GL_LINEAR_MIPMAP_LINEAR` (and `MAG_FILTER`, `WRAP_S` / `WRAP_T`, `MAX_ANISOTROPY`) sets filtering and wrapping;
mipmaps are built when a mipmap filter is asked for; the defaults are linear and repeat. Textures are cached by
file and modification time and reloaded when the file changes; *Build ▸ Clear texture cache* drops them all. A
texture that cannot be read is reported in the log and the fragment renders without it.

## Gradients → GLSL

*Edit ▸ Insert gradient…* turns a gradient into GLSL at the cursor (or on the clipboard) — FragM's ggr2glsl,
generalised: the source is the Gradient Library's current gradient, any gradient file the host reads (`.ugr`,
`.map`, `.flame` palettes, images) or a GIMP `.ggr` (its segments keep GIMP's blend shapes — linear, curved, sine,
sphere — and colour spaces — RGB, HSV clockwise / counter-clockwise — exactly; ggr2glsl's sine and sphere shapes ran
backwards). Three forms: **segments** (the segment arrays and GIMP's maths in GLSL; exact), a **sampled table**
(`const vec3[N]` with a linear `mix`; cheapest) or a **1-D texture** (a PNG strip written beside the fragment plus a
`file[…]` line). *Use as* wraps the function as the object colour (`#define providesColor` + `baseColor` with rotation /
offset / scale sliders) or the sky (`providesBackground` + `backgroundColor`); put such a block before the raytracer
`#include`. GIMP gradients also open in the Gradient Library like any other format.

## Mesh export

*Render ▸ Export mesh…* turns a fragment with `float DE(vec3 p)` into a printable mesh: the distance estimator is
sampled on a voxel grid **on the GPU** (a probe program: the fragment's shader with a generated `main`, the same
parameter values as the viewport; `baseColor` gives vertex colours when the fragment `#define providesColor`), the
shell `DE = threshold × voxel` is extracted with the host's surface nets (a threshold of half a voxel closes
estimators that never go negative), cleaned with the host's clean-up levels (welding, small pieces, holes, smoothing,
decimation) and checked (watertight, pieces, volume, thin walls). *Fit* runs a coarse pass first and shrinks the box
to where the fractal is. A preview still and the report appear in the dialog; *Export* writes OBJ / STL / PLY / glTF /
USD (with vertex colours, in world units or scaled to a size in millimetres) plus a markdown report; *Send to 3D
Editor* saves a PLY asset and opens it on the 3D Editor's Instances tab for instancing and lighting there.
A dense grid is capped at 512³ with a memory estimate; **sparse blocks** lift that to 4096³: a coarse pass finds the
blocks the surface crosses, each is sampled with two voxel layers of padding, meshed on its own and trimmed to its
box, and a weld joins the identical boundary vertices — the result is the same mesh a dense grid would give, with
only the occupied blocks ever in memory. The job runs on its own thread and context and can be cancelled.
*Normals* can come from the **distance field's gradient** instead of the faces — smoother shading true to the
estimator rather than the voxel steps, at the same resolution. *Bake colours to a texture* paints the vertex colours
into a PNG through generated UVs (box / spherical / cylindrical / xatlas when installed) so OBJ, glTF and USD carry them
as an image; *Blender script* writes `<name>_blender.py` beside the files — `blender --python <name>_blender.py`
imports the mesh with its material (the texture or the vertex colours), a camera and a sun.

### Exporting the distance estimator as code

*Render ▸ Export DE as code…* writes the fragment's `DE` — with every function it calls, the `#define`s and globals
they use, and the **slider values baked in as constants** (`const float Power = 8.0;`), so the exported code is what
the viewport shows — as **GLSL**, a **Shadertoy** (the same plus a small raymarcher `mainImage` with the fragment's
camera: paste into the Image tab), a **Unity** ShaderLab file (an HLSL raymarcher on a proxy cube) or an **Unreal**
`.ush` include with a `RaymarchDE` for a Custom node. The HLSL translation is mechanical — types, `mix` / `fract` /
`inversesqrt` / `dFdx`, `atan(y, x)`, `mod` (a `glsl_mod` helper with GLSL's semantics), single-scalar vector
constructors — and the notes list what it could not settle: matrix products need `mul()` and HLSL's row-major
layout, textures are not carried over, `gl_*` built-ins have no equivalent. A fragment that sets globals in `init()`
(FragM's `providesInit`) gets `init()` exported and called first.

## Primitives, operators and folds

`#include "Primitives.frag"` (after the raytracer include) brings ~60 signed distance primitives, the operators that
combine them and the folds fractals are built from, all as plain GLSL functions — a standard library for writing
distance estimators, collected from Inigo Quilez's distance functions, Mercury's hg_sdf and Jon Baker's Distance
Estimator Compendium (attributions in `library/ATTRIBUTION.md`; the file includes `QuilezLib.frag`, so do not include
both).

| Family | Functions (all `float sd…(vec3 p, …)`, negative inside, centred at the origin) |
|---|---|
| Boxes / planes | `sdBox`, `sdBoxCheap`, `sdRoundBox`, `sdBoxFrame`, `sdChamferBox`, `sdPlane(p, n, h)`, `sdCross`, `sdCorner`, `sdBox2D` |
| Round things | `sdSphere`, `sdEllipsoid`, `sdCylinder(p, r, h)`, `sdCylinderInfinite`, `sdRoundedCylinder`, `sdCylinder6 / 8`, `sdCapsule`, `sdCapsuleLine(p, a, b, r)`, `sdTorus(p, R, r)`, `sdTorus82`, `sdTorus88`, `sdCappedTorus`, `sdLink`, `sdDisc`, `sdSolidAngle`, `sdWavySphere`, `sdTwistedTube` |
| Cones / pyramids | `sdCone(p, r, h)`, `sdCappedCone`, `sdRoundCone`, `sdPyramid` |
| Prisms | `sdHexPrism`, `sdTriPrism`, `sdOctPrism`, `sdRhombus` |
| Polyhedra | `sdOctahedron`, `sdIcosahedron`, `sdDodecahedron`, `sdRhombicDodecahedron`, `fGDF(p, r, [e,] begin, end)` with `GDFVectors` (`sdGDFOctahedron / Dodecahedron / Icosahedron / TruncatedOctahedron / TruncatedIcosahedron / Cube`) |
| Surfaces | `sdGyroid`, `sdSchwarzP`, `sdGyroidTorus`, `udTriangle`, `udQuad`, `sdStar` |
| Operators | `opUnion / opSubtract / opIntersect`, `opSmoothUnion / opSmoothSubtract / opSmoothIntersect(a, b, k)`, `opRound`, `opOnion`, `opElongate`, `opRepeat`, `opRepeatLimited`, `opRepeatMirror`, `opRepeatPolar(p.xz, n)`, `opTwist`, `opBend`, `opTranslate`, `opMirror`, `opFoldPlane`, `opDisplaceSine` |
| Folds | `foldBox(p, limit)`, `foldSphere(p, scale, minR2, fixedR2)`, `foldMenger`, `foldSierpinski`, `foldKaleido(p.xz, n)` |
| Helpers | `rot2(a)`, `rot3(axis, a)`, `lpNorm`, `lengthN`, `length6`, `dot2`, `smin`, `PHI` |

### The DE Composer

*Build ▸ DE Composer…* is the visual way to the same thing: a loop of steps — mirror, Menger / Sierpinski / kaleido
/ plane folds, box fold, sphere fold, sphere inversion, scale + offset (Knighty's IFS), scale + start point (the
Mandelbox), scale + constant (Julia), rotate, translate, repeat, twist, Knighty's Menger z shift — and an end shape
(box, sphere, octahedron, torus, cross, cylinder, point, dodecahedron, gyroid). Every parameter becomes a slider of
the generated fragment; *Create tab* opens it, *Update tab* rewrites it as you change the recipe (the recipe is kept
in the tab's metadata, so reopening the composer on that tab continues where you left off). Presets: Menger sponge,
Sierpinski tetrahedron, Mandelbox. Only steps with a well-defined distance estimate are offered (isometries,
scalings and conformal folds tracked in the scale `s`; the distance is `shape(p) / s`).

*Edit ▸ Insert command ▸ Primitives* and *Operators and folds* insert calls; *File ▸ New from template ▸ Primitives
playground* starts a fragment with them; *Library ▸ Examples ▸ Primitives* shows every primitive (*Primitives
Gallery*, a menu with all 42 shapes), the booleans, the Menger sponge from a box and crosses, kaleidoscopic folds, the
Mandelbox from `foldBox` + `foldSphere`, domain repetition, a gyroid shell and chain maille. A distance estimator
built from these is exactly what *Render ▸ Export mesh…* wants.

## Preferences

*Edit ▸ Preferences…* (stored per user): **GUI** — recent files, loop play by default, draw camera paths and hide
them behind the surface, 2D wheel mode (zoom towards the pointer or the centre), log rows kept, the Parameters dock's
arrangement, the 3D navigation style; **Editor** — font size, the colour theme (*Follow application theme* — the
default, recolouring with the main window's *View ▸ Theme* — or any of the application's themes pinned to the fragment
editors; *Edit ▸ Editor theme* offers the same), jump to the first error line, reload a
tab when its file changes on disk, the **session autosave** interval; **GLSL** — build on open (*autorun*), auto-build, move `main` to the end
(FragM's *moveMain*), locked parameters as `#define` or `const`, the compatibility layer (*modernise* / FragM's patch /
off), presets carry easing curves, the animation frame rate, the viewport's refresh interval and interactive scale,
the **GPU load limit** (a duty cycle: below 100 % the renderer idles between passes) and *pause rendering while the
window is hidden or minimised*;
**Paths** — extra include folders; **Application** — mirror the log to a file (rotated at a size cap), *verbose* (log
the parameter values after every build).

*Build ▸ Test GLSL versions* compiles the fragment at every GLSL version the driver offers (3.30 … 4.60) and reports
each outcome in the log — FragM's *Test versions*.

## The fragment language

A fragment is a GLSL fragment shader plus Fragmentarium's directives, all handled before the driver sees the text.

### Directives

| Directive | Meaning |
|---|---|
| `#include "file.frag"` | Textual inclusion (at column 0 only), resolved beside the fragment, then on the include paths, then in the bundled `Include/` folder. A file may be included twice on purpose. |
| `#buffershader "file.frag"` | A second program run over the accumulated image (tone mapping); it sees `frontbuffer`. |
| `#preset Name` … `#endpreset` | Parameter values as `name = value` lines. `KeyFrame.nnnn` presets are camera keyframes; `Range…` presets hold easing curves. |
| `#replace "a" "b"` | Replace `a` by `b` in every later line. |
| `#camera 2D` / `#camera 3D` | Which camera control the viewport uses (2D when absent). |
| `#buffer RGBA8 / RGBA16 / RGBA16F / RGBA32F / NONE` | The accumulation buffer's format (RGBA32F by default). |
| `#group Name` | The Parameters tab for the following uniforms (`Default` when absent; reset after every include). |
| `#vertex` … `#endvertex` | Vertex shader code (the includes provide it; most fragments need none). |
| `#info text` | Shown in the log. |
| `#donotrun` | Marks an include (listed as such in the library). |
| `#TexParameter name GL_PARAM GL_VALUE` | Texture filtering / wrapping / anisotropy for a sampler (see *Textures*). |
| `#define DontClearOnChange` | Parameter edits keep the accumulation (feedback systems such as Game of Life). |
| `#define IterationsBetweenRedraws n` | Draw `n + 1` subframes per shown image. |
| `#define SubframeMax n` | Sets the toolbar's subframe maximum when the fragment is built. |
| `#define providesInit / providesColor / providesBackground / providesNormal / providesInside / providesFiltering` | Contracts with the raytracer includes (plain GLSL defines). |

### Annotated uniforms → widgets

```glsl
uniform float Power; slider[1,8,16]                       // slider + spin box (from, default, to)
uniform float Detail; slider[-7,-2.3,0] Logarithmic        // logarithmic mapping
uniform float Fog; slider[0,0,2] Locked                    // baked into the shader unless unlocked
uniform vec3 Eye; slider[(-50,-50,-50),(0,0,-10),(50,50,50)] NotLockable
uniform vec3 Dir; slider[(0,0,0),(0,1,0),(0,0,0)]           // equal bounds: a unit direction (renormalised while edited)
uniform vec3 BaseColor; color[1.0,1.0,1.0]                 // colour swatch
uniform vec4 Glow; color[0,0.5,1, 1.0,0.8,0.2]             // a value slider (min, default, max) and a colour → (r, g, b, value)
uniform int Iterations; slider[1,12,100]
uniform int ToneMapping; menu[1, Linear;Filmic;Reinhard]   // combo box, the index is the value
uniform bool Julia; checkbox[false]
uniform sampler2D tex; file[texture.jpg]                   // a texture file (always locked)
uniform sampler2D env; file[sky.exr, R;G;B;A]              // EXR channel selection
uniform double Fine; slider[0,0.5,1]                       // double precision (needs #version 400 or later)
```

The comment line directly above a declaration becomes the widget's tooltip. The values of `float` parameters are
written with 9 significant digits (18 for `double`).

### Special uniforms (set by the renderer)

`uniform vec2 pixelSize` (1 / buffer size), `uniform int subframe` (1 for the first subframe), `uniform float time`
(seconds, the animation clock), `uniform sampler2D backbuffer` (the previous subframe's accumulation), `uniform
sampler2D frontbuffer` (the accumulation, in the buffer shader), `uniform mat4 projectionMatrix` (the legacy
`gl_ProjectionMatrix`: identity, or the tile transform of a hi-res render), `uniform bool DepthToAlpha` and
`uniform bool AutoFocus` (check boxes the host reacts to).

### Settings text

What presets hold, what `F2` copies and what `.fragparams` files contain:

```
// Generated by: Mandelbulb.frag
// Created on: …
Power = 8
Eye = 1.65826,-1.22975,0.277736
Detail = -2.84956 Logarithmic
HardShadow = 0.35385 Locked
Julia = false
```

A value outside its slider range is clamped with a warning in the log; an unknown name is reported; a changed lock
marks the program for a rebuild.

### Legacy GLSL and the compatibility layer

Fragments are written in GLSL 1.10 / 1.20 (`gl_FragColor`, `varying`, `gl_Vertex`, `gl_ProjectionMatrix`, `texture2D`).
Modern OpenGL contexts (what moderngl creates; the only kind macOS offers) are *core profile* and reject those names,
so the Fragments window translates every program to GLSL 3.30 core (or the version the fragment asks for) before
compiling: a prelude declares the replacements, legacy texture calls become wrapper functions, duplicate
declarations from several includes are dropped, `#extension` lines move to the top. Every line keeps its origin, so
errors still point into the right file. Doubles (`double`, `dvec`) need an explicit `#version 400` or later, as in
FragM. The translated text is what *Show preprocessed source* shows; a rejected program's sources and the driver's
log are written to `<cache>/Fractalchemy/glsl-failures/`.

Of the 232 bundled examples 225 compile; the seven that do not (listed in `tests/test_fragments_engine.py`) fail in
FragM as well — they use functions before including them, undeclared uniforms, or `double` code that never compiled.

## Sessions and crash recovery

*File ▸ Save session…* writes every open tab — the file it came from, the full text of tabs with unsaved edits, the
current settings text and preset, which tab is current — as one `.fasession`; *Open session…* brings them back with
their looks. The same session is written by itself to the cache folder every few minutes (*Preferences ▸ Editor ▸
Session autosave*) and removed on a clean shutdown; a file left behind means the last run ended badly, and the next
start says so in the log and status bar — *File ▸ Recover last session* restores its tabs (unsaved text included).

## Files

`.frag` (Fragmentarium's) and `.fafrag` (Fractalchemy's) open and save alike; *Save as* offers both. A `.fafrag` is the
same text plus, at most once, a block FragM's preprocessor sees as a comment:

```
/*[fractalchemy]
{"version": 1, "render": {…}, "animation": {"fps": 25, "length": 10, …}, "library": {"tags": […], "thumbnail": "…"}}
[/fractalchemy]*/
```

It carries the render settings, the animation clock and the library's tags / thumbnail; saving as `.frag` omits it.
`.fragparams` files are the settings text (*Parameters ▸ Colours from the Gradient Library* (all colour parameters, or *of this tab*) and *Colours from gradient
file…* give every `color[…]` parameter a colour sampled evenly along a gradient — one undo step. *Parameters ▸ Save parameters to file…* / *Load parameters from file…*); images written by the
window (screenshots, renders) carry the settings under the `frAg` key, the one FragM uses, so either program reads the
other's images. A file changed by another program is reloaded when its tab has no unsaved edits. Recent files are on
the File menu; the tabs that were open are reopened on the next start.

## Performance notes

The viewport reads the accumulated image back from the GPU after each pass and paints it (at 1920 × 1080 that is 8 MB
and a few milliseconds on a discrete GPU; FragM reads its tiles back as well). The GPU is busy for as long as a fragment accumulates (FragM's
*continuous* behaviour): *Subframe max* on the toolbar ends it (10 by default; 0 keeps going), the **GPU load limit**
preference idles between passes (50 % halves the load and doubles the time to the same quality), *pause when hidden*
stops the work while nothing is visible, and *Progressive* mode with a stopped clock is idle once the maximum is
reached. Three things keep heavy fragments responsive and clear of the driver's watchdog: the render scale while the camera moves (half size by default, a
preference), the number of subframes per delivered image adapting to the refresh interval, and **automatic tiling** —
a subframe that takes longer than the budget (`FRAG_SUBFRAME_BUDGET_MS`, 500 ms) makes the job draw the following
ones as 2×2, 3×3 … scissored rectangles of the same surface. Hi-res renders are tiled by construction. The GL
display path (a shared-context blit instead of the read-back) is a possible later addition; measured on llvmpipe
the read-back is not the bottleneck.

## Fractalchemy's own fragments

`Examples/Fractalchemy Collection/`: 2D — Nova, Magnet (type I), Phoenix, a gathering Buddhabrot (slow to converge:
*Subframe max* 0 and patience), the Apollonian gasket, Indra's Pearls (inversions in a necklace of kissing circles), a
Kleinian limit set (Jos Leys and Knighty's Maskit-slice construction), the Dragon curves (Heighway, Lévy, twin); 3D —
Amazing Surf and ABoxMod1 (Mandelbulb3D's), FoldingIntPow, Juliabulb, Lambdabulb, the Jerusalem cube, the Mosely
snowflake, a sphere-inversion IFS, the Koch snowflake (2D field, an extruded prism), the 3D Koch snowflake (the
tetrahedron that converges to a cube), a Dragon ribbon, **Indra's Pearls in 3D** (the group generated by inversions
in a chain of kissing spheres — a necklace with poles, or the spheres of a tetrahedron, octahedron or cube; every
pearl is an exact sphere mapped back through the chain of inversions, so the distance estimate is exact; pearls
larger than *PearlSize* are invisible so the nesting shows, and the set can be cut open) and a **3D Kleinian limit
set** (Jos Leys and Knighty's Maskit-slice construction — lattice translation, fold, inversion — coloured by the
nesting depth, with the gasket, a tunnel view and an open tower as presets). `Include/Triplex.frag` has the Mandelbulb arithmetic they
share (`tPow`, `tPowDeriv`, `tMul`, `tDistance`). `Examples/Fractalchemy Tutorials/` are four fragments that teach
by `// STEP n:` comments — a first distance estimator, folds, colouring and orbit traps, animation and rendering —
which the **Walkthrough** dock turns into a clickable list.

## What differs from FragM

* Every program is translated to core-profile GLSL (FragM compiles the legacy text as is); *Show preprocessed source*
  shows the result. A fragment without a `#vertex` block gets a pass-through vertex shader (FragM refuses it). A
  `const float` initializer that calls a function the includes redefined (`Math.frag` wraps `sqrt`, so `const float
  phi = (sqrt(5.0) + 1.0) / 2.0` is no constant expression — NVIDIA's C1059) is evaluated at build time and written
  back as a literal.
* ggr2glsl's blend shapes follow GIMP's reference maths (see *Gradients*); the gradient bridge takes every gradient
  format the host reads, not only `.ggr`.
* Not ported: the shader assembler view (*Shader Asm*, NVIDIA-only), the EXR command-line tools menu, the `.fqs`
  scripting language (replaced by the Python CLI and the batch dialog), Qt-style-sheet themes for the editor, spline
  occlusion by the depth buffer (paths are drawn over the image).
* Added: the library pane with thumbnails, tags, ratings and a parameter index, the `.fafrag` metadata, every host
  image format and EXR with depth, ffmpeg video, stereo pairs and 360° panoramas, render regions, the render queue,
  distributed tile ranges, the *All parameters* interpolation mode with a graph editor, mesh export from the DE (with
  gradient normals, texture baking and a Blender script), the DE exporter to GLSL / Shadertoy / Unity / Unreal, the
  watchdog mitigation, undo for parameters and camera moves, orbit navigation with numpad views and draggable keyframe
  handles, the post stack (bloom, aberration, grain, LUTs), favourites, mutation with a history strip, A/B compare,
  the mini-map, inline diagnostics with go-to-definition, snippets with tab-stops and multi-cursor editing, sessions
  with crash recovery, the Walkthrough dock.
