#info Lambdabulb: z = lambda * z * (1 - z^(n-1)) in triplex arithmetic (the lambda Mandelbrot lifted to 3D)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Triplex.frag"

#group Lambdabulb
uniform int Iterations; slider[1,12,40]
uniform float Power; slider[2,3,8]
uniform vec3 Lambda; slider[(-3,-3,-3),(1.3,0.2,0.1),(3,3,3)]
uniform float Bailout; slider[2,16,64]
// Numerical derivative step (the DE uses a delta estimate)
uniform float Delta; slider[0.00001,0.0001,0.01]

vec3 iterate(vec3 z) {
	for (int i = 0; i < Iterations; i++) {
		z = tMul(Lambda, tMul(z, vec3(1.0, 0.0, 0.0) - tPow(z, Power - 1.0)));
		if (length(z) > Bailout) break;
	}
	return z;
}

float DE(vec3 p) {
	float r = length(iterate(p));
	float rx = length(iterate(p + vec3(Delta, 0.0, 0.0)));
	float ry = length(iterate(p + vec3(0.0, Delta, 0.0)));
	float rz = length(iterate(p + vec3(0.0, 0.0, Delta)));
	float dr = length(vec3(rx - r, ry - r, rz - r)) / Delta;
	return 0.5 * log(r) * r / max(dr, 1e-6);
}

#preset Default
FOV = 0.5
Eye = 2.2,1.6,-2.8
Target = 0,0,0
Up = 0,1,0
Detail = -3.0
DetailAO = -1.4
FudgeFactor = 0.6
BaseColor = 0.85,0.85,0.8
OrbitStrength = 0.7
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
