# Rendering design: one scene, two engines

Fractalchemy renders with two engines that **share one definition of the scene** and differ only
in how they trade precision for speed. The preview engine exists for immediate feedback while
exploring; the final renderer exists for numerical precision and output quality.
Because both read the same `Flame` — formulas, camera, colouring, palette — the viewport is a
faithful preview of the final render.

```
                     fractalchemy/fractal            (shared, Qt-free)
            Flame · XForm · Camera (2D + 3D) · Coloring · palette
            variations.py  — the registry: every variation defined for numpy AND GLSL
            formats/       — .flame (Apophysis/flam3) · .chaos (Chaotica) · .fa (ours)
                               │
                     fractalchemy/formulas           (the formulas themselves)
            builtin/ (Python)  ·  library/*.c (plugin dialect → lang/ compiler)  ·  user folders
                               │
                 CompiledFlame (render/compiled.py)
        resolved + prepared variations (pre → normal → post) · xaos table · palette
                ┌──────────────┴───────────────┐
      Preview engine (render/gpu_engine.py)   CPU engine (render/cpu_engine.py)
      moderngl / OpenGL 3.3, float32          numpy, float64, one population per thread
      generated GLSL per flame (codegen.py)   bincount histograms merged per pass
                └──────────────┬───────────────┘
                tone map (render/tonemap.py): numpy + GLSL, same constants
                               │
             RenderService (render/service.py): one worker thread,
             priority queue, cancellation, progressive passes, pause/resume of refining jobs

   Final renderer (render/final_engine.py) — one FinalRenderJob thread per render
        samplers.py: CpuSampler (worker processes, shared-memory histogram, float64)
                     GpuSampler (GpuPopulation → RGBA32F texture → float64 master)
        per tile:  histogram → log_scale → density estimation → reconstruction filter → finish
        output.py: PNG / TIFF 16-bit writers, Pillow formats, SVG, embedded parameters
```

## The scene (`fractalchemy/fractal`)

* `Flame` holds `xforms` (each: weight, colour, colour speed, opacity, pre/post affine, variation
  weights, parameters, xaos row), an optional `final` transform, `Camera`, `Coloring` and a
  256-entry palette. Conventions follow flam3/Apophysis exactly (coefficient order, y pointing down,
  `color_speed = (1 − symmetry) / 2`, `scale · 2^zoom` pixels per unit) so files round-trip.
* `variations.py` is the registry; the formulas themselves live in `fractalchemy/formulas/` (see
  [formulas.md](formulas.md)). Each entry carries a numpy function and GLSL written from the same formula —
  either natively (`builtin/`, helper names `t`, `w`, `r2`, `r`, `theta`, `phi`, `P_<param>`, `rnd(s)`) or
  compiled from the Apophysis plugin C dialect (`library/`). `tests/test_variations.py` runs every one on
  the same points in both engines and asserts they agree, so a variation cannot silently mean different
  things in the two engines.
* Points carry `(x, y, z, colour)`. A transform runs, in Apophysis's order: colour blend → pre-affine →
  `pre_` variations (rewrite the input point) → normal variations (accumulate) → `post_` variations
  (rewrite the accumulator) → post affine → direct colour blend (`var_color`). After the final transform
  the 3D camera (pitch, yaw, perspective, zpos, depth of field; `render/projection.py`) projects onto the
  flat camera.
* `formats/` turn files into `Flame`s. Unknown variations are recorded in `Flame.unsupported` and shown
  in the status bar rather than refusing the file. `.fa` is JSON (`Flame.to_dict()`), so it is diff-friendly
  and extensible: unknown keys are ignored, missing keys take defaults.

## Preview engine (GPU)

One pass:

1. **Iterate** — a vertex shader advances every point of the population (`PREVIEW_POINTS`) by one
   chaos-game step: choose the next xform from the xaos table for the previous xform, apply pre-affine,
   `pre_blur`, the variation sum, post-affine, blend the colour. Transform feedback writes the new state
   (x, y, colour, last xform, RNG seed) into the other buffer. Non-finite points are re-seeded.
   The first draw of a job runs `PREVIEW_FUSE` iterations inside the shader (`u_iters`) without plotting.
2. **Plot** — the population is drawn as `GL_POINTS`: the final xform is applied, the camera maps the
   point to clip space, and `(palette colour × opacity, opacity)` is added into an RGBA32F histogram.
3. **Tone map** — a fullscreen pass applies the Apophysis log-density mapping and the RGBA8 result is
   read back and handed to the GUI thread.

The flame's *structure* is compiled into GLSL (one function per xform, a `switch` to dispatch);
all *numbers* live in a float texture addressed by generated indices, so parameter changes only
re-upload a texture. Programs are cached by source text.

## CPU engine

The same algorithm vectorised over a point population in numpy (float64). Each worker thread owns a
population, an RNG and a private histogram; `np.bincount` accumulates hits; partial histograms are summed
after each pass. numpy releases the GIL in its kernels, so the threads run concurrently. It is the
automatic fallback when no OpenGL context can be created, and the basis for the precision renderer.

