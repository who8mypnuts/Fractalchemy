#info Kleinian limit set by Jos Leys and Knighty (tdhooper's variant). From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Kleinian
uniform int Iterations; slider[1,80,200]
uniform float KleinR; slider[1.0,1.89,2.5]
uniform float KleinI; slider[-1,0.1,1]
uniform vec2 BoxSize; slider[(-2,-2),(-0.8089,0.68),(2,2)]
uniform float Separation; slider[0,0.45,1]
uniform float Thickness; slider[0,0.3,1]

vec2 wrap(vec2 x, vec2 a, vec2 s) {
	x -= s;
	return (x - a * floor(x / a)) + s;
}

void TransA(inout vec3 z, inout float DF, float a, float b) {
	float iR = 1.0 / dot(z, z);
	z *= -iR;
	z.x = -b - z.x;
	z.y = a + z.y;
	DF *= iR;
}

float DE(vec3 z) {
	float a = KleinR, b = KleinI;
	vec2 box_size = BoxSize;
	vec3 lz = z + vec3(1.0), llz = z + vec3(-1.0);
	float DE = 1e12, DF = 1.0;
	float f = sign(b) * Separation;
	for (int i = 0; i < Iterations; i++) {
		z.x += b / a * z.y;
		z.xz = wrap(z.xz, box_size * 2.0, -box_size);
		z.x -= b / a * z.y;
		if (z.y >= a * 0.5 + f * (2.0 * a - 1.95) / 4.0 * sign(z.x + b * 0.5) * (1.0 - exp(-(7.2 - (1.95 - a) * 15.0) * abs(z.x + b * 0.5)))) {
			z = vec3(-b, a, 0.0) - z;
		}
		TransA(z, DF, a, b);
		if (dot(z - llz, z - llz) < 1e-5) break;
		llz = lz; lz = z;
	}
	float y = min(z.y, a - z.y);
	DE = min(DE, min(y, Thickness) / max(DF, 2.0));
	return DE;
}

#preset Default
FOV = 0.5
Eye = 0.1,1.2,-3.0
Target = 0,0.9,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
BaseColor = 0.9,0.85,0.8
OrbitStrength = 0.3
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
