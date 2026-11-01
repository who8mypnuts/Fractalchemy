"""GLSL vocabulary for the highlighter and the completer: keywords, types, built-in functions and variables.

Distilled from FragM's `glsl.xml` (the renderingpipeline.com GLSL 4.4 highlighter) and the GLSL 1.10–4.60
specifications; the fragment-language words (directives and annotations) are Fragmentarium's own.
"""

from __future__ import annotations

KEYWORDS = frozenset("""
attribute const uniform varying buffer shared coherent volatile restrict readonly writeonly layout centroid flat smooth
noperspective patch sample break continue do for while switch case default if else subroutine in out inout invariant precise
discard return lowp mediump highp precision struct true false
""".split())

TYPES = frozenset("""
void bool int uint float double vec2 vec3 vec4 dvec2 dvec3 dvec4 bvec2 bvec3 bvec4 ivec2 ivec3 ivec4 uvec2 uvec3 uvec4
mat2 mat3 mat4 mat2x2 mat2x3 mat2x4 mat3x2 mat3x3 mat3x4 mat4x2 mat4x3 mat4x4
dmat2 dmat3 dmat4 dmat2x2 dmat2x3 dmat2x4 dmat3x2 dmat3x3 dmat3x4 dmat4x2 dmat4x3 dmat4x4
sampler1D sampler2D sampler3D samplerCube sampler1DShadow sampler2DShadow samplerCubeShadow sampler1DArray sampler2DArray
sampler1DArrayShadow sampler2DArrayShadow isampler1D isampler2D isampler3D isamplerCube isampler1DArray isampler2DArray
usampler1D usampler2D usampler3D usamplerCube usampler1DArray usampler2DArray sampler2DRect sampler2DRectShadow isampler2DRect
usampler2DRect samplerBuffer isamplerBuffer usamplerBuffer sampler2DMS isampler2DMS usampler2DMS sampler2DMSArray
isampler2DMSArray usampler2DMSArray samplerCubeArray samplerCubeArrayShadow isamplerCubeArray usamplerCubeArray image2D
atomic_uint
""".split())

FUNCTIONS = frozenset("""
radians degrees sin cos tan asin acos atan sinh cosh tanh asinh acosh atanh pow exp log exp2 log2 sqrt inversesqrt abs sign
floor trunc round roundEven ceil fract mod modf min max clamp mix step smoothstep isnan isinf floatBitsToInt floatBitsToUint
intBitsToFloat uintBitsToFloat fma frexp ldexp packUnorm2x16 packSnorm2x16 packUnorm4x8 packSnorm4x8 unpackUnorm2x16
unpackSnorm2x16 unpackUnorm4x8 unpackSnorm4x8 packDouble2x32 unpackDouble2x32 packHalf2x16 unpackHalf2x16 length distance dot
cross normalize ftransform faceforward reflect refract matrixCompMult outerProduct transpose determinant inverse lessThan
lessThanEqual greaterThan greaterThanEqual equal notEqual any all not uaddCarry usubBorrow umulExtended imulExtended
bitfieldExtract bitfieldInsert bitfieldReverse bitCount findLSB findMSB textureSize textureQueryLod textureQueryLevels
texture textureProj textureLod textureOffset texelFetch texelFetchOffset textureProjOffset textureLodOffset textureProjLod
textureProjLodOffset textureGrad textureGradOffset textureProjGrad textureProjGradOffset textureGather textureGatherOffset
textureGatherOffsets texture1D texture1DProj texture1DLod texture1DProjLod texture2D texture2DProj texture2DLod
texture2DProjLod texture3D texture3DProj texture3DLod texture3DProjLod textureCube textureCubeLod shadow1D shadow2D
shadow1DProj shadow2DProj shadow1DLod shadow2DLod shadow1DProjLod shadow2DProjLod dFdx dFdy dFdxFine dFdyFine dFdxCoarse
dFdyCoarse fwidth fwidthFine fwidthCoarse interpolateAtCentroid interpolateAtSample interpolateAtOffset noise1 noise2 noise3
noise4 EmitStreamVertex EndStreamPrimitive EmitVertex EndPrimitive barrier memoryBarrier
""".split())

BUILTIN_VARIABLES = frozenset("""
gl_FragCoord gl_FrontFacing gl_PointCoord gl_FragColor gl_FragData gl_FragDepth gl_Position gl_PointSize gl_ClipDistance
gl_Vertex gl_Normal gl_Color gl_MultiTexCoord0 gl_ProjectionMatrix gl_ModelViewMatrix gl_ModelViewProjectionMatrix
gl_NormalMatrix gl_TexCoord gl_VertexID gl_InstanceID gl_PrimitiveID gl_SampleID gl_SamplePosition gl_MaxTextureUnits
""".split())

# Fragmentarium's own words: the host directives and the annotation keywords
DIRECTIVES = ("#include", "#buffershader", "#preset", "#endpreset", "#replace", "#camera", "#buffer", "#group", "#vertex",
              "#endvertex", "#info", "#donotrun", "#TexParameter", "#define", "#ifdef", "#ifndef", "#if", "#else", "#elif", "#endif",
              "#undef", "#version", "#extension", "#pragma", "#line", "#error")
