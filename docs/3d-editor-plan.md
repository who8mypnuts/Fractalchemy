# The 3D Editor — plan

A new tool window, *Windows ▸ 3D Editor*, that adds two things without touching anything that exists:

1. **Solid rendering** of the fractal shown in the main window — the point cloud treated as a surface, lit and
   shaded (what JWildfire calls *solid rendering*) — with a 3D viewport to look at it from any side, a render
   to image, and **export as a 3D object** (OBJ, STL, PLY, glTF, OpenUSD, a Blender scene) in a *full* form and a
   *cleaned, print-ready* form.
2. **Holon IFS** in the manner of Xenodream: imported (or generated) meshes placed at every point of a 3D
   iterated function system — thousands of smiley-face balls along a 3D spiral — with lights and HDRI
   environments, rendered in the viewport and exportable as instanced scenes.

**Decisions taken** (review of the first draft): `usd-core` is a requirement, so USD exports write `.usda` /
`.usdc` / `.usdz` through it; the Blender export is a script + assets; print readiness is a **report** (watertight,
manifold, thin walls, size) with a recommendation and **buttons** for each repair level — *simple clean-up*
(weld, drop debris, orient normals), *aggressive* (plus hole filling, smoothing, decimation) and *remesh* (a voxel
remesh as the last resort); the flame's 3D camera fields stay the one camera, driven by an orbit rig; **phase 1
is the solid renderer without meshing**; the scene lives in its own **`.fa3d`** file with Open / Save in the 3D
Editor from the start (materials, lights, assets and instancers will be embedded there, which `.fa` should not
carry). **Phase 1 is implemented** (§11 marks it); the rest is the design to build on. Where JWildfire is
referenced, the relevant code was read (`create/tina/base/solidrender`, `base/raster/NormalsCalculator`, `render/LogDensityFilter`,
`meshgen/*`), so the techniques named are ones known to work on fractal point clouds.

---

## 1. What the user sees

### The window
```
┌ 3D Editor ───────────────────────────────────────────────────────────────────────────────────────┐
│ Toolbar: [Use main fractal] [Solid ▾ Points/Solid/Mesh] [Render…] [Export ▾] | [Undo][Redo] | [Fit] [Cam ▾] │
├───────────────┬──────────────────────────────────────────────────┬────────────────────────────────┤
│ Scene         │                                                  │ Properties (tabs)               │
│  ▸ Fractal    │                                                  │  Render  · Materials · Lights   │
│  ▸ Mesh       │          3D viewport (orbit / pan / zoom)        │  Environment · Mesh · Instances │
│  ▸ Instancers │          solid preview, mesh, instances,         │  Export                         │
│  ▸ Lights     │          HDRI background, gizmos                 │                                 │
│  ▸ Environment│                                                  │                                 │
├───────────────┴──────────────────────────────────────────────────┴────────────────────────────────┤
│ Status: points · triangles · memory · last render / mesh / export; progress bar for long jobs     │
└───────────────────────────────────────────────────────────────────────────────────────────────────┘
```
A tool window of the main window like the others (hidden on close, remembered between runs), with its own
*scene document* and undo history. The main window is not changed: the 3D Editor **pulls** the fractal
(*Use main fractal*, and a *follow* toggle that re-pulls on every edit made in the Transform Editor), and can
**push** a flame back (*Send to main window*) when the user tweaks the fractal here.

### Workflow A — solid render of the current fractal
1. *Use main fractal* copies the flame in (camera, 3D camera, palette, colouring included).
2. The viewport shows it as a **point cloud** immediately (the engines already produce `(x, y, z, colour)`
   orbits), and as a **solid** as soon as the first solid pass lands: a surface with lighting, materials by
   transform, ambient occlusion, shadows.
3. The *Render* tab: quality (samples), resolution, the 3D camera (orbit in the viewport or type pitch / yaw /
   perspective / distance), depth of field, fog, background. *Render…* opens the **Render 3D Image** window: the
   Render Image window's size / output panels and job life cycle (`JobWindowBase`), with the solid renderer's
   own quality panel. (Built this way rather than as a mode of the Render Image window: the solid renderer has
   no tiles, filters or denoiser, so a mode switch there would have disabled most of that window.)
