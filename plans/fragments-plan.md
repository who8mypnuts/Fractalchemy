# Fragments — plan

A new tool window, *Windows ▸ Fragments* (toolbar button, `F12`), that brings **Fragmentarium** — the GLSL fractal
editor and renderer — into Fractalchemy in its entirety: the `.frag` language (preprocessor, `#include`, uniform
annotations → sliders, presets, buffer shaders, cameras), the progressive GPU renderer (subframe accumulation,
tiles, hi-res and animation output), the parameter editor with locks and presets, the 2D / 3D camera controls,
keyframe camera paths and easing curves, textures, and the file workflow — rebuilt in Python / PySide6 / moderngl in
the shape of the rest of Fractalchemy (a Qt-free core, a render service on its own thread, signals and slots, small
modules, tests), with the things the host already does well reused rather than rewritten (the code editor, the
library pane, the job windows, the image writers, ffmpeg, the mesh pipeline).

**Source of truth: FragM 2.5.7** (`samples/fragmentarium/FragM`, 3Dickulus's fork — the most recent and complete
implementation; its `3Dickulus.changes` is the feature log). The original Fragmentarium 1.0 sources are a subset and
are used only where FragM's code is unclear. FragmentariumWeb (a WebGL2 rewrite with its own integrators) is *not*
a source of truth — it replaces the raytracer includes with its own — but two of its ideas are adopted as
extensions (§9.6 interpolated keyframes, §10.1 the embedded thumbnail). The example fragments (`Fragmentarium_Examples_Folder`: 188 runnable `.frag` files in 17
categories + 67 include files, the FragM `Examples/` submodule) and the extra community fragments
(`fragm-formulas`) become the **built-in library** and the compatibility test corpus.

**Decisions taken** (the reasoning is in §17):

1. **Rendering is offscreen moderngl on a worker thread**, read back and painted by a QWidget — the pattern of the
   flame viewport, not FragM's `QOpenGLWidget` on the GUI thread. The GUI never blocks on a slow shader; tiled
   hi-res renders and thumbnails use the same engine; headless tests run on llvmpipe. A shared-context blit is a
   later optimisation behind the same interface (§6.9).
2. **A GLSL compatibility layer** turns the legacy GLSL 1.10 / 1.20 the fragment corpus is written in
   (`gl_FragColor`, `varying`, `gl_Vertex`, `gl_ProjectionMatrix`, `texture2D`) into GLSL 3.30 core (or the version the
   fragment asks for) so fragments run unchanged on core-profile contexts — FragM's "compatibility patch" idea made
   complete and made the default. Validated by a spike: 138 of 188 examples compile through a 100-line prototype
   (appendix C); the remaining failures are prototype gaps with known fixes.
3. **`.fafrag`** is FragM-compatible GLSL text — `.frag` plus an optional Fractalchemy metadata block inside a
   comment (§10.1) — never a JSON wrapper, so every `.fafrag` still opens in FragM and every `.frag` opens here.
4. **The scheduler is shared.** `RenderService` gains an engine-factory hook; the Fragments window owns a second
   instance on its own thread with the fragment engine plugged in. Keys, priorities, supersede / pause semantics are
   reused, not copied.
5. **FragM behaviour is preserved by default** — every preprocessor directive, camera key, settings-text format and
   preset convention — and **extended** only where the host already offers more (undo, a library with thumbnails,
   every image format, ffmpeg, EXR, a richer timeline). Extensions never change what a FragM file means.
6. **Scripting**: FragM's QtScript (`.fqs`) automation is replaced by a Python batch API + CLI (`tools/render_frag.py`,
   §11.6) and a *Batch render presets / keyframes* dialog, which cover every shipped `.fqs` use case.
7. **Phase 1 is the complete editing / rendering loop** (§15): preprocessor, compatibility layer, engine, service,
   window with editor / viewport / parameters / log, presets, cameras — every example renders. Files, library,
   animation, the render window, textures and the extras follow as separately shippable phases.

---

## 1. What the user sees

### 1.1 The window

```
┌ Fragments ─────────────────────────────────────────────────────────────────────────────────────────────────────┐
│ Menu: File  Edit  Build  Render  Parameters  Camera  Animation  Library  Windows  Help                             │
│ Toolbar 1: [New 2D][New 3D][Open][Save][Save as ▾] │ [Undo][Redo] │ [Build F5]●[Auto] │ [Progressive|Animation]     │
│            [⏮][▶][⏹] Subframes [10▴▾] "Done 37" │ Buffer X[1280] 🔒 Y[720] [Lock to window ▾] │ [Render…][Library] │
│ Toolbar 2 (Time): Time 3s:12f [▁▁▁▁▁▁▲▁▁▁▁▁▲▁▁▁▁▁▲▁▁▁▁] length [10] s   fps 25    (▲ = keyframe ticks)            │
├───────────────┬──────────────────────────────────┬────────────────────────────────┬──────────────────────────────┤
│ Library (dock)│ Source tabs  [Mandelbulb.frag ×] │ Viewport                       │ Parameters (dock)            │
│ folders of    │ GLSL editor: line numbers, error │ progressive accumulation,      │ Preset: [Default ▾] [Apply]  │
│ .frag/.fafrag │ marks, highlighting, completion, │ camera control (mouse / keys), │ ┌ Camera ┐ Raytracer  Light  │
│ + Examples    │ find / replace, snippets menu    │ fullscreen (Esc), readouts     │ 🔓 FOV   [====|====] 0.4     │
│ thumbnails    │                                  │ overlay: spline paths, FPS,    │ 🔓 Eye   [=|=======] 1.6…    │
│ search box    │                                  │ "Building…", tile progress     │          [====|====] -1.2…   │
│               │                                  │                                │ …                            │
│               ├──────────────────────────────────┴────────────────────────────────┤ Coloring  Floor  Post        │
│               │ Log (dock): ⓘ Parse: Mandelbulb.frag · ⓘ Compiled in 412 ms ·     │ [Reset all][Reset group]     │
│               │ ⚠ DE-Raytracer.frag:131 warning … (click → jumps to the line)     │ [Lock group][Unlock group]   │
├───────────────┴───────────────────────────────────────────────────────────────────┴──────────────────────────────┤
│ Status: GPU (NVIDIA …) · 1280×720 aspect 1.78 · FPS 31.2 · subframe 37 · X:0.21 Y:-0.04 Z:1.3 · step 0.1         │
└────────────────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

A `QMainWindow` child of the main window like the 3D Editor: closing hides it; geometry, dock layout, open tabs,
the parameter values of every tab and the options are remembered between runs (FragM reopens the tabs that were
open last time; so do we). Docks (Library, Parameters, Log) are movable / stackable / closable (*Windows* menu lists
them). The Parameters dock switches its group tabs between *North* and *East* as it is docked wide or tall, as FragM
does.

### 1.2 Workflow A — open, tweak, look around

1. *Library ▸ Examples ▸ Historical 3D Fractals ▸ Mandelbulb.frag* (or double-click it in the library pane, or
   *File ▸ Open…*, or drop a file on the window). The source opens in a tab; with *Autorun on load* (default) it is
   preprocessed and compiled on the render thread; the log shows *Parse* / *Including* / *Compiled in N ms*; the
   viewport starts accumulating subframes and the status bar counts them.
2. The Parameters dock shows one tab per `#group` — *Camera*, *Raytracer*, *Light*, *Coloring*, *Floor*, *Post* —
   with a slider + spin box per float, three rows per `vec3`, colour swatches, check boxes, menus; the *Default*
   preset is applied. Drag *Power*: the accumulation restarts and the picture re-forms; Ctrl+Z puts it back.
3. Look around: left-drag turns the camera, right-drag pans, both buttons (or the wheel) dolly, `W A S D R F` fly,
   `T G Y H` pitch / yaw, `Q E` roll, `1 / 3` halve / double the step, `5` resets it, Shift+wheel changes it too;
   middle-click puts the *Target* on the surface under the mouse (and the focal plane there when *AutoFocus* is on);
   Shift+`~` looks at the origin. While a button is down the render runs at half resolution and one subframe per
   frame; when it is released the full-resolution accumulation resumes.
4. Lock a slider (the padlock): its value is baked into the shader as a `#define`, the build button lights up,
   *Build* (F5) recompiles — the shader gets faster. *Parameters ▸ Copy settings* (F2) puts the `name = value`
   text on the clipboard; F3 pastes it back; *Group to preset* (F4) / *Insert preset from current settings* (F8) write
   a `#preset` block into the source.

### 1.3 Workflow B — write a fragment

*File ▸ New 3D fragment* (Ctrl+Shift+N) opens FragM's minimal DE fragment (`#include "DE-Raytracer.frag"`, a
`DE()` of a sphere shell, a `Default` preset). Edit the `DE()`; *Build* (or the *Auto* toggle, which rebuilds a moment
after typing stops when the last build took under a second). A compile error is listed in the log with the **file
and line of the original source** (an include's line points into the include; clicking opens it in a tab at that
line, read-only for bundled includes), the line is marked in the editor, and the previous good program keeps
rendering. *Edit ▸ Insert command ▸* offers every preprocessor directive, special uniform, texture option, the
includes on the include path, and *Insert preset from current settings*. *Edit ▸ Templates ▸* has a dozen starters
(§10.5). *Build ▸ Show preprocessed source* opens the exact GLSL handed to the driver; *Build ▸ Test GLSL versions*
compiles the fragment against every version the driver offers and reports which pass.

### 1.4 Workflow C — animate

*Animation* mode (toolbar): `time` advances at the chosen fps while ▶ plays; `F10` rewinds, `F11` plays, `F12` stops,
Space toggles when the viewport has focus. Move the camera, press `F8`: a `KeyFrame.0001` preset is written into the
source holding FOV / Eye / Target / Up; do it again elsewhere; with two or more keyframes the camera follows a
Catmull-Rom path through them over the animation length (ticks on the time slider, the path drawn over the
viewport in Progressive / Stop mode, *Loop camera path* on the Animation menu). Select a float slider, press `F7`:
the **Easing curve** dialog (type, start / end value, frame range, period / amplitude / overshoot, loops, ping-pong,
a curve preview) animates that parameter; *Range-…* presets keep such curves. Right-click the time slider (or
*Animation ▸ Timeline editor*) for the timeline: keyframes and curves on one ruler, draggable. *Render…* with
*Animation* checked writes the frames and, when ffmpeg is installed, the video.

### 1.5 Workflow D — render

*Render ▸ High resolution and animation render…* (Ctrl+R) opens the **Render Fragment** window (the host's job
window shape): **Size** (tile size, *tiles* N×N, *padding*, the resulting image size, aspect lock, *from screen*),
**Quality** (subframes), **Animation** (frame range, fps, length, *preview* frame), **Output** (every image format the
host writes incl. 16-bit PNG / TIFF and OpenEXR with *depth to alpha*, embedded parameters, *save the fragment
with its includes and textures* into a `<name> Files` folder, unique file names), a plan line (`4 × 4 tiles of
1920 × 1080 · 200 subframes · 3200 draws`), an ETA from the viewport's measured subframe time, a tile-by-tile preview,
Start / Pause / Stop, and afterwards a link to the file. Rendering runs on its own thread with its own GL context;
the window can be closed and the editor used meanwhile.

### 1.6 Workflow E — a 3D fractal as a mesh

