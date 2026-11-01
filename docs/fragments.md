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
* **Log**: the preprocessor's remarks (*Parse*, *Including file*, `#info` lines, clamped preset values, locked
  variables), *Compiled script in N ms*, and compile errors with the **file and line** they belong to — clicking a
  row opens the file (bundled includes open read-only) at that line; the line is marked in the editor too.
* **Library** (dock, `Ctrl+L`): the bundled examples (read-only — *Save* becomes *Save as*) and your own folders
  (*Library ▸ Add folder to library…*) of `.frag` / `.fafrag` files, with a search box and an optional thumbnail
  view (*Library ▸ Thumbnails*: each fragment rendered once at a small size and cached). Double-click opens a
  tab; drag a file onto the window to open it; the host's library features (copy / move / rename, per-folder
  views) apply to your folders.
* **Grading** (dock, tabbed with Parameters): exposure, tone mapping (Reinhard / filmic / ACES), gamma, contrast,
  saturation, hue shift, vignette, invert — applied by the display pass on top of the fragment's own buffer shader,
  so every change shows at once without touching the accumulation; saved in the `.fafrag`; applies to hi-res renders.
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
   and annotations, and the fragment's own functions.
7. *File ▸ New from template* starts from one of the built-in templates (FragM's New 2D / New 3D, a kaleidoscopic IFS, a
   Mandelbox, a 2D Julia / Mandelbrot with a map, a Shadertoy-style shader, a buffer-feedback system, the fast
   raytracer) or one of yours (*Save as template…* keeps the current source under
   `~/.config/Fractalchemy/fragments/templates`).

### Camera menu

*Add camera bookmark…* (`Ctrl+B`) keeps the current camera under a name in the `.fafrag`; the menu lists the
bookmarks (one click applies one, undoable) and removes them. *Record camera path* (`Ctrl+Shift+R`) samples the
camera every 0.4 s while you fly and, when turned off, writes the samples into the source as `KeyFrame.nnnn`
presets — the path of a flight without pressing `F8` at every turn.

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

| 3D camera (`#camera 3D`: `Eye`, `Target`, `Up`, `FOV`) | |
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

While a button is held the viewport renders at half resolution and one subframe at a time; on release the
full-size accumulation resumes. Esc toggles fullscreen (Shift + right-click shows the menus there).

## Animation

A fragment is animated two ways, both FragM's:

* **The camera path.** For a 3D fragment `F8` inserts a `KeyFrame.nnnn` preset holding the camera (`Eye`, `Target`,
  `Up`, `FOV`, and `FocalPlane` when *AutoFocus* is on). The keyframes are spaced evenly over the animation's length
  and the camera follows a Catmull-Rom spline through them (*Animation ▸ Loop camera path* closes it). The paths are
  drawn over the viewport (*Draw camera paths*); *Clear animation actions* removes the curves, the keyframe presets
  stay in the source.
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
the playhead, double-click a curve to edit it. *Animation* mode plays at the frame rate on a wall clock (a slow
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
* The plan line says what will be drawn; the estimate extrapolates from the viewport's measured subframe speed.

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

`--preset`, `--keyframes`, `--padding`, `--format` (`png16`, `exr`, …), `--depth-alpha`, `--include-path` and `--quiet`
complete the set; the exit code is the number of failures.

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
always locked). LDR images load through Pillow unconverted, `.hdr` and `.exr` as float (`file[sky.exr, R;G;B;A]`
channel selection is parsed; the loader currently takes RGB), `samplerCube` from a strip of six square faces
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

*Edit ▸ Preferences…* (stored per user): **GUI** — recent files, loop play by default, draw camera paths, 2D wheel
mode (zoom towards the pointer or the centre), log rows kept; **Editor** — font size, jump to the first error line,
reload a tab when its file changes on disk; **GLSL** — build on open (*autorun*), auto-build, move `main` to the end
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

Of the 218 bundled examples 211 compile; the seven that do not (listed in `tests/test_fragments_engine.py`) fail in
FragM as well — they use functions before including them, undeclared uniforms, or `double` code that never compiled.

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
*Subframe max* 0 and patience); 3D — Amazing Surf and ABoxMod1 (Mandelbulb3D's), FoldingIntPow, Juliabulb,
Lambdabulb, the Jerusalem cube, the Mosely snowflake, a sphere-inversion IFS. `Include/Triplex.frag` has the
Mandelbulb arithmetic they share (`tPow`, `tPowDeriv`, `tMul`, `tDistance`).

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
* Added: the library pane with thumbnails, the `.fafrag` metadata, every host image format and EXR with depth,
  ffmpeg video, the *All parameters* interpolation mode, mesh export from the DE, the watchdog mitigation, undo for
  parameters and camera moves.
