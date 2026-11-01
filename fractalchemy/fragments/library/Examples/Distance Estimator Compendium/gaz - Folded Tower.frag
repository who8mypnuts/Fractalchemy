#info Folded tower by gaziya5 (gaz). From Jon Baker's Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Fractal
uniform int Iterations; slider[1,6,16]
uniform float PreOffset; slider[0,1.2,3]
uniform vec3 Offset; slider[(0,0,0),(0.6,0.6,3.5),(4,4,8)]
uniform float MinR2; slider[0.01,0.1,1]
uniform float Scale; slider[0.5,2,4]
uniform float ClampSize; slider[0.1,1.5,5]

float DE(vec3 p) {
	p = abs(p) - PreOffset;
	if (p.x < p.z) p.xz = p.zx;
	if (p.y < p.z) p.yz = p.zy;
	if (p.x < p.y) p.xy = p.yx;
	float s = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = abs(p);
		float r = Scale / clamp(dot(p, p), MinR2, 1.0);
		s *= r;
		p *= r;
		p -= Offset;
	}
	p -= clamp(p, -ClampSize, ClampSize);
	return length(p) / s;
}

#preset Default
FOV = 0.4
Eye = 4.5,3.2,-5.5
Target = 0,0.3,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
FudgeFactor = 0.6
BaseColor = 0.8,0.8,0.85
OrbitStrength = 0.5
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
