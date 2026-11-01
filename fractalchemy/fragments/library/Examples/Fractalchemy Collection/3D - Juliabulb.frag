#info Juliabulb: the Mandelbulb iteration z^n + c with a fixed c, so every point is a Julia set of the bulb
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Triplex.frag"

#group Juliabulb
uniform int Iterations; slider[1,12,40]
uniform float Power; slider[1,8,16]
uniform vec3 JuliaC; slider[(-2,-2,-2),(0.3,0.55,-0.3),(2,2,2)]
uniform float Bailout; slider[2,8,64]

float DE(vec3 p) {
	vec3 z = p;
	float dr = 1.0;
	for (int i = 0; i < Iterations; i++) {
		dr = tPowDeriv(z, Power, dr);
		z = tPow(z, Power) + JuliaC;
		if (length(z) > Bailout) break;
	}
	return tDistance(z, dr);
}

#preset Default
FOV = 0.5
Eye = 2.4,1.8,-3.0
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.5
BaseColor = 0.85,0.8,0.8
OrbitStrength = 0.7
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
