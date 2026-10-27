# Rendering design: one scene, two engines

Fractalchemy renders with two engines that **share one definition of the scene** and differ only
in how they trade precision for speed. The preview engine exists for immediate feedback while
exploring; the final renderer exists for numerical precision and output quality.
Because both read the same `Flame` — formulas, camera, colouring, palette — the viewport is a
faithful preview of the final render.

```
                     fractalchemy/fractal            (shared, Qt-free)
            Flame · XForm · Camera · Coloring · palette
            variations.py  — every variation defined for numpy AND GLSL
            formats/       — .flame (Apophysis/flam3) · .chaos (Chaotica) · .fa (ours)
                               │
                 CompiledFlame (render/compiled.py)
        resolved variations · xaos selection table · palette array
                ┌──────────────┴───────────────┐
      Preview engine (render/gpu_engine.py)   CPU engine (render/cpu_engine.py)
      moderngl / OpenGL 3.3, float32          numpy, float64, one population per thread
      generated GLSL per flame (codegen.py)   bincount histograms merged per pass
                └──────────────┬───────────────┘
                tone map (render/tonemap.py): numpy + GLSL, same constants
                               │
             RenderService (render/service.py): one worker thread,
             priority queue, cancellation, progressive passes

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
* `variations.py` is the single catalogue. Each entry carries a numpy function and a GLSL snippet
  written from the same formula, with the same helper names (`t`, `w`, `r2`, `r`, `theta`, `phi`,
  `P_<param>`, `rnd(s)`). `tests/test_variations.py` runs both on the same points and asserts they agree,
  so a variation cannot silently mean different things in the two engines.
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
8. **Save** (`output.py`). Pillow writes the 8-bit formats; 16-bit PNG and TIFF are written directly (Pillow
   has no 16-bit RGB encoder); SVG wraps the PNG. Parameters are embedded as Apophysis XML when asked.

The same `ToneParams` drive the preview and the final image, which is why a final render has the same
exposure as the viewport at any density, oversample or tile split (tested against the preview engine).

## Tiers

| Mode | Numerics | Status |
|---|---|---|
| Interactive | float32 GPU, progressive | **done** (the preview engine) |
| Final render | tiles; float64 CPU processes or float32 GPU with float64 accumulation; oversampling, reconstruction filters, density estimation, denoisers; 8 / 16-bit output | **done** (Render Image window) |
| Deep render | arbitrary-precision reference orbit + perturbation | later — matters for escape-time formulas more than flames |
| fp64 on the GPU | `GL_ARB_gpu_shader_fp64` | not planned: the variation snippets use float intrinsics and consumer GPUs run doubles at 1/32 rate |

Adding a variation: add one `@variation(...)` entry in `variations.py` with both forms; the tests pick it up.
Adding a format: implement `FractalFormat` in `fractal/formats/` and list it in `FORMATS`.
