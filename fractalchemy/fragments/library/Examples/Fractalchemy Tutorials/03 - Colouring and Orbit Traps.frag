#info Tutorial 3: colouring a fractal — orbit traps, the Coloring tab, and your own baseColor()
// STEP 1: providesColor tells the raytracer to call our baseColor(point, normal) instead of its own orbit-trap mix.
#define providesColor
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Colouring
uniform int Iterations; slider[1,8,16]
uniform float Power; slider[2,8,16]
// STEP 2: A colour annotation: color[r,g,b] gives a swatch that opens the colour picker.
uniform vec3 ColorA; color[0.9,0.3,0.1]
uniform vec3 ColorB; color[0.1,0.4,0.9]
// How fast the colour cycles with the orbit trap
uniform float Cycles; slider[0.1,2,10]
// STEP 3: Parameters ▸ Colours from the Gradient Library fills every colour swatch from a gradient in one go.

float trap;

// STEP 4: An orbit trap records something about the orbit (here the smallest |z|) while the DE iterates.
float DE(vec3 p) {
	vec3 z = p;
	float dr = 1.0;
	trap = 1e9;
	for (int i = 0; i < Iterations; i++) {
		float r = length(z);
		if (r > 4.0) break;
		trap = min(trap, r);
		float theta = acos(clamp(z.z / r, -1.0, 1.0)) * Power, phi = atan(z.y, z.x) * Power;
		dr = pow(r, Power - 1.0) * Power * dr + 1.0;
		z = pow(r, Power) * vec3(sin(theta) * cos(phi), sin(theta) * sin(phi), cos(theta)) + p;
	}
	float r = length(z);
	return 0.5 * log(r) * r / dr;
}

void init() {}

// STEP 5: baseColor runs once per hit: call DE again to refresh the trap for the hit point, then turn it into a colour.
vec3 baseColor(vec3 point, vec3 normal) {
	DE(point);
	float t = 0.5 + 0.5 * cos(trap * Cycles * 6.2831853);
	return mix(ColorA, ColorB, t);
}

// STEP 6: The Coloring tab's OrbitStrength mixes BaseColor with baseColor(); set it to 1 to see only this function.
#preset Default
FOV = 0.5
Eye = 2.4,1.8,-3.0
Target = 0,0,0
Up = 0,1,0
Iterations = 8
Power = 8
Cycles = 2
Detail = -3.0
OrbitStrength = 1
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
