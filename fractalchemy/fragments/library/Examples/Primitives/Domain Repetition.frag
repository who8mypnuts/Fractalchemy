#info Domain repetition: tori repeated around an axis and links on a limited grid, all from Primitives.frag
#include "MathUtils.frag"
#include "DE-Raytracer.frag"
#include "Primitives.frag"

#group Repetition
// How many tori around the y axis
uniform float Wedges; slider[1,8,24]
// Distance of the ring of tori from the axis
uniform float RingRadius; slider[0,2.2,5]
uniform float TorusRadius; slider[0.05,0.5,2]
uniform float TubeRadius; slider[0.01,0.12,0.5]
// Links on a grid: spacing and how many on each side
uniform float GridSpacing; slider[0.3,1.2,3]
uniform vec3 GridLimit; slider[(0,0,0),(1,0,1),(4,4,4)]
uniform float LinkSize; slider[0.05,0.3,1]

float DE(vec3 p) {
	vec3 q = p;
	q.xz = opRepeatPolar(q.xz, Wedges);
	q.x -= RingRadius;
	float ring = sdTorus(q.xzy, TorusRadius, TubeRadius);
	vec3 g = opRepeatLimited(p, GridSpacing, GridLimit);
	float links = sdLink(g, LinkSize, LinkSize * 0.7, LinkSize * 0.25);
	return min(ring, links);
}

#preset Default
FOV = 0.4
Eye = 4.2,4.0,-5.6
Target = 0,0,0
Up = 0,1,0
Detail = -3.0
DetailAO = -1.3
BaseColor = 0.85,0.8,0.7
OrbitStrength = 0
BackgroundColor = 0.3,0.35,0.45
GradientBackground = 0.3
#endpreset
