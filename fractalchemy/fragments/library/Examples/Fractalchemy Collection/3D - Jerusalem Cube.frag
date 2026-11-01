#info Jerusalem cube: a cube minus a cross of slabs, with the 8 corner cubes (scale 1+sqrt 2) and 12 edge cubes (scale (1+sqrt 2)^2) repeating the pattern
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Jerusalem
uniform int Iterations; slider[1,4,10]
// The Jerusalem ratio is 1 + sqrt(2) = 2.41421; other values give related carvings
uniform float Ratio; slider[2.1,2.41421356,3.2]

float DE(vec3 p) {
	float k = Ratio;
	float a = 2.0 / k;               // corner cube side
	float b = 2.0 / (k * k);         // edge cube side (also the slab width)
	float s = 1.0;
	float d = sdBox(p, vec3(1.0));
	for (int i = 0; i < Iterations; i++) {
		p = abs(p);
		if (p.x < p.y) p.xy = p.yx;
		if (p.x < p.z) p.xz = p.zx;
		if (p.y < p.z) p.yz = p.zy;              // now p.x >= p.y >= p.z
		if (p.z > b * 0.5) {                      // a corner cube: centre at 1 - a/2 on every axis
			p = (p - (1.0 - a * 0.5)) * k;
			s *= k;
		} else {                                  // an edge cube (or the hole): two coordinates near 1, one near 0
			p = vec3(p.x - (1.0 - b * 0.5), p.y - (1.0 - b * 0.5), p.z) * k * k;
			s *= k * k;
		}
		d = max(d, sdBox(p, vec3(1.0)) / s);
	}
	return d;
}

#preset Default
FOV = 0.4
Eye = 2.6,2.0,-3.0
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.5
BaseColor = 0.9,0.85,0.7
OrbitStrength = 0
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
