# Proposed variations

**Status**: the importer (`tools/import_jwf_variations.py`) now translates JWildfire variations mechanically; its
runs have added 268 of them to `fractalchemy/formulas/library/jwildfire/` (see `docs/jwildfire_import.md` for the
full list and for what could not be translated, by reason). Of the names below, the §1 classics, the lattices,
the one-step attractors, the `_bs` trig set, the map projections and most of §5's warps are in; the `cut_*` /
`dc_*` / `glsl_*` shader families, the Jacobi functions, `hexes`, the `Complex`-based maps and everything with
state or resources remain the hand-porting queue.

A survey of what the formula library lacks and what could fill the gaps, written against the **JWildfire** sources
(`JWildfire/src/org/jwildfire/create/tina/variation/*Func.java`, V9.20 tree, 1 010 variations by `getName()`) and
our own registry (566 formulas loaded). 634 JWildfire names are not in our set; this document groups them,
explains what each family does, says how portable it is to the formula dialect, and puts the classics and
other ideas beside them. Each section ends with a priority.

How portability was judged: JWildfire's `transform()` maps onto the dialect one to one (`pAffineTP.x/y/z` →
`FTx/FTy/FTz`, `pVarTP.x += …` → `FPx += …`, `pAmount` → `VVAR`, parameters → `VAR()`, `pContext.random()` →
`random01()`, `MathLib.*` → the math functions, `init`/`initOnce` → `PluginVarPrepare`). Things the dialect cannot
do are images, fonts and files at render time (`RESSOURCE_*` / `SUPPORTS_EXTERNAL_SHAPES`), code compiled at run
time (`VARTYPE_EDIT_FORMULA`), and sub-flames. 457 of the 634 also carry JWildfire's own CUDA translation
(`SupportsGPU`), which doubles as a second reference when verifying the numpy and GLSL twins.

