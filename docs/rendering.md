# Rendering design: one scene, two engines

Fractalchemy renders with two engines that **share one definition of the scene** and differ only
in how they trade precision for speed. The preview engine exists for immediate feedback while
exploring; the final engine (in progress) exists for numerical precision and output quality.
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
* The viewport renders at `INTERACTIVE_SCALE` (50 %) while dragging/zooming/resizing and at full size
  `INTERACTION_SETTLE_MS` after the last change. Each request has a generation number; late passes
  from older generations are discarded.
* Every pass delivers an image, so the picture sharpens in stages instead of appearing all at once.

## Tiers (roadmap)

| Mode | Numerics | Status |
|---|---|---|
| Interactive | float32 GPU, progressive | **done** (this preview engine) |
| Refined preview | more passes / full quality on the GPU | settings exist (`passes`, `quality`), UI to come |
| Precision render | float64 CPU (multi-threaded) and/or fp64 GPU, density estimation, oversampling, filters | CPU engine is the base; filtering/DE to come |
| Deep render | arbitrary-precision reference orbit + perturbation | later — matters for escape-time formulas more than flames |
| Output | PNG / TIFF / OpenEXR with saved render settings | to come |

Adding a variation: add one `@variation(...)` entry in `variations.py` with both forms; the tests pick it up.
Adding a format: implement `FractalFormat` in `fractal/formats/` and list it in `FORMATS`.
