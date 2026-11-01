#info Phoenix fractal: z(n+1) = z(n)^2 + c.x + c.y z(n-1) (Shigehiro Ushiki), Mandelbrot and Julia modes
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Phoenix
uniform int Iterations; slider[1,150,1000]
uniform bool Julia; checkbox[true]
// The classic Phoenix Julia set uses c = (0.5667, -0.5)
uniform vec2 JuliaC; slider[(-2,-2),(0.5667,-0.5),(2,2)]
uniform float Power; slider[2,2,6]
uniform float Escape; slider[4,100,10000]
uniform float R; slider[0,0.2,1]
uniform float G; slider[0,0.5,1]
uniform float B; slider[0,0.8,1]
uniform float ColorSpeed; slider[0,0.05,0.5]

vec3 color(vec2 c) {
	vec2 cc = Julia ? JuliaC : c;
	vec2 z = Julia ? vec2(c.y, c.x) : vec2(0.0);
	vec2 prev = vec2(0.0);
	int i;
	for (i = 0; i < Iterations; i++) {
		vec2 zn = (Power == 2.0 ? cSqr(z) : cPow(z, Power)) + vec2(cc.x, 0.0) + cc.y * prev;
		prev = z;
		z = zn;
		if (dot(z, z) > Escape) break;
	}
	if (i >= Iterations) return vec3(0.0);
	float ci = (float(i) + 1.0 - log2(0.5 * log2(dot(z, z)))) * ColorSpeed;
	return vec3(0.5 + 0.5 * cos(6.0 * ci + R), 0.5 + 0.5 * cos(6.0 * ci + G), 0.5 + 0.5 * cos(6.0 * ci + B));
}

#preset Default
Center = 0,0
Zoom = 0.55
Iterations = 150
Julia = true
JuliaC = 0.5667,-0.5
Power = 2
Escape = 100
ColorSpeed = 0.05
#endpreset
