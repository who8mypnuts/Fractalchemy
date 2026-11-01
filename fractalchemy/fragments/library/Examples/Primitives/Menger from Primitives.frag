#info Menger sponge built from a box and repeated crosses (Inigo Quilez's construction)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Menger
uniform int Iterations; slider[0,4,8]
// Width of the holes (1 = the classic sponge)
uniform float HoleWidth; slider[0.1,1.0,1.9]
// Twist the space before carving (0 = straight)
uniform float Twist; slider[-2,0,2]
// Bend the space before carving
uniform float Bend; slider[-1,0,1]

float DE(vec3 p) {
	p = opTwist(p, Twist);
	p = opBend(p, Bend);
	float d = sdBox(p, vec3(1.0));
	float s = 1.0;
	for (int m = 0; m < Iterations; m++) {
		vec3 a = mod(p * s, 2.0) - 1.0;
		s *= 3.0;
		vec3 r = abs(1.0 - 3.0 * abs(a));
		float c = sdCross(r, HoleWidth) / s;      // negative inside the three beams
		d = max(d, c);
	}
	return d;
}

#preset Default
FOV = 0.4
Eye = 2.8,2.1,-3.2
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.95,0.85,0.6
OrbitStrength = 0
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset
