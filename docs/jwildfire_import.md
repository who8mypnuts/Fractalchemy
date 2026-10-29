# JWildfire import report

1027 variation sources scanned; **253 imported**, 312 already in the library (same name), 462 not importable.

## Imported

* **2D** (195): abs_fold, afterimage, aftershock, amoeba, apocarpet_js, apollony, astroid, aurora, aurora_curtain, azimuthal, bedhead, bravais, brick, bubble_col, busybrad, calcination, cam, cantor, catapult, catenary, caustic, cell2, chainmail, cirrus, clifford_js, coagulation, collision, color_wheel, complex, contour_map, copperplate, corners, corona, cos2_bs, cosh2_bs, cot2_bs, coth2_bs, cpow3_wf, csc2_bs, csc_squared, csch2_bs, cumulonimbus, curl_noise, cyclone, deltoid, devil_warp, diamond_lattice, diatom, dipole, disc2, disc3, domain_fold, doppler, dragon_scale, duffing, elliptic2, embroidery, epispiral_wf, epitrochoid, erode, exp2_bs, faraday, fault, fbm_warp, flourish, flower_db, fog_bank, fractal_zoom, gear_teeth, gingerbread, glitchy2, glynnia3, gnomonic_proj, gothic_arch, gradient_warp, hadamard_js, halo, hammer, heart_wf, hexagonal, hole2, honeycomb, ikeda, inflate, intersection, inverted_julia, involute, invpolar, invsquircular, invtree_js, isobar, jet_stream, karman_vortex, labyrinth, lace, lace_js, lagrange, laminar, lattice, leather, liquefaction, lissajous, lituus_var, log_apo, log_db, marble, meander, membrane, mercator, mercator_cylinder, mirror_rotate, mitosis, moebius_strip, multi_ifs, mushroom, nephroid, ouroboros, pTransform, p_wave, panorama2, parallel, pdj_v2, penrose_fold, phyllotaxis, pickover, piston, pleat, quadrupole, quasicrystal, quilt, quintessence, rainbow_arc, rays1, resonance, rewind, ridged, rings3, robinson, roche, ruffle, satin, sattractor_js, schwarz_christoffel, screw, sec2_bs, secant, sech2_bs, simplex_warp, sin2_bs, sinh2_bs, sinusoidal_proj, sph_harmonic, spirograph, spliptic_bs, squircular, standing_wave, stereographic, stereographic_plane, sublimation, supernova, superposition, svensson_js, symmetric_icon, tan2_bs, tanh2_bs, taper, tentacle, tessellate, tidal_lock, tinkerbell, toroidal, torus_knot, tqmirror (Nic Anderson), tri_lattice, tunneling, turbulence, tweed, twintrian, twist_ribbon, vine, virus, vogel, wave_func, waves2_wf, waves3_wf, waves3d_decay, waves4_wf, waves_phase, weave, weld_seam, woggle_js, wood_grain, yin_yang, zhukowski, zigzag
* **2D, BASE_SHAPE** (3): flora, maple_leaf, oak_leaf
* **2D, BASE_SHAPE, PRE** (1): pre_rect_wf
* **2D, DC** (1): pixel_flow
* **2D, DC, POST** (1): post_mirror_wf
* **2D, SIMULATION, BASE_SHAPE** (1): dustpoint
* **3D** (19): blade3D, blob3D, bubble_wf, butterfly3D, cylinder_apo, ennepers2, glitchy1, hypertile3D2b, hypertile3Db, lazysensen, log_tile2, onion, pdj3D, petal3D_apo, polySurf, shredded, spherical3D_wf, tangent3D, whitney_umbrella
* **3D, BASE_SHAPE** (1): cone
* **3D, BASE_SHAPE, DC** (1): conicalSpiral
* **3D, CROP, ESCAPE_TIME_FRACTAL, DC** (1): post_bulbtorus_crop
* **3D, CROP, POST, ESCAPE_TIME_FRACTAL, DC** (2): post_benesi_crop, post_bristorbrot_crop
* **3D, DC** (5): colorscale_wf, dc_carpet3D, lorenz_js, spirograph3D, swirl3D_wf
* **3D, POST** (1): post_colorscale_wf
* **3D, PRE** (2): pre_disc3d, pre_sinusoidal3d
* **BASE_SHAPE** (12): butterfly_fay, cannabiscurve_wf, chrysanthemum (Jesus Sosa), cloverleaf_wf, flower, japanese_maple_leaf, line, pie3D, rose_wf, seashell3D, square3D, xheart_blur_wf
* **BASE_SHAPE, BLUR** (1): r_circleblur
* **BLUR** (1): parabola
* **POST** (3): post_flatten, post_ztranslate_wf, pre_flatten
* **other** (2): waffle, whirligig

## Not imported, by reason