**Licence**: JWildfire is LGPL-2.1 (each file's header). Many variations name a further author in a comment
(Jesus Sosa, Brad Stefanov, Whittaker Courtney, Steven Brodhead Sr, CozyG, Rick Sidwell, Jed Kelsey …) and some
are ports of GPL Apophysis plugins (`hexes` from slobo777's *Hexes and Crackle*). Keep the existing practice —
one provenance + licence header per file naming the original author — and a `library/jwildfire/LICENSE` note.

---

## 1. Classics and near-classics we are missing

These exist in flam3 / Apophysis / JWildfire and turn up in flames in the wild, so they are the first to add.
All are short 2D maths with a CUDA twin in JWildfire; each is an afternoon at most.

| name | what it does | notes |
|---|---|---|
| `twintrian` | flam3 classic: `sinr·log₁₀(sin²r)` and `sinr·sin(πr)` — the "two triangles" twist | we have `twintrian2` only |
| `disc2` | flam3: `disc` with a rotation `rot` and a `twist` of the angle | `rot`, `twist` |
| `disc3` | Brad Stefanov's disc with eight scale / shift parameters | `a`…`h` |
| `flower` | flam3 `flower`: petals via `r·cos(holes·θ)` | we have `flower2` / `flower3D` |
| `parabola` | flam3 `parabola` blur: `width`, `height` | random |
| `secant` | flam3 `secant2`'s original form | — |
| `rays1`, `rings3`, `hole2` | Raykoid666's rays, a third `rings`, Michael Faber's `hole` with four parameters | — |
| `lissajous` | Jed Kelsey's Lissajous curve as a variation (`tmin`, `tmax`, `a`–`e`) | — |
| `jac_cn`, `jac_dn`, `jac_sn`, `jac_elk` | Jacobi elliptic functions (arithmetic-geometric mean loop), modulus `k` | we only have `jac_asn` |
| `polylogarithm` | `Li_n(z)` on the complex plane (`n`, `zpow`) | series loop |
| `vogel` | Victor Ganora's Vogel spiral (sunflower seed packing, golden angle) | — |
| `spirograph`, `rhodonea`, `epitrochoid`, `astroid`, `deltoid`, `nephroid`, `catenary`, `lituus_var`, `involute` | classic plane curves as point generators / maps | `rhodonea` (CozyG) is a 500-line configurable rose with inner / outer spread modes |
| `cylinder_apo`, `log_apo`, `petal3D_apo` | the Apophysis-flavoured variants JWildfire keeps beside the flam3 ones | only worth it for compatibility |
| `onion`, `onion2`, `bulge`, `taper`, `squircular`, `invsquircular`, `inversion`, `invpolar`, `intersection` | small warps: onion-shell folding (chronologicaldot), image-warp bulge, taper, square↔circle maps, circle inversion | — |
| `stereographic`, `stereographic_plane`, `mercator`, `mercator_cylinder`, `gnomonic_proj`, `azimuthal`, `hammer`, `robinson`, `sinusoidal_proj` | map projections as variations (JWildfire's *projection* set) | — |
| `joukowski` / `zhukowski`, `schwarz_christoffel`, `mobius3D_with_inverse`, `mobiqN`, `quaternion` | conformal maps and quaternion Möbius | `Complex` helper in Java → `std::complex` in the dialect |
| `cos2_bs` … `tanh2_bs`, `csc_squared`, `sqrt_acosh` …, `acosech`, `acosh`, `acoth`, `exp2_bs`, `exp_multi`, `f_complex` | Brad Stefanov's scaled complex trig (`x1`, `x2`, `y1`, `y2` per function) and the inverse hyperbolics | 14 files, nearly identical — generate them |
| `tangent3D`-style 3D siblings: `blade3D`, `blob3D`, `butterfly3D`, `pie3D`, `pdj3D`, `cylinder3D`, `hexnix3D`, `hexprism3D`, `bubbleT3D`, `juliascope3Db`, `hypertile3Db`, `hypertile3D2b` | the 2D formula with a depth rule | — |
| `pre_blur3D`, `pre_flatten`, `post_flatten`, `pre_recip`, `pre_stabilize`, `pre_sinusoidal3d`, `pre_disc3d`, `post_trig`, `post_ztranslate_wf` | pre / post helpers JWildfire users expect | — |

**Priority: first.** Small, expected, and `.flame` files from JWildfire reference them.

---

## 2. Tilings, lattices and Truchet patterns

JWildfire is rich where we are thin: cell-based warps that break the plane into tiles and act per cell.

- `hexes` — slobo777's *Hexes* (the sibling of `crackle`, which we ported by hand): hexagonal cells, each scaled /
  rotated / powered about its centre (`cellsize`, `power`, `rotate`, `scale`). Port alongside `crackle`; shares
  its Voronoi helpers. `dc_hexes_wf` colours by cell.
- `hexagonal`, `honeycomb`, `bravais`, `lattice`, `diamond_lattice`, `tri_lattice`, `tessellate`, `quasicrystal`
  (`freq`, `amp` — Penrose-like 5-fold interference), `penrose_fold`, `voronoi_fold`, `worley` (`scale`, `jitter`),
  `wangtiles` (needs a tile image — skip), `arctruchet`, `truchetflow`, `msTruchet`, `triantruchet`, `truchet_ae`,
  `tile_reverse` (Whittaker Courtney), `sphtiling3v2`, `de_stijl`, `drunken_tiles`, `brick`, `chainmail`,
  `gear_teeth`, `weave`, `tweed`, `labyrinth`, `nsudoku`, `taprats`, `quilt`.
- The **`cut_*` family** (47 formulas, Jesus Sosa, from *The Book of Shaders*): each computes a pattern value at
  the point — bricks, circles, hexagonal dots, Truchet, Celtic knots, zig-zags, spirals, Voronoi, metaballs,
  Kleinian, Mandelbrot, text glyphs … — and keeps or discards the point by it (`mode`, `zoom`, `invert`).
  They are 2D "masks" that carve shapes out of whatever feeds them; 2D + `BASE_SHAPE`. Most have a CUDA twin.
  The Java uses a small `vec2`/`G.*` GLSL-lookalike library; in the dialect those become helper functions
  (`fract`, `step`, `smoothstep`, `mix` — a shared `shaderlib.h` next to `noiseb.h` would serve all 47).
- **Symmetry groups** (Jesus Sosa after McGregor & Watt): `sym_bg1`–`sym_bg7` (the seven frieze / band groups)
  and `sym_ng1`–`sym_ng17` (the seventeen wallpaper groups) with `stepx` / `stepy`; plus `c_symmetry`,
  `point_mirror_symmetry`, `post_point_symmetry_wf`, `post_axis_symmetry_wf`, `mirror_rotate`, `combimirror`,
  `tqmirror`, `kaleidoimg` (image — skip). All short.

**Priority: second** — `hexes` and the lattices first (they complete families we already have), then the
symmetry groups (24 tiny files, one template), then `cut_*` once the shader helper header exists.

---

## 3. Attractors and iterated maps

One step of a classic chaotic map per point — trivial to port, visually distinctive, and JWildfire users use
them a lot:

- `hopalong` (Martin's map), `gumowski_mira`, `pickover`, `ikeda`, `tinkerbell`, `bedhead`, `duffing`,
  `clifford_js`, `symmetric_icon` (Field & Golubitsky icons: `lambda`, `alpha`, `beta`, `omega`),
  `hadamard_js`, `sattractor_js`, `threeply`, `lorenz_js` (3D, coloured by speed), `attractor_flow`
  (a family with presets, 3D), `iconattractor_js` (presets from a resource — port the presets as a table).
- The `_js` "simulation" set — `lsystem_js`, `tree_js`, `hilbert_js`, `koch_js`, `htree_js`, `gosperisland_js`,
  `siercarpet_js`, `dragon_js`, `rsquares_js`, `brownian_js`, `crown_js`, `harmonograph_js`, `recurrenceplot` —
  draw curves / fractal paths as point clouds. The curve-by-parameter ones (harmonograph, siercarpet, crown) are
  plain maths; the L-system / turtle ones build a line list at init (`PluginVarPrepare` could fill a table, up
  to a fixed size) — feasible but second-rank.
- `multi_ifs` (1 559 lines: a catalogue of named IFS presets with colouring modes) — a table-driven port.

**Priority: second / third.** The one-step maps are an hour each; do them as a batch.

---

## 4. Escape-time fractals and 3D shapes as variations

- `fract_mandelbrot_wf`, `fract_julia_wf`, `fract_dragon_wf`, `fract_pearls_wf`, `fract_meteors_wf`,
  `fract_salamander_wf` (Andreas Maschke): sample points of an escape-time set, coloured by iteration count —
  bounded loops, which the compiler supports. `fract_formula_julia_wf` / `fract_formula_mand_wf` evaluate a typed
  formula at run time — offer their presets as fixed formulas instead.
- `mandelbrot` (JWildfire's own, with `max_iter`, `invert`, `skin` …), `mandelbox2D`, `kifs3d` (Kaleidoscopic IFS,
  3D, with 557 lines of folds), `inverted_julia`, `julia_outside`, `starfractal`, `cantor`, `apollony`,
  `dragon_scale`, `gingerbread` / `gingerbread_man`.
- **3D primitives by signed distance** (Jesus Sosa after Inigo Quilez): `box3D`, `cone3D`, `cylinder3D`,
  `capsule3D`, `ellipsoid3D`, `octahedron3D`, `pyramid3D`, `rhombus3D`, `cappedcone3D`, `cappedtorus3D`,
  `ocylinder3D`, `octogonprism3D`, `bbox3D`, `rbox3D`, … — each samples random points and keeps those inside
  the SDF (a 50-iteration rejection loop), so they are random, loop-bound `BASE_SHAPE`s. Portable; heavy per
  point. Surfaces: `torus_knot`, `knots3D`, `mobius_strip` / `moebius_strip`, `seashell3D`,
  `dinis_surface_wf`, `polySurf`, `sph_harmonic`, `whitney_umbrella`, `flame_bulb`, `romanesco`, `neuron3D`,
  `cactusGlobe`, `mushroom`, `ouroboros`, `tentacle`, `vine`, `diatom`.
- 3D crops: `post_mandelbulb3d_crop`, `post_mandelbox3d_crop`, `post_bristorbrot_crop`, `post_coastalbrot_crop`,
  `post_bulbtorus_crop`, `post_benesi_crop`, `post_asurf_crop`, `post_aexion_crop` — keep points inside a 3D
  fractal (escape-time test per point); plus the 2D `crop_box`, `crop_cross`, `crop_polygon`, `crop_rhombus`,
  `crop_stars`, `crop_trapezoid`, `crop_triangle`, `crop_vesica`, `crop_x`, `post_crosscrop`, `post_point_crop`,
  `spherecrop` (we have `crop`, `circlecrop`, `hexcrop`, `hypercrop`, `post_smartcrop`).

**Priority: third** (the `fract_*` set and the 2D crops earlier — they are simple and popular).

---

## 5. Noise, warps and "natural" effects

Mostly recent JWildfire additions (2D, short, with CUDA twins) built on value / simplex / Worley noise:

- `curl_noise`, `fbm_warp`, `simplex_warp`, `gradient_warp`, `turbulence`, `marble`, `wood_grain`, `erode`,
  `liquefaction`, `ridged`, `greebles`, `natural_foam`, `membrane`, `sublimation`, `coagulation`,
  `calcination`, `fog_bank`, `cirrus`, `cumulonimbus`, `aurora`, `aurora_curtain`, `corona`, `supernova`,
  `caustic`, `resonance`, `doppler`, `faraday`, `karman_vortex`, `jet_stream`, `laminar`, `tidal_lock`,
  `roche`, `fresnel`, `glitchy1` / `glitchy2`, `satin`, `leather`, `copperplate`, `embroidery`, `lace`,
  `flourish`, `camouflage`, `dustpoint`, `ringer`, `rewind`, `piston`, `catapult`, `collision`, `mitosis`,
  `virus`, `meeple`, `busybrad`, `quintessence`, `szubieta`, `halo`, `rainbow_arc`, `color_wheel`, `colordomain`.
- They need one shared noise header (our `noiseb.h` already has simplex / Perlin for `crackle`; Worley /
  cellular would be new) — then each is a page.
- Direct-colour "shader" set (Jesus Sosa, `dc_*`, 59 of them): `dc_perlin`, `dc_worley`, `dc_voronoise`,
  `dc_turbulence`, `dc_gabornoise`, `dc_tree`, `dc_mandala`, `dc_poincaredisc`, `dc_hyperbolictile`,
  `dc_menger`, `dc_apollonian`, `dc_layers`, `dc_kaliset`, `dc_circuits`, `dc_fingerprint`, … These colour a
  random point of the plane by a shader function (`BASE_SHAPE` + `DC` + `SIMULATION`): they are fragment shaders
  run point-wise. Portable with the shader helper header; `dc_code` and the whole `glsl_*` set (19) compile
  user-typed Java / GLSL-lookalike code at run time (`EDIT_FORMULA`) — not portable as such, but our Formula
  Editor is exactly the replacement: offer the best-known ones (`glsl_kaliset`, `glsl_apollonian`,
  `glsl_mandala`, `glsl_hyperbolictile`, `glsl_fractaldots`) as fixed formulas.

**Priority: third / fourth** — after the helper header, the warps (§5) are quick wins; the `dc_*` shaders are a
longer series best done a few at a time.

---

## 6. Structural / engine-level variations (decide first, then import or skip)

- `prepost_affine`, `prepost_blob`, `prepost_circlize`, `prepost_mobius`, `pre_affine3D`, `post_affine3D`,
  `affine3D` — JWildfire's *pre-post* concept (a variation with an affine before and after, 3D rotation
  `yaw` / `pitch` / `roll`). Our pre / post affines plus a 3D affine formula cover it; `affine3D` alone is
  worth adding.
- `subflame_wf`, `pre_subflame_wf`, `ringsubflame`, `glynns3subfl` — run another flame inside a variation. Needs
  a "flame in variation" engine feature; skip unless that becomes a goal.
- `custom_wf`, `custom_wf_full`, `pre_custom_wf`, `post_custom_wf`, `dc_code`, `glsl_code`, `fract_formula_*` —
  code typed at run time. Our Formula Editor *is* this feature; nothing to import.
- `colormap_wf`, `post_colormap_wf`, `displacemap_wf`, `post_bumpmap_wf`, `text_wf`, `svg_wf`, `primitives_wf`,
  `kaleidoimg`, `wangtiles`, `iflames` — images, fonts, SVG, tile sets loaded at render time. Excluded by the
  dialect on purpose; would need a resource-in-parameter-texture mechanism.
- `dla_wf`, `dla3d_wf` (diffusion-limited aggregation grown at init), `pixel_flow`, `recurrenceplot`, `lsystem_js`
  with presets — precomputed point clouds / line lists. Possible through `PluginVarPrepare`-filled tables with a
  fixed cap; low priority.
- `afterimage`, `aftershock`, `cam`, `plane_wf`, `pointgrid_wf`, `pointgrid3d_wf`, `_slice_indicator_wf`,
  `post_prepost_affine` — JWildfire UI / render helpers; skip.

---

## 7. Beyond JWildfire: other sources worth a look

- **Chaotica** ships a handful of its own (`chaotica_*` is not a thing, but its `bwraps`-style and
  `cylinder` variants map onto ours); `.chaos` files we open already resolve to our names.
- **Fractorium / Ember** (`EmberCL`): its variation list mirrors Apophysis + JWildfire and adds a few
  (`splits3D`, `hypertile3D` variants we have; `circleblur`, `bubbleT3D` we partly have). A pass over its list
  after the JWildfire import would catch stragglers.
- **Our own ideas** that none of the programs has and the Formula Editor makes cheap: a `poincare_tile` with
  configurable {p, q} (we have `hypertile*`; a general one with the group generators exposed); a
  `voronoi_cell_color` direct-colour formula built on `voronoi.h`; parameterised **gradient-domain** colouring
  (`dc_angle`, `dc_radius`, `dc_speed`: colour by polar angle, radius or step length — tiny, useful for tests);
  and **unit-test rigs as formulas** (`probe_identity`, `probe_checker`) for the verifier.

---

## 8. Import plan

1. **Tool**: `tools/import_jwf_variations.py` — scan `*Func.java`, read `getName()`, `getParameterNames()` /
   defaults, `getVariationTypes()`, the `transform()` body and `init*()`; translate the Java subset that maps
   1:1 (assignments, arithmetic, `MathLib` calls, `if` / `for` / `while`, local `double` / `int`, `Complex`
   → `std::complex`), emit a dialect file with a provenance header, compile it, **verify numpy vs GLSL** with
   `formulas/verify.py` (and against the CUDA body where `getGPUCode()` exists), and write the survivors into
   `library/jwildfire/`. Unsupported constructs are reported per file, like `import_apo_plugins.py` does.
2. **Helpers first**: a `shaderlib.h` (GLSL-style `fract`, `step`, `smoothstep`, `mix`, `clamp`, `length`,
   `dot`, 2-vector helpers) and a `cellular.h` (Worley / Voronoi distances) next to `noiseb.h` / `voronoi.h`,
   so §2 and §5 become mechanical.
3. **Order**: §1 classics → `hexes` + lattices + symmetry groups → attractors → `fract_*` + 2D crops → warps
   → `cut_*` → `dc_*` shaders → 3D primitives and crops.
4. **Naming**: keep JWildfire's exact names (so its `.flame` files render), register an alias where the maths is
   identical to a formula we have (the `_apo` variants), and never shadow an existing name with different maths.
