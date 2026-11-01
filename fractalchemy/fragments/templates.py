"""Starter fragments and the snippets of the *Insert command* menu.

`NEW_2D` and `NEW_3D` are FragM's *New 2D fragment* / *New 3D fragment* texts verbatim (a Mandelbrot with Iñigo
Quilez's colouring on `Progressive2D.frag`; a sphere-shell distance estimator on `DE-Raytracer.frag`); the other
starters cover the include families (kaleidoscopic IFS, Mandelbox, a 2D Julia with its map, a Shadertoy-style
shader, a feedback system, the fast raytracer). The snippet groups mirror FragM's `createCommandHelpMenu`: host
preprocessor commands, texture options, special uniforms. The user's own templates live in a folder of `.fafrag`
files (`user_templates_dir()`), one per template.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

NEW_2D = '''// New 2D fragment...
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

// Escape time fractals iterate a function for each point
// in the plane, and checks if the sequence generated converges.
//
// Just implement the 'color' function below.
// It is possible to draw Mandelbrots and Julias
// and customize the coloring.
//
// Here is an example of a Mandelbrot:

// The name for the tab for our set of control sliders
#group Mandelbrot

// Number of iterations
uniform int  Iterations; slider[10,200,1000]

uniform float R; slider[0,0,1]
uniform float G; slider[0,0.4,1]
uniform float B; slider[0,0.7,1]

uniform float Power; slider[1,2,10]
uniform float Bailout; slider[0,64,384]

// The color scheme here is based on one from Inigo Quilez's Shader Toy:
// http://www.iquilezles.org/www/articles/mset_smooth/mset_smooth.htm
vec3 IQColor(float i, vec2 z) {
      float co;  // equivalent optimized smooth interation count
      co = 3.1415+i - log(log2(length(z)))/log(Power);
      co = 6.2831*sqrt(co);
      return .5+.5*cos(co+vec3(R,G,B) );
}

vec3 color(vec2 c) {

	vec2 z = vec2(0.0,0.0);

	int i;

	for (i = 0; i < Iterations; i++) {
		// calculate Z
		z = cPow(z, Power) + c;
		// check bailout
		if (dot(z,z) > Bailout) break;
	}

	vec3 rColor=vec3(0.0);

	if(i<Iterations)
		rColor = IQColor(float(i),z);

	return rColor;
}

#preset Default
Center = -0.5,0.0
Zoom = 0.75
#endpreset
'''

NEW_3D = '''// New 3D fragment...
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

float DE(vec3 pos) {
	return abs(length(abs(pos)+vec3(-1.0))-1.2);
}

// minimum number of settings for a 3D preset

#preset Default
FOV = 0.4
Eye = 5.582327,4.881191,-6.709066
Target = -0.44036019,-0.145859154,0.288424741
Up = -0.115126834,0.845289908,0.508173856
#endpreset
'''

KALEIDOSCOPIC_IFS = '''#info Kaleidoscopic IFS (Menger sponge)
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#group Menger
// Knighty's kaleidoscopic IFS: fold, then scale about an offset. A perfect Menger is Scale 3.
uniform float Scale; slider[0.00,3.0,4.00]
uniform vec3 RotVector; slider[(0,0,0),(1,1,1),(1,1,1)]
uniform float RotAngle; slider[0.00,0,180]
uniform vec3 Offset; slider[(0,0,0),(1,1,1),(1,1,1)]
uniform int Iterations;  slider[0,8,100]
uniform int ColorIterations;  slider[0,8,100]

mat3 rot;

void init() {
	rot = rotationMatrix3(normalize(RotVector), RotAngle);
}

float DE(vec3 z)
{
	int n = 0;
	while (n < Iterations) {
		z = rot * z;
		z = abs(z);
		if (z.x < z.y) { z.xy = z.yx; }
		if (z.x < z.z) { z.xz = z.zx; }
		if (z.y < z.z) { z.yz = z.zy; }
		z = Scale * z - Offset * (Scale - 1.0);
		if (z.z < -0.5 * Offset.z * (Scale - 1.0)) z.z += Offset.z * (Scale - 1.0);
		if (n < ColorIterations) orbitTrap = min(orbitTrap, vec4(abs(z), dot(z, z)));
		n++;
	}
	return abs(length(z)) * pow(Scale, float(-n));
}

#preset Default
FOV = 0.4
Eye = -3.72729,-0.0860174,-1.93389
Target = 5.14721,0.118786,2.6706
Up = -0.00348884,0.999311,-0.0369503
Detail = -2.35396
#endpreset
'''

MANDELBOX = '''#info Mandelbox (Tom Lowe's box fold + sphere fold)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#group Mandelbox
uniform float Scale; slider[-5.00,2.0,4.00]
uniform float MinRad2; slider[0,0.25,2.0]
uniform int Iterations;  slider[0,17,300]
uniform int ColorIterations;  slider[0,3,300]
uniform vec3 RotVector; slider[(0,0,0),(1,1,1),(1,1,1)]
uniform float RotAngle; slider[0.00,0,180]

vec4 scale = vec4(Scale, Scale, Scale, abs(Scale)) / MinRad2;
float absScalem1 = abs(Scale - 1.0);
float AbsScaleRaisedTo1mIters = pow(abs(Scale), float(1 - Iterations));

float DE(vec3 pos) {
	vec4 p = vec4(pos, 1), p0 = p;
	mat3 rot = rotationMatrix3(normalize(RotVector), RotAngle);
	for (int i = 0; i < Iterations; i++) {
		p.xyz = rot * p.xyz;
		p.xyz = clamp(p.xyz, -1.0, 1.0) * 2.0 - p.xyz;      // box fold
		float r2 = dot(p.xyz, p.xyz);
		if (i < ColorIterations) orbitTrap = min(orbitTrap, abs(vec4(p.xyz, r2)));
		p *= clamp(max(MinRad2 / r2, MinRad2), 0.0, 1.0);  // sphere fold
		p = p * scale + p0;
	}
	return ((length(p.xyz) - absScalem1) / p.w - AbsScaleRaisedTo1mIters);
}

#preset Default
FOV = 0.4
Eye = 6.0,4.0,-8.0
Target = 0,0,0
Up = 0,1,0
Detail = -2.5
#endpreset
'''

JULIA_2D = '''#info 2D Julia / Mandelbrot with a map (Progressive2DJulia.frag)
#include "Complex.frag"
#include "MathUtils.frag"
#include "Progressive2DJulia.frag"
#group Formula
uniform float Power; slider[1,2,8]

// Implement the iteration: z ← formula(z, c)
vec2 formula(vec2 z, vec2 c) {
	return cPow(z, Power) + c;
}

#preset Default
Center = -0.5,0
Zoom = 0.6
Julia = false
JuliaX = -0.8
JuliaY = 0.156
#endpreset
'''

SHADERTOY = '''#info A Shadertoy-style shader (iResolution, iGlobalTime, gl_FragCoord)
#include "Shadertoy.frag"
#group Shader
uniform float Speed; slider[0,1,5]
uniform vec3 Tint; color[0.3,0.6,1.0]

void main(void) {
	vec2 uv = gl_FragCoord.xy / iResolution.xy;
	vec2 p = uv * 2.0 - 1.0;
	p.x *= iResolution.x / iResolution.y;
	float r = length(p);
	float a = atan(p.y, p.x);
	float v = 0.5 + 0.5 * sin(10.0 * r - iGlobalTime * Speed * 3.0 + 4.0 * a);
	gl_FragColor = vec4(Tint * v, 1.0);
}
'''

FEEDBACK = '''#info Buffer feedback: the previous frame is read back and decayed (needs Animation mode or a subframe max of 0)
#include "2D.frag"
#define DontClearOnChange
#define IterationsBetweenRedraws 2
#define SubframeMax 0
#group Feedback
uniform sampler2D backbuffer;
uniform int subframe;
uniform float Decay; slider[0.8,0.97,1.0]
uniform float Twist; slider[-0.2,0.03,0.2]
uniform vec3 Seed; color[1.0,0.6,0.2]

vec3 color(vec2 z) {
	vec2 uv = (viewCoord + vec2(1.0)) * 0.5;
	// read the previous frame slightly rotated about the centre
	vec2 d = uv - 0.5;
	float c = cos(Twist), s = sin(Twist);
	vec2 r = vec2(c * d.x - s * d.y, s * d.x + c * d.y) * 0.995 + 0.5;
	vec3 prev = texture2D(backbuffer, r).rgb * Decay;
	float ring = smoothstep(0.02, 0.0, abs(length(z) - 0.5 - 0.1 * sin(float(subframe) * 0.05)));
	return max(prev, Seed * ring);
}

#preset Default
Center = 0,0
Zoom = 1.2
AntiAlias = 1
#endpreset
'''

FAST_RAYTRACER = '''#info A distance estimator on the fast raytracer (no shadows / AO: quick to explore)
#include "MathUtils.frag"
#include "Fast-Raytracer.frag"
#group Shape
uniform float Radius; slider[0.1,1.2,3.0]
uniform vec3 Box; slider[(0,0,0),(1,1,1),(3,3,3)]

float DE(vec3 pos) {
	vec3 q = abs(pos) - Box;
	float box = length(max(q, 0.0)) + min(max(q.x, max(q.y, q.z)), 0.0);
	return max(box, -(length(pos) - Radius));   // a box with a sphere carved out
}

#preset Default
FOV = 0.4
Eye = 4.0,3.0,-5.0
Target = 0,0,0
Up = 0,1,0
#endpreset
'''


@dataclass(frozen=True)
class Template:
    """A starter fragment.

    Attributes:
        name: Menu text.
        text: The fragment source.
        kind: `2D` / `3D` (the camera it uses).
        description: One line for the status bar / tooltip.
    """
    name: str
    text: str
    kind: str
    description: str = ""


PRIMITIVES = '''// Primitives playground: compose the distance primitives of Primitives.frag
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Shapes
uniform float Smoothness; slider[0.001,0.2,1]
uniform vec3 SphereOffset; slider[(-3,-3,-3),(0.9,0.5,0),(3,3,3)]
uniform float Twist; slider[-3,0,3]

// Primitives: sdSphere, sdBox, sdRoundBox, sdBoxFrame, sdTorus(p, R, r), sdCapsule, sdCylinder(p, r, h), sdCone,
// sdOctahedron, sdIcosahedron, sdDodecahedron, fGDF, sdGyroid, sdHexPrism ... (see Primitives.frag)
// Operators: opUnion, opSubtract, opIntersect, opSmoothUnion, opOnion, opRound, opRepeat, opRepeatPolar, opTwist, opBend
// Folds:     foldBox, foldSphere, foldMenger, foldSierpinski, foldKaleido
float DE(vec3 p) {
	p = opTwist(p, Twist);
	float box = sdRoundBox(p, vec3(0.8, 0.5, 0.8), 0.05);
	float ball = sdSphere(p - SphereOffset, 0.6);
	float ring = sdTorus(p - vec3(0.0, 0.7, 0.0), 1.1, 0.08);
	return opUnion(opSmoothUnion(box, ball, Smoothness), ring);
}

#preset Default
FOV = 0.4
Eye = 2.6,2.2,-3.6
Target = 0,0.2,0
Up = 0,1,0
Detail = -2.8
DetailAO = -1.2
BaseColor = 0.85,0.8,0.7
OrbitStrength = 0
BackgroundColor = 0.35,0.4,0.5
GradientBackground = 0.3
#endpreset
'''

BUILTIN_TEMPLATES = (
    Template("New 2D fragment", NEW_2D, "2D", "A Mandelbrot on Progressive2D.frag with Iñigo Quilez's colouring (FragM's New 2D)"),
    Template("New 3D fragment", NEW_3D, "3D", "A sphere-shell distance estimator on DE-Raytracer.frag (FragM's New 3D)"),
    Template("Kaleidoscopic IFS (Menger)", KALEIDOSCOPIC_IFS, "3D", "Knighty's fold-and-scale IFS on DE-Raytracer.frag"),
    Template("Mandelbox", MANDELBOX, "3D", "Tom Lowe's box fold + sphere fold on DE-Raytracer.frag"),
    Template("2D Julia / Mandelbrot with map", JULIA_2D, "2D", "Progressive2DJulia.frag: implement formula(z, c)"),
    Template("Shadertoy-style shader", SHADERTOY, "2D", "iResolution / iGlobalTime / gl_FragCoord, no camera"),
    Template("Buffer feedback", FEEDBACK, "2D", "Reads the previous frame back: a feedback system with DontClearOnChange"),
    Template("Fast raytracer", FAST_RAYTRACER, "3D", "A DE on Fast-Raytracer.frag (quick, no shadows or AO)"),
    Template("Primitives playground", PRIMITIVES, "3D", "Boxes, spheres, tori and the operators of Primitives.frag on DE-Raytracer.frag"),
)

# FragM's Edit ▸ Insert Command menu, group by group
SNIPPETS: dict[str, tuple[str, ...]] = {
    "Host preprocessor commands": (
        "#info sometext", '#include "some.frag"', "#camera 2D", "#camera 3D", "#group parameter_group_name", "#preset preset_name",
        "#endpreset", "#define DontClearOnChange", "#define IterationsBetweenRedraws 10", "#define SubframeMax 20",
        "#define providesColor", "#define providesBackground", "#define providesNormal", "#define providesInit",
    ),
    "Special uniforms": (
        "uniform float time;", "uniform int subframe;", "uniform int i; slider[0,1,2]", "uniform float f; slider[0,1,2]",
        "uniform vec2 pixelSize;", "uniform vec2 v; slider[(0,0),(1,1),(1,1)]", "uniform vec3 v; slider[(0,0,0),(1,1,1),(1,1,1)]",
        "uniform vec4 v; slider[(0,0,0,0),(1,1,1,1),(1,1,1,1)]", "uniform double f; slider[0,1,2]", "uniform dvec2 v; slider[(0,0),(1,1),(1,1)]",
        "uniform dvec3 v; slider[(0,0,0),(1,1,1),(1,1,1)]", "uniform dvec4 v; slider[(0,0,0,0),(1,1,1,1),(1,1,1,1)]",
        "uniform bool b; checkbox[true]", "uniform sampler2D tex; file[tex.jpg]", "uniform samplerCube cubetex; file[cubetex.jpg]",
        "uniform vec3 color; color[0.0,0.0,0.0]", "uniform vec4 color; color[0.0,1.0,0.0,0.0,0.0,0.0]",
        "uniform bool DepthToAlpha; checkbox[true]", "uniform bool AutoFocus; checkbox[true]",
    ),
    "Primitives (Primitives.frag)": (
        '#include "Primitives.frag"', "sdSphere(p, 1.0)", "sdBox(p, vec3(1.0))", "sdRoundBox(p, vec3(1.0), 0.1)", "sdBoxFrame(p, vec3(1.0), 0.05)",
        "sdTorus(p, 1.0, 0.25)", "sdCapsule(p, 0.5, 0.2)", "sdCapsuleLine(p, vec3(0.0), vec3(1.0), 0.1)", "sdCylinder(p, 0.5, 1.0)",
        "sdCone(p, 0.5, 1.0)", "sdCappedCone(p, 0.5, 0.5, 0.2)", "sdHexPrism(p, 0.5, 0.2)", "sdOctahedron(p, 1.0)", "sdIcosahedron(p, 1.0)",
        "sdDodecahedron(p, 1.0)", "fGDF(p, 1.0, 16.0, 3, 18)", "sdEllipsoid(p, vec3(1.0, 0.5, 0.7))", "sdPyramid(p, 1.0)",
        "sdGyroid(p, 7.0, 0.05, 0.0)", "sdPlane(p, vec3(0.0, 1.0, 0.0), 1.0)",
    ),
    "Operators and folds (Primitives.frag)": (
        "opUnion(a, b)", "opSubtract(a, b)", "opIntersect(a, b)", "opSmoothUnion(a, b, 0.2)", "opSmoothSubtract(a, b, 0.2)",
        "opSmoothIntersect(a, b, 0.2)", "opOnion(d, 0.05)", "opRound(d, 0.1)", "p = opRepeat(p, vec3(2.0));", "p = opRepeatLimited(p, 2.0, vec3(2.0));",
        "p.xz = opRepeatPolar(p.xz, 8.0);", "p = opTwist(p, 1.0);", "p = opBend(p, 0.5);", "p = opElongate(p, vec3(0.5, 0.0, 0.0));",
        "p = foldBox(p, 1.0);", "p = foldSphere(p, dr, 0.25, 1.0);", "p = foldMenger(p);", "p = foldSierpinski(p);",
        "p.xz = foldKaleido(p.xz, 6.0);", "p *= rot3(vec3(0.0, 1.0, 0.0), 0.5);",
    ),
    "2D texture options": (
        "#TexParameter textureName GL_TEXTURE_MAG_FILTER GL_NEAREST", "#TexParameter textureName GL_TEXTURE_WRAP_S GL_CLAMP",
        "#TexParameter textureName GL_TEXTURE_WRAP_T GL_CLAMP", "#TexParameter textureName GL_TEXTURE_MAX_LEVEL 1000",
        "#TexParameter textureName GL_TEXTURE_WRAP_S GL_REPEAT", "#TexParameter textureName GL_TEXTURE_WRAP_T GL_REPEAT",
        "#TexParameter textureName GL_TEXTURE_MAG_FILTER GL_LINEAR", "#TexParameter textureName GL_TEXTURE_MIN_FILTER GL_LINEAR_MIPMAP_LINEAR",
        "#TexParameter textureName GL_TEXTURE_MIN_FILTER GL_LINEAR_MIPMAP_NEAREST", "#TexParameter textureName GL_TEXTURE_MIN_FILTER GL_NEAREST_MIPMAP_LINEAR",
        "#TexParameter textureName GL_TEXTURE_MIN_FILTER GL_NEAREST_MIPMAP_NEAREST", "#TexParameter textureName GL_TEXTURE_MAX_ANISOTROPY float(>1.0 <16.0)",
    ),
}


def template_named(name: str) -> Template | None:
    for template in BUILTIN_TEMPLATES:
        if template.name == name:
            return template
    return None


def user_templates_dir() -> Path:
    """Where *Save as template* writes (`<app data>/fragments/templates`)."""
    from ..formulas.loader import user_formula_dir
    return user_formula_dir().parent / "fragments" / "templates"


def user_templates(folder: Path | None = None) -> list[Template]:
    """The user's templates: every `.fafrag` / `.frag` in the templates folder, named after the file."""
    folder = folder or user_templates_dir()
    if not folder.is_dir():
        return []
    out = []
    for path in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
        if path.suffix.lower() in (".fafrag", ".frag") and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            kind = "3D" if "#camera 3D" in text or "Raytracer" in text else "2D"
            out.append(Template(path.stem, text, kind, str(path)))
    return out


def save_user_template(name: str, text: str, folder: Path | None = None) -> Path:
    """Write `text` as the user template `name`; returns the file."""
    folder = folder or user_templates_dir()
    folder.mkdir(parents=True, exist_ok=True)
    safe = re.sub(r'[\\/:*?"<>|]+', "_", name).strip() or "template"
    path = folder / f"{safe}.fafrag"
    path.write_text(text, encoding="utf-8")
    return path


__all__ = ["NEW_2D", "NEW_3D", "PRIMITIVES", "Template", "BUILTIN_TEMPLATES", "SNIPPETS", "template_named", "user_templates", "user_templates_dir",
           "save_user_template"]
