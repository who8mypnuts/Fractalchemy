#info Inigo Quilez's Apollonian gasket (sphere inversions in a repeated cell). MIT; listed in the Distance Estimator Compendium.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,6,12]
uniform float K; slider[0.5,0.95,1.5]
// Nudges the cell away from the origin (iq's trick)
uniform float Trick; slider[0,0.04,0.2]
uniform float Thickness; slider[0,0.02,0.1]

float DE(vec3 p) {
	float scale = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = -1.0 + 2.0 * fract(0.5 * p + 0.5);
		p -= sign(p) * Trick;
		float r2 = dot(p, p);
		float k = K / r2;
		p *= k;
		scale *= k;
	}
	float d1 = sqrt(min(min(dot(p.xy, p.xy), dot(p.yz, p.yz)), dot(p.zx, p.zx))) - Thickness;
	float d2 = abs(p.y);
	return 0.5 * min(d1, d2) / scale;
}

#preset Default
FOV = 0.5
Eye = 1.4,1.1,-1.9
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
BaseColor = 0.95,0.9,0.8
OrbitStrength = 0.4
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.28,0.3,0.38
GradientBackground = 0.3
#endpreset
