#info A Kleinian limit set in three dimensions — Jos Leys and Knighty's construction: translate along the group's lattice, fold across the Maskit line, invert in the unit sphere, repeat; the points that never settle form the limit set. KleinR near 2 gives the Apollonian gasket; below it the set opens into a tower of holes. Coloured by the nesting depth.
#define providesColor
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Kleinian
uniform int Iterations; slider[1,80,300]
// The Maskit parameter: 2 gives the gasket; smaller opens the set up
uniform float KleinR; slider[1.0,1.95,2.5]
uniform float KleinI; slider[-1,0.05,1]
// The lattice the set repeats on, in x and z
uniform vec2 BoxSize; slider[(0.2,0.2),(0.8,0.8),(2,2)]
// Bends the fold line (0 = the straight Maskit fold)
uniform float Separation; slider[0,0.25,1]
// The set is drawn this thick
uniform float Thickness; slider[0,0.3,1]

#group Kleinian colours
uniform vec3 ShellColor; color[1.0,0.9,0.7]
uniform vec3 DeepColor; color[0.25,0.1,0.45]
uniform float ColorSpeed; slider[0,0.05,0.5]

int depth = 0;

vec2 wrap(vec2 x, vec2 a, vec2 s) {
	x -= s;
	return (x - a * floor(x / a)) + s;
}

float DE(vec3 z) {
	float a = KleinR, b = KleinI;
	float f = sign(b) * Separation;
	float DF = 1.0;
	vec3 lz = z + vec3(1.0), llz = z + vec3(-1.0);
	depth = 0;
	for (int i = 0; i < Iterations; i++) {
		z.x += b / a * z.y;                                   // shear so the lattice translation is along the Maskit line
		z.xz = wrap(z.xz, BoxSize * 2.0, -BoxSize);
		z.x -= b / a * z.y;
		if (z.y >= a * 0.5 + f * (2.0 * a - 1.95) / 4.0 * sign(z.x + b * 0.5) * (1.0 - exp(-(7.2 - (1.95 - a) * 15.0) * abs(z.x + b * 0.5)))) {
			z = vec3(-b, a, 0.0) - z;                           // fold across the line
		}
		float iR = 1.0 / dot(z, z);                           // invert in the unit sphere, flip and translate
		z *= -iR;
		z.x = -b - z.x;
		z.y = a + z.y;
		DF *= max(1.0, iR);
		depth++;
		if (dot(z - llz, z - llz) < 1e-5) break;
		llz = lz; lz = z;
	}
	float y = min(z.y, a - z.y);                          // the distance to the two planes the group keeps mapping the set between
	return min(y, Thickness) / max(DF, 2.0);
}

vec3 baseColor(vec3 point, vec3 normal) {
	DE(point);
	float t = float(depth) * ColorSpeed;
	return mix(ShellColor, DeepColor, clamp(t, 0.0, 1.0)) * (0.8 + 0.2 * cos(6.2831853 * t + vec3(0.0, 2.0, 4.0)));
}

#preset Default
FOV = 0.5
Eye = 0.1,1.2,-3.0
Target = 0,0.9,0
Up = 0,1,0
Iterations = 80
KleinR = 1.95
KleinI = 0.05
BoxSize = 1,1
Separation = 0.25
Thickness = 0.3
ColorSpeed = 0.03
Detail = -3.2
DetailAO = -1.5
MaxRaySteps = 300
FudgeFactor = 0.8
OrbitStrength = 1
BackgroundColor = 0.22,0.24,0.32
GradientBackground = 0.3
#endpreset

#preset Gasket
KleinR = 2.0
KleinI = 0.0
Separation = 0
Eye = 0.1,1.2,-3.0
#endpreset

#preset Down the tunnel
Eye = 0.4,1.3,-2.2
Target = 0,0.9,0
#endpreset

#preset Open tower
KleinR = 1.8
KleinI = 0.2
BoxSize = 1,0.6
Separation = 0.4
Eye = 1.2,1.6,-3.0
#endpreset