4. *Materials*: one per transform (diffuse, ambient, specular + size, specular colour, light-diffusion curve,
   reflection strength from the environment), or *by palette colour*. *Lights*: distant lights with altitude /
   azimuth / colour / intensity / shadow. *Environment*: an HDRI (`.hdr` / `.exr`) or a colour, exposure, rotation,
   visible as background or lighting only.

### Workflow B — mesh and export
1. *Mesh* tab: **resolution** (voxels along the longest axis), **threshold** (iso-level, with a live
   histogram), **smoothing** (Gaussian radius), **dilate / erode**, **remove pieces smaller than N triangles**,
   **colour** (vertex colours from the palette, or none). *Generate mesh* runs on the worker processes the
   final renderer already uses; the viewport shows the mesh as it arrives with a triangle count and a
   watertight / manifold report.
2. *Export* tab: the **Full** mesh (every triangle marching cubes produced, vertex colours, per-vertex normals)
   and the **Clean** mesh (welded, small pieces dropped, holes filled, normals made consistent, decimated to a
   target triangle count, smoothed; scaled to millimetres; watertight — the *print-ready* one), each to OBJ,
   STL, PLY, glTF/GLB, USD, and the Blender scene (a `.py` + assets, see §6); *with materials* (UVs + texture
   or vertex colours + shader nodes) or *object only*.