*Render ▸ Export mesh…* for a fragment that defines `float DE(vec3)`: the DE is sampled on a voxel grid on the GPU
(a generated probe shader around the fragment's own `DE()`), the host's surface-nets isosurface and clean-up
pipeline make a printable mesh with a report, and it is written as OBJ / STL / PLY / glTF / USD — or *sent to the 3D
Editor* as an instancer asset. (The host's `solid/` package does the work; only the DE sampler is new.)

### 1.7 Mouse and keyboard reference (FragM's, verbatim)

| Camera 3D | |
|---|---|
| Left-drag | orient (turn the view) |
| Shift + Left-drag | rotate around the world origin |
| Shift + Alt + Left-drag | rotate around the *Target* |
| Right-drag | translate in the screen plane |
| Left + Right drag | dolly (zoom) |
| Wheel | dolly by step / FOV; Shift + wheel halves / doubles the step |
| Middle click | set *Target* (and *FocalPlane* when *AutoFocus* is on) to the surface point under the cursor |
| Ctrl + Middle click | set `LightPos` (when the fragment has one, e.g. `DE-Kn2.frag`) |
| Click without drag | status bar shows the 3D point under the cursor |
| `W` `S` | forward / back · `A` `D` strafe · `R` `F` down / up |
| `T` `G` | pitch · `Y` `H` yaw · `Q` `E` roll |
| `1` `3` `2` `5` | step ×0.5 · ×2 · ×10 · reset |
| Shift + `~` | look at the origin |

| Camera 2D | |
|---|---|
| Left-drag | pan |
| Right-drag | zoom about the press point |
| Wheel | zoom (*fixed*: about the cursor; *traveling*: centre moves to the cursor — a preference) |
| `A` `D` `W` `S` | pan · `Q` `E` zoom · `1` `3` `2` `X` step ×0.5 · ×2 · ×10 · ×0.1 |

| Window | |
|---|---|
| `F1` reset all parameters · `F2` copy settings · Shift+`F2` copy group · `F3` paste · Shift+`F3` paste selected text · `F4` group → preset | |
| `F5` build · `F7` add easing curve · `F8` add preset / keyframe · `F9` select the current preset in the source | |
| `F10` rewind · `F11` play · `F12` stop · Space play / pause (viewport focused) · Esc fullscreen on / off | |
| Ctrl+N / Ctrl+Shift+N new 2D / 3D · Ctrl+O open · Ctrl+R *render* (Ctrl+Shift+R reload, FragM's Ctrl+R) · Ctrl+S / Ctrl+Shift+S save · Ctrl+W close tab | |
| Ctrl+F find · Ctrl+H replace · Ctrl+G go to line · Ctrl+Z / Ctrl+Shift+Z undo / redo (parameters and camera; the editor has its own) | |

Shortcuts are window-local (`Qt.WindowShortcut`), so the host's `F4`–`F11` window shortcuts are not affected.

---

## 2. FragM feature inventory and where each lands

Every FragM feature, read from `MainWindow.cpp`, `DisplayWidget.cpp`, `Preprocessor.cpp`, `VariableEditor.cpp`, the
widgets, `CameraControl.cpp`, `OutputDialog`, `PreferencesDialog`, `TimeLine`, `EasingWindow`, `VideoDialog`,
`ggr2glsl` and `3Dickulus.changes`. "Module" names are defined in §3; "Phase" in §15.

| FragM feature | Ours | Module | Phase |
|---|---|---|---|
| `#include "file"` resolved relative to the fragment, then the include paths | same order; include paths default to the bundled `Include/` | `fragments/files.py`, `preprocessor.py` | 1 |
| `#buffershader "file"` | same | `preprocessor.py` | 1 |
| `#preset name` … `#endpreset` (presets, `KeyFrame.nnnn`, `Range-…`) | same text format | `preprocessor.py`, `presets.py` | 1 / 3 |
| `#replace "a" "b"` | same | `preprocessor.py` | 1 |
| `#camera 2D` / `3D` | same | `preprocessor.py`, `camera.py` | 1 |
| `#buffer NONE/RGBA8/RGBA16/RGBA16F/RGBA32F` | same (RGBA16 → RGBA16F where the driver lacks normalised 16-bit) | `gl/surfaces.py` | 1 |
| `#group name` | same (tabs; `Default` when empty; falls back to default after an include) | `preprocessor.py`, `parameter_panel.py` | 1 |
| `#vertex` … `#endvertex` | same; the vertex part is modernised too | `preprocessor.py`, `glsl_compat.py` | 1 |
| `#info text` | logged | `preprocessor.py` | 1 |
| `#donotrun` | logged "not a runnable fragment"; library marks it as an include | `preprocessor.py`, `library` | 1 / 2 |
| `#TexParameter name GL_… GL_…` | same (min/mag filter, wrap, max level, anisotropy, mipmaps) | `textures.py`, `gl/textures.py` | 5 |
| `#define DontClearOnChange` | same (accumulation survives parameter edits — feedback fragments) | `gl/surfaces.py` | 1 |
| `#define IterationsBetweenRedraws n` | same (subframes per delivered pass) | `gl/job.py` | 1 |
| `#define SubframeMax n` | same (sets the toolbar value) | `window.py` | 1 |
| `#define providesInit/Color/Background/Normal/Inside/Filtering` | untouched — they are GLSL, handled by the includes | — | 1 |
| `uniform float x; slider[a,b,c] [Logarithmic] [Locked…]` (float/double, vec2/3/4, dvec) | same grammar (FragM's regexes, §4.3) | `preprocessor.py`, `parameters.py` | 1 |
| `uniform int x; slider[a,b,c]` · `menu[d, a;b;c]` · `uniform bool x; checkbox[true]` | same | idem | 1 |
| `uniform vec3 c; color[r,g,b]` · `uniform vec4 c; color[min,def,max,r,g,b]` | same | idem | 1 |
| `uniform sampler2D t; file[name]` (+ `file[name, channels]` for EXR) · `samplerCube` · `isampler2D` / `usampler2D` | same; Pillow / `.hdr` / `.exr` loaders | `textures.py`, `gl/textures.py` | 5 |
| `uniform vec2 pixelSize`, `int subframe`, `float time`, `sampler2D backbuffer/frontbuffer`, `mat4 projectionMatrix`, `globalPixelSize` | same special uniforms | `gl/engine.py` | 1 |
| `uniform bool DepthToAlpha` / `AutoFocus` detection | same | `preprocessor.py`, `viewport.py` | 1 / 4 |
| `#version` handling, "move main to end" (`fragmentariumMain`) | same (preference) + the compatibility layer | `glsl_compat.py` | 1 |
| `#line` directives for error line numbers | our own line map (file, line) per emitted line; driver log parsing for NVIDIA / AMD / Mesa formats | `glsl_compat.py`, `gl/diagnostics.py` | 1 |
| Locked uniforms substituted with `#define` or `const` (preference) | same | `parameters.py` | 1 |
| Lock types Locked / NotLocked / NotLockable / AlwaysLocked | same, same settings-text suffixes | `parameters.py`, `parameter_widgets.py` | 1 |
| Hide widgets for uniforms the compiler optimised away (unless locked) | same (active-uniform query after link) | `gl/engine.py` → `parameter_panel.py` | 1 |
| Float widgets: slider + spin box, 9 (float) / 18 (double) decimals, scientific format, edit scale, edit bounds (rewrites the source line), *Select source* | same | `parameter_widgets.py` | 1 |
| vec3 with `min == max` → normalised direction (except `Up`) | same | `parameter_widgets.py` | 1 |
| Colour widgets with live colour dialog | same; the host's `ColorDialog` | `parameter_widgets.py` | 1 |
| Preset combo, apply, reset all / group, lock / unlock group, copy / copy group / paste, paste from selected text, group → preset, save / load parameters (`.fragparams`), load from PNG | same | `parameter_panel.py`, `document_format.py` | 1 / 2 |
| Settings text `name = v[,v…] [Logarithmic] [LockType]`, warnings on clamping / unknown names | same format | `parameters.py` | 1 |
| Camera 2D / 3D control (full key / mouse set above), step size, `screenTo3D`, depth read at the mouse | same maths | `camera.py`, `viewport.py` | 1 |
| Progressive / Animation modes, subframe max, "Done n", FPS label, continuous rendering, refresh rate | same | `viewport.py`, `window.py` | 1 / 3 |
| Buffer size: lock to window / custom X × Y / aspect lock / from-screen | same | `window.py` (`buffer_size.py`) | 1 |
| Time slider, length (s), fps, `time` uniform, rewind / play / stop, loop play, Space | same | `animation_controls.py` | 3 |
| KeyFrame presets → Catmull-Rom splines for Eye / Target / Up, camera follows in Animation mode, ticks, path overlay (occluded or not), loop camera path | same maths (`QtSpline` port) | `spline.py`, `viewport.py` | 3 |
| Easing curves per float component (12-field string), `F7` dialog, loops, ping-pong, `Range-…` presets, *save easing in presets* preference, timeline editor | same semantics (`QEasingCurve`) | `easing.py`, `easing_dialog.py`, `timeline_window.py` | 3 |
| Hi-res / animation render: tiles, padding, subframes, tile size, aspect lock, frame range, fps, preview, unique names, autosave fragment (+ includes, + textures "release files"), EXR with depth → alpha, 32768 limit, ETA, progress | same + every host format; padding is cropped so seams are exact | `gl/tiles.py`, `gl/final.py`, `render_window.py` | 4 |
| Video encoding dialog (ffmpeg / mencoder) | the host's ffmpeg pipeline (MP4 / H.265 / WebM / ProRes / GIF) | `animation/render.py` reused | 4 |
| Screenshot with parameters in PNG text (`frAg`), preview dialog *Save* | same key, every format's comment field | `document_format.py` | 2 |
| Recent files, tabs, reload, close tab, unsaved marks, file watcher + autoload | same | `window.py`, `tabs.py` | 2 |
| Examples menu built from the examples folder | *Library* menu + library pane with thumbnails | `library_panel.py` | 2 |
| New 2D / New 3D fragment | same text + more templates | `templates.py` | 2 |
| Insert command menu (preprocessor, uniforms, texture options, includes, preset) | same | `templates.py`, `code_editor.py` | 2 |
| Indent script, find, syntax highlighter (GLSL 1.1–4.4 keywords), bracket matching, line numbers, jump to error line, editor themes | `BaseCodeEditor` + GLSL highlighter / completer | `code_editor.py` | 1 |
| Preprocessed-source viewer, *Test GLSL versions*, log window (levels, clickable), log to file, verbose | same | `window.py`, `log_panel.py` | 1 / 5 |
| Fullscreen (Esc), Shift+RMB context menu in fullscreen | same | `viewport.py` | 2 |
| Preferences dialog (GUI / editor / GLSL / application groups, include paths, fps, refresh, compat patch, moveMain, useDefines, autorun, autosave includes, save easing, loop, spline occlusion, 2D camera mode, line numbers, jump to line, GL debug, log file, tile size from screen, texture dialog mimetypes, GIMP gradient paths) | same set minus the tool paths (EXR tools, shader ASM: not applicable) | `preferences_dialog.py` | 5 |
| GIMP gradient → GLSL (`ggr2glsl`) | generalised: any gradient the host reads (`.ugr`, `.ggr`, `.map`, flame palettes, the Gradient Library's current gradient) → GLSL function or 1-D texture | `gradient_glsl.py` | 5 |
| fqScript automation (`.fqs`) + debugger | Python batch API + CLI + *Batch render* dialog | `batch.py`, `tools/render_frag.py` | 4 |
| Shader ASM browser (NVIDIA-only `GL_NV` objdump) | **not ported** (driver-specific; no Python binding) — noted in docs | — | — |
| Command line: `fragmentarium file.frag --autorun --verbose --style …` | `python main.py --fragment file.frag` opens the window on it; `--verbose` maps to the log level | `main.py` | 2 |
| Translations (de / nl / ru) | not ported (the host is untranslated) | — | — |
| Splash / welcome note | *Help ▸ Welcome note* text only | `window.py` | 5 |
| Double-precision uniforms (GL 4.x, `dvec`, `#version 400+`) | same when the context is ≥ 4.0 (uniform upload with `glUniform*d` via moderngl's `d` formats); reported otherwise | `gl/uniforms.py` | 1 |
| Depth buffer: `gl_FragDepth` written by the raytracers, read for `screenTo3D` and EXR depth | depth texture attached to the accumulation surface; one-pixel read after the first subframe | `gl/surfaces.py` | 1 / 4 |
| GPU watchdog (TDR) advice in the FAQ | active mitigation: interactive half-resolution, automatic tiling when a subframe exceeds a time budget, subframes-per-pass adaptation | `gl/job.py` | 6 |

Extensions beyond FragM (all optional, none changes FragM semantics): undo / redo for parameters and camera; a
library pane with thumbnails and search; every host image format; 16-bit and EXR output; ffmpeg video; mesh export
from the DE; gradient bridge; Python batch CLI; automatic build; interpolation of *all* parameters between keyframes
as a selectable mode (§9.6); a GLSL completer; render ETA from measured subframe speed; the
"build in the background while the old program keeps rendering" behaviour.

---

## 3. Architecture

### 3.1 Packages and modules

All new code sits beside the existing packages. Qt-free core first (testable without a display), GL code second
(needs moderngl; tests use llvmpipe through the existing `gl_context` fixture), Qt UI last. Every module is kept
under ~400 lines with the responsibilities listed; functions and classes stay small.

```
fractalchemy/
  fragments/                       Qt-free core of the .frag language and the document (like fractal/, scene3d/)
    __init__.py
    source.py        FragmentSource: the preprocessed program — fragment lines + vertex lines, each with an
                     origin (file, line); params (GuiParameter list, in order); presets {name: text}; textures
                     {uniform: path}; texture_params {uniform: {GL_PARAM: value}}; camera ("2D"/"3D"); buffer
                     ("NONE"/"RGBA8"/…); buffer_shader (FragmentSource | None); flags: clear_on_change,
                     subframes_between_redraws, subframe_max, depth_to_alpha, auto_focus, has_pixel_size;
                     dependencies (every file included); version_line; `text()` / `vertex_text()`; a LineMap
    preprocessor.py  Preprocessor: FragM's `parse()` step by step (§4): include resolution, #buffershader,
                     #preset blocks lifted out, #replace, #camera / #buffer / #group / #vertex / #info /
                     #donotrun / #TexParameter, uniform annotations → params (the regexes of Preprocessor.h,
                     translated literally), moveMain, `create_autosave_fragment()` (includes flattened, presets
                     stripped, for "save the fragment with the render"); never touches GL
    parameters.py    the parameter model: LockType, SliderType, GuiParameter + Float/Float2/3/4/Color/FloatColor/
                     Int/IntMenu/Bool/Sampler parameters (unique_name as FragM's: group:name:from:default:to),
                     Value parsing / formatting (FDEC 9 / DDEC 18 significant digits, `.0` for GLSL), clamping
                     with warnings, the settings text (`name = v,v,v [Logarithmic] [LockType]`) read / write,
                     `locked_substitution(param, value, use_defines)` → `#define` / `const` line
    state.py         ParameterState: {name: value} + lock / slider overrides for one fragment; apply_preset(),
                     to_settings_text(provenance), from_settings_text() → (changed names, recompile needed,
                     warnings); camera_settings() (FOV/Eye/Target/Up or Center/Zoom); diff for undo merging
    files.py         FileManager: include paths, original file, resolve_name() (absolute → beside the fragment →
                     include paths, FragM's order, with "tried paths"), file_exists(), image extensions, getFiles()
                     with the filter cache; the bundled Include folder is always the last include path
    glsl_compat.py   the compatibility layer (§5): target version choice, vertex / fragment preludes, legacy
                     built-in rewrites, declaration de-duplication, wrapper functions, `#extension` handling,
                     output keeps a LineMap so driver errors map back to (file, line)
    camera.py        Camera2D / Camera3D: pure functions on (eye, target, up, fov) / (center, zoom, transform):
                     key steps, mouse drags (orient, orbit origin, orbit target, pan, dolly), wheel, step size
                     rules, orthogonalise_up(), screen_to_3d(), 2D model coordinates and the rotate / stretch
                     matrix, the "fixed" and "traveling" wheel modes — FragM's CameraControl.cpp made Qt-free
    spline.py        Catmull-Rom camera path (QtSpline's basis and its end-point "fudge", loop mode), KeyFrame
                     parsing (`KeyFrame.nnnn` presets → eye / target / up), frames → (eye, target, up) at frame
    easing.py        EasingCurve setting (the 12-field string) parse / format, evaluate(frame) with loops and
                     ping-pong exactly as DisplayWidget::updateEasingCurves, using QtCore.QEasingCurve by type
                     number (QtCore is GUI-free; the host's library/ already uses QObject in "core")
    presets.py       preset text helpers: build a preset block from a ParameterState (with / without
                     provenance comments), KeyFrame naming / numbering, Range presets (easing settings only),
                     find / replace a preset block in source text, `select preset text range` for F9
    document_format.py  .frag / .fafrag read / write (§10.1): the `/*[fractalchemy] … [/fractalchemy]*/` metadata
                     block (JSON: render settings, animation settings, library tags, thumbnail); `.fragparams`;
                     parameters embedded in images (PNG `frAg` text key; other formats via render/output.py)
    textures.py      texture decoding to numpy (Pillow; .hdr / .exr via solid/hdri.py — EXR channel selection
                     "R;G;B;A" as FragM), cubemap strips (+x −x +y −y +z −z in a row), #TexParameter → GL
                     parameter names / values, integer textures for isampler2D / usampler2D, cache keys
    templates.py     built-in fragments (New 2D / New 3D as FragM's strings, plus the starters in §10.5), the
                     Insert-command snippets (§10.6), the user templates folder (per-user data dir / fragments)
    examples.py      the bundled library: package-data paths (`fragments/library/Include`, `/Examples`), the
                     categorised tree, attribution text
    batch.py         headless API: render_presets(path, out_dir, …), render_keyframes(…), render_frames(…),
                     compile_check(path) — used by tools/render_frag.py and the Batch dialog
    gradient_glsl.py Gradient → GLSL (`vec3 gradient(float t)` as a const array + mix, or a 1-D texture block);
                     GIMP `.ggr` segments (ggr2glsl's blend / colour types) through the host's gradient model
    gl/                              moderngl side (imports moderngl; created on the thread that owns the context)
      engine.py      FragEngine: owns the context (created via render/gpu_engine.create_context), capability
                     report (GL / GLSL versions, max texture size, double support), the program cache keyed by
                     the modernised source text, `build(source) -> Program` (compile + link, diagnostics
                     mapped through the LineMap, ShaderBuildError with the report file like gpu_engine),
                     the fullscreen-triangle VAO, `start(payload, settings) -> FragJob` (the service protocol)
      program.py     Program: the linked main program (+ buffershader program), active-uniform table
                     {name: (type, size)} for "unused" detection and type-correct upload, texture units
      uniforms.py    upload helpers: ParameterState value → moderngl uniform by declared GLSL type (int / bool /
                     float / double / vec / dvec / sampler), the special uniforms (pixelSize, subframe, time,
                     backbuffer = 0, frontbuffer, projectionMatrix, globalPixelSize), tile projection matrix
      surfaces.py    Surface: the ping-pong pair of FBOs (colour RGBA8 / 16F / 32F + depth texture) for one
                     render key, swap(), clear(), `subframe` counter, depth_at(x, y), read_rgba8() / read_float()
                     and the SurfaceCache {key: Surface} that lets a re-submitted key keep its accumulation
                     (DontClearOnChange, buffershader-only changes)
      textures.py    GL textures from textures.py arrays (2D, cube, integer formats), #TexParameter application
                     (mipmaps generated first), the texture cache {(path, channels): Texture} with unused-eviction
      job.py         FragJob: the service's job protocol (`stats`, `run_pass(cancelled)`, `close()`): each pass =
                     `subframes_between_redraws + 1` subframe draws (backbuffer → frontbuffer, swap) then the
                     display pass (buffershader or straight copy) into an RGBA8 target and a read-back;
                     stats.passes_* = subframes; interactive scale; time budget watch (§6.8)
      tiles.py       tile maths: projection matrix for tile (i, n, padding), tile placement, padding crop,
                     the 32768 guard, plan description (`describe_plan`)
      final.py       FragFinalRenderer: tiles × subframes with RenderControl (pause / cancel), per-frame camera
                     (splines) and easing values, assembly into one float image, depth-to-alpha, progress
                     callbacks with ETA; frame loops for animation; writes through render/output.py + exr.py
      diagnostics.py driver log parsing (NVIDIA `0(12) : error C…`, AMD `ERROR: 0:12:`, Mesa `0:12(5): error:`)
                     → (line, message) → LineMap → (file, line); the glsl-failures report writer reused
      mesh.py        DE → voxel grid: a probe program (the fragment's source with a generated main that writes
                     `DE(p)` for a slice of points) rendered slice by slice into R32F targets → VoxelGrid →
                     solid.isosurface / solid.mesh / solid.pipeline exports
  ui/fragments/                    the window (Qt)
    __init__.py      exports FragmentsWindow
    window.py        FragmentsWindow(QMainWindow): menus, toolbars, docks, splitter, status bar, persistence,
                     coordination only (≈ 450 lines); the heavy lifting is in the modules below
    actions.py       the QActions / menus / toolbars (make_action + populate from widgets/actions.py)
    document.py      FragDocument(QObject): one open fragment — source text, path, modified, the last good
                     FragmentSource and Program facts, ParameterState with an undo history (merge keys for
                     drags), presets, lock state, camera kind; signals: source_changed, built, build_failed,
                     parameters_changed(names, recompile), preset_applied, camera_changed, modified_changed,
                     undo_changed; `needs_build` flag (FragM's highlighted Build button)
    tabs.py          TabManager: QTabBar + QStackedWidget of GlslCodeEditors, one FragDocument per tab, close /
                     reload / unsaved prompts, "tabs remember their parameters", session restore
    viewport.py      FragViewport(QWidget): paints the latest read-back image (fitted, or 1:1 for custom buffer
                     sizes), mouse / key / wheel → camera.py → document, interactive scale, FPS, "Building…"
                     overlay, spline path overlay (QPainter, projected with the 3D camera; optional depth
                     occlusion using the depth read), fullscreen, Shift+RMB menu, status readouts
    render_driver.py RenderDriver(QObject): the glue between a FragDocument, the viewport and the
                     RenderService — decides what to submit when (build, parameter change with / without clear,
                     buffershader-only change, camera drag, time tick, mode switch, subframe max), owns the keys,
                     keeps the surface semantics (DontClearOnChange), collects stats for the status bar
    parameter_panel.py  ParameterPanel: the group tabs, preset combo + Apply, widget creation from params
                     (unique-name matching so widgets survive a rebuild), hide-unused, group actions, copy /
                     paste, context menu
    parameter_widgets.py  ComboSlider (slider + ExpSpinBox; linear / logarithmic; 9 / 18 decimals; scientific;
                     context menu: select source / edit scale / bounds), FloatWidget, Float2/3/4Widget
                     (normalised directions), IntWidget, IntMenuWidget, BoolWidget, ColorWidget, FloatColorWidget,
                     SamplerWidget (file combo + 4 channel combos + browse), lock buttons; all emit
                     `changed(name, value, locked_changed)` — no knowledge of GL
    code_editor.py   GlslCodeEditor(BaseCodeEditor) + GlslHighlighter (keywords by version, built-ins, the
                     preprocessor directives and uniform annotations, `#preset` blocks dimmed) + a completer
                     (GLSL built-ins, the fragment's uniforms / functions, snippets), bracket matching
    log_panel.py     LogPanel: levels (info / warning / error / script), clickable `file:line`, max lines, copy,
                     clear, *log to file*
    buffer_size.py   BufferSizeBar: X / Y spin boxes, aspect lock, "Lock to window / Custom size" menu — FragM's
                     getBufferSize() logic
    animation_controls.py  time toolbar (label, slider with keyframe ticks, length, fps), Progressive / Animation,
                     rewind / play / stop, subframe max, "Done n"; the wall clock (like animation_playback.py)
    easing_dialog.py the F7 dialog (EasingWindow port: curve picker with previews, period / amplitude /
                     overshoot, value and frame ranges, loops, ping-pong, Apply / Discard / Cancel)
    timeline_window.py  the timeline editor (widgets/timeline.py for the ruler + keyframes; easing curve lanes)
    render_window.py FragRenderWindow(JobWindowBase): Size / Quality / Animation / Output panels, plan + ETA,
                     tile-by-tile preview, the FragRenderJob thread
    render_panels.py the panels of the render window (tile / subframes / animation); reuses OutputPanel and
                     render_size_panel pieces
    batch_dialog.py  render every preset / keyframe to images (batch.py on a thread)
    library_panel.py the fragment library pane (library/ machinery + FRAGMENT_CATALOG + a ThumbnailProvider that
                     renders through the fragment service at low priority)
    mesh_export_dialog.py  DE → mesh settings (resolution, bounds, iso, clean level), progress, export formats,
                     *Send to 3D Editor*
    gradient_dialog.py  gradient → GLSL (pick from the Gradient Library / a file; preview; insert or copy)
    preferences_dialog.py  the preferences (§12.4)
    help.py          Mouse & keyboard help, welcome note, the language reference (docs/fragments.md rendered)
  render/service.py  +EngineFactory hook (§6.4) — the only change to an existing module besides the main window
  widgets/icons.py   +fragments_icon(), small glyphs (lock, play / stop / rewind already exist or come from the theme)
  library/catalog.py +FRAGMENT_CATALOG (.frag / .fafrag; one entry per file; rename / delete / duplicate)
  ui/main_window.py  +show_fragments(), the action, closeEvent handling
ui/main_window.ui    +actionFragments in menuWindows and the toolbar
tools/render_frag.py the CLI (§11.6)
docs/fragments.md    the user guide + language reference (`.frag` directives, annotations, special uniforms)
tests/test_fragments_*.py  (§14)
fractalchemy/fragments/library/   package data: Include/ (67 files), Examples/<category>/… (188 + community),
                     ATTRIBUTION.md (per-file licences as in the sources)
```

### 3.2 Data flow

```
 editor text ──(Build)──▶ Preprocessor.parse ──▶ FragmentSource ──▶ glsl_compat.modernise ──▶ (vertex, fragment, LineMap)
                                │                      │                                              │
                                │                      ├─ params ──▶ ParameterState (defaults, preset) ─┐  │
                                │                      └─ presets / textures / flags                  │  │
                                ▼                                                                     ▼  ▼
                           log panel ◀────────── diagnostics ◀──────── FragEngine.build (render thread) ◀── RenderService.submit(key, FragRequest)
                                                                                │
 ParameterPanel ◀──▶ FragDocument ──▶ RenderDriver ──▶ FragRequest(program source, values, camera, time, size, tile, flags)
                                                                                ▼
 FragViewport ◀── pass_done(key, rgba8, stats) ◀── FragJob.run_pass: subframes into Surface (ping-pong) → display pass → read back
```

* A **FragRequest** is the immutable payload of one render: the modernised sources (or their cache key), the
  uniform values (already clamped / typed), texture references, the special uniform values (time, size, tile), and
  the surface policy (`clear`, `redisplay_only`, `subframes`, `subframes_per_pass`). It has `.copy()` for the service.
* **Compilation happens on the render thread** (contexts are thread-bound). The GUI submits; the job's first
  `run_pass` compiles (cached by source text) and the window shows *Building…* until the first image arrives or
  `job_failed` carries the mapped diagnostics. The previously compiled program keeps rendering in the meantime
  because a *failed* build does not replace the surface or the last image.
* **Parameter edits** do not recompile: the request changes values only; the engine re-uses the cached program.
  Locks (and anything that changes the preprocessed text) set `needs_build`.

### 3.3 Threading model

| Thread | Owns | Talks to the GUI via |
|---|---|---|
| GUI | windows, documents, parameter state, editors, the camera maths (cheap) | — |
| Fragment render thread (`RenderService` #2) | one `FragEngine` + GL context, program cache, surfaces, textures | `engine_ready`, `pass_done(key, image, stats)`, `job_finished`, `job_failed(key, message)` |
| Final render thread (`FragRenderJob`, a `QThread` per render, like `FinalRenderJob`) | its own `FragEngine` + context | `progressed(FragProgress)`, `succeeded(FragOutcome)`, `failed(str)` |
| Mesh export thread (`MeshFromDEJob`) | its own `FragEngine` + context for the DE probe, then numpy | `progressed`, `finished_with`, `failed` |
| Thread pool (`run_in_background`) | file loads, include scans, library scanning, texture decoding to numpy (upload happens on the render thread) | callbacks on the GUI thread |

Rules: no GL call outside the thread that created the context; numpy arrays cross threads by value (the service
already copies payloads); `RenderControl` (cancel / pause) is the shared flag object for the final renderer; the
viewport never waits on the render thread — a newer submit supersedes the older job between subframes.

### 3.4 Signals and slots inventory (the ones that define the design)

* `FragDocument`: `source_changed()`, `needs_build_changed(bool)`, `built(FragmentSource, BuildFacts)`,
  `build_failed(list[Diagnostic])`, `parameters_changed(names: list[str], recompile: bool, buffer_only: bool)`,
  `preset_applied(str)`, `camera_changed()`, `path_changed(Path|None)`, `modified_changed(bool)`,
  `undo_changed(bool, bool)`.
* `ParameterPanel`: `value_edited(name, value, merge_key)`, `lock_toggled(name, LockType)`, `bounds_edited(name,
  which, bound, value)` (→ source edit), `select_source_requested(name)`, `preset_chosen(name)`,
  `group_action(kind, group)`.
* `FragViewport`: `camera_edited(settings_text, interactive: bool)`, `point_picked(x, y, z, button, modifiers)`,
  `render_progress(RenderStats)`, `render_failed(str)`, `fullscreen_toggled(bool)`.
* `RenderDriver`: `stats_changed(RenderStats)`, `fps_changed(float)`, `subframe_changed(int)`, `building(bool)`.
* `AnimationControls`: `frame_changed(int)`, `mode_changed(str)`, `play_state_changed(bool)`, `length_changed(int)`,
  `fps_changed(int)`, `subframe_max_changed(int)`.
* `TabManager`: `current_changed(FragDocument|None)`, `document_closed(FragDocument)`.
* `FragmentsWindow`: `status(str)` to the host's status bar; `fragment_rendered(Path)` for the library thumbnails.

---

## 4. The `.frag` language: preprocessor specification (FragM parity)

The preprocessor is a literal translation of `Preprocessor.cpp` / `Preprocessor.h`; the regular expressions are
ported one for one (Qt `QRegExp` → Python `re`, with `\S`, `\s`, `\d` and the `{,1}` / `{5,6}` quantifiers checked
against Qt's semantics — `[d]{,1}` means an optional `d`, `[float|double]{5,6}` is a character class, so a literal
translation would accept `fllllo`; we translate intent: `(float|double)`, `(true|false)`). The corpus is the test:
every parameter FragM finds in the 188 examples, we find, with the same group / default / range / lock / slider
type (§14.2 records a snapshot).

### 4.1 `parse_source` — includes and the raw line list

1. Split on `\r\n|\r|\n`. Record `(file_index, line_number)` for every line (this replaces FragM's `#line`
   arithmetic: the LineMap is carried through every later transform instead).
2. `#include "name"` — matched **only at column 0** (FragM's `^#include(.*)\s"([^"]+)"\s*$`), so an indented
   `#include` in a comment block (ComplexBase.frag's documentation) is ignored exactly as FragM ignores it. The file is
   resolved through `FileManager.resolve_name` (absolute; beside the including file; each include path in order)
   and parsed recursively **textually, every time** — `Complex.frag` includes `ComplexBase.frag` twice under
   `#if __VERSION__ >= 400`, and it must stay that way. A missing file is a critical log entry; the line is dropped
   and parsing continues (FragM: `CRITICAL` + `continue`). Include depth is capped at 32 with a clear error to turn an
   include cycle into a message rather than a recursion error. Dependencies are collected (for autosave copies).
3. `#buffershader "name"` — parsed as a separate `FragmentSource` with `move_main=False`; it receives the
   fragment's `#version` line when it lacks one (FragM inserts it).
4. `#group default` is appended after every included file (FragM does), so groups do not leak out of includes.
5. The `#version` line of the first (user) file is remembered (`version_line`) for the compatibility layer.

### 4.2 `parse` — the second pass over the merged lines (in FragM's order)

For each line `s`:

1. `#preset name` (case-insensitive, trimmed) lifts every line up to `#endpreset` out of the source into
   `presets[name]` (a missing `#endpreset` is a warning). Preset names keep their case; `KeyFrame.0001`,
   `Range-0010-0100` are ordinary presets to the preprocessor.
2. `#replace "from" "to"` adds a replacement rule (the directive itself is commented out); every **later** line
   has `from` → `to` applied textually (FragM applies the map to each line before the directive check).
3. "Specials" (each is replaced by `// <line>` so line numbers hold): `#camera 2D|3D`, `#TexParameter u p v`
   (three words, else a warning), `#buffer TYPE`, `#donotrun`, `#group name`, `#vertex` / `#endvertex` (lines in between
   move to `vertex_source` and are commented out in the fragment), `#info text` (logged at script level), and with
   `move_main`: `void main(` → `void fragmentariumMain(`.
4. Uniform annotations (§4.3) — the first regex that matches wins, in FragM's order: `sampler2DChannel`,
   `sampler2D`, `samplerCube`, `floatColorChooser`, `float1Slider`, `float2Slider`, `float3Slider`, `float4Slider`,
   `colorChooser`, `intMenu`, `intSlider`, `boolChooser`; then `#define DontClearOnChange`, `#define
   IterationsBetweenRedraws n`, `#define SubframeMax n` (all case-insensitive). A matched uniform line is replaced
   by the bare declaration `uniform <type> <name>;` and a `GuiParameter` is appended with the current group and the
   **tooltip = the comment line immediately above** (`lastComment`).
5. `isampler2D` / `usampler2D` file annotations (FragM declares the regexes but handles them through the sampler
   widgets): treated like `sampler2D` with an integer texture format.
6. Magic uniform detection on the whole source: `uniform vec2 pixelSize` → `has_pixel_size`; `uniform bool
   DepthToAlpha` → `depth_to_alpha`; `uniform bool AutoFocus` → `auto_focus` (case-insensitive, as FragM).
7. With `move_main`, `void main() { fragmentariumMain(); }` is appended so `main` is the last definition.
8. Version consistency: the vertex source gets the fragment's `#version` when it has none; a mismatch is a warning.

### 4.3 Uniform annotation grammar (from `Preprocessor.h`, `NUMf` / `NUMi`)

```
NUMf  := [-+]? digits? (. digits?)? ([eE] [+-]? digits)?      (whitespace around)
NUMi  := [-+]? digits
slider_type := (Linear|Logarithmic)?          lock_type := (Locked|NotLocked|NotLockable)? .?$

uniform (float|double) NAME; slider[NUMf,NUMf,NUMf] slider_type lock_type          → FloatParameter(from, default, to)
uniform (d?vec2) NAME; slider[(f,f),(f,f),(f,f)] …                                 → Float2Parameter
uniform (d?vec3) NAME; slider[(f,f,f),(f,f,f),(f,f,f)] …                           → Float3Parameter
uniform (d?vec4) NAME; slider[(f,f,f,f),(f,f,f,f),(f,f,f,f)] …                     → Float4Parameter
uniform (d?vec3) NAME; color[f,f,f] lock_type                                      → ColorParameter(rgb)
uniform (d?vec4) NAME; color[min,default,max, r,g,b] lock_type                     → FloatColorParameter(value + rgb)
uniform int NAME; slider[i,i,i] lock_type                                          → IntParameter
uniform int NAME; menu[i, text;text;…] lock_type                                   → IntMenuParameter
uniform bool NAME; checkbox[true|false] lock_type                                  → BoolParameter
uniform sampler2D NAME; file[name]  |  file[name, channels]                        → SamplerParameter (AlwaysLocked)
uniform samplerCube NAME; file[name]                                               → SamplerParameter
```

Semantics kept: `d`-prefixed types set `is_double` (18 significant digits, `dvec` upload); unparsable numbers log a
warning and skip the parameter (the bare uniform stays, so the shader still compiles); lock types default to
`NotLocked`, samplers are `AlwaysLocked`; a `vec3` slider whose `from == to` becomes a **normalised direction**
widget (`(-1,-1,-1)…(1,1,1)`), except one named `Up` (FragM: spline animation needs it un-normalised);
`unique_name` (group:name:from:default:to) decides whether an existing widget survives a rebuild.

### 4.4 Special uniforms and defines (set by the engine, never by the user)

| Name | Type | Value |
|---|---|---|
| `pixelSize` | vec2 | `(1/w, 1/h)` of the **buffer being drawn** (a tile's size when tiling — FragM's choice; `aaScale` compensates with `projectionMatrix`) |
| `globalPixelSize` | vec2 | same, kept for `DepthBufferShader.frag` / `NODE-Raytracer.frag` |
| `subframe` | int | 0-based counter of accumulated subframes (FragM increments before the draw: first draw sees 1 — **we match FragM**: the first subframe is 1) |
| `time` | float | frame / fps in Animation mode; the stored time when stopped; 0 in Progressive unless the slider was moved |
| `backbuffer` | sampler2D | texture unit 0: the previous subframe's accumulation |
| `frontbuffer` | sampler2D | unit 0 in the buffershader: the accumulated image to tone-map |
| `projectionMatrix` | mat4 | identity, or the tile transform (§6.6) — the legacy `gl_ProjectionMatrix` |
| `DepthToAlpha`, `AutoFocus` | bool | user check boxes whose presence the host reacts to |
| `#define DontClearOnChange` | — | parameter edits reset `subframe` but keep the buffers (feedback systems) |
| `#define IterationsBetweenRedraws n` | — | n+1 subframes per delivered image |
| `#define SubframeMax n` | — | sets the toolbar's subframe maximum when the fragment is built |

### 4.5 Deliberate improvements (documented in `docs/fragments.md`, off by default where they change behaviour)

* Include-cycle detection (error instead of a crash).
* The line map replaces `#line` (drivers disagree about `#line` semantics after a `#version` change; FragM's
  arithmetic has several special cases — ours is exact by construction).
* `#include <name>` (angle brackets) is accepted as a synonym restricted to the include paths. *Extension.*
* Warnings for a `slider[...]` whose default is outside `[from, to]` (FragM clamps silently into the widget).

---

## 5. GLSL compatibility layer (`glsl_compat.py`)

The corpus targets GLSL 1.10 / 1.20 (16 files say `#version 120`, four `130`, three `330 / 400 / 410
compatibility`, the rest nothing → 1.10). Core-profile contexts — what moderngl creates on every platform, what
macOS offers exclusively, what AMD enforces — reject the legacy built-ins. FragM injects a macro patch and
requests a compatibility profile where it can (Windows). We make the translation complete and deterministic, in
three steps, keeping the LineMap (inserted preludes map to `None`, so an error there is reported as "in the
compatibility prelude" with the prelude text).

### 5.1 Target version

* Requested = the fragment's `#version N [profile]` or 110 when absent. Target = `max(330, requested)`; the
  profile word is dropped (`compatibility` → core). If requested > the context's GLSL version, the build fails with
  *this fragment needs GLSL N; the driver offers M* (and the capability report).
* `double` / `dvec` / `#extension GL_ARB_gpu_shader_fp64` in the source with target < 400 → target 400 when the
  context allows (FragM relied on the `#version 4x0` line being present; we also infer).
* A **preference** keeps FragM's behaviour available: *Compatibility layer: Modernise (default) · Patch only (FragM's
  macros, for drivers with a compatibility context) · Off*. A failed *Modernise* build automatically retries *Patch
  only* once when the context reports a compatibility profile, and logs which variant ran.

### 5.2 Vertex shader prelude (after `#version`)

```glsl
layout(location = 0) in vec4 vertex_position;   #define gl_Vertex vertex_position
uniform mat4 projectionMatrix;                  #define gl_ProjectionMatrix projectionMatrix
#define varying out
```
(FragM's `fvSourcePatch`, minus the ES branches.) The engine always draws the same fullscreen triangle
`(-1,-1) (3,-1) (-1,3)` FragM draws (`points[9]`), so `gl_Position = gl_Vertex` works.

### 5.3 Fragment shader prelude and rewrites

```glsl
#define varying in
out vec4 fragColor;          #define gl_FragColor fragColor
```
plus **wrapper functions instead of macros** for the texture calls — `vec4 texture2D(sampler2D s, vec2 c) { return
texture(s, c); }`, `texture2DLod`, `textureCube`, `shadow2D` — emitted only for the sampler types actually used,
because a fragment may define its own `texture(...)` function (eiffieGI2's Kisocahedron does, and a
`#define texture2D texture` then breaks it — found by the spike). `gl_FragDepth` and `gl_FragCoord` are valid in
core and pass through. `gl_FragData[n]` → `layout(location=n) out vec4 fragData_n` + `#define` when present.
Deprecated `noise1..4` are replaced by a hash-based noise with a warning (no driver implements them anyway).

### 5.4 Declaration hygiene

Legacy compilers tolerated what 3.30 rejects; the layer fixes the mechanical cases and leaves the rest to the
log:

* duplicate `varying` / `uniform` / `attribute` declarations (the same line appearing through two includes —
  `3D.frag` declares `uniform int subframe;` in both halves; `Progressive2D.frag` and a user file both declare
  `uniform vec2 pixelSize;`) — de-duplicated by normalised text;
* a `#version` line anywhere but the first line is removed (the prelude carries the target);
* `precision` statements are kept (harmless in core);
* `#extension GL_ARB_gpu_shader_fp64 : enable` is kept; `GL_EXT_gpu_shader4` → removed with a note;
* `attribute` → `in` in vertex code;
* integer / float implicit conversions are legal in 3.30 as in 1.20 — nothing to do.

### 5.5 Diagnostics

`gl/diagnostics.py` parses the three driver formats, maps the emitted line through the LineMap to `(file, line,
column, message, severity)`, attaches the offending source line, and the log panel shows `file:line — message`
(clickable). The whole modernised source + driver log is written to `<cache>/Fractalchemy/glsl-failures/` exactly as
`gpu_engine._dump_failure` does today (reused). *Build ▸ Show preprocessed source* shows the modernised text with a
gutter of original `file:line` references, so what the driver saw is never a mystery.

### 5.6 Validation (phase 1 acceptance)

The spike (appendix C) compiled 138 / 188 examples with a naive moderniser; the 50 failures split into: include
resolution / recursion bugs of the prototype (31 — a real `FileManager` fixes them), the `texture` macro clash (1),
genuinely broken or dependency-missing fragments that also fail in FragM (`iResolution` without the Shadertoy include,
a `vec4` returned from a `vec3` function: 4–6), and order-of-definition issues (`rand2` used before MathUtils is
included: 3 — FragM fails the same way; verified by reading). Target: **every example that compiles in FragM compiles
here**, recorded as a fixture list with the per-file outcome so regressions are visible (`tests/test_fragments_corpus.py`).

---

## 6. Rendering

### 6.1 Surfaces (`gl/surfaces.py`)

A `Surface` is FragM's `backBuffer` / `previewBuffer` pair: two FBOs of the fragment's `#buffer` type (default
RGBA32F when a buffershader exists or the fragment reads `backbuffer`; FragM warns "trying to use a backbuffer but no
buffer type" and we do too) with a **depth texture** (`gl_FragDepth` from the raytracers; read for `screenTo3D` and
EXR depth). `subframe` lives on the surface. Operations: `clear()` (both FBOs to transparent black + depth 1.0),
`swap()`, `draw_target()` / `back_texture()`, `depth_at(x, y)`, `read_rgba8()` (display) and `read_float()` (final
renders). A `SurfaceCache` keyed by the render key keeps surfaces alive across jobs so that:

* `DontClearOnChange` fragments (Game of Life, Reaction-Diffusion, Droste feedback) keep their state through
  parameter edits (FragM: `subframeCounter = 0`, buffers kept);
* a *buffershader-only* change (Post group sliders: Gamma, Exposure, ToneMapping…) re-runs only the display pass
  (FragM's `bufferShaderOnly`) — instant tone-mapping changes without losing accumulation;
* a resize / buffer-type change / build replaces the surface.

### 6.2 The job (`gl/job.py`) — FragM's `drawToFrameBufferObject` as a service job

```
run_pass(cancelled):
    if program not built: build (cache) — raises ShaderBuildError with mapped diagnostics
    if request.clear or surface missing or size/type changed: surface = new / cleared
    if not request.redisplay_only:
        for i in range(subframes_between_redraws + 1):
            if cancelled(): return None                      # a newer request superseded us between subframes
            surface.swap(); surface.subframe += 1
            bind backbuffer (unit 0), set special uniforms (pixelSize, subframe, time, projectionMatrix)
            on the first subframe of the job: upload every user uniform (typed), bind textures (units 1…)
            draw the triangle into surface.front (depth test ALWAYS, depth write on — FragM's state)
    display pass: buffershader (frontbuffer = surface.front, its own user uniforms) or a straight copy → RGBA8 FBO
    read back RGBA8 → (H, W, 4) uint8; stats.passes_done = surface.subframe; stats.seconds += …
    return image
```

`stats.passes_total` = the subframe maximum (0 = unlimited → a large sentinel so the service's *refine* logic keeps
going while idle and yields to other keys — the library thumbnails — between passes). `RenderStats.samples` counts
subframe × pixels so `samples_per_second` feeds the ETA. The first pass of a job also reports `BuildFacts` (compile
ms, active uniforms, unused uniforms, GL strings) through `stats.notes` / a dedicated signal.

### 6.3 Uniform upload (`gl/uniforms.py`)

Values come typed from `ParameterState` (the GLSL type from the annotation). Upload by the **program's active
uniform type**, not the annotation, as FragM does (`setShaderUniforms` walks `GL_ACTIVE_UNIFORMS`): an `int`
annotation on a `float` uniform still works; a uniform the compiler removed is skipped and reported as *unused* so
the panel hides its widget (unless locked). Doubles go through moderngl's `d` formats when the context is ≥ 4.0.
Samplers are set to their texture unit. Bools as ints. The buffershader receives the union of values (FragM adds
buffershader params not present in the main fragment to the same panel).

### 6.4 The service (`render/service.py` generalisation)

```python
class EngineFactory(Protocol):
    def create(self) -> Engine: ...                       # on the worker thread; sets service.engine_name
    def fallback(self, engine, exc) -> Engine | None: ...  # a second engine for payloads the first rejects (flames: CPU)
RenderService(parent, prefer_gpu=True, factory: EngineFactory | None = None)
submit(key, payload: HasCopy, settings, priority)         # payload.copy(); settings may be any object the engine accepts
```
The default factory reproduces today's GPU-then-CPU behaviour (no behaviour change for the flame windows — the
existing tests guard it). The Fragments window creates `RenderService(factory=FragEngineFactory())`; the fragment
engine's `start(FragRequest, FragRenderSettings)` returns a `FragJob`. Priorities: `PRIORITY_EDITOR` for interactive
camera drags, `PRIORITY_VIEWPORT` for the viewport, `PRIORITY_THUMBNAIL` for the library.

### 6.5 Interactivity

* While a mouse button is down (or a key held) the driver submits `scale = INTERACTIVE_SCALE` requests with one
  subframe per pass under the interactive priority (FragM: `buttonDown → pendingRedraws = 1`); on release a
  full-resolution request resumes accumulation. The last image is repositioned, never stretched wrongly: the
  viewport letterboxes at the buffer aspect like the 3D viewport.
* A parameter slider drag coalesces: at most one request in flight per `EDITOR_PREVIEW_THROTTLE_MS`, a trailing
  full request on release (the host's pattern).
* Continuous mode (Animation ▶, or Progressive with subframes remaining) is driven by the service's refine loop,
  not a timer: the job keeps adding subframes until `subframe_max`; the *refresh rate* preference only bounds how
  often images are read back (subframes per pass adapt to hit ~`1000/refresh_ms` deliveries per second).

### 6.6 Tiles (`gl/tiles.py`) — FragM's `renderTile`

For tile `i` of `n × n` with padding `p`: `x = i // n − (n−1)/2`, `y = i % n − (n−1)/2`;
`projectionMatrix = translate(x·2/n, y·2/n, 1) · scale((1+p)/n, (1+p)/n, 1)`; each tile gets a fresh surface,
`subframes` draws, then its float buffer is read. **Assembly**: tile `i` lands at `(i // n, (n−1) − i % n)` in tile
units (FragM's `dx`, `dy`); with `p > 0` the tile's central `1/(1+p)` is cropped before placement so seams are exact
(FragM pastes whole tiles, which is wrong for `p > 0`; documented as a fix). A plan guard refuses a total side over
32768 unless the output is EXR (FragM's rule; EXR tiles stream to disk).

### 6.7 The final renderer (`gl/final.py`)

`FragFinalRenderer(source, state, settings, control).run(progress)`:

1. For each frame in the range (one frame for a still): compute `time = frame / fps`; if keyframes exist, set
   Eye / Target / Up from the splines (and `FocalPlane` when AutoFocus); if easing curves exist, set their values.
2. For each tile: render `subframes` subframes (checking `control` between subframes for pause / cancel), read the
   float accumulation (and the depth when *depth to alpha*), crop padding, place.
3. Display pass on the assembled float image (the buffershader run once over the full image — or per tile, as
   FragM does, when the buffershader reads neighbours; a setting, default per tile = FragM) → float RGBA; for EXR
   the **un-tone-mapped** accumulation is written (FragM's EXR path reads the float front buffer: linear, with
   `alpha = depth` when requested; we match, and offer *tone-mapped* as an option).
4. Write through `render/output.py` (8 / 16-bit, every format, parameters embedded as `frAg` text / comment) or
   `render/exr.py` (half / float); a `.fafrag` sidecar with the settings as a `Default` preset (FragM's autosave)
   and, when asked, the includes and textures copied beside it (`saveFragments` with `releaseFiles`).
5. Progress: `FragProgress(frame, frames, tile, tiles, subframe, subframes, eta_seconds, preview: rgba8 | None)` at
   most four times a second plus every finished tile (the preview fills tile by tile like the host's tile renderer).

### 6.8 GPU watchdog mitigation (`gl/job.py`, phase 6)

A subframe that takes longer than `FRAG_SUBFRAME_BUDGET_MS` (default 500) triggers **automatic tiling of the
viewport**: the job renders the frame as 2×2 / 3×3 sub-tiles of the same surface with `glViewport` + scissor, each
under the budget, so a single draw never approaches the driver's 2-second reset. The status bar shows `tiled 2×2`.
Users can pin the factor in preferences. The hi-res renderer is tiled by construction.

### 6.9 Display path options

Phase 1: read back RGBA8 (`fbo.read`) → `rgba_to_qimage` → `QPainter`. At 1920×1080 that is 8 MB per delivered
image, 3–5 ms on a discrete GPU, fine at the refresh rates involved (FragM itself reads tiles back). Phase 6
option: `QOpenGLWidget` sharing the service's context and blitting the surface texture directly — same
`FragViewport` API, chosen at construction when the platform supports context sharing with a standalone context
(moderngl `create_context(share=True)`); the read-back path stays the default until it proves itself.

---

## 7. Parameters: widgets, locks, presets, settings text

### 7.1 Widgets (`parameter_widgets.py`) — FragM's `FloatWidget.h` family

* **ComboSlider**: a `QSlider` with 1e8 steps over the range (FragM's `scale`), an `ExpSpinBox` (a QDoubleSpinBox
  that accepts and, on request, shows scientific notation; 9 decimals, 18 for doubles; keyboard tracking off),
  logarithmic mapping (`log|v|`, sign-aware like FragM), context menu *Select source* / *Edit scale* /
  *Scientific* / *Standard* / *Upper bound* / *Lower bound* — the bound actions rewrite the annotation in the
  source through the document (`comboSliderBoundsChanged` ported as a text edit on the right regex group).
* **FloatWidget** one slider; **Float2 / 3 / 4** stacked sliders; Float3 / Float4 **normalise** when `from == to`
  (FragM's `n1Changed`…: the edited component is kept, the others rescaled; a zero remainder snaps to ±1).
* **IntWidget** integer slider + spin; **IntMenuWidget** combo of the `menu[...]` texts; **BoolWidget** check box;
  **ColorWidget** swatch opening the host's non-modal `ColorDialog` with live updates (FragM 2.5: realtime
  feedback); **FloatColorWidget** slider + swatch for `vec4 color[min,def,max,r,g,b]`; **SamplerWidget** editable
  combo of image files found beside the fragment and on the include paths, four channel combos shown for EXR (red
  background when a channel is missing), a browse button (image filter; *mimetypes* preference), the texture is
  `AlwaysLocked`.
* Every widget has FragM's **lock button** (padlock) and label; locked widgets get the "provided" label style;
  `NotLockable` hides the button, `AlwaysLocked` disables it.
* Widgets are pure UI: they emit `changed(name, value, locked_changed)`; the panel routes to the document.

### 7.2 The panel (`parameter_panel.py`) — `VariableEditor`

Group tabs (created in parameter order; `Default` for empty group; removed when empty after a rebuild), a preset
combo with *Apply* (and auto-apply on selection, FragM's `presetSelected`), widget reuse across rebuilds by
`unique_name` (values survive an edit-and-build cycle), **hide unused** (active-uniform report; locked ones stay
visible; FragM's `hideUnusedVariableWidgets`), the group context actions (*Reset group*, *Lock group*, *Unlock
group*, *Copy group*, *Group → preset*), `F1` reset all, `F2` / `F3` copy / paste settings, Shift+`F3` paste from the
editor's selection, the Camera tab that always exists (`updateCamera`), the East / North tab flip on dock resize.

### 7.3 Settings text (`parameters.py`, `state.py`)

`to_settings_text(provenance=True)` writes FragM's two comment lines (`// Generated by: file`, `// Created on:
date`) then `name = value[,value…][ Logarithmic][ Locked]` per parameter (only non-default lock / slider types are
written), then the easing curve lines when *save easing in presets* is on. `from_settings_text()` accepts the same,
skips `#` and `//` lines, detects 12-field easing lines (`a:b:…`), splits on the first `=`, clamps to the range
with a warning (*value from preset clamped*), warns for unknown names, returns whether a recompile is needed
(a lock changed). Camera settings extraction filters `FOV`, `Eye =`, `Target`, `Up` (3D) or `Center`, `Zoom` (2D) —
`getCameraSettings()`.

### 7.4 Locks

`Locked` / `AlwaysLocked` parameters are substituted in the preprocessed source: `uniform float X;` →
`#define X 1.5` (preference *use defines*, default) or `const float X = 1.5;`; for vectors `#define X vec3(…)`.
Toggling a lock marks the document `needs_build`; *Build* recompiles; the panel shows the lock state from the
settings text (`Locked` suffix) when a preset is applied. Locked widgets are still editable (a change marks
`needs_build` again — FragM's `variablesChanged(lockedChanged)`).

### 7.5 Undo (extension)

`FragDocument` keeps an undo history of `ParameterState` snapshots with merge keys (a slider drag = one step; a
camera drag = one step; a preset apply = one step; a lock toggle = one step). The text editor's own undo stack is
separate (as in the Script / Formula editors). Ctrl+Z in the window applies to whichever had focus last: the editor
widget when it has focus, the parameter history otherwise.

---

## 8. Cameras (`fragments/camera.py`, `ui/fragments/viewport.py`)

`Camera3D` and `Camera2D` are pure functions over the camera parameters (read from / written to the
`ParameterState` by name: `Eye`, `Target`, `Up`, `FOV`; `Center`, `Zoom` or `log_Zoom`, `EnableTransform`,
`RotateAngle`, `StretchAngle`, `StretchAmount`), ported from `CameraControl.cpp` with the same constants:

* 3D: `stepSize` 0.1 default, clamped `[1e-5, 10]`; keys move by `step` along `dir` / `right` / `up`; rotations by
  `fovDown · 5` degrees (`T G Y H`) and 2° (`Q E`); mouse: `sensitivity = fovDown + 0.5`, `mouseSpeed = step ·
  sensitivity`, rotation angles `−dp · mouseSpeed · 100` degrees about `upDown` and `rightDown`; right-drag
  translates `dp · 10 · mouseSpeed`; both buttons dolly `directionDown · dp.x · mouseSpeed`; wheel dolly `dir · step ·
  notches / fov`; Shift + wheel halves / doubles the step; `orthogonalize_up()` after every key move and on press;
  `screen_to_3d(sx, sy, depth)` → the point on the surface (`eye + dir / sz`) using the depth read from the surface
  (`ZAtMXY`: read after the first and second subframes following a press — FragM reads at `subframeCounter <= 2`).
* 2D: `factor = 1.05^step` for `Q E`, pan by `0.1 / zoom` through the rotate / stretch matrix; left-drag pans
  `dp / zoomDown`; right-drag zooms about the press point (`getModelCoord`); wheel ×1.15 in *fixed* (about the
  cursor) or *traveling* (centre → cursor) mode (preference `ddCameraMode`).
* The viewport maps events to these functions and writes the result into the document as `camera_edited(text,
  interactive)`; interactive edits merge into one undo step; the status bar shows the point / step messages FragM
  shows (`Camera: Use W/S to fly…`, `Step size: …`).
* `AutoFocus`: when the fragment has the check box and it is on, every camera write also sets `FocalPlane =
  |Target − Eye|` (`setCameraSettings`).
* Middle-click: `Target` (or `LightPos` with Ctrl) = the picked point.

---

## 9. Animation (`animation_controls.py`, `spline.py`, `easing.py`, `timeline_window.py`)

### 9.1 Time and modes

`AnimationControls` owns the clock (`lastStoredTime`, frame ticks at `fps`): Progressive mode keeps `time` at the
stored frame; Animation mode advances while playing (`lastStored + elapsed · fps`), stops at the end (or loops
with *Loop play*), `F10` rewinds (easing curves to frame 0), `F11` / `F12` / Space; the label shows `Time: 3s:12f`;
the slider's maximum is `length · fps`, page step `fps`; switching to Progressive remembers the last view. Every
frame change in Animation mode clears the accumulation (FragM: `requireRedraw(true)` on `timeChanged`) and the
driver submits with the new `time` and camera.

### 9.2 Keyframes and camera paths (`spline.py`)

`KeyFrame.nnnn` presets hold FOV / Eye / Target / Up (the `F8` text). With ≥ 2 keyframes: three Catmull-Rom splines
(`QtSpline::spline` basis `½·[−1 2 −1 0; 3 −5 0 2; −3 4 1 0; 1 −1 0 0]`, the end-point "fudge" so the path lands on
the control points, loop mode wrapping the indices) sampled at `length · fps` frames; Animation playback and the
final renderer set the camera from frame `t` (`eyeSpline[index]`, `targetSpline`, `upSpline` normalised); ticks on
the slider at `max / (k−1)`; `F9` selects the current keyframe's text in the editor; *Animation ▸ Clear animation
objects*; *Loop camera path*. The viewport draws the Eye path (red), Target path (blue) and control points (green)
projected with the current camera (`glm::perspective(2·atan(fov), aspect, 1e-5, 1000) · lookAt`) over the image
with QPainter; *Spline occlusion* hides segments behind the surface using the depth texture read at their projected
pixels (cheap enough for a few hundred points; a preference as in FragM; the GL line renderer is not ported).

### 9.3 Easing curves (`easing.py`, `easing_dialog.py`)

The 12-field setting `slider:typeName:typeNum:start:end:firstFrame:lastFrame:period:amplitude:overshoot:loops:pingpong`
attaches to one **slider component** (`Power1`, `JuliaC2`). Evaluation per frame follows `updateEasingCurves`:
before `firstFrame` the start value; inside, `QEasingCurve(typeNum)` with period / amplitude / overshoot applied to
`(frame − first) % loopDuration` (reversed on odd loops when ping-pong); after the end the final value (or the start
for even ping-pong loop counts). An end frame past the animation length stops playback with FragM's message
(*Easingcurve end frame N is greater than maximum M… select group → name and press F7, or set the animation
length…*). The `F7` dialog is the `EasingWindow` port (curve list with preview icons, line / circle preview, period /
amplitude / overshoot, start / finish values with a range slider, frame in / out with a range slider, loops, ping-pong;
*Apply* / *Discard* / *Cancel* when a curve exists). `Range-…` presets hold curve lines only; *save easing in
presets* writes them into ordinary presets; a `Default` preset with curves activates them on load.

### 9.4 Timeline editor (`timeline_window.py`)

The host's `Timeline` widget (ruler, keyframe markers, playhead, zoom) shows the keyframes (draggable → renumbers /
re-spaces the `KeyFrame.nnnn` presets' positions — FragM spaces keyframes evenly over the length; dragging is an
extension that stores an optional frame in the preset as a comment `// frame = 120`), and below it one lane per
easing curve (name, frame range bar, the curve drawn with `QEasingCurve`), double-click → `F7` dialog, right-click →
remove. Opened from the time toolbar's context menu or *Animation ▸ Timeline editor*.

### 9.5 Render integration

The final renderer (§6.7) evaluates splines and curves per frame; *Animation* in the render window uses the
controls' length / fps and a frame range; *preview* renders one frame into a dialog with *Save* (FragM's preview
window).

### 9.6 Extension — interpolated presets

An *Interpolation* option on the Animation menu: *Camera path only* (FragM, default) or *All parameters*: numeric
parameters are interpolated between consecutive `KeyFrame.nnnn` presets (linear or smooth, like the host's
Animation window; booleans / ints / menus hold). Stored in the `.fafrag` metadata block; ignored by FragM.

---

## 10. Files, formats, library, templates

### 10.1 `.fafrag` and `.frag`

Both are GLSL text parsed by the same preprocessor. A `.fafrag` may end with one metadata block that FragM's
preprocessor sees as a comment:

```glsl
/*[fractalchemy]
{
  "version": 1,
  "render": {"tile_size": [1920, 1080], "tiles": 2, "padding": 0.0, "subframes": 200, "format": "png16", "depth_to_alpha": false},
  "animation": {"fps": 25, "length": 10, "interpolation": "camera", "loop_path": false},
  "library": {"tags": ["mandelbulb", "3d"], "author": "…", "thumbnail": "<base64 PNG 160×100>"},
  "tabs": {"preset": "Default"}
}
[/fractalchemy]*/
```

Rules: JSON must not contain `*/` (escaped if it does); the block is stripped before preprocessing and re-emitted
on save; `File ▸ Save as ▸ Fragmentarium .frag` omits it; loading a `.frag` has no metadata → defaults. Presets,
keyframes and ranges stay FragM `#preset` blocks — the *only* place parameters live, so FragM interoperability is
total. The library shows the embedded thumbnail when present and renders one otherwise.

### 10.2 Other files

* `.fragparams` — the settings text (*Parameters ▸ Save to file / Load from file*).
* Images — parameters embedded under the `frAg` key (PNG `tEXt`, FragM's key, so FragM loads our PNGs and vice
  versa; other formats through `render/output.py`'s comment fields); *Load parameters* accepts an image.
* The render's autosave folder `<name> Files/` with `<name>.frag` (includes flattened, presets stripped, a `Default`
  preset of the settings appended — `createAutosaveFragment`), optionally the included files and textures copied
  and re-referenced (*release files*).
* Recent files (max N preference, full-path option), a `QFileSystemWatcher` on open files with *autoload on
  external change* (else a prompt), drag-and-drop of `.frag` / `.fafrag` / `.fragparams` / images-with-parameters
  onto the window.

### 10.3 The library pane (`library_panel.py`)

`FRAGMENT_CATALOG` (one entry per file; `.frag`, `.fafrag`; a file with `#donotrun` is listed as an *include* with a
dimmed icon and opens read-only unless copied) plugs into the host's `library/` machinery: folders (the bundled
**Examples** root is always present, read-only, on top; user roots below), search, thumbnails (`ThumbnailProvider`
variant rendering through the fragment service at `PRIORITY_THUMBNAIL` — 160×100, 4 subframes, the `Default`
preset, cached under `<cache>/fragments/thumbs/<hash>.png`; the embedded thumbnail first), rename / duplicate /
delete / new folder / reveal, drag between folders, the *Library* menu mirroring the tree (FragM's Examples menu).

### 10.4 Bundled library (`fractalchemy/fragments/library/`)

`Include/` — the 67 FragM include files (canonical versions from `Fragmentarium_Examples_Folder/Include`, the most
recent); `Examples/` — the 188 runnable examples in their categories (2D Systems, Benesi, CozyG, DarkBeam,
Experimental, Historical 3D Fractals, Kaleidoscopic IFS, Kali's Creations, Knighty Collection (+ sub-folders), Theory,
Tryptophan, Tutorials, eiffieGI2) plus a **Community** category with the `fragm-formulas` samples (gannjondal's
Newton fragments); textures referenced by examples (`texture.jpg`, `cubemap.png`, the Ditch-River HDRs); the
`.gitmodules` of the examples repo is **not** fetched (empty submodules are listed in `ATTRIBUTION.md` as "more at
…"). Per-file licences stay in the file headers; `ATTRIBUTION.md` summarises FragM's GPL-3 for the includes and the
example authors. The include path preference defaults to this `Include/` folder and accepts more.

### 10.5 Templates (`templates.py`)

*File ▸ New ▸* / *Edit ▸ Templates*: FragM's **New 2D** (Mandelbrot with IQ colouring) and **New 3D** (a sphere-shell
DE) verbatim, then: *Escape-time 2D with orbit trap*, *Progressive 2D Julia*, *DE raytracer 3D (Menger)*,
*Mandelbox*, *Kaleidoscopic IFS*, *Path tracer (Path-Raytracer.frag)*, *IBL raytracer with an HDR sky*, *Fast
raytracer*, *Buffer feedback (Game of Life)*, *Shadertoy port (Shadertoy.frag)*, *2D with a gradient (inserts the
gradient bridge's function)*. Each is a complete fragment with a `Default` preset. *My templates*: save the current
tab as a template (per-user `fragments/templates/` folder, plain `.fafrag`), rename / delete.

### 10.6 Insert command menu (`templates.py` snippets)

FragM's `createCommandHelpMenu` one for one: *Host preprocessor commands* (`#info`, `#include`, `#camera 2D/3D`,
`#group`, `#preset` / `#endpreset`, `#define DontClearOnChange / IterationsBetweenRedraws / SubframeMax / providesColor /
providesBackground / providesNormal`), *2D texture options* (the `#TexParameter` lines), *Special uniforms* (time,
subframe, int / float sliders, pixelSize, vec2 / 3 / 4 sliders, double variants when GL ≥ 4, bool, sampler2D /
samplerCube file, vec3 / vec4 colours, DepthToAlpha, AutoFocus), *Include* (every `.frag` on the include path),
*Insert preset from current settings*.

---

## 11. The Render Fragment window and batch rendering

### 11.1 Window (`render_window.py`, `render_panels.py`) — `JobWindowBase`

Panels (left, disabled while a job runs): **Tile size** (width / height spin boxes ≤ 4096 · aspect lock · *from
screen* (the viewport's buffer size) · **Tiles** slider 1–32 with the total `n²` · **Padding** 0–1), the resulting
**image size** line; **Quality** (subframes 1–65535; *tiles per frame* advanced); **Animation** (check box; start /
end frame with a range slider; fps; length → total frames; *preview frame only*); **Output** (the host's
`OutputPanel`: path, format, depth, quality, transparency, *embed parameters*, *save parameters beside*, plus:
*unique file name* (a time stamp), *save fragment and settings* (+ includes, + release textures), *depth to alpha*
for EXR, *tone-mapped EXR*); the **plan** line and the **estimate** (from the viewport's measured seconds per
subframe × tiles × subframes × frames). Right: `RenderProgressPanel` (tile-by-tile preview, progress, elapsed /
remaining, speed as subframes/s, the result link). Start / Pause / Stop / Close as the other job windows.

### 11.2 Job (`FragRenderJob(QThread)`)

Snapshot at *Start*: the document's preprocessed source (after locks), the parameter state, presets (keyframes,
ranges), the animation settings, textures (paths →decoded on the thread), render settings. Creates its own
`FragEngine` (own context) on the thread; runs `FragFinalRenderer` (§6.7); `RenderControl` for pause / cancel;
`FragOutcome(path(s), frames rendered, notes, report)`; *save incomplete* keeps what was finished. A details report
(`name.md`, the host's `report/` writers adapted: fragment name, includes, parameters, GL strings, per-tile timings)
is optional as in the Render Image window.

### 11.3 Animation output and video

Frames `name_00001.png` (FragM's 5-digit padding, growing for > 99999 frames) in `<folder>/<name> Files/Images/`
when *save fragment* is on (FragM's layout) or beside the name otherwise; the host's ffmpeg panel (`animation/render.py`:
formats, CRF, keep frames, the command line shown) makes the video afterwards — replaces FragM's VideoDialog
(mencoder is not supported).

### 11.4 Preview

*Preview frame only* renders the frame at the chosen size into a dialog with a scroll area and *Save…* (FragM's
PREVIEW dialog); parameters are embedded when saved.

### 11.5 Batch dialog (`batch_dialog.py`)

*Render ▸ Batch render…*: choose *every preset* / *every keyframe* / *a frame range*, the output folder and
settings (the render window's panels reused), runs `batch.py` on a `FragRenderJob`-like thread with a per-item
progress list (FragM's `renderPresets.fqs` / `renderKeyframes.fqs`).

### 11.6 CLI (`tools/render_frag.py`)

```
python tools/render_frag.py FILE.frag [--preset NAME | --all-presets | --keyframes] [--size WxH] [--tiles N]
       [--padding P] [--subframes S] [--frames A-B --fps F --length L] [--format png|png16|exr|…] [--depth-alpha]
       [--out DIR/NAME] [--include-path DIR …] [--check]   # --check: preprocess + compile only, exit code = failures
```
Headless (EGL / llvmpipe when no display); used by the corpus test and for farm renders. Replaces FragM's `.fqs`
scripts (`testFrags.fqs` ≙ `--check` over a folder; `TileSizeBenchmark.fqs` ≙ `--benchmark` printing seconds per tile
for a set of tile sizes).

---

## 12. Extras

### 12.1 Textures (phase 5; `textures.py`, `gl/textures.py`)

Decoding on the thread pool: Pillow formats (8 / 16-bit, sRGB as-is — FragM uploads Qt images unconverted),
`.hdr` (RGBE → float32 via `solid/hdri.read_hdr`), `.exr` (scanline half / float, uncompressed / ZIP / ZIPS via
`solid/hdri.read_exr`, channel selection `R;G;B;A` or any named channels for `file[name, chans]`, missing channel →
warning + zeros), cube maps from a horizontal strip of six faces (`+x −x +y −y +z −z`, FragM 2.5) or six files
`name_px.jpg` … (extension), integer textures for `isampler2D` / `usampler2D`. Upload on the render thread;
`#TexParameter` applied after upload (mipmaps generated when a `*_MIPMAP_*` filter is asked for — FragM's order);
defaults `GL_LINEAR` / `GL_REPEAT`; anisotropy when the extension exists. Cache keyed by `(path, channels, mtime)`
with unused eviction after each build (`clearTextureCache`); *Build ▸ Clear texture cache*. Texture units: 0 is the
backbuffer / frontbuffer, user samplers from 1.

### 12.2 Gradient bridge (phase 5; `gradient_glsl.py`, `gradient_dialog.py`)

*Edit ▸ Insert gradient…*: pick the Gradient Library's current gradient, any gradient file the host reads
(`.ugr`, `.map`, `.flame` palettes, images) or a GIMP `.ggr` (segments with GIMP's blend types linear / curved /
sine / sphere-inc / sphere-dec and colour types RGB / HSV cw / HSV ccw — ggr2glsl's logic on the host's `Gradient`
model) → GLSL: `vec3 gradient(float t)` as a `const vec3 table[N]` with linear `mix` (N = 256 or the stop count for
a piecewise version), or a `uniform sampler2D gradientTex; file[…]` + a generated PNG strip. Inserted at the
cursor or copied. A 2D template uses it.

### 12.3 Mesh export (phase 5; `gl/mesh.py`, `mesh_export_dialog.py`)

For fragments with `float DE(vec3 p)`: a **probe program** = the fragment's preprocessed source (the raytracer's
`main` renamed away) + a generated `main` that, for a slice `z = z_k`, writes `DE(vec3(x, y, z_k))` (after `init()`
when `providesInit`) into an R32F target of `res × res`; `res` slices → a `VoxelGrid` (bounds from the dialog:
default the unit cube scaled by a *size* field, or *fit*: a coarse 32³ pass finds where `DE < iso`); the host's
`surface_nets` at `iso` (default 0, or a small positive value to thicken), then `solid.mesh` clean levels + the
print report, then `solid.pipeline.export_result` → OBJ / STL / PLY / glTF / USD / Blender script with vertex colours
from `baseColor()` when `providesColor` (a second probe pass). *Send to 3D Editor* registers the clean mesh as an
asset (`ThreeDWindow.instances_panel` import path). Runs on `MeshFromDEJob` (own context) with progress / cancel;
memory guard on `res³`.

### 12.4 Preferences (phase 5; `preferences_dialog.py`)

Groups and keys (QSettings under `fragments/`): **GUI** — max recent files, full paths in recent, loop play,
spline paths / occlusion, 2D camera mode, log max lines; **Editor** — theme (Default / Solarized dark / light /
Retta colour sets for the highlighter), font, line numbers, jump to line on error, autoload on external change;
**GLSL** — autorun on load, auto-build, move `main` to the end, locked uniforms use `#define` / `const`, compatibility
layer mode (§5.1), include files with autosave, presets contain easing settings, animation fps, refresh rate (ms),
subframe budget (§6.8), tile size from screen; **Paths** — include paths (the bundled `Include` pinned), texture
dialog uses mimetypes, GIMP gradient paths; **Application** — log to file / path / size, GL debug (moderngl
`ctx.error` checks after each call group, off by default).

### 12.5 Help (`help.py`)

*Help ▸ Mouse and keyboard* (§1.7 as a dialog), *Welcome note* (FragM's, updated), *Fragment language reference*
(renders `docs/fragments.md`), *Scripting / batch rendering* (the CLI), links to FragM's wiki, FractalForums and the
GLSL specification.

### 12.6 Log (`log_panel.py`)

Levels Info / Warning / Critical / Script with colours; `file:line` references clickable (opens the file in a tab —
bundled includes read-only — and centres the line; FragM's `loadErrorSourceFile`); a context menu *Copy* / *Clear* /
*Open file*; optional mirror to `fragm.log`-style file with a size cap; *verbose* logs uniform values on the first
subframe (FragM's `--verbose`).

---

## 13. Integration into Fractalchemy

* `ui/main_window.ui`: `actionFragments` (text *Fragments*, tooltip *Fragments: write and render GLSL fragment
  shaders — Fragmentarium fractals — with sliders, presets, cameras, animation and hi-res output (F12)*, shortcut
  `F12`) in `menuWindows` after `actionThreeDEditor` and on the toolbar before `actionRenderImage`.
* `ui/main_window.py`: `fragments_window` property (created on first use like the 3D Editor; `FragmentsWindow(self,
  self._settings, gradient_library=self.gradient_library, three_d=lambda: self.three_d_editor)`), `show_fragments(path=None)`,
  `status` → status bar, `closeEvent`: `confirm_quit()` (unsaved tabs, running render), `save_state()`, stop its
  service. `main.py`: `--fragment FILE` opens the window on a file at start-up.
* `widgets/icons.py`: `fragments_icon()` — a code-sheet glyph with a shard (triangle) in the highlight colour,
  rendered at the usual sizes.
* `config.py`: `FRAG_DEFAULT_SUBFRAMES = 10`, `FRAG_REFRESH_MS = 40`, `FRAG_SUBFRAME_BUDGET_MS = 500`,
  `FRAG_THUMBNAIL = (160, 100, 4)`, `FRAG_INTERACTIVE_SCALE = INTERACTIVE_SCALE`, `FRAG_MAX_TILE_SIDE = 4096`,
  `FRAG_MAX_IMAGE_SIDE = 32768`.
* `requirements.txt`: nothing new (moderngl, numpy, Pillow, scipy already required).
* `README.md`: a *Fragments window* section in the style of the others + the layout block; `docs/fragments.md`:
  user guide + language reference; this plan stays in `plans/`.
* Gradient Library link: the gradient dialog reads `gradient_library.document.gradient`.
* 3D Editor link: mesh hand-off through the existing asset import (a PLY written to a temp path then
  `instances_panel.import_mesh(path)` — an existing public method).

---

## 14. Testing

All headless (`QT_QPA_PLATFORM=offscreen`; GL through the `gl_context` fixture on llvmpipe; tests needing GL are
skipped with the reason when no context can be created).

### 14.1 Unit (Qt-free)

* `test_fragments_preprocessor.py`: every directive; include order and "twice is twice"; column-0 include rule;
  missing include → critical + continue; cycle cap; presets lifted with names and bodies; `#replace` later-lines
  rule; `#vertex` split; `moveMain`; magic uniforms; tooltips from the comment above; `create_autosave_fragment`.
* `test_fragments_parameters.py`: every annotation form × type (floats, doubles, vec2/3/4, dvec, colours, float
  colour, int, menu, bool, samplers with channels), lock / slider suffixes, `unique_name`, settings text round
  trip (FDEC / DDEC formatting, `.0`), clamping warnings, unknown names, camera settings extraction, locked
  substitution (`#define` and `const`), normalised-direction rule incl. the `Up` exception.
* `test_fragments_compat.py`: target version rules; preludes; wrapper functions only for used samplers; the
  user-defined `texture` function case; de-duplication; `gl_FragData`; LineMap correctness (random line → original
  file / line); diagnostics parsing for the three driver formats.
* `test_fragments_camera.py`: 3D key moves against hand-computed vectors; orient / orbit-origin / orbit-target /
  pan / dolly drags reproduce FragM's formulas (fixtures computed from the C++ with glm semantics); step clamps;
  `screen_to_3d`; 2D pan / zoom-about-point / wheel fixed vs traveling; the rotate / stretch matrix.
* `test_fragments_animation.py`: spline passes through control points at keyframe frames (the fudge), loop mode
  wraps, keyframe parsing; easing evaluation before / inside / after the range, loops, ping-pong parity with a
  direct `QEasingCurve` computation; the end-frame-over-length message; `Range-` presets; settings lines.
* `test_fragments_format.py`: `.fafrag` metadata block round trip, stripping for `.frag`, FragM's preprocessor
  regexes ignore it (asserted by running our FragM-literal preprocessor on it: no params / presets change);
  `.fragparams`; PNG `frAg` embed / read; tiles maths (placement, padding crop, 32768 guard, plan text).
* `test_fragments_gradient.py`: ggr parsing and the GLSL output evaluates (numpy port of the emitted function)
  to the gradient's colours within 1/255.

### 14.2 Corpus (GL)

`test_fragments_corpus.py`: preprocess **every** bundled example; compare the parameter inventory (group, name,
type, range, default, lock, slider type) to a committed JSON snapshot (generated once by the FragM-literal
preprocessor, reviewed by hand for a dozen files against FragM's own log output); compile every runnable example
through the compatibility layer on llvmpipe — expected-pass list committed; render **one subframe at 64×40** for a
stratified sample (every category, every include family: Progressive2D, DE-Raytracer, Fast, Soft, Path, IBL,
Brute, Subblue, 3DKn, BufferShader variants) and assert finite pixels and a non-constant image where the `Default`
preset shows something. Marked `slow`; the CLI's `--check` runs the same.

### 14.3 Engine (GL)

`test_fragments_engine.py`: surface ping-pong accumulates (subframe n ⇒ alpha ≈ n for `Progressive2D`); clear vs
`DontClearOnChange`; buffershader-only redisplay leaves the accumulation untouched; tiles == untiled (a 2×2 tiled
render assembled equals a single render within 1e-6 for a deterministic fragment; with padding the crop removes
the overlap); depth read at a pixel on the Mandelbulb hits the `gl_FragDepth` formula; double uniform upload when
GL ≥ 4.0 (skip otherwise); unused-uniform detection; texture upload (2D, cube strip, EXR channels) and
`#TexParameter`; the DE probe → `VoxelGrid` → surface nets on the sphere-shell template gives a watertight mesh
whose radius matches; the final renderer writes PNG16 and EXR (read back through `read_exr`) with depth alpha.

### 14.4 UI

`test_fragments_window.py`: the window opens from the main window's action; `New 3D` builds and delivers a pass;
parameter edit → re-render with `clear`; preset apply → values; undo / redo; lock → `needs_build` → build; the panel
hides an unused uniform; tabs remember values; save / open `.fafrag` round trip with metadata; library pane lists the
Examples root and opens a file; camera drag → document camera changed and an interactive render; compile error →
log entry with mapped file:line and the editor's error mark; the render window renders a 2×2-tile 64×64 image to a
temp PNG with embedded `frAg`; batch dialog renders two presets; closing with unsaved tabs asks; `confirm_quit`
with a running render asks. `test_fragments_animation_ui.py`: F8 inserts a KeyFrame preset at the end; two keyframes
→ ticks + spline; F7 dialog writes a curve line into the document; play advances `time`; timeline drag.

### 14.5 Performance checks (manual, documented numbers)

Mandelbulb 1280×720: build < 1 s, first subframe < 50 ms on a mid-range discrete GPU; camera drag ≥ 30 fps at half
resolution; GUI stays responsive during a 4×4 × 1920×1080 × 200-subframe render (the job thread owns its
context). Read-back overhead measured and documented (§6.9).

---

## 15. Delivery in phases

Each phase is shippable; the existing windows are untouched except the hooks in §13.

| Phase | Delivers | Acceptance |
|---|---|---|
| **1. Core loop** | `fragments/` source, preprocessor, parameters, state, files, glsl_compat, camera; `gl/` engine, program, uniforms, surfaces, job, diagnostics; `RenderService` factory hook; `ui/fragments/` window (menus, toolbars), document, tabs, viewport, render_driver, parameter_panel + widgets, code_editor, log_panel, buffer_size; presets (apply / insert / select); cameras with the full key / mouse set; Build / auto-build; preprocessed-source viewer; main-window action + icon; bundled `Include/` + `Examples/` as package data (read-only tree on the *Library* menu, no pane yet) | every FragM-compiling example compiles and renders; `test_fragments_{preprocessor,parameters,compat,camera,corpus,engine}`; the window test's core cases |
| **2. Files & library** | `.fafrag` / `.frag` / `.fragparams` / image-embedded parameters; open / save / save as / reload / recent / watcher / drag-and-drop; the library pane with thumbnails and search; templates (§10.5) and the insert-command menu; screenshots; fullscreen; `--fragment` CLI flag; session restore of tabs | `test_fragments_format`, library + files cases in the window test |
| **3. Animation** | time toolbar and modes, `time` uniform, keyframes → splines, path overlay with occlusion, F7 easing dialog, Range presets, timeline editor, loop options, interpolation mode (§9.6) | `test_fragments_animation`, `test_fragments_animation_ui` |
| **4. Render window** | `gl/tiles`, `gl/final`, `FragRenderJob`, the Render Fragment window (panels, plan, ETA, preview, outcome), EXR with depth, autosave fragment (+ includes, release files), animation frames + ffmpeg, preview dialog, batch dialog, `tools/render_frag.py` | tiles == untiled test, EXR round trip, the render window test, CLI `--check` over the corpus in CI |
| **5. Extras** | textures (all kinds, `#TexParameter`, cache, sampler widget), gradient bridge, mesh export + 3D Editor hand-off, preferences dialog, help, log-to-file, *Test GLSL versions* | texture / mesh engine tests, gradient test, preferences persist |
| **6. Polish & performance** | watchdog auto-tiling, adaptive subframes-per-pass, optional shared-context blit, GLSL completer polish, editor themes, README + `docs/fragments.md`, a review pass against the repo's rubric (architecture / DRY / comments / tests) | the documented performance numbers; full suite green; pyflakes clean |

Rough size: ~9–11 k lines of Python across ~45 modules (the FragM C++ is ~15 k lines plus Qt UI files; the host
already provides the editor, library, job window, writers and mesh pipeline).

### 15.1 Execution, step by step

Conventions for every step: write the module docstring first (what and why, as the repository does), keep
functions under ~40 lines, add the test in the same step, run `python -m pytest tests/test_fragments_*.py -q` and
`python -m pyflakes fractalchemy tests tools` before moving on. Steps marked **(GL)** need the llvmpipe context.

#### Phase 1 — the core loop

1. **Package data and corpus fixtures.**
   1. Create `fractalchemy/fragments/library/Include/` (copy the 67 files from
      `samples/fragmentarium/Fragmentarium_Examples_Folder/Include`, plus the textures and HDRs it references) and
      `Examples/<category>/` (the 188 runnable examples; `Community/gannjondal/` from `fragm-formulas`). Write
      `ATTRIBUTION.md`. Add the folder to the package data (check `setup`-less layout: the code locates it with
      `Path(__file__).parent / "library"`).
   2. `fragments/examples.py`: `include_dir()`, `examples_dir()`, `example_tree() -> list[(category, [paths])]`,
      `is_include(path)` (first non-blank line `#donotrun`).
   3. Test: the tree lists every category; every example path exists; `Include/` has `DE-Raytracer.frag`.
2. **FileManager** (`fragments/files.py`).
   1. `FileManager(include_paths, original=None)`; `resolve_name(name, origin) -> Path` raising `IncludeNotFound`
      carrying `tried: list[Path]`; `file_exists`; `get_files(filters)` with the cache; `image_files()`;
      `set_include_paths` (the bundled `Include/` always appended last).
   2. Tests: order of resolution (beside the fragment beats include paths), absolute paths, the tried list.
3. **Parameter model** (`fragments/parameters.py`, `fragments/state.py`).
   1. Enums `LockType`, `SliderType` with `from_text` / `to_text` (FragM's strings, case-insensitive parse, empty
      for Linear / NotLocked).
   2. `GuiParameter` dataclass family with `unique_name`, `glsl_type`, `components`, `default`, `clamp(value) ->
      (value, clamped: bool)`, `format(value, is_double)`, `parse(text) -> value`.
   3. `settings_line(name, value, lock, slider, default_lock, default_slider)` and `parse_settings(text) ->
      ParsedSettings(values, locks, sliders, easing_lines, warnings)`.
   4. `locked_substitution(param, value, use_defines) -> str`.
   5. `ParameterState`: values / locks / sliders keyed by name, `from_params(params)`, `apply(parsed) ->
      ApplyResult(changed, recompile, warnings)`, `to_text(provenance)`, `camera_text(kind)`, `copy()`, `diff(other)`.
   6. Tests (§14.1 list).
4. **Preprocessor** (`fragments/source.py`, `fragments/preprocessor.py`).
   1. `LineMap`, `FragmentSource`, `Message(level, text, file, line)`.
   2. `_parse_source` (includes, buffershader, `#group default` after includes, version capture, depth cap);
      `_parse` (presets, replace, specials, annotations in FragM's order, magic uniforms, moveMain, version check).
   3. The annotation regexes as module constants with a comment citing `Preprocessor.h`; a `NUMF` / `NUMI` pair;
      each `parse_*` a small function returning a `GuiParameter` or `None` + a warning.
   4. `create_autosave_fragment` (includes inlined, presets removed, `#version` kept first).
   5. Tests (§14.1) + the corpus inventory snapshot generator (`tools/fragments_snapshot.py`) and
      `test_fragments_corpus.py::test_parameter_inventory_matches_snapshot`.
5. **Compatibility layer** (`fragments/glsl_compat.py`, `fragments/gl/diagnostics.py`).
   1. `target_version(requested, context, needs_fp64)`; `vertex_prelude(version)`; `fragment_prelude(version,
      used_samplers, uses_fragdata)`; `dedupe_declarations(lines, map)`; `rewrite_legacy(lines)` (attribute → in,
      `#version` removal, `#extension` policy, `noise*`); `modernise(source, options) -> ModernSource` carrying
      vertex / fragment text and maps.
   2. `diagnostics.parse_log(text) -> list[(line, column, severity, message)]` for NVIDIA / AMD / Mesa; `map_to_source`.
   3. Tests (§14.1), including the `texture`-function fragment and a LineMap fuzz (every emitted line that came from a
      file maps back to a line whose text equals the original).
6. **Engine (GL)** (`fragments/gl/engine.py`, `program.py`, `uniforms.py`, `surfaces.py`, `job.py`).
   1. `Capabilities.probe(ctx)`; `FragEngine.__init__` (context via `render.gpu_engine.create_context`, triangle
      VBO / VAO, caches); `build()` with the cache and `ShaderBuildError` (reuse `gpu_engine._dump_failure` by
      extracting a shared `write_failure_report(sources: dict, log, renderer)` into `render/gpu_engine.py`).
   2. `Program`: main + buffershader programs, `active_uniforms()`, `unused(names)`.
   3. `uniforms.py`: `upload(program, values, params, caps)` type-dispatched; `special_uniforms(program, width,
      height, subframe, time, projection)`; `tile_projection(i, n, padding)` (also used by `tiles.py`).
   4. `Surface` / `SurfaceCache` with the depth texture and the reads.
   5. `FragRequest` (+ `.copy()`), `FragRenderSettings`, `FragJob.run_pass` exactly as §6.2; `BuildFacts` travel in
      a new optional `RenderStats.facts` attribute (default `None`; the flame engines never set it), so the service's
      `_snapshot` copies it and the driver reads compile time, active / unused uniforms and GL strings from the
      first pass.
   6. Tests (GL): §14.3 surface / clear / redisplay / unused cases on `templates.NEW_2D` and `NEW_3D`.
7. **Service hook** (`render/service.py`).
   1. `EngineFactory` protocol, `DefaultEngineFactory` reproducing `_create_engine` + `_fallback_engine`; the
      constructor's `factory=None`; `submit(key, payload, settings, priority)` with `payload.copy()`.
   2. Run the existing `tests/test_render.py`, `test_main_window.py`, `test_viewer_controls.py` — unchanged results.
   3. `FragEngineFactory` in `fragments/gl/engine.py` (`create()` → `FragEngine`, `fallback()` → `None`).
8. **Cameras** (`fragments/camera.py`).
   1. `Camera3DState` (eye, target, up, fov) and `Camera2DState`; the operation functions listed in §8; `StepSize`
      helper with the clamps; `screen_to_3d`; 2D `model_coord`, `transform_matrix`.
   2. Tests with fixtures derived from the C++ formulas.
9. **Documents and tabs** (`ui/fragments/document.py`, `tabs.py`).
   1. `FragDocument` with the signals of §3.4, the undo history (a small `History` class: snapshots + merge keys,
      shared shape with `FractalDocument`'s — factor a `widgets`-free `ui/history.py` if the existing code has an
      extractable piece; otherwise a 60-line local class), `build()` (preprocess + lock substitution + modernise on
      the GUI thread — cheap; compile on the render thread through the request), `request()`.
   2. `TabManager` over `QTabBar` + `QStackedWidget` of editors, one document each, unsaved marks, close prompts.
10. **Code editor** (`ui/fragments/code_editor.py`).
    1. `GlslHighlighter(QSyntaxHighlighter)`: keyword sets per version (1.10 → 4.60 from FragM's `glsl.xml`
       distilled into `fragments/glsl_keywords.py`), types, built-in functions, qualifiers, preprocessor lines,
       annotation tails (`slider[...]` in a distinct colour), `#preset` blocks dimmed, comments / strings / numbers,
       bracket matching on cursor move.
    2. `GlslCodeEditor(BaseCodeEditor)`: `comment_prefix = "//"`, brace indentation like `FormulaCodeEditor`, a
       completer over GLSL built-ins + the document's uniform / function names + snippet names; `indent_script()`
       (FragM's brace-count indenter) as an action.
11. **Viewport and driver** (`ui/fragments/viewport.py`, `render_driver.py`, `buffer_size.py`).
    1. `FragViewport`: paint (fit / 1:1), overlays (building, tiled n×n, FPS), input → camera functions → document;
       interactive flag while a button / key is down; depth pick requests; fullscreen toggle.
    2. `RenderDriver`: owns the service key per document; slots for every document signal deciding `clear` /
       `redisplay_only` / `subframes`; throttling; `stats_changed`; the subframe-max and continuous logic;
       `BuildFacts` → document `built` / `build_failed` (mapped diagnostics).
    3. `BufferSizeBar` with `getBufferSize()` semantics.
12. **Parameter panel and widgets** (`parameter_widgets.py`, `parameter_panel.py`).
    1. `ComboSlider` + `ExpSpinBox`; the widget classes; lock buttons; context menus; bounds edit → document text
       edit through `presets.py`'s regex helpers (shared with the preprocessor constants).
    2. `ParameterPanel`: tabs, preset combo, rebuild-with-reuse, hide unused, group actions, copy / paste, F-keys.
13. **Log panel** (`log_panel.py`) and **window** (`window.py`, `actions.py`).
    1. Menus / toolbars per appendix A (phase-1 subset), docks, splitter, status bar, persistence
       (`fragments/geometry`, `state`, `tabs`, `splits`), `bring_to_front`, `confirm_quit`, `save_state`.
    2. Build / auto-build timer (1 s after the last edit when the last build took < 1 s), *Show preprocessed
       source* (a read-only `GlslCodeEditor` dialog with the `file:line` gutter), the *Library ▸ Examples* tree menu.
    3. Main-window hooks (§13) and `fragments_icon()`.
14. **Phase-1 tests**: `test_fragments_window.py` core cases; the corpus compile + render sample (GL, `slow`).
15. **Review pass** against the rubric (module sizes, docstrings, DRY); update `README.md` with a first *Fragments
    window* section and write `docs/fragments.md` (language reference from §4 / §5).

#### Phase 2 — files and library

1. `fragments/document_format.py`: metadata block read / strip / write, `.fragparams`, image parameters
   (`frAg`) via `render/png_tiff.py` (extend `png_bytes(..., text_key="frAg")`) and `output.read_embedded_parameters`.
2. `ui/fragments/file_actions.py` (a `FileActionsBase` subclass): open / save / save as (`.fafrag` default, `.frag`
   option) / reload / recent / watcher (`QFileSystemWatcher`, *autoload* preference) / drag-and-drop; parameter file
   and image import; screenshot (`Render ▸ Save screenshot…`: the last viewport image with parameters embedded,
   every format).
3. `library/catalog.py`: `FRAGMENT_CATALOG` (`matches` by suffix; `entry_names` = [stem]; a single-entry
   `EntryFormat` with rename / remove / duplicate at file level).
4. `ui/fragments/library_panel.py`: `LibraryPanel` reuse (the host's panel class) + `FragThumbnailProvider`
   (render through the service, cache to disk, embedded thumbnail first) + the Examples root pinned read-only.
5. `fragments/templates.py` (templates, snippets, user templates folder) and the *Edit ▸ Insert command* /
   *Templates* menus; *File ▸ New ▸*.
6. Session restore (open tabs, current tab, per-tab preset / values), `--fragment` in `main.py`, fullscreen +
   Shift+RMB menu.
7. Tests: `test_fragments_format.py`; window cases for files / library / templates / screenshot.

#### Phase 3 — animation

1. `fragments/spline.py` (+ tests), `fragments/easing.py` (+ tests), `fragments/presets.py` keyframe / range helpers.
2. `ui/fragments/animation_controls.py`: the time toolbar, modes, clock, play / stop / rewind, Space, loop play; the
   driver honours `time`, clears per frame in Animation mode, applies splines and easing per frame.
3. Viewport overlay: path drawing with projection; occlusion through `Surface.depth_at` batch reads (one read of
   the depth texture per delivered image, sampled in numpy).
4. `easing_dialog.py` (F7), F8 / F9 actions, *Range-* presets, *save easing in presets*.
5. `timeline_window.py` with `widgets/timeline.py` + curve lanes.
6. Interpolation mode (§9.6) in `fragments/interpolate.py` (numeric parameters between keyframe presets; reuse
   `animation/interpolate.py`'s easing helpers where they fit).
7. Tests: `test_fragments_animation.py`, `test_fragments_animation_ui.py`.

#### Phase 4 — the render window, batch, CLI

1. `fragments/gl/tiles.py` (+ tests), `fragments/gl/final.py` (+ GL tests: tiled == untiled, padding, EXR depth).
2. `fragments/gl/final_job.py`: `FragRenderJob(QThread)` with `RenderControl`, `FragProgress`, `FragOutcome`;
   writers via `render/output.py` / `render/exr.py`; the autosave fragment folder (`saveFragments` semantics:
   `<name> Files/`, includes, release textures, overwrite prompt handled in the window before start).
3. `ui/fragments/render_panels.py` (Tile / Quality / Animation panels; reuse `OutputPanel`, `RenderProgressPanel`,
   `render_size_panel` link / swap pieces), `render_window.py` (`JobWindowBase` subclass; plan + ETA; preview
   dialog with Save); the ffmpeg options (the animation render panels' video group reused).
4. `fragments/batch.py`, `ui/fragments/batch_dialog.py`, `tools/render_frag.py` (argparse; EGL fallback; exit codes).
5. Tests: `test_fragments_render_window.py`; CLI smoke test on two examples; `--check` over the corpus in the slow
   suite.

#### Phase 5 — textures, gradient bridge, mesh export, preferences, help

1. `fragments/textures.py` (+ tests on small generated images / an EXR written by `render/exr.py` / a cube strip),
   `fragments/gl/textures.py` (+ GL tests), `SamplerWidget` completion (channels, browse, red state), *Clear texture
   cache*.
2. `fragments/gradient_glsl.py` (+ tests). The host has no GIMP `.ggr` reader (`formats/` covers ugr / map / flame /
   chaos / ufr / fa / images), so add `formats/ggr.py` (segments → stops, the registry entry; the Gradient Library
   gains `.ggr` for free) and keep ggr2glsl's exact blend / colour-type maths in `gradient_glsl.py` for the GLSL
   output; `ui/fragments/gradient_dialog.py`.
3. `fragments/gl/mesh.py` (probe shader, slices → `VoxelGrid`), `MeshFromDEJob`, `mesh_export_dialog.py`, the 3D
   Editor hand-off; GL tests on the sphere shell.
4. `preferences_dialog.py` (§12.4) and the settings keys; `help.py`; log-to-file; *Test GLSL versions*; verbose.
5. Tests: §14.3 texture / mesh cases; preferences persistence; gradient output check.

#### Phase 6 — polish and performance

1. Watchdog auto-tiling and adaptive subframes-per-pass in `FragJob` (+ a test with an artificially slow fragment:
   a `for` loop of N iterations; assert the job switches to tiles when the budget is tiny).
2. Optional shared-context `QOpenGLWidget` display (`ui/fragments/gl_viewport.py`) behind the `FragViewport`
   interface; a preference; measurements recorded in `docs/fragments.md`.
3. Completer polish (signatures for GLSL built-ins with one-line docs), editor themes, bracket matching polish.
4. Documentation: `README.md` section complete, `docs/fragments.md` complete (user guide, language reference,
   differences from FragM, not-ported list), `docs/rendering.md` gains a paragraph on the second service.
5. Full-suite run, pyflakes, a review cycle against the repository rubric; TASK_STATE notes.

---

## 16. Risks and mitigations

| Risk | Mitigation |
|---|---|
| Legacy GLSL constructs the layer does not anticipate (user functions shadowing built-ins, odd `#version` placement, driver-specific leniency that fragments relied on) | corpus test with an expected-pass list; the *Patch only* / *Off* modes; the failure report file; the preprocessed-source viewer; every fix becomes a test case |
| GPU watchdog resets on heavy fragments (the classic Fragmentarium problem) | interactive half-resolution; automatic viewport tiling under a time budget; tiles + subframes in hi-res; a visible *tiled n×n* status so the user understands |
| Read-back cost at large viewports | measured in phase 1; adaptive subframes-per-pass; the shared-context blit option in phase 6 |
| `RenderService` generalisation destabilising the flame windows | the default factory reproduces today's code path; the existing render / viewport tests run unchanged; the change is ~40 lines |
| Double precision (`dvec`, `#version 400+`) unavailable on some machines (macOS: GL 4.1 ok; Mesa llvmpipe: 4.5 ok; old Intel: no) | capability report at start-up; a clear build message; the examples that need it are tagged in the library |
| Include / texture path differences between FragM installations and ours | FragM's resolution order exactly; the bundled `Include/` last; *Tried paths* listed in the log like FragM |
| Preset semantics drift (clamping, lock suffixes, easing lines) breaking FragM round trips | the settings-text tests use strings produced by FragM (taken from the examples' presets and the `3Dickulus-HOW-TO.txt` samples) |
| Thread-safety slips (GL on the GUI thread) | all GL behind `FragEngine`, created in `EngineFactory.create()` on the worker; an assertion on the owning thread id in debug |
| Scope: FragM is large | phases each complete in themselves; the parity table (§2) is the checklist; the not-ported list is explicit (shader ASM, translations, mencoder) |

---

## 17. Decisions and their reasons

1. **Offscreen rendering on a worker thread, not `QOpenGLWidget`.** FragM blocks its GUI during heavy frames and
   hi-res renders (it hides the GL area behind a pixmap while tiling). The host already solved this for flames; one
   model for all renderers keeps the code uniform, the tests headless, and lets the library render thumbnails
   with the same engine.
2. **A complete compatibility layer rather than a compatibility-profile context.** moderngl / glcontext create core
   contexts; macOS has no compatibility profile; AMD is strict. FragM's own patch already proves the macro
   approach; we finish it. The spike shows the corpus is within reach.
3. **`.fafrag` as FragM-compatible text.** The presets *are* the parameter store in the Fragmentarium world;
   wrapping them in JSON would break every round trip with FragM and with the thousands of existing `.frag`
   files. Metadata that FragM has no notion of rides in a comment.
4. **Shared scheduler.** The service's key / priority / pause semantics are exactly what a second renderer needs;
   copying 250 lines would be the DRY violation the repository's review rubric flags.
5. **Python batch API instead of QtScript.** PySide6 has no QtScript; the `.fqs` scripts are render-farm recipes,
   which a CLI + dialog express more directly; the host's Script Editor can call the batch API too.
6. **Examples bundled as package data.** The same approach as `formulas/library/`; the fragments *are* the
   "built-in library / templating system" the feature asks for, and the test corpus.
7. **Mesh export through the existing `solid/` pipeline.** Only a DE sampler is new; the isosurface, clean-up,
   report and every writer already exist and are tested.
8. **Not ported**: the NVIDIA shader-ASM browser (driver-private, no binding), the GUI translations, mencoder,
   M. Benesi's feedback-array "zap" tools (removed in FragM 2.5 already).

---

## Appendix A — menu-by-menu parity checklist (FragM → Fragments)

| FragM menu item | Fragments | Notes |
|---|---|---|
| File ▸ New 2D / New 3D / Open / Reload / Save / Save As / recent / Close Tab / Exit | File ▸ New ▸ (templates) / Open… / Reload / Save / Save as ▸ (`.fafrag` · `.frag`) / recent / Close tab / Close window | Exit closes the window, not the app |
| Edit ▸ Cut / Copy / Paste / Find / Shader Asm / Indent Script / Insert Command ▸ / Add Easing Curve F7 / Add Key Frame F8 / Select Preset F9 / Timeline Editor / Preferences | Edit ▸ Undo / Redo / Cut / Copy / Paste / Find / Replace / Go to line / Indent / Insert command ▸ / Templates ▸ / Insert gradient… / Preferences…; Animation ▸ Add easing curve F7 / Add keyframe F8 / Select preset F9 / Timeline editor | Shader Asm not ported |
| Render ▸ Compile GLSL F5 / High Resolution and Animation Render / Output Preprocessed Script / Fullscreen / Save Screen Shot / Edit Cmd Script / Video Encoding | Build ▸ Build F5 / Auto-build / Show preprocessed source / Test GLSL versions / Clear texture cache; Render ▸ Render… Ctrl+R / Batch render… / Export mesh… / Fullscreen Esc / Save screenshot… | video encoding is in the render window |
| Parameters ▸ Reset All F1 / Copy Settings F2 / Copy Group / Paste F3 / Paste from Selected Shift+F3 / Group to preset F4 / Save to File / Load from File | Parameters ▸ same, plus Reset group, Lock / Unlock group, Hide unused (toggle) | |
| Examples ▸ (tree) | Library ▸ Examples (tree) / Show library pane / Add folder… / Edit library… | |
| Windows ▸ (docks) | Windows ▸ Library / Parameters / Log / Time toolbar / toolbars | |
| Help ▸ About / Welcome / Mouse and Keyboard / Scripting help × 4 / web links | Help ▸ Mouse and keyboard / Fragment language reference / Batch rendering & CLI / Welcome note / FragM wiki · FractalForums · GLSL spec (links) | |
| Options ▸ Windows / Clear Textures / Clear Animation Actions / Test versions / Loop Camera Path | Build ▸ Clear texture cache / Test GLSL versions; Animation ▸ Clear animation objects / Loop camera path / Loop play / Interpolation ▸ | |
| Toolbars: File, Edit, Buffer Dimensions, Render (Build), Rendering Mode (Progressive / Animation, rewind / play / stop, Subframe Max, Done n), Time (label, slider, length) | the same two rows (§1.1) | FPS in the status bar as in FragM |

## Appendix B — key module skeletons

```python
# fractalchemy/fragments/source.py
@dataclass
class LineMap:            # emitted line index -> (file index, line number) or None for generated lines
    files: list[Path]; origins: list[tuple[int, int] | None]
    def origin(self, emitted_line: int) -> tuple[Path, int] | None: ...

@dataclass
class FragmentSource:
    fragment: list[str]; vertex: list[str]; line_map: LineMap; vertex_line_map: LineMap
    params: list[GuiParameter]; presets: dict[str, str]; textures: dict[str, Path | None]
    texture_params: dict[str, dict[str, str]]; camera: str = "2D"; buffer: str = ""
    buffer_shader: "FragmentSource | None" = None; clear_on_change: bool = True
    subframes_between_redraws: int = 0; subframe_max: int = -1; depth_to_alpha: bool = False
    auto_focus: bool = False; has_pixel_size: bool = False; version_line: str = ""
    dependencies: list[Path] = field(default_factory=list); messages: list[Message] = field(default_factory=list)

# fractalchemy/fragments/preprocessor.py
class Preprocessor:
    def __init__(self, files: FileManager, move_main: bool = True): ...
    def parse(self, text: str, path: Path | None) -> FragmentSource: ...
    def create_autosave_fragment(self, text: str, path: Path | None) -> FragmentSource: ...

# fractalchemy/fragments/glsl_compat.py
@dataclass(frozen=True)
class CompatOptions: mode: str = "modernise"; context_glsl: int = 330; has_fp64: bool = False
def modernise(source: FragmentSource, options: CompatOptions) -> ModernSource  # .vertex, .fragment, .maps, .version, .notes

# fractalchemy/fragments/gl/engine.py
class FragEngine:
    name = "Fragments GPU"
    def __init__(self, ctx=None): ...            # creates a standalone context when none is given
    def capabilities(self) -> Capabilities: ...  # gl_version, glsl_versions, max_texture, fp64, renderer
    def build(self, modern: ModernSource) -> Program: ...   # cached; raises ShaderBuildError(diagnostics)
    def start(self, request: FragRequest, settings: FragRenderSettings) -> FragJob: ...
    def close(self) -> None: ...

# fractalchemy/fragments/gl/job.py
@dataclass(frozen=True)
class FragRenderSettings: width: int; height: int; subframe_max: int; subframes_per_pass: int = 1
                          scale: float = 1.0; tile: TileSpec | None = None; time: float = 0.0
class FragJob:
    stats: RenderStats
    def run_pass(self, cancelled: Callable[[], bool]) -> np.ndarray | None: ...
    def close(self) -> None: ...

# fractalchemy/ui/fragments/document.py
class FragDocument(QObject):
    source_changed = Signal(); needs_build_changed = Signal(bool); built = Signal(object, object)
    build_failed = Signal(list); parameters_changed = Signal(list, bool, bool); preset_applied = Signal(str)
    camera_changed = Signal(); path_changed = Signal(object); modified_changed = Signal(bool); undo_changed = Signal(bool, bool)
    def set_text(self, text: str) -> None; def set_value(self, name, value, merge_key=None) -> None
    def apply_preset(self, name: str) -> None; def set_lock(self, name, lock: LockType) -> None
    def undo(self) / redo(self); def request(self, settings) -> FragRequest
```

## Appendix C — spike results (`plans/spikes/`)

`frag_modernise_spike.py` (170 lines): a minimal preprocessor (includes, presets, `#vertex`, annotation stripping
with defaults), a macro-based moderniser to `#version 330 core`, a moderngl render loop with ping-pong RGBA32F
surfaces, eight subframes and the buffershader display pass, run on llvmpipe (Mesa 25, GL 4.5 core):

* `2D Systems/Mandelbrot.frag` (Progressive2D + BufferShader): compiles, renders the set (white, since only the
  preset's camera values were uploaded in the first run; correct once annotation defaults were applied).
* `Historical 3D Fractals/Mandelbulb.frag` (`DE-Raytracer.frag`, 69 parameters, `gl_FragDepth`): compiles, renders
  a lit, coloured Mandelbulb in 1.7 s for 8 subframes at 256×160 on the software rasteriser.
* `frag_compile_all_examples.py`: 138 / 188 runnable examples compile through this prototype; the 50 failures are
  classified in §5.6 (prototype include handling 31, macro clash 1, FragM-broken or dependency-missing 6–8, order
  of definition 3, driver strictness 4 — each with a planned fix or an "also fails in FragM" note).

Two findings shaped the plan: `#include` must match at column 0 only (FragM's regex) and be purely textual (files
are included twice on purpose); and the `texture2D → texture` rewrite must be a wrapper function, not a macro.

## Appendix D — implementation status (end of phase 6)

All six phases are implemented; the code map of §4 holds with these additions and deviations:

| Plan item | Status |
|---|---|
| Phases 1–4 (core loop, files and library, animation, render window / batch / CLI) | done as planned; `.fafrag` metadata, thumbnails, Catmull-Rom paths, easing curves, timeline, tiles + padding, EXR with depth, ffmpeg, `tools/render_frag.py` |
| §9.6 interpolated presets | done: `fragments/interpolate.py` (`KeyframeBlend`), *Animation ▸ Interpolation ▸ All parameters*, saved in the metadata |
| §12.1 textures | done; EXR channel selection is parsed but the loader takes RGB (documented) |
| §12.2 gradient bridge | done as `formats/ggr.py` (host format, GIMP's reference maths — ggr2glsl's sine / sphere shapes ran backwards and its curved shape missed the midpoint) + `fragments/gradient_glsl.py` (segments / table / texture forms, object / background roles) + `gradient_dialog.py` |
| §12.3 mesh export | done: `gl/mesh.py` probe (k slices per draw, `fit_bounds`, colours from `baseColor`), `fragments/mesh.py` (surface nets at `DE = threshold × voxel`, the host's clean levels and report, OBJ / STL / PLY / glTF / USD), `mesh_export_dialog.py` + `mesh_job.py` (own thread and context, preview, *Send to 3D Editor*) |
| §12.4 preferences | done: `fragments/preferences.py` + `preferences_dialog.py`; keys under `fragments/preferences/` |
| §12.5 help | done: `ui/fragments/help.py` (guide from `docs/fragments.md`, CLI page, welcome note, links) |
| §12.6 log | done incl. log-to-file with rotation and *verbose* |
| *Test GLSL versions*, *Clear texture cache* | done through `gl/tasks.py` (engine chores as priority jobs on the service thread; `CompatOptions.force_version`) |
| §6.8 watchdog | done: `FragRenderSettings.subframe_budget_ms`; `FragJob` times each subframe (`ctx.finish`) and splits the next ones 2×2 … 4×4 with scissors; `BuildFacts.tiled`; status bar *tiled n×n* |
| §6.9 shared-context blit | not done (the read-back path is not the bottleneck on the measured systems; documented as a possible addition) |
| Completer polish | done: GLSL built-ins with signatures and one-line docs, the host's words, own functions with signatures |
| Editor themes, Shader Asm, EXR tools menu, spline depth occlusion | not ported (documented in `docs/fragments.md`) |
| Fragments without `#vertex` | extension: a pass-through vertex shader is supplied (FragM refuses them) |
