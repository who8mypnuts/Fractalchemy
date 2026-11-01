#info Möbius / sphere-inversion IFS: fold into an octant, invert in a sphere, scale and offset — a Kleinian-flavoured limit set
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Inversion
uniform int Iterations; slider[1,8,24]
// Fold offset before every inversion
uniform vec3 Fold; slider[(-3,-3,-3),(1,1,1),(3,3,3)]
// Inversion radius squared (the sphere everything is reflected in)
uniform float Radius2; slider[0.1,2,8]
uniform float MinR2; slider[0.01,0.2,2]
uniform float MaxR2; slider[0.5,1.5,8]
uniform vec3 Offset; slider[(-4,-4,-4),(0.6,0.6,2.5),(4,4,8)]
uniform float Thickness; slider[0,0.01,0.3]

float DE(vec3 p) {
	float s = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = abs(p) - Fold;
		float f = Radius2 / clamp(dot(p, p), MinR2, MaxR2);       // inversion in the sphere, clamped (a sphere fold)
		p *= f;
		s *= f;
		p -= Offset;
	}
	return (length(p.xz) - Thickness * s) / s;
}

#preset Default
FOV = 0.5
Eye = 3.6,2.6,-4.8
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.5
FudgeFactor = 0.6
BaseColor = 0.85,0.85,0.9
OrbitStrength = 0.6
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
