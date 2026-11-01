#info A Kleinian limit set in the Maskit slice (Jos Leys and Knighty's construction in two dimensions): translate, fold, invert; the distance to the set is coloured
#include "MathUtils.frag"
#include "Complex.frag"
#include "Progressive2D.frag"

#group Kleinian
uniform int Iterations; slider[1,60,300]
// The Maskit parameter: 2 is the gasket, smaller values open the set up
uniform float KleinR; slider[1.0,1.95,2.5]
uniform float KleinI; slider[-1,0.05,1]
uniform float Separation; slider[0,0.25,1]
uniform float Thickness; slider[0,0.01,0.2]
uniform vec3 SetColor; color[1.0,0.9,0.7]
uniform vec3 Far; color[0.1,0.05,0.2]
uniform float ColorSpeed; slider[0,3,20]

vec3 color(vec2 z) {
	float a = KleinR, b = KleinI;
	float f = sign(b) * Separation;
	float DF = 1.0;
	vec2 lz = z + vec2(1.0), llz = z + vec2(-1.0);
	for (int i = 0; i < Iterations; i++) {
		z.x += b / a * z.y;
		z.x = mod(z.x + 1.0, 2.0) - 1.0;
		z.x -= b / a * z.y;
		if (z.y >= a * 0.5 + f * (2.0 * a - 1.95) / 4.0 * sign(z.x + b * 0.5) * (1.0 - exp(-(7.2 - (1.95 - a) * 15.0) * abs(z.x + b * 0.5)))) {
			z = vec2(-b, a) - z;
		}
		float iR = 1.0 / dot(z, z);
		z *= -iR;
		z.x = -b - z.x;
		z.y = a + z.y;
		DF *= max(1.0, iR);
		if (dot(z - llz, z - llz) < 1e-5) break;
		llz = lz; lz = z;
	}
	float d = min(z.y, a - z.y) / max(DF, 2.0);
	if (d < Thickness) return SetColor;
	return mix(SetColor, Far, clamp(d * ColorSpeed, 0.0, 1.0));
}

#preset Default
Center = 0,0.95
Zoom = 0.45
Iterations = 60
KleinR = 1.95
KleinI = 0.05
Separation = 0.25
Thickness = 0.01
ColorSpeed = 3
#endpreset
