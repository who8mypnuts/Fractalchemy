#info Magnet fractal type I: z = ((z^2 + c - 1) / (2 z + c - 2))^2, with convergence to 1 coloured separately
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Magnet
uniform int Iterations; slider[1,100,1000]
uniform bool Julia; checkbox[false]
uniform vec2 JuliaC; slider[(-3,-3),(1.2,0.4),(3,3)]
uniform float Escape; slider[10,100,10000]
uniform float Converge; slider[0.000001,0.0001,0.1]
uniform float R; slider[0,0.1,1]
uniform float G; slider[0,0.5,1]
uniform float B; slider[0,0.9,1]
uniform vec3 ConvergedColor; color[0.1,0.1,0.15]

vec3 color(vec2 c) {
	vec2 z = Julia ? c : vec2(0.0);
	vec2 cc = Julia ? JuliaC : c;
	int i;
	for (i = 0; i < Iterations; i++) {
		vec2 num = cSqr(z) + cc - vec2(1.0, 0.0);
		vec2 den = 2.0 * z + cc - vec2(2.0, 0.0);
		z = cSqr(cDiv(num, den));
		if (dot(z, z) > Escape) break;
		vec2 d = z - vec2(1.0, 0.0);
		if (dot(d, d) < Converge) return ConvergedColor * (1.0 - 0.5 * float(i) / float(Iterations));
	}
	if (i >= Iterations) return vec3(0.0);
	float ci = float(i) + 1.0 - log2(0.5 * log2(dot(z, z)));
	ci *= 0.05;
	return vec3(0.5 + 0.5 * cos(6.0 * ci + R), 0.5 + 0.5 * cos(6.0 * ci + G), 0.5 + 0.5 * cos(6.0 * ci + B));
}

#preset Default
Center = 1.3,0
Zoom = 0.35
Iterations = 100
Julia = false
JuliaC = 1.2,0.4
Escape = 100
Converge = 0.0001
#endpreset
