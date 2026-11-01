#info Kali's kaliset towers (the 'Kali set' folded over a repeated plane). From the Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,14,24]
uniform vec3 Fold; slider[(-4,-4,-4),(0,2,0),(4,4,4)]
uniform vec3 Offset; slider[(-2,-2,-2),(0.5,1,0.5),(2,2,2)]
uniform float MinR2; slider[0.01,0.4,1.5]
uniform float Scale; slider[0.5,2,4]

float DE(vec3 p) {
	p.xz = abs(0.5 - mod(p.xz, 1.0)) + 0.01;
	float DEfactor = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = abs(p) - Fold;
		float r2 = dot(p, p);
		float sc = Scale / clamp(r2, MinR2, 1.0);
		p *= sc;
		DEfactor *= sc;
		p = p - Offset;
	}
	return length(p) / DEfactor - 0.0005;
}

#preset Default
FOV = 0.5
Eye = 1.8,1.4,-2.4
Target = 0.5,0.2,0.5
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.6
BaseColor = 0.8,0.75,0.7
OrbitStrength = 0.5
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
