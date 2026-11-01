#info Amazing Surf (Mandelbulb3D): Tglad's fold on x and y only, a sphere fold, scale and rotation
#define providesInit
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Amazing Surf
uniform int Iterations; slider[1,12,40]
uniform float Scale; slider[-4,2,4]
uniform vec2 Fold; slider[(0,0),(1,1),(3,3)]
uniform float MinR2; slider[0.0001,0.25,2]
uniform float FixedR2; slider[0.01,1,4]
uniform vec3 Rotation; slider[(-180,-180,-180),(0,0,0),(180,180,180)]
uniform bool Julia; checkbox[false]
uniform vec3 JuliaC; slider[(-3,-3,-3),(0,0,0),(3,3,3)]

mat3 rot;
void init() { rot = rotationMatrixXYZ(Rotation); }

float DE(vec3 p) {
	vec3 c = Julia ? JuliaC : p;
	float dr = 1.0;
	for (int i = 0; i < Iterations; i++) {
		p.xy = clamp(p.xy, -Fold, Fold) * 2.0 - p.xy;       // Tglad's box fold on two axes only
		float r2 = dot(p, p);
		float f = FixedR2 / clamp(r2, MinR2, FixedR2);
		p *= f;
		dr *= f;
		p = rot * p * Scale + c;
		dr = dr * abs(Scale) + 1.0;
	}
	return length(p) / abs(dr);
}

#preset Default
FOV = 0.5
Eye = 3,2.2,-6
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.5
FudgeFactor = 0.7
BaseColor = 0.8,0.8,0.85
OrbitStrength = 0.6
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