### Workflow C — holon IFS (Xenodream-style)
1. *Import mesh…* (OBJ / STL / PLY / glTF) or *Generate* (sphere, cube, torus, the current fractal's clean mesh).
   The mesh becomes an **asset** in the scene tree with its own decimated preview proxy.
2. *Add instancer*: a fractal (the main one, or a new 3D IFS built here with 3D affine transforms:
   scale / rotate / translate per transform, the usual weights / xaos) whose orbit points become **instance
   positions**, each carrying a **frame** (rotation + scale accumulated along the orbit) so every smiley face is
   turned and shrunk the way the fractal turns and shrinks. Modes: *chaos game* (N random orbit points) or
   *tree* (every composition of the transforms to depth d — deterministic, evenly filled, Xenodream's look).
3. The viewport draws the instances with the lights and the environment; *Render…* renders them; *Export*
   writes an instanced scene (USD `PointInstancer`, Blender Geometry Nodes *Instance on Points*, glTF with
   `EXT_mesh_gpu_instancing`) or a single baked mesh.

---

## 2. Architecture (what goes where)

All new code lives beside the existing packages; no existing module changes its behaviour, only a few gain a
hook (the GPU engine's program cache, the Render Image window's engine choice, the main window's menu).

```
fractalchemy/
  scene3d/                 Qt-free model (like fractal/scene.py)
    model.py               Scene3D, MeshAsset, Instancer, DistantLight, Environment, Material, SolidSettings,
                           CameraRig (orbit camera), MeshSettings, ExportSettings; to_dict / from_dict
    format.py              the .fa3d file (JSON; the fractal embedded as today's .fa dict; assets by path + hash)
    frames.py              frame accumulation along an orbit (affine-only and Jacobian modes), tree enumeration
  solid/                   Qt-free rendering and meshing core (numpy), the reference the GPU must match
    capture.py             run the chaos game and keep the points: (x, y, z, colour, xform index, frame) arrays,
                           through RenderService jobs (GPU transform feedback or the CPU engine) — reused, not rewritten
    zbuffer.py             splat points into depth / colour-index / material-id / normal buffers (np.minimum.at,
                           oversampled), with a projective 3D camera (matrix from fractal/scene.Camera + distance)
    normals.py             screen-space normals from the depth buffer (JWildfire's neighbour-pair scheme, coarse + fine),
                           optional accumulated normals from local PCA of neighbouring points (meshing, instancing)
    shading.py             deferred shading: distant lights, Phong, per-material curves, SSAO (hemisphere samples on
                           the depth buffer), shadow maps (a depth-only splat from each light), environment lighting
                           (irradiance SH9 + specular lookups into the HDRI), fog, then the existing tone map / curves
    hdri.py                readers for Radiance .hdr (RGBE) and OpenEXR (scanline, half/float; the writer in
                           render/exr.py is the model), equirect sampling, SH9 projection, prefiltered mips
    voxelize.py            density / colour voxel grids from the points (memory budget from render/memory.py),
                           Gaussian / dilate / erode filters
    marching_cubes.py      vectorised numpy marching cubes (the 256-case tables), per-vertex normals from the
                           density gradient, per-vertex colours from the colour grid
    mesh.py                Mesh (vertices, faces, normals, colours, uvs): weld, components, orient, fill holes,
                           degenerate removal, Taubin smoothing, quadric decimation, watertight / manifold report,
                           scale to mm, bounding box, volume
    uv.py                  box / cylindrical / spherical projection UVs; xatlas when installed; vertex-colour → texture bake
    io/                    obj.py (+mtl), stl.py (binary), ply.py, gltf.py (GLB, COLOR_0, textures, instancing ext),
                           usd.py (.usda writer: Mesh, normals, st, displayColor, UsdPreviewSurface, PointInstancer;
                           .usdz / .usdc through usd-core when present), blender.py (scene script + assets),
                           import_mesh.py (OBJ / STL / PLY / glTF readers)
  render/
    gpu_solid.py           the GPU twin of solid/: the same generated iterate shader; a G-buffer plot program
                           (depth test on points, colour index + material id + frame), shading in fragment shaders;
                           the engines' `start()` dispatch on `RenderSettings.solid` (a Scene3D), so the
                           RenderService runs solid jobs unchanged; the render to file is `ui/three_d/render_window.py`
                           (`SolidRenderJob`: its own engine on a worker thread, `output.save_image` for the formats)
  ui/three_d/
    window.py              ThreeDWindow (QMainWindow tool window): toolbar, scene tree, viewport, properties, status
    document.py            Scene3DDocument: the scene + undo (same shape as FractalDocument)
    viewport.py            QOpenGLWidget + moderngl: point cloud, solid image, meshes, instances, HDRI background,
                           gizmos; orbit / pan / zoom; picks the selected object
    panels/                render_panel, materials_panel, lights_panel, environment_panel, mesh_panel,
                           instances_panel, export_panel (each a widget + signals, like the editor tabs)
    jobs.py                mesh generation / export / capture as background jobs (QThread + worker processes via
                           the existing cpu_workers), progress to the status bar
  widgets/
    orbit_camera.py        the camera maths for the viewport (Qt-free) — unit-tested
```

Principles kept from the rest of the code base: every algorithm exists in numpy first (testable, the CPU
fallback) and the GPU must agree with it (a `test_solid.py` in the spirit of `test_variations.py`); the
model is Qt-free; windows coordinate, panels emit signals, documents own undo; long work runs off the GUI thread.

---

## 3. The data model

```python
@dataclass
class Scene3D:
    name: str
    fractal: Flame | None            # the solid-render subject (a copy of the main window's)
    follow_main: bool                # re-pull on edits
    solid: SolidSettings             # quality, depth test tolerance, normal mode, ao, shadows, fog, dof, background
    materials: list[Material]        # one per transform (index), plus "by colour" mode
    lights: list[DistantLight]       # altitude, azimuth, colour, intensity, cast_shadows, shadow_softness
    environment: Environment         # hdri path | colour, exposure, rotation, visible, lighting strength
    camera: CameraRig                # target, distance, pitch, yaw, roll, fov / perspective, clip planes, dof
    mesh: MeshSettings               # resolution, threshold, smoothing, dilate, min_piece, colour mode, target triangles
    assets: list[MeshAsset]          # imported / generated meshes: path, hash, transform, proxy (decimated), material
    instancers: list[Instancer]      # asset, source fractal (main or own 3D IFS), mode (chaos | tree), count / depth,
                                     # frame mode (affine | jacobian), size falloff, colour from palette, cap
    export: ExportSettings           # which forms, formats, units, uv mode, texture size, blender options
```
`.fa3d` is JSON (the flame as the `.fa` dict it already has; assets referenced by path with a content hash and an
optional embedded copy for small ones). Undo covers the scene like `FractalDocument` covers the flame.

---

## 4. Solid rendering — the pipeline

1. **Iterate** — exactly today's chaos game (the generated GLSL / numpy); the 3D camera's `pitch / yaw /
   perspective / zpos / dof` are already in `Camera`; the 3D Editor adds an orbit rig that *produces* those values
   so the main window, the Transform Editor and the 3D Editor stay one camera model.
2. **G-buffer splat** — instead of additive plotting, each point is depth-tested: per (oversampled) pixel keep the
   nearest point's depth, colour index, material (= transform index), and, when the iterate pass accumulates
   frames, its frame. GPU: a point draw with `GL_DEPTH_TEST` into an FBO with depth + two colour attachments;
   CPU: `np.minimum.at` on a flattened depth buffer, then a gather. A **depth tolerance** (JWildfire's "solid
   rendering" keeps a small band behind the front-most sample so density can still modulate brightness) blends
   the points within a band for anti-aliasing.
3. **Normals** — from the depth buffer: for each pixel, cross products of neighbour-pair offsets (JWildfire's
   16-pair coarse scheme averaged with a fine 4-pair one), rejecting pairs across depth discontinuities. Optional
   second mode: **accumulated normals** — a small neighbourhood PCA of points in 3D, done on the captured cloud
   (used by the mesher and instancing for surface-aligned frames).
4. **Shading** (deferred, per pixel): material by transform → diffuse (N·L through a light-diffusion curve),
   Phong specular with colour, ambient; **SSAO** (hemisphere samples against the depth buffer, radius / falloff /
   intensity, blurred); **shadows** (one depth-only splat per shadow-casting light from the light's view, PCF
   softness); **environment**: irradiance from SH9 of the HDRI for ambient, a specular lookup (roughness → mip);
   fog by depth; the background (HDRI, colour or transparent). Output linear RGB(A) + depth.
5. **Post** — today's tone mapping, curves, the existing DOF bokeh (the depth buffer makes it exact), then the
   Render Image window's filters / denoise / output formats unchanged.

Quality: the number of points decides the coverage; the solid renderer refines like the viewport does today
(more passes, the depth buffer keeps the nearest). Budget: the G-buffer is `width × height × oversample²` ×
(depth, colour, material, normal) — the existing `MAX_BUCKETS` guard applies.

Performance targets: viewport solid preview of a 1-million-point cloud in < 1 s on the GPU; the CPU path is the
reference and the fallback (slower, not interactive).

---

## 5. Meshing — from points to a printable object

1. **Voxelise** — a density grid (`resolution³`, memory-budgeted; 256³ float32 = 64 MB) accumulated from the
   captured points (GPU: a 3D texture via point draws into slices; CPU: `np.add.at`), plus a colour grid (palette
   index weighted by density) and, optionally, a material grid.
2. **Filter** — Gaussian smoothing (radius in voxels), dilate / erode (morphological), a density **threshold**
   chosen on a log-histogram (the UI shows it) — JWildfire's pre-filters, vectorised.
3. **Marching cubes** — numpy implementation over all cubes at once (the classic 256-entry edge / triangle
   tables), interpolated vertices, normals from the density gradient (central differences), vertex colours from
   the colour grid. (`scikit-image` has `marching_cubes`; keeping our own avoids a dependency and lets the GPU
   later do it in compute-less OpenGL via a two-pass transform feedback — not needed in phase 1.)
4. **The full mesh** — exactly that: every triangle, vertex normals, vertex colours. Large (millions of
   triangles at 256³), faithful.
5. **The clean mesh** — a pipeline with a report at each step: weld vertices (tolerance), drop degenerate faces,
   drop components under N triangles (or keep the largest K), fill small holes, **orient** faces consistently
   (propagate winding across adjacency, flip outward by volume sign), Taubin smoothing (λ/μ, iterations), quadric
   edge-collapse **decimation** to a target triangle count (own implementation; `fast-simplification` used when
   installed), recompute normals; **print checks**: watertight, manifold edges, self-intersections (sampled),
   scale to millimetres with a target size, volume and bounding box in mm, thin-wall estimate (distance from
   surface through the voxel field). The report goes in the export beside the files (`name_report.md`, like the
   render reports).

---

## 6. Export formats

| form | full | clean | materials |
|---|---|---|---|
| **OBJ** + MTL | ✓ | ✓ | vertex colours (the `v x y z r g b` extension) and/or UVs + PNG texture; MTL with Kd / map_Kd |
| **STL** (binary) | ✓ | ✓ | none (geometry only — the print format) |
| **PLY** (binary) | ✓ | ✓ | vertex colours, normals |
| **glTF / GLB** | ✓ | ✓ | `COLOR_0`, PBR material, optional baked texture; instances via `EXT_mesh_gpu_instancing` |
| **OpenUSD** (.usda; .usdc/.usdz when `usd-core` is installed) | ✓ | ✓ | `UsdGeom.Mesh` with normals, `primvars:displayColor`, `st`; `UsdPreviewSurface` material; `PointInstancer` for holon scenes |
| **Blender scene** | ✓ | ✓ | a `.py` that Blender runs (`blender --python scene.py`, or *File ▸ Import* from the UI script) building objects, a Principled BSDF node tree fed by the Color Attribute or the baked image texture through UVs, the lights and the HDRI as a World node tree, the camera; holon scenes as a point mesh with attributes + a Geometry Nodes *Instance on Points* modifier (true instancing, any count) |

*With materials* = UVs + texture (box / spherical / cylindrical projection, or an atlas through `xatlas` when
installed, vertex colours baked into the texture) or vertex colours with shader nodes; *object only* = geometry
and normals. Units: metres in USD / glTF, millimetres option for STL / OBJ print exports. Every writer is
pure Python (tested by writing and re-reading), the readers in `io/import_mesh.py` cover the same formats.

Why a Blender script rather than a `.blend`: the `.blend` format can only be written by Blender itself; a
script plus USD/GLB assets is what Blender's own documentation recommends, round-trips materials faithfully
and keeps the export independent of Blender versions.

---

## 7. Holon IFS — instancing meshes along a fractal

* **Frames.** The chaos game is extended to carry a 3×3 frame per point: `F' = J(p)·F`, where `J` is the
  transform's affine (exact for affine / linear transforms — Xenodream's holons are affine) or the local Jacobian
  of the full transform by finite differences (so variations like `spherical` or `julia3D` still turn and squash
  the instances sensibly). The frame's scale is the instance size; a *size falloff* and a *minimum size* cap
  the count of visible instances. Frames are orthonormalised with the scale kept separately (so skew stays
  optional).
* **Tree mode.** Enumerate every composition `T_i1 ∘ … ∘ T_id` of the transforms to depth `d` (with weights as
  pruning thresholds): deterministic, gap-free, the classic Xenodream structure; `count ≤ n^d`, capped.
* **Viewport.** Instanced drawing (one VBO of frames, `glDrawArraysInstanced`) with the asset's proxy mesh at
  distance and the full mesh up close; per-instance colour from the palette index; lights / environment shared
  with the solid renderer (same shading code, forward path for meshes).
* **Render.** Meshes and instances are rasterised into the same G-buffer as the solid fractal, so a scene can mix
  a solid fractal, imported meshes and instancers with shadows between them.
* **Export.** USD `PointInstancer` (positions, orientations as quaternions, scales, prototype = the asset),
  Blender Geometry Nodes, glTF instancing, or a baked single mesh (instances transformed and concatenated,
  with the clean-up pipeline available on the result).
* **Own 3D IFS editing.** The instancer's fractal can be the main window's (pulled) or one built in the
  *Instances* tab with 3D affine controls (position / rotation / scale gizmos in the viewport, weights, xaos,
  a variation per transform from the registry). A flame built here is a normal `Flame` — it can be sent to the
  main window and saved as `.fa`.

---

## 8. Lighting and environments

* Distant lights (altitude, azimuth, colour, intensity, shadows on/off, softness) — the JWildfire set, plus point
  lights later. Defaults: a key at 55° / −22° and a fill, as JWildfire's.
* HDRI: `.hdr` (RGBE — a 60-line decoder) and `.exr` (scanline half / float, uncompressed and ZIP — the mirror of
  our EXR writer), equirectangular. Used as background (rotation, exposure, blur) and as light: SH9 irradiance for
  diffuse, prefiltered mips for specular by material roughness, plus *extract N key lights from the HDRI* (the
  brightest regions become distant lights with shadows — HDRI lighting with shadows without path tracing).
* Exposure / tone mapping shared with the existing colouring (brightness, gamma, curves) so renders match.

---

## 9. What this unlocks in the formula library

With a solid renderer, depth and 3D shape become visible, and several JWildfire families that the 2D viewer
cannot show to advantage become worthwhile (see `proposed_variations.md` and `docs/jwildfire_import.md`):

* the **3D primitives by signed distance** (`box3D`, `cone3D`, `cylinder3D`, `capsule3D`, `ellipsoid3D`,
  `octahedron3D`, `pyramid3D`, `torus_knot`, `knots3D`, `seashell3D`, `dinis_surface_wf`, `polySurf`,
  `sph_harmonic`, `whitney_umbrella`, …) — surfaces and volumes meant to be lit;
* the **3D crops** (`post_mandelbulb3d_crop`, `post_mandelbox3d_crop`, `post_bristorbrot_crop`, …): Mandelbulb /
  Mandelbox shells as solids;
* `affine3D` / the `prepost_*` set: 3D affines with yaw / pitch / roll — the natural transforms of a 3D IFS
  editor (the instancer's own transforms map onto them);
* a new native formula, **`mesh_points`** — points sampled on an imported mesh's surface (the mesh as a table in
  the parameter texture), which is JWildfire's `primitives_wf` / `obj_mesh_wf` idea done with our assets: a
  transform that *is* a smiley face, usable in any flame, not only in the 3D Editor;
* `dla3d_wf`-style grown structures become possible as an *asset generator* (grow once, instance many times).

---

## 10. Dependencies, fallbacks, threading

* Required: nothing new — numpy and moderngl are already there. The viewport needs an OpenGL 3.3 context
  (`QOpenGLWidget`); without one the window still works with the CPU solid renderer showing a picture and
  orbit by re-render, and meshing / export are CPU code anyway.
* Optional, detected at run time and reported in the Export tab: `usd-core` (binary `.usdc` / `.usdz`; `.usda`
  is always available), `xatlas` (UV atlases; projections otherwise), `fast-simplification` (faster decimation;
  the built-in quadric decimator otherwise), `OpenEXR` / `imageio` (EXR compressions beyond ZIP).
* Long jobs — capture, voxelise, marching cubes, clean-up, export — run on the final renderer's worker
  processes (`render/cpu_workers.py`) with progress and cancel through the existing `JobWindowBase` pattern;
  the viewport's solid preview goes through `RenderService` at editor priority like the live previews.
* Memory: voxel grid and G-buffer sizes are checked against the same budgets as the histogram.

---

## 11. Delivery in phases

| phase | delivers | tests |
|---|---|---|
| **1. Solid render + window** ✓ done | `scene3d` model + `.fa3d`; `solid/` capture / zbuffer / normals / shading (numpy); `render/gpu_solid.py` G-buffer + shading on the GPU; `ThreeDWindow` with the viewport (points + solid, orbit rig), Render / Camera / Materials / Lights / Environment tabs; *Render…* in the Render 3D Image window; *Use main fractal* / follow / send back; a **density threshold** (`SolidSettings.min_hits`: samples per G-buffer pixel a surface needs — removes the haze blur variations scatter) | numpy vs GPU agreement on the G-buffer and shaded image (`test_solid.py`); camera maths; window opens / pulls / renders on the CPU engine; the render to file |
| **2. Mesh + export** | voxelise, filters, marching cubes, the clean-up pipeline with the report, OBJ / STL / PLY / glTF / USDA writers + readers, UV projections, Blender script export; the Mesh and Export tabs | round-trip every format; watertight / manifold checks on known shapes (sphere, torus point clouds); decimation preserves volume within tolerance |
| **3. Holon IFS** | frames in the chaos game (affine + Jacobian), tree mode, mesh import + proxies, instanced viewport, instances in the G-buffer, PointInstancer / Geometry Nodes / glTF instancing export; the Instances tab with 3D affine gizmos | frame accumulation against closed forms; instance counts; export round trips |
| **4. Environment + polish** | HDRI readers, IBL (SH9 + prefiltered), key-light extraction, shadow softness, fog, the `mesh_points` formula, the 3D formula imports from §9, documentation | HDRI decode against known images; IBL energy tests; the formulas through `test_variations` |

Each phase is shippable on its own; phase 1 alone already gives JWildfire-style solid renders of every existing
fractal.

---

## 12. Questions to settle before starting

1. **USD** — decided: `usd-core` is required (`requirements.txt`); exports go through it.
2. **Blender** — decided: the script + assets approach (§6).
3. **Print readiness** — decided: a report with a recommendation and one button per repair level (simple /
   aggressive / remesh).
4. **Camera** — decided: the flame's 3D camera fields, driven by the viewport's orbit rig.
5. **Scope of phase 1** — decided: the solid renderer without meshing (done); meshing follows as phase 2.
6. **Name and file** — decided: "3D Editor", `.fa3d` from the start, opened and saved inside the window.