## Tone mapping

`render/tonemap.py` implements Apophysis's `ImageMaker` maths in normalised form (its
`BRIGHT_ADJUST`, `PREFILTER_WHITE` and `white_level` factors cancel):

```
q     = count · ppu² / (contrast · samples)
L     = brightness · contrast · 268/256 · log10(1 + q)
alpha = L^(1/γ)   (linear blend below gamma_threshold), clamped to 1
out   = vibrancy · alpha · rgb/L + (1 − vibrancy) · rgb^(1/γ) + (1 − alpha) · background
```

Normalising by `samples` (iterations plotted so far) is what makes progressive passes brighten
consistently instead of saturating. The numpy and GLSL versions are derived from one `ToneParams`
and tested against each other.

### Supersampling and the spatial filter

As in Apophysis/flam3 the histogram is a grid of *buckets*: `oversample` buckets per pixel side plus a
gutter (`RenderSettings.bucket_size`). The tone map runs in two stages — the log-density scale above is
applied **per bucket**, then `render/filtering.py`'s Gaussian kernel (Apophysis `CreateFilter`: width from
`2 · 1.8 · oversample · filter_radius`, parity of `oversample`, `exp(−2 r²)`, normalised) sums each pixel's
buckets, and gamma / vibrancy / background are applied to the result. Oversample 2 with radius 0.5 is a
plain 2×2 box (anti-aliasing of thin lines, slightly less speckle in faint areas because the log is taken
before averaging); larger radii soften. Oversample 1 / radius 0.2 is Apophysis's own preview (no filter).
No density estimation or other denoising is done anywhere.

### Tone curves

