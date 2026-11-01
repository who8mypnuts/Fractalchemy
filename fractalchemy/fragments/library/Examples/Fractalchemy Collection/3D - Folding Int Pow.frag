#info FoldingIntPow (Mandelbulb3D): Tglad's fold followed by an integer triplex power and a Z multiplier
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Triplex.frag"

#group FoldingIntPow
uniform int Iterations; slider[1,10,30]
uniform float Power; slider[2,3,8]
uniform float Fold; slider[0,1,3]
uniform float ZMul; slider[-3,1,3]
uniform float Bailout; slider[2,8,64]
uniform bool Julia; checkbox[false]
uniform vec3 JuliaC; slider[(-2,-2,-2),(0.2,0.4,0.1),(2,2,2)]

float DE(vec3 p) {
	vec3 c = Julia ? JuliaC : p;
	vec3 z = p;
	float dr = 1.0;
	float r = length(z);
	for (int i = 0; i < Iterations; i++) {
		z = abs(z + Fold) - abs(z - Fold) - z;
		dr = tPowDeriv(z, Power, dr);
		z = tPow(z, Power);
		z.z *= ZMul;
		z += c;
		r = length(z);
		if (r > Bailout) break;
	}
	return tDistance(z, dr);
}

#preset Default
FOV = 0.5
Eye = 6,4,-8
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.5
FudgeFactor = 0.5
BaseColor = 0.8,0.8,0.85
OrbitStrength = 0.7
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
