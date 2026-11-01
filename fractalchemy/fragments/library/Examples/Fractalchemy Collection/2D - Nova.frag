#info Nova fractal: a relaxed Newton iteration z - R (z^p - 1) / (p z^(p-1)) + c, coloured by the root it converges to
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Nova
uniform int Iterations; slider[1,60,500]
uniform float Power; slider[1,3,8]
// Relaxation (1 = plain Newton)
uniform float Relax; slider[0.1,1,2]
uniform bool Julia; checkbox[false]
uniform vec2 JuliaC; slider[(-2,-2),(0.35,0.1),(2,2)]
// Start value (Nova is usually started at 1)
uniform vec2 Start; slider[(-2,-2),(1,0),(2,2)]
uniform float Bailout; slider[0.000001,0.00001,0.01]
// Colour phases
uniform float R; slider[0,0,1]
uniform float G; slider[0,0.4,1]
uniform float B; slider[0,0.7,1]
uniform float Spread; slider[0,0.1,1]

vec3 color(vec2 c) {
	vec2 z = Julia ? c : Start;
	vec2 cc = Julia ? JuliaC : c;
	float p = Power;
	int i;
	for (i = 0; i < Iterations; i++) {
		vec2 zp1 = cPow(z, p - 1.0);
		vec2 zp = cMul(zp1, z);
		vec2 step = cDiv(zp - vec2(1.0, 0.0), p * zp1);
		vec2 zn = z - Relax * step + cc;
		if (dot(zn - z, zn - z) < Bailout) { z = zn; break; }
		z = zn;
	}
	if (i >= Iterations) return vec3(0.0);
	float root = atan(z.y, z.x) / 6.2831853;
	float ci = root + Spread * float(i);
	return vec3(0.5 + 0.5 * cos(6.0 * ci + R), 0.5 + 0.5 * cos(6.0 * ci + G), 0.5 + 0.5 * cos(6.0 * ci + B));
}

#preset Default
Center = -0.3,0
Zoom = 0.6
Iterations = 60
Power = 3
Relax = 1
Julia = false
JuliaC = 0.35,0.1
Start = 1,0
Bailout = 0.00001
R = 0
G = 0.4
B = 0.7
Spread = 0.1
#endpreset
