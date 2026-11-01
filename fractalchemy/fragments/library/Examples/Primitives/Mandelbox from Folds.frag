#info The Mandelbox written with foldBox and foldSphere from Primitives.frag
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Mandelbox
uniform int Iterations; slider[1,12,30]
uniform float Scale; slider[-4,2,4]
uniform float MinRadius2; slider[0,0.25,2]
uniform float FixedRadius2; slider[0,1,4]
uniform float FoldingLimit; slider[0,1,2]
// Julia mode keeps the offset fixed instead of adding the start point
uniform bool Julia; checkbox[false]
uniform vec3 JuliaC; slider[(-2,-2,-2),(0,0,0),(2,2,2)]

float DE(vec3 p) {
	vec3 offset = Julia ? JuliaC : p;
	float dr = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p = foldBox(p, FoldingLimit);
		p = foldSphere(p, dr, MinRadius2, FixedRadius2);
		p = Scale * p + offset;
		dr = dr * abs(Scale) + 1.0;
	}
	return length(p) / abs(dr);
}

#preset Default
FOV = 0.4
Eye = 13,10,-17
Target = 0,0,0
Up = 0,1,0
Detail = -3.0
DetailAO = -1.5
BaseColor = 0.7,0.75,0.8
OrbitStrength = 0.7
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