### unsupported construct (125)

* `AbstractAffine3DFunc.java` — no public class extending a variation base class
* `AbstractBrushStrokeWFFunc.java` — no public class extending a variation base class
* `AbstractBufferedImageWFFunc.java` — no public class extending a variation base class
* `AbstractColorMapWFFunc.java` — no public class extending a variation base class
* `AbstractDisplacementMapWFFunc.java` — no public class extending a variation base class
* `AbstractFalloff3Func.java` — no public class extending a variation base class
* `AbstractFractFormulaWFFunc.java` — no public class extending a variation base class
* `AbstractFractWFFunc.java` — no public class extending a variation base class
* `AnamorphCylFunc.java` — an inner class
* `ArcTruchetFunc.java` — an inner class
* `AttractorFlowFunc.java` — default of preset is not a constant (0, attractorMode = 0, waveMode = 0, zMode = 0)
* `BSplitFunc.java` — point member doHide
* `BoxfoldFunc.java` — uses 'new' (an object)
* `BrownianFunc.java` — an inner class
* `CSinFunc.java` — field _c of type Complex
* `ChaosCubesFunc.java` — uses 'new' (an object)
* `CircleCropFunc.java` — point member doHide
* `CircleTrans1Func.java` — an inner class
* `ColorDomainFunc.java` — field cf_runner of type ComplexFuncRunner
* `CrackleFunc.java` — no getName()
* `Crop3DFunc.java` — point member doHide
* `CropFunc.java` — point member doHide
* `CropTriangleFunc.java` — point member doHide
* `CustomWFFunc.java` — no getName()
* `CutTrianTessFunc.java` — field nb of type vec3
* `CutTruchetWeavingFunc.java` — rewrites its parameters while running
* `CutZFunc.java` — no getName()
* `DCCubeFunc.java` — rewrites its parameters while running
* `DCTriTileFunc.java` — an inner class
* `DC_BaseFunc.java` — no public class extending a variation base class
* `DLA3DWFFunc.java` — an inner class
* `DLAWFFunc.java` — an inner class
* `DinisSurfaceWFFunc.java` — point member doHide
* `DragonFunc.java` — an inner class
* `DucksFunc.java` — an inner class
* `EllipticFunc.java` — default of mode is not a constant (MODE_MIRRORY)
* `GLSLFunc.java` — no public class extending a variation base class
* `GeometricPrimitivesFunc.java` — Java collections
* `GlynnSim1Func.java` — an inner class
* `GlynnSim2BFunc.java` — an inner class
* `GlynnSim2Func.java` — an inner class
* `GlynnSim3Func.java` — an inner class
* `GosperIslandFunc.java` — an inner class
* `HamidFunc.java` — rewrites its parameters while running
* `HilbertFunc.java` — an inner class
* `Hourglass3DFunc.java` — default of maxheight is not a constant (3.0 + 3.0 * Math.random())
* `HtreeFunc.java` — an inner class
* `HyperbolicEllipseFunc.java` — an inner class
* `InternalPrePostAffinePostWFFunc.java` — field delegate of type PrePostAffineFunc
* `InternalPrePostAffinePreWFFunc.java` — field delegate of type PrePostAffineFunc
* `InternalSliceRangeIndicatorWFFunc.java` — point member rgbColor
* `InversionFunc.java` — an inner class
* `JacCnFunc.java` — an inner class
* `JacDnFunc.java` — uses 'new' (an object)
* `JacSnFunc.java` — uses 'new' (an object)
* `JoukowskiFunc.java` — field z0 of type vec2
* `KIFS3DFunc.java` — an inner class
* `KleinGroupFunc.java` — parameter avoid_reversal is not a plain field (avoid_reversal ? 1 : 0)
* `KochFunc.java` — an inner class
* `Linear3DFunc.java` — no getName()
* `LoqFunc.java` — default of base is not a constant (M_E)
* `LsystemFunc.java` — an inner class
* `MaskFunc.java` — point member doHide
* `MaurerLinesFunc.java` — an inner class
* `MaurerRoseFunc.java` — an inner class
* `MobiqNFunc.java` — default of qat", PARAM_AX = "qax", PARAM_AY = "qay", PARAM_AZ = "qaz is not a constant (1.0, qax = 0.0, qay = 0.0, qaz = 0.0)
* `Mobius3DWithInverseFunc.java` — an inner class
* `MobiusStripFunc.java` — point member doHide
* `NBlurFunc.java` — an inner class
* `NaturalFoamFunc.java` — an inner class
* `Neuron3DFunc.java` — an inner class
* `OctapolFunc.java` — an inner class
* `Onion2Func.java` — uses 'new' (an object)
* `PRose3DFunc.java` — context call getRandGen
* `PlaneWFFunc.java` — parameter blend_colormap is not a plain field (colorMapHolder.getBlend_colormap())
* `PolylogarithmFunc.java` — an inner class
* `PostAxisSymmetryWFFunc.java` — default of axis is not a constant (AXIS_X)
* `PostCircleCropFunc.java` — point member doHide
* `PostCropFunc.java` — point member doHide
* `PostCropTriangleFunc.java` — point member doHide
* `PostCrosscropFunc.java` — point member doHide
* `PostDCZTranslFunc.java` — no getName()
* `PostMandelbox3dCropFunc.java` — point member doHide
* `PostMandelbulb3dCropFunc.java` — point member doHide
* `PostZScaleWFFunc.java` — no getName()
* `PostZVarFunc.java` — no getName()
* `PowBlockFunc.java` — default of numerator is not a constant (2.0 + Math.random() * 5.0)
* `PreCircleCropFunc.java` — point member doHide
* `PreCropFunc.java` — point member doHide
* `PreWave3DWFFunc.java` — uses 'new' (an object)
* `PreZVarFunc.java` — no getName()
* `PrimitivesWFFunc.java` — default of shape is not a constant (SHAPE_SPHERE)
* `Q_odeFunc.java` — default of q_ode03 is not a constant (1.0 - 2.0 * Math.random())
* `QuaternionFunc.java` — default of logqbase is not a constant (M_E)
* `RectanglesFunc.java` — default of x is not a constant (0.3, y = 0.2)
* `RhodoneaFunc.java` — point member doHide
* `RingerFunc.java` — an inner class
* `RomanescoFunc.java` — uses 'new' (an object)
* `RsquaresFunc.java` — an inner class
* `SVGWFFunc.java` — an inner class
* `ShapeWarpFunc.java` — no getName()
* `SimpleVariationFunc.java` — no public class extending a variation base class
* `SnowflakeWFFunc.java` — an inner class
* `SphTiling3V2Func.java` — field xy of type XYZPoint
* `SphereCropFunc.java` — point member doHide
* `SphereNjaFunc.java` — uses 'new' (an object)
* `SynthFunc.java` — an inner class
* `TargetFunc.java` — default of even is not a constant (-M_PI + Math.random() + M_2PI)
* `TargetSpFunc.java` — default of size is not a constant (0.5 + Math.random() * 3.0)
* `TessShapeFunc.java` — parameter strength is not a plain field (this.strength)
* `TextWFFunc.java` — an inner class
* `TreeFunc.java` — an inner class
* `TriangleFunc.java` — default of x1 is not a constant (-0.20,y1=-0.10,z1=0.0,x2=0.20,y2=-0.10,z2=0.0,x3=0.20,y3=0.10,z3=0.0)
* `Truchet2Func.java` — rewrites its parameters while running
* `VariationFunc.java` — no public class extending a variation base class
* `WFunc.java` — default of angle is not a constant (Math.random())
* `WallPaperFunc.java` — Integer.signum
* `WangTilesFunc.java` — an inner class
* `WedgeFunc.java` — default of angle is not a constant (M_PI_2)
* `XFunc.java` — default of hypergon is not a constant (Math.random())
* `XTrbFunc.java` — an inner class
* `YFunc.java` — default of hypergon is not a constant (Math.random())
* `ZFunc.java` — default of hypergon is not a constant (Math.random())
* `ZTwisterFunc.java` — default of base is not a constant (Math.E)
* `ZVarFunc.java` — no getName()