`fractal/curves.py` holds five control-point curves (overall, red, green, blue, alpha) interpolated with a
monotone cubic; `render/tonemap.py` applies them after gamma / vibrancy: the alpha curve remaps the coverage
before the background is composited, then every channel goes through *overall* and its own curve
(`r' = red(overall(r))`, as Apophysis's `csa[ch][csa[0][v]]`). GLSL reads the same 256-entry tables from a
256×2 texture. Apophysis 7X's 48-number `curves` attribute is imported by sampling its rational Béziers.

## Preview quality: samples, refinement, zoom

Graininess is only ever sample count: at quality *q* a pixel of average density has seen *q* samples, so
its relative noise is 1/√q; the GPU and CPU engines produce the same noise at equal counts (tested against
each other and a high-quality reference). Three faithful things make the preview clean:

* **Passes then refinement.** The configured `passes` deliver `quality` quickly; after them the job keeps
  adding passes that each *double* the samples (`RenderSettings.next_pass_samples`) until
  `refine_to` (default q 500) — Chaotica-style "it gets better while you look". The status bar shows
  `Refining · q 37` and finally `q 500 ✓`. A refining job yields to *any* other request (thumbnails) and
  is **paused, not restarted**: `RenderService` keeps the job and its histogram and resumes it behind the
  other work (`PRIORITY_REFINE`). The transient half-size render while interacting never refines.
* **Apophysis's zoom rule.** Apophysis renders `quality · 4^zoom` samples per pixel, so a zoomed-in view
  (where most iterations land outside the frame) is not starved; `RenderSettings.for_zoom` does the
  same (never fewer than nominal, capped at 64× = zoom 3).
* **Oversample / filter** as above (defaults 2 / 0.5, `MAX_BUCKETS` lowers the oversample for huge viewports).
* **Detail** (viewer bar): `FractalViewport.render_scale` renders at ½ or ¼ of the screen resolution.

## When the GPU rejects a shader

`GpuEngine.programs()` raises `ShaderBuildError`; the service renders that flame on the CPU and notes it in
the Info tab's *Render* group. The generated vertex/plot shaders and the driver's compiler log are written to
`<cache dir>/Fractalchemy/glsl-failures/<timestamp>.txt` (`~/.cache` on Linux, `%LOCALAPPDATA%` on Windows,
`~/Library/Caches` on macOS) — please attach that file when reporting a formula the GPU will not take.

## Responsiveness

* `RenderService` runs one worker thread that owns the engine (OpenGL contexts are thread-bound).
  Requests carry a *key*: resubmitting a key cancels the previous job for that slot, so an old render
  can never overwrite a newer view. Lower priority numbers run first; thumbnails yield to viewport work.
* The viewport frames the flame as an image of the chosen output resolution (`Camera.at_size`, width-based
  framing as in Apophysis) and renders only the *visible* part of it at screen density: the render camera is
  the image camera re-centred on the visible rectangle with `ppu × view zoom`. Output size therefore never
  changes the cost of a preview, and zooming the view to 300 % reveals real detail.
* The viewport renders at `INTERACTIVE_SCALE` (50 %) while dragging/zooming/resizing and at full size
  `INTERACTION_SETTLE_MS` after the last change. Each request has a generation number; late passes
  from older generations are discarded.
* Every pass delivers an image, so the picture sharpens in stages instead of appearing all at once.

## Final renderer

`FinalRenderer.run()` (render/final_engine.py) turns a `Flame` and a `FinalRenderSettings` into a
16-bit RGBA image, reporting `FinalProgress` as it goes; `FinalRenderJob` runs it on a QThread for
the Render window. The stages, in order, and why they are in that order:

1. **Plan** (`final_settings.plan_tiles`). The histogram has `oversample²` buckets per pixel, 32 bytes
   each in float64 (plus filter copies), so a large image exceeds any memory budget. The image is cut
   into the fewest **tiles** that fit the budget (and, on the GPU, the texture size limit), each padded
   by a **gutter** as wide as the widest filter. Every tile runs the complete chaos game and keeps only
   the points landing inside it — Apophysis's "slices" — so the plan's cost is `tiles × quality × pixels`.
   The window shows that before Start.
2. **Sample** (`samplers.py`). The CPU sampler spawns one **worker process** per core: threads do not scale
   here because a chaos-game step is dozens of short numpy kernels and they serialise on the interpreter
   and allocator (measured 1.5× on four cores; processes give ~linear scaling). The tile's histogram is a
   `(4, rows, cols)` float64 block in **shared memory**. Each worker partitions its batch of hits by
   horizontal band (a radix sort on a 16-bit key, O(n)) and adds each band under that band's lock — no
   hit is ever lost to a race, workers rarely wait, and the adds become cache-friendly, which dominates
   for multi-million-bucket tiles. The GPU sampler reuses the preview engine's `GpuPopulation` and plots
   into an RGBA32F texture that is read back into the float64 master every few seconds and cleared, so
   float32 never accumulates long enough to lose counts. Both samplers check a `RenderControl`
   (cancel / pause) between chunks; paused time is excluded from the clock.
3. **Log-scale** (`tonemap.log_scale`). Per bucket, `L = k1·log10(1 + count·k2)` and `L · mean colour`.
   flam3 and Apophysis filter *this*, not the raw counts and not the gamma-corrected colour, so the
   spatial filters below operate on it. `k2` uses the bucket density, i.e. `ppu × oversample`, and the
   samples actually run for the tile — a tile stopped early is therefore correctly exposed, just noisier.
4. **Density estimation** (`filters.density_estimate`), when chosen as the denoiser. flam3 scatters each
   bucket through a Gaussian whose width is `max_radius / density^curve`, clamped to `[min, max]`. Doing that
   per bucket in numpy is hopeless; instead the widths are quantised to a geometric ladder of ~8 levels,
   each bucket's value is split between its two nearest levels, each level's share is blurred once
   (scipy's C Gaussian when available, three box blurs otherwise), and the results are summed. Energy is
   conserved, sparse regions smooth out, dense detail stays sharp.
5. **Reconstruction filter** (`filters.downsample`). The oversampled buckets become pixels through a
   separable kernel built from a 1-D profile: Gaussian (the flam3 / Apophysis `exp(-2u²)` cut at 1.8 radii), box,
   triangle, the Mitchell-Netravali family, Lanczos 2 / 3, Blackman-Harris. Taps are strided slices of the
   padded tile, so a kernel of *t* taps costs `t × pixels` per axis.
6. **Finish** (`tonemap.finish`): gamma, gamma threshold, vibrancy and background, or — for transparent
   output — straight alpha with the colour un-premultiplied, as flam3 does.
7. **Denoise** (`denoise.py`), for image-space denoisers, once on the whole 16-bit image: guided filter and
   bilateral in numpy; OpenCV non-local means and Intel Open Image Denoise when installed.
8. **Save** (`output.py`). Pillow writes the 8-bit formats; 16-bit PNG and TIFF (`png_tiff.py`) and OpenEXR
   (`exr.py`, linear light, associated alpha, ZIP chunks) are written directly; SVG wraps the PNG. Parameters are
   embedded as Apophysis XML when asked, and the `report/` package can write a details file beside the image
   (Markdown / HTML for people, `key<TAB>value` text for pipelines) from the same `FinalResult` facts that fill
   the EXR header.

The same `ToneParams` drive the preview and the final image, which is why a final render has the same
exposure as the viewport at any density, oversample or tile split (tested against the preview engine).

## Tiers

| Mode | Numerics | Status |
|---|---|---|
| Interactive | float32 GPU, progressive | **done** (the preview engine) |
| Refined preview | continuous refinement, oversample + filter | **done** (Image tab ▸ Preview) |
| Final render | tiles; float64 CPU processes or float32 GPU with float64 accumulation; oversampling, reconstruction filters, density estimation, denoisers; 8 / 16-bit output | **done** (Render Image window) |
| Deep render | arbitrary-precision reference orbit + perturbation | later — matters for escape-time formulas more than flames |
| fp64 on the GPU | `GL_ARB_gpu_shader_fp64` | not planned: the variation snippets use float intrinsics and consumer GPUs run doubles at 1/32 rate |

Adding a variation: drop a plugin-dialect `.c` file (or a `@variation(...)` Python module) into a formulas
folder; the tests pick it up (see formulas.md).
Adding a format: implement `FractalFormat` in `fractal/formats/` and list it in `FORMATS`.