ANNOTATIONS = ("slider", "color", "checkbox", "menu", "file", "Locked", "NotLocked", "NotLockable", "AlwaysLocked", "Logarithmic")
SPECIAL_UNIFORMS = ("pixelSize", "subframe", "time", "backbuffer", "frontbuffer", "projectionMatrix", "globalPixelSize")
FRAGMENTARIUM_DEFINES = ("providesInit", "providesColor", "providesBackground", "providesNormal", "providesInside", "providesFiltering",
                         "DontClearOnChange", "IterationsBetweenRedraws", "SubframeMax", "linearGamma")

# One-line documentation for the completer: name → (signature, what it does). `genType` stands for float / vecN.
DOCS: dict[str, tuple[str, str]] = {
    "sin": ("genType sin(genType angle)", "Sine of an angle in radians."),
    "cos": ("genType cos(genType angle)", "Cosine of an angle in radians."),
    "tan": ("genType tan(genType angle)", "Tangent of an angle in radians."),
    "asin": ("genType asin(genType x)", "Arc sine, in [-π/2, π/2]."),
    "acos": ("genType acos(genType x)", "Arc cosine, in [0, π]."),
    "atan": ("genType atan(genType y, genType x) / atan(genType y_over_x)", "Arc tangent; the two-argument form keeps the quadrant."),
    "pow": ("genType pow(genType x, genType y)", "x raised to the power y (undefined for x < 0)."),
    "exp": ("genType exp(genType x)", "e to the power x."),
    "log": ("genType log(genType x)", "Natural logarithm."),
    "exp2": ("genType exp2(genType x)", "2 to the power x."),
    "log2": ("genType log2(genType x)", "Base-2 logarithm."),
    "sqrt": ("genType sqrt(genType x)", "Square root."),
    "inversesqrt": ("genType inversesqrt(genType x)", "1 / sqrt(x)."),
    "abs": ("genType abs(genType x)", "Absolute value."),
    "sign": ("genType sign(genType x)", "-1, 0 or 1 by the sign of x."),
    "floor": ("genType floor(genType x)", "Largest integer ≤ x."),
    "ceil": ("genType ceil(genType x)", "Smallest integer ≥ x."),
    "fract": ("genType fract(genType x)", "x - floor(x)."),
    "mod": ("genType mod(genType x, genType y)", "x - y · floor(x / y)."),
    "min": ("genType min(genType x, genType y)", "The smaller value, component-wise."),
    "max": ("genType max(genType x, genType y)", "The larger value, component-wise."),
    "clamp": ("genType clamp(genType x, genType lo, genType hi)", "min(max(x, lo), hi)."),
    "mix": ("genType mix(genType a, genType b, genType t)", "Linear blend a · (1 - t) + b · t."),
    "step": ("genType step(genType edge, genType x)", "0 where x < edge, else 1."),
    "smoothstep": ("genType smoothstep(genType e0, genType e1, genType x)", "Hermite interpolation between 0 and 1 over [e0, e1]."),
    "length": ("float length(genType v)", "Euclidean length of a vector."),
    "distance": ("float distance(genType a, genType b)", "length(a - b)."),
    "dot": ("float dot(genType a, genType b)", "Dot product."),
    "cross": ("vec3 cross(vec3 a, vec3 b)", "Cross product."),
    "normalize": ("genType normalize(genType v)", "v scaled to unit length."),
    "reflect": ("genType reflect(genType I, genType N)", "I reflected about the normal N."),
    "refract": ("genType refract(genType I, genType N, float eta)", "Refraction of I through the surface N with index ratio eta."),
    "faceforward": ("genType faceforward(genType N, genType I, genType Nref)", "N or -N so that it faces against I."),
    "texture": ("vec4 texture(sampler s, vec2 uv)", "Sample a texture (GLSL 1.30+; texture2D is mapped onto it)."),
    "texture2D": ("vec4 texture2D(sampler2D s, vec2 uv)", "Sample a 2D texture (legacy name; the compatibility layer provides it)."),
    "textureCube": ("vec4 textureCube(samplerCube s, vec3 dir)", "Sample a cube map (legacy name)."),
    "texelFetch": ("vec4 texelFetch(sampler s, ivec2 pixel, int lod)", "Read one texel by integer coordinates."),
    "textureSize": ("ivec2 textureSize(sampler s, int lod)", "The texture's size in texels."),
    "dFdx": ("genType dFdx(genType p)", "Screen-space derivative in x."),
    "dFdy": ("genType dFdy(genType p)", "Screen-space derivative in y."),
    "fwidth": ("genType fwidth(genType p)", "abs(dFdx(p)) + abs(dFdy(p))."),
    "transpose": ("mat transpose(mat m)", "Transposed matrix."),
    "inverse": ("mat inverse(mat m)", "Inverse matrix (GLSL 1.40+)."),
    "determinant": ("float determinant(mat m)", "Determinant."),
    "matrixCompMult": ("mat matrixCompMult(mat a, mat b)", "Component-wise matrix product."),
    "isnan": ("bvec isnan(genType x)", "True where x is NaN."),
    "isinf": ("bvec isinf(genType x)", "True where x is infinite."),
    "any": ("bool any(bvec v)", "True when any component is true."),
    "all": ("bool all(bvec v)", "True when every component is true."),
    "lessThan": ("bvec lessThan(vec a, vec b)", "Component-wise a < b."),
    "greaterThan": ("bvec greaterThan(vec a, vec b)", "Component-wise a > b."),
    "equal": ("bvec equal(vec a, vec b)", "Component-wise a == b."),
    "radians": ("genType radians(genType degrees)", "Degrees to radians."),
    "degrees": ("genType degrees(genType radians)", "Radians to degrees."),
    "round": ("genType round(genType x)", "Nearest integer."),
    "trunc": ("genType trunc(genType x)", "Integer part, towards zero."),
    "modf": ("genType modf(genType x, out genType i)", "Fractional part, the integer part in i."),
    # the host's words
    "#include": ('#include "file.frag"', "Insert another fragment (searched beside this file, then the include paths, then the bundled Include folder)."),
    "#group": ("#group Name", "The tab the following uniforms' widgets go on."),
    "#preset": ("#preset Name … #endpreset", "A block of `Parameter = value` lines; `Default` is applied after a build; KeyFrame.NNN presets make the camera path."),
    "#endpreset": ("#endpreset", "Ends a preset block."),
    "#camera": ("#camera 2D | 3D", "Which camera the viewport drives (sets the Camera group's uniforms)."),
    "#buffer": ("#buffer RGBA8 | RGBA16 | RGBA16F | RGBA32F", "The accumulation buffer's texture format."),
    "#buffershader": ('#buffershader "BufferShader.frag"', "The display pass (tone mapping) over the accumulation."),
    "#vertex": ("#vertex … #endvertex", "Lines between the two go into the vertex shader."),
    "#replace": ('#replace "from" "to"', "Textual substitution applied to the lines that follow."),
    "#info": ("#info text", "A line shown in the log after a build."),
    "#donotrun": ("#donotrun", "This file is an include, not a runnable fragment."),
    "#TexParameter": ("#TexParameter sampler GL_TEXTURE_MIN_FILTER GL_LINEAR", "A texture parameter for a sampler (filters, wrapping, anisotropy)."),
    "slider": ("uniform float X; slider[min,default,max]", "A slider widget (vec2/3/4 take (a,b,c) triples; `Locked` / `NotLockable` after it)."),
    "color": ("uniform vec3 C; color[r,g,b]  or  uniform vec4 C; color[min,default,max,r,g,b]", "A colour picker (vec4: a slider and a colour)."),
    "checkbox": ("uniform bool B; checkbox[true]", "A check box."),
    "menu": ('uniform int M; menu[0,"Name A","Name B"]', "A combo box of named integer values."),
    "file": ("uniform sampler2D T; file[name.png]", "A texture file (always locked)."),
    "Locked": ("slider[…] Locked", "The parameter starts locked (compiled in as a constant)."),
    "NotLockable": ("slider[…] NotLockable", "The parameter can never be locked (the camera's, for instance)."),
    "Logarithmic": ("slider[…] Logarithmic", "The slider moves logarithmically."),
    "pixelSize": ("uniform vec2 pixelSize", "1 / buffer size — the size of one pixel in clip space."),
    "subframe": ("uniform int subframe", "The accumulation subframe counter (0 for the first)."),
    "time": ("uniform float time", "Seconds on the animation clock."),
    "backbuffer": ("uniform sampler2D backbuffer", "The previous subframe's accumulation."),
    "frontbuffer": ("uniform sampler2D frontbuffer", "The accumulation, for the buffer shader."),
    "projectionMatrix": ("uniform mat4 projectionMatrix", "The tile transform of a hi-res render (identity in the viewport)."),
    "providesInit": ("#define providesInit", "The fragment defines `void init()` (called before each pixel by the raytracers)."),
    "providesColor": ("#define providesColor", "The fragment defines `vec3 baseColor(vec3 point, vec3 normal)`."),
    "providesBackground": ("#define providesBackground", "The fragment defines `vec3 backgroundColor(vec3 dir)`."),
    "providesNormal": ("#define providesNormal", "The fragment defines `vec3 normal(vec3 p, float eps)`."),
    "DontClearOnChange": ("#define DontClearOnChange", "Parameter changes do not restart the accumulation (feedback fragments)."),
    "IterationsBetweenRedraws": ("#define IterationsBetweenRedraws N", "Draw N subframes between displayed images."),
    "SubframeMax": ("#define SubframeMax N", "The default *Subframe max* for this fragment."),
}

__all__ = ["KEYWORDS", "TYPES", "FUNCTIONS", "BUILTIN_VARIABLES", "DIRECTIVES", "ANNOTATIONS", "SPECIAL_UNIFORMS", "FRAGMENTARIUM_DEFINES", "DOCS"]