### specialised base class (106)

* `Affine3DFunc.java` — extends AbstractAffine3DFunc (a specialised base class)
* `BrushStrokeWFFunc.java` — extends AbstractBrushStrokeWFFunc (a specialised base class)
* `ColorMapWFFunc.java` — extends AbstractColorMapWFFunc (a specialised base class)
* `CurliecueFunc.java` — extends DrawFunc (a specialised base class)
* `DCCracklePWFFunc.java` — extends DCCrackleWFFunc (a specialised base class)
* `DCCrackleWFFunc.java` — extends CrackleFunc (a specialised base class)
* `DCHexesWFFunc.java` — extends HexesFunc (a specialised base class)
* `DC_AcrilicFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_ApollonianFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_BooleansFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_CairoTilesFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_CirclesBlueFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_CircuitsFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_CodeFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_DucksFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_FingerPrintFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_FractColorFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_FractalDotsFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_GaborNoiseFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_GenericMandelbrootFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_GlyphoFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_Grid3DFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_HexagonsFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_HoshiFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_HyperbolicFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_InversionFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_KaleidoComplexFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_KaleidoscopicFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_KaliSet2Func.java` — extends DC_BaseFunc (a specialised base class)
* `DC_KaliSetFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_LayersFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_MandBrotFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_MandalaFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_MandelBox2DFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_MengerFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_MoebiusLogFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_PentaTilesFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_PoincareDiscFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_PortalFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_QuadtreeFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_RandomOctreeFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_RotationsFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_SpacefoldFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_SquaresFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_StarsFieldFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_SunFlowerFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_TeslaFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_TreeFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_TrianTessFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_TruchetFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_TurbulenceFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_VoronoiseFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_VortexFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_WarpingFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DC_WorleyFunc.java` — extends DC_BaseFunc (a specialised base class)
* `DisplacementMapWFFunc.java` — extends AbstractDisplacementMapWFFunc (a specialised base class)
* `F_ComplexFunc.java` — extends DC_BaseFunc (a specialised base class)
* `Falloff3Func.java` — extends AbstractFalloff3Func (a specialised base class)
* `FractDragonWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `FractFormulaJuliaWFFunc.java` — extends AbstractFractFormulaWFFunc (a specialised base class)
* `FractFormulaMandWFFunc.java` — extends AbstractFractFormulaWFFunc (a specialised base class)
* `FractJuliaWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `FractMandelbrotWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `FractMeteorsWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `FractPearlsWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `FractSalamanderWFFunc.java` — extends AbstractFractWFFunc (a specialised base class)
* `GLSLAcrilicFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLApollonianFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLCirclesBlueFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLCircuitsFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLFractalDotsFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLGrid3DFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLHoshiFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLHyperbolicFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLKaleidoComplexFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLKaleidoscopicFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLKaliSet2Func.java` — extends GLSLFunc (a specialised base class)
* `GLSLKaliSetFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLMandalaFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLMandelBox2DFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLRandomOctreeFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLSquaresFunc.java` — extends GLSLFunc (a specialised base class)
* `GLSLStarsFieldFunc.java` — extends GLSLFunc (a specialised base class)
* `GPatternFunc.java` — extends DrawFunc (a specialised base class)
* `GlynnS3SubflWFFunc.java` — extends SubFlameWFFunc (a specialised base class)
* `Knots3DFunc.java` — extends AbstractOBJMeshWFFunc (a specialised base class)
* `MSTruchetFunc.java` — extends AbstractBufferedImageWFFunc (a specialised base class)
* `MandalaFunc.java` — extends DrawFunc (a specialised base class)
* `NSudokuFunc.java` — extends DrawFunc (a specialised base class)
* `PostAffine3DFunc.java` — extends AbstractAffine3DFunc (a specialised base class)
* `PostBrushStrokeWFFunc.java` — extends AbstractBrushStrokeWFFunc (a specialised base class)
* `PostColorMapWFFunc.java` — extends AbstractColorMapWFFunc (a specialised base class)
* `PostCustomWFFunc.java` — extends CustomWFFunc (a specialised base class)
* `PostDisplacementMapWFFunc.java` — extends AbstractDisplacementMapWFFunc (a specialised base class)
* `PostFalloff2Func.java` — extends Falloff2Func (a specialised base class)
* `PostFalloff3Func.java` — extends AbstractFalloff3Func (a specialised base class)
* `PreAffine3DFunc.java` — extends AbstractAffine3DFunc (a specialised base class)
* `PreCustomWFFunc.java` — extends CustomWFFunc (a specialised base class)
* `PreFalloff3Func.java` — extends AbstractFalloff3Func (a specialised base class)
* `PreSubFlameWFFunc.java` — extends SubFlameWFFunc (a specialised base class)
* `RingSubFlameFunc.java` — extends SubFlameWFFunc (a specialised base class)
* `SZubietaFunc.java` — extends DrawFunc (a specialised base class)
* `SunFlowersFunc.java` — extends DrawFunc (a specialised base class)
* `SunflowerVoroniFunc.java` — extends DrawFunc (a specialised base class)
* `TapratsFunc.java` — extends DrawFunc (a specialised base class)
* `TrianTruchetFunc.java` — extends DrawFunc (a specialised base class)

### GLSL helper classes (vec2 / vec3 / mat) (67)

* `BoundingBox3DFunc.java` — GLSL vector helper classes
* `Box3DFunc.java` — GLSL vector helper classes
* `BulgeFunc.java` — GLSL vector helper classes
* `CappedCone3DFunc.java` — GLSL vector helper classes
* `CappedTorus3DFunc.java` — GLSL vector helper classes
* `Capsule3DFunc.java` — GLSL vector helper classes
* `Cone3DFunc.java` — GLSL vector helper classes
* `CropBoxFunc.java` — GLSL vector helper classes
* `CropCrossFunc.java` — GLSL vector helper classes
* `CropPolygonFunc.java` — GLSL vector helper classes
* `CropRhombusFunc.java` — GLSL vector helper classes
* `CropStarsFunc.java` — GLSL vector helper classes
* `CropTrapezoidFunc.java` — GLSL vector helper classes
* `CropVesicaFunc.java` — GLSL vector helper classes
* `CropXFunc.java` — GLSL vector helper classes
* `CutApollonianFunc.java` — GLSL vector helper classes
* `CutCelticFunc.java` — GLSL vector helper classes
* `CutChainsFunc.java` — GLSL vector helper classes
* `CutGlyphoFunc.java` — GLSL vector helper classes
* `CutHexDotsFunc.java` — GLSL vector helper classes
* `CutKleinianFunc.java` — GLSL vector helper classes
* `CutMetaBallsFunc.java` — GLSL vector helper classes
* `CutRGridFunc.java` — GLSL vector helper classes
* `CutShapesFunc.java` — GLSL vector helper classes
* `CutSpiralCBFunc.java` — GLSL vector helper classes
* `CutSpiralFunc.java` — GLSL vector helper classes
* `CutSqCirFunc.java` — GLSL vector helper classes
* `CutTileIllusionFunc.java` — GLSL vector helper classes
* `CutTriskelFunc.java` — GLSL vector helper classes
* `CutVasarelyFunc.java` — GLSL vector helper classes
* `CutWoodFunc.java` — GLSL vector helper classes
* `CutXFunc.java` — GLSL vector helper classes
* `CutYuebingFunc.java` — GLSL vector helper classes
* `CutZigZagFunc.java` — GLSL vector helper classes
* `Cylinder3DFunc.java` — GLSL vector helper classes
* `Ellipsoid3DFunc.java` — GLSL vector helper classes
* `FresnelFunc.java` — GLSL vector helper classes
* `GlynnLissaFunc.java` — GLSL vector helper classes
* `GlynnSpiroGraf3DFunc.java` — GLSL vector helper classes
* `GlynnSuperShapeFunc.java` — GLSL vector helper classes
* `HexPrism3DFunc.java` — GLSL vector helper classes
* `Octahedron3DFunc.java` — GLSL vector helper classes
* `OctogonPrism3DFunc.java` — GLSL vector helper classes
* `OrientedCappedCone3DFunc.java` — GLSL vector helper classes
* `OrientedCylinder3DFunc.java` — GLSL vector helper classes
* `OrientedRoundCone3DFunc.java` — GLSL vector helper classes
* `PostAexion3dCropFunc.java` — GLSL vector helper classes
* `PostAmazingSurfCropFunc.java` — GLSL vector helper classes
* `PostCoastalbrotCropFunc.java` — GLSL vector helper classes
* `PostCropBoxFunc.java` — GLSL vector helper classes
* `PostCropCrossFunc.java` — GLSL vector helper classes
* `PostCropPolygonFunc.java` — GLSL vector helper classes
* `PostCropRhombusFunc.java` — GLSL vector helper classes
* `PostCropStarsFunc.java` — GLSL vector helper classes
* `PostCropTrapezoidFunc.java` — GLSL vector helper classes
* `PostCropVesicaFunc.java` — GLSL vector helper classes
* `PostCropXFunc.java` — GLSL vector helper classes
* `PostZSymmetryFunc.java` — GLSL vector helper classes
* `PreZSymmetryFunc.java` — GLSL vector helper classes
* `Pyramid3DFunc.java` — GLSL vector helper classes
* `Rhombus3DFunc.java` — GLSL vector helper classes
* `RoundBox3DFunc.java` — GLSL vector helper classes
* `SolidAngle3DFunc.java` — GLSL vector helper classes
* `Torus3DFunc.java` — GLSL vector helper classes
* `TriPrism3DFunc.java` — GLSL vector helper classes
* `TunnelFunc.java` — GLSL vector helper classes
* `ZSymmetryFunc.java` — GLSL vector helper classes

### state between points (62)

* `Blur3DFunc.java` — keeps state between points (gauss_N)
* `BubbleT3DFunc.java` — keeps state between points (c, s)
* `CutHexTruchetFlowFunc.java` — keeps state between points (uvx, uvy)
* `CutKaleidoFunc.java` — array field c (state between points)
* `DCCylinder2Func.java` — array field r (state between points)
* `DCCylinderFunc.java` — array field r (state between points)
* `DCDModulusFunc.java` — keeps state between points (newColor, oldColor)
* `DCGnarlyFunc.java` — keeps state between points (gauss_N)
* `DCKaleidotileFunc.java` — keeps state between points (newColor, oldColor)
* `ExBlurFunc.java` — keeps state between points (_n)
* `FarBlurFunc.java` — keeps state between points (_n)
* `FlameBulbFunc.java` — a Random object (state between points)
* `GingerBreadManFunc.java` — keeps state between points (x0, y0)
* `Hexnix3DFunc.java` — keeps state between points (_bcycle, _fcycle, _rswtch)
* `IconAttractorFunc.java` — array field pdeg (state between points)
* `KaleidoImgFunc.java` — array field inlinedImage (state between points)
* `MacMillanFunc.java` — keeps state between points (x, xa, y)
* `Mandala2Func.java` — array field wobble_dat (state between points)
* `Murl2Func.java` — keeps state between points (_a, _cosa, _im)
* `MurlFunc.java` — keeps state between points (_a, _c, _cosa)
* `PointMirrorSymmetryFunc.java` — array field bufferX (state between points)
* `PostBumpMapWFFunc.java` — array field inlinedImage (state between points)
* `PostHeatFunc.java` — keeps state between points (ap, ar, at)
* `PostPointCropFunc.java` — keeps state between points (post_scrop_c, post_scrop_x, post_scrop_y)
* `PostPointSymmetryWFFunc.java` — array field _sina (state between points)
* `PostSmartCropFunc.java` — keeps state between points (post_scrop_c, post_scrop_x, post_scrop_y)
* `PreBlur3DFunc.java` — keeps state between points (gauss_N)
* `PreBlurFunc.java` — keeps state between points (gauss_N)
* `RadialBlurFunc.java` — keeps state between points (gauss_N)
* `RecurrencePlotFunc.java` — keeps state between points (oldx, y1, y2)
* `ScramblyFunc.java` — array field _mx_rd (state between points)
* `SiercarpetFunc.java` — keeps state between points (d)
* `StarFractalFunc.java` — array field a (state between points)
* `SymBandG1Func.java` — array field transfs (state between points)
* `SymBandG2Func.java` — array field transfs (state between points)
* `SymBandG3Func.java` — array field transfs (state between points)
* `SymBandG4Func.java` — array field transfs (state between points)
* `SymBandG5Func.java` — array field transfs (state between points)
* `SymBandG6Func.java` — array field transfs (state between points)
* `SymBandG7Func.java` — array field transfs (state between points)
* `SymNetG10Func.java` — array field transfs (state between points)
* `SymNetG11Func.java` — array field transfs (state between points)
* `SymNetG12Func.java` — array field transfs (state between points)
* `SymNetG13Func.java` — array field transfs (state between points)
* `SymNetG14Func.java` — array field transfs (state between points)
* `SymNetG15Func.java` — array field transfs (state between points)
* `SymNetG16Func.java` — array field transfs (state between points)
* `SymNetG17Func.java` — array field transfs (state between points)
* `SymNetG1Func.java` — array field transfs (state between points)
* `SymNetG2Func.java` — array field transfs (state between points)
* `SymNetG3Func.java` — array field transfs (state between points)
* `SymNetG4Func.java` — array field transfs (state between points)
* `SymNetG5Func.java` — array field transfs (state between points)
* `SymNetG6Func.java` — array field transfs (state between points)
* `SymNetG7Func.java` — array field transfs (state between points)
* `SymNetG8Func.java` — array field transfs (state between points)
* `SymNetG9Func.java` — array field transfs (state between points)
* `ThreeplyFunc.java` — keeps state between points (x0, y0)
* `Tile_Reverse_Func.java` — keeps state between points (rev)
* `TruchetAEFunc.java` — keeps state between points (x)
* `TruchetFlowFunc.java` — keeps state between points (uvx, uvy)
* `ZBlurFunc.java` — keeps state between points (gauss_N)

### a Random object (47)

* `Cut2eWangTileFunc.java` — field randomize of type Random
* `CutAlienTextFunc.java` — field randomize of type Random
* `CutBTreeFunc.java` — field randomize of type Random
* `CutBasicTruchetFunc.java` — field randomize of type Random
* `CutBooleansFunc.java` — field randomize of type Random
* `CutBricksFunc.java` — field randomize of type Random
* `CutCircleDesignFunc.java` — field randomize of type Random
* `CutFingerPrintFunc.java` — field randomize of type Random
* `CutFractalFunc.java` — field randomize of type Random
* `CutFunFunc.java` — field randomize of type Random
* `CutJigsawFunc.java` — field randomize of type Random
* `CutMagFieldFunc.java` — field randomize of type Random
* `CutMandalaFunc.java` — field randomize of type Random
* `CutPatternFunc.java` — field randomize of type Random
* `CutRandomTileFunc.java` — field randomize of type Random
* `CutSWarpFunc.java` — field randomize of type Random
* `CutSinCosFunc.java` — field randomize of type Random
* `CutSnowflakeFunc.java` — field randomize of type Random
* `CutSpotsFunc.java` — field randomize of type Random
* `CutSqSplitsFunc.java` — field randomize of type Random
* `CutTriScaleTruchetFunc.java` — field randomize of type Random
* `CutTruchetFunc.java` — field randomize of type Random
* `CutWebFunc.java` — field randomize of type Random
* `DC_ButerfliesFunc.java` — field randomize of type Random
* `DeStijlFunc.java` — field cell_rand of type MarsagliaRandomGenerator
* `DrunkenTilesFunc.java` — field random of type Random
* `GreeblesFunc.java` — field cell_rand of type MarsagliaRandomGenerator
* `Grid3DWFFunc.java` — field sizeSpreadRnd of type Random
* `GumowskiMiraFunc.java` — field randomize of type Random
* `HarmonographFunc.java` — field rand of type Random
* `HopalongFunc.java` — field randomize of type Random
* `Julia3DFunc.java` — default of power is not a constant (genRandomPower())
* `Julia3DQFunc.java` — default of power is not a constant (genRandomPower())
* `Julia3DZFunc.java` — default of power is not a constant (genRandomPower())
* `JuliaCFunc.java` — default of re is not a constant (genRandomPower()+0.5)
* `JuliaN3DXFunc.java` — default of power is not a constant (genRandomPower())
* `JuliaQFunc.java` — default of power is not a constant (genRandomPower())
* `KaplanFunc.java` — field randomize of type Random
* `MandelbrotFunc.java` — field randGen of type AbstractRandomGenerator
* `PhoenixJuliaFunc.java` — default of power is not a constant (genRandomPower())
* `PointGrid3DWFFunc.java` — field _shapeRandGen of type AbstractRandomGenerator
* `PointGridWFFunc.java` — field _shapeRandGen of type AbstractRandomGenerator
* `PostJulia3DQFunc.java` — default of power is not a constant (genRandomPower())
* `PostJuliaQFunc.java` — default of power is not a constant (genRandomPower())
* `PreStabilizeFunc.java` — field rand of type Random
* `QuadFunc.java` — field myRandGen of type MarsagliaRandomGenerator
* `VortexFunc.java` — field randomize of type Random

### Complex helper class (22)

* `AcosechFunc.java` — complex-number helper class
* `AcoshFunc.java` — complex-number helper class
* `AcothFunc.java` — complex-number helper class
* `Arcsech2Func.java` — complex-number helper class
* `ArcsinhFunc.java` — complex-number helper class
* `ArctanhFunc.java` — complex-number helper class
* `CombimirrorFunc.java` — complex-number helper class
* `CrownFunc.java` — complex-number helper class
* `ExpMultiFunc.java` — complex-number helper class
* `JacAsnFunc.java` — complex-number helper class
* `JuliaOutsideFunc.java` — complex-number helper class
* `MobiusDragon3DFunc.java` — complex-number helper class
* `PlusRecipFunc.java` — complex-number helper class
* `PostTrigFunc.java` — complex-number helper class
* `PreRecipFunc.java` — complex-number helper class
* `RingTileFunc.java` — complex-number helper class
* `Sqrt_AcosechFunc.java` — complex-number helper class
* `Sqrt_AcoshFunc.java` — complex-number helper class
* `Sqrt_AcothFunc.java` — complex-number helper class
* `Sqrt_AsechFunc.java` — complex-number helper class
* `Sqrt_AsinhFunc.java` — complex-number helper class
* `Sqrt_AtanhFunc.java` — complex-number helper class

### helper methods (10)

* `CactusGlobeFunc.java` — helper calculateCactusPoint() returns double[]
* `Cell3DFunc.java` — helper rotatePoint3D() has a parameter 'double[] coords'
* `CheckerboardWFFunc.java` — Tools helpers
* `DCPerlinFunc.java` — Tools helpers
* `JubiQFunc.java` — Tools helpers
* `JuliaN2Func.java` — Tools helpers
* `JuliaNFunc.java` — Tools helpers
* `JuliaScope3DbFunc.java` — Tools helpers
* `JuliaScopeFunc.java` — Tools helpers
* `JuliaScopePlusFunc.java` — Tools helpers

### does not compile (10)

* `camouflage` — line 33: unexpected ';' in expression
* `chunk` — break outside a loop
* `gamma` — function lgamma() is not available in GLSL
* `hexaplay3D` — unknown name 'scale'
* `jac_elk` — line 17: unsupported member access .lang
* `mandelbox2D` — unknown function radians()
* `meeple` — line 50: expected identifier, found '['
* `post_log_tile2` — unknown name 'spreadx'
* `threepoint_js` — unknown function random()
* `waveblur_wf` — unknown function limitVal()

### GLSL rejected (6)

* `gridout2` — numpy and GLSL differ on 2 of 12 points (max difference 1.56e+00)
* `gridout3D` — numpy and GLSL differ on 2 of 12 points (max difference 1.56e+00)
* `hexes` — numpy and GLSL differ on 12 of 12 points (max difference 5.19e+00)
* `minkQM` — numpy and GLSL differ on 2 of 12 points (max difference 1.84e-01)
* `voronoi_fold` — numpy and GLSL differ on 7 of 12 points (max difference 3.70e-01)
* `worley` — numpy and GLSL differ on 7 of 12 points (max difference 4.38e-01)

### prepost variation (4)

* `PrePostAffineFunc.java` — a pre+post variation (JWildfire's prepost concept)
* `PrePostBlobFunc.java` — a pre+post variation (JWildfire's prepost concept)
* `PrePostCirclizeFunc.java` — a pre+post variation (JWildfire's prepost concept)
* `PrePostMobiusFunc.java` — a pre+post variation (JWildfire's prepost concept)

### code compiled at run time (2)

* `CustomFullVariationWrapperFunc.java` — code compiled at run time
* `GLSLBaseFunc.java` — code compiled at run time

### external shapes (1)

* `SubFlameWFFunc.java` — external shapes (images / fonts / flames)

## Already in the library

arch, asteria, atan, atan2_spirals, auger, bCollide, bMod, bSwirl, bTransform, barycentroid, bent, bent2, bi_linear, bipolar, bipolar2, blade, blob, blocky, blur, blur_circle, blur_linear, blur_pixelize, blur_zoom, boarders, boarders2, bubble, bubble2, butterfly, bwrands, bwraps, bwraps7, cardioid, cell, checks, chladni, circleLinear, circleRand, circleblur, circlesplit, circlize, circlize2, circular, circular2, circus, collideoscope, conic, cos, cosh, coshq, cosine, cosq, cot, coth, cothq, cotq, cpow, cpow2, cpow3, crob, cross, csc, csch, cschq, cscq, cubic3D, cubicLattice_3D, curl, curl3D, curl_sp, curve, cylinder, cylinder2, d_spherical, dc_bubble, dc_carpet, dc_linear, dc_triangle, dc_ztransl, deltaA, diamond, disc, disc3d, eCollide, eJulia, eMod, eMotion, ePush, eRotate, eScale, eSwirl, eclipse, edisc, ennepers, epispiral, erf, erf3D, escher, estiq, ex, exp, exponential, extrude, eyefish, falloff2, fan, fan2, fdisc, fibonacci2, fisheye, flatten, flipcircle, flipy, flux, foci, foci_3D, fourth, funnel, gaussian_blur, gdoffs, glynnia, gridout, handkerchief, heart, helicoid, helix, hemisphere, henon, hex_modulus, ho, hole, holesq, horseshoe, hyperbolic, hypercrop, hypershift, hypershift2, hypertile, hypertile1, hypertile2, hypertile3D, hypertile3D1, hypertile3D2, idisc, inflateZ_1, inflateZ_2, inflateZ_3, inflateZ_4, inflateZ_5, inflateZ_6, julia, kaleidoscope, klein, layered_spiral, lazyTravis, lazyjess, lazysusan, linear, linearT, linearT3D, log, loonie, loonie2, loonie3, loonie_3D, lozi, mcarpet, minkowskope, mobiq, mobius, mobiusN, modulus, ngon, noise, npolar, octagon, ortho, oscilloscope, oscilloscope2, ovoid, ovoid3d, panorama1, pdj, perspective, petal, petal3D, pie, poincare3D, polar, polar2, popcorn, popcorn2, popcorn2_3D, post_bwraps2, post_curl, post_curl3D, post_depth, post_rblur, post_rotate_x, post_rotate_y, post_rotate_z, post_spherical, post_spin_z, power, pre_boarders2, pre_bwraps2, pre_curl, pre_dcztransl, pre_disc, pre_rotate_x, pre_rotate_y, pre_spherical, pre_spin_z, pre_zscale, pre_ztranslate, pressure_wave, projective, pulse, pyramid, rational3, rays, rays2, rays3, rings, rings2, ripple, rippled, rosoni, roundspher, roundspher3D, scry, scry2, scry_3D, sec, secant2, sech, sechq, secq, separation, shift, shredlin, shredrad, sigmoid, sin, sineblur, sinh, sinhq, sinq, sintrange, sinusgrid, sinusoidal, sinusoidal3d, sph3D, spherical, spherical3D, sphericalN, spiral, spiralwing, spligon, split, splitbrdr, splits, splits3D, square, squarize, squirrel, squish, starblur, stripes, stripfit, stwin, superShape3d, super_shape, svf, swirl, swirl3, tan, tancos, tangent, tanh, tanhq, tanq, taurus, tile_hlp, tile_log, trade, truchet, truchet_fill, truchet_hex_crop, truchet_hex_fill, twoface, unpolar, vibration2, voron, waves, waves2, waves22, waves23, waves2_3D, waves2_radial, waves2b, waves3, waves4, waves42, wdisc, wedge_julia, wedge_sph, whorl, xerf, xheart, zcone, zscale, ztranslate
