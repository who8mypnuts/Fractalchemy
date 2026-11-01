#info European 4-in-1 chain maille: a grid of tilted tori (athibaul, Distance Estimator Compendium, CC BY-NC-SA 3.0)
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Maille
uniform float RingRadius; slider[0.1,0.4,1]
uniform float WireRadius; slider[0.01,0.07,0.3]
// Tilt of every ring
uniform float Angle; slider[0,0.3,1.5]
uniform vec2 Separation; slider[(0.2,0.2),(1,0.8),(3,3)]
// Rings on each side of the origin (0 = endless)
uniform float Extent; slider[0,4,20]

float torusGrid(vec3 p, float r_small, float r_large, float angle, vec2 sep) {
	vec3 q = p - vec3(round(p.xy / sep) * sep, 0.0) - vec3(0.0, sep.y / 2.0, 0.0);
	q.yz *= rot2(angle);
	float d = sdTorus(q.xzy, r_large, r_small);
	q = p - vec3(round(p.xy / sep) * sep, 0.0) - vec3(0.0, -sep.y / 2.0, 0.0);
	q.yz *= rot2(angle);
	return min(d, sdTorus(q.xzy, r_large, r_small));
}

float DE(vec3 p) {
	float d = torusGrid(p, WireRadius, RingRadius, Angle, Separation);
	d = min(d, torusGrid(p - vec3(Separation / 2.0, 0.0), WireRadius, RingRadius, -Angle, Separation));
	if (Extent > 0.0) d = max(d, sdBox(p, vec3(Extent * Separation.x, Extent * Separation.y, 2.0)));
	return d;
}

#preset Default
FOV = 0.4
Eye = 2.4,-1.8,-6.0
Target = 0,0,0
Up = 0,1,0
Detail = -3.2
DetailAO = -1.4
BaseColor = 0.9,0.85,0.6
OrbitStrength = 0
Specular = 1.5
SpecularExp = 30
BackgroundColor = 0.25,0.28,0.35
GradientBackground = 0.3
#endpreset
