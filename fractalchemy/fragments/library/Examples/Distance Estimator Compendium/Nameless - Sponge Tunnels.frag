#info Sponge tunnels by Nameless. From Jon Baker's Distance Estimator Compendium, CC BY-NC-SA 3.0.
#include "MathUtils.frag"
#include "DE-Raytracer.frag"

#group Fractal
uniform int Iterations; slider[1,14,20]
uniform vec3 Fold; slider[(0,0,0),(2,4,2),(8,8,8)]
uniform float Repeat; slider[1,8,16]
uniform float Scale; slider[1,9,20]
uniform float MaxR2; slider[1,12,30]
uniform float ClampSize; slider[0.1,1.2,3]

float DE(vec3 p0) {
	vec4 p = vec4(p0, 3.0);
	p *= 2.0 / min(dot(p.xyz, p.xyz), 30.0);
	for (int i = 0; i < Iterations; i++) {
		p.xyz = Fold - (abs(p.xyz) - Fold);
		p.xyz = mod(p.xyz - Repeat * 0.5, Repeat) - Repeat * 0.5;
		p *= Scale / min(dot(p.xyz, p.xyz), MaxR2);
	}
	p.xyz -= clamp(p.xyz, -ClampSize, ClampSize);
	return length(p.xyz) / p.w;
}

#preset Default
FOV = 0.5
Eye = 1.6,1.2,-2.2
Target = 0,0,0
Up = 0,1,0
Detail = -3.4
DetailAO = -1.5
FudgeFactor = 0.6
BaseColor = 0.85,0.8,0.75
OrbitStrength = 0.5
X = 0.5,0.6,0.6,0.7
Y = 1,0.6,0,0.4
Z = 0.8,0.78,1,0.5
R = 0.4,0.7,1,0.12
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
