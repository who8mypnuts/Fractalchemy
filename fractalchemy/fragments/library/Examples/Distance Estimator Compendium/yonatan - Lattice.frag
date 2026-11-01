#info yonatan's repeated lattice (an IFS in a unit cell). From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,7,12]
uniform vec3 Offset; slider[(0,0,0),(2,0,3),(5,5,8)]
uniform float Scale; slider[1.5,3,4]

float DE(vec3 p) {
	p = fract(p) - 0.5;
	vec3 O = Offset;
	float s = 1.0;
	for (int j = 0; j < Iterations; j++) {
		p = abs(p);
		p = (p.x < p.y ? p.zxy : p.zyx) * Scale - O;
		if (p.z < -0.5 * O.z) p.z += O.z;
		s *= Scale;
	}
	return length(p.xy) / s;
}

#preset Default
FOV = 0.4
Eye = 1.9,1.4,-2.3
Target = 0.5,0.5,0.5
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.6
BaseColor = 0.9,0.9,0.9
OrbitStrength = 0
BackgroundColor = 0.28,0.3,0.38
GradientBackground = 0.3
#endpreset
