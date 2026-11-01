#info kamoshika's very compact Menger sponge. From Jon Baker's Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,5,10]
uniform float Offset; slider[0.1,0.3333,0.6]
uniform float Scale; slider[2,3,4]
uniform vec3 BoxSize; slider[(0.1,0.1,0.1),(1,1,1),(3,3,3)]

float DE(vec3 p) {
	float a = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = abs(p) - Offset;
		if (p.y > p.x) p.xy = p.yx;
		if (p.z > p.y) p.yz = p.zy;
		p.z = abs(p.z);
		p *= Scale;
		p -= 1.0;
		a *= Scale;
	}
	return length(max(abs(p) - BoxSize, 0.0)) / a;
}

#preset Default
FOV = 0.4
Eye = 2.2,1.7,-2.6
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.9,0.85,0.7
OrbitStrength = 0
BackgroundColor = 0.3,0.33,0.4
GradientBackground = 0.3
#endpreset
